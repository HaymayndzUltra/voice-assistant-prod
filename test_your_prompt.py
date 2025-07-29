#!/usr/bin/env python3
"""
Simple script to test your prompt with phi3:instruct
Just replace the prompt variable with your ready prompt!
"""

import requests
import json

def test_prompt_with_phi3(prompt, system_prompt=""):
    """Test any prompt with phi3:instruct"""
    
    print(f"🤖 Testing prompt with phi3:instruct...")
    print(f"📤 Your prompt: {prompt}")
    
    payload = {
        "model": "phi3:instruct",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 1024
        }
    }
    
    if system_prompt:
        payload["system"] = system_prompt
        print(f"⚙️ System prompt: {system_prompt}")
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            print(f"\n✅ Response from phi3:instruct:")
            print(f"📝 {generated_text}")
            
            return generated_text
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # 🔥 REPLACE THIS WITH YOUR READY PROMPT! 🔥
    your_prompt = "Explain how to integrate a new AI model into an existing system"
    
    # Optional: Add a system prompt for specific behavior
    system_prompt = ""  # Leave empty for general responses
    
    # Test your prompt
    result = test_prompt_with_phi3(your_prompt, system_prompt)
    
    if result:
        print(f"\n🎉 Success! Your prompt worked with phi3:instruct")
    else:
        print(f"\n❌ Failed to get response from phi3:instruct") 