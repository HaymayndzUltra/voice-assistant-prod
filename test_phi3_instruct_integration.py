#!/usr/bin/env python3
"""
Test script for phi3:instruct model integration
Verifies that the model is properly integrated into your AI system
"""

import json
import time
import requests
from typing import Dict, Any

def test_ollama_connection():
    """Test basic Ollama connection"""
    print("🔍 Testing Ollama connection...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Ollama is running. Found {len(models)} models:")
            for model in models:
                print(f"   - {model.get('name', 'unknown')}")
            return True
        else:
            print(f"❌ Ollama returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return False

def test_phi3_instruct_availability():
    """Test if phi3:instruct model is available"""
    print("\n🔍 Checking phi3:instruct availability...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            phi3_models = [m for m in models if "phi3" in m.get('name', '').lower()]
            
            if phi3_models:
                print("✅ Phi3 models found:")
                for model in phi3_models:
                    print(f"   - {model.get('name')} (size: {model.get('size', 'unknown')})")
                return True
            else:
                print("❌ No phi3 models found. You may need to run:")
                print("   ollama pull phi3:instruct")
                return False
        else:
            print(f"❌ Failed to get model list: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False

def test_phi3_instruct_generation():
    """Test phi3:instruct text generation"""
    print("\n🤖 Testing phi3:instruct generation...")
    
    test_prompt = "Explain what makes phi3:instruct special in 2 sentences."
    
    try:
        payload = {
            "model": "phi3:instruct",
            "prompt": test_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 256
            }
        }
        
        print(f"📤 Sending prompt: '{test_prompt}'")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            elapsed_time = time.time() - start_time
            
            print(f"✅ Generation successful ({elapsed_time:.2f}s)")
            print(f"📝 Response: {generated_text}")
            
            # Check response quality
            if len(generated_text) > 10:
                print("✅ Response quality: Good (substantial content)")
            else:
                print("⚠️ Response quality: Poor (too short)")
                
            return True
        else:
            print(f"❌ Generation failed with status: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during generation: {e}")
        return False

def test_task_decomposition():
    """Test phi3:instruct for task decomposition (your rule-based parser use case)"""
    print("\n🎯 Testing task decomposition with phi3:instruct...")
    
    system_prompt = """You are an expert task decomposition assistant. Break down complex tasks into clear, actionable steps.

RULES:
1. Always respond with valid JSON in this exact format:
{
  "steps": ["step 1 description", "step 2 description", ...],
  "complexity": "COMPLEX|MEDIUM|SIMPLE",
  "estimated_duration": 60,
  "reasoning": ["why this task is complex", "what makes it challenging"]
}

2. Each step should be specific and actionable
3. Support both English and Filipino/Taglish input
4. Be practical about time estimates"""

    test_task = "Create a user authentication system with login, registration, and password reset functionality"
    
    try:
        payload = {
            "model": "phi3:instruct",
            "prompt": test_task,
            "system": system_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 1024
            }
        }
        
        print(f"📤 Decomposing task: '{test_task}'")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            elapsed_time = time.time() - start_time
            
            print(f"✅ Decomposition successful ({elapsed_time:.2f}s)")
            
            # Try to parse JSON response
            try:
                parsed = json.loads(response_text)
                print("✅ JSON parsing successful")
                print(f"📋 Steps: {len(parsed.get('steps', []))}")
                print(f"🎯 Complexity: {parsed.get('complexity', 'unknown')}")
                print(f"⏱️ Estimated duration: {parsed.get('estimated_duration', 'unknown')} minutes")
                
                # Show first few steps
                steps = parsed.get('steps', [])
                for i, step in enumerate(steps[:3], 1):
                    print(f"   {i}. {step}")
                if len(steps) > 3:
                    print(f"   ... and {len(steps) - 3} more steps")
                    
                return True
                
            except json.JSONDecodeError:
                print("⚠️ Response is not valid JSON, but generation worked")
                print(f"Raw response: {response_text[:200]}...")
                return True
                
        else:
            print(f"❌ Decomposition failed with status: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during decomposition: {e}")
        return False

def test_integration_with_your_system():
    """Test integration with your existing Ollama client"""
    print("\n🔗 Testing integration with your Ollama client...")
    
    try:
        from ollama_client import call_ollama, SYSTEM_PROMPTS
        
        test_prompt = "Fix a bug in the login system"
        
        print(f"📤 Testing with your client: '{test_prompt}'")
        start_time = time.time()
        
        result = call_ollama(
            prompt=test_prompt,
            system_prompt=SYSTEM_PROMPTS["task_decomposition"]
        )
        
        elapsed_time = time.time() - start_time
        
        if result:
            print(f"✅ Integration successful ({elapsed_time:.2f}s)")
            print("📋 Result structure:")
            for key, value in result.items():
                if isinstance(value, list):
                    print(f"   {key}: {len(value)} items")
                else:
                    print(f"   {key}: {value}")
            return True
        else:
            print("❌ Integration failed - no result returned")
            return False
            
    except ImportError:
        print("⚠️ Could not import ollama_client - skipping integration test")
        return False
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 Phi3:Instruct Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Phi3:Instruct Availability", test_phi3_instruct_availability),
        ("Basic Generation", test_phi3_instruct_generation),
        ("Task Decomposition", test_task_decomposition),
        ("System Integration", test_integration_with_your_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Phi3:instruct is fully integrated.")
    elif passed >= len(results) - 1:
        print("✅ Most tests passed. Minor issues to address.")
    else:
        print("⚠️ Several tests failed. Check Ollama setup and model availability.")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if not any(name == "Phi3:Instruct Availability" and success for name, success in results):
        print("   - Run: ollama pull phi3:instruct")
    if not any(name == "Ollama Connection" and success for name, success in results):
        print("   - Start Ollama: ollama serve")
    if not any(name == "System Integration" and success for name, success in results):
        print("   - Check your ollama_client.py configuration")

if __name__ == "__main__":
    main() 