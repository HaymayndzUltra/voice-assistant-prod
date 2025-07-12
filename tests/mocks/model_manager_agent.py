"""Mock implementation of ModelManagerAgent for testing purposes"""

class ModelManagerAgent:
    """Mock ModelManagerAgent class for testing"""
    
    def __init__(self, config_path=None, **kwargs):
        self.config = {}
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        self.loaded_model_instances = {}
        
    def handle_request(self, request):
        """Mock handle_request method"""
        return {"status": "success", "message": "Mock response"}
        
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