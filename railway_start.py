# railway_start.py - Reliable Railway startup
import os
import subprocess
import sys
import time

def main():
    print("=== Railway DevOps Sentinel Startup ===")
    
    # Get port from Railway
    port = os.environ.get('PORT', '8000')
    print(f"Starting on port: {port}")
    
    # Environment debug
    print(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT')}")
    print(f"DATABASE_URL configured: {'Yes' if os.getenv('DATABASE_URL') else 'No'}")
    print(f"GOOGLE_API_KEY configured: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")
    
    # Start uvicorn
    cmd = [
        'uvicorn', 
        'main:app', 
        '--host', '0.0.0.0', 
        '--port', port,
        '--workers', '1',
        '--log-level', 'info'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()