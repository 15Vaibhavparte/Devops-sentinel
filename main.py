# main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer
import google.generativeai as genai  # <-- Import Google's library
import time
import random

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

# Load the embedding model (use same as ingest.py for consistency)
print("Loading embedding model...")
sentence_model = SentenceTransformer('all-mpnet-base-v2')  # 768 dimensions to match database

# Initialize the Gemini model (for generation)
print("Initializing Gemini model...")
generation_model = genai.GenerativeModel('gemini-1.5-flash')  # Much higher free tier limits

print("--- Server is ready and models are loaded ---")


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

# --- API ENDPOINTS ---
@app.get("/")
def root():
    return {"message": "DevOps Sentinel Query Agent with Gemini AI is running!"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        
        # Test Gemini API
        test_response = generation_model.generate_content("Hello")
        
        return {
            "status": "healthy", 
            "database": "connected",
            "gemini": "available"
        }
    except Exception as e:
        print(f"DEBUG: Health check failed: {e}")  # Added debug logging
        return {"status": "unhealthy", "error": str(e)}

@app.post("/query-agent/", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    """Query the knowledge base using vector similarity search and generate answer with Gemini"""
    
    try:
        print(f"DEBUG: Processing question: {request.question}")  # Added debug logging
        
        # 1. Create embedding for the incoming question
        query_embedding = sentence_model.encode(request.question).tolist()
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
                "llm_model": "gemini-1.5-flash"
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