import json
import os
import subprocess
import sys
import time


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
def get_config():
    config_path = PathManager.join_path("config", "distributed_config.json")
    with open(config_path, "r") as f:
        return json.load(f)

def start_agent(agent_name, port):
    print(f"Starting agent: {agent_name} on port {port}")
    agent_script = f"agents/{agent_name}.py"
    
    # Check if agent script exists
    if not os.path.exists(agent_script):
        print(f"Warning: Agent script {agent_script} not found")
        return None
        
    try:
        # Start the agent process
        process = subprocess.Popen(
            [sys.executable, agent_script, "--port", str(port), "--distributed"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"Started {agent_name} with PID {process.pid}")
        return process
    except Exception as e:
        print(f"Error starting {agent_name}: {e}")
        return None

def main():
    print("=== Force Starting Second PC Agents ===")
    
    # Load configuration
    config = get_config()
    
    # Get second PC agents and ports
    second_pc_agents = config["machines"]["second_pc"]["agents"]
    ports = config["ports"]
    
    # Start each agent
    processes = {}
    for agent in second_pc_agents:
        if agent in ports:
            port = ports[agent]
            proc = start_agent(agent, port)
            if proc:
                processes[agent] = proc
        else:
            print(f"Warning: No port defined for {agent}")
    
    print(f"Started {len(processes)} agents")
    
    # Keep running until Ctrl+C
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping all agents...")
        for agent, proc in processes.items():
            print(f"Terminating {agent}")
            proc.terminate()
        
        print("All agents stopped")

if __name__ == "__main__":
    main()
