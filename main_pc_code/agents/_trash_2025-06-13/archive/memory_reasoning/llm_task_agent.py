from main_pc_code.src.core.base_agent import BaseAgent
"""
LLM Task Agent
-------------
Manages LLM integration and task memory for the voice assistant system.
Handles:
- LLM model management and switching
- Task learning and adaptation
- Context management
- Natural language understanding
"""

import os
import sys
import json
import time
import logging
import threading
import queue
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import task memory
from web_automation.utils.task_memory import TaskMemory
import psutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "llm_task_agent.log")))
    ]
)
logger = logging.getLogger('LLMTaskAgent')

class LLMTaskAgent(BaseAgent):
    """Agent for managing LLM integration and task memory"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="LlmTaskAgent")
        # Initialize task memory
        self.task_memory = TaskMemory()
        
        # Initialize LLM models
        self.models = {
            "primary": None,  # GPT-4
            "secondary": None,  # Local LLM
            "fallback": None   # Smaller model
        }
        
        # Initialize queues
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        
        # Initialize locks
        self._model_lock = threading.Lock()
        self._memory_lock = threading.Lock()
        
        # Initialize state
        self.running = False
        self.current_model = "primary"
        
        # Load models
        self._load_models()
        
        # Connect signals
        self._connect_signals()
        
    def _load_models(self):
        """Load LLM models"""
        try:
            # Load primary model (GPT-4)
            self.models["primary"] = self._load_gpt4()
            
            # Load secondary model (Local LLM)
            self.models["secondary"] = self._load_local_llm()
            
            # Load fallback model
            self.models["fallback"] = self._load_fallback_model()
            
            logger.info("Successfully loaded all models")
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            raise
            
    def _load_gpt4(self):
        """Load GPT-4 model"""
        try:
            # TODO: Implement GPT-4 loading
            return None
        except Exception as e:
            logger.error(f"Error loading GPT-4: {str(e)}")
            return None
            
    def _load_local_llm(self):
        """Load local LLM model"""
        try:
            # TODO: Implement local LLM loading
            return None
        except Exception as e:
            logger.error(f"Error loading local LLM: {str(e)}")
            return None
            
    def _load_fallback_model(self):
        """Load fallback model"""
        try:
            # TODO: Implement fallback model loading
            return None
        except Exception as e:
            logger.error(f"Error loading fallback model: {str(e)}")
            return None
            
    def _connect_signals(self):
        """Connect task memory signals"""
        self.task_memory.task_learned.connect(self._handle_task_learned)
        self.task_memory.task_triggered.connect(self._handle_task_triggered)
        self.task_memory.memory_updated.connect(self._handle_memory_updated)
        self.task_memory.behavior_updated.connect(self._handle_behavior_updated)
        self.task_memory.adaptation_learned.connect(self._handle_adaptation_learned)
        self.task_memory.error_occurred.connect(self._handle_error)
        
    def _handle_task_learned(self, trigger: str, action: str):
        """Handle newly learned task"""
        logger.info(f"Learned new task: {trigger} -> {action}")
        
    def _handle_task_triggered(self, trigger: str, action: str):
        """Handle triggered task"""
        logger.info(f"Triggered task: {trigger} -> {action}")
        
    def _handle_memory_updated(self, memory: dict):
        """Handle memory update"""
        logger.info("Memory updated")
        
    def _handle_behavior_updated(self, old_behavior: str, new_behavior: str):
        """Handle behavior update"""
        logger.info(f"Behavior updated: {old_behavior} -> {new_behavior}")
        
    def _handle_adaptation_learned(self, pattern: str, adaptation: str):
        """Handle learned adaptation"""
        logger.info(f"Learned adaptation: {pattern} -> {adaptation}")
        
    def _handle_error(self, error: str):
        """Handle error"""
        logger.error(f"Error: {error}")
        
    def process_command(self, command: str) -> str:
        """Process a command using LLM and task memory"""
        try:
            # Add command to queue
            self.command_queue.put(command)
            
            # Get response from queue
            response = self.response_queue.get(timeout=30)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            return f"Error: {str(e)}"
            
    def _process_command_internal(self, command: str):
        """Internal command processing"""
        try:
            # First check task memory
            if self.task_memory.process_command(command):
                return
                
            # If not in task memory, use LLM
            with self._model_lock:
                model = self.models[self.current_model]
                if model:
                    response = self._generate_response(model, command)
                else:
                    response = "No model available"
                    
            # Add response to queue
            self.response_queue.put(response)
            
        except Exception as e:
            logger.error(f"Error in internal command processing: {str(e)}")
            self.response_queue.put(f"Error: {str(e)}")
            
    def _generate_response(self, model: Any, command: str) -> str:
        """Generate response using LLM"""
        try:
            # TODO: Implement LLM response generation
            return "Response from LLM"
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: {str(e)}"
            
    def switch_model(self, model_name: str):
        """Switch to different LLM model"""
        with self._model_lock:
            if model_name in self.models:
                self.current_model = model_name
                logger.info(f"Switched to model: {model_name}")
            else:
                logger.error(f"Model not found: {model_name}")
                
    def start(self):
        """Start the agent"""
        self.running = True
        
        # Start command processing thread
        self.command_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.command_thread.start()
        
        logger.info("LLM Task Agent started")
        
    def stop(self):
        """Stop the agent"""
        self.running = False
        
        # Stop command processing thread
        if hasattr(self, 'command_thread'):
            self.command_thread.join()
            
        # Clean up task memory
        self.task_memory.cleanup()
        
        logger.info("LLM Task Agent stopped")
        
    def _process_commands(self):
        """Process commands from queue"""
        while self.running:
            try:
                command = self.command_queue.get(timeout=1)
                self._process_command_internal(command)
                self.command_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing command: {str(e)}")
                

    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

def main():
    """Main function"""
    try:
        # Create agent
        agent = LLMTaskAgent()
        
        # Start agent
        agent.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        if 'agent' in locals():
            agent.stop()
            
if __name__ == "__main__":
    main() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise