import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from src.core.base_agent import BaseAgent
"""
Unified Planning Agent
- Combines chain of thought reasoning, code execution, task planning, and progressive code generation
- Handles complex multi-step tasks with iterative refinement
- Provides safe code execution environment
- Integrates with AutoGen framework
"""
import zmq
import json
import time
import logging
import traceback
import tempfile
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from utils.config_loader import parse_agent_args
from utils.service_discovery_client import discover_service, register_service, get_service_address
from utils.env_loader import get_env
from src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server
import psutil
from datetime import datetime
from datetime import datetime

# Configure logging (keep as is, or optionally source log level/path from _agent_args)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("UnifiedPlanningAgent")

SECURE_ZMQ = is_secure_zmq_enabled()

_agent_args = parse_agent_args()

class UnifiedPlanningAgent(BaseAgent):
    """Unified agent for planning, execution, and code generation"""
    def __init__(self):
        self.port = int(_agent_args.get('port', 5601))
        self.health_port = int(_agent_args.get('health_port', 5602))
        self.bind_address = _agent_args.get('bind_address', get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        self.zmq_timeout = int(_agent_args.get('zmq_request_timeout', 5000))
        super().__init__(_agent_args)
        self.running = True
        self.start_time = time.time()
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {"core": False}
        }
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        logger.info("UnifiedPlanningAgent basic init complete, async init started")
        
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        self.receiver.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.receiver = configure_secure_server(self.receiver)
            logger.info("Secure ZMQ enabled for UnifiedPlanningAgent")
        
        # Bind to address using self.bind_address for Docker compatibility
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.receiver.bind(bind_address)
        logger.info(f"Unified Planning Agent bound to {bind_address}")
        
        # Register with service discovery
        self._register_service()
        
        # Health check socket
        self.health_check = self.context.socket(zmq.REP)
        self.health_check.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        self.health_check.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        
        # Apply secure ZMQ if enabled for health check socket
        if SECURE_ZMQ:
            self.health_check = configure_secure_server(self.health_check)
        
        # Bind health check socket
        health_bind_address = f"tcp://{self.bind_address}:{self.health_port}"
        self.health_check.bind(health_bind_address)
        logger.info(f"Health check endpoint bound to {health_bind_address}")
        
        # Socket to communicate with task router
        self.task_router = self._create_service_socket("TaskRouter")
        if not self.task_router:
            logger.error("Failed to connect to TaskRouter")
        
        # Socket to communicate with autogen framework
        self.framework = self._create_service_socket("AutoGenFramework")
        if not self.framework:
            logger.error("Failed to connect to AutoGenFramework")
        
        # Setup temp directory for code execution
        self.temp_dir = Path(tempfile.gettempdir()) / "unified_planning_agent"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Language configurations for execution
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
        
        # Agent capabilities mapping
        self.agent_capabilities = {
            "web_scraping": ["web_scraper"],
            "data_extraction": ["web_scraper"],
            "system_cleaning": ["system_cleaner"],
            "performance_optimization": ["system_cleaner"],
            "code_generation": ["code_generator"],
            "code_execution": ["executor"],
            "file_operations": ["filesystem_assistant"],
            "web_automation": ["web_scraper"],
            "text_translation": ["translation"],
            "voice_synthesis": ["tts"]
        }
        
        # Running flags
        self.running = True
        self.health_status = "OK"
        self.last_health_check = time.time()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        logger.info("Unified Planning Agent initialized")
    
    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}
    
    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="UnifiedPlanningAgent",
                port=self.port,
                additional_info={
                    "health_check_port": self.health_port,
                    "capabilities": ["planning", "code_execution", "task_breakdown"],
                    "status": "running"
                }
            )
            if register_result and register_result.get("status") == "SUCCESS":
                logger.info("Successfully registered with service discovery")
            else:
                logger.warning(f"Service registration failed: {register_result.get('message', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error registering service: {e}")
    
    def _create_service_socket(self, service_name):
        """Create a socket connected to a service using service discovery"""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
            socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
            
            # Apply secure ZMQ if enabled
            if SECURE_ZMQ:
                socket = configure_secure_client(socket)
            
            # Get service address from service discovery
            service_address = get_service_address(service_name)
            if service_address:
                socket.connect(service_address)
                logger.info(f"Connected to {service_name} at {service_address}")
                return socket
            else:
                # Fallback to default ports if service discovery fails
                fallback_ports = {
                    "TaskRouter": getattr(_agent_args, 'task_router_port', 5557),
                    "AutoGenFramework": int(config.get('zmq.autogen_framework_port', 5600))
                }
                
                fallback_port = fallback_ports.get(service_name)
                if fallback_port:
                    fallback_address = f"tcp://{self.bind_address}:{fallback_port}"
                    socket.connect(fallback_address)
                    logger.warning(f"Could not discover {service_name}, using fallback address: {fallback_address}")
                    return socket
                else:
                    logger.error(f"Failed to connect to {service_name}: No service discovery or fallback available")
                    return None
        except Exception as e:
            logger.error(f"Error creating socket for {service_name}: {str(e)}")
            return None
    
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Place all blocking init here
            self._init_components()
            self.initialization_status["components"]["core"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logger.info("UnifiedPlanningAgent initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logger.error(f"Initialization error: {e}")
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None, model: str = "phi3") -> str:
        """Send a request to the LLM through the model manager"""
        try:
            # Prepare request
            request = {
                "request_type": "generate",
                "model": model,
                "prompt": prompt,
                "temperature": 0.7
            }
            
            if system_prompt:
                request["system_prompt"] = system_prompt
            
            # Send request to task router instead of model manager
            self.task_router.send_string(json.dumps(request))
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.task_router, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
                response_str = self.task_router.recv_string()
                response = json.loads(response_str)
                
                if response["status"] == "success":
                    return response["text"]
                else:
                    logger.error(f"Error from task router: {response.get('error', 'Unknown error')}")
                    raise Exception(response.get("error", "Unknown error"))
            else:
                logger.error("Timeout waiting for response from task router")
                raise Exception("Timeout waiting for response from task router")
        
        except Exception as e:
            logger.error(f"Error sending to LLM: {str(e)}")
            raise
    
    def _execute_code(self, code: str, language: str = "python", parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code safely in a controlled environment"""
        try:
            # Create temporary file
            file_extension = self.language_configs[language]["file_extension"]
            temp_file = self.temp_dir / f"temp_{int(time.time())}{file_extension}"
            
            # Write code to file
            with open(temp_file, "w") as f:
                f.write(code)
            
            # Get language configuration
            config = self.language_configs[language]
            
            # Execute code
            if "compile_command" in config:
                # Compile first
                compile_cmd = config["compile_command"] + [str(temp_file)]
                process = subprocess.run(compile_cmd, capture_output=True, text=True)
                
                if process.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Compilation error: {process.stderr}"
                    }
                
                # Get executable path
                if language == "c++":
                    exe_path = temp_file.with_suffix("")
                else:
                    exe_path = temp_file.with_suffix(".exe")
                
                # Run compiled code
                run_cmd = config["command"] + [str(exe_path)]
            else:
                # Run interpreted code
                run_cmd = config["command"] + [str(temp_file)]
            
            # Execute with timeout
            process = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=config["timeout"]
            )
            
            # Clean up
            temp_file.unlink()
            if "compile_command" in config:
                exe_path.unlink()
            
            # Return result
            if process.returncode == 0:
                return {
                    "success": True,
                    "output": process.stdout,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": process.stdout,
                    "error": process.stderr
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {config['timeout']} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_problem_breakdown(self, user_request: str, code_context: Optional[str] = None) -> List[str]:
        """Break down a problem into smaller steps using chain of thought"""
        prompt = "I need to break down a coding task into clear, logical steps.\n\n"
        prompt += f"Task: {user_request}\n\n"
        
        if code_context:
            prompt += f"Relevant Code Context:\n```\n{code_context}\n```\n\n"
        
        prompt += "Break this task down into a numbered list of steps. Each step should be specific and achievable. Include planning steps and validation steps."
        
        response = self._send_to_llm(prompt)
        
        # Extract numbered steps from the response
        steps = []
        for line in response.split('\n'):
            # Look for lines that start with a number followed by a period or parenthesis
            if re.match(r'^\d+[\.\)]', line.strip()):
                step = re.sub(r'^\d+[\.\)]\s*', '', line.strip())
                if step:
                    steps.append(step)
        
        # If we couldn't extract steps in the expected format, just split by newlines
        if not steps:
            steps = [line.strip() for line in response.split('\n') if line.strip()]
        
        return steps
    
    def _generate_solution_for_step(self, step: str, previous_steps_info: List[Dict[str, Any]], code_context: Optional[str] = None) -> str:
        """Generate a solution for a specific step"""
        prompt = "I need to implement a specific step in a larger coding task.\n\n"
        
        if code_context:
            prompt += f"Relevant Code Context:\n```\n{code_context}\n```\n\n"
        
        if previous_steps_info:
            prompt += "Previous steps completed:\n"
            for prev_step_info in previous_steps_info:
                prompt += f"- {prev_step_info['step']}\n"
                if 'solution' in prev_step_info:
                    prompt += f"```\n{prev_step_info['solution']}\n```\n"
            prompt += "\n"
        
        prompt += f"Current step to implement: {step}\n\n"
        prompt += "Provide code that implements just this step. Make sure it's compatible with previous steps."
        
        return self._send_to_llm(prompt)
    
    def _verify_solution(self, step: str, solution: str, code_context: Optional[str] = None) -> Dict[str, Any]:
        """Verify a solution for a step"""
        prompt = "I need to verify if a code solution correctly implements a step.\n\n"
        
        if code_context:
            prompt += f"Relevant Code Context:\n```\n{code_context}\n```\n\n"
        
        prompt += f"Step to verify: {step}\n\n"
        prompt += f"Solution to verify:\n```\n{solution}\n```\n\n"
        prompt += "Analyze this solution and identify any issues or potential improvements. Consider:\n"
        prompt += "1. Does it correctly implement the step?\n"
        prompt += "2. Are there any bugs or edge cases not handled?\n"
        prompt += "3. Is it compatible with previous steps?\n"
        prompt += "4. Are there any performance or security concerns?\n"
        prompt += "5. Does it follow best practices?\n\n"
        prompt += "Return your analysis as a JSON object with the following properties:\n"
        prompt += "- has_issues: boolean indicating if any issues were found\n"
        prompt += "- issues: array of identified issues\n"
        prompt += "- improvements: array of suggested improvements\n"
        prompt += "- confidence: number between 0 and 1 indicating confidence in the solution"
        
        response = self._send_to_llm(prompt)
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                return {
                    "has_issues": True,
                    "issues": ["Could not parse verification response"],
                    "improvements": [],
                    "confidence": 0.0
                }
        except json.JSONDecodeError:
            return {
                "has_issues": True,
                "issues": ["Invalid JSON in verification response"],
                "improvements": [],
                "confidence": 0.0
            }
    
    def _refine_solution(self, step: str, solution: str, verification: Dict[str, Any], code_context: Optional[str] = None) -> str:
        """Refine a solution based on verification feedback"""
        prompt = "I need to refine a code solution based on verification feedback.\n\n"
        
        if code_context:
            prompt += f"Relevant Code Context:\n```\n{code_context}\n```\n\n"
        
        prompt += f"Step to implement: {step}\n\n"
        prompt += f"Current solution:\n```\n{solution}\n```\n\n"
        
        if verification["issues"]:
            prompt += "Issues identified:\n"
            for issue in verification["issues"]:
                prompt += f"- {issue}\n"
            prompt += "\n"
        
        if verification["improvements"]:
            prompt += "Suggested improvements:\n"
            for improvement in verification["improvements"]:
                prompt += f"- {improvement}\n"
            prompt += "\n"
        
        prompt += "Please provide an improved version of the solution that addresses these issues and incorporates the suggested improvements."
        
        return self._send_to_llm(prompt)
    
    def _generate_combined_solution(self, steps_with_solutions: List[Dict[str, Any]], user_request: str, code_context: Optional[str] = None) -> str:
        """Combine all step solutions into a coherent whole"""
        prompt = "I need to combine multiple code components into a cohesive solution.\n\n"
        prompt += f"Original task: {user_request}\n\n"
        
        if code_context:
            prompt += f"Existing code context:\n```\n{code_context}\n```\n\n"
        
        prompt += "Here are the components implementing each step:\n\n"
        
        for i, step_info in enumerate(steps_with_solutions):
            prompt += f"Step {i+1}: {step_info['step']}\n"
            prompt += f"```\n{step_info['solution']}\n```\n\n"
        
        prompt += "Combine these components into a complete, well-organized solution that accomplishes the original task. Eliminate redundancy and ensure all components work together seamlessly."
        
        return self._send_to_llm(prompt)
    
    def _create_plan(self, description: str) -> List[Dict[str, Any]]:
        """Create a plan from a natural language description"""
        logger.info(f"Creating plan for: {description}")
        
        # System prompt for the planning LLM
        system_prompt = """You are a task planning AI. Your job is to break down a complex task into a series of steps that can be executed by specialized agents. For each step, you need to specify:

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

1. The agent type that should handle the step
2. A description of what needs to be done
3. Any parameters needed for the step

Available agent types:
- web_scraper: For web scraping, data extraction, and web automation
- system_cleaner: For system maintenance, optimization, and performance improvements
- code_generator: For generating code based on descriptions
- executor: For executing code safely
- filesystem_assistant: For file operations
- translation: For translating text between languages
- tts: For text-to-speech conversion

Return your plan as a JSON array of steps, where each step is an object with the following properties:
- agent_type: The type of agent to handle this step
- description: A description of what needs to be done
- parameters: An object containing any parameters needed for the step"""
        
        # Create the prompt for the planning LLM
        prompt = f"""Task description: {description}

Break down this task into a series of steps that can be executed by specialized agents. Return your plan as a JSON array of steps."""
        
        try:
            # Get plan from LLM
            response = self._send_to_llm(prompt, system_prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            
            if json_match:
                plan_json = json_match.group(0)
                plan = json.loads(plan_json)
                logger.info(f"Created plan with {len(plan)} steps")
                return plan
            else:
                logger.error("Could not extract JSON plan from LLM response")
                raise Exception("Could not extract JSON plan from LLM response")
        
        except Exception as e:
            logger.error(f"Error creating plan: {str(e)}")
            raise
    
    def _analyze_task(self, description: str) -> Dict[str, Any]:
        """Analyze a task to determine its requirements and complexity"""
        logger.info(f"Analyzing task: {description}")
        
        # System prompt for the analysis LLM
        system_prompt = """You are a task analysis AI. Your job is to analyze a task description and identify:
1. The main goal of the task
2. Required capabilities to complete the task
3. Estimated complexity (simple, medium, complex)
4. Potential challenges or risks

Available capabilities:
- web_scraping: Extracting data from websites
- data_extraction: Parsing and processing data
- system_cleaning: Cleaning up system files and optimizing performance
- performance_optimization: Improving system performance
- code_generation: Creating code based on descriptions
- code_execution: Running code safely
- file_operations: Reading, writing, and managing files
- web_automation: Automating web browser actions
- text_translation: Translating text between languages
- voice_synthesis: Converting text to speech

Return your analysis as a JSON object with the following properties:
- goal: The main goal of the task
- capabilities: An array of required capabilities
- complexity: Estimated complexity (simple, medium, complex)
- challenges: An array of potential challenges or risks"""
        
        # Create the prompt for the analysis LLM
        prompt = f"""Task description: {description}

Analyze this task and identify its requirements and complexity. Return your analysis as a JSON object."""
        
        try:
            # Get analysis from LLM
            response = self._send_to_llm(prompt, system_prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                analysis_json = json_match.group(0)
                analysis = json.loads(analysis_json)
                logger.info(f"Task analysis: {analysis}")
                return analysis
            else:
                logger.error("Could not extract JSON analysis from LLM response")
                raise Exception("Could not extract JSON analysis from LLM response")
        
        except Exception as e:
            logger.error(f"Error analyzing task: {str(e)}")
            raise
    
    def _map_capabilities_to_agents(self, capabilities: List[str]) -> Dict[str, List[str]]:
        """Map capabilities to agent types"""
        agent_map = {}
        
        for capability in capabilities:
            if capability in self.agent_capabilities:
                agent_types = self.agent_capabilities[capability]
                
                for agent_type in agent_types:
                    if agent_type not in agent_map:
                        agent_map[agent_type] = []
                    
                    agent_map[agent_type].append(capability)
        
        return agent_map
    
    def _health_check_loop(self):
        """Health check loop"""
        while self.running:
            try:
                # Check if we have any messages
                if self.health_check.poll(timeout=1000, flags=zmq.POLLIN):
                    # Receive request
                    request = self.health_check.recv_string()
                    
                    # Send response
                    response = {
                        "status": self.health_status,
                        "last_check": self.last_health_check,
                        "uptime": time.time() - self.last_health_check
                    }
                    self.health_check.send_string(json.dumps(response))
                
                # Update health status
                self.last_health_check = time.time()
                self.health_status = "OK"
            
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                self.health_status = "ERROR"
    
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
                        
                        if request_type == "plan":
                            # Handle planning request
                            description = request.get("description")
                            
                            if not description:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: description"
                                }
                            else:
                                try:
                                    # First analyze the task
                                    analysis = self._analyze_task(description)
                                    
                                    # Then create a plan
                                    plan = self._create_plan(description)
                                    
                                    response = {
                                        "status": "success",
                                        "plan": plan,
                                        "analysis": analysis
                                    }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error planning task: {str(e)}"
                                    }
                        
                        elif request_type == "analyze":
                            # Handle analysis request
                            description = request.get("description")
                            
                            if not description:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: description"
                                }
                            else:
                                try:
                                    analysis = self._analyze_task(description)
                                    
                                    response = {
                                        "status": "success",
                                        "analysis": analysis
                                    }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error analyzing task: {str(e)}"
                                    }
                        
                        elif request_type == "generate":
                            # Handle code generation request
                            description = request.get("description")
                            code_context = request.get("code_context")
                            
                            if not description:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: description"
                                }
                            else:
                                try:
                                    # Break down the problem
                                    steps = self._generate_problem_breakdown(description, code_context)
                                    
                                    # Generate and verify solutions for each step
                                    steps_with_solutions = []
                                    for step in steps:
                                        # Generate solution
                                        solution = self._generate_solution_for_step(
                                            step,
                                            steps_with_solutions,
                                            code_context
                                        )
                                        
                                        # Verify solution
                                        verification = self._verify_solution(step, solution, code_context)
                                        
                                        # If issues found, refine solution
                                        if verification["has_issues"]:
                                            solution = self._refine_solution(
                                                step,
                                                solution,
                                                verification,
                                                code_context
                                            )
                                        
                                        steps_with_solutions.append({
                                            "step": step,
                                            "solution": solution,
                                            "verification": verification
                                        })
                                    
                                    # Combine solutions
                                    final_solution = self._generate_combined_solution(
                                        steps_with_solutions,
                                        description,
                                        code_context
                                    )
                                    
                                    response = {
                                        "status": "success",
                                        "solution": final_solution,
                                        "steps": steps_with_solutions
                                    }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error generating code: {str(e)}"
                                    }
                        
                        elif request_type == "execute":
                            # Handle code execution request
                            code = request.get("code")
                            language = request.get("language", "python")
                            parameters = request.get("parameters")
                            
                            if not code:
                                response = {
                                    "status": "error",
                                    "error": "Missing required parameter: code"
                                }
                            else:
                                try:
                                    result = self._execute_code(code, language, parameters)
                                    
                                    response = {
                                        "status": "success",
                                        "result": result
                                    }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error executing code: {str(e)}"
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
        """Run the unified planning agent"""
        try:
            # Register with AutoGen framework using service discovery
            if self.framework:
                self.framework.send_string(json.dumps({
                    "request_type": "register_agent",
                    "agent_id": "unified_planning",
                    "endpoint": f"tcp://{self.bind_address}:{self.port}",
                    "capabilities": [
                        "planning",
                        "task_decomposition",
                        "code_generation",
                        "code_execution",
                        "chain_of_thought"
                    ]
                }))
                
                # Wait for response
                response_str = self.framework.recv_string()
                response = json.loads(response_str)
                
                if response["status"] != "success":
                    logger.error(f"Error registering with AutoGen framework: {response.get('error', 'Unknown error')}")
                else:
                    logger.info("Registered with AutoGen framework")
            else:
                logger.warning("AutoGen framework connection not available, skipping registration")
            
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
        logger.info("Cleaning up resources...")
        self.running = False
        
        # Unregister from AutoGen framework
        try:
            if self.framework:
                self.framework.send_string(json.dumps({
                    "request_type": "unregister_agent",
                    "agent_id": "unified_planning"
                }))
                
                # Wait for response with timeout
                try:
                    response_str = self.framework.recv_string()
                    logger.info("Successfully unregistered from AutoGen framework")
                except zmq.Again:
                    logger.warning("Timeout waiting for unregister response from AutoGen framework")
        except Exception as e:
            logger.error(f"Error unregistering from AutoGen framework: {e}")
        
        # Close sockets in a try-finally block to ensure they're all closed
        try:
            if hasattr(self, 'receiver'):
                self.receiver.close()
                logger.debug("Closed receiver socket")
            
            if hasattr(self, 'health_check'):
                self.health_check.close()
                logger.debug("Closed health check socket")
            
            if hasattr(self, 'task_router') and self.task_router:
                self.task_router.close()
                logger.debug("Closed task router socket")
            
            if hasattr(self, 'framework') and self.framework:
                self.framework.close()
                logger.debug("Closed framework socket")
        except Exception as e:
            logger.error(f"Error during socket cleanup: {e}")
        finally:
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                logger.debug("Terminated ZMQ context")
        
        logger.info("Unified Planning Agent stopped successfully")


# Main entry point
if __name__ == "__main__":
    agent = UnifiedPlanningAgent()
    agent.run()