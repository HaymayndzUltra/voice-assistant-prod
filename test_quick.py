#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("🔑 CURRENT API KEY STATUS:")
print("=" * 40)

# Check OpenAI
openai_key = os.getenv('OPENAI_API_KEY', '')
if openai_key:
    print(f"✅ OpenAI API Key: {openai_key[:8]}...{openai_key[-8:]}")
else:
    print("❌ OpenAI API Key: Not found")

# Check ElevenLabs  
elevenlabs_key = os.getenv('ELEVENLABS_API_KEY', '')
if elevenlabs_key:
    print(f"✅ ElevenLabs API Key: {elevenlabs_key[:8]}...")
else:
    print("❌ ElevenLabs API Key: Not found")

# Check Google
google_key = os.getenv('GOOGLE_TRANSLATE_API_KEY', '')
if google_key:
    print(f"✅ Google Translate API Key: {google_key[:8]}...")
else:
    print("❌ Google Translate API Key: Not found")

print("\n🎯 CLOUD MODELS CONFIGURATION:")
print("=" * 40)

# STT Models
print(f"STT Model: {os.getenv('OPENAI_STT_MODEL', 'whisper-1')}")

# TTS Models  
print(f"TTS Model: {os.getenv('OPENAI_TTS_MODEL', 'tts-1')}")
print(f"TTS Voice: {os.getenv('OPENAI_TTS_VOICE', 'alloy')}")
print(f"ElevenLabs Model: {os.getenv('ELEVENLABS_MODEL_ID', 'eleven_monolingual_v1')}")

print("\n💡 WHAT YOU NEED TO SET:")
print("=" * 40)
if not elevenlabs_key:
    print("📝 Set ELEVENLABS_API_KEY in .env file for best TTS")
if not google_key:
    print("📝 Set GOOGLE_TRANSLATE_API_KEY in .env file for translation")

print(f"\n🌟 OpenAI is WORKING with models:")
print(f"   STT: {os.getenv('OPENAI_STT_MODEL', 'whisper-1')}")
print(f"   TTS: {os.getenv('OPENAI_TTS_MODEL', 'tts-1-hd')} voice: {os.getenv('OPENAI_TTS_VOICE', 'nova')}")
