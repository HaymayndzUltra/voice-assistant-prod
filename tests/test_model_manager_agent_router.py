import threading
import time
import zmq
import pytest

from main_pc_code.model_manager_suite import get_instance as get_model_manager_instance

# Use a high-numbered port to avoid collisions
TEST_PORT = 5950

@pytest.fixture(scope="module")
def mma_agent():
    """Start ModelManagerAgent in background thread for tests."""
    agent = ModelManagerAgent()
    # Force ZMQ to default to inproc for direct handler tests to avoid port binding issues.
    # Instead of running agent.run() (infinite), we expose its handle_request directly.
    yield agent
    # No cleanup needed for direct method calls


def test_status_action(mma_agent):
    response = mma_agent.handle_request({"action": "status"})
    assert isinstance(response, dict)
    assert response.get("status") in {"ok", "SUCCESS", "success"}


def test_generate_action_placeholder(mma_agent, monkeypatch):
    """Patch GGUF manager so test does not depend on llama-cpp availability."""
    # Dummy GGUF manager mock
    class _DummyGGUF:
        def load_model(self, model_id):
            return True
        def generate_text(self, **kwargs):
            return {"text": "dummy response"}
    monkeypatch.setattr(
        "main_pc_code.agents.gguf_model_manager.get_instance",
        lambda: _DummyGGUF(),
        raising=True,
    )

    req = {"action": "generate", "model_pref": "fast", "prompt": "Hello"}
    resp = mma_agent.handle_request(req)
    assert resp.get("status") == "ok"
    assert "response_text" in resp 