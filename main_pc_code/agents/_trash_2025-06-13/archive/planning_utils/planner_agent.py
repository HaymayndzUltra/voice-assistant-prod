from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Planner Agent
- Breaks down natural language requests into executable steps
- Determines which agents should handle each step
- Creates a plan for complex multi-step tasks
- Coordinates with the AutoGen framework
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

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config
from common.env_helpers import get_env

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "planner_agent.log")
log_file.parent.mkdir(exist_ok=True)

logger = configure_logging(__name__),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PlannerAgent")

# Get ZMQ ports from config
PLANNER_AGENT_PORT = config.get('zmq.planner_agent_port', 5601)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
AUTOGEN_FRAMEWORK_PORT = config.get('zmq.autogen_framework_port', 5600)

class PlannerAgent(BaseAgent):
    """Agent for planning and task decomposition"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="PlannerAgent")
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.bind(f"tcp://127.0.0.1:{PLANNER_AGENT_PORT}")
        logger.info(f"Planner Agent bound to port {PLANNER_AGENT_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on port {MODEL_MANAGER_PORT}")
        
        # Socket to communicate with autogen framework
        self.framework = self.context.socket(zmq.REQ)
        self.framework.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.framework.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.framework.connect(f"tcp://localhost:{AUTOGEN_FRAMEWORK_PORT}")
        logger.info(f"Connected to AutoGen Framework on port {AUTOGEN_FRAMEWORK_PORT}")
        
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
        
        # Running flag
        self.running = True
        
        logger.info("Planner Agent initialized")
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a request to the LLM through the model manager"""
        try:
            # Prepare request
            request = {
                "request_type": "generate",
                "model": "phi3",  # Use Phi-3 for planning
                "prompt": prompt,
                "temperature": 0.7
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
    
    def create_plan(self, description: str) -> List[Dict[str, Any]]:
        """Create a plan from a natural language description"""
        logger.info(f"Creating plan for: {description}")
        
        # System prompt for the planning LLM
        system_prompt = """You are a task planning AI. Your job is to break down a complex task into a series of steps that can be executed by specialized agents. For each step, you need to specify:
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
- parameters: An object containing any parameters needed for the step

Example:
[
  {
    "agent_type": "web_scraper",
    "description": "Scrape product information from example.com",
    "parameters": {
      "url": "https://example.com/products",
      "data_type": "product",
      "output_format": "csv"
    }
  },
  {
    "agent_type": "filesystem_assistant",
    "description": "Save the scraped data to a file",
    "parameters": {
      "operation": "write",
      "file_path": "scraped_products.csv",
      "content_source": "previous_step"
    }
  }
]"""
        
        # Create the prompt for the planning LLM
        prompt = f"""Task description: {description}

Break down this task into a series of steps that can be executed by specialized agents. Return your plan as a JSON array of steps."""
        
        try:
            # Get plan from LLM
            response = self._send_to_llm(prompt, system_prompt)
            
            # Extract JSON from response
            import re
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
    
    def analyze_task(self, description: str) -> Dict[str, Any]:
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
            import re

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
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
    
    def map_capabilities_to_agents(self, capabilities: List[str]) -> Dict[str, List[str]]:
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
                                    analysis = self.analyze_task(description)
                                    
                                    # Then create a plan
                                    plan = self.create_plan(description)
                                    
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
                                    analysis = self.analyze_task(description)
                                    
                                    response = {
                                        "status": "success",
                                        "analysis": analysis
                                    }
                                except Exception as e:
                                    response = {
                                        "status": "error",
                                        "error": f"Error analyzing task: {str(e)}"
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
        """Run the planner agent"""
        try:
            # Register with AutoGen framework
            self.framework.send_string(json.dumps({
                "request_type": "register_agent",
                "agent_id": "planner",
                "endpoint": f"tcp://localhost:{PLANNER_AGENT_PORT}",
                "capabilities": ["planning", "task_decomposition"]
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
                "agent_id": "planner"
            }))
            
            # Wait for response
            response_str = self.framework.recv_string()
        except:
            pass
        
        self.receiver.close()
        self.model_manager.close()
        self.framework.close()
        self.context.term()
        
        logger.info("Planner Agent stopped")


# Main entry point
if __name__ == "__main__":
    try:
        logger.info("Starting Planner Agent...")
        agent = PlannerAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Planner Agent interrupted by user")
    except Exception as e:
        logger.error(f"Error running Planner Agent: {str(e)}")
        traceback.print_exc()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise