"""
Multi-Agent Swarm Manager
------------------
Manages a swarm of specialized agents to accomplish complex tasks:
- Decomposes high-level goals into specific tasks
- Coordinates execution across multiple agents
- Synthesizes results from different agents
- Handles task prioritization and scheduling
"""

import zmq
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import threading
from queue import Queue
import asyncio
import traceback

from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_parser import parse_agent_args
from main_pc_code.utils.service_discovery_client import discover_service, register_service, get_service_address
from main_pc_code.utils.env_loader import get_env
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, configure_secure_client, configure_secure_server

# Parse command line arguments
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('swarm_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
SWARM_MANAGER_PORT = 5645  # Main port for SwarmManager
if hasattr(_agent_args, 'port'):
    SWARM_MANAGER_PORT = int(_agent_args.port)
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Get bind address from environment variables with default to a safe value for Docker compatibility
BIND_ADDRESS = get_env('BIND_ADDRESS', '0.0.0.0')

# Secure ZMQ configuration
SECURE_ZMQ = is_secure_zmq_enabled()

class SwarmTask:
    def __init__(self, task_id: str, goal: str, priority: int):
        """Initialize a swarm task."""
        self.task_id = task_id
        self.goal = goal
        self.priority = priority
        self.status = 'pending'
        self.steps = []
        self.results = []
        self.start_time = None
        self.end_time = None
        self.final_result = None
        self.error = None
    
    def add_step(self, step: Dict[str, Any]):
        """Add a step to the task."""
        self.steps.append({
            'step_id': f"step_{len(self.steps) + 1}",
            'description': step['description'],
            'agent': step['agent'],
            'action': step['action'],
            'parameters': step.get('parameters', {}),
            'status': 'pending',
            'result': None
        })
    
    def update_step(self, step_index: int, status: str, result: Any = None):
        """Update a step's status and result."""
        if 0 <= step_index < len(self.steps):
            self.steps[step_index]['status'] = status
            if result is not None:
                self.steps[step_index]['result'] = result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            'task_id': self.task_id,
            'goal': self.goal,
            'priority': self.priority,
            'status': self.status,
            'steps': self.steps,
            'results': self.results,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'final_result': self.final_result,
            'error': self.error
        }

