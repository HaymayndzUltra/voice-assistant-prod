import requests
import json
import sys
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url

def test_ollama(model_name="phi"):
    """
    Test if Ollama is running and if a model is available
    """
    print(f"\n=== Ollama API Test for {model_name} ===\n")
    
    # Test 1: Check if Ollama server is running
    try:
        print("1. Testing Ollama server connection...")
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print(f"   [SUCCESS]: Ollama server is running (status code {response.status_code})")
            models = response.json().get("models", [])
            print(f"   Found {len(models)} models: {', '.join([m.get('name', 'unknown') for m in models])}")
        else:
            print(f"   [ERROR]: Ollama returned unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   [ERROR]: Could not connect to Ollama server. Is it running?")
        print("   Run 'ollama serve' in a separate terminal.")
        return False
    except Exception as e:
        print(f"   [ERROR]: {str(e)}")
        return False
        
    # Test 2: Check if model exists
    try:
        print(f"\n2. Checking if model '{model_name}' exists...")
        model_exists = False
        for model in models:
            if model_name in model.get('name', ''):
                model_exists = True
                print(f"   [SUCCESS]: Model '{model_name}' is available!")
                print(f"   Full model name: {model.get('name')}")
                break
                
        if not model_exists:
            print(f"   [ERROR]: Model '{model_name}' not found in available models.")
            print(f"   You may need to run: ollama pull {model_name}")
            return False
    except Exception as e:
        print(f"   [ERROR] checking model: {str(e)}")
        return False
        
    # Test 3: Try a simple inference with the model
    try:
        print(f"\n3. Testing basic inference with '{model_name}'...")
        print("   Using a simpler prompt with shorter timeout to avoid lockups...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": "Say hello",
                "stream": False,
                "max_tokens": 10
            },
            timeout=15
        )
        
        if response.status_code == 200:
            output = response.json().get("response", "")
            print(f"   [SUCCESS]: Model returned a response")
            print(f"   Response: {output[:100]}..." if len(output) > 100 else f"   Response: {output}")
            return True
        else:
            print(f"   [ERROR]: Model inference failed with status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   [ERROR] during model inference: {str(e)}")
        return False

if __name__ == "__main__":
    model = "phi" if len(sys.argv) < 2 else sys.argv[1]
    success = test_ollama(model)
    
    if success:
        print("\n[SUCCESS] ALL TESTS PASSED: Ollama is working correctly with the model!")
    else:
        print("\n[FAILED] TESTS FAILED: Please fix the issues above before continuing.")
    
    print("\nPress Enter to exit...")
    input()
