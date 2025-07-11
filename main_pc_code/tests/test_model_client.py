import pytest
import zmq
import threading
import time
from unittest.mock import patch

# The module we are testing
from main_pc_code.utils import model_client

@pytest.fixture
def mock_mma_server():
    """A mock ZMQ REP server to simulate the ModelManagerAgent."""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5599") # Use a dedicated test port for the mock

    def server_task():
        while True:
            try:
                request = socket.recv_json()
                if not isinstance(request, dict):
                    # Ignore or close if not a dict
                    socket.send_json({"status": "error", "message": "Malformed request"})
                    continue
                if request.get("action") == "generate":
                    response = {
                        "status": "ok",
                        "model_used": f"mock_{request.get('model_pref')}",
                        "response_text": "Mocked response."
                    }
                    socket.send_json(response)
                elif request.get("action") == "status":
                    socket.send_json({"status": "ok", "service": "MockMMA"})
                else:
                    socket.send_json({"status": "error", "message": "Unknown action"})
            except zmq.ContextTerminated:
                break # Exit loop when context is terminated
    
    thread = threading.Thread(target=server_task, daemon=True)
    thread.start()

    yield

    socket.close()
    context.term()


@patch.dict(model_client.os.environ, {"MODEL_MANAGER_PORT": "5599"})
def test_generate_success(mock_mma_server):
    """Test the happy path for the generate function."""
    response = model_client.generate("Hello", quality="fast")
    assert response['status'] == 'ok'
    assert response['model_used'] == 'mock_fast'
    assert response['response_text'] == 'Mocked response.'


@patch.dict(model_client.os.environ, {"MODEL_MANAGER_PORT": "5599"})
def test_get_status_success(mock_mma_server):
    """Test the happy path for the get_status function."""
    response = model_client.get_status()
    assert response['status'] == 'ok'
    assert response['service'] == 'MockMMA'

@patch.dict(model_client.os.environ, {"MODEL_MANAGER_PORT": "6000"}) # A port where nothing is listening
def test_generate_timeout_and_retry():
    """Test that the client handles timeouts and returns an error."""
    # Patch the timeout to be very short for a quick test
    with patch.object(model_client, 'REQUEST_TIMEOUT', 100), \
         patch.object(model_client, 'REQUEST_RETRIES', 2):
        
        start_time = time.time()
        response = model_client.generate("test timeout")
        end_time = time.time()

        # Check that it returned an error
        assert response['status'] == 'error'
        assert "Failed to communicate" in response['message']
        
        # Check that it actually tried to retry (took longer than one timeout)
        assert (end_time - start_time) > 0.2 # 2 retries * 100ms timeout 