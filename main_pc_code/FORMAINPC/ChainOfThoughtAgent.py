#!/usr/bin/env python3
# Chain-of-Thought Agent - Implements multi-step reasoning for more reliable code generation
# Transforms a single request into a sequence of reasoning steps
# Helps LLMs break down problems and avoid common errors

import zmq
import json
import os
import threading
import time
import logging
import re
import sys
from pathlib import Path
from datetime import datetime
import traceback
import psutil

# Add the parent directory to sys.path to import the config
from main_pc_code.utils.config_loader import load_config
config = load_config()
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# === PHASE A: BASEAGENT INHERITANCE ===

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

config = load_config()

# Configure log directory
logs_dir = Path(config.get('system.logs_dir', 'logs'))
logs_dir.mkdir(exist_ok=True)
LOG_PATH = logs_dir / "chain_of_thought_agent.log"
ZMQ_CHAIN_OF_THOUGHT_PORT = 5612  # Chain of Thought port
REMOTE_CONNECTOR_PORT = 5557  # Remote Connector Agent port for model inference

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ChainOfThoughtAgent")

class ChainOfThoughtAgent(BaseAgent):
    def __init__(self, port: int = 5612, name: str = "ChainOfThoughtAgent", **kwargs):
        # Use _agent_args if port or name are not provided
        agent_port = port if port is not None else config.get("port", 5612)
        agent_name = name if name is not None else config.get("name", 'ChainOfThoughtAgent')
        super().__init__(name=str(agent_name), port=int(agent_port))
        logger.info("=" * 80)
        logger.info("Initializing Chain of Thought Agent")
        logger.info("=" * 80)
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{agent_port}")
        self.running = True
        
        # Context for Remote Connector Agent connection
        self.llm_router_context = zmq.Context()
        self.llm_router_socket = None  # Will be initialized when needed
        self.llm_router_port = REMOTE_CONNECTOR_PORT  # Use Remote Connector for model inference
        
        # Record start time for uptime tracking
        self.start_time = time.time()
        
        # Track statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info(f"Chain of Thought Agent started on port {agent_port}")
        logger.info(f"Remote Connector port: {self.llm_router_port}")
        logger.info("=" * 80)
    
    def connect_llm_router(self):
        """Establish connection to the Remote Connector Agent for model inference"""
        if self.llm_router_socket is None:
            self.llm_router_socket = self.llm_router_context.socket(zmq.REQ)
            self.llm_router_socket.connect(f"tcp://127.0.0.1:{self.llm_router_port}")
            logger.info(f"[ChainOfThought] Connected to Remote Connector Agent on port {self.llm_router_port}")
    
    def send_to_llm(self, prompt, model=None, max_tokens=None):
        """
        Send a prompt to the Remote Connector Agent for model inference
        
        Args:
            prompt (str): The prompt to send to the LLM
            model (str, optional): Specific model to use, or None for default
            max_tokens (int, optional): Maximum tokens in the response
        
        Returns:
            str: The LLM's response
        """
        if self.llm_router_socket is None:
            self.connect_llm_router()
        
        # Format request for Remote Connector Agent
        request = {
            "request_type": "generate",
            "prompt": prompt,
            "model": model if model else "phi3",  # Use phi3 as default if no model specified
            "temperature": 0.7
        }
        
        if max_tokens:
            request["max_tokens"] = max_tokens
        
        try:
            logger.info(f"[ChainOfThought] Sending request to Remote Connector for model {request['model']}")
            self.llm_router_socket.send_string(json.dumps(request))
            
            # Use a longer timeout for inference
            poller = zmq.Poller()
            poller.register(self.llm_router_socket, zmq.POLLIN)
            
            if poller.poll(30000):  # 30 second timeout
                response = self.llm_router_socket.recv_string()
                result = json.loads(response)
                
                if result.get("status") == "success":
                    return result.get("response", "")
                else:
                    error_msg = result.get("error", "Unknown error from Remote Connector")
                    logger.error(f"[ChainOfThought] Error from Remote Connector: {error_msg}")
                    return f"Error: {error_msg}"
            else:
                logger.error("[ChainOfThought] Timeout waiting for Remote Connector response")
                return "Error: Timeout waiting for model response"
                
        except Exception as e:
            logger.error(f"[ChainOfThought] Error sending to Remote Connector: {str(e)}")
            return f"Error: {str(e)}"
    
    def generate_problem_breakdown(self, user_request, code_context=None):
        """
        First step: Break down the problem into smaller steps
        
        Args:
            user_request (str): The original user request
            code_context (str, optional): Any relevant code context
        
        Returns:
            list: A list of steps to solve the problem
        """
        prompt = "I need to break down a coding task into clear, logical steps.\n\n"
        prompt += f"Task: {user_request}\n\n"
        
        if code_context:
            prompt += f"Relevant Code Context:\n```\n{code_context}\n```\n\n"
        
        prompt += "Break this task down into a numbered list of steps. Each step should be specific and achievable. Include planning steps and validation steps."
        
        response = self.send_to_llm(prompt)
        
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
    
    def generate_solution_for_step(self, step, previous_steps_info, code_context=None):
        """
        Second step: Generate a solution for a specific step
        
        Args:
            step (str): The step to generate a solution for
            previous_steps_info (list): Information about previous steps
            code_context (str, optional): Any relevant code context
        
        Returns:
            str: The generated solution for this step
        """
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
        
        return self.send_to_llm(prompt)
    
    def verify_solution(self, step, solution, code_context=None):
        """
        Third step: Verify the generated solution for issues
        
        Args:
            step (str): The step being implemented
            solution (str): The generated solution
            code_context (str, optional): Any relevant code context
        
        Returns:
            dict: Verification results with issues and suggestions
        """
        prompt = "I need to review code for potential issues before implementation.\n\n"
        prompt += f"The code implements this task: {step}\n\n"
        
        prompt += f"Code to review:\n```\n{solution}\n```\n\n"
        
        if code_context:
            prompt += f"Existing code context:\n```\n{code_context}\n```\n\n"
        
        prompt += "Review the code for these issues:\n"
        prompt += "1. Is it syntactically correct?\n"
        prompt += "2. Does it handle edge cases?\n"
        prompt += "3. Are there potential runtime errors?\n"
        prompt += "4. Does it follow best practices?\n"
        prompt += "5. Will it integrate well with existing code?\n\n"
        
        prompt += "List any issues found and suggest fixes. If no issues are found, state that the code looks good."
        
        verification = self.send_to_llm(prompt)
        
        # Determine if there are serious issues
        has_issues = "issue" in verification.lower() or "problem" in verification.lower() or "error" in verification.lower()
        # Check if the verification explicitly says the code is good
        looks_good = "looks good" in verification.lower() or "no issues" in verification.lower()
        
        return {
            "verification": verification,
            "has_issues": has_issues and not looks_good,
            "looks_good": looks_good
        }
    
    def refine_solution(self, step, original_solution, verification_results, code_context=None):
        """
        Fourth step: If verification found issues, refine the solution
        
        Args:
            step (str): The step being implemented
            original_solution (str): The original generated solution
            verification_results (dict): Results from the verification step
            code_context (str, optional): Any relevant code context
        
        Returns:
            str: The refined solution
        """
        prompt = "I need to fix issues in code based on review feedback.\n\n"
        prompt += f"The code implements this task: {step}\n\n"
        
        prompt += f"Original code:\n```\n{original_solution}\n```\n\n"
        
        prompt += f"Review feedback:\n{verification_results['verification']}\n\n"
        
        if code_context:
            prompt += f"Existing code context:\n```\n{code_context}\n```\n\n"
        
        prompt += "Provide an improved version of the code that addresses all issues mentioned in the review feedback."
        
        return self.send_to_llm(prompt)
    
    def generate_combined_solution(self, steps_with_solutions, user_request, code_context=None):
        """
        Final step: Combine all step solutions into a coherent whole
        
        Args:
            steps_with_solutions (list): List of steps and their solutions
            user_request (str): The original user request
            code_context (str, optional): Any relevant code context
        
        Returns:
            str: The complete solution
        """
        prompt = "I need to combine multiple code components into a cohesive solution.\n\n"
        prompt += f"Original task: {user_request}\n\n"
        
        if code_context:
            prompt += f"Existing code context:\n```\n{code_context}\n```\n\n"
        
        prompt += "Here are the components implementing each step:\n\n"
        
        for i, step_info in enumerate(steps_with_solutions):
            prompt += f"Step {i+1}: {step_info['step']}\n"
            prompt += f"```\n{step_info['solution']}\n```\n\n"
        
        prompt += "Combine these components into a complete, well-organized solution that accomplishes the original task. Eliminate redundancy and ensure all components work together seamlessly."
        
        return self.send_to_llm(prompt)
    
    def generate_with_cot(self, user_request, code_context=None):
        """
        Main function to generate code using Chain of Thought reasoning
        
        Args:
            user_request (str): The user's code generation request
            code_context (str, optional): Any relevant code context
        
        Returns:
            dict: Result containing the solution and the reasoning process
        """
        logger.info(f"[ChainOfThought] Starting CoT generation for: {user_request[:50]}...")
        
        # Step 1: Break down the problem
        steps = self.generate_problem_breakdown(user_request, code_context)
        logger.info(f"[ChainOfThought] Problem broken down into {len(steps)} steps")
        
        # Step 2 & 3 & 4: For each step, generate and verify a solution
        steps_with_solutions = []
        for i, step in enumerate(steps):
            logger.info(f"[ChainOfThought] Generating solution for step {i+1}/{len(steps)}")
            
            # Generate solution for this step
            solution = self.generate_solution_for_step(
                step, 
                steps_with_solutions,  # Pass info about previous steps
                code_context
            )
            
            # Verify the solution
            verification = self.verify_solution(step, solution, code_context)
            
            # If issues were found, refine the solution
            if verification["has_issues"]:
                logger.info(f"[ChainOfThought] Issues found in step {i+1}, refining solution")
                solution = self.refine_solution(step, solution, verification, code_context)
                # Re-verify after refinement
                verification = self.verify_solution(step, solution, code_context)
            
            # Record this step's info
            steps_with_solutions.append({
                "step": step,
                "solution": solution,
                "verification": verification
            })
        
        # Step 5: Combine all solutions
        logger.info(f"[ChainOfThought] Combining all solutions")
        combined_solution = self.generate_combined_solution(
            steps_with_solutions,
            user_request,
            code_context
        )
        
        return {
            "solution": combined_solution,
            "steps": steps_with_solutions,
            "request": user_request,
            "timestamp": time.time()
        }
    
    def _get_health_status(self):
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}

    def handle_query(self, query):
        """Handle incoming ZMQ requests"""
        try:
            logger.info(f"Received request: {json.dumps(query)}")
            self.total_requests += 1
            
            request_type = query.get("request_type", "")
            
            if request_type == "health_check":
                logger.info("Processing health check request")
                response = self._get_health_status()
                logger.info(f"Health check response: {json.dumps(response)}")
                return response
            
            elif request_type == "generate":
                # Handle code generation request
                user_request = query.get("prompt", "")
                code_context = query.get("code_context")
                
                logger.info(f"Processing code generation request - prompt length: {len(user_request)}")
                if code_context:
                    logger.info(f"Code context provided - length: {len(code_context)}")
                
                result = self.generate_with_cot(user_request, code_context)
                
                if result.get("status") == "success":
                    self.successful_requests += 1
                else:
                    self.failed_requests += 1
                
                logger.info(f"Code generation completed - status: {result.get('status')}")
                return result
            
            else:
                error_msg = f"Unknown request type: {request_type}"
                logger.error(error_msg)
                self.failed_requests += 1
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.failed_requests += 1
            return {"status": "error", "message": error_msg}
    
    def run(self):
        """Run the Chain of Thought Agent"""
        logger.info("Starting Chain of Thought Agent main loop")
        while self.running:
            try:
                # Use a timeout to allow checking for shutdown
                if self.socket.poll(1000) == 0:  # 1 second timeout
                    continue
                
                # Receive request
                request_str = self.socket.recv_string()
                logger.debug(f"Received raw request: {request_str}")
                
                try:
                    request = json.loads(request_str)
                except json.JSONDecodeError:
                    error_msg = "Invalid JSON in request"
                    logger.error(error_msg)
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": error_msg
                    }))
                    continue
                
                # Process request
                response = self.handle_query(request)
                
                # Send response
                logger.debug(f"Sending response: {json.dumps(response)}")
                self.socket.send_string(json.dumps(response))
                
            except zmq.error.Again:
                # Socket timeout, continue
                continue
            except Exception as e:
                error_msg = f"Error in main loop: {str(e)}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                try:
                    self.socket.send_string(json.dumps({
                        "status": "error",
                        "message": error_msg
                    }))
                except:
                    pass
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        if self.llm_router_socket:
            self.llm_router_socket.close()
        logger.info(f"[ChainOfThought] Agent stopping")

# Helper function to send requests to the agent
def send_cot_request(request, port=ZMQ_CHAIN_OF_THOUGHT_PORT):
    """
    Send a request to the Chain of Thought Agent
    
    Args:
        request (dict): The request to send
        port (int): The port to connect to
    
    Returns:
        dict: The response from the agent
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://127.0.0.1:{port}")
    
    socket.send_string(json.dumps(request))
    response = socket.recv_string()
    
    socket.close()
    context.term()
    
    return json.loads(response)

# Helper functions for other agents to use
def generate_code_with_cot(user_request, code_context=None):
    """
    Generate code using Chain of Thought reasoning
    
    Args:
        user_request (str): The user's code generation request
        code_context (str, optional): Any relevant code context
    
    Returns:
        str: The generated code solution
    """
    request = {
        "action": "generate",
        "request": user_request,
        "code_context": code_context
    }
    
    response = send_cot_request(request)
    if response.get("status") == "ok":
        return response.get("result", {}).get("solution", "")
    else:
        return f"Error: {response.get('message', 'Unknown error')}"

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ChainOfThoughtAgent()
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
