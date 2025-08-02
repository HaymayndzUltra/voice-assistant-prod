import zmq
import threading
import time
import pytest
import os
import yaml

# IMPORTANT: This requires the ModelManagerAgent class to be importable.
from common.env_helpers import get_env
from main_pc_code.agents.model_manager_agent import ModelManagerAgent

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

@pytest.fixture(scope="module")
def mma_service():
    """
    Spins up the ModelManagerAgent in a separate thread for testing.
    """
    # Create a dummy config for the test
    config_path = str(PathManager.get_temp_dir() / "test_llm_config.yaml")
    with open(config_path, "w") as f:
        yaml.dump({
            'load_policy': {
                'fast': 'phi-3-mini-test',
                'quality': 'mistral-7b-test',
                'fallback': 'phi-2-test'
            },
            'models': {
                'phi-3-mini-test': {},
                'mistral-7b-test': {},
                'phi-2-test': {}
            }
        }, f)
    
    # Set environment variable for the agent to find the config
    os.environ['LLM_CONFIG_PATH'] = config_path
    os.environ['MODEL_MANAGER_PORT'] = '5588' # Use a test port

    agent = ModelManagerAgent(config_path=config_path)
    # agent.llm_config = agent._load_llm_config()  # Not needed, __init__ loads it
    thread = threading.Thread(target=agent.run, daemon=True)
    thread.start()
    
    # Give the server a moment to start
    time.sleep(0.5)
    
    yield
    
    # Teardown
    agent.running = False
    time.sleep(0.5)
    os.remove(config_path)
    del os.environ['LLM_CONFIG_PATH']
    del os.environ['MODEL_MANAGER_PORT']

def test_status_action(mma_service):
    """Tests the 'status' action to ensure it returns the correct structure."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5588")

    socket.send_json({"action": "status"})
    response = socket.recv_json()
    assert isinstance(response, dict)
    assert response.get('status') == 'ok'
    assert response.get('service') == 'ModelManagerAgent'
    assert 'known_models' in response and isinstance(response['known_models'], list), "known_models missing or not a list"
    assert 'phi-3-mini-test' in response['known_models'], "phi-3-mini-test not in known_models"
    assert 'load_policy' in response and isinstance(response['load_policy'], dict), "load_policy missing or not a dict"
    assert response['load_policy'].get('fast') == 'phi-3-mini-test', "load_policy['fast'] incorrect"

def test_generate_action(mma_service):
    """Tests the 'generate' action with different preferences."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5588")

    # Test 'fast' preference
    socket.send_json({"action": "generate", "model_pref": "fast", "prompt": "test"})
    response_fast = socket.recv_json()
    assert isinstance(response_fast, dict)
    assert response_fast['status'] == 'ok'
    assert response_fast['model_used'] == 'phi-3-mini-test'

    # Test 'quality' preference
    socket.send_json({"action": "generate", "model_pref": "quality", "prompt": "test"})
    response_quality = socket.recv_json()
    assert isinstance(response_quality, dict)
    assert response_quality['status'] == 'ok'
    assert response_quality['model_used'] == 'mistral-7b-test' 