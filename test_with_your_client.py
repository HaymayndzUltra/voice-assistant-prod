#!/usr/bin/env python3
"""
Test your prompt using your existing ollama_client.py
This uses your rule-based parser's LLM integration
"""

from ollama_client import call_ollama, SYSTEM_PROMPTS

def test_with_your_client(prompt, task_type="general"):
    """Test prompt using your existing client"""
    
    print(f"🔗 Testing with your existing Ollama client...")
    print(f"📤 Your prompt: {prompt}")
    
    # Choose system prompt based on task type
    if task_type == "task_decomposition":
        system_prompt = SYSTEM_PROMPTS["task_decomposition"]
        print("⚙️ Using task decomposition system prompt")
    elif task_type == "validation":
        system_prompt = SYSTEM_PROMPTS["simple_validation"]
        print("⚙️ Using validation system prompt")
    else:
        system_prompt = ""
        print("⚙️ No system prompt (general response)")
    
    # Call your existing client
    result = call_ollama(prompt, system_prompt)
    
    if result:
        print(f"\n✅ Response from your client:")
        if "raw_response" in result:
            print(f"📝 Raw: {result['raw_response']}")
        else:
            print(f"📝 Parsed: {result}")
        return result
    else:
        print(f"\n❌ No response from your client")
        return None

if __name__ == "__main__":
    # 🔥 REPLACE THIS WITH YOUR READY PROMPT! 🔥
    your_prompt = "Break down the task of creating a user authentication system"
    
    # Choose task type: "general", "task_decomposition", or "validation"
    task_type = "task_decomposition"
    
    # Test your prompt
    result = test_with_your_client(your_prompt, task_type)
    
    if result:
        print(f"\n🎉 Success! Your prompt worked with your client")
    else:
        print(f"\n❌ Failed to get response") 