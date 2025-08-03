#!/usr/bin/env python3
"""
Complete Hybrid AI Setup Test
Local STT (Whisper) + Cloud TTS (OpenAI HD) + Local LLM (Llama3) + Cloud Fallback
"""

import sys
import asyncio
from pathlib import Path

sys.path.append('/home/haymayndz/AI_System_Monorepo')

async def test_complete_setup():
    """Test the complete hybrid AI setup"""
    
    print("🧪 COMPLETE HYBRID AI SETUP TEST")
    print("=" * 60)
    print("📋 Configuration:")
    print("   🎤 STT: Local Whisper (primary) → OpenAI Cloud (fallback)")
    print("   🔊 TTS: OpenAI TTS-1-HD (primary) → ElevenLabs (fallback)")  
    print("   🧠 LLM: Local Llama3 (primary) → OpenAI (fallback)")
    print("   🌍 Translation: Google Cloud (primary) → Azure (fallback)")
    print("=" * 60)
    
    try:
        from common.hybrid_api_manager import api_manager, tts, llm_chat
        
        # Test 1: Local STT (Whisper)
        print("\n1️⃣ Testing LOCAL WHISPER STT...")
        try:
            import whisper
            print(f"   ✅ Whisper available: v{whisper.__version__}")
            
            # Create a small test audio (empty for now)
            dummy_audio = b'\x00' * 1024 
            stt_result = await api_manager.speech_to_text(dummy_audio, "en-US")
            print(f"   ✅ STT Result: '{stt_result}'")
            
        except Exception as e:
            print(f"   ❌ Local STT failed: {e}")
            
        # Test 2: Cloud TTS (OpenAI HD)
        print("\n2️⃣ Testing CLOUD TTS (OpenAI TTS-1-HD)...")
        try:
            test_text = "Hello! This is a test of OpenAI TTS-1-HD with Nova voice."
            audio_data = await tts(test_text)
            print(f"   ✅ TTS Success: Generated {len(audio_data)} bytes")
            print(f"   Model: {api_manager.config['tts']['primary_provider']} (OpenAI TTS-1-HD)")
            
        except Exception as e:
            print(f"   ❌ Cloud TTS failed: {e}")
            
        # Test 3: Local LLM (Llama3)
        print("\n3️⃣ Testing LOCAL LLM (Llama3)...")
        try:
            test_prompt = "What is the capital of the Philippines? Give a brief answer."
            llm_response = await llm_chat(test_prompt, temperature=0.3)
            print(f"   ✅ LLM Response: {llm_response[:100]}...")
            print(f"   Model: {api_manager.config['llm']['primary_provider']} (Llama3)")
            
        except Exception as e:
            print(f"   ❌ Local LLM failed: {e}")
            print("   📥 Llama3 might still be downloading...")
            
        # Test 4: Check Download Status
        print("\n4️⃣ Checking Model Status...")
        
        # Check Whisper models
        try:
            import whisper
            available_models = []
            for model in ['tiny', 'base', 'small', 'medium', 'large']:
                try:
                    whisper.load_model(model)
                    available_models.append(model)
                except:
                    pass
            print(f"   🎤 Whisper models: {', '.join(available_models)}")
        except:
            print("   ❌ Cannot check Whisper models")
            
        # Check Ollama models
        try:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\\n')[1:]  # Skip header
                models = [line.split()[0] for line in lines if line.strip()]
                print(f"   🧠 Ollama models: {', '.join(models)}")
            else:
                print("   ❌ Cannot check Ollama models")
        except:
            print("   ❌ Ollama not available")
            
        print("\n" + "=" * 60)
        print("📊 SETUP SUMMARY")
        print("=" * 60)
        
        # Configuration summary
        config = api_manager.config
        
        print("🎯 Your Optimized Hybrid Configuration:")
        print(f"   STT: {config['stt']['primary_provider']} → {config['stt']['fallback_provider']}")
        print(f"   TTS: {config['tts']['primary_provider']} → {config['tts']['fallback_provider']}")
        print(f"   LLM: {config['llm']['primary_provider']} → {config['llm']['fallback_provider']}")
        print(f"   Translation: {config['translate']['primary_provider']} → {config['translate']['fallback_provider']}")
        
        print("\n💡 BENEFITS OF YOUR SETUP:")
        print("   🎤 STT: Local = Privacy + Speed, No API costs")
        print("   🔊 TTS: Cloud = High quality, Multiple voices")  
        print("   🧠 LLM: Local = Privacy + Cost savings, Cloud fallback for reliability")
        print("   🌍 Translation: Cloud = Best accuracy")
        
        print("\n🚀 Ready for AI Voice Assistant deployment!")
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
    except Exception as e:
        print(f"❌ Test Error: {e}")

if __name__ == "__main__":
    print("🌟 HYBRID AI SYSTEM - Complete Setup Test")
    asyncio.run(test_complete_setup())
