import sys
sys.argv = [sys.argv[0]]
import pytest
import time
import zmq
import threading
import os
import socket
import importlib
import logging

# Configure logging for the test
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_pilot_migration")

# Helper to find a free port
def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]

@pytest.fixture
def mock_mma_server():
    """A mock ZMQ REP server to simulate the ModelManagerAgent on a free port."""
    port = _get_free_port()
    os.environ['MODEL_MANAGER_PORT'] = str(port)
    os.environ['MODEL_MANAGER_HOST'] = 'localhost'
    
    # Use a specific context for the test
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://localhost:{port}")
    logger.info(f"Mock server bound to port {port}")
    
    # Use an event to signal when server is ready
    ready_event = threading.Event()
    stop_event = threading.Event()

    def server_task():
        logger.info("Mock server thread started")
        ready_event.set()  # Signal that the server is ready
        
        while not stop_event.is_set():
            try:
                if socket.poll(100, zmq.POLLIN):
                    request = socket.recv_json()
                    logger.info(f"Mock server received request: {request}")
                    
                    if isinstance(request, dict) and request.get("action") == "generate":
                        response = {
                            "status": "ok",
                            "model_used": "mock_fast_model",
                            "response_text": "DUMMY_ANALYSIS_RESULT"
                        }
                        logger.info(f"Mock server sending response: {response}")
                        socket.send_json(response)
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error in mock server: {e}")
                break
            except Exception as e:
                logger.error(f"Error in mock server: {e}")
                break

    thread = threading.Thread(target=server_task, daemon=True)
    thread.start()
    
    # Wait for the server to be ready
    ready_event.wait(timeout=5)
    time.sleep(0.5)  # Give a bit more time for ZMQ socket to be fully ready
    
    yield port
    
    # Clean up
    stop_event.set()
    thread.join(timeout=1)
    socket.close()
    context.term()
    logger.info("Mock server cleaned up")


def test_sla_migration_and_performance(mock_mma_server):
    """Integration & performance test for StreamingLanguageAnalyzer using model_client."""
    # Reload model_client after setting env so it picks up the new port
    from main_pc_code.utils import model_client as mc
    importlib.reload(mc)
    
    # Log the actual address being used
    logger.info(f"Model client will connect to: {mc.MMA_ADDRESS}")
    
    # Patch the analyzer module reference to use reloaded client
    from main_pc_code.agents import streaming_language_analyzer as sla_mod
    sla_mod.model_client = mc
    
    # Monkeypatch the __init__ to avoid heavy initialization
    original_analyze = sla_mod.StreamingLanguageAnalyzer.analyze_with_llm
    def light_init(self):
        self.context = zmq.Context()  # Minimal context needed for the test
        logger.info("Using light initialization for StreamingLanguageAnalyzer")
    
    sla_mod.StreamingLanguageAnalyzer.__init__ = light_init

    # Create the agent with the light init
    sla_agent = sla_mod.StreamingLanguageAnalyzer()
    
    # Bind the analyze method
    sla_agent.analyze_with_llm = original_analyze.__get__(sla_agent)

    test_prompt = "This is a test sentence."

    # Add a small delay to ensure everything is ready
    time.sleep(0.5)
    
    # Test the analyze_with_llm method
    start_time = time.perf_counter()
    response = sla_agent.analyze_with_llm(test_prompt)
    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    print(f"\n[Performance] Pilot Migration Latency: {latency_ms:.2f} ms")
    logger.info(f"Response from analyze_with_llm: {response}")

    assert response is not None
    assert response == "DUMMY_ANALYSIS_RESULT"
    assert latency_ms < 1000, "Latency is unexpectedly high for a local stubbed call." 