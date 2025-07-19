import pytest
import threading
import time
import os
import yaml
import json
import zmq
from pathlib import Path

# Import the ModelManagerAgent and model_client for testing
from main_pc_code.agents.model_manager_agent import ModelManagerAgent
from main_pc_code.utils import model_client
from common.env_helpers import get_env

# Test port for the ModelManagerAgent
TEST_PORT = 5589

@pytest.fixture(scope="function")
def model_manager_agent():
    """
    Setup and teardown fixture for ModelManagerAgent.
    
    This fixture starts the ModelManagerAgent in a separate thread
    for each test function and cleans up after the test is complete.
    """
    # Create a temporary test directory
    test_dir = Path("/tmp/model_manager_test")
    test_dir.mkdir(exist_ok=True)
    
    # Create logs directory for the agent
    logs_dir = test_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create a test config file
    config_path = test_dir / "test_llm_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump({
            'load_policy': {
                'fast': 'phi-3-mini-128k-instruct',
                'quality': 'Mistral-7B-Instruct-v0.2',
                'fallback': 'phi-2'
            },
            'models': {
                'phi-3-mini-128k-instruct': {
                    'repo_id': 'microsoft/phi-3-mini-128k-instruct',
                    'type': 'huggingface'
                },
                'Mistral-7B-Instruct-v0.2': {
                    'repo_id': 'mistralai/Mistral-7B-Instruct-v0.2',
                    'type': 'huggingface'
                },
                'phi-2': {
                    'repo_id': 'TheBloke/phi-2-GGUF',
                    'filename': 'phi-2.Q4_0.gguf',
                    'type': 'gguf'
                }
            }
        }, f)
    
    # Set environment variables for testing
    os.environ['MODEL_MANAGER_PORT'] = str(TEST_PORT)
    os.environ['LLM_CONFIG_PATH'] = str(config_path)
    
    # Override model_client settings for testing
    original_host = model_client.MMA_HOST
    original_port = model_client.MMA_PORT
    original_address = model_client.MMA_ADDRESS
    model_client.MMA_PORT = str(TEST_PORT)
    model_client.MMA_ADDRESS = f"tcp://localhost:{TEST_PORT}"
    
    # Create and start the agent
    agent = ModelManagerAgent()
    agent_thread = threading.Thread(target=agent.run, daemon=True)
    agent_thread.start()
    
    # Give the agent time to start up
    time.sleep(1)
    
    yield agent
    
    # Cleanup
    agent.running = False
    time.sleep(0.5)  # Give the agent time to shut down
    
    # Restore model_client settings
    model_client.MMA_HOST = original_host
    model_client.MMA_PORT = original_port
    model_client.MMA_ADDRESS = original_address
    
    # Clean up test files
    if config_path.exists():
        config_path.unlink()
    
    # Remove environment variables
    if 'MODEL_MANAGER_PORT' in os.environ:
        del os.environ['MODEL_MANAGER_PORT']
    if 'LLM_CONFIG_PATH' in os.environ:
        del os.environ['LLM_CONFIG_PATH']


def test_status_endpoint(model_manager_agent):
    """
    Test the /status endpoint of the ModelManagerAgent.
    
    This test verifies that:
    1. The status endpoint returns a successful response
    2. The response contains loaded_models and routing_policy
    3. The routing_policy matches the config in llm_config.yaml
    """
    # Use model_client to get status
    response = model_client.get_status()
    
    # Verify the response structure
    assert response is not None, "Response should not be None"
    assert response.get('status') == 'ok', f"Expected status 'ok', got {response.get('status')}"
    
    # Verify the response contains the expected keys
    assert 'loaded_models' in response, "Response should contain loaded_models"
    assert 'routing_policy' in response, "Response should contain routing_policy"
    
    # Verify the routing policy matches the config
    routing_policy = response.get('routing_policy', {})
    assert routing_policy.get('fast') == 'phi-3-mini-128k-instruct', "Fast model should be phi-3-mini-128k-instruct"
    assert routing_policy.get('quality') == 'Mistral-7B-Instruct-v0.2', "Quality model should be Mistral-7B-Instruct-v0.2"
    assert routing_policy.get('fallback') == 'phi-2', "Fallback model should be phi-2"


