#!/bin/bash

echo "🌥️  Installing Cloud API Dependencies..."
echo "========================================"

# Change to project directory
cd /home/haymayndz/AI_System_Monorepo

# Install cloud API requirements
echo "📦 Installing cloud API packages..."
pip3 install -r requirements_cloud_apis.txt

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo "✅ Cloud API dependencies installed successfully!"
    echo ""
    echo "🎯 Next steps:"
    echo "1. Run: python3 scripts/setup_api_cloud.py"
    echo "2. Configure your API keys"
    echo "3. Test: python3 scripts/test_api_priorities.py"
    echo ""
    echo "🔑 You'll need these API keys:"
    echo "   - OpenAI API Key (for STT/TTS/LLM fallback)"
    echo "   - ElevenLabs API Key (for high-quality TTS)"
    echo "   - Google Translate API Key (for translation)"
    echo "   - Azure Speech Key (optional fallback)"
else
    echo "❌ Installation failed. Please check the errors above."
    exit 1
fi
