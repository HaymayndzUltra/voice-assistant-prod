import zmq
import subprocess
import time
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.system_config import pc2_settings

def start_agent(script_path, args=None):
    """Start an agent process"""
    try:
        cmd = ["python", script_path]
        if args:
            cmd.extend(args)
        print(f"Starting {script_path}...")
        subprocess.Popen(cmd, cwd="agents")
        time.sleep(2)  # Give some time to start
        return True
    except Exception as e:
        print(f"Failed to start {script_path}: {e}")
        return False

def check_agent_health(port, timeout=2):
    """Check agent health using ZMQ"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://127.0.0.1:{port}")
    socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
    
    try:
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        return True, response
    except Exception as e:
        print(f"Health check failed: {e}")
        return False, None
    finally:
        socket.close()
        context.term()

def main():
    # List of agents to check with their ports
    agents = [
        {"name": "Consolidated Translator", "script": "consolidated_translator.py", "port": 5563},
        {"name": "NLLB Adapter", "script": "llm_translation_adapter.py", "port": 5581},
        {"name": "TinyLlama Service", "script": "tinyllama_service_enhanced.py", "port": 5615},
        {"name": "Unified Memory Reasoning", "script": "unified_memory_reasoning_agent.py", "port": 5596},
        {"name": "DreamWorld Agent", "script": "DreamWorldAgent.py", "port": 5642},
        {"name": "Learning Adjuster", "script": "learning_adjuster_agent.py", "port": 5643},
        {"name": "Cognitive Model", "script": "CognitiveModelAgent.py", "port": 5644},
        {"name": "GOT/TOT Agent", "script": "got_tot_agent.py", "port": 5645}
    ]
    
    print("\n=== Starting Agent Health Check ===\n")
    
    for agent in agents:
        print(f"\n=== Checking {agent['name']} ===")
        
        # Start the agent
        if start_agent(agent['script']):
            print(f"✓ {agent['name']} started successfully")
            
            # Check health
            is_healthy, response = check_agent_health(agent['port'])
            if is_healthy:
                print(f"✓ {agent['name']} is healthy")
                print("Health check response:", response)
            else:
                print(f"✗ {agent['name']} health check failed")
        else:
            print(f"✗ Failed to start {agent['name']}")

if __name__ == "__main__":
    main()
