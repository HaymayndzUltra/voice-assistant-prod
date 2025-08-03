#!/usr/bin/env python3
"""
Test Local STT + Cloud TTS Configuration
"""

import sys
import asyncio
from pathlib import Path

sys.path.append('/home/haymayndz/AI_System_Monorepo')

async def test_local_stt_cloud_tts():
    """Test local STT with cloud TTS"""
    
    print("🧪 Testing LOCAL STT + CLOUD TTS Setup")
    print("=" * 50)
    
    try:
        from common.hybrid_api_manager import api_manager, tts
        
        # Check current configuration
        status = api_manager.get_service_status()
        
        print("📊 Current Configuration:")
        print(f"   STT: {api_manager.config['stt']['primary_provider']} → {api_manager.config['stt']['fallback_provider']}")
        print(f"   TTS: {api_manager.config['tts']['primary_provider']} → {api_manager.config['tts']['fallback_provider']}")
        
        print("\n🎯 Testing Priority Setup...")
        
        # Test 1: Check if Whisper is available
        print("\n1️⃣ Testing Local Whisper STT...")
        try:
            import whisper
            print(f"   ✅ Whisper available: v{whisper.__version__}")
            
            # Test with dummy audio (small sample)
            dummy_audio = b'\x00' * 1024  # Dummy audio data
            stt_result = await api_manager.speech_to_text(dummy_audio, "en-US")
            print(f"   ✅ STT Test: '{stt_result}'")
            
        except Exception as e:
            print(f"   ❌ Local STT failed: {e}")
            
        # Test 2: Test TTS (Cloud)
        print("\n2️⃣ Testing Cloud TTS...")
        try:
            test_text = "Hello, this is a test of local STT with cloud TTS."
            audio_data = await tts(test_text)
            print(f"   ✅ TTS Success: Generated {len(audio_data)} bytes of audio")
            print(f"   Provider: {api_manager.config['tts']['primary_provider']}")
        except Exception as e:
            print(f"   ❌ TTS failed: {e}")
            
        print("\n📈 CONFIGURATION SUMMARY:")
        print("=" * 50)
        print("🎤 STT: LOCAL WHISPER FIRST")
        print("   Primary: Local Whisper")
        print("   Fallback: OpenAI Whisper (cloud)")
        print()
        print("🔊 TTS: CLOUD FIRST") 
        print("   Primary: ElevenLabs (need API key)")
        print("   Fallback: OpenAI TTS-HD (working)")
        
        # Check if Whisper models are downloaded
        print("\n💾 Local Whisper Models:")
        try:
            import whisper
            models = ['tiny', 'base', 'small', 'medium', 'large']
            for model in models:
                try:
                    whisper.load_model(model)
                    print(f"   ✅ {model} model available")
                except:
                    print(f"   ❌ {model} model not available")
        except:
            print("   ❌ Cannot check whisper models")
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
    except Exception as e:
        print(f"❌ Test Error: {e}")

if __name__ == "__main__":
    print("🎯 LOCAL STT + CLOUD TTS Configuration Test")
    asyncio.run(test_local_stt_cloud_tts())
