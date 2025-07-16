from main_pc_code.src.core.base_agent import BaseAgent
"""
Executor Agent
- Safely executes code in a sandboxed environment
- Supports multiple programming languages
- Integrates with the AutoGen framework
- Provides execution results and error handling
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
import subprocess
import platform
import uuid
import io
import contextlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "executor_agent.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ExecutorAgent")

# Get ZMQ ports from config
EXECUTOR_PORT = config.get('zmq.executor_port', 5613)
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5650)

# Flag to enable/disable AutoGen Framework integration
USE_AUTOGEN_FRAMEWORK = False  # Set to False for standalone mode, True for framework integration

class ExecutorAgent(BaseAgent):
    """Agent for safely executing code"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ExecutorAgent")
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.bind(f"tcp://127.0.0.1:{EXECUTOR_PORT}")
        logger.info(f"Executor Agent bound to port {EXECUTOR_PORT}")
        
        # Socket to communicate with autogen framework (if enabled)
        if USE_AUTOGEN_FRAMEWORK:
            self.framework = self.context.socket(zmq.REQ)
            self.framework.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.framework.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.framework.connect(f"tcp://localhost:{AUTOGEN_FRAMEWORK_PORT}")
            logger.info(f"Connected to AutoGen Framework on port {AUTOGEN_FRAMEWORK_PORT}")
        else:
            self.framework = None
            logger.info("AutoGen Framework integration disabled (standalone mode)")

        
        # Setup temp directory for code execution
        self.temp_dir = Path(tempfile.gettempdir()) / "executor_agent"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Maximum execution time (in seconds)
        self.max_execution_time = 30
        
        # Language configurations
        self.language_configs = {
            "python": {
                "file_extension": ".py",
                "command": ["python"],
                "timeout": 30
            },
            "javascript": {
                "file_extension": ".js",
                "command": ["node"],
                "timeout": 30
            },
            "java": {
                "file_extension": ".java",
                "compile_command": ["javac"],
                "command": ["java"],
                "timeout": 30
            },
            "c#": {
                "file_extension": ".cs",
                "compile_command": ["csc"],
                "command": [],  # Will be set based on compiled output
                "timeout": 30
            },
            "c++": {
                "file_extension": ".cpp",
                "compile_command": ["g++", "-o"],
                "command": [],  # Will be set based on compiled output
                "timeout": 30
            }
        }
        
        # Running flag
        self.running = True
        
        logger.info("Executor Agent initialized")
    
    def _detect_language_from_code(self, code: str) -> str:
        """Detect programming language from code"""
        # Check for common language patterns
        if "import " in code or "from " in code and " import " in code or "def " in code or "class " in code:

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
            return "python"
        elif "function " in code or "const " in code or "let " in code or "var " in code:
            return "javascript"
        elif "public class " in code or "public static void main" in code:
            return "java"
        elif "using System;" in code or "namespace " in code or "public class " in code and "static void Main" in code:
            return "c#"
        elif "#include <" in code or "int main(" in code:
            return "c++"
        
        # Default to Python if language can't be detected
        return "python"
    
    def _create_temp_file(self, code: str, language: str) -> str:
        """Create a temporary file with the code"""
        # Get file extension for the language
        file_extension = self.language_configs.get(language, {}).get("file_extension", ".txt")
        
        # Generate a unique filename
        filename = f"code_{uuid.uuid4().hex}{file_extension}"
        file_path = self.temp_dir / filename
        
        # Write code to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
        
        logger.info(f"Created temporary file: {file_path}")
        
        return str(file_path)
    
    def _execute_python_code(self, code: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Python code in a sandboxed environment"""
        logger.info("Executing Python code")
        
        try:
            # Create a dictionary for local variables
            local_vars = {}
            if parameters:
                local_vars.update(parameters)
            
            # Capture stdout and stderr
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()
            
            # Execute code with timeout
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(exec, code, {}, local_vars)
                    try:
                        future.result(timeout=self.max_execution_time)
                    except TimeoutError:
                        return {
                            "status": "error",
                            "error": f"Execution timed out after {self.max_execution_time} seconds",
                            "code": code,
                            "language": "python"
                        }
            
            # Get stdout and stderr
            stdout = stdout_buffer.getvalue()
            stderr = stderr_buffer.getvalue()
            
            # Check for errors
            if stderr:
                return {
                    "status": "error",
                    "error": stderr,
                    "stdout": stdout,
                    "code": code,
                    "language": "python"
                }
            
            # Extract result from local variables
            result = None
            if "result" in local_vars:
                result = local_vars["result"]
            
            return {
                "status": "success",
                "result": result,
                "stdout": stdout,
                "local_vars": {k: str(v) for k, v in local_vars.items() if not k.startswith("_")}
            }
        
        except Exception as e:
            logger.error(f"Error executing Python code: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "code": code,
                "language": "python"
            }
    
    def _execute_code_subprocess(self, file_path: str, language: str) -> Dict[str, Any]:
        """Execute code in a subprocess"""
        logger.info(f"Executing {language} code in subprocess")
        
        try:
            # Get language configuration
            lang_config = self.language_configs.get(language, {})
            command = lang_config.get("command", [])
            timeout = lang_config.get("timeout", 30)
            
            if not command:
                return {
                    "status": "error",
                    "error": f"Unsupported language: {language}",
                    "code": Path(file_path).read_text() if hasattr(Path(file_path), 'read_text') else None,
                    "language": language
                }
            
            # Check if compilation is needed
            compile_command = lang_config.get("compile_command")
            if compile_command:
                compile_process = subprocess.run(
                    compile_command + [str(file_path)],
                    capture_output=True,
                    text=True
                )
                if compile_process.returncode != 0:
                    return {
                        "status": "error",
                        "error": compile_process.stderr,
                        "code": Path(file_path).read_text() if hasattr(Path(file_path), 'read_text') else None,
                        "language": language
                    }
                # For C++/C#, update command to run the compiled binary
                if language in ["c++", "c#"]:
                    command = [str(Path(file_path).with_suffix(''))]
            
            # Execute code
            process = subprocess.run(
                command + [str(file_path)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if process.returncode != 0:
                return {
                    "status": "error",
                    "error": process.stderr,
                    "stdout": process.stdout,
                    "code": Path(file_path).read_text() if hasattr(Path(file_path), 'read_text') else None,
                    "language": language
                }
            
            return {
                "status": "success",
                "stdout": process.stdout,
                "stderr": process.stderr
            }
        
        except subprocess.TimeoutExpired:
            logger.error(f"Execution timed out after {timeout} seconds")
            return {
                "status": "error",
                "error": f"Execution timed out after {timeout} seconds",
                "code": Path(file_path).read_text() if hasattr(Path(file_path), 'read_text') else None,
                "language": language
            }
        
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "code": Path(file_path).read_text() if hasattr(Path(file_path), 'read_text') else None,
                "language": language
            }
    
    def execute_code(self, code: str, language: Optional[str] = None, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code safely"""
        logger.info("Executing code")
        
        try:
            # Detect language if not provided
            if not language:
                language = self._detect_language_from_code(code)
            
            logger.info(f"Detected language: {language}")
            
            # For Python, we can execute in-process for better performance and parameter passing
            if language.lower() == "python":
                return self._execute_python_code(code, parameters)
            
            # For other languages, execute in a subprocess
            file_path = self._create_temp_file(code, language)
            return self._execute_code_subprocess(file_path, language)
        
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "code": code,
                "language": language if language else None
            }
    
    def handle_requests(self):
        """Main loop to handle incoming requests"""
        logger.info("Starting request handler")
        
        while self.running:
            try:
                # Set timeout to allow checking running flag
                poller = zmq.Poller()
                poller.register(self.receiver, zmq.POLLIN)
                
                if poller.poll(1000):  # 1 second timeout
                    # Receive request
                    request_str = self.receiver.recv_string()
                    
                    try:
                        request = json.loads(request_str)
                        request_type = request.get("request_type")
                        
                        logger.info(f"Received request: {request_type}")
                        
                        # Health check support
                        if (request.get("action") == "health_check") or (request_type == "health_check"):
                            response = {"status": "healthy", "service": "ExecutorAgent"}
                        
                        elif request_type == "execute":
                            # Handle code execution request
                            code = request.get("code")
                            language = request.get("language")
                            parameters = request.get("parameters")
                            
                            if not code:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: code"
                                }
                            else:
                                response = self.execute_code(code, language, parameters)
                        
                        elif request_type == "task_step":
                            # Handle task step request from AutoGen framework
                            content = request.get("content", {})
                            step = content.get("step", {})
                            
                            if not step:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: step"
                                }
                            else:
                                try:
                                    # Extract parameters from step
                                    description = step.get("description", "")
                                    parameters = step.get("parameters", {})
                                    
                                    # Extract specific parameters for code execution
                                    code = parameters.get("code")
                                    language = parameters.get("language")
                                    exec_parameters = parameters.get("parameters")
                                    
                                    if not code:
                                        response = {
                                            "status": "error",
                                            "error": "Missing required parameter: code"
                                        }
                                    else:
                                        result = self.execute_code(code, language, exec_parameters)
                                        response = {
                                            "status": "success",
                                            "result": result
                                        }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error executing task step: {str(e)}"
                                    }
                        
                        else:
                            response = {
                                "status": "error",
                                "error": f"Unknown request type: {request_type}"
                            }
                    
                    except json.JSONDecodeError:
                        response = {
                            "status": "error",
                            "error": "Invalid JSON in request"
                        }
                    except Exception as e:
                        response = {
                            "status": "error",
                            "error": f"Error processing request: {str(e)}"
                        }
                    
                    # Send response
                    self.receiver.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
            except Exception as e:
                logger.error(f"Error in request handler: {str(e)}")
                traceback.print_exc()
    
    def run(self):
        """Run the executor agent"""
        try:
            # Register with AutoGen framework (if enabled)
            if USE_AUTOGEN_FRAMEWORK and self.framework is not None:
                logger.info("Attempting to register with AutoGen framework...")
                try:
                    self.framework.send_string(json.dumps({
                        "request_type": "register_agent",
                        "agent_id": "executor",
                        "endpoint": f"tcp://localhost:{EXECUTOR_PORT}",
                        "capabilities": ["code_execution"]
                    }))
                    
                    # Wait for response with timeout
                    poller = zmq.Poller()
                    poller.register(self.framework, zmq.POLLIN)
                    
                    if poller.poll(5000):  # 5 second timeout
                        response_str = self.framework.recv_string()
                        response = json.loads(response_str)
                        
                        if response["status"] != "success":
                            logger.error(f"Error registering with AutoGen framework: {response.get('error', 'Unknown error')}")
                        else:
                            logger.info("Registered with AutoGen framework")
                    else:
                        logger.warning("Timeout waiting for response from AutoGen framework. Continuing in standalone mode.")
                except Exception as e:
                    logger.warning(f"Failed to register with AutoGen framework: {str(e)}. Continuing in standalone mode.")
            else:
                logger.info("Running in standalone mode (AutoGen framework integration disabled)")

            
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
        
        # Unregister from AutoGen framework (if enabled)
        if USE_AUTOGEN_FRAMEWORK and self.framework is not None:
            try:
                self.framework.send_string(json.dumps({
                    "request_type": "unregister_agent",
                    "agent_id": "executor"
                }))
                
                # Wait for response with timeout
                poller = zmq.Poller()
                poller.register(self.framework, zmq.POLLIN)
                
                if poller.poll(3000):  # 3 second timeout
                    response_str = self.framework.recv_string()
                    logger.info("Unregistered from AutoGen framework")
                else:
                    logger.warning("Timeout while unregistering from AutoGen framework")
            except Exception as e:
                logger.warning(f"Error unregistering from AutoGen framework: {str(e)}")
                pass
        
        self.receiver.close()
        if self.framework is not None:
            self.framework.close()
        self.context.term()
        
        logger.info("Executor Agent stopped")


# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Executor Agent...")
        agent = ExecutorAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Executor Agent interrupted by user")
    except Exception as e:
        logger.error(f"Error running Executor Agent: {str(e)}")
        traceback.print_exc()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise