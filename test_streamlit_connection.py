# test_streamlit_connection.py
# Quick test script to verify Streamlit can connect to Railway backend

import requests
import os

# Use the same configuration as ui.py
API_BASE_URL = os.getenv("API_BASE_URL", "https://devops-sentinel-production.up.railway.app")
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

print(f"Testing connection to: {API_BASE_URL}")
print(f"Health endpoint: {HEALTH_ENDPOINT}")

try:
    response = requests.get(HEALTH_ENDPOINT, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✅ Backend connection successful!")
    else:
        print("❌ Backend connection failed!")
        
except Exception as e:
    print(f"❌ Connection error: {e}")
