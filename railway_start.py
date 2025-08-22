# railway_start.py - Railway startup script
import os
import subprocess

def main():
    port = os.environ.get('PORT', '8000')
    print(f"Starting DevOps Sentinel on port {port}")
    
    cmd = ['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', port]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()