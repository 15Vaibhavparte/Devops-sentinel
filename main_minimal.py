# main_minimal.py - Minimal version for debugging Railway deployment

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app
app = FastAPI(title="DevOps Sentinel", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "DevOps Sentinel API", "status": "online", "version": "minimal"}

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    
    # Check environment variables
    google_api_key = os.getenv("GOOGLE_API_KEY")
    database_url = os.getenv("DATABASE_URL")
    
    return {
        "status": "healthy",
        "service": "DevOps Sentinel",
        "version": "minimal",
        "environment": {
            "google_api_key": "✅ Present" if google_api_key else "❌ Missing",
            "database_url": "✅ Present" if database_url else "❌ Missing",
            "port": os.getenv("PORT", "8000"),
        }
    }

@app.get("/debug")
async def debug_info():
    """Debug endpoint to check environment"""
    
    env_vars = {}
    for key in sorted(os.environ.keys()):
        if any(term in key.upper() for term in ['API', 'KEY', 'GOOGLE', 'GEMINI', 'DATABASE', 'PORT']):
            value = os.environ[key]
            # Mask sensitive values
            if 'API' in key.upper() or 'KEY' in key.upper():
                masked = f"{value[:5]}...{value[-4:]}" if len(value) > 10 else "***"
                env_vars[key] = masked
            else:
                env_vars[key] = value
    
    return {
        "environment_variables": env_vars,
        "python_version": os.sys.version,
        "cwd": os.getcwd()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
