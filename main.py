# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests
from sqlalchemy import create_engine, text
import google.generativeai as genai
from sentence_transformers import SentenceTransformer  # Make sure this is imported
import time
import random
import requests  # Added for Slack notifications

# --- INITIALIZATION ---
# Load environment variables and initialize models just once when the app starts
load_dotenv()
app = FastAPI(title="DevOps Sentinel Query Agent", version="1.0.0")

# --- GEMINI CONFIGURATION ---
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is required!")
genai.configure(api_key=google_api_key)
# --- END GEMINI CONFIGURATION ---

# Validate database environment variables
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")

if not all([tidb_host, tidb_port, tidb_user, tidb_password]):
    raise ValueError("Missing required TiDB environment variables!")

# Convert port to integer
try:
    tidb_port = int(tidb_port)
except (ValueError, TypeError):
    raise ValueError(f"TIDB_PORT must be a valid integer, got: {tidb_port}")

# Database connection with correct SSL path for Windows
DB_NAME = "devops_sentinel"
ssl_ca_path = os.path.abspath("isrgrootx1.pem")
connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_ca={ssl_ca_path}"
engine = create_engine(connection_string)

# --- LAZY MODEL LOADING ---
print("Initializing application...")

# Don't load the model during startup - load it when needed
sentence_model = None

def get_sentence_model():
    """Lazy load the sentence transformer model"""
    global sentence_model
    if sentence_model is None:
        print("Loading embedding model...")
        try:
            # Try to load the model
            sentence_model = SentenceTransformer('all-mpnet-base-v2')
            print("Embedding model loaded successfully!")
        except Exception as e:
            print(f"Failed to load model: {e}")
            # Try alternative smaller model
            try:
                print("Trying smaller model...")
                sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("Smaller model loaded successfully!")
            except Exception as e2:
                print(f"Failed to load smaller model: {e2}")
                raise Exception("Cannot load any embedding model. Please check your internet connection.")
    
    return sentence_model

# Initialize the Gemini model (for generation)
print("Initializing Gemini model...")
generation_model = genai.GenerativeModel('gemini-2.5-flash')  # Much higher free tier limits

print("--- Gemini 2.5 Flash initialized successfully ---")


# --- API DATA MODELS ---
# Define the structure of the request we expect
class QueryRequest(BaseModel):
    question: str
    
    class Config:
        # Example for API documentation
        schema_extra = {
            "example": {
                "question": "What should I do about database connection timeouts?"
            }
        }

class QueryResponse(BaseModel):
    question: str
    answer: str
    source_context: str
    success: bool

class SlackRequest(BaseModel):
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "message": "High CPU usage detected on production database server"
            }
        }

class AlertRequest(BaseModel):
    title: str
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Database Connection Timeout Alert",
                "message": "Multiple connection timeouts detected on production database server"
            }
        }

# --- Global cache for health status ---
# We store the status outside the function to remember it between calls
health_cache = {
    "status": "unhealthy",
    "database": "unknown", 
    "gemini": "unknown",
    "last_check_time": 0  # Store the time of the last check
}
CACHE_DURATION_SECONDS = 60  # Check status only once per minute

# --- API ENDPOINTS ---
@app.get("/")
def root():
    return {"message": "DevOps Sentinel Query Agent with Gemini AI is running!"}

