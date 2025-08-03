#!/usr/bin/env python3
"""
API Priority Test Script
Quick test para ma-verify ang hybrid API setup mo
"""

import sys
import asyncio
import json
from pathlib import Path

# Add project to path
sys.path.append('/home/haymayndz/AI_System_Monorepo')

async def test_api_priorities():
    """Test the hybrid API priority system"""
    
    print("🧪 Testing Hybrid API Priority System")
    print("=" * 60)
    
    try:
        from common.hybrid_api_manager import api_manager, tts, translate, llm_chat
        
        # Get service status first
        status = api_manager.get_service_status()
        print("📊 Current API Configuration:")
        for service, config in status.items():
            available = config['available_providers']
            status_icon = "✅" if available else "❌"
            print(f"{status_icon} {service.upper()}: {config['primary']} → {config['fallback']}")
            if available:
                print(f"   Available: {', '.join(available)}")
            else:
                print("   Available: None (check API keys)")
        
        print("\n" + "=" * 60)
        print("🎯 PRIORITY TESTS")
        print("=" * 60)
        
        # Test 1: TTS (Cloud First)
        print("\n1️⃣ Testing TTS (Cloud First Priority)...")
        try:
            test_text = "Testing TTS with cloud-first priority."
            audio_data = await tts(test_text)
            print(f"✅ TTS Success: Generated {len(audio_data)} bytes of audio")
            print(f"   Primary Provider: {api_manager.config['tts']['primary_provider']}")
        except Exception as e:
            print(f"❌ TTS Failed: {e}")
            
        # Test 2: Translation (Cloud First)
        print("\n2️⃣ Testing Translation (Cloud First Priority)...")
        try:
            test_text = "Hello, how are you today?"
            translated = await translate(test_text, "es")  # English to Spanish
            print(f"✅ Translation Success: '{test_text}' → '{translated}'")
            print(f"   Primary Provider: {api_manager.config['translate']['primary_provider']}")
        except Exception as e:
            print(f"❌ Translation Failed: {e}")
            
        # Test 3: LLM (Local First)
        print("\n3️⃣ Testing LLM (Local First Priority)...")
        try:
            test_prompt = "What is the capital of the Philippines?"
            response = await llm_chat(test_prompt, temperature=0.3)
            print(f"✅ LLM Success: {response[:100]}...")
            print(f"   Primary Provider: {api_manager.config['llm']['primary_provider']}")
        except Exception as e:
            print(f"❌ LLM Failed: {e}")
            
        print("\n" + "=" * 60)
        print("📈 TEST SUMMARY")
        print("=" * 60)
        
        # Configuration recommendations
        print("\n💡 RECOMMENDATIONS:")
        
        # Check if OpenAI is available
        if 'openai' in status['stt']['available_providers']:
            print("✅ OpenAI configured - Good for STT fallback")
        else:
            print("⚠️  OpenAI not configured - Set OPENAI_API_KEY for STT/TTS fallback")
            
        # Check if ElevenLabs is available  
        if api_manager.credentials['elevenlabs']['api_key']:
            print("✅ ElevenLabs configured - Excellent TTS quality")
        else:
            print("⚠️  ElevenLabs not configured - Set ELEVENLABS_API_KEY for best TTS")
            
        # Check if Google Translate is available
        if 'google' in status['translate']['available_providers']:
            print("✅ Google Translate configured - Excellent translation quality")
        else:
            print("⚠️  Google Translate not configured - Set GOOGLE_TRANSLATE_API_KEY")
            
        # Local model status
        local_model_path = api_manager.config['llm']['local_model_path']
        if Path(local_model_path).exists():
            print(f"✅ Local LLM model found at {local_model_path}")
        else:
            print(f"⚠️  Local LLM model not found at {local_model_path}")
            print("   Consider downloading a local model or using cloud fallback")
            
        print("\n🎯 Your current setup priorities:")
        print(f"   STT: {api_manager.config['stt']['primary_provider']} (cloud first)")
        print(f"   TTS: {api_manager.config['tts']['primary_provider']} (cloud first)")
        print(f"   Translate: {api_manager.config['translate']['primary_provider']} (cloud first)")
        print(f"   LLM: {api_manager.config['llm']['primary_provider']} (local first)")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure the hybrid_api_manager.py is in the common/ directory")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

def show_setup_guide():
    """Show quick setup guide"""
    print("\n" + "=" * 60)
    print("🚀 QUICK SETUP GUIDE")
    print("=" * 60)
    print("1. Run setup script: python scripts/setup_api_cloud.py")
    print("2. Set your API keys:")
    print("   - OpenAI API Key (STT/TTS fallback)")
    print("   - ElevenLabs API Key (Primary TTS)")  
    print("   - Google Translate API Key (Primary Translation)")
    print("3. Test again: python scripts/test_api_priorities.py")
    print("=" * 60)

if __name__ == "__main__":
    print("🌥️  Hybrid API Priority Test")
    
    # Run the test
    try:
        asyncio.run(test_api_priorities())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        
    # Show setup guide
    show_setup_guide()
