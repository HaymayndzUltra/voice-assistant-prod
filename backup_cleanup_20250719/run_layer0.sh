#!/bin/bash
# Run script for Layer 0 agents

# Set environment variables
export PYTHONPATH=$(pwd)
export ENV_TYPE=development
export NETWORK_CONFIG_PATH=$(pwd)/config/network_config.yaml
export FORCE_LOCAL_MODE=true

# Create log directories if they don't exist
mkdir -p logs

# Run the unified startup script
python3 unified_layer0_startup.py --config main_pc_code/NEWMUSTFOLLOW/minimal_system_config_local.yaml 