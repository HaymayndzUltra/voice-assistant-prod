import requests
import time
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url

print("=== Simple Ollama Connection Test ===")
print("Testing with higher timeout (30 seconds)...")

try:
    start_time = time.time()
    print("Connecting to Ollama...")
    response = requests.get("http://localhost:11434/api/tags", timeout=30)
    elapsed = time.time() - start_time
    
    print(f"Response time: {elapsed:.2f} seconds")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("SUCCESS: Ollama is running!")
        print(f"Available models: {response.json()}")
    else:
        print(f"ERROR: Unexpected status code {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"ERROR: {str(e)}")
    
print("\nPress Enter to exit...")
input()
