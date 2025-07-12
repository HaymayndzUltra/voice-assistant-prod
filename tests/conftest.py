"""
Test configuration for the AI System
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add mock implementations for problematic imports
class MockGGUFManager:
    def load_model(self, model_id):
        return True
    
    def generate_text(self, **kwargs):
        return {"text": "dummy response"}

@pytest.fixture(autouse=True)
def mock_gguf_manager(monkeypatch):
    """Mock the gguf_model_manager module completely to avoid importing it"""
    # Create a mock module with the get_instance function
    mock_module = MagicMock()
    mock_module.get_instance.return_value = MockGGUFManager()
    
    # Add the mock module to sys.modules
    sys.modules['main_pc_code.agents.gguf_model_manager'] = mock_module
    
    # No need to use monkeypatch.setattr since we're directly replacing the module
    yield
    
    # Clean up after the test
    if 'main_pc_code.agents.gguf_model_manager' in sys.modules:
        del sys.modules['main_pc_code.agents.gguf_model_manager']

# Mock for the ModelManagerAgent to use in tests
class MockModelManagerAgent:
    def __init__(self, **kwargs):
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        self.loaded_model_instances = {}
        self.model_last_used_timestamp = {}
        self.models = {}
        
    def handle_request(self, request):
        """Mock handle_request method"""
        if request.get("action") == "status":
            return {"status": "ok", "message": "Mock status response"}
        elif request.get("action") == "generate":
            return {"status": "ok", "response_text": "Mock generated text"}
        return {"status": "error", "message": "Unknown action"}
        
    def select_model(self, task_type, context_size=None):
        """Mock select_model method"""
        return "mock_model"
        
    def load_model(self, model_id):
        """Mock load_model method"""
        self.loaded_models[model_id] = True
        return True
        
    def unload_model(self, model_id):
        """Mock unload_model method"""
        if model_id in self.loaded_models:
            del self.loaded_models[model_id]
        return True
        
    def health_check(self):
        """Mock health_check method"""
        return {"status": "healthy"}
        
    def cleanup(self):
        """Mock cleanup method"""
        pass 