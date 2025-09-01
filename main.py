# main.py

import os
from dotenv import load_dotenv
import sys

# --- ENVIRONMENT SETUP ---
# Load .env file for local development
load_dotenv()

# Debug environment loading
print("=== ENVIRONMENT DEBUG ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Environment check:")

# Check for API key with multiple possible names
api_key_names = ["GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"]
google_api_key = None

for key_name in api_key_names:
    value = os.getenv(key_name)
    if value:
        google_api_key = value
        print(f"✅ Found API key in: {key_name}")
        break
    else:
        print(f"❌ Not found: {key_name}")

if not google_api_key:
    print("❌ CRITICAL ERROR: No Google API key found!")
    print("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if any(term in key.upper() for term in ['API', 'KEY', 'GOOGLE', 'GEMINI']):
            value = os.environ[key]
            masked = f"{value[:5]}...{value[-4:]}" if len(value) > 10 else "***"
            print(f"  {key}: {masked}")
    
    print("⚠️ WARNING: Application will start but Google API will not work!")
    google_api_key = "dummy-key-for-startup"  # Allow startup to continue

print(f"✅ Using API key: {google_api_key[:10]}...{google_api_key[-4:]}")
print("=== END ENVIRONMENT DEBUG ===")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from sqlalchemy import create_engine, text
import google.generativeai as genai
from sentence_transformers import SentenceTransformer 
import time
import random
import requests  # Added for Slack notifications
import certifi
import ssl
#----------------
import asyncio
import schedule
import threading
from datetime import datetime, timedelta
import json
# --- INITIALIZATION ---
app = FastAPI(title="DevOps Sentinel Query Agent", version="1.0.0")

# --- NEW: Add CORS Middleware ---
origins = [
    "http://localhost",
    "http://localhost:8501",  # Local Streamlit development
    "http://127.0.0.1:8501",  # Alternative localhost format
    "https://devops-sentinel-7khjtvmu95xk8faeyoer8u.streamlit.app",  # ← Add your Streamlit Cloud URL
    "https://devops-sentinel-7khjtvmu95xk8faeyoer8u.streamlit.app/",  # With trailing slash
    "https://*.streamlit.app",  # Allow all Streamlit Cloud apps (optional)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("--- CORS middleware configured for Streamlit integration ---")

# --- GEMINI CONFIGURATION ---
genai.configure(api_key=google_api_key)
# --- END GEMINI CONFIGURATION ---

# # Validate database environment variables
# tidb_host = os.getenv("TIDB_HOST")
# tidb_port = os.getenv("TIDB_PORT")
# tidb_user = os.getenv("TIDB_USER")
# tidb_password = os.getenv("TIDB_PASSWORD")

# if not all([tidb_host, tidb_port, tidb_user, tidb_password]):
#     raise ValueError("Missing required TiDB environment variables!")

# # Convert port to integer
# try:
#     tidb_port = int(tidb_port)
# except (ValueError, TypeError):
#     raise ValueError(f"TIDB_PORT must be a valid integer, got: {tidb_port}")

# Database connection for Railway (replace the problematic section)
DB_NAME = "devops_sentinel"

# Get database URL from environment
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Use the full DATABASE_URL (Railway style)
    connection_string = database_url
    print(f"✅ Using DATABASE_URL from environment")
    print(f"✅ Database connection configured (Railway mode)")
else:
    # Fallback to individual components (local development)
    tidb_host = os.getenv("TIDB_HOST")
    tidb_port = os.getenv("TIDB_PORT", "4000")
    tidb_user = os.getenv("TIDB_USER")
    tidb_password = os.getenv("TIDB_PASSWORD")
    
    if all([tidb_host, tidb_user, tidb_password]):
        # Check if running on Railway (no SSL certificate file)
        is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
        
        if is_railway:
            # Railway deployment - no SSL certificate file
            connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_disabled=false"
            print(f"✅ Railway mode: Database connection without SSL certificate file")
        else:
            # Local development - try to use SSL certificate
            ssl_ca_path = "./certs/isrgrootx1.pem"
            if os.path.exists(ssl_ca_path):
                connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_ca={ssl_ca_path}"
                print(f"✅ Local mode: Using SSL certificate: {ssl_ca_path}")
            else:
                connection_string = f"mysql+pymysql://{tidb_user}:{tidb_password}@{tidb_host}:{tidb_port}/{DB_NAME}?ssl_disabled=false"
                print(f"✅ Local mode: SSL certificate not found, using connection without SSL file")
    else:
        print("❌ Database configuration incomplete!")
        connection_string = None

# Create database engine
try:
    if connection_string:
        engine = create_engine(
            connection_string,
            pool_size=1,          # Reduce pool size to save memory
            max_overflow=2,       # Limit overflow connections
            pool_timeout=30,
            pool_recycle=1800,    # Recycle connections more frequently
            pool_pre_ping=True,   # Helps with connection issues
            echo=False           # Disable SQL logging to save memory
        )
        print("✅ Database engine created successfully (memory-optimized)")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            print("✅ Database connection test successful")
    else:
        engine = None
        print("❌ No database engine created")
        
except Exception as e:
    print(f"❌ Database setup error: {e}")
    engine = None

print("=== END DATABASE CONFIGURATION ===")

# --- OPTIMIZED MEMORY-EFFICIENT MODEL LOADING ---
print("Initializing application...")

# Don't load the model during startup - load it when needed
sentence_model = None

def get_sentence_model():
    """Lazy load the sentence transformer model with memory optimization"""
    global sentence_model
    if sentence_model is None:
        print("Loading lightweight embedding model...")
        try:
            # Use the smallest possible model to reduce memory usage
            import torch
            # Force CPU usage to reduce memory footprint
            sentence_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            # Set to eval mode to reduce memory usage
            sentence_model.eval()
            print("✅ Lightweight embedding model loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to load lightweight model: {e}")
            # Fallback to even smaller model
            try:
                print("🔄 Trying ultra-compact model...")
                sentence_model = SentenceTransformer('paraphrase-MiniLM-L3-v2', device='cpu')
                sentence_model.eval()
                print("✅ Ultra-compact model loaded successfully!")
            except Exception as e2:
                print(f"❌ Failed to load ultra-compact model: {e2}")
                raise Exception("Cannot load any embedding model. Please check your internet connection.")
    
    return sentence_model

def cleanup_model():
    """Force cleanup of model to free memory"""
    global sentence_model
    if sentence_model is not None:
        try:
            import torch
            if hasattr(sentence_model, '_modules'):
                # Clear model from memory
                sentence_model = None
                # Force garbage collection
                import gc
                gc.collect()
                # Clear PyTorch cache if available
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                print("🧹 Model memory cleaned up")
        except Exception as e:
            print(f"⚠️ Model cleanup warning: {e}")
            sentence_model = None

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
async def health_check():
    """Railway-compatible health check"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "environment": "railway"
        }
        
        # Test database connection
        try:
            if engine:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                health_status["database"] = "connected"
            else:
                health_status["database"] = "not_configured"
        except Exception as db_error:
            health_status["database"] = f"error: {str(db_error)[:100]}"
        
        # Test Gemini API
        google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        health_status["gemini"] = "configured" if google_api_key else "not_configured"
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/query-agent/", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    """Query the knowledge base using vector similarity search and generate answer with Gemini"""
    
    try:
        print(f"DEBUG: Processing question: {request.question}")  # Added debug logging
        
        # 1. Create embedding for the incoming question
        query_embedding = get_sentence_model().encode(request.question).tolist()
        print(f"DEBUG: Generated embedding with {len(query_embedding)} dimensions")  # Added debug logging
        
        # 🔧 DIMENSION COMPATIBILITY FIX
        if len(query_embedding) == 384:
            query_embedding.extend([0.0] * (768 - 384))
            print(f"DEBUG: Padded embedding to {len(query_embedding)} dimensions")
        
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
        
        # 🔧 DIMENSION COMPATIBILITY FIX
        if len(query_embedding) == 384:
            query_embedding.extend([0.0] * (768 - 384))
            print(f"DEBUG: Padded alert embedding to {len(query_embedding)} dimensions")
        
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
    """Get statistics about the knowledge base and system status"""
    try:
        with engine.connect() as connection:
            # Get total count
            result = connection.execute(text("SELECT COUNT(*) as total FROM knowledgebase"))
            total_chunks = result.fetchone()[0]
            
            # Get unique sources
            result = connection.execute(text("SELECT COUNT(DISTINCT source_file) as sources FROM knowledgebase"))
            unique_sources = result.fetchone()[0]
            
            # Get memory usage
            memory_info = "N/A"
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_info = f"{memory_mb:.1f} MB"
            except ImportError:
                memory_info = "psutil not available"
            except Exception as e:
                memory_info = f"Error: {e}"
            
            return {
                "total_chunks": total_chunks,
                "unique_sources": unique_sources,
                "embedding_model": "all-MiniLM-L6-v2 (memory-optimized, padded to 768)",
                "vector_dimensions": "384→768 (compatibility mode)",  # Updated for clarity
                "llm_model": "gemini-2.5-flash",
                "memory_usage": memory_info,
                "model_loaded": sentence_model is not None
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
    print(f"DEBUG: Generated grafana embedding with {len(query_embedding)} dimensions")
    
    # 🔧 DIMENSION COMPATIBILITY FIX
    if len(query_embedding) == 384:
        query_embedding.extend([0.0] * (768 - 384))
        print(f"DEBUG: Padded grafana embedding to {len(query_embedding)} dimensions")

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
        
        # 🔧 DIMENSION COMPATIBILITY FIX
        # Pad 384-dim vectors to 768-dim to match existing database vectors
        if len(query_embedding) == 384:
            # Pad with zeros to match 768 dimensions
            query_embedding.extend([0.0] * (768 - 384))
            print(f"DEBUG: Padded embedding to {len(query_embedding)} dimensions for database compatibility")
        
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
                    result = {"status": "Alert processed and sent to Slack.", "success": True}
                except:
                    result = {"status": "Alert processed but failed to send to Slack.", "success": False}
            else:
                result = {"status": "Alert processed but Slack not configured.", "success": False}
        else:
            # Return to UI for questions
            result = {
                "question": question,
                "answer": llm_answer,
                "source_context": f"Source: {source_file}\n\nContext: {retrieved_chunk}",
                "success": True
            }
        
        # � AUTONOMOUS LEARNING: Store alert for pattern analysis
        if is_alert:
            # Store alert in agent memory for learning
            alert_info = {
                "type": alert_name,
                "service": service_name,
                "timestamp": datetime.now().isoformat(),
                "severity": "medium",  # Could be extracted from Grafana
                "resolved": True if "success" in result else False,
                "solution_found": len(rows) > 0,
                "response_quality": "high" if llm_answer and len(llm_answer) > 100 else "low"
            }
            agent_state.alert_history.append(alert_info)
            
            # Keep only last 50 alerts for pattern analysis
            if len(agent_state.alert_history) > 50:
                agent_state.alert_history = agent_state.alert_history[-50:]
            
            # Trigger autonomous learning action
            autonomous_action("grafana_alert_processed", {
                "alert_name": alert_name,
                "service": service_name,
                "system": "grafana_monitoring",
                "severity": "info",
                "solution_provided": len(llm_answer) > 0,
                "knowledge_base_hit": len(rows) > 0,
                "timestamp": time.time()
            })
            
            print(f"🧠 Agent learned from alert: {alert_name} for {service_name}")
        
        # �🧹 MEMORY CLEANUP: Force cleanup after processing to prevent OOM
        try:
            import gc
            gc.collect()  # Force garbage collection
            print("🧹 Memory cleanup completed")
        except Exception as cleanup_error:
            print(f"⚠️ Memory cleanup warning: {cleanup_error}")
        
        return result
            
    except Exception as e:
        print(f"DEBUG: Processing error: {e}")
        # Cleanup on error too
        try:
            import gc
            gc.collect()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

def create_tidb_engine_with_ca(connection_string):
    """Create TiDB engine with proper CA certificate verification"""
    
    try:
        if "tidbcloud.com" in connection_string:
            print("🔍 Setting up TiDB Cloud SSL with system CA bundle...")
            
            # Get system CA bundle path
            ca_bundle_path = certifi.where()
            print(f"   Using CA bundle: {ca_bundle_path}")
            
            # Modify connection string to use system CA bundle
            if "ssl_ca=" in connection_string:
                # Replace existing ssl_ca parameter
                import re
                connection_string = re.sub(r'ssl_ca=[^&]*', f'ssl_ca={ca_bundle_path}', connection_string)
            else:
                # Add CA parameter
                separator = "&" if "?" in connection_string else "?"
                connection_string += f"{separator}ssl_ca={ca_bundle_path}&ssl_verify_cert=true&ssl_verify_identity=false"
            
            print(f"✅ Updated connection string with system CA bundle")
        
        # Create engine with SSL context
        engine = create_engine(
            connection_string,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            connect_args={
                "ssl_verify_cert": True,
                "ssl_verify_identity": False,
                "connect_timeout": 20
            }
        )
        
        print("✅ TiDB Cloud engine created with CA verification")
        return engine
        
    except Exception as e:
        print(f"❌ Engine creation failed: {e}")
        return None

# Replace your database configuration section with this:

print("=== DATABASE CONFIGURATION ===")

def create_safe_database_engine():
    """Create database engine with safe URL handling"""
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ No DATABASE_URL found")
        return None
    
    # Fix Railway environment variable issue - remove PREFIX if present
    if database_url.startswith("DATABASE_URL="):
        database_url = database_url.replace("DATABASE_URL=", "", 1)
        print("🔧 Fixed Railway environment variable prefix issue")
    
    # Clean any whitespace
    database_url = database_url.strip()
    
    try:
        # Ensure SSL for TiDB Cloud
        if "tidbcloud.com" in database_url and "ssl_verify_cert=false" in database_url:
            # Replace with secure SSL settings
            database_url = database_url.replace("ssl_verify_cert=false&ssl_verify_identity=false", "ssl_verify_cert=true&ssl_verify_identity=false")
            print("🔒 Updated to secure SSL connection for TiDB Cloud")
        elif "tidbcloud.com" in database_url and "ssl" not in database_url:
            # Add SSL parameters if missing
            separator = "&" if "?" in database_url else "?"
            database_url += f"{separator}ssl_verify_cert=true&ssl_verify_identity=false"
            print("🔒 Added SSL parameters for TiDB Cloud")
        
        print(f"✅ Using DATABASE_URL from environment")
        print(f"   URL (first 50 chars): {database_url[:50]}...")
        
        # Create engine without modifying the URL
        from sqlalchemy import create_engine
        
        engine = create_engine(
            database_url,  # Use cleaned URL
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True,
            echo=False  # Set to True for SQL debugging
        )
        
        print("✅ Database engine created successfully")
        return engine
        
    except Exception as e:
        print(f"❌ Database engine creation failed: {e}")
        
        # Try with secure fallback
        try:
            print("🔄 Trying secure fallback connection...")
            secure_fallback_url = "mysql+pymysql://MXWJujpTmY2R5cp.root:kJXZQBTtUS5mxeTn@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/devops_sentinel?ssl_verify_cert=true&ssl_verify_identity=false"
            
            fallback_engine = create_engine(secure_fallback_url)
            print("✅ Secure fallback database engine created")
            return fallback_engine
            
        except Exception as fallback_error:
            print(f"❌ Secure fallback also failed: {fallback_error}")
            return None

# Create the engine
engine = create_safe_database_engine()

if engine:
    try:
        # Test connection
        print("🔍 Testing database connection...")
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1 as test"))
            print("✅ Database connection test successful")
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        
print("=== END DATABASE CONFIGURATION ===")

# Add this debug function to see the exact URL being processed:

def debug_database_url():
    """Debug the DATABASE_URL to see what's causing parsing issues"""
    database_url = os.getenv("DATABASE_URL")
    
    print("=== DATABASE_URL DEBUG ===")
    if database_url:
        print(f"Raw DATABASE_URL: {database_url}")
        print(f"URL Length: {len(database_url)}")
        
        # Check for problematic characters
        problematic_chars = ['[', ']', '{', '}', ' ', '\n', '\r']
        for char in problematic_chars:
            if char in database_url:
                print(f"⚠️ Found problematic character: '{char}'")
        
        # Try basic URL parsing
        try:
            from urllib.parse import urlparse
            parsed = urlparse(database_url)
            print(f"✅ URL parsing successful:")
            print(f"   Scheme: {parsed.scheme}")
            print(f"   Username: {parsed.username}")
            print(f"   Hostname: {parsed.hostname}")
            print(f"   Port: {parsed.port}")
            print(f"   Path: {parsed.path}")
            print(f"   Query: {parsed.query}")
        except Exception as e:
            print(f"❌ URL parsing failed: {e}")
    else:
        print("❌ No DATABASE_URL found")
    
    print("=== END DATABASE_URL DEBUG ===")

# Call this before your database configuration
debug_database_url()

# Add these new agent capabilities to your main.py:



# --- AGENT STATE MANAGEMENT ---
class AgentState:
    def __init__(self):
        self.monitoring_active = False
        self.last_health_check = None
        self.alert_history = []
        self.learned_patterns = {}
        self.autonomous_actions_taken = []

agent_state = AgentState()

# --- AUTONOMOUS MONITORING FUNCTIONS ---
@app.post("/agent/start-monitoring/")
async def start_autonomous_monitoring():
    """Start the autonomous monitoring agent"""
    agent_state.monitoring_active = True
    
    # Start background monitoring tasks
    threading.Thread(target=run_monitoring_scheduler, daemon=True).start()
    
    return {
        "status": "Autonomous monitoring started",
        "capabilities": [
            "System health monitoring",
            "Predictive alerting", 
            "Auto-remediation",
            "Pattern learning"
        ],
        "monitoring_active": True
    }

@app.post("/agent/stop-monitoring/")
async def stop_autonomous_monitoring():
    """Stop the autonomous monitoring agent"""
    agent_state.monitoring_active = False
    return {"status": "Autonomous monitoring stopped", "monitoring_active": False}

def run_monitoring_scheduler():
    """Background scheduler for autonomous monitoring"""
    schedule.every(30).seconds.do(autonomous_health_check)
    schedule.every(5).minutes.do(predictive_analysis)
    schedule.every(15).minutes.do(pattern_learning)
    
    while agent_state.monitoring_active:
        schedule.run_pending()
        time.sleep(10)

def autonomous_health_check():
    """Agent monitors external DevOps systems for issues"""
    print("🤖 Agent: Monitoring external DevOps systems...")
    
    try:
        # 1. Check database connectivity (external system)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM knowledgebase"))
            kb_count = result.fetchone()[0]
        
        # 2. Monitor knowledge base integrity
        if kb_count == 0:
            autonomous_action("knowledge_base_empty", {
                "kb_count": kb_count,
                "severity": "critical",
                "system": "knowledge_base",
                "action": "alert_admin",
                "timestamp": time.time()
            })
        
        # 3. Check for recent alert patterns (DevOps monitoring)
        recent_alerts = agent_state.alert_history[-5:] if len(agent_state.alert_history) >= 5 else []
        if len(recent_alerts) >= 3:
            # Check if too many alerts in short time (system instability)
            recent_times = [alert.get("timestamp") for alert in recent_alerts]
            if recent_times:
                time_span = (datetime.fromisoformat(recent_times[-1]) - datetime.fromisoformat(recent_times[0])).total_seconds()
                if time_span < 300:  # 5 minutes
                    autonomous_action("alert_storm_detected", {
                        "alert_count": len(recent_alerts),
                        "time_span_minutes": time_span / 60,
                        "severity": "warning",
                        "system": "monitoring",
                        "action": "analyze_patterns",
                        "timestamp": time.time()
                    })
        
        # 4. Check system availability (simulate external monitoring)
        try:
            # This simulates checking external systems
            health_response = requests.get(f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/health", timeout=5)
            if health_response.status_code != 200:
                autonomous_action("api_health_degraded", {
                    "status_code": health_response.status_code,
                    "severity": "warning",
                    "system": "api_gateway",
                    "action": "monitor_closely",
                    "timestamp": time.time()
                })
        except Exception as health_error:
            autonomous_action("external_system_unreachable", {
                "error": str(health_error),
                "severity": "critical",
                "system": "external_api",
                "action": "escalate",
                "timestamp": time.time()
            })
        
        agent_state.last_health_check = datetime.now()
        print("✅ Agent: DevOps systems monitoring completed")
        
    except Exception as e:
        print(f"❌ Agent: DevOps monitoring failed: {e}")
        autonomous_action("monitoring_system_failed", {
            "error": str(e),
            "severity": "critical",
            "system": "agent_monitoring",
            "action": "restart_monitoring",
            "timestamp": time.time()
        })

def autonomous_action(issue_type: str, context: dict):
    """Agent takes autonomous actions based on DevOps monitoring"""
    print(f"🚨 Agent: Taking autonomous action for {issue_type}")
    
    action_taken = {
        "issue_type": issue_type,
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "action_id": f"agent_{int(time.time())}",
        "system": context.get("system", "unknown"),
        "severity": context.get("severity", "medium")
    }
    
    try:
        if issue_type == "knowledge_base_empty":
            # Critical DevOps issue: Knowledge base unavailable
            send_agent_notification("🚨 CRITICAL: Knowledge base is empty - DevOps solutions unavailable!")
            action_taken["result"] = "Success: Critical alert sent to operations team"
            
        elif issue_type == "alert_storm_detected":
            # DevOps pattern: Too many alerts indicate system instability
            alert_count = context.get("alert_count", 0)
            time_span = context.get("time_span_minutes", 0)
            send_agent_notification(f"⚠️ ALERT STORM: {alert_count} alerts in {time_span:.1f} minutes - System instability detected!")
            action_taken["result"] = f"Success: Alert storm notification sent ({alert_count} alerts)"
            
        elif issue_type == "api_health_degraded":
            # DevOps monitoring: API health issues
            status_code = context.get("status_code", "unknown")
            send_agent_notification(f"🔧 API HEALTH: Service returning {status_code} - Monitoring closely")
            action_taken["result"] = f"Success: API health alert sent (status: {status_code})"
            
        elif issue_type == "external_system_unreachable":
            # Critical DevOps issue: External system down
            error = context.get("error", "unknown")
            send_agent_notification(f"🆘 SYSTEM DOWN: External system unreachable - {error}")
            action_taken["result"] = "Success: System outage escalated to operations"
            
        elif issue_type == "monitoring_system_failed":
            # Meta-monitoring: The monitoring itself failed
            send_agent_notification("🔴 MONITORING FAILURE: DevOps agent monitoring system failed - Manual intervention required")
            action_taken["result"] = "Success: Monitoring failure escalated"
            
        elif issue_type == "grafana_alert_processed":
            # Autonomous learning from Grafana alerts
            alert_name = context.get("alert_name", "unknown")
            service = context.get("service", "unknown")
            solution_provided = context.get("solution_provided", False)
            
            if solution_provided:
                action_taken["result"] = f"Success: Learned from {alert_name} alert for {service}"
                print(f"🧠 Agent: Successfully processed and learned from {alert_name}")
            else:
                action_taken["result"] = f"Learning: No solution found for {alert_name} - flagged for knowledge base improvement"
                send_agent_notification(f"📚 KNOWLEDGE GAP: No solution found for '{alert_name}' on {service} - Consider updating knowledge base")
            
        else:
            # Handle Grafana alerts and other DevOps events
            send_agent_notification(f"🤖 DevOps Agent: Handled {issue_type} - Context: {context}")
            action_taken["result"] = f"Success: Processed {issue_type}"
            
    except Exception as e:
        action_taken["result"] = f"Failed: {str(e)}"
        print(f"❌ Agent action failed: {e}")
    
    # Store action in agent memory
    agent_state.autonomous_actions_taken.append(action_taken)
    
    # Keep only last 100 actions
    if len(agent_state.autonomous_actions_taken) > 100:
        agent_state.autonomous_actions_taken = agent_state.autonomous_actions_taken[-100:]
    if len(agent_state.autonomous_actions_taken) > 100:
        agent_state.autonomous_actions_taken = agent_state.autonomous_actions_taken[-100:]

def predictive_analysis():
    """Agent performs predictive analysis on patterns"""
    print("🔮 Agent: Performing predictive analysis...")
    
    try:
        # Analyze recent alert patterns
        recent_alerts = agent_state.alert_history[-10:]  # Last 10 alerts
        
        if len(recent_alerts) >= 3:
            # Look for patterns
            alert_types = [alert.get("type", "unknown") for alert in recent_alerts]
            most_common = max(set(alert_types), key=alert_types.count)
            
            if alert_types.count(most_common) >= 3:
                # Pattern detected - proactive action
                prediction = {
                    "pattern": f"Recurring {most_common} alerts",
                    "confidence": alert_types.count(most_common) / len(alert_types),
                    "recommendation": f"Investigate root cause of {most_common}",
                    "timestamp": datetime.now().isoformat()
                }
                
                send_agent_notification(f"🔮 Agent Prediction: Pattern detected - {prediction['pattern']} (confidence: {prediction['confidence']:.1%})")
                
                print(f"🎯 Agent: Detected pattern - {prediction['pattern']}")
    
    except Exception as e:
        print(f"❌ Agent: Predictive analysis failed: {e}")

def pattern_learning():
    """Agent learns from historical data to improve responses"""
    print("🧠 Agent: Learning from patterns...")
    
    try:
        # Analyze successful resolutions
        successful_actions = [action for action in agent_state.autonomous_actions_taken 
                            if action.get("result", "").startswith("Success")]
        
        # Update learned patterns
        for action in successful_actions[-5:]:  # Learn from last 5 successful actions
            issue_type = action["issue_type"]
            if issue_type not in agent_state.learned_patterns:
                agent_state.learned_patterns[issue_type] = {
                    "success_count": 0,
                    "total_attempts": 0,
                    "best_action": None
                }
            
            agent_state.learned_patterns[issue_type]["success_count"] += 1
            agent_state.learned_patterns[issue_type]["total_attempts"] += 1
            agent_state.learned_patterns[issue_type]["best_action"] = action.get("result")
        
        print(f"🧠 Agent: Learned from {len(successful_actions)} successful actions")
    
    except Exception as e:
        print(f"❌ Agent: Pattern learning failed: {e}")

def send_agent_notification(message: str):
    """Send autonomous agent notifications to Slack"""
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook_url:
        try:
            payload = {
                "text": f"🤖 **DevOps Sentinel Agent**\n{message}\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
            requests.post(slack_webhook_url, json=payload, timeout=10)
            print(f"📤 Agent: Notification sent to Slack")
        except Exception as e:
            print(f"❌ Agent: Failed to send notification: {e}")

# --- ENHANCED ALERT PROCESSING WITH AGENT CAPABILITIES ---
@app.post("/agent/process-alert/")
async def agent_process_alert(request_data: dict):
    """Enhanced alert processing with autonomous agent capabilities"""
    
    # Store alert in agent memory
    alert_info = {
        "type": request_data.get("alertname", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "severity": request_data.get("severity", "medium"),
        "service": request_data.get("service", "unknown")
    }
    agent_state.alert_history.append(alert_info)
    
    # Keep only last 50 alerts
    if len(agent_state.alert_history) > 50:
        agent_state.alert_history = agent_state.alert_history[-50:]
    
    # Check if agent has learned how to handle this alert type
    alert_type = alert_info["type"]
    if alert_type in agent_state.learned_patterns:
        pattern = agent_state.learned_patterns[alert_type]
        success_rate = pattern["success_count"] / pattern["total_attempts"]
        
        if success_rate > 0.7:  # High confidence
            print(f"🤖 Agent: Using learned pattern for {alert_type} (success rate: {success_rate:.1%})")
            
            # Apply learned solution
            auto_response = f"🤖 **Agent Auto-Response** (Confidence: {success_rate:.1%})\n\n"
            auto_response += f"Based on previous successful resolutions:\n{pattern['best_action']}\n\n"
            auto_response += "**Recommended Action:** " + pattern.get('best_action', 'Apply standard procedure')
            
            send_agent_notification(f"🎯 Agent: Applied learned solution for {alert_type}")
            
            return {
                "agent_response": auto_response,
                "confidence": success_rate,
                "source": "learned_pattern",
                "success": True
            }
    
    # If no learned pattern, use normal RAG processing
    # ... (your existing process-input logic here) ...
    
    print(f"🔍 Agent: Processing new alert type: {alert_type}")
    # Continue with normal processing...

# --- AGENT STATUS AND CONTROL ENDPOINTS ---
@app.get("/agent/status")
def get_agent_status():
    """Get current agent status and capabilities"""
    return {
        "monitoring_active": agent_state.monitoring_active,
        "last_health_check": agent_state.last_health_check.isoformat() if agent_state.last_health_check else None,
        "total_autonomous_actions": len(agent_state.autonomous_actions_taken),
        "learned_patterns_count": len(agent_state.learned_patterns),
        "recent_alerts_count": len(agent_state.alert_history),
        "capabilities": {
            "autonomous_monitoring": True,
            "predictive_analysis": True,
            "pattern_learning": True,
            "auto_remediation": True,
            "proactive_notifications": True
        },
        "agent_memory": {
            "successful_actions": len([a for a in agent_state.autonomous_actions_taken if "Success" in a.get("result", "")]),
            "patterns_learned": list(agent_state.learned_patterns.keys()),
            "uptime": "Active" if agent_state.monitoring_active else "Stopped"
        }
    }

@app.get("/agent/actions")
def get_agent_actions():
    """Get recent autonomous actions taken by the agent"""
    return {
        "recent_actions": agent_state.autonomous_actions_taken[-10:],  # Last 10 actions
        "total_actions": len(agent_state.autonomous_actions_taken),
        "learned_patterns": agent_state.learned_patterns
    }