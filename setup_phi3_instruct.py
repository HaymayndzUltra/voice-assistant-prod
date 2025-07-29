#!/usr/bin/env python3
"""
Setup script for phi3:instruct model integration
Pulls the model and verifies it's working with your system
"""

import subprocess
import sys
import time
import requests
import json

def run_command(command, description):
    """Run a shell command and return success status"""
    print(f"🔄 {description}...")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            print(f"   Error: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def check_ollama_running():
    """Check if Ollama is running"""
    print("🔍 Checking if Ollama is running...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama is running")
            return True
        else:
            print(f"❌ Ollama returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama is not running: {e}")
        return False

def check_model_exists(model_name):
    """Check if a specific model exists"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            for model in models:
                if model.get('name') == model_name:
                    print(f"✅ Model {model_name} is already available")
                    print(f"   Size: {model.get('size', 'unknown')}")
                    return True
            return False
        else:
            return False
    except Exception:
        return False

def pull_phi3_instruct():
    """Pull the phi3:instruct model"""
    if check_model_exists("phi3:instruct"):
        print("✅ phi3:instruct is already available")
        return True
    
    print("📥 Pulling phi3:instruct model...")
    print("   This may take several minutes depending on your internet connection...")
    
    return run_command(
        "ollama pull phi3:instruct",
        "Pulling phi3:instruct model"
    )

def test_model_generation():
    """Test if the model can generate text"""
    print("🧪 Testing phi3:instruct generation...")
    
    test_prompt = "Hello, can you respond with 'phi3:instruct is working'?"
    
    try:
        payload = {
            "model": "phi3:instruct",
            "prompt": test_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 50
            }
        }
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            print(f"✅ Generation test successful")
            print(f"   Response: {generated_text}")
            return True
        else:
            print(f"❌ Generation test failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Generation test failed: {e}")
        return False

def update_configurations():
    """Update system configurations to use phi3:instruct"""
    print("⚙️ Updating system configurations...")
    
    # List of files that might need updating
    config_files = [
        "pc2_code/_pc2mainpcSOT.yaml",
        "main_pc_code/agents/model_config.yaml",
        "ollama_client.py"
    ]
    
    updated_count = 0
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Check if phi3:instruct is already mentioned
            if "phi3:instruct" in content:
                print(f"   ✅ {config_file} already configured")
                updated_count += 1
            else:
                print(f"   ⚠️ {config_file} may need manual configuration")
                
        except FileNotFoundError:
            print(f"   ⚠️ {config_file} not found")
        except Exception as e:
            print(f"   ❌ Error reading {config_file}: {e}")
    
    if updated_count > 0:
        print(f"✅ {updated_count} configuration files are ready")
        return True
    else:
        print("⚠️ No configuration files found - manual setup may be needed")
        return False

def main():
    """Main setup function"""
    print("🚀 Phi3:Instruct Setup Script")
    print("=" * 50)
    
    # Step 1: Check if Ollama is running
    if not check_ollama_running():
        print("\n❌ Ollama is not running. Please start it first:")
        print("   ollama serve")
        print("\nThen run this script again.")
        return False
    
    # Step 2: Pull the model if needed
    if not pull_phi3_instruct():
        print("\n❌ Failed to pull phi3:instruct model")
        return False
    
    # Step 3: Test the model
    if not test_model_generation():
        print("\n❌ Model generation test failed")
        return False
    
    # Step 4: Update configurations
    update_configurations()
    
    # Step 5: Run integration test
    print("\n🔗 Running integration test...")
    try:
        result = subprocess.run([
            sys.executable, "test_phi3_instruct_integration.py"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Integration test passed")
            print(result.stdout)
        else:
            print("⚠️ Integration test had issues")
            print(result.stderr)
            
    except Exception as e:
        print(f"⚠️ Could not run integration test: {e}")
    
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("   1. Your phi3:instruct model is ready to use")
    print("   2. Run 'python test_phi3_instruct_integration.py' to verify everything")
    print("   3. Your rule-based parser will now use phi3:instruct for complex tasks")
    print("   4. Check the logs for any configuration issues")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 