class MultiAgentSwarmManager(BaseAgent):
    """Agent for managing and coordinating a swarm of specialized agents."""
    
    def __init__(self):
        """Initialize the multi-agent swarm manager."""
        # Standard BaseAgent initialization at the beginning
        self.config = _agent_args
        super().__init__(
            name=getattr(self.config, 'name', 'MultiAgentSwarmManager'),
            port=getattr(self.config, 'port', SWARM_MANAGER_PORT)
        )
        
        # Initialize state
        self.start_time = time.time()
        self.port = SWARM_MANAGER_PORT
        self.bind_address = get_env('BIND_ADDRESS', '0.0.0.0')
        self.zmq_timeout = int(getattr(self.config, 'zmq_request_timeout', 5000))
        self.context = zmq.Context()
        
        # REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, self.zmq_timeout)
        self.socket.setsockopt(zmq.SNDTIMEO, self.zmq_timeout)
        
        # Apply secure ZMQ if enabled
        if SECURE_ZMQ:
            self.socket = configure_secure_server(self.socket)
            logger.info("Secure ZMQ enabled for MultiAgentSwarmManager")
        
        # Bind to address using BIND_ADDRESS for Docker compatibility
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.socket.bind(bind_address)
        logger.info(f"MultiAgentSwarmManager bound to {bind_address}")
        
        # Register with service discovery
        self._register_service()
        
        # REQ socket for CoordinatorAgent (LLM access)
        self.coordinator_socket = self._create_service_socket("CoordinatorAgent")
        if not self.coordinator_socket:
            logger.error("Failed to connect to CoordinatorAgent")
        
        # REQ socket for AutoGen Framework
        self.autogen_socket = self._create_service_socket("AutoGenFramework")
        if not self.autogen_socket:
            logger.error("Failed to connect to AutoGenFramework")
        
        # Poller for non-blocking socket operations
        self.poller = zmq.Poller()
        if self.coordinator_socket:
            self.poller.register(self.coordinator_socket, zmq.POLLIN)
        if self.autogen_socket:
            self.poller.register(self.autogen_socket, zmq.POLLIN)
        
        # Task management
        self.tasks = {}  # task_id -> SwarmTask
        self.task_queue = Queue()
        self.task_results = {}
        
        # Agent registry - will be populated from AutoGen Framework
        self.available_agents = {}
        
        # Start task processor
        self.processor_thread = threading.Thread(target=self._process_tasks)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        # Start agent discovery thread
        self.discovery_thread = threading.Thread(target=self._discover_agents)
        self.discovery_thread.daemon = True
        self.discovery_thread.start()
        
        # Track metrics for health status
        self.processed_tasks = 0
        self.active_tasks = 0
        self.failed_tasks = 0
        
        logger.info("Multi-Agent Swarm Manager initialized")
    
    def _register_service(self):
        """Register this agent with the service discovery system"""
        try:
            register_result = register_service(
                name="MultiAgentSwarmManager",
                port=self.port,
                additional_info={
                    "capabilities": ["swarm_management", "task_orchestration", "agent_coordination"],
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
                    "CoordinatorAgent": 5590,
                    "AutoGenFramework": 5650
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
    
    def _discover_agents(self):
        """Periodically discover available agents from AutoGen Framework."""
        while True:
            try:
                if not self.autogen_socket:
                    logger.warning("AutoGen socket not available, skipping agent discovery")
                    time.sleep(60)
                    continue
                    
                # Request agent list from AutoGen Framework
                self.autogen_socket.send_json({
                    "action": "get_agents"
                })
                
                # Wait for response with timeout
                socks = dict(self.poller.poll(5000))  # 5 second timeout
                if self.autogen_socket in socks and socks[self.autogen_socket] == zmq.POLLIN:
                    response = self.autogen_socket.recv_json()
                    
                    if response.get('status') == 'success':
                        self.available_agents = response.get('agents', {})
                        logger.info(f"Discovered {len(self.available_agents)} agents")
                    else:
                        logger.error(f"Error discovering agents: {response.get('message')}")
                else:
                    logger.warning("Timeout waiting for agent discovery response")
            
            except Exception as e:
                logger.error(f"Error in agent discovery: {str(e)}")
            
            # Sleep before next discovery
            time.sleep(60)  # Check every minute
    
    def plan_and_execute(self, goal: str, priority: int = 1) -> Dict[str, Any]:
        """Plan and execute a high-level goal using specialist agents.
        
        Args:
            goal: High-level goal description
            priority: Task priority (1-10, higher is more important)
            
        Returns:
            Dictionary with task details and status
        """
        try:
            # Generate task ID
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            
            # Create task
            task = SwarmTask(task_id, goal, priority)
            
            # Decompose goal into steps
            steps = self._decompose_goal(goal)
            if not steps:
                return {
                    'status': 'error',
                    'message': 'Failed to decompose goal into steps',
                    'task_id': task_id
                }
            
            # Add steps to task
            for step in steps:
                task.add_step(step)
            
            # Store task
            self.tasks[task_id] = task
            
            # Add to queue for processing
            self.task_queue.put(task_id)
            
            return {
                'status': 'success',
                'message': f'Task {task_id} created and queued for execution',
                'task_id': task_id,
                'task': task.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error in plan_and_execute: {str(e)}")
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f'Error planning task: {str(e)}'
            }
    
    def _decompose_goal(self, goal: str) -> List[Dict[str, Any]]:
        """Decompose a high-level goal into actionable steps using LLM.
        
        Args:
            goal: High-level goal description
            
        Returns:
            List of steps, each with agent, action, and parameters
        """
        try:
            # Create system prompt for decomposition
            system_prompt = """
            You are a planning AI that decomposes high-level goals into specific steps for specialist agents.
            
            Available agents and their capabilities:
            1. UnifiedWebAgent: web search, information gathering, scraping websites
            2. KnowledgeBase: storing and retrieving facts, user preferences
            3. MemoryManager: short-term memory for conversations
            4. EmotionEngine: detecting and processing emotional states
            5. PersonalityEngine: adjusting response style based on emotions
            6. EmpathyAgent: determining appropriate voice settings for responses
            
            For each step in the plan:
            1. Provide a clear description of what needs to be done
            2. Specify which agent should handle it
            3. Define the action the agent should take
            4. Include any necessary parameters
            
            Your response should be a JSON array of steps, each with these fields:
            - description: Clear description of the step
            - agent: Name of the agent to handle this step
            - action: Specific action for the agent to perform
            - parameters: Dictionary of parameters needed for the action
            
            Make sure the steps are in logical order and cover all aspects needed to achieve the goal.
            """
            
            # Send request to CoordinatorAgent for LLM inference
            request_id = f"decompose_{int(time.time())}"
            self.coordinator_socket.send_json({
                'action': 'request_model_inference',
                'model_name': 'default',
                'system_prompt': system_prompt,
                'prompt': goal,
                'temperature': 0.2,
                'request_id': request_id
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(30000))  # 30 second timeout
            if self.coordinator_socket in socks and socks[self.coordinator_socket] == zmq.POLLIN:
                response = self.coordinator_socket.recv_json()
                
                if response.get('status') == 'success':
                    # Parse the response
                    result = response.get('result', '')
                    
                    # Extract JSON array from the result
                    import re
                    json_match = re.search(r'\[.*\]', result, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        steps = json.loads(json_str)
                        logger.info(f"Decomposed goal into {len(steps)} steps")
                        return steps
                    else:
                        # Try to parse the whole result as JSON
                        try:
                            steps = json.loads(result)
                            if isinstance(steps, list):
                                logger.info(f"Decomposed goal into {len(steps)} steps")
                                return steps
                        except json.JSONDecodeError:
                            logger.error("Failed to parse LLM response as JSON")
                            
                    logger.error(f"Invalid response format from LLM: {result}")
                    return []
                else:
                    logger.error(f"Error from CoordinatorAgent: {response.get('message')}")
                    return []
            else:
                logger.error("Timeout waiting for LLM response")
                return []
                
        except Exception as e:
            logger.error(f"Error in _decompose_goal: {str(e)}")
            traceback.print_exc()
            return []
    
    def _execute_step(self, task: SwarmTask, step_index: int) -> Dict[str, Any]:
        """Execute a single step using the appropriate agent.
        
        Args:
            task: The task containing the step
            step_index: Index of the step to execute
            
        Returns:
            Response from the agent
        """
        try:
            step = task.steps[step_index]
            agent = step['agent']
            action = step['action']
            parameters = step.get('parameters', {})
            
            logger.info(f"Executing step {step_index + 1} of task {task.task_id}: {step['description']}")
            
            # Create message for agent
            message = {
                "sender": "swarm_manager",
                "receiver": agent,
                "message_type": "task_step",
                "content": {
                    "task_id": task.task_id,
                    "step_id": step['step_id'],
                    "action": action,
                    "parameters": parameters,
                    "description": step['description'],
                    "context": {
                        "goal": task.goal,
                        "step_number": step_index + 1,
                        "total_steps": len(task.steps)
                    }
                }
            }
            
            # Send message through AutoGen Framework
            self.autogen_socket.send_json({
                "action": "send_message",
                "message": message
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(60000))  # 60 second timeout
            if self.autogen_socket in socks and socks[self.autogen_socket] == zmq.POLLIN:
                response = self.autogen_socket.recv_json()
                
                if response.get('status') == 'success':
                    # The message was sent successfully, but we need to wait for the agent's response
                    # In a real implementation, this would involve a callback or polling mechanism
                    # For now, we'll simulate a response
                    
                    # TODO: Implement proper response handling from agents
                    # This is a placeholder for the actual agent response
                    agent_response = {
                        'status': 'success',
                        'result': f"Simulated response from {agent} for action {action}",
                        'message': f"Step {step_index + 1} completed successfully"
                    }
                    
                    return agent_response
                else:
                    logger.error(f"Error sending message to {agent}: {response.get('message')}")
                    return {
                        'status': 'error',
                        'message': f"Failed to communicate with {agent}: {response.get('message')}"
                    }
            else:
                logger.error(f"Timeout waiting for response from AutoGen Framework")
                return {
                    'status': 'error',
                    'message': f"Timeout waiting for response from AutoGen Framework"
                }
            
        except Exception as e:
            logger.error(f"Error executing step: {str(e)}")
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _synthesize_results(self, task: SwarmTask) -> Dict[str, Any]:
        """Synthesize results from all steps into a final result.
        
        Args:
            task: The completed task
            
        Returns:
            Final synthesized result
        """
        try:
            # Collect results from all steps
            step_results = []
            for step in task.steps:
                if step['result'] is not None:
                    step_results.append({
                        'description': step['description'],
                        'agent': step['agent'],
                        'result': step['result']
                    })
            
            # Create system prompt for synthesis
            system_prompt = """
            You are an AI that synthesizes results from multiple steps into a coherent final answer.
            
            The user's original goal was:
            {goal}
            
            The following steps were executed to achieve this goal:
            {steps}
            
            Please synthesize these results into a comprehensive, coherent response that directly addresses the user's goal.
            Focus on providing a clear, concise answer that integrates all the information gathered.
            Ensure your response is well-structured and easy to understand.
            """
            
            # Format steps for the prompt
            steps_text = ""
            for i, result in enumerate(step_results):
                steps_text += f"Step {i+1}: {result['description']}\n"
                steps_text += f"Agent: {result['agent']}\n"
                steps_text += f"Result: {result['result']}\n\n"
            
            # Replace placeholders in system prompt
            system_prompt = system_prompt.format(
                goal=task.goal,
                steps=steps_text
            )
            
            # Send request to CoordinatorAgent for LLM inference
            request_id = f"synthesize_{task.task_id}"
            self.coordinator_socket.send_json({
                'action': 'request_model_inference',
                'model_name': 'default',
                'system_prompt': system_prompt,
                'prompt': f"Please synthesize the results for the goal: {task.goal}",
                'temperature': 0.3,
                'request_id': request_id
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(30000))  # 30 second timeout
            if self.coordinator_socket in socks and socks[self.coordinator_socket] == zmq.POLLIN:
                response = self.coordinator_socket.recv_json()
                
                if response.get('status') == 'success':
                    # Get the synthesized result
                    synthesized_result = response.get('result', '')
                    return {
                        'status': 'success',
                        'result': synthesized_result
                    }
                else:
                    logger.error(f"Error from CoordinatorAgent: {response.get('message')}")
                    return {
                        'status': 'error',
                        'message': f"Failed to synthesize results: {response.get('message')}"
                    }
            else:
                logger.error("Timeout waiting for LLM response during synthesis")
                return {
                    'status': 'error',
                    'message': "Timeout waiting for result synthesis"
                }
                
        except Exception as e:
            logger.error(f"Error synthesizing results: {str(e)}")
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f"Error synthesizing results: {str(e)}"
            }
    
    def _process_tasks(self):
        """Process tasks from the queue."""
        while True:
            try:
                # Get next task
                task_id = self.task_queue.get()
                task = self.tasks[task_id]
                
                # Update task status
                task.status = 'in_progress'
                task.start_time = datetime.now().isoformat()
                
                # Execute each step
                all_steps_successful = True
                for i in range(len(task.steps)):
                    # Execute step
                    result = self._execute_step(task, i)
                    
                    # Update step status
                    status = result.get('status', 'error')
                    task.update_step(i, status, result)
                    
                    # Check for failure
                    if status == 'error':
                        all_steps_successful = False
                        task.error = result.get('message', 'Unknown error')
                        break
                    
                    # Add result to task results
                    task.results.append(result)
                
                # Synthesize results if all steps were successful
                if all_steps_successful:
                    synthesis = self._synthesize_results(task)
                    if synthesis.get('status') == 'success':
                        task.final_result = synthesis.get('result')
                        task.status = 'completed'
                    else:
                        task.error = synthesis.get('message', 'Failed to synthesize results')
                        task.status = 'failed'
                else:
                    task.status = 'failed'
                
                # Update task end time
                task.end_time = datetime.now().isoformat()
                
                # Store results
                self.task_results[task_id] = task.to_dict()
                logger.info(f"Task {task_id} {task.status}")
                
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
                traceback.print_exc()
                time.sleep(1)
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task."""
        if task_id in self.tasks:
            return {
                'status': 'success',
                'task': self.tasks[task_id].to_dict()
            }
        elif task_id in self.task_results:
            return {
                'status': 'success',
                'task': self.task_results[task_id]
            }
        else:
            return {
                'status': 'error',
                'message': f'Task not found: {task_id}'
            }
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """Get all tasks."""
        active_tasks = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
        completed_tasks = {task_id: task for task_id, task in self.task_results.items() 
                          if task_id not in active_tasks}
        
        return {
            'status': 'success',
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the swarm manager."""
        return {
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'active_tasks': len(self.tasks),
            'completed_tasks': len(self.task_results),
            'available_agents': len(self.available_agents),
            'agent_list': list(self.available_agents.keys())
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
            
        elif action == 'plan_and_execute':
            goal = request.get('goal')
            priority = request.get('priority', 1)
            
            if not goal:
                return {'status': 'error', 'message': 'Missing required parameter: goal'}
                
            return self.plan_and_execute(goal, priority)
            
        elif action == 'get_task_status':
            task_id = request.get('task_id')
            
            if not task_id:
                return {'status': 'error', 'message': 'Missing required parameter: task_id'}
                
            return self.get_task_status(task_id)
            
        elif action == 'get_all_tasks':
            return self.get_all_tasks()
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def run(self):
        """Run the main loop."""
        logger.info("Starting Multi-Agent Swarm Manager main loop")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                traceback.print_exc()
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.ZMQError as zmq_err:
                    logger.error(f"ZMQ error sending response: {zmq_err}")
    
    def stop(self):
        """Stop the swarm manager and clean up resources."""
        logger.info("Stopping Multi-Agent Swarm Manager")
        
        # Stop threads
        try:
            # Join threads with timeout to avoid hanging
            if hasattr(self, 'processor_thread') and self.processor_thread.is_alive():
                self.processor_thread.join(timeout=2.0)
                if self.processor_thread.is_alive():
                    logger.warning("Processor thread did not terminate gracefully")
            
            if hasattr(self, 'discovery_thread') and self.discovery_thread.is_alive():
                self.discovery_thread.join(timeout=2.0)
                if self.discovery_thread.is_alive():
                    logger.warning("Discovery thread did not terminate gracefully")
        except Exception as e:
            logger.error(f"Error stopping threads: {e}")
        
        # Close sockets in a try-finally block to ensure they're all closed
        try:
            if hasattr(self, 'socket'):
                self.socket.close()
                logger.debug("Closed main socket")
            
            if hasattr(self, 'coordinator_socket') and self.coordinator_socket:
                self.coordinator_socket.close()
                logger.debug("Closed coordinator socket")
            
            if hasattr(self, 'autogen_socket') and self.autogen_socket:
                self.autogen_socket.close()
                logger.debug("Closed autogen socket")
            
            if hasattr(self, 'poller'):
                # Unregister sockets from poller
                if hasattr(self, 'coordinator_socket') and self.coordinator_socket:
                    try:
                        self.poller.unregister(self.coordinator_socket)
                    except:
                        pass
                
                if hasattr(self, 'autogen_socket') and self.autogen_socket:
                    try:
                        self.poller.unregister(self.autogen_socket)
                    except:
                        pass
        except Exception as e:
            logger.error(f"Error during socket cleanup: {e}")
        finally:
            # Terminate ZMQ context
            if hasattr(self, 'context'):
                self.context.term()
                logger.debug("Terminated ZMQ context")
        
        logger.info("Multi-Agent Swarm Manager stopped successfully")

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

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'multi_agent_swarm_manager',
            'components': {
                'coordinator_connected': self.coordinator_socket is not None,
                'autogen_connected': self.autogen_socket is not None,
                'task_processor': hasattr(self, 'processor_thread') and self.processor_thread.is_alive(),
                'agent_discovery': hasattr(self, 'discovery_thread') and self.discovery_thread.is_alive()
            },
            'status_detail': 'active',
            'processed_tasks': getattr(self, 'processed_tasks', 0),
            'active_tasks': len(self.tasks) if hasattr(self, 'tasks') else 0,
            'failed_tasks': getattr(self, 'failed_tasks', 0),
            'available_agents': len(self.available_agents) if hasattr(self, 'available_agents') else 0,
            'uptime': time.time() - self.start_time
        }

    def cleanup(self):
        """Gracefully shutdown the agent"""
        logger.info("Cleaning up MultiAgentSwarmManager")
        
        # Close sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'coordinator_socket'):
            self.coordinator_socket.close()
        if hasattr(self, 'autogen_socket'):
            self.autogen_socket.close()
            
        # Clean up ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
            
        # Call parent cleanup
        super().cleanup()
        logger.info("MultiAgentSwarmManager cleanup complete")

# Example usage
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = MultiAgentSwarmManager()
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