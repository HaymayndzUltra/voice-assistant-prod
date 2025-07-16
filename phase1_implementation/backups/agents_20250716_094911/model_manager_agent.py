from common.core.base_agent import BaseAgent

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path

def get_main_pc_code():
    """Get the path to the main_pc_code directory"""
    current_dir = Path(__file__).resolve().parent
    main_pc_code_dir = current_dir.parent
    return main_pc_code_dir

MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

"""
Model Manager / Resource Monitor Agent
- Tracks status and availability of all models
- Reports health to Task Router
- Provides model selection based on availability and task requirements
"""

class ModelManagerAgent(BaseAgent):
    """Model Manager Agent for handling model requests and managing resources."""
    
    def __init__(self, config_path=None, **kwargs):
        """Initialize the Model Manager Agent.
        
        Args:
            config_path: Path to configuration file
            **kwargs: Additional arguments to pass to BaseAgent
        """
        super().__init__(name="ModelManagerAgent", port=5570, **kwargs)
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        self.loaded_model_instances = {}
        self.model_last_used_timestamp = {}
        self.models = {}
        
    def handle_request(self, request):
        """Handle incoming requests.
        
        Args:
            request: The request to handle
            
        Returns:
            Response dictionary
        """
        if isinstance(request, dict):
            action = request.get("action")
            if action == "status":
                return {"status": "ok", "message": "Model Manager Agent is running"}
            elif action == "generate":
                return {"status": "ok", "response_text": "This is a mock response", "model_used": "mock_model"}
        return {"status": "error", "message": "Invalid request"}