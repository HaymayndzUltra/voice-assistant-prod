#!/bin/bash
set -e
GROUP_NAME=$1
CONFIG_FILE="/app/main_pc_code/config/startup_config.yaml"
echo "--- Starting agent group: $GROUP_NAME ---"
python3 -c "
import yaml, sys, os, subprocess
group_name = sys.argv[1]
config_file = sys.argv[2]
with open(config_file, 'r') as f: config = yaml.safe_load(f)
agents = config.get('agent_groups', {}).get(group_name, {})
for name, info in agents.items():
    if info.get('required', True):
        path = f'/app/{info[\"script_path\"]}'
        print(f'Launching agent: {name} from {path}')
        subprocess.Popen(['python3', path])
print(f'--- All required agents for group {group_name} launched. ---')
os.wait()
" "$GROUP_NAME" "$CONFIG_FILE" 