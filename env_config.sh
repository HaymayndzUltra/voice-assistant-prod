#!/bin/bash

# Environment type (development, testing, production)
export ENV_TYPE="development"

# Network configuration
export FORCE_LOCAL_MODE="true"
export MAINPC_IP="127.0.0.1"  # Use loopback for local development
export PC2_IP="127.0.0.1"     # Use loopback for local development
export BIND_ADDRESS="0.0.0.0" # Listen on all interfaces

# Feature flags
export ENABLE_METRICS="false"
export ENABLE_SECURE_ZMQ="false"
export ENABLE_PROMETHEUS="false"
export SERVICE_DISCOVERY_TIMEOUT="5000"  # Shorter timeout for development
export SERVICE_DISCOVERY_RETRIES="3"

# System paths
export PYTHONPATH="${PYTHONPATH}:${PWD}"

export LOG_LEVEL="INFO"
export SECURE_ZMQ="0"
export USE_DUMMY_AUDIO="true"
export DEBUG_MODE="true"
export CACHE_ENABLED="true"
export MEMORY_DB_PATH="./data/memory.db"
export MODEL_CACHE_DIR="./cache/models"
export ZMQ_REQUEST_TIMEOUT="5000"
export HEALTH_CHECK_INTERVAL="30"
export PROJECT_ROOT="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

# System paths
export PYTHON_PATH="$PROJECT_ROOT:$PYTHON_PATH"

echo "Environment configuration loaded from $(realpath "${BASH_SOURCE[0]}")"
echo "PROJECT_ROOT set to: $PROJECT_ROOT" 