@app.get("/health")
def health_check():
    """
    Health check endpoint with caching to avoid hitting API rate limits.
    """
    current_time = time.time()
    
    # Check if the cache is older than our duration (60 seconds)
    if (current_time - health_cache["last_check_time"]) > CACHE_DURATION_SECONDS:
        print("DEBUG: Health check cache expired. Performing new health check...")
        
        try:
            # Test database connection
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            health_cache["database"] = "connected"
            
            # Test Gemini API (only if we haven't hit rate limits recently)
            try:
                test_response = generation_model.generate_content("Hello")
                if test_response.text:
                    health_cache["gemini"] = "available"
                else:
                    health_cache["gemini"] = "error"
            except Exception as gemini_error:
                error_msg = str(gemini_error)
                if "429" in error_msg or "quota" in error_msg.lower():
                    health_cache["gemini"] = "rate_limited"
                    print("DEBUG: Gemini rate limited during health check")
                else:
                    health_cache["gemini"] = "unavailable"
                    print(f"DEBUG: Gemini error during health check: {gemini_error}")

            # Set overall status based on components
            if health_cache["database"] == "connected":
                if health_cache["gemini"] in ["available", "rate_limited"]:
                    health_cache["status"] = "healthy"
                else:
                    health_cache["status"] = "degraded"  # DB works, AI doesn't
            else:
                health_cache["status"] = "unhealthy"
            
        except Exception as e:
            print(f"DEBUG: Health check failed: {e}")
            health_cache["status"] = "unhealthy"
            health_cache["database"] = "disconnected"
            
        # Update the time of the last check
        health_cache["last_check_time"] = current_time
        print(f"DEBUG: Health check completed. Status: {health_cache['status']}")
    else:
        # Cache is still fresh, return cached results
        time_since_check = current_time - health_cache["last_check_time"]
        print(f"DEBUG: Using cached health status (checked {time_since_check:.1f} seconds ago)")

    # Always return the content of the cache
    return health_cache

