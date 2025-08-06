from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import logging
import threading
from typing import Dict, Optional
from datetime import datetime
from main_pc_code.agents.memory_client import MemoryClient
import time
import psutil
from datetime import datetime
from common.utils.log_setup import configure_logging

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

class ChainOfThoughtAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ChainOfThoughtAgent")
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://0.0.0.0:{port}")
        
        # Initialize memory client
        self.memory_client = MemoryClient(port=memory_port)
        
        # Reasoning patterns
        self.reasoning_patterns = {
            "problem_solving": [
                "define_problem",
                "analyze_constraints",
                "generate_solutions",
                "evaluate_solutions",
                "select_best_solution"
            ],
            "code_generation": [
                "understand_requirements",
                "design_structure",
                "implement_core",
                "add_error_handling",
                "optimize_performance"
            ],
            "debugging": [
                "identify_symptoms",
                "locate_cause",
                "test_hypothesis",
                "implement_fix",
                "verify_solution"
            ],
            "tree_of_thought": [
                "generate_initial_thoughts",
                "evaluate_branches",
                "prune_weak_branches",
                "expand_promising_branches",
                "select_best_path"
            ]
        }
        
        # Start processing thread
        self.running = True
        self.process_thread = threading.Thread(target=self._process_requests)
        self.process_thread.start()
        
        logger.info(f"ChainOfThoughtAgent initialized on port {port}")

    def _process_requests(self):
        while self.running:
            try:
                message = self.socket.recv_json()
                response = self._handle_request(message)
                self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                self.socket.send_json({"status": "error", "message": str(e)})

    def _handle_request(self, message: Dict) -> Dict:
        request_type = message.get("request_type", "")
        
        handlers = {
            "start_reasoning": self._start_reasoning,
            "continue_reasoning": self._continue_reasoning,
            "get_reasoning_state": self._get_reasoning_state,
            "store_reasoning_pattern": self._store_reasoning_pattern,
            "get_reasoning_patterns": self._get_reasoning_patterns,
            "health_check": self._health_check,
            "use_chain_of_thought": self._use_chain_of_thought,
            "use_tree_of_thought": self._use_tree_of_thought
        }
        
        handler = handlers.get(request_type)
        if handler:
            return handler(message)
        return {"status": "error", "message": f"Unknown request type: {request_type}"}

    def _use_chain_of_thought(self, message: Dict) -> Dict:
        prompt = message.get("prompt")
        code_context = message.get("code_context")
        
        if not prompt:
            return {"status": "error", "message": "No prompt provided"}
        
        # Start reasoning process
        result = self._start_reasoning({
            "request_type": "start_reasoning",
            "reasoning_type": "problem_solving",
            "context": {
                "prompt": prompt,
                "code_context": code_context
            }
        })
        
        if result["status"] != "success":
            return result
        
        reasoning_id = f"reasoning_problem_solving_{result['state']['start_time']}"
        
        # Process through steps
        current_step = 0
        while current_step < len(self.reasoning_patterns["problem_solving"]):
            step_name = self.reasoning_patterns["problem_solving"][current_step]
            
            # Generate step result based on step type
            step_result = self._generate_step_result(step_name, prompt, code_context)
            
            # Continue reasoning
            result = self._continue_reasoning({
                "request_type": "continue_reasoning",
                "reasoning_id": reasoning_id,
                "step_result": step_result
            })
            
            if result["status"] != "success":
                return result
            
            current_step += 1
        
        # Get final state
        final_state = self._get_reasoning_state({
            "request_type": "get_reasoning_state",
            "reasoning_id": reasoning_id
        })
        
        return {
            "status": "success",
            "reasoning_id": reasoning_id,
            "final_state": final_state["state"]
        }

    def _use_tree_of_thought(self, message: Dict) -> Dict:
        prompt = message.get("prompt")
        code_context = message.get("code_context")
        
        if not prompt:
            return {"status": "error", "message": "No prompt provided"}
        
        # Start tree of thought process
        result = self._start_reasoning({
            "request_type": "start_reasoning",
            "reasoning_type": "tree_of_thought",
            "context": {
                "prompt": prompt,
                "code_context": code_context
            }
        })
        
        if result["status"] != "success":
            return result
        
        reasoning_id = f"reasoning_tree_of_thought_{result['state']['start_time']}"
        
        # Process through steps
        current_step = 0
        while current_step < len(self.reasoning_patterns["tree_of_thought"]):
            step_name = self.reasoning_patterns["tree_of_thought"][current_step]
            
            # Generate step result based on step type
            step_result = self._generate_tree_step_result(step_name, prompt, code_context)
            
            # Continue reasoning
            result = self._continue_reasoning({
                "request_type": "continue_reasoning",
                "reasoning_id": reasoning_id,
                "step_result": step_result
            })
            
            if result["status"] != "success":
                return result
            
            current_step += 1
        
        # Get final state
        final_state = self._get_reasoning_state({
            "request_type": "get_reasoning_state",
            "reasoning_id": reasoning_id
        })
        
        return {
            "status": "success",
            "reasoning_id": reasoning_id,
            "final_state": final_state["state"]
        }

    def _generate_step_result(self, step_name: str, prompt: str, code_context: Optional[str] = None) -> Dict:
        # This is a simplified implementation. In a real system, this would use an LLM
        # to generate appropriate responses for each step.
        if step_name == "define_problem":
            return {
                "problem_definition": f"Analyzing prompt: {prompt}",
                "key_aspects": ["Understanding requirements", "Identifying constraints"]
            }
        elif step_name == "analyze_constraints":
            return {
                "constraints": ["Time complexity", "Resource usage", "Code quality"],
                "priority": "High"
            }
        elif step_name == "generate_solutions":
            return {
                "solutions": ["Solution 1", "Solution 2", "Solution 3"],
                "approach": "Iterative improvement"
            }
        elif step_name == "evaluate_solutions":
            return {
                "evaluation": {
                    "Solution 1": {"pros": ["Fast"], "cons": ["Complex"]},
                    "Solution 2": {"pros": ["Simple"], "cons": ["Slow"]},
                    "Solution 3": {"pros": ["Balanced"], "cons": ["Medium complexity"]}
                }
            }
        elif step_name == "select_best_solution":
            return {
                "selected_solution": "Solution 3",
                "reasoning": "Best balance of performance and complexity"
            }
        return {"status": "error", "message": f"Unknown step: {step_name}"}

    def _generate_tree_step_result(self, step_name: str, prompt: str, code_context: Optional[str] = None) -> Dict:
        # This is a simplified implementation. In a real system, this would use an LLM
        # to generate appropriate responses for each step.
        if step_name == "generate_initial_thoughts":
            return {
                "thoughts": ["Thought 1", "Thought 2", "Thought 3"],
                "confidence": [0.8, 0.6, 0.7]
            }
        elif step_name == "evaluate_branches":
            return {
                "evaluations": {
                    "Thought 1": {"score": 0.8, "reasoning": "Most promising"},
                    "Thought 2": {"score": 0.6, "reasoning": "Moderate potential"},
                    "Thought 3": {"score": 0.7, "reasoning": "Good alternative"}
                }
            }
        elif step_name == "prune_weak_branches":
            return {
                "pruned": ["Thought 2"],
                "remaining": ["Thought 1", "Thought 3"]
            }
        elif step_name == "expand_promising_branches":
            return {
                "expansions": {
                    "Thought 1": ["Sub-thought 1.1", "Sub-thought 1.2"],
                    "Thought 3": ["Sub-thought 3.1", "Sub-thought 3.2"]
                }
            }
        elif step_name == "select_best_path":
            return {
                "selected_path": "Thought 1 -> Sub-thought 1.1",
                "confidence": 0.9,
                "reasoning": "Most complete and promising solution"
            }
        return {"status": "error", "message": f"Unknown step: {step_name}"}

    def _start_reasoning(self, message: Dict) -> Dict:
        reasoning_type = message.get("reasoning_type")
        initial_context = message.get("context", {})
        
        if reasoning_type not in self.reasoning_patterns:
            return {"status": "error", "message": f"Unknown reasoning type: {reasoning_type}"}
        
        # Create reasoning state
        state = {
            "type": reasoning_type,
            "current_step": 0,
            "steps": self.reasoning_patterns[reasoning_type],
            "context": initial_context,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        
        # Store in memory
        self.memory_client.store_memory(
            f"reasoning_{reasoning_type}_{datetime.now().timestamp()}",
            state,
            "short_term"
        )
        
        return {
            "status": "success",
            "message": "Reasoning started",
            "state": state
        }

    def _continue_reasoning(self, message: Dict) -> Dict:
        reasoning_id = message.get("reasoning_id")
        step_result = message.get("step_result")
        
        # Retrieve current state
        state_result = self.memory_client.retrieve_memory(reasoning_id)
        if state_result["status"] != "success":
            return {"status": "error", "message": "Reasoning state not found"}
        
        state = state_result["memory"]["value"]
        current_step = state["current_step"]
        
        # Update state with step result
        if "results" not in state:
            state["results"] = []
        state["results"].append({
            "step": current_step,
            "step_name": state["steps"][current_step],
            "result": step_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Move to next step
        state["current_step"] += 1
        
        # Check if reasoning is complete
        if state["current_step"] >= len(state["steps"]):
            state["status"] = "completed"
            state["end_time"] = datetime.now().isoformat()
        
        # Update in memory
        self.memory_client.store_memory(reasoning_id, state, "short_term")
        
        return {
            "status": "success",
            "message": "Reasoning step completed",
            "state": state
        }

    def _get_reasoning_state(self, message: Dict) -> Dict:
        reasoning_id = message.get("reasoning_id")
        state_result = self.memory_client.retrieve_memory(reasoning_id)
        
        if state_result["status"] != "success":
            return {"status": "error", "message": "Reasoning state not found"}
        
        return {
            "status": "success",
            "state": state_result["memory"]["value"]
        }

    def _store_reasoning_pattern(self, message: Dict) -> Dict:
        pattern_type = message.get("pattern_type")
        pattern = message.get("pattern")
        
        if not isinstance(pattern, list):
            return {"status": "error", "message": "Pattern must be a list of steps"}
        
        self.reasoning_patterns[pattern_type] = pattern
        
        # Store in long-term memory
        self.memory_client.store_memory(
            f"reasoning_pattern_{pattern_type}",
            pattern,
            "long_term"
        )
        
        return {"status": "success", "message": "Reasoning pattern stored"}

    def _get_reasoning_patterns(self, message: Dict) -> Dict:
        pattern_type = message.get("pattern_type")
        
        if pattern_type:
            patterns = {pattern_type: self.reasoning_patterns.get(pattern_type, [])}
        else:
            patterns = self.reasoning_patterns
        
        return {
            "status": "success",
            "patterns": patterns
        }

    def _health_check(self, message: Dict) -> Dict:
        # Check memory client health
        memory_health = self.memory_client.health_check()
        
        return {
            "status": "healthy",
            "memory_status": memory_health["status"],
            "reasoning_patterns": len(self.reasoning_patterns)
        }

    def shutdown(self):
        self.running = False
        self.process_thread.join()
        self.socket.close()
        self.context.term()
        self.memory_client.close()
        logger.info("ChainOfThoughtAgent shutdown complete")


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

if __name__ == "__main__":
    agent = ChainOfThoughtAgent()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        agent.shutdown() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise