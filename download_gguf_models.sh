#!/bin/bash
# 🚀 GGUF MODEL DOWNLOADER FOR RTX 4090 TESTING
# Download optimized GGUF models for fast inference

echo "🔽 DOWNLOADING GGUF MODELS FOR RTX 4090..."

# Create models directory
mkdir -p models/gguf
cd models/gguf

# Download Phi-3-Mini GGUF (Q4_K_M quantization)
echo "📦 Downloading Phi-3-Mini Q4_K_M..."
wget -O phi-3-mini-4k-instruct-q4_K_M.gguf \
    "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"

# Download Mistral-7B GGUF (Q4_K_M quantization)  
echo "📦 Downloading Mistral-7B Q4_K_M..."
wget -O mistral-7b-instruct-v0.2-q4_K_M.gguf \
    "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"

# Check downloads
echo "✅ DOWNLOAD COMPLETE!"
echo "📊 File sizes:"
ls -lh *.gguf

echo ""
echo "🎯 Models ready for testing!"
echo "Run: python3 complete_model_test.py" 