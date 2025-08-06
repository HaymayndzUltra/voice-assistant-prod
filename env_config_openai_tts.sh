#!/bin/bash

# Environment Configuration for OpenAI TTS-1-HD Primary Setup
# Updated configuration without ElevenLabs dependency

# TTS Cloud Providers Configuration
export TTS_PRIMARY_PROVIDER="openai"
export TTS_FALLBACK_PROVIDER="google"  # or "azure" if you have Azure
export TTS_USE_LOCAL_FALLBACK="true"

# OpenAI Configuration (Primary TTS Provider)
export OPENAI_API_KEY="your_openai_api_key_here"
export OPENAI_TTS_MODEL="tts-1-hd"  # High-definition TTS model
export OPENAI_TTS_VOICE="alloy"     # Available: alloy, echo, fable, onyx, nova, shimmer

# STT Configuration (optional - for speech input)
export STT_PRIMARY_PROVIDER="openai"
export STT_FALLBACK_PROVIDER="local"
export OPENAI_STT_MODEL="whisper-1"

# Translation Configuration (optional)
export TRANSLATE_PRIMARY_PROVIDER="google"
export TRANSLATE_FALLBACK_PROVIDER="openai"

# LLM Configuration (Local-first)
export LLM_PRIMARY_PROVIDER="local"
export LLM_FALLBACK_PROVIDER="openai"
export LLM_LOCAL_MODEL_PATH="ollama://llama3:13b-instruct"
export LLM_USE_CLOUD_FALLBACK="true"

# Google Cloud Configuration (optional fallback)
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
# export GOOGLE_CLOUD_PROJECT_ID="your_project_id"
# export GOOGLE_TTS_LANGUAGE="en-US"

# Azure Configuration (optional fallback)
# export AZURE_SPEECH_KEY="your_azure_speech_key"
# export AZURE_SPEECH_REGION="your_region"

# System Configuration
export PYTHONPATH="$PYTHONPATH:$PWD"
export LOG_LEVEL="INFO"

echo "✅ Environment configured for OpenAI TTS-1-HD primary setup"
echo "🔊 TTS Priority: OpenAI TTS-1-HD → Google Cloud → Local TTS"
echo "🎤 STT Priority: OpenAI Whisper → Local Whisper"
echo "🌐 Translation: Google Translate → OpenAI GPT"
echo "🤖 LLM: Local Models → OpenAI GPT"