#!/bin/bash
# This script starts all agents belonging to a specific group on MainPC.

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if a group name is provided
if [ -z "$1" ]; then
  echo "Error: No agent group provided."
  echo "Usage: ./run_group.sh <agent_group_name>"
  exit 1
fi

GROUP_NAME=$1
CONFIG_FILE="/app/main_pc_code/config/startup_config.yaml"

echo "--- Starting agent group: $GROUP_NAME ---"

# Use a Python script to parse the YAML and get agent script paths.
# This avoids needing to install extra tools like yq in the Docker image.
AGENT_PATHS=$(python3 -c "
import yaml, sys
group_name = sys.argv[1]
config_file = sys.argv[2]
with open(config_file, 'r') as f: config = yaml.safe_load(f)
agents = config.get('agent_groups', {}).get(group_name, {})
for name, info in agents.items():
    if info.get('required', True):
        print(info['script_path'])
" "$GROUP_NAME" "$CONFIG_FILE")

# Launch each agent script in the background
for script_path in $AGENT_PATHS; do
  full_path="/app/$script_path"
  if [ -f "$full_path" ]; then
    agent_name=$(basename "$full_path")
    echo "Launching agent: $agent_name"
    python3 "$full_path" &
  else
    echo "Warning: Script not found for agent: $script_path"
  fi
done

echo "--- All required agents for group '$GROUP_NAME' launched. ---"

# Keep the container running by waiting for any background process to exit.
# If a critical agent crashes, the container will stop.
wait -n 