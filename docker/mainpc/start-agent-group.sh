#!/bin/bash

set -e

echo "🚀 Starting Agent Group: ${GROUP_NAME}"

# Source the startup configuration
STARTUP_CONFIG="/app/main_pc_code/config/startup_config.yaml"

if [ ! -f "$STARTUP_CONFIG" ]; then
    echo "❌ ERROR: Startup config not found at $STARTUP_CONFIG"
    exit 1
fi

# Python script to extract agents for this group and start them
python3 - << EOF
import yaml
import subprocess
import sys
import os
import time
import threading
from pathlib import Path

def load_config():
    with open('/app/main_pc_code/config/startup_config.yaml', 'r') as f:
        return yaml.safe_load(f)

def start_agent(agent_name, agent_config):
    """Start a single agent"""
    script_path = agent_config.get('script_path', '')
    if not script_path:
        print(f"❌ No script_path for {agent_name}")
        return None
    
    # Convert script path to module path
    if script_path.endswith('.py'):
        script_path = script_path[:-3]  # Remove .py
    
    module_path = script_path.replace('/', '.')
    
    print(f"🔄 Starting {agent_name} from {module_path}")
    
    try:
        # Start agent as subprocess
        process = subprocess.Popen([
            sys.executable, '-m', module_path
        ], env=os.environ.copy())
        
        print(f"✅ Started {agent_name} (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Failed to start {agent_name}: {e}")
        return None

def main():
    group_name = os.environ.get('GROUP_NAME', '')
    if not group_name:
        print("❌ ERROR: GROUP_NAME environment variable not set")
        sys.exit(1)
    
    print(f"📋 Loading agents for group: {group_name}")
    
    try:
        config = load_config()
        agent_groups = config.get('agent_groups', {})
        
        if group_name not in agent_groups:
            print(f"❌ ERROR: Group '{group_name}' not found in config")
            print(f"Available groups: {list(agent_groups.keys())}")
            sys.exit(1)
        
        group_config = agent_groups[group_name]
        agents = {}
        processes = {}
        
        print(f"🎯 Found {len(group_config)} agents in group '{group_name}'")
        
        # Start all agents in the group
        for agent_name, agent_config in group_config.items():
            if isinstance(agent_config, dict):
                print(f"🚀 Starting agent: {agent_name}")
                process = start_agent(agent_name, agent_config)
                if process:
                    processes[agent_name] = process
                time.sleep(2)  # Stagger starts
        
        if not processes:
            print("❌ ERROR: No agents were started successfully")
            sys.exit(1)
        
        print(f"✅ Successfully started {len(processes)} agents")
        print("🔄 Monitoring agent processes...")
        
        # Monitor processes
        while True:
            time.sleep(10)
            
            # Check if any process has died
            for agent_name, process in list(processes.items()):
                if process.poll() is not None:
                    print(f"⚠️  Agent {agent_name} has stopped (exit code: {process.returncode})")
                    
                    # Attempt restart
                    print(f"🔄 Restarting {agent_name}...")
                    new_process = start_agent(agent_name, group_config[agent_name])
                    if new_process:
                        processes[agent_name] = new_process
                        print(f"✅ Restarted {agent_name}")
                    else:
                        print(f"❌ Failed to restart {agent_name}")
                        del processes[agent_name]
            
            if not processes:
                print("❌ All agents have stopped. Exiting.")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("🛑 Shutting down agent group...")
        for agent_name, process in processes.items():
            print(f"🛑 Stopping {agent_name}...")
            process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF 