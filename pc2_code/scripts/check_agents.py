import subprocess
import json
import zmq
import time
from pc2_code.config.system_config import pc2_settings
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env

def check_agent_health(agent_name, port):
    """Check agent health using ZMQ"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(get_zmq_connection_string({port}, "localhost")))
    
    try:
        socket.send_json({"action": "health_check"})
        socket.recv_json()
        return True
    except Exception as e:
        print(f"Health check failed for {agent_name}: {e}")
        return False
    finally:
        socket.close()
        context.term()

def start_agent(agent_script):
    """Start an agent process"""
    try:
        print(f"Starting {agent_script}...")
        subprocess.Popen(["python", agent_script], cwd="agents")
        time.sleep(2)  # Give some time to start
        return True
    except Exception as e:
        print(f"Failed to start {agent_script}: {e}")
        return False

def main():
    # List of agents to check
    agents = {
        "Translator Agent": "translator_agent.py --server",
        "NLLB Adapter": "llm_translation_adapter.py",
        "TinyLlama Service": "tinyllama_service_enhanced.py",
        "Unified Memory Reasoning": "unified_memory_reasoning_agent.py",
        "DreamWorld Agent": "DreamWorldAgent.py",
        "Learning Adjuster": "learning_adjuster_agent.py",
        "Cognitive Model": "CognitiveModelAgent.py",
        "GOT/TOT Agent": "got_tot_agent.py"
    }
    
    print("\n=== Starting Agent Health Check ===\n")
    
    for agent_name, script in agents.items():
        print(f"\n=== Checking {agent_name} ===")
        
        # Try to start the agent
        if start_agent(script):
            print(f"{agent_name} started successfully")
            
            # Check health after starting
            if agent_name == "Translator Agent":
                port = pc2_settings["model_configs"]["translator-agent-pc2"]["zmq_port"]
            elif agent_name == "NLLB Adapter":
                port = pc2_settings["model_configs"]["nllb-translation-adapter-pc2"]["zmq_port"]
            elif agent_name == "TinyLlama Service":
                port = pc2_settings["model_configs"]["tinyllama-service-pc2"]["zmq_port"]
            else:
                port = 5596  # Default port for other agents
                
            if check_agent_health(agent_name, port):
                print(f"✓ {agent_name} is healthy")
            else:
                print(f"✗ {agent_name} health check failed")
        else:
            print(f"✗ Failed to start {agent_name}")

if __name__ == "__main__":
    main()
