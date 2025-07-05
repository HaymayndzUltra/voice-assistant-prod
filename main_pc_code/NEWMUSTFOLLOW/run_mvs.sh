#!/bin/bash

# MVS Runner Script
# This script sets up the environment and runs the Minimal Viable System

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'
BOLD='\033[1m'

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
MAIN_PC_CODE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$MAIN_PC_CODE_DIR")"

echo -e "${BLUE}${BOLD}Starting Minimal Viable System...${RESET}"
echo "Script directory: $SCRIPT_DIR"
echo "Main PC code directory: $MAIN_PC_CODE_DIR"
echo "Project root: $PROJECT_ROOT"

# Create env_config.sh if it doesn't exist
ENV_CONFIG="$PROJECT_ROOT/env_config.sh"
if [ ! -f "$ENV_CONFIG" ]; then
    echo -e "${YELLOW}Creating environment configuration file at $ENV_CONFIG${RESET}"
    cat > "$ENV_CONFIG" << 'EOL'
#!/bin/bash

# Environment configuration for AI System Monorepo
# This file is sourced by run_mvs.sh

# Machine configuration
export MACHINE_TYPE="MAINPC"
export PYTHONPATH="$PYTHONPATH:$PWD"

# Network configuration
export MAIN_PC_IP="localhost"
export PC2_IP="localhost"
export BIND_ADDRESS="0.0.0.0"

# Security settings
export SECURE_ZMQ="0"
export ZMQ_CERTIFICATES_DIR="certificates"

# Service discovery
export SYSTEM_DIGITAL_TWIN_PORT="7120"
export SERVICE_DISCOVERY_ENABLED="1"
export FORCE_LOCAL_SDT="1"

# Voice pipeline ports
export TASK_ROUTER_PORT="8573"
export STREAMING_TTS_PORT="5562"
export TTS_PORT="5562"
export INTERRUPT_PORT="5577"

# Resource constraints
export MAX_MEMORY_MB="2048"
export MAX_VRAM_MB="2048"

# Logging
export LOG_LEVEL="INFO"
export LOG_DIR="logs"

# Timeouts and retries
export ZMQ_REQUEST_TIMEOUT="10000"
export CONNECTION_RETRIES="3"
export SERVICE_DISCOVERY_TIMEOUT="10000"

# Voice pipeline settings
export VOICE_SAMPLE_DIR="voice_samples"
export MODEL_DIR="models"
export CACHE_DIR="cache"

# Dummy audio for testing
export USE_DUMMY_AUDIO="true"

# Create necessary directories
mkdir -p logs data models cache certificates
EOL
    chmod +x "$ENV_CONFIG"
    echo -e "${GREEN}Created environment configuration file${RESET}"
else
    echo -e "${GREEN}Using existing environment configuration file${RESET}"
fi

# Source the environment configuration
echo "Sourcing environment configuration from $ENV_CONFIG"
source "$ENV_CONFIG"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${RESET}"
    exit 1
fi

# Change to the script directory
cd "$SCRIPT_DIR"

# Create necessary directories
mkdir -p logs data models cache certificates

# Run the MVS
echo -e "${BLUE}${BOLD}Starting MVS...${RESET}"
python3 start_mvs.py "$@"

# Check the exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}${BOLD}MVS exited successfully${RESET}"
else
    echo -e "${RED}${BOLD}MVS exited with an error${RESET}"
fi 