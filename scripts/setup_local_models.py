#!/usr/bin/env python3
"""
Local Model Setup Script
Para sa LLM local-first configuration
"""

import os
import sys
import subprocess
from pathlib import Path

def check_ollama_installed():
    """Check if Ollama is installed"""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def install_ollama():
    """Install Ollama"""
    print("🚀 Installing Ollama...")
    try:
        subprocess.run(['curl', '-fsSL', 'https://ollama.ai/install.sh'], capture_output=True, check=True)
        result = subprocess.run(['bash'], input='curl -fsSL https://ollama.ai/install.sh | sh', 
                              text=True, capture_output=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Failed to install Ollama: {e}")
        return False

def list_available_models():
    """List recommended models for your setup"""
    print("\n🤖 RECOMMENDED LOCAL MODELS:")
    print("=" * 50)
    
    models = [
        {
            'name': 'llama2:7b-chat',
            'size': '3.8GB',
            'description': 'Fast, good for general tasks',
            'recommended': True
        },
        {
            'name': 'llama2:13b-chat', 
            'size': '7.3GB',
            'description': 'Better quality, slower',
            'recommended': True
        },
        {
            'name': 'codellama:7b-instruct',
            'size': '3.8GB', 
            'description': 'Specialized for coding',
            'recommended': False
        },
        {
            'name': 'mistral:7b-instruct',
            'size': '4.1GB',
            'description': 'Alternative to Llama2',
            'recommended': False
        }
    ]
    
    for i, model in enumerate(models, 1):
        status = "⭐ RECOMMENDED" if model['recommended'] else "  Optional"
        print(f"{i}. {model['name']} ({model['size']}) {status}")
        print(f"   {model['description']}")
        print()

def download_model(model_name):
    """Download a model via Ollama"""
    print(f"📥 Downloading {model_name}...")
    print("This may take several minutes depending on model size...")
    
    try:
        result = subprocess.run(['ollama', 'pull', model_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Successfully downloaded {model_name}")
            return True
        else:
            print(f"❌ Failed to download {model_name}")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False

def update_env_file(model_path):
    """Update .env file with model path"""
    env_path = Path('/home/haymayndz/AI_System_Monorepo/.env')
    
    if not env_path.exists():
        print("❌ .env file not found")
        return False
        
    # Read current content
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update LLM_LOCAL_MODEL_PATH
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('LLM_LOCAL_MODEL_PATH='):
            lines[i] = f'LLM_LOCAL_MODEL_PATH={model_path}\n'
            updated = True
            break
    
    if updated:
        with open(env_path, 'w') as f:
            f.writelines(lines)
        print(f"✅ Updated .env file: LLM_LOCAL_MODEL_PATH={model_path}")
        return True
    else:
        print("❌ Could not find LLM_LOCAL_MODEL_PATH in .env file")
        return False

def show_current_config():
    """Show current local model configuration"""
    env_path = Path('/home/haymayndz/AI_System_Monorepo/.env')
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if 'LLM_LOCAL_MODEL_PATH=' in line:
                    model_path = line.strip().split('=', 1)[1]
                    print(f"📍 Current LLM Model Path: {model_path}")
                    return model_path
    
    print("❌ No LLM model path configured")
    return None

def main():
    print("🤖 LOCAL MODEL SETUP for LLM Local-First Priority")
    print("=" * 60)
    
    # Show current config
    show_current_config()
    
    print("\n🛠️  SETUP OPTIONS:")
    print("1. Install Ollama + Download recommended model (EASIEST)")
    print("2. Use existing local model path")
    print("3. Show available models")
    print("4. Test current model")
    print("5. Exit")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == '1':
        # Install Ollama and download model
        if not check_ollama_installed():
            print("🔧 Ollama not found. Installing...")
            if not install_ollama():
                print("❌ Failed to install Ollama. Please install manually:")
                print("   curl -fsSL https://ollama.ai/install.sh | sh")
                return
        else:
            print("✅ Ollama already installed")
            
        # List and download model
        list_available_models()
        model_choice = input("Enter model name (or 1 for llama2:7b-chat): ").strip()
        
        if model_choice == '1' or model_choice == '':
            model_name = 'llama2:7b-chat'
        else:
            model_name = model_choice
            
        if download_model(model_name):
            update_env_file(f"ollama://{model_name}")
            print(f"\n🎉 LOCAL MODEL SETUP COMPLETE!")
            print(f"   Model: {model_name}")
            print(f"   Path: ollama://{model_name}")
            print("\n🚀 Ready to test with: python3 scripts/test_api_priorities.py")
            
    elif choice == '2':
        # Use existing model path
        model_path = input("Enter local model path: ").strip()
        if model_path:
            update_env_file(model_path)
            print(f"✅ Updated model path: {model_path}")
        
    elif choice == '3':
        # Show available models
        list_available_models()
        print("\n💡 To download: ollama pull <model-name>")
        
    elif choice == '4':
        # Test current model
        print("🧪 Testing current model configuration...")
        try:
            sys.path.append('/home/haymayndz/AI_System_Monorepo')
            from common.hybrid_api_manager import llm_chat
            import asyncio
            
            async def test_llm():
                response = await llm_chat("What is the capital of the Philippines?")
                print(f"✅ LLM Response: {response}")
                
            asyncio.run(test_llm())
        except Exception as e:
            print(f"❌ Model test failed: {e}")
            
    elif choice == '5':
        print("👋 Setup cancelled")
        return
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
