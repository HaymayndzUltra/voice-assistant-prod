import zmq
import subprocess
import time
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pc2_code.config.system_config import pc2_settings

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
        {"name": "Consolidated Translator", "port": 5563},
        {"name": "NLLB Adapter", "port": 5581},
        {"name": "TinyLlama Service", "port": 5615},
        {"name": "Unified Memory Reasoning", "port": 5596},
        {"name": "DreamWorld Agent", "port": 5642},
        {"name": "Learning Adjuster", "port": 5643},
        {"name": "Cognitive Model", "port": 5644},
        {"name": "GOT/TOT Agent", "port": 5645}
    ]
    
    print("\n=== Running Agent Health Check ===\n")
    
    healthy_count = 0
    total_agents = len(agents)
    
    for agent in agents:
        print(f"\n=== Checking {agent['name']} ===")
        
        # Check health
        is_healthy, response = check_agent_health(agent['port'])
        if is_healthy:
            healthy_count += 1
            print(f"✓ {agent['name']} is healthy")
            print("Health check response:", response)
        else:
            print(f"✗ {agent['name']} health check failed")
    
    print(f"\n=== Health Check Summary ===")
    print(f"Healthy agents: {healthy_count}/{total_agents} ({healthy_count/total_agents*100:.1f}%)")
    
    if healthy_count == total_agents:
        print("All agents are healthy and communicating properly!")
    else:
        print(f"{total_agents - healthy_count} agents are not responding properly.")

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