def test_generate_endpoint_fast(model_manager_agent):
    """
    Test the /generate endpoint with the 'fast' model preference.
    
    This test verifies that:
    1. The generate endpoint returns a successful response
    2. The response contains the expected placeholder text
    3. The model_used field matches the 'fast' model in llm_config.yaml
    """
    # Use model_client to send a generate request
    test_prompt = "This is a test prompt for the fast model."
    response = model_client.generate(prompt=test_prompt, quality="fast")
    
    # Verify the response structure
    assert response is not None, "Response should not be None"
    assert response.get('status') == 'ok', f"Expected status 'ok', got {response.get('status')}"
    
    # Verify the response contains the expected fields
    assert 'response_text' in response, "Response should contain response_text"
    assert 'model_used' in response, "Response should contain model_used"
    
    # Verify the model_used matches the expected model
    assert response.get('model_used') == 'phi-3-mini-128k-instruct', \
        f"Expected model_used 'phi-3-mini-128k-instruct', got {response.get('model_used')}"
    
    # Verify the response contains the expected placeholder text
    response_text = response.get('response_text', '')
    assert test_prompt[:50] in response_text, "Response should contain the prompt"


def test_generate_endpoint_quality(model_manager_agent):
    """
    Test the /generate endpoint with the 'quality' model preference.
    
    This test verifies that:
    1. The generate endpoint returns a successful response
    2. The response contains the expected placeholder text
    3. The model_used field matches the 'quality' model in llm_config.yaml
    """
    # Use model_client to send a generate request
    test_prompt = "This is a test prompt for the quality model."
    response = model_client.generate(prompt=test_prompt, quality="quality")
    
    # Verify the response structure
    assert response is not None, "Response should not be None"
    assert response.get('status') == 'ok', f"Expected status 'ok', got {response.get('status')}"
    
    # Verify the response contains the expected fields
    assert 'response_text' in response, "Response should contain response_text"
    assert 'model_used' in response, "Response should contain model_used"
    
    # Verify the model_used matches the expected model
    assert response.get('model_used') == 'Mistral-7B-Instruct-v0.2', \
        f"Expected model_used 'Mistral-7B-Instruct-v0.2', got {response.get('model_used')}"
    
    # Verify the response contains the expected placeholder text
    response_text = response.get('response_text', '')
    assert test_prompt[:50] in response_text, "Response should contain the prompt"


def test_generate_endpoint_invalid_pref(model_manager_agent):
    """
    Test the /generate endpoint with an invalid model preference.
    
    This test verifies that:
    1. The generate endpoint handles invalid model preferences gracefully
    2. The response contains an error status and appropriate message
    """
    # Use model_client to send a generate request with an invalid preference
    test_prompt = "This is a test prompt with an invalid model preference."
    response = model_client.generate(prompt=test_prompt, quality="non_existent_pref")
    
    # Verify the response structure
    assert response is not None, "Response should not be None"
    
    # The current implementation should fall back to 'fast' model if preference is unknown
    # If this behavior changes to return an error, update this test accordingly
    if response.get('status') == 'error':
        # If error response, verify it contains an appropriate message
        assert 'message' in response, "Error response should contain a message"
        assert 'preference' in response.get('message', '').lower(), \
            "Error message should mention the preference"
    else:
        # If falling back to 'fast' model, verify the model_used is correct
        assert response.get('status') == 'ok', f"Expected status 'ok', got {response.get('status')}"
        assert response.get('model_used') == 'phi-3-mini-128k-instruct', \
            f"Expected fallback to 'phi-3-mini-128k-instruct', got {response.get('model_used')}"


def test_direct_zmq_communication(model_manager_agent):
    """
    Test direct ZMQ communication with the ModelManagerAgent.
    
    This test verifies that:
    1. Direct ZMQ requests to the agent work correctly
    2. Both status and generate actions return the expected responses
    """
    # Create a ZMQ socket for direct communication
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{TEST_PORT}")
    
    # Test status action
    socket.send_json({"action": "status"})
    status_response = socket.recv_json()
    
    # Verify status response
    assert status_response.get('status') == 'ok', "Status response should have 'ok' status"
    assert 'routing_policy' in status_response, "Status response should contain routing_policy"
    
    # Test generate action
    test_prompt = "Direct ZMQ test prompt"
    socket.send_json({
        "action": "generate",
        "model_pref": "fast",
        "prompt": test_prompt
    })
    generate_response = socket.recv_json()
    
    # Verify generate response
    assert generate_response.get('status') == 'ok', "Generate response should have 'ok' status"
    assert generate_response.get('model_used') == 'phi-3-mini-128k-instruct', \
        "Generate response should use the correct model"
    
    # Clean up
    socket.close()
    context.term()


if __name__ == "__main__":
    # This allows running the tests directly (useful for debugging)
    pytest.main(["-xvs", __file__]) 