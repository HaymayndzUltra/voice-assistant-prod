import sys
import os
import time
import logging
import threading
import json
import zmq
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from main_pc_code.src.common.data_models import TaskDefinition, TaskResult, TaskStatus
from src.core.base_agent import BaseAgent
from utils.service_discovery_client import get_service_address, register_service
from utils.env_loader import get_env
from main_pc_code.agents.request_coordinator import CircuitBreaker

logger = logging.getLogger("ModelOrchestrator")

class PlanStep(BaseModel):
    step_id: str
    agent_type: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ModelOrchestrator(BaseAgent):
    def __init__(self, port: int = 7010):
        super().__init__(name="ModelOrchestrator", port=port)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{port}")
        self.running = True
        self._register_service()
        self._start_threads()
        logger.info(f"ModelOrchestrator started on port {port}")

        # Circuit breakers for all external services
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

        # ZMQ sockets for external services
        self.model_manager_socket = self._connect_to_service("ModelManagerAgent")
        # Add more as needed (e.g., vision, code, LLM APIs)

        # Context management
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}  # key: conversation_id

    def _init_circuit_breakers(self):
        services = ["ModelManagerAgent"]  # Add more as needed
        for service in services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _connect_to_service(self, service_name: str) -> Optional[zmq.Socket]:
        try:
            service_address = get_service_address(service_name)
            if service_address:
                socket = self.context.socket(zmq.REQ)
                socket.connect(service_address)
                logger.info(f"Connected to {service_name} at {service_address}")
                return socket
            else:
                logger.error(f"Failed to discover {service_name}. Socket will be None.")
                return None
        except Exception as e:
            logger.error(f"Error connecting to {service_name}: {e}")
            return None

    def _register_service(self):
        register_service(
            name=self.name,
            port=self.port,
            additional_info={"capabilities": ["planning", "model_routing", "inference"]}
        )

    def _start_threads(self):
        thread = threading.Thread(target=self._handle_requests, daemon=True)
        thread.start()

    def _send_request(self, service_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Standardized ZMQ request with circuit breaker and error handling.
        """
        socket = None
        if service_name == "ModelManagerAgent":
            socket = self.model_manager_socket
        # Add more services as needed
        cb = self.circuit_breakers.get(service_name)
        if not socket or not cb:
            logger.error(f"Service {service_name} not available or circuit breaker missing.")
            return None
        if not cb.allow_request():
            logger.error(f"Circuit breaker for {service_name} is open. Request blocked.")
            return None
        try:
            socket.send_json(request)
            response = socket.recv_json()
            cb.record_success()
            if not isinstance(response, dict):
                logger.error(f"Non-dict response from {service_name}: {response}")
                return None
            return response
        except Exception as e:
            cb.record_failure()
            logger.error(f"Error sending request to {service_name}: {e}")
            return None

    def _handle_requests(self):
        while self.running:
            try:
                message = self.socket.recv_json()
                if not isinstance(message, dict):
                    self.socket.send_json({"status": "error", "message": "Invalid request format"})
                    continue
                action = message.get("action")
                if action == "break_down_goal":
                    goal = message.get("goal")
                    if not isinstance(goal, dict):
                        response = {"status": "error", "message": "Goal must be a dictionary"}
                    else:
                        response = self._plan_and_execute(goal)
                else:
                    response = {"status": "error", "message": f"Unknown action: {action}"}
                self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error in _handle_requests: {e}")
                self.socket.send_json({"status": "error", "message": str(e)})

    def _plan_and_execute(self, goal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 1: Generate a multi-step plan using ModelManager (LLM)
        Step 2: For each step, select and execute the best model
        Returns a list of TaskDefinition dicts for GoalManager compliance.
        """
        try:
            plan = self._generate_plan(goal)
            conversation_id = goal.get("conversation_id", "default")
            if conversation_id not in self.conversation_history:
                self.conversation_history[conversation_id] = []
            task_definitions = []
            for idx, step in enumerate(plan):
                model = self._select_model_for_step(step)
                result = self._execute_step(step, model, conversation_id)
                self.conversation_history[conversation_id].append({"step": step.dict(), "result": result})
                # Build TaskDefinition for each step
                task_id = f"task_{goal.get('id', 'unknown')}_{idx+1}"
                task_def = TaskDefinition(
                    task_id=task_id,
                    agent_id="ModelOrchestrator",
                    task_type=step.agent_type,
                    priority=goal.get("priority", 5),
                    parameters=step.parameters,
                    dependencies=[],
                    timeout_seconds=goal.get("timeout_seconds"),
                )
                task_definitions.append(task_def.dict())
            return {"status": "success", "tasks": task_definitions}
        except Exception as e:
            logger.error(f"Error in _plan_and_execute: {e}")
            return {"status": "error", "message": str(e)}

    def _generate_plan(self, goal: Dict[str, Any]) -> List[PlanStep]:
        """
        Generate a plan by calling ModelManagerAgent (LLM) via _send_request.
        Uses circuit breaker for resilience.
        """
        request = {"action": "generate_plan", "goal": goal}
        response = self._send_request("ModelManagerAgent", request)
        if (
            response
            and response.get("status") == "success"
            and isinstance(response.get("plan"), list)
        ):
            plan_list = response["plan"]
            valid_steps = []
            for step in plan_list:
                if (
                    isinstance(step, dict)
                    and isinstance(step.get("step_id"), str)
                    and isinstance(step.get("agent_type"), str)
                    and isinstance(step.get("description"), str)
                    and ("parameters" not in step or isinstance(step.get("parameters"), dict))
                ):
                    valid_steps.append(PlanStep(**step))
                else:
                    logger.warning(f"Skipping invalid plan step: {step}")
            return valid_steps
        else:
            raise RuntimeError(f"Invalid plan response: {response}")

    def _select_model_for_step(self, step: PlanStep) -> str:
        """
        Use ModelManagerAgent to recommend the best model for the step.
        """
        request = {"action": "recommend_model", "task_description": step.description}
        response = self._send_request("ModelManagerAgent", request)
        if response and response.get("status") == "success" and isinstance(response.get("model"), str):
            return response["model"]
        else:
            logger.error(f"Model recommendation failed for step: {step.description}. Response: {response}")
            return "default_model"

    def _execute_step(self, step: PlanStep, model: str, conversation_id: str) -> Dict[str, Any]:
        """
        Actually call the selected model (simulate with ModelManagerAgent for now).
        Uses circuit breaker for resilience.
        """
        request = {
            "action": "execute_model",
            "model": model,
            "step": step.dict(),
            "context": self.conversation_history.get(conversation_id, [])
        }
        response = self._send_request("ModelManagerAgent", request)
        if response:
            return response
        else:
            return {"status": "error", "message": "Model execution failed or no response."}

    def run(self):
        logger.info("ModelOrchestrator is running...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            self.socket.close()
            self.context.term()
            logger.info("ModelOrchestrator stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ModelOrchestrator Agent")
    parser.add_argument("--port", type=int, default=7010, help="Port to bind to")
    args = parser.parse_args()
    agent = ModelOrchestrator(port=args.port)
    agent.run() 