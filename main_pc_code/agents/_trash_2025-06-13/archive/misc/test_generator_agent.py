from main_pc_code.src.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
#!/usr/bin/env python3
# Test Generator Agent - Automatically creates tests for generated code
# Validates code functionality and helps identify issues before execution
# Works with the Chain of Thought and Auto-Fixer agents for better code reliability

import zmq
import json
import os
import threading
import time
import logging
import re
import tempfile
import subprocess
from datetime import datetime
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
from common.utils.log_setup import configure_logging

LOG_PATH = str(PathManager.get_logs_dir() / "test_generator_agent.log")
ZMQ_TEST_GENERATOR_PORT = 5613  # New agent port

logger = configure_logging(__name__)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class TestGeneratorAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="TestGeneratorAgent")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        self.running = True
        # Context for LLM router connection
        self.llm_router_context = zmq.Context()
        self.llm_router_socket = None  # Will be initialized when needed
        self.llm_router_port = 5600  # Default LLM router port
        logging.info(f"[TestGenerator] Agent started on port {zmq_port}")
    
    def connect_llm_router(self):
        """Establish connection to the LLM router"""
        if self.llm_router_socket is None:
            self.llm_router_socket = self.llm_router_context.socket(zmq.REQ)
            self.llm_router_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.llm_router_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.llm_router_socket.connect(f"tcp://127.0.0.1:{self.llm_router_port}")
            logging.info(f"[TestGenerator] Connected to LLM router on port {self.llm_router_port}")
    
    def send_to_llm(self, prompt, model=None, max_tokens=None):
        """
        Send a prompt to the LLM router and get the response
        
        Args:
            prompt (str): The prompt to send to the LLM
            model (str, optional): Specific model to use, or None for router to decide
            max_tokens (int, optional): Maximum tokens in the response
        
        Returns:
            str: The LLM's response
        """
        self.connect_llm_router()
        
        request = {
            "prompt": prompt,
            "type": "code",  # This helps the router choose an appropriate model
        }
        
        if model:
            request["model"] = model
        
        if max_tokens:
            request["max_tokens"] = max_tokens
        
        try:
            self.llm_router_socket.send_string(json.dumps(request))
            response = self.llm_router_socket.recv_string()
            result = json.loads(response)
            return result.get("response", "")
        except Exception as e:
            logging.error(f"[TestGenerator] Error sending to LLM: {str(e)}")
            return f"Error: {str(e)}"
    
    def extract_functions(self, code):
        """
        Extract function definitions from code
        
        Args:
            code (str): The code to extract functions from
            
        Returns:
            list: List of function definitions
        """
        # Simple regex to match function definitions in Python
        # This is a basic implementation - a more robust solution would use ast
        matches = re.finditer(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)', code, re.DOTALL)
        
        functions = []
        for match in matches:
            func_name = match.group(1)
            func_params = match.group(2).strip()
            functions.append({
                "name": func_name,
                "params": func_params
            })
        
        return functions
    
    def extract_classes(self, code):
        """
        Extract class definitions(BaseAgent) from code
        
        Args:
            code (str): The code to extract classes from
            
        Returns:
            list: List of class definitions(BaseAgent)
        """
        # Simple regex to match class definitions(BaseAgent) in Python
        matches = re.finditer(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\((.*?)\))?:', code, re.DOTALL)
        
        classes = []
        for match in matches:
            class_name = match.group(1)
            class_parents = match.group(2).strip() if match.group(2) else ""
            classes.append({
                "name": class_name,
                "parents": class_parents
            })
        
        return classes
    
    def generate_tests(self, code, code_description=None, test_type="unit"):
        """
        Generate tests for the given code
        
        Args:
            code (str): The code to generate tests for
            code_description (str, optional): Description of what the code does
            test_type (str): Type of tests to generate (unit, integration, etc.)
            
        Returns:
            str: The generated tests
        """
        functions = self.extract_functions(code)
        classes = self.extract_classes(code)
        
        prompt = "I need to generate Python tests for some code. "
        
        if test_type == "unit":
            prompt += "Please write pytest-style unit tests.\n\n"
        elif test_type == "integration":
            prompt += "Please write integration tests that ensure components work together.\n\n"
        else:
            prompt += "Please write appropriate tests for this code.\n\n"
        
        if code_description:
            prompt += f"The code is supposed to: {code_description}\n\n"
        
        prompt += f"Here is the code to test:\n```python\n{code}\n```\n\n"
        
        if functions:
            prompt += "The code contains these functions:\n"
            for func in functions:
                prompt += f"- {func['name']}({func['params']})\n"
            prompt += "\n"
        
        if classes:
            prompt += "The code contains these classes:\n"
            for cls in classes:
                if cls['parents']:
                    prompt += f"- {cls['name']}({cls['parents']})\n"
                else:
                    prompt += f"- {cls['name']}\n"
            prompt += "\n"
        
        prompt += "Please generate thorough tests that verify:\n"
        prompt += "1. Normal/expected functionality\n"
        prompt += "2. Edge cases\n"
        prompt += "3. Error handling\n\n"
        
        prompt += "The tests should be executable and include necessary imports. Use pytest fixtures where appropriate."
        
        return self.send_to_llm(prompt)
    
    def run_tests(self, code, tests):
        """
        Run the generated tests against the code
        
        Args:
            code (str): The code to test
            tests (str): The tests to run
            
        Returns:
            dict: Test results
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write the code to a temporary file
            code_path = os.path.join(tmpdir, "module_to_test.py")
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Write the tests to a temporary file
            test_path = os.path.join(tmpdir, "test_module.py")
            with open(test_path, "w", encoding="utf-8") as f:
                # Make sure tests import from the right module
                modified_tests = tests.replace("import module_to_test", "").replace("from module_to_test", "")
                f.write(f"from module_to_test import *\n{modified_tests}")

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
            
            # Run pytest on the tests
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", test_path, "-v"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=30  # Timeout after 30 seconds
                )
                
                passed = "failed" not in result.stdout.lower()
                
                return {
                    "success": passed,
                    "output": result.stdout,
                    "errors": result.stderr
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "output": "Tests timed out after 30 seconds",
                    "errors": "Test execution took too long, possible infinite loop or resource-intensive operation"
                }
            except Exception as e:
                return {
                    "success": False,
                    "output": "",
                    "errors": str(e)
                }
    
    def suggest_fixes(self, code, tests, test_results):
        """
        Suggest fixes for failing tests
        
        Args:
            code (str): The original code
            tests (str): The tests that were run
            test_results (dict): Results from running the tests
            
        Returns:
            str: Suggested fixes for the code
        """
        prompt = "I need help fixing code that failed tests.\n\n"
        
        prompt += f"Original code:\n```python\n{code}\n```\n\n"
        prompt += f"Tests:\n```python\n{tests}\n```\n\n"
        
        prompt += "Test results:\n"
        prompt += f"```\n{test_results['output']}\n```\n\n"
        
        if test_results["errors"]:
            prompt += f"Errors:\n```\n{test_results['errors']}\n```\n\n"
        
        prompt += "Please analyze why the tests failed and provide a fixed version of the original code. Do not change the tests."
        prompt += "Explain what was wrong and how you fixed it."
        
        return self.send_to_llm(prompt)
    
    def generate_and_run_tests(self, code, code_description=None, test_type="unit"):
        """
        Generate tests, run them, and suggest fixes if needed
        
        Args:
            code (str): The code to test
            code_description (str, optional): Description of what the code does
            test_type (str): Type of tests to generate
            
        Returns:
            dict: Results including tests, test results, and suggested fixes
        """
        logging.info(f"[TestGenerator] Generating {test_type} tests")
        tests = self.generate_tests(code, code_description, test_type)
        
        logging.info(f"[TestGenerator] Running tests")
        test_results = self.run_tests(code, tests)
        
        fixes = None
        if not test_results["success"]:
            logging.info(f"[TestGenerator] Tests failed, suggesting fixes")
            fixes = self.suggest_fixes(code, tests, test_results)
        
        return {
            "tests": tests,
            "test_results": test_results,
            "suggested_fixes": fixes,
            "timestamp": time.time()
        }
    
    def handle_query(self, query):
        """
        Process incoming requests to the agent
        
        Args:
            query (dict): The request to process
            
        Returns:
            dict: The response to the request
        """
        action = query.get("action")
        
        if action == "generate_tests":
            code = query.get("code")
            code_description = query.get("description")
            test_type = query.get("test_type", "unit")
            
            if not code:
                return {"status": "error", "message": "No code provided"}
            
            tests = self.generate_tests(code, code_description, test_type)
            return {"status": "ok", "tests": tests}
        
        elif action == "run_tests":
            code = query.get("code")
            tests = query.get("tests")
            
            if not code or not tests:
                return {"status": "error", "message": "Missing code or tests"}
            
            results = self.run_tests(code, tests)
            return {"status": "ok", "results": results}
        
        elif action == "suggest_fixes":
            code = query.get("code")
            tests = query.get("tests")
            test_results = query.get("test_results")
            
            if not code or not tests or not test_results:
                return {"status": "error", "message": "Missing code, tests, or test results"}
            
            fixes = self.suggest_fixes(code, tests, test_results)
            return {"status": "ok", "fixes": fixes}
        
        elif action == "generate_and_run":
            code = query.get("code")
            code_description = query.get("description")
            test_type = query.get("test_type", "unit")
            
            if not code:
                return {"status": "error", "message": "No code provided"}
            
            results = self.generate_and_run_tests(code, code_description, test_type)
            return {"status": "ok", "results": results}
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def run(self):
        """Main agent loop"""
        while self.running:
            try:
                # Wait for next request from client
                message = self.socket.recv_string()
                logging.info(f"[TestGenerator] Received request")
                
                # Parse the request
                query = json.loads(message)
                
                # Process the request
                response = self.handle_query(query)
                
                # Send reply back to client
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logging.error(f"[TestGenerator] Error: {str(e)}")
                # Try to send error response if possible
                try:
                    self.socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        if self.llm_router_socket:
            self.llm_router_socket.close()
        logging.info(f"[TestGenerator] Agent stopping")

# Helper function to send requests to the agent
def send_test_generator_request(request, port=ZMQ_TEST_GENERATOR_PORT):
    """
    Send a request to the Test Generator Agent
    
    Args:
        request (dict): The request to send
        port (int): The port to connect to
        
    Returns:
        dict: The response from the agent
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.connect(f"tcp://127.0.0.1:{port}")
    
    socket.send_string(json.dumps(request))
    response = socket.recv_string()
    
    socket.close()
    context.term()
    
    return json.loads(response)

# Helper functions for other agents to use
def generate_tests(code, description=None, test_type="unit"):
    """
    Generate tests for code
    
    Args:
        code (str): The code to generate tests for
        description (str, optional): Description of what the code does
        test_type (str): Type of tests to generate (unit, integration, etc.)
        
    Returns:
        str: The generated tests
    """
    request = {
        "action": "generate_tests",
        "code": code,
        "description": description,
        "test_type": test_type
    }
    
    response = send_test_generator_request(request)
    return response.get("tests", "") if response.get("status") == "ok" else ""

def test_code(code, description=None):
    """
    Generate and run tests for code, suggesting fixes if tests fail
    
    Args:
        code (str): The code to test
        description (str, optional): Description of what the code does
        
    Returns:
        dict: Results including tests, whether they passed, and suggested fixes
    """
    request = {
        "action": "generate_and_run",
        "code": code,
        "description": description
    }
    
    response = send_test_generator_request(request)
    if response.get("status") == "ok":
        return response.get("results", {})
    else:
        return {"error": response.get("message", "Unknown error")}

def main():
    """Run the Test Generator Agent"""
    agent = TestGeneratorAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        logging.error(f"[TestGenerator] Fatal error: {str(e)}")
    finally:
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