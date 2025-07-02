#!/bin/bash

# Required directories and files
REQUIRED_DIRS=(
    "./agents"
    "./src"
    "./config"
    "./utils"
)

REQUIRED_FILES=(
    "./config/model_config.json"
    "./config/system_config.py"
    "./utils/agent_utils.py"
)

# Check required directories
echo "Checking required directories..."
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "Error: Required directory $dir not found!"
        exit 1
    fi
done

# Check required files
echo "Checking required files..."
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: Required file $file not found!"
        exit 1
    fi
done

# Check for essential agent files
echo "Checking essential agent files..."
ESSENTIAL_AGENTS=(
    "./agents/model_manager_agent.py"
    "./agents/streaming_speech_recognition.py"
    "./agents/nlu_agent.py"
)

for agent in "${ESSENTIAL_AGENTS[@]}"; do
    if [ ! -f "$agent" ]; then
        echo "Error: Essential agent file $agent not found!"
        exit 1
    fi
done

# Check for essential src files
echo "Checking essential src files..."
ESSENTIAL_SRC=(
    "./src/core/main.py"
    "./src/audio/fused_audio_preprocessor.py"
)

for src in "${ESSENTIAL_SRC[@]}"; do
    if [ ! -f "$src" ]; then
        echo "Error: Essential source file $src not found!"
        exit 1
    fi
done

echo "All required directories and files are present."
exit 0 