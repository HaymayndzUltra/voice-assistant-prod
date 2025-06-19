from src.core.base_agent import BaseAgent
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
from datetime import datetime

LOG_PATH = "chain_of_thought_agent.log"
ZMQ_CHAIN_OF_THOUGHT_PORT = 5613  # Main PC CoT Agent port
CGA_PORT = 5604  # Main PC CodeGeneratorAgent port

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class ChainOfThoughtAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ChainOfThoughtAgent")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
        self.running = True
        self.cga_context = zmq.Context()
        self.cga_socket = None  # Will be initialized when needed
        self.cga_port = CGA_PORT
        logging.info(f"[ChainOfThought] Agent started on port {zmq_port}")
    
    def connect_cga(self):
        """Establish connection to the Main PC CodeGeneratorAgent for model inference"""
        if self.cga_socket is None:
            self.cga_socket = self.cga_context.socket(zmq.REQ)
            self.cga_socket.connect(f"tcp://127.0.0.1:{self.cga_port}")
            logging.info(f"[ChainOfThought] Connected to CodeGeneratorAgent on port {self.cga_port}")
    
    def send_to_llm(self, prompt, model_id="wizardcoder-python", system_prompt=None, max_tokens=1024, temperature=0.7):
        """
        Send a prompt to the Main PC CodeGeneratorAgent for GGUF model inference
        """
        self.connect_cga()
        request = {
            "action": "generate_with_gguf",
            "model_id": model_id,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        # Remove None fields
        request = {k: v for k, v in request.items() if v is not None}
        try:
            logging.info(f"[ChainOfThought] Sending request to CGA for model {model_id}")
            self.cga_socket.send_string(json.dumps(request))
            poller = zmq.Poller()
            poller.register(self.cga_socket, zmq.POLLIN)
            if poller.poll(30000):  # 30s timeout
                response = self.cga_socket.recv_string()
                result = json.loads(response)
                if result.get("status") == "success":
                    return result.get("text", "")
                else:
                    error_msg = result.get("error", "Unknown error from CGA")
                    logging.error(f"[ChainOfThought] Error from CGA: {error_msg}")
                    return f"Error: {error_msg}"
            else:
                logging.error("[ChainOfThought] Timeout waiting for CGA response")
                return "Error: Timeout waiting for model response"
        except Exception as e:
            logging.error(f"[ChainOfThought] Error sending to CGA: {str(e)}")
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
        logging.info(f"[ChainOfThought] Starting CoT generation for: {user_request[:50]}...")
        
        # Step 1: Break down the problem
        steps = self.generate_problem_breakdown(user_request, code_context)
        logging.info(f"[ChainOfThought] Problem broken down into {len(steps)} steps")
        
        # Step 2 & 3 & 4: For each step, generate and verify a solution
        steps_with_solutions = []
        for i, step in enumerate(steps):
            logging.info(f"[ChainOfThought] Generating solution for step {i+1}/{len(steps)}")
            
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
                logging.info(f"[ChainOfThought] Issues found in step {i+1}, refining solution")
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
        logging.info(f"[ChainOfThought] Combining all solutions")
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
    
    def handle_query(self, query):
        """
        Process incoming requests to the agent
        
        Args:
            query (dict): The request to process
        
        Returns:
            dict: The response to the request
        """
        action = query.get("action")
        
        if action == "health_check":
            return {"status": "healthy", "service": "MainPC_CoT_Agent"}
        
        elif action == "generate":
            user_request = query.get("request")
            code_context = query.get("code_context")
            
            if not user_request:
                return {"status": "error", "message": "No request provided"}
            
            result = self.generate_with_cot(user_request, code_context)
            return {"status": "ok", "result": result}
        
        elif action == "generate_step":
            step = query.get("step")
            previous_steps = query.get("previous_steps", [])
            code_context = query.get("code_context")
            
            if not step:
                return {"status": "error", "message": "No step provided"}
            
            solution = self.generate_solution_for_step(step, previous_steps, code_context)
            return {"status": "ok", "solution": solution}
        
        elif action == "verify":
            step = query.get("step")
            solution = query.get("solution")
            code_context = query.get("code_context")
            
            if not solution:
                return {"status": "error", "message": "No solution provided"}
            
            verification = self.verify_solution(step, solution, code_context)
            return {"status": "ok", "verification": verification}
        
        elif action == "refine":
            step = query.get("step")
            solution = query.get("solution")
            verification = query.get("verification")
            code_context = query.get("code_context")
            
            if not solution or not verification:
                return {"status": "error", "message": "Missing solution or verification"}
            
            refined = self.refine_solution(step, solution, verification, code_context)
            return {"status": "ok", "refined": refined}
        
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def run(self):
        """Main agent loop"""
        while self.running:
            try:
                # Wait for next request from client
                message = self.socket.recv_string()
                logging.info(f"[ChainOfThought] Received request")
                
                # Parse the request
                query = json.loads(message)
                
                # Process the request
                response = self.handle_query(query)
                
                # Send reply back to client
                self.socket.send_string(json.dumps(response))
                
            except Exception as e:
                logging.error(f"[ChainOfThought] Error: {str(e)}")
                # Try to send error response if possible
                try:
                    self.socket.send_string(json.dumps({"status": "error", "message": str(e)}))
                except:
                    pass
    
    def stop(self):
        """Stop the agent"""
        self.running = False
        if self.cga_socket:
            self.cga_socket.close()
        logging.info(f"[ChainOfThought] Agent stopping")

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

def main():
    """Run the Chain of Thought Agent"""
    agent = ChainOfThoughtAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        logging.error(f"[ChainOfThought] Fatal error: {str(e)}")
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
