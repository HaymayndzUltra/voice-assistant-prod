#!/bin/bash
# Run script for improved Layer 0 startup

# Ensure we're in the project root
cd "$(dirname "$0")"

# Create necessary directories
mkdir -p logs
mkdir -p temp

# Clean up any lingering processes
echo "Cleaning up any lingering processes..."
python3 cleanup_agents.py --force

# Set environment variables
export PYTHONPATH=$(pwd)
export ENV_TYPE=development
export NETWORK_CONFIG_PATH=$(pwd)/config/network_config.yaml
export FORCE_LOCAL_MODE=true
export PROJECT_ROOT=$(pwd)

# Run the improved startup script with cleanup first
echo "Running improved Layer 0 startup..."
python3 improved_layer0_startup.py --cleanup-only
python3 improved_layer0_startup.py --config main_pc_code/NEWMUSTFOLLOW/minimal_system_config_local.yaml 