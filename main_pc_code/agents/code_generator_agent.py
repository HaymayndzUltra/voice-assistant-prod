"""
Code Generator Agent
------------------
- Generates code based on natural language descriptions
- Supports multiple programming languages
- Integrates with the AutoGen framework
- Uses local LLMs for code generation
"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.path_manager import PathManager

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = PathManager.get_main_pc_code()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

import os
import uuid
import time
import zmq
import json
import logging
import traceback
import sys
import gc
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
import tempfile
import re
import threading


# Import path manager for containerization-friendly paths
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager

sys.path.insert(0, str(PathManager.get_project_root()))
from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from main_pc_code.utils.env_loader import get_env
# from main_pc_code.agents.gguf_model_manager import GGUFModelManager  # Optional dependency
from common.env_helpers import get_env

# Parse command line arguments
config = load_unified_config(str(Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"))

# Configure logging
log_file = PathManager.get_logs_dir() / str(PathManager.get_logs_dir() / "code_generator_agent.log")
log_file.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeGeneratorAgent")

MODEL_IDLE_TIMEOUT = 600  # seconds
model_last_used = {}

class CodeGeneratorAgent(BaseAgent):
    """Agent for generating code from natural language prompts. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    def __init__(self):
        # Standard BaseAgent initialization at the beginning
        self.config = load_unified_config(str(Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"))
        super().__init__(
            name=getattr(self.config, 'name', 'CodeGeneratorAgent'),
            port=getattr(self.config, 'port', 5708)
        )
        self.start_time = time.time()
        self.port = getattr(self.config, 'port', 5708)
        self.bind_address = getattr(self.config, 'bind_address', get_env('BIND_ADDRESS', '0.0.0.0'))
        self.zmq_timeout = int(getattr(self.config, 'zmq_request_timeout', 5000))
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        self.socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        self.logger = logger
        self.gguf_manager = None
        self.running = True
        # Initialize GGUF support if available
        try:
            self.gguf_manager = GGUFModelManager()
            self.logger.info("GGUF Model Manager initialized")
        except Exception as e:
            self.logger.warning(f"GGUF Model Manager not available: {e}")
            self.gguf_manager = None
        self.logger.info(f"Code Generator Agent initialized on port {self.port}")

    

        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
    def run(self):
        try:
            self.socket.bind(f"tcp://{self.bind_address}:{self.port}")
            self.logger.info(f"Code Generator Agent listening on port {self.port}")
            self.handle_requests()
        except Exception as e:
            self.logger.error(f"Failed to start Code Generator Agent: {e}")

    def handle_requests(self):
        self.logger.info("Ready to handle requests...")
        while self.running:
            try:
                message = self.socket.recv_string()
                self.logger.debug(f"Received message: {message[:100]}...")
                request = json.loads(message)
                action = request.get('action')
                response = {"status": "error", "error": "Unknown action"}
                self.logger.info(f"Handling action: {action}")
                if action == 'ping':
                    response = {"status": "success", "message": "pong", "timestamp": time.time()}
                elif action == 'health_check':
                    response = self._get_health_status()
                elif action == 'load_gguf_model':
                    model_id = request.get('model_id')
                    if not model_id:
                        response = {"status": "error", "error": "Missing model_id parameter"}
                    else:
                        response = self.load_gguf_model(model_id)
                elif action == 'unload_gguf_model':
                    model_id = request.get('model_id')
                    if not model_id:
                        response = {"status": "error", "error": "Missing model_id parameter"}
                    else:
                        response = self.unload_gguf_model(model_id)
                elif action == 'generate_with_gguf':
                    model_id = request.get('model_id')
                    prompt = request.get('prompt')
                    system_prompt = request.get('system_prompt')
                    max_tokens = request.get('max_tokens', 1024)
                    temperature = request.get('temperature', 0.7)
                    if not model_id or not prompt:
                        response = {"status": "error", "error": "Missing required parameters"}
                    else:
                        response = self.generate_with_gguf(
                            model_id=model_id,
                            prompt=prompt,
                            system_prompt=system_prompt,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )
                elif action == 'get_gguf_status':
                    if self.gguf_manager:
                        try:
                            models = self.gguf_manager.list_models()
                            status = {}
                            for model in models:
                                model_id = model.get('model_id')
                                status[model_id] = 'loaded' if model.get('loaded', False) else 'unloaded'
                            response = {
                                "status": "success",
                                "models": status,
                                "timestamp": time.time()
                            }
                        except Exception as e:
                            self.logger.error(f"Error getting GGUF model status: {e}")
                            response = {"status": "error", "error": str(e)}
                    else:
                        response = {
                            "status": "error",
                            "error": "GGUF manager not available",
                            "timestamp": time.time()
                        }
                elif action == 'list_gguf_models':
                    if self.gguf_manager:
                        try:
                            models = self.gguf_manager.list_models()
                            response = {
                                "status": "success",
                                "models": models,
                                "timestamp": time.time()
                            }
                        except Exception as e:
                            self.logger.error(f"Error listing GGUF models: {e}")
                            response = {"status": "error", "error": str(e)}
                    else:
                        response = {
                            "status": "error",
                            "error": "GGUF manager not available",
                            "timestamp": time.time()
                        }
                elif action == 'generate':
                    model = request.get('model')
                    prompt = request.get('prompt')
                    request_id = request.get('request_id', f"gen_{int(time.time())}")
                    self.logger.info(f"Ollama generation request (ID: {request_id}): model={model}, prompt_len={len(prompt) if prompt else 0}")
                    if not model or not prompt:
                        response = {"status": "error", "error": "Missing model or prompt parameter"}
                    else:
                        try:
                            import requests
                            ollama_url = "http://localhost:11434/api/generate"
                            ollama_request = {
                                "model": model,
                                "prompt": prompt,
                            }
                            self.logger.info(f"Sending request to Ollama API: {model}")
                            ollama_response = requests.post(ollama_url, json=ollama_request)
                            if ollama_response.status_code == 200:
                                result = ollama_response.json()
                                generated_text = result.get('response', '')
                                code_blocks = re.findall(r'```(?:\w+)?\n([\s\S]*?)```', generated_text)
                                code = code_blocks[0] if code_blocks else generated_text
                                response = {
                                    "status": "success",
                                    "code": code,
                                    "full_response": generated_text,
                                    "model": model,
                                    "request_id": request_id
                                }
                            else:
                                response = {
                                    "status": "error",
                                    "error": f"Ollama API error: {ollama_response.status_code} {ollama_response.text}",
                                    "request_id": request_id
                                }
                        except ImportError as e:
                            self.logger.error(f"Import error: {e}")
                            response = {"status": "error", "error": f"Import error: {str(e)}"}
                        except Exception as e:
                            self.logger.error(f"Error generating with Ollama: {e}")
                            response = {"status": "error", "error": f"Error: {str(e)}"}
                elif action == 'generate_code':
                    description = request.get('description', '')
                    language = request.get('language')
                    use_voting = request.get("use_voting", False)
                    save_to_file = request.get("save_to_file", True)
                    model_id = request.get('model_id')
                    request_id = request.get('request_id', f"gen_{int(time.time())}")
                    self.logger.info(f"Code generation request (ID: {request_id}): desc len={len(description)}, lang={language}, model_id={model_id}")
                    if not description:
                        response = {"status": "error", "error": "Missing description parameter"}
                    else:
                        response = self.forward_to_model_manager({
                            "request_type": "generate_code",
                            "description": description,
                            "language": language,
                            "use_voting": use_voting,
                            "save_to_file": save_to_file,
                            "model_id": model_id,
                            "request_id": request_id
                        })
                self.logger.debug(f"Sending response: {response}")
                self.socket.send_string(json.dumps(response))
            except Exception as e:
                self.logger.error(f"Error handling request: {e}")
                try:
                    self.socket.send_string(json.dumps({"status": "error", "error": str(e)}))
                except:
                    pass

    def load_gguf_model(self, model_id):
        if not self.gguf_manager:
            return {"status": "error", "error": "GGUF manager not available"}
        try:
            result = self.gguf_manager.load_model(model_id)
            return result
        except Exception as e:
            self.logger.error(f"Error loading GGUF model {model_id}: {e}")
            return {"status": "error", "error": str(e)}

    def unload_gguf_model(self, model_id):
        if not self.gguf_manager:
            return {"status": "error", "error": "GGUF manager not available"}
        try:
            result = self.gguf_manager.unload_model(model_id)
            return result
        except Exception as e:
            self.logger.error(f"Error unloading GGUF model {model_id}: {e}")
            return {"status": "error", "error": str(e)}

    def generate_with_gguf(self, model_id, prompt, system_prompt=None, max_tokens=1024, temperature=0.7):
        if not self.gguf_manager:
            return {"status": "error", "error": "GGUF manager not available"}
        try:
            self._update_model_usage(model_id)
            models = self.gguf_manager.list_models()
            model_loaded = False
            for model in models:
                if model.get('model_id') == model_id and model.get('loaded', False):
                    model_loaded = True
                    break
            if not model_loaded:
                load_success = self.gguf_manager.load_model(model_id)
                if not load_success:
                    return {"status": "error", "error": f"Failed to load model {model_id}"}
            result = self.gguf_manager.generate_text(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return result
        except Exception as e:
            self.logger.error(f"Error generating with GGUF model {model_id}: {e}")
            return {"status": "error", "error": str(e)}

    def forward_to_model_manager(self, request):
        import zmq
        import psutil
        from datetime import datetime
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        socket.setsockopt(zmq.RCVTIMEO, 60000)
        try:
            self.logger.info(f"Connecting to Model Manager at {self.model_manager_address}")
            task_router_address = self.model_manager_address.replace("5556", "8570")
            socket.connect(task_router_address)
            self.logger.info(f"Forwarding request to Model Manager: {request}")
            socket.send_string(json.dumps(request))
            self.logger.info("Waiting for response from Model Manager...")
            response_str = socket.recv_string()
            response = json.loads(response_str)
            self.logger.info(f"Received response from Model Manager: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Error forwarding to Model Manager: {e}")
            return {"status": "error", "error": f"Error communicating with Model Manager: {e}"}
        finally:
            socket.close()
            context.term()

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'code_generator',
            'components': {
                'gguf_manager': self.gguf_manager is not None,
                'socket_bound': hasattr(self, 'socket'),
            },
            'status_detail': 'active',
            'uptime': time.time() - self.start_time
        }

    def cleanup(self):
        """Gracefully shutdown the agent"""
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        super().cleanup()
        self.logger.info("CodeGeneratorAgent cleanup complete")

# Example usage
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = CodeGeneratorAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()