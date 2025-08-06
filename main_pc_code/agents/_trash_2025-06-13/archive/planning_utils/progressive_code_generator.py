from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Progressive Code Generator
- Breaks down complex tasks into smaller, testable components
- Builds code incrementally with testing at each step
- Integrates with the error database for faster fixes
- Supports both English and Filipino commands
"""
import zmq
import json
import time
import logging
import sys
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import re
import threading

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import config
from main_pc_code.agents.error_database import ErrorDatabase
from common.env_helpers import get_env

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "progressive_code_generator.log")
log_file.parent.mkdir(exist_ok=True)

logger = configure_logging(__name__),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ProgressiveCodeGenerator")

# Get ZMQ ports from config
PROGRESSIVE_CODE_GEN_PORT = config.get('zmq.progressive_code_gen_port', 5607)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5556)
EXECUTOR_PORT = config.get('zmq.executor_port', 5613)

class ProgressiveCodeGenerator(BaseAgent):
    """Progressive code generator that builds code incrementally with testing"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ProgressiveCodeGenerator")
        """Initialize the progressive code generator"""
        # Initialize ZMQ
        self.context = zmq.Context()
        
        # Socket to receive requests
        self.receiver = self.context.socket(zmq.REP)
        self.receiver.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.receiver.bind(f"tcp://127.0.0.1:{PROGRESSIVE_CODE_GEN_PORT}")
        logger.info(f"Progressive Code Generator bound to port {PROGRESSIVE_CODE_GEN_PORT}")
        
        # Socket to communicate with model manager
        self.model_manager = self.context.socket(zmq.REQ)
        self.model_manager.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.model_manager.connect(f"tcp://localhost:{MODEL_MANAGER_PORT}")
        logger.info(f"Connected to Model Manager on port {MODEL_MANAGER_PORT}")
        
        # Socket to communicate with executor agent
        self.executor = self.context.socket(zmq.REQ)
        self.executor.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.executor.connect(f"tcp://localhost:{EXECUTOR_PORT}")
        logger.info(f"Connected to Executor Agent on port {EXECUTOR_PORT}")
        
        # Initialize error database
        self.error_db = ErrorDatabase()
        
        # Running flag
        self.running = True
        
        logger.info("Progressive Code Generator initialized")
    
    def _send_to_llm(self, prompt: str, system_prompt: Optional[str] = None, model: str = "deepseek") -> str:
        """Send a request to the LLM through the model manager"""
        try:
            # Prepare request
            request = {
                "request_type": "generate",
                "model": model,
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
    
    def _break_down_task(self, description: str, language: str) -> List[Dict[str, Any]]:
        """Break down a complex task into smaller, testable components"""
        prompt = f"""Break down the following coding task into smaller, testable components.
For each component, provide:
1. A brief description
2. Input/output examples if applicable
3. Dependencies on other components
4. Suggested test cases

Task: {description}
Language: {language}

Format your response as a JSON array of components, each with the following structure:
```json
[
  {{
    "id": 1,
    "name": "component_name",
    "description": "What this component does",
    "dependencies": [list of component ids this depends on],
    "test_cases": [
      {{"input": "example input", "expected_output": "expected output"}}
    ]
  }}
]
```
"""
        
        response = self._send_to_llm(prompt)
        
        # Extract JSON from response
        json_pattern = r"```json\s*([\s\S]*?)```"
        json_matches = re.findall(json_pattern, response)
        
        if json_matches:
            try:
                components = json.loads(json_matches[0])
                logger.info(f"Task broken down into {len(components)} components")
                return components
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from LLM response")
        
        # Fallback: return a single component for the entire task
        logger.warning("Using fallback task breakdown")
        return [{
            "id": 1,
            "name": "main_component",
            "description": description,
            "dependencies": [],
            "test_cases": []
        }]
    
    def _generate_component_code(self, component: Dict[str, Any], language: str) -> str:
        """Generate code for a specific component"""
        prompt = f"""Generate code for the following component:
Name: {component['name']}
Description: {component['description']}
Language: {language}

{f"Test Cases: {json.dumps(component['test_cases'], indent=2)}" if component.get('test_cases') else ""}

Only provide the code, no explanations.
"""
        
        response = self._send_to_llm(prompt)
        code = self._extract_code_from_llm_response(response)
        
        return code
    
    def _generate_test_code(self, component: Dict[str, Any], code: str, language: str) -> str:
        """Generate test code for a component"""
        prompt = f"""Generate test code for the following component:
Name: {component['name']}
Description: {component['description']}
Language: {language}

Component Code:
```{language}
{code}
```

{f"Test Cases: {json.dumps(component['test_cases'], indent=2)}" if component.get('test_cases') else ""}

Generate code that tests this component. The test should verify that the component works as expected.
Only provide the test code, no explanations.
"""
        
        response = self._send_to_llm(prompt)
        test_code = self._extract_code_from_llm_response(response)
        
        return test_code
    
    def _fix_code_with_error_db(self, code: str, error: str, language: str) -> Optional[str]:
        """Try to fix code using the error database"""
        # Find matching error pattern
        match_result = self.error_db.find_matching_error(error, language)
        
        if match_result:
            pattern_id, error_type, solutions = match_result
            
            if solutions:
                # Use the best solution
                best_solution = solutions[0]
                logger.info(f"Found matching error pattern: {error_type} with solution (success rate: {best_solution['success_rate']})")
                
                # Apply the solution
                # This is a simplified version - in a real system, this would be more sophisticated
                # For now, we'll just return the solution code
                return best_solution["solution_code"]
        
        return None
    
    def _fix_code_with_llm(self, code: str, error: str, language: str) -> str:
        """Fix code using LLM"""
        prompt = f"""The following {language} code has an error:
```{language}
{code}
```

Error message:
{error}

Please fix the code. Only provide the corrected code, no explanations.
"""
        
        response = self._send_to_llm(prompt)
        fixed_code = self._extract_code_from_llm_response(response)
        
        return fixed_code
    
    def _integrate_components(self, components: List[Dict[str, Any]], component_code: Dict[int, str], language: str) -> str:
        """Integrate all components into a single codebase"""
        # Sort components by dependencies
        sorted_components = self._topological_sort(components)
        
        # Prepare the integration prompt
        component_descriptions = []
        for comp in sorted_components:
            comp_id = comp["id"]
            if comp_id in component_code:
                component_descriptions.append(f"""Component {comp_id}: {comp['name']}
Description: {comp['description']}
Code:
```{language}
{component_code[comp_id]}
```
""")
        
        components_text = "\n".join(component_descriptions)
        
        prompt = f"""Integrate the following components into a single {language} codebase:

{components_text}

The components should be integrated in a way that they work together seamlessly.
Only provide the integrated code, no explanations.
"""
        
        response = self._send_to_llm(prompt)
        integrated_code = self._extract_code_from_llm_response(response)
        
        return integrated_code
    
    def _topological_sort(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort components by dependencies using topological sort"""
        # Create a graph
        graph = {}
        for comp in components:
            comp_id = comp["id"]
            graph[comp_id] = comp.get("dependencies", [])
        
        # Perform topological sort
        visited = set()
        temp = set()
        order = []
        
        def dfs(node):
            if node in temp:
                # Cycle detected
                return False
            if node in visited:
                return True
            
            temp.add(node)
            
            for neighbor in graph.get(node, []):
                if not dfs(neighbor):
                    return False
            
            temp.remove(node)
            visited.add(node)
            order.append(node)
            return True
        
        # Visit all nodes
        for node in graph:
            if node not in visited:
                if not dfs(node):
                    # Cycle detected, return original order
                    return components
        
        # Reverse the order and map back to components
        order.reverse()
        id_to_component = {comp["id"]: comp for comp in components}
        sorted_components = [id_to_component[comp_id] for comp_id in order]
        
        return sorted_components
    
    def generate_progressive_code(self, description: str, language: str) -> Dict[str, Any]:
        """Generate code progressively with testing at each step"""
        logger.info(f"Generating progressive code for: {description}")
        start_time = time.time()
        
        try:
            # Break down the task into components
            components = self._break_down_task(description, language)
            
            # Generate code for each component
            component_code = {}
            component_status = {}
            
            for component in components:
                comp_id = component["id"]
                comp_name = component["name"]
                logger.info(f"Generating code for component {comp_id}: {comp_name}")
                
                # Check if all dependencies are satisfied
                dependencies = component.get("dependencies", [])
                unsatisfied_deps = [dep for dep in dependencies if dep not in component_code]
                
                if unsatisfied_deps:
                    logger.warning(f"Component {comp_id} has unsatisfied dependencies: {unsatisfied_deps}")
                    component_status[comp_id] = {
                        "status": "skipped",
                        "reason": f"Unsatisfied dependencies: {unsatisfied_deps}"
                    }
                    continue
                
                # Generate code for the component
                code = self._generate_component_code(component, language)
                
                # Generate test code
                test_code = self._generate_test_code(component, code, language)
                
                # Execute the test
                try:
                    test_result = self._execute_code(test_code)
                    if test_result.get("success", False):
                        logger.info(f"Component {comp_id} tests passed")
                        component_code[comp_id] = code
                        component_status[comp_id] = {
                            "status": "success",
                            "test_result": test_result
                        }
                    else:
                        # Test failed, try to fix the code
                        error = test_result.get("error", "Unknown error")
                        logger.warning(f"Component {comp_id} tests failed: {error}")
                        
                        # Try to fix with error database first
                        fixed_code = self._fix_code_with_error_db(code, error, language)
                        
                        if not fixed_code:
                            # If no fix found in database, use LLM
                            fixed_code = self._fix_code_with_llm(code, error, language)
                        
                        # Test the fixed code
                        fixed_test_code = self._generate_test_code(component, fixed_code, language)
                        fixed_test_result = self._execute_code(fixed_test_code)
                        
                        if fixed_test_result.get("success", False):
                            logger.info(f"Component {comp_id} fixed and tests passed")
                            component_code[comp_id] = fixed_code
                            component_status[comp_id] = {
                                "status": "fixed",
                                "test_result": fixed_test_result
                            }
                            
                            # Learn from the fix
                            self.error_db.learn_from_fix(error, language, code, fixed_code, True)
                        else:
                            # Still failed, use the original code
                            logger.warning(f"Component {comp_id} could not be fixed")
                            component_code[comp_id] = code
                            component_status[comp_id] = {
                                "status": "failed",
                                "test_result": fixed_test_result
                            }
                except Exception as e:
                    logger.error(f"Error testing component {comp_id}: {str(e)}")
                    component_code[comp_id] = code
                    component_status[comp_id] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            # Integrate all components
            integrated_code = self._integrate_components(components, component_code, language)
            
            # Execute the integrated code
            try:
                integrated_result = self._execute_code(integrated_code)
                if integrated_result.get("success", False):
                    logger.info("Integrated code executed successfully")
                    final_status = "success"
                else:
                    # Try to fix the integrated code
                    error = integrated_result.get("error", "Unknown error")
                    logger.warning(f"Integrated code execution failed: {error}")
                    
                    # Try to fix with error database first
                    fixed_code = self._fix_code_with_error_db(integrated_code, error, language)
                    
                    if not fixed_code:
                        # If no fix found in database, use LLM
                        fixed_code = self._fix_code_with_llm(integrated_code, error, language)
                    
                    # Test the fixed code
                    fixed_result = self._execute_code(fixed_code)
                    
                    if fixed_result.get("success", False):
                        logger.info("Integrated code fixed and executed successfully")
                        integrated_code = fixed_code
                        integrated_result = fixed_result
                        final_status = "fixed"
                        
                        # Learn from the fix
                        self.error_db.learn_from_fix(error, language, integrated_code, fixed_code, True)
                    else:
                        logger.warning("Integrated code could not be fixed")
                        final_status = "failed"
            except Exception as e:
                logger.error(f"Error executing integrated code: {str(e)}")
                integrated_result = {
                    "success": False,
                    "error": str(e)
                }
                final_status = "error"
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                "status": final_status,
                "code": integrated_code,
                "language": language,
                "components": components,
                "component_status": component_status,
                "execution_result": integrated_result,
                "execution_time": execution_time
            }
        
        except Exception as e:
            logger.error(f"Error in progressive code generation: {str(e)}")
            traceback.print_exc()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                "status": "error",
                "error": str(e),
                "language": language,
                "execution_time": execution_time
            }
    
    def fix_code_progressively(self, code: str, error: str, language: str) -> Dict[str, Any]:
        """Fix code progressively with testing at each step"""
        logger.info(f"Fixing code progressively")
        start_time = time.time()
        
        try:
            # Try to fix with error database first
            fixed_code = self._fix_code_with_error_db(code, error, language)
            
            if fixed_code:
                # Test the fixed code
                try:
                    test_result = self._execute_code(fixed_code)
                    if test_result.get("success", False):
                        logger.info("Code fixed with error database and executed successfully")
                        
                        end_time = time.time()
                        execution_time = end_time - start_time
                        
                        return {
                            "status": "success",
                            "fixed_code": fixed_code,
                            "language": language,
                            "execution_result": test_result,
                            "execution_time": execution_time,
                            "fix_method": "error_database"
                        }
                except Exception:
                    # If execution fails, continue with LLM fix
                    pass
            
            # If no fix found in database or execution failed, use LLM
            fixed_code = self._fix_code_with_llm(code, error, language)
            
            # Test the fixed code
            try:
                test_result = self._execute_code(fixed_code)
                if test_result.get("success", False):
                    logger.info("Code fixed with LLM and executed successfully")
                    
                    # Learn from the fix
                    self.error_db.learn_from_fix(error, language, code, fixed_code, True)
                    
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    return {
                        "status": "success",
                        "fixed_code": fixed_code,
                        "language": language,
                        "execution_result": test_result,
                        "execution_time": execution_time,
                        "fix_method": "llm"
                    }
                else:
                    # If still failing, try one more time with more context
                    new_error = test_result.get("error", "Unknown error")
                    logger.warning(f"First fix attempt failed: {new_error}")
                    
                    prompt = f"""The following {language} code has multiple errors:
```{language}
{code}
```

First error message:
{error}

I tried to fix it, but the fixed code still has errors:
```{language}
{fixed_code}
```

New error message:
{new_error}

Please fix all errors in the code. Only provide the fully corrected code, no explanations.
"""
                    
                    response = self._send_to_llm(prompt)
                    final_fixed_code = self._extract_code_from_llm_response(response)
                    
                    # Test the final fixed code
                    final_test_result = self._execute_code(final_fixed_code)
                    
                    if final_test_result.get("success", False):
                        logger.info("Code fixed with second LLM attempt and executed successfully")
                        
                        # Learn from the fix
                        self.error_db.learn_from_fix(new_error, language, fixed_code, final_fixed_code, True)
                        
                        end_time = time.time()
                        execution_time = end_time - start_time
                        
                        return {
                            "status": "success",
                            "fixed_code": final_fixed_code,
                            "language": language,
                            "execution_result": final_test_result,
                            "execution_time": execution_time,
                            "fix_method": "llm_multi_step"
                        }
                    else:
                        logger.warning("Code could not be fixed after multiple attempts")
                        
                        end_time = time.time()
                        execution_time = end_time - start_time
                        
                        return {
                            "status": "failed",
                            "fixed_code": final_fixed_code,
                            "language": language,
                            "execution_result": final_test_result,
                            "execution_time": execution_time,
                            "fix_method": "llm_multi_step"
                        }
            except Exception as e:
                logger.error(f"Error testing fixed code: {str(e)}")
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                return {
                    "status": "error",
                    "error": str(e),
                    "fixed_code": fixed_code,
                    "language": language,
                    "execution_time": execution_time,
                    "fix_method": "llm"
                }
        
        except Exception as e:
            logger.error(f"Error in progressive code fixing: {str(e)}")
            traceback.print_exc()
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            return {
                "status": "error",
                "error": str(e),
                "language": language,
                "execution_time": execution_time
            }
    
    def handle_requests(self):
        """Handle incoming requests"""
        logger.info("Starting to handle requests...")
        
        while self.running:
            try:
                # Wait for message with timeout
                if self.receiver.poll(timeout=1000) == 0:
                    continue
                
                # Receive request
                request_str = self.receiver.recv_string()
                request = json.loads(request_str)
                
                # Handle request
                request_type = request.get("request_type")
                
                if request_type == "generate":
                    description = request.get("description")
                    language = request.get("language", "python")
                    
                    if not description:
                        response = {
                            "status": "error",
                            "error": "Missing description"
                        }
                    else:
                        result = self.generate_progressive_code(description, language)
                        response = {
                            "status": "success",
                            "result": result
                        }
                
                elif request_type == "fix":
                    code = request.get("code")
                    error = request.get("error")
                    language = request.get("language", "python")
                    
                    if not code or not error:
                        response = {
                            "status": "error",
                            "error": "Missing code or error"
                        }
                    else:
                        result = self.fix_code_progressively(code, error, language)
                        response = {
                            "status": "success",
                            "result": result
                        }
                
                else:
                    response = {
                        "status": "error",
                        "error": f"Unknown request type: {request_type}"
                    }
                
                # Send response
                self.receiver.send_string(json.dumps(response))
            
            except zmq.Again:
                # Timeout, continue loop
                pass
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
    
    def run(self):
        """Run the progressive code generator"""
        try:
            logger.info("Starting Progressive Code Generator...")
            self.handle_requests()
        except KeyboardInterrupt:
            logger.info("Progressive Code Generator interrupted by user")
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.receiver.close()
        self.model_manager.close()
        self.executor.close()
        self.context.term()
        self.error_db.close()
        logger.info("Progressive Code Generator stopped")


if __name__ == "__main__":
    import argparse

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    parser = argparse.ArgumentParser(description="Progressive Code Generator: Builds code incrementally with testing.")
    parser.add_argument('--server', action='store_true', help='Run in server mode, waiting for ZMQ requests')
    args = parser.parse_args()
    
    generator = ProgressiveCodeGenerator()
    
    if args.server:
        # Just initialize the agent and keep it running, waiting for ZMQ requests
        logger.info("Progressive Code Generator running in server mode, waiting for requests...")
        try:
            # Keep the process alive
            generator.handle_requests()
        except KeyboardInterrupt:
            logger.info("Progressive Code Generator interrupted by user")
    else:
        # Run the full agent
        generator.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise