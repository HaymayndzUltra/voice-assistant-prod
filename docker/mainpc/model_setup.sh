#!/bin/bash
# Model Setup Script for MainPC (RTX 4090)
# This script downloads and sets up all the necessary models for the MainPC

# Create model directories
mkdir -p models/llm
mkdir -p models/vision
mkdir -p models/voice
mkdir -p models/embeddings

# Set environment variables
export PYTHONPATH=$PYTHONPATH:$(pwd)
export HF_HOME=$(pwd)/models/.cache
export TRANSFORMERS_CACHE=$(pwd)/models/.cache

echo "=== Setting up models for MainPC (RTX 4090) ==="

# Download GGUF models
cd models/llm

echo "=== Downloading Llama-3-8B GGUF model ==="
if [ ! -f "llama3-8b-instruct.Q4_K_M.gguf" ]; then
    wget -O llama3-8b-instruct.Q4_K_M.gguf https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf
fi

echo "=== Downloading CodeLlama-7B GGUF model ==="
if [ ! -f "codellama-7b-instruct.Q4_K_M.gguf" ]; then
    wget -O codellama-7b-instruct.Q4_K_M.gguf https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf
fi

echo "=== Downloading DeepSeek Coder GGUF model ==="
if [ ! -f "deepseek-coder-v1.5.Q4_K_M.gguf" ]; then
    wget -O deepseek-coder-v1.5.Q4_K_M.gguf https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf
fi

echo "=== Downloading TinyLlama GGUF model ==="
if [ ! -f "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" ]; then
    wget -O tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
fi

# Download Hugging Face models
cd ../

echo "=== Downloading voice models ==="
cd voice
# Whisper for STT
python -c 'from transformers import WhisperForConditionalGeneration, WhisperProcessor; WhisperForConditionalGeneration.from_pretrained("openai/whisper-medium"); WhisperProcessor.from_pretrained("openai/whisper-medium")'

# PIPER for TTS
if [ ! -d "piper" ]; then
    mkdir -p piper
    cd piper
    wget https://github.com/rhasspy/piper/releases/download/v1.2.0/voice-en-us-libritts-high.tar.gz
    tar -xzf voice-en-us-libritts-high.tar.gz
    wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
    tar -xzf piper_amd64.tar.gz
    cd ..
fi

echo "=== Downloading vision models ==="
cd ../vision
# Face recognition
python -c 'import gdown; gdown.download("https://drive.google.com/uc?id=1EXPBSXwTaqrSC0OhUdXNmKSh9qJUQ55-", "model-r50-am-lfw.h5", quiet=False)'

# CLIP for image understanding
python -c 'from transformers import CLIPProcessor, CLIPModel; CLIPModel.from_pretrained("openai/clip-vit-large-patch14"); CLIPProcessor.from_pretrained("openai/clip-vit-large-patch14")'

cd ../embeddings
# Sentence transformers for embeddings
python -c 'from sentence_transformers import SentenceTransformer; SentenceTransformer("all-MiniLM-L6-v2")'

echo "=== All models have been downloaded successfully ==="

# Configure model settings
cd ../../
echo "=== Configuring model settings ==="
cp -n main_pc_code/agents/model_config.yaml main_pc_code/agents/model_config.yaml.bak
cat > main_pc_code/agents/model_config.yaml << EOL
# Model Configuration with Version Management
# Last updated: $(date +%Y-%m-%d)

models:
  # Primary code generation models
  deepseek:
    path: models/llm/deepseek-coder-v1.5.Q4_K_M.gguf
    version: v1.5
    vram_mb: 6000
    args: --ctx-size 16384 --batch-size 512 --threads 8 --temp 0.7
    fallback: codellama
    use_case: code_generation
    priority: high
    preload: true
    
  codellama:
    path: models/llm/codellama-7b-instruct.Q4_K_M.gguf
    version: v1.0
    vram_mb: 6000
    args: --ctx-size 12288 --batch-size 512 --threads 8 --temp 0.7
    fallback: llama3
    use_case: code_generation
    priority: high
    preload: true
    
  llama3:
    path: models/llm/llama3-8b-instruct.Q4_K_M.gguf
    version: v1.0
    vram_mb: 6000
    args: --ctx-size 8192 --batch-size 512 --threads 6 --temp 0.7
    fallback: tinyllama
    use_case: reasoning
    priority: medium
    preload: false
    
  # Fallback / lightweight model
  tinyllama:
    path: models/llm/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
    version: v1.0
    vram_mb: 1500
    args: --ctx-size 2048 --batch-size 128 --threads 2 --temp 0.8
    fallback: null
    use_case: fallback
    priority: low
    preload: true
    emergency_fallback: true

# Global configuration
global:
  vram_limit_mb: 20000  # 20GB VRAM limit for RTX 4090 (24GB)
  model_timeout_sec: 300  # 5 minutes of inactivity before unloading
  max_retries: 3
  base_retry_delay: 1.0  # seconds
  health_port: 5597
  default_fallback: "tinyllama"
  emergency_vram_threshold: 0.05
  model_startup_timeout_sec: 60
  check_compatibility: true
EOL

echo "=== Model setup complete! ===" 