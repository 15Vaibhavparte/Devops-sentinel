# railway_start.py - Python startup script for Railway
import os
import subprocess
import sys

def start_server():
    """Start the uvicorn server with proper port handling"""
    
    # Get port from environment
    port = os.environ.get('PORT', '8000')
    
    print("=== DevOps Sentinel Railway Startup ===")
    print(f"PORT environment variable: {port}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Validate port
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError(f"Invalid port number: {port_int}")
    except ValueError as e:
        print(f"ERROR: Invalid port value '{port}': {e}")
        print("Using default port 8000")
        port = "8000"
    
    print(f"Starting uvicorn server on port {port}")
    
    # Start uvicorn
    cmd = [
        'uvicorn', 
        'main:app', 
        '--host', '0.0.0.0', 
        '--port', port,
        '--workers', '1'
    ]
    
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Server failed to start: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Server stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    start_server()