@app.post("/query-agent/", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    """Query the knowledge base using vector similarity search and generate answer with Gemini"""
    
    try:
        print(f"DEBUG: Processing question: {request.question}")  # Added debug logging
        
        # 1. Create embedding for the incoming question
        query_embedding = get_sentence_model().encode(request.question).tolist()
        print(f"DEBUG: Generated embedding with {len(query_embedding)} dimensions")  # Added debug logging
        
        # 2. Convert to proper vector format for TiDB
        query_vector = f"[{','.join(map(str, query_embedding))}]"
        
        # 3. Perform vector search in TiDB to get context
        with engine.connect() as connection:
            stmt = text("""
                SELECT 
                    content_chunk,
                    source_file,
                    VEC_COSINE_DISTANCE(embedding, VEC_FROM_TEXT(:query_vector)) as distance
                FROM knowledgebase
                ORDER BY distance ASC
                LIMIT 3;
            """)
            
            result = connection.execute(stmt, {"query_vector": query_vector})
            rows = result.fetchall()
        
        print(f"DEBUG: Found {len(rows)} relevant documents")  # Added debug logging
        
        if not rows:
            print("DEBUG: No relevant documents found in knowledge base")  # Added debug logging
            return {
                "question": request.question,
                "answer": "I couldn't find any relevant information in the knowledge base to answer your question.",
                "source_context": "No relevant documents found",
                "success": False
            }

        # Get the best matching context (lowest distance = highest similarity)
        best_context = rows[0][0]  # content_chunk
        source_file = rows[0][1]   # source_file
        
        # Combine multiple contexts for richer answers
        all_contexts = "\n\n".join([row[0] for row in rows[:2]])  # Top 2 results
        
        print(f"DEBUG: Using context from: {source_file}")  # Added debug logging
        
        # --- STEP 4 - GENERATE AN ANSWER USING GEMINI ---
        try:
            print("DEBUG: Calling Gemini API...")
            
            # Create a clean prompt for Gemini
            prompt = f"""
You are a helpful and knowledgeable DevOps assistant. Based on the context provided below, answer the user's question in a clear, practical, and actionable way.

Context from knowledge base:
{all_contexts}

User Question: {request.question}

Instructions:
- Provide a direct, helpful answer based on the context
- Include specific steps or recommendations when applicable
- If the context doesn't fully answer the question, mention what information is available
- Keep the response practical and actionable for DevOps scenarios
"""
            
            # Try calling Gemini with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = generation_model.generate_content(prompt)
                    llm_answer = response.text
                    print("DEBUG: Successfully received response from Gemini")
                    break
                except Exception as retry_error:
                    if "429" in str(retry_error) or "quota" in str(retry_error).lower():
                        if attempt < max_retries - 1:
                            # Wait with exponential backoff
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            print(f"DEBUG: Rate limited, waiting {wait_time:.1f} seconds before retry {attempt + 1}/{max_retries}")
                            time.sleep(wait_time)
                            continue
                    raise retry_error
            
            # Return the final, polished answer from Gemini
            return {
                "question": request.question,
                "answer": llm_answer,
                "source_context": f"Source: {source_file}\n\nContext: {best_context}",
                "success": True
            }
            
        except Exception as e:
            # --- THIS IS THE KEY CHANGE - DETAILED GEMINI ERROR LOGGING ---
            print(f"DEBUG: An error occurred with the Gemini API: {e}")
            print(f"DEBUG: Error type: {type(e).__name__}")
            print(f"DEBUG: Error details: {str(e)}")
            
            # Try to get more specific error information
            if hasattr(e, 'response'):
                print(f"DEBUG: Response status: {e.response}")
            if hasattr(e, 'details'):
                print(f"DEBUG: Error details: {e.details}")
            
            # Fallback: return context without Gemini if API fails
            return {
                "question": request.question,
                "answer": f"LLM service unavailable. Here's the relevant information from the knowledge base:\n\n{best_context}",
                "source_context": f"Source: {source_file}",
                "success": False
            }
            
    except Exception as e:
        print(f"DEBUG: General query processing error: {e}")  # Added debug logging
        print(f"DEBUG: Error type: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@app.post("/notify-slack/")
def notify_slack(request: SlackRequest):
    """Sends a message to a configured Slack channel."""
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        raise HTTPException(status_code=500, detail="Slack webhook URL is not configured.")

    try:
        print(f"DEBUG: Sending message to Slack: {request.message[:100]}...")  # Added debug logging
        
        # Format the message for Slack's API
        payload = {"text": f"🤖 DevOps Sentinel Alert:\n\n{request.message}"}

        # Send the request
        response = requests.post(slack_webhook_url, json=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        print("DEBUG: Successfully sent message to Slack")  # Added debug logging
        return {"success": True, "message": "Notification sent to Slack."}
        
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Failed to send to Slack: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification to Slack: {str(e)}")

@app.post("/alert-trigger/")
async def alert_trigger(request: AlertRequest):
    """
    Receives an alert, processes it through the full RAG pipeline, 
    and sends a notification to Slack with AI-generated solution.
    """
    print(f"DEBUG: Received alert: {request.title}")
    
    try:
        # --- 1. Run the RAG Process (Logic from /query-agent/) ---
        question = request.message
        query_embedding = get_sentence_model().encode(question).tolist()
        print(f"DEBUG: Generated embedding for alert with {len(query_embedding)} dimensions")
        
        # Convert to proper vector format for TiDB
        query_vector = f"[{','.join(map(str, query_embedding))}]"
        
        # Perform vector search in TiDB to get context
        with engine.connect() as connection:
            stmt = text("""
                SELECT 
                    content_chunk,
                    source_file,
                    VEC_COSINE_DISTANCE(embedding, VEC_FROM_TEXT(:query_vector)) as distance
                FROM knowledgebase
                ORDER BY distance ASC
                LIMIT 2;
            """)
            
            result = connection.execute(stmt, {"query_vector": query_vector})
            rows = result.fetchall()
        
        print(f"DEBUG: Found {len(rows)} relevant documents for alert")
        
        if not rows:
            print("DEBUG: No relevant runbook found for this alert")
            return {
                "error": "No relevant runbook documents found for this alert.",
                "success": False,
                "alert_title": request.title
            }

        # Get the best matching context
        retrieved_chunk = rows[0][0]  # content_chunk
        source_file = rows[0][1]     # source_file
        
        # Combine multiple contexts if available
        all_contexts = "\n\n".join([row[0] for row in rows])
        
        print(f"DEBUG: Using runbook context from: {source_file}")

        # --- 2. Generate Answer with Gemini ---
        try:
            print("DEBUG: Calling Gemini API for alert processing...")
            
            prompt = f"""
You are an expert DevOps incident response assistant. An alert has fired with the following details:

**Alert Title:** {request.title}Invoke-RestMethod -Uri "http://127.0.0.1:8000/process-input/" -Method POST -ContentType "application/json" -Body '{"question": "What should I do about database connection timeouts?"}'Invoke-RestMethod -Uri "http://127.0.0.1:8000/process-input/" -Method POST -ContentType "application/json" -Body '{"question": "What should I do about database connection timeouts?"}'Invoke-RestMethod -Uri "http://127.0.0.1:8000/process-input/" -Method POST -ContentType "application/json" -Body '{"question": "What should I do about database connection timeouts?"}'
**Alert Message:** {request.message}

Based on the runbook context below, provide a concise, actionable solution:

**Runbook Context:**
{all_contexts}

Instructions:
- Provide immediate action steps to resolve this alert
- Include specific commands or procedures if available in the context
- Prioritize critical actions first
- Keep the response focused and actionable for incident response
- If the context doesn't fully cover the alert, mention what steps are available
"""
            
            # Try calling Gemini with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = generation_model.generate_content(prompt)
                    llm_answer = response.text
                    print("DEBUG: Successfully received alert response from Gemini")
                    break
                except Exception as retry_error:
                    if "429" in str(retry_error) or "quota" in str(retry_error).lower():
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            print(f"DEBUG: Rate limited, waiting {wait_time:.1f} seconds before retry {attempt + 1}/{max_retries}")
                            time.sleep(wait_time)
                            continue
                    raise retry_error
                    
        except Exception as e:
            print(f"DEBUG: Gemini failed on alert processing: {e}")
            # Fallback to context-only response
            llm_answer = f"Alert received but LLM service unavailable. Here's the relevant runbook information:\n\n{retrieved_chunk}"

        # --- 3. Send the Final Answer to Slack ---
        slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not slack_webhook_url:
            print("DEBUG: Slack webhook URL not configured")
            return {
                "error": "Slack webhook URL is not configured.",
                "success": False,
                "generated_solution": llm_answer,
                "alert_title": request.title
            }
        
        # Format the final message for Slack
        final_message = f"""🚨 **ALERT: {request.title}** 🚨

📋 **Alert Details:**
{request.message}

🤖 **DevOps Sentinel's Recommended Action:**
{llm_answer}

📚 **Source:** {source_file}
⏰ **Processed:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}"""
        
        try:
            print("DEBUG: Sending alert resolution to Slack...")
            payload = {"text": final_message}
            slack_response = requests.post(slack_webhook_url, json=payload, timeout=10)
            slack_response.raise_for_status()

            print("DEBUG: Alert notification sent to Slack successfully")
            return {
                "success": True,
                "message": "Alert processed and notification sent to Slack.",
                "alert_title": request.title
            }
            
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: Failed to send alert notification to Slack: {e}")
            return {
                "success": False,
                "error": f"Alert processed but failed to send notification to Slack: {str(e)}",
                "generated_solution": llm_answer,
                "alert_title": request.title
            }
        
    except Exception as e:
        print(f"DEBUG: General alert processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Alert processing failed: {str(e)}")

# --- Additional utility endpoints ---
@app.get("/stats")
def get_stats():
    """Get statistics about the knowledge base"""
    try:
        with engine.connect() as connection:
            # Get total count
            result = connection.execute(text("SELECT COUNT(*) as total FROM knowledgebase"))
            total_chunks = result.fetchone()[0]
            
            # Get unique sources
            result = connection.execute(text("SELECT COUNT(DISTINCT source_file) as sources FROM knowledgebase"))
            unique_sources = result.fetchone()[0]
            
            return {
                "total_chunks": total_chunks,
                "unique_sources": unique_sources,
                "embedding_model": "all-mpnet-base-v2",
                "vector_dimensions": 768,
                "llm_model": "gemini-2.5-flash"
            }
    except Exception as e:
        print(f"DEBUG: Stats endpoint error: {e}")  # Added debug logging
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.post("/test-gemini/")
def test_gemini(request: QueryRequest):
    """Test Gemini API directly"""
    try:
        print(f"DEBUG: Testing Gemini with question: {request.question}")  # Added debug logging
        response = generation_model.generate_content(f"Answer this DevOps question: {request.question}")
        print("DEBUG: Gemini test successful")  # Added debug logging
        return {
            "question": request.question,
            "gemini_response": response.text,
            "success": True
        }
    except Exception as e:
        # --- DETAILED ERROR LOGGING FOR GEMINI TEST ---
        print(f"DEBUG: Gemini test failed: {e}")
        print(f"DEBUG: Error type: {type(e).__name__}")
        print(f"DEBUG: Error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gemini API failed: {str(e)}")

@app.post("/grafana-alert/", response_model=QueryResponse)
def grafana_alert(request_data: dict):
    """
    Receive a Grafana alert or a direct question, process it, 
    and return the answer or send a notification to Slack.
    """
    is_alert = False
    question = ""

    # --- 1. Check the input type and generate a question ---
    if "question" in request_data:
        # It's a direct query from our Streamlit UI
        print("DEBUG: Processing direct question.")
        question = request_data["question"]

    elif request_data.get("status") == "firing" and "alerts" in request_data:
        # It's a structured Grafana alert
        print("DEBUG: Processing structured Grafana alert.")
        is_alert = True
        try:
            # Extract info from the first alert in the payload
            alert_details = request_data["alerts"][0]["labels"]
            alert_name = alert_details.get("alertname", "Unknown Alert")
            service_name = alert_details.get("service", "an unknown service")
            
            # This is the "Reasoning" step: transform data into a question
            question = f"What are the steps to resolve the '{alert_name}' for '{service_name}'?"
            print(f"DEBUG: Transformed alert into question: '{question}'")

        except (KeyError, IndexError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid Grafana alert format: {e}")
    else:
        raise HTTPException(status_code=400, detail="Invalid input format. Must be a direct question or a Grafana alert.")

    # --- 2. Run the RAG Pipeline (this logic is the same) ---
    query_embedding = get_sentence_model().encode(question).tolist()

    retrieved_chunk = None
    with engine.connect() as connection:
        # ... (Your TiDB vector search query remains the same here) ...
        stmt = text("""
            SELECT content_chunk
            FROM knowledgebase
            ORDER BY VEC_COS_SIM(embedding, CAST(:query_embedding AS JSON)) DESC
            LIMIT 1;
        """)
        result = connection.execute(stmt, {"query_embedding": str(query_embedding)}).fetchone()
        if result:
            retrieved_chunk = result[0]

    if not retrieved_chunk:
        return {"answer": "Could not find relevant documents.", "success": False}

    # --- 3. Generate Answer with Gemini (this logic is the same) ---
    try:
        prompt = f"Context: {retrieved_chunk}\n\nQuestion: {question}"
        # ... (Your Gemini call and prompt engineering remains the same here) ...
        response = generation_model.generate_content(prompt)
        llm_answer = response.text
    except Exception as e:
        return {"answer": f"LLM service unavailable: {e}", "success": False}

    # --- 4. Send Response or Notification ---
    if is_alert:
        # If it was an alert, send the solution to Slack
        final_message = f"🚨 **Alert: {alert_name}** 🚨\n\n**🤖 Sentinel's Recommended Action:**\n{llm_answer}"
        # ... (Your Slack notification logic goes here) ...
        requests.post(os.getenv("SLACK_WEBHOOK_URL"), json={"text": final_message})
        print("DEBUG: Sent alert resolution to Slack.")
        return {"status": "Alert processed and sent to Slack."}
    else:
        # If it was a direct question, return the answer to the UI
        return {"question": question, "answer": llm_answer, "source_context": retrieved_chunk, "success": True}

@app.post("/process-input/")
async def process_input(request_data: dict):
    """
    A single, smart endpoint that handles both direct questions (from UI)
    and structured alerts (from Grafana).
    """
    question = ""
    is_alert = False
    alert_name = ""
    service_name = ""

    # --- 1. Check the input type and generate a question ---
    if "question" in request_data:
        # It's a direct query from our Streamlit UI
        print("DEBUG: Processing direct question.")
        question = request_data["question"]
    
    elif request_data.get("status") == "firing" and "alerts" in request_data:
        # It's a structured Grafana alert
        print("DEBUG: Processing structured Grafana alert.")
        is_alert = True
        try:
            # Extract info from the first alert in the payload
            alert_details = request_data["alerts"][0]["labels"]
            alert_name = alert_details.get("alertname", "Unknown Alert")
            service_name = alert_details.get("service", "an unknown service")
            instance = alert_details.get("instance", "unknown instance")
            
            # Get summary from annotations if available
            annotations = request_data["alerts"][0].get("annotations", {})
            summary = annotations.get("summary", "No summary available")
            
            # This is the "Reasoning" step: transform data into a question
            question = f"What are the steps to resolve the '{alert_name}' alert for '{service_name}' on instance '{instance}'? Alert details: {summary}"
            print(f"DEBUG: Transformed alert into question: '{question}'")

        except (KeyError, IndexError) as e:
            print(f"DEBUG: Invalid Grafana alert format: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid Grafana alert format: {e}")
            
    elif "title" in request_data and "message" in request_data:
        # It's a legacy alert format (for backward compatibility)
        print("DEBUG: Processing legacy alert format.")
        is_alert = True
        alert_name = request_data["title"]
        question = request_data["message"]
        
    else:
        raise HTTPException(status_code=400, detail="Invalid input format. Must be a direct question or a Grafana alert.")

    print(f"DEBUG: Final question to process: {question}")

    # Use the same RAG logic from your query-agent endpoint
    try:
        print("DEBUG: Creating embedding for the question...")
        model = get_sentence_model()
        query_embedding = model.encode(question).tolist()
        print(f"DEBUG: Generated embedding with {len(query_embedding)} dimensions")
        
        # Convert to proper vector format for TiDB
        query_vector = f"[{','.join(map(str, query_embedding))}]"
        
        # Perform vector search in TiDB to get context
        with engine.connect() as connection:
            stmt = text("""
                SELECT 
                    content_chunk,
                    source_file,
                    VEC_COSINE_DISTANCE(embedding, VEC_FROM_TEXT(:query_vector)) as distance
                FROM knowledgebase
                ORDER BY distance ASC
                LIMIT 2;
            """)
            
            result = connection.execute(stmt, {"query_vector": query_vector})
            rows = result.fetchall()
        
        print(f"DEBUG: Found {len(rows)} relevant documents")
        
        if not rows:
            return {
                "answer": "Could not find relevant documents in the knowledge base for this query.",
                "success": False,
                "question": question
            }

        # Get the best matching context
        retrieved_chunk = rows[0][0]  # content_chunk
        source_file = rows[0][1]     # source_file
        
        # Combine multiple contexts for richer answers
        all_contexts = "\n\n".join([row[0] for row in rows])
        
        print(f"DEBUG: Using context from: {source_file}")

        # Generate answer with Gemini (same logic as your existing endpoint)
        try:
            print("DEBUG: Calling Gemini API...")
            
            if is_alert:
                prompt = f"""
You are an expert DevOps incident response assistant. An alert has fired with the following details:

**Alert Name:** {alert_name}
**Service:** {service_name}
**Question:** {question}

Based on the runbook context below, provide a concise, actionable solution:

**Runbook Context:**
{all_contexts}

Instructions:
- Provide immediate action steps to resolve this alert
- Include specific commands or procedures if available in the context
- Prioritize critical actions first
- Keep the response focused and actionable for incident response
"""
            else:
                prompt = f"""
You are a helpful and knowledgeable DevOps assistant. Based on the context provided below, answer the user's question in a clear, practical, and actionable way.

Context from knowledge base:
{all_contexts}

User Question: {question}

Instructions:
- Provide a direct, helpful answer based on the context
- Include specific steps or recommendations when applicable
- If the context doesn't fully answer the question, mention what information is available
- Keep the response practical and actionable for DevOps scenarios
"""
            
            response = generation_model.generate_content(prompt)
            llm_answer = response.text
            print("DEBUG: Successfully received response from Gemini")
                    
        except Exception as e:
            print(f"DEBUG: Gemini failed: {e}")
            llm_answer = f"LLM service unavailable. Here's the relevant information from the knowledge base:\n\n{retrieved_chunk}"

        # Return response based on input type
        if is_alert:
            # Send to Slack for alerts
            slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
            if slack_webhook_url:
                final_message = f"""🚨 **ALERT: {alert_name}** 🚨

📋 **Service:** {service_name}
📝 **Details:** {question}

🤖 **DevOps Sentinel's Recommended Action:**
{llm_answer}

📚 **Source:** {source_file}"""
                
                try:
                    requests.post(slack_webhook_url, json={"text": final_message}, timeout=10)
                    return {"status": "Alert processed and sent to Slack.", "success": True}
                except:
                    return {"status": "Alert processed but failed to send to Slack.", "success": False}
            else:
                return {"status": "Alert processed but Slack not configured.", "success": False}
        else:
            # Return to UI for questions
            return {
                "question": question,
                "answer": llm_answer,
                "source_context": f"Source: {source_file}\n\nContext: {retrieved_chunk}",
                "success": True
            }
            
    except Exception as e:
        print(f"DEBUG: Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")