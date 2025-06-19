"""
Code Generator Agent
- Generates code based on natural language descriptions
- Supports multiple programming languages
- Integrates with the AutoGen framework
- Uses local LLMs for code generation
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading
import tempfile
import re

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "code_generator_agent.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeGeneratorAgent")

# Get ZMQ ports from config
CODE_GENERATOR_PORT = config.get('zmq.code_generator_port', 5605)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)
EXECUTOR_PORT = config.get('zmq.executor_port', 5603)

class CodeGeneratorAgent:
    """Agent for code generation"""
    def __init__(self):
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.bind(f"tcp://0.0.0.0:{CODE_GENERATOR_PORT}")
        logger.info(f"Code Generator Agent bound to port {CODE_GENERATOR_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on port {MODEL_MANAGER_PORT}")
        
        # Socket to communicate with autogen framework
        self.framework = self.context.socket(zmq.REQ)
        self.framework.connect(f"tcp://localhost:{AUTOGEN_FRAMEWORK_PORT}")
        logger.info(f"Connected to AutoGen Framework on port {AUTOGEN_FRAMEWORK_PORT}")
        
        # Socket to communicate with executor agent
        self.executor = self.context.socket(zmq.REQ)
        self.executor.connect(f"tcp://localhost:{EXECUTOR_PORT}")
        logger.info(f"Connected to Executor Agent on port {EXECUTOR_PORT}")
        
        # Setup output directory
        self.output_dir = Path(config.get('system.output_dir', 'output')) / "code"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Language templates
        self.language_templates = {
            "python": {
                "file_extension": ".py",
                "comment_prefix": "#",
                "imports_section": "# Import necessary libraries\n",
                "main_section": "\n\n# Main function\ndef main():\n    pass\n\n# Run the main function if this script is executed directly\nif __name__ == \"__main__\":\n    main()\n"
            },
            "javascript": {
                "file_extension": ".js",
                "comment_prefix": "//",
                "imports_section": "// Import necessary libraries\n",
                "main_section": "\n\n// Main function\nfunction main() {\n    \n}\n\n// Run the main function\nmain();\n"
            },
            "java": {
                "file_extension": ".java",
                "comment_prefix": "//",
                "imports_section": "// Import necessary libraries\n",
                "main_section": "\n\npublic class Main {\n    public static void main(String[] args) {\n        \n    }\n}\n"
            },
            "c#": {
                "file_extension": ".cs",
                "comment_prefix": "//",
                "imports_section": "// Import necessary libraries\nusing System;\n",
                "main_section": "\n\npublic class Program {\n    public static void Main(string[] args) {\n        \n    }\n}\n"
            },
            "c++": {
                "file_extension": ".cpp",
                "comment_prefix": "//",
                "imports_section": "// Import necessary libraries\n#include <iostream>\n",
                "main_section": "\n\nint main() {\n    \n    return 0;\n}\n"
            },
            "html": {
                "file_extension": ".html",
                "comment_prefix": "<!--",
                "comment_suffix": "-->",
                "imports_section": "",
                "main_section": "<!DOCTYPE html>\n<html>\n<head>\n    <title>Generated Page</title>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n</head>\n<body>\n    \n</body>\n</html>\n"
            }
        }
        
        # Running flag
        self.running = True
        
        logger.info("Code Generator Agent initialized")
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None, model: str = "deepseek") -> str:
        """Send a request to the LLM through the model manager"""
        try:
            # Prepare request
            request = {
                "request_type": "generate",
                "model": model,  # Use DeepSeek Coder for code generation by default
                "prompt": prompt,
                "temperature": 0.2  # Lower temperature for more deterministic code generation
            }
            
            if system_prompt:
                request["system_prompt"] = system_prompt
            
            # Send request to model manager
            self.model_manager.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.model_manager, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
                response_str = self.model_manager.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    return response["text"]
                else:
                    logger.error(f"Error from model manager: {response.get('error', 'Unknown error')}")
                    raise Exception(response.get("error", "Unknown error"))
            else:
                logger.error("Timeout waiting for response from model manager")
                raise Exception("Timeout waiting for response from model manager")
        
        except Exception as e:
            logger.error(f"Error sending to LLM: {str(e)}")
            raise
    
    def _execute_code(self, code: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code using the executor agent"""
        try:
            # Prepare request
            request = {
                "request_type": "execute",
                "code": code,
                "parameters": parameters or {}
            }
            
            # Send request to executor agent
            self.executor.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.executor, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
                response_str = self.executor.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    return response["result"]
                else:
                    logger.error(f"Error from executor agent: {response.get('error', 'Unknown error')}")
                    raise Exception(response.get("error", "Unknown error"))
            else:
                logger.error("Timeout waiting for response from executor agent")
                raise Exception("Timeout waiting for response from executor agent")
        
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            raise
    
    def _save_code_to_file(self, code: str, language: str, filename: Optional[str] = None) -> str:
        """Save code to a file"""
        # Get file extension for the language
        file_extension = self.language_templates.get(language.lower(), {}).get("file_extension", ".txt")
        
        # Generate filename if not provided
        if not filename:
            timestamp = int(time.time())
            filename = f"generated_code_{timestamp}{file_extension}"
        elif not filename.endswith(file_extension):
            filename = f"{filename}{file_extension}"
        
        # Save code to file
        file_path = self.output_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        
        logger.info(f"Saved code to {file_path}")
        
        return str(file_path)
    
    def _detect_language_from_description(self, description: str) -> str:
        """Detect programming language from description"""
        description_lower = description.lower()
        
        # Check for explicit language mentions
        if "python" in description_lower:
            return "python"
        elif "javascript" in description_lower or "js" in description_lower:
            return "javascript"
        elif "java" in description_lower and "javascript" not in description_lower:
            return "java"
        elif "c#" in description_lower or "csharp" in description_lower:
            return "c#"
        elif "c++" in description_lower or "cpp" in description_lower:
            return "c++"
        elif "html" in description_lower:
            return "html"
        
        # Default to Python if no language is specified
        return "python"
    
    def _extract_code_from_llm_response(self, response: str) -> str:
        """Extract code from LLM response"""
        # Try to extract code from markdown code blocks
        code_block_pattern = r"```(?:\w+)?\s*([\s\S]*?)```"
        code_blocks = re.findall(code_block_pattern, response)
        
        if code_blocks:
            # Join all code blocks
            return "\n\n".join(code_blocks)
        else:
            # If no code blocks found, return the entire response
            return response

    def generate_code(self, description: str, language: Optional[str] = None, save_to_file: bool = True) -> Dict[str, Any]:
        """Generate code based on description"""
        logger.info("Generating code from description")
        if not language:
            language = self._detect_language_from_description(description)
        prompt = f"""Generate {language or 'code'} for the following task:\n{description}"""
        response = self._send_to_llm(prompt, model=language or "deepseek")
        code = self._extract_code_from_llm_response(response)
        if save_to_file:
            filename = self._save_code_to_file(code, language)
        else:
            filename = None
        return {
            "code": code,
            "language": language,
            "filename": filename
        }

    def fix_code(self, code: str, error: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Fix code based on error feedback"""
        logger.info("Fixing code based on error feedback")
        if not language:
            language = self._detect_language_from_description(code)
        prompt = (
            f"The following {language or 'code'} has an error.\n"
            f"Error message: {error}\n"
            f"Please fix the code below so it works correctly.\n"
            f"---\n"
            f"{code}\n"
            f"---\n"
            f"Return only the fixed code."
        )
        response = self._send_to_llm(prompt, model=language or "deepseek")
        fixed_code = self._extract_code_from_llm_response(response)
        return {
            "fixed_code": fixed_code,
            "language": language
        }

    def handle_requests(self):
        """Handle incoming requests"""
        # Aggressive auto-offload/auto-load logic
        import threading
        self._model_lock = threading.Lock()
        self._last_activity = time.time()
        self._idle_timeout = 30  # 30s default for codegen

        def _offload_model():
            with self._model_lock:
                if hasattr(self, 'model') and self.model is not None:
                    logger.info("[Auto-Offload] Unloading codegen model to save VRAM...")
                    self.model = None

        def _maybe_reload_model():
            with self._model_lock:
                if not hasattr(self, 'model') or self.model is None:
                    logger.info("[Auto-Load] Reloading codegen model on demand...")
                    self.model = self._load_model() if hasattr(self, '_load_model') else None

        # Background thread to monitor idle timeout
        def _idle_monitor():
            while self.running:
                time.sleep(1)
                if time.time() - self._last_activity > self._idle_timeout:
                    _offload_model()
        threading.Thread(target=_idle_monitor, daemon=True).start()

        while self.running:
            try:
                # Wait for request
                request_str = self.receiver.recv_string()
                request = json.loads(request_str)

                # Reload model if needed
                _maybe_reload_model()
                self._last_activity = time.time()

                # Handle request
                if request["request_type"] == "generate":
                    use_voting = request.get("use_voting", False)
                    response = self.generate_code(
                        request["description"],
                        request.get("language"),
                        request.get("save_to_file", True),
                        use_voting=use_voting
                    )
                elif request["request_type"] == "fix":
                    use_voting = request.get("use_voting", False)
                    response = self.fix_code(
                        request["code"],
                        request["error"],
                        request.get("language"),
                        use_voting=use_voting
                    )
                elif request["request_type"] == "execute":
                    response = self._execute_code(request["code"], request.get("parameters"))
                else:
                    response = {
                        "status": "error",
                        "error": "Unknown request type"
                    }
                
                # Send response
                self.receiver.send_string(json.dumps(response))
            
            except json.JSONDecodeError:
                response = {
                    "status": "error",
                    "error": "Invalid JSON in request"
                }
                self.receiver.send_string(json.dumps(response))
            except Exception as e:
                response = {
                    "status": "error",
                    "error": f"Error processing request: {str(e)}"
                }
                self.receiver.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in request handler: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the code generator agent"""
        try:
            # Register with AutoGen framework
            self.framework.send_string(json.dumps({
                "request_type": "register_agent",
                "agent_id": "code_generator",
                "endpoint": f"tcp://localhost:{CODE_GENERATOR_PORT}",
                "capabilities": ["code_generation"]
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
            response = json.loads(response_str)
            
            if response["status"] != "success":
                logger.error(f"Error registering with AutoGen framework: {response.get('error', 'Unknown error')}")
            else:
                logger.info("Registered with AutoGen framework")
            
            # Main request handling loop
            self.handle_requests()
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        # Unregister from AutoGen framework
        try:
            self.framework.send_string(json.dumps({
                "request_type": "unregister_agent",
                "agent_id": "code_generator"
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
        except:
            pass
        
        self.receiver.close()
        self.model_manager.close()
        self.framework.close()
        self.executor.close()
        self.context.term()
        
        logger.info("Code Generator Agent stopped")


    def generate_with_voting(self, description: str, language: Optional[str] = None, save_to_file: bool = True, models: Optional[list] = None, voting_mode: str = "first_pass") -> dict:
        """
        Generate code using multiple models and select the best result via voting.
        voting_mode: 'first_pass' (return first that passes execution), 'majority' (if testable), or 'all' (return all outputs)
        """
        logger.info("Generating code with model voting...")
        if not language:
            language = self._detect_language_from_description(description)
        prompt = f"""Generate {language or 'code'} for the following task:\n{description}"""
        # Default model list
        if models is None:
            models = ["deepseek", "phi3", "llama3", "mistral", "codellama", "wizardcoder"]
        results = []
        for model in models:
            try:
                response = self._send_to_llm(prompt, model=model)
                code = self._extract_code_from_llm_response(response)
                exec_result = self._execute_code(code) if language == "python" else {"success": None, "error": None}
                results.append({
                    "model": model,
                    "code": code,
                    "exec_result": exec_result
                })
            except Exception as e:
                logger.error(f"Model {model} failed: {str(e)}")
                results.append({
                    "model": model,
                    "code": None,
                    "exec_result": {"success": False, "error": str(e)}
                })
        # Voting/selection logic
        best = None
        for res in results:
            if res["exec_result"].get("success"):
                best = res
                break
        if not best:
            best = results[0]  # fallback: first output
        filename = self._save_code_to_file(best["code"], language) if save_to_file and best["code"] else None
        return {
            "code": best["code"],
            "language": language,
            "filename": filename,
            "model": best["model"],
            "all_results": results
        }

    def generate_code(self, description: str, language: Optional[str] = None, save_to_file: bool = True, use_voting: bool = False) -> Dict[str, Any]:
        """Generate code based on description, optionally using model voting"""
        logger.info("Generating code from description" + (" with voting" if use_voting else ""))
        if use_voting:
            return self.generate_with_voting(description, language, save_to_file)
        if not language:
            language = self._detect_language_from_description(description)
        prompt = f"""Generate {language or 'code'} for the following task:\n{description}"""
        response = self._send_to_llm(prompt, model=language or "deepseek")
        code = self._extract_code_from_llm_response(response)
        if save_to_file:
            filename = self._save_code_to_file(code, language)
        else:
            filename = None
        return {
            "code": code,
            "language": language,
            "filename": filename
        }

    def fix_code(self, code: str, error: str, language: Optional[str] = None, use_voting: bool = False) -> Dict[str, Any]:
        """Fix code based on error feedback, optionally using model voting"""
        logger.info("Fixing code based on error feedback" + (" with voting" if use_voting else ""))
        if use_voting:
            prompt = (
                f"The following {language or 'code'} has an error.\n"
                f"Error message: {error}\n"
                f"Please fix the code below so it works correctly.\n"
                f"---\n"
                f"{code}\n"
                f"---\n"
                f"Return only the fixed code."
            )
            # Use voting across models for fixing
            voting_result = self.generate_with_voting(prompt, language, save_to_file=False)
            # Add fixed_code field for backward compatibility
            voting_result["fixed_code"] = voting_result["code"]
            return voting_result
        if not language:
            language = self._detect_language_from_description(code)
        prompt = (
            f"The following {language or 'code'} has an error.\n"
            f"Error message: {error}\n"
            f"Please fix the code below so it works correctly.\n"
            f"---\n"
            f"{code}\n"
            f"---\n"
            f"Return only the fixed code."
        )
        response = self._send_to_llm(prompt, model=language or "deepseek")
        fixed_code = self._extract_code_from_llm_response(response)
        return {
            "fixed_code": fixed_code,
            "language": language
        }

# Main entry point
if __name__ == "__main__":

    try:
        logger.info("Starting Code Generator Agent...")
        agent = CodeGeneratorAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Code Generator Agent interrupted by user")
    except Exception as e:
        logger.error(f"Error running Code Generator Agent: {str(e)}")
        traceback.print_exc()
