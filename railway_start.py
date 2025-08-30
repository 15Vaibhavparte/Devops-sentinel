# railway_start.py - Railway startup script with debugging
import os
import subprocess
import sys

def check_environment():
    """Check critical environment variables"""
    print("=== RAILWAY ENVIRONMENT CHECK ===")
    
    # Check critical variables
    google_api_key = os.getenv("GOOGLE_API_KEY")
    database_url = os.getenv("DATABASE_URL")
    port = os.getenv("PORT", "8000")
    
    print(f"PORT: {port}")
    print(f"GOOGLE_API_KEY: {'✅ Present' if google_api_key else '❌ Missing'}")
    print(f"DATABASE_URL: {'✅ Present' if database_url else '❌ Missing'}")
    
    # Check Railway-specific variables
    railway_env = os.getenv("RAILWAY_ENVIRONMENT")
    railway_project = os.getenv("RAILWAY_PROJECT_NAME")
    
    print(f"RAILWAY_ENVIRONMENT: {railway_env}")
    print(f"RAILWAY_PROJECT_NAME: {railway_project}")
    
    if not google_api_key:
        print("❌ GOOGLE_API_KEY is required!")
        return False
        
    if not database_url:
        print("❌ DATABASE_URL is required!")
        return False
    
    print("✅ All critical environment variables present")
    return True

def main():
    print("=== STARTING DEVOPS SENTINEL ON RAILWAY ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Check environment first
    if not check_environment():
        print("❌ Environment check failed - exiting")
        sys.exit(1)
    
    # Railway sets PORT automatically, but let's be explicit
    port = os.environ.get('PORT', '8080')  # Default to 8080 for Railway
    print(f"🚀 Starting DevOps Sentinel on port {port}")
    print(f"Environment PORT: {os.environ.get('PORT', 'Not set')}")
    
    try:
        # Use main.py with explicit port
        cmd = ['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', str(port), '--log-level', 'info']
        print(f"Command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()