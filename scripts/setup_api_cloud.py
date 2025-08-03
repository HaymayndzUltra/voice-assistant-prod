#!/usr/bin/env python3
"""
Interactive API Cloud Configuration Setup
Configures cloud API keys for hybrid AI services
"""

import os
import json
from pathlib import Path

def load_current_env():
    """Load current environment variables"""
    env_path = Path.cwd() / '.env'
    current_env = {}
    
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    current_env[key] = value
    
    return current_env

def show_api_status():
    """Show current API configuration status"""
    current_env = load_current_env()
    
    print("\n📝 Current API Configuration Status:")
    
    # Check OpenAI
    openai_key = current_env.get('OPENAI_API_KEY', '')
    if openai_key and len(openai_key) > 20:
        print(f"✅ OpenAI API Key: Configured ({openai_key[:8]}...)")
    else:
        print("❌ OpenAI API Key: Not configured")
        
    # Check Google Cloud
    google_key = current_env.get('GOOGLE_TRANSLATE_API_KEY', '')
    if google_key and len(google_key) > 20:
        print(f"✅ Google Translate API Key: Configured ({google_key[:8]}...)")
    else:
        print("❌ Google Translate API Key: Not configured")
        
    # Check Azure
    azure_key = current_env.get('AZURE_TRANSLATOR_KEY', '')
    if azure_key and len(azure_key) > 20:
        print(f"✅ Azure Translator Key: Configured ({azure_key[:8]}...)")
    else:
        print("❌ Azure Translator Key: Not configured")
        
    # Check ElevenLabs
    elevenlabs_key = current_env.get('ELEVENLABS_API_KEY', '')
    if elevenlabs_key and len(elevenlabs_key) > 20:
        print(f"✅ ElevenLabs API Key: Configured ({elevenlabs_key[:8]}...)")
    else:
        print("❌ ElevenLabs API Key: Not configured")

def setup_interactive():
    """Interactive setup of API keys"""
    print("\n🔧 Interactive API Configuration Setup")
    print("Leave blank to skip or keep existing values")
    
    current_env = load_current_env()
    
    # OpenAI API Key
    current_openai = current_env.get('OPENAI_API_KEY', '')
    if current_openai:
        print(f"\nCurrent OpenAI key: {current_openai[:8]}...")
    new_openai = input("Enter OpenAI API key (sk-...): ").strip()
    if new_openai:
        current_env['OPENAI_API_KEY'] = new_openai
    
    # Google Translate API Key
    current_google = current_env.get('GOOGLE_TRANSLATE_API_KEY', '')
    if current_google:
        print(f"\nCurrent Google key: {current_google[:8]}...")
    new_google = input("Enter Google Translate API key: ").strip()
    if new_google:
        current_env['GOOGLE_TRANSLATE_API_KEY'] = new_google
    
    # Azure Translator Key
    current_azure = current_env.get('AZURE_TRANSLATOR_KEY', '')
    if current_azure:
        print(f"\nCurrent Azure key: {current_azure[:8]}...")
    new_azure = input("Enter Azure Translator key: ").strip()
    if new_azure:
        current_env['AZURE_TRANSLATOR_KEY'] = new_azure
        
        # Azure Region
        current_region = current_env.get('AZURE_TRANSLATOR_REGION', 'eastus')
        new_region = input(f"Enter Azure region [{current_region}]: ").strip()
        current_env['AZURE_TRANSLATOR_REGION'] = new_region or current_region
    
    # ElevenLabs API Key
    current_elevenlabs = current_env.get('ELEVENLABS_API_KEY', '')
    if current_elevenlabs:
        print(f"\nCurrent ElevenLabs key: {current_elevenlabs[:8]}...")
    new_elevenlabs = input("Enter ElevenLabs API key: ").strip()
    if new_elevenlabs:
        current_env['ELEVENLABS_API_KEY'] = new_elevenlabs
    
    # Save to .env file
    save_env(current_env)
    print("\n✅ Configuration saved to .env file")

def save_env(env_dict):
    """Save environment variables to .env file"""
    env_path = Path.cwd() / '.env'
    
    # Read existing content to preserve comments
    existing_lines = []
    if env_path.exists():
        with open(env_path, 'r') as f:
            existing_lines = f.readlines()
    
    # Update or add new variables
    updated_lines = []
    updated_keys = set()
    
    for line in existing_lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            if key in env_dict:
                updated_lines.append(f"{key}={env_dict[key]}\n")
                updated_keys.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add new keys that weren't in the file
    for key, value in env_dict.items():
        if key not in updated_keys:
            updated_lines.append(f"{key}={value}\n")
    
    # Write back to file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)

def main():
    print("🌐 Hybrid API Cloud Configuration Setup")
    print("=====================================")
    
    show_api_status()
    
    choice = input("\nWould you like to configure API keys? (y/N): ").strip().lower()
    if choice in ['y', 'yes']:
        setup_interactive()
    else:
        print("Configuration unchanged.")

if __name__ == "__main__":
    main()
