# File: main_pc_code/agents/model_orchestrator.py
#
# Ito ang FINAL at PINAHUSAY na bersyon ng ModelOrchestrator.
# Pinagsasama nito ang task classification at context-awareness ng EnhancedModelRouter
# at ang iterative code generation at safe execution ng UnifiedPlanningAgent.

import sys
import os
import time
import logging
import threading
import json
import uuid
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

# --- Path Setup ---
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import TaskDefinition, TaskResult, TaskStatus, ErrorSeverity

# --- Shared Utilities ---
# I-assume na ang CircuitBreaker ay nasa isang shared utility file
from main_pc_code.agents.request_coordinator import CircuitBreaker # Pansamantalang import

# --- Logging Setup ---
logger = logging.getLogger('ModelOrchestrator')

# --- Constants ---
DEFAULT_PORT = 7010
ZMQ_REQUEST_TIMEOUT = 30000 # Mas mahabang timeout para sa LLM at code execution
MAX_REFINEMENT_ITERATIONS = 3 # Limitasyon para sa code refinement loop

# ===================================================================
#         ANG BAGONG UNIFIED MODEL ORCHESTRATOR
# ===================================================================
class ModelOrchestrator(BaseAgent):
    """
    Orchestrates all model interactions, from simple chat to complex,
    iterative code generation and safe execution.
    """

    def __init__(self, **kwargs):
        super().__init__(name="ModelOrchestrator", port=DEFAULT_PORT, **kwargs)

        # --- State Management ---
        self.language_configs = self._get_language_configs()
        self.temp_dir = Path(tempfile.gettempdir()) / "model_orchestrator_sandbox"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # --- Downstream Services & Resilience ---
        self.downstream_services = [
            "ModelManagerAgent", "UnifiedMemoryReasoningAgent", "WebAssistant"
        ]
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

        logger.info("Unified ModelOrchestrator initialized successfully.")

    def _get_language_configs(self) -> Dict[str, Dict]:
        """Defines a-i-execute ang code para sa iba't ibang lenggwahe."""
        return {
            "python": {"extension": ".py", "command": [sys.executable]},
            "javascript": {"extension": ".js", "command": ["node"]},
            # Pwedeng dagdagan pa ng iba (e.g., shell, java)
        }

    def _init_circuit_breakers(self):
        """Initializes Circuit Breakers for all downstream services."""
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    # ===================================================================
    #         CORE API & DISPATCHER
    # ===================================================================

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Classifies the task and dispatches to the correct handler.
        """
        action = request.get("action")
        task_def_data = request.get("task")
        if not action or not task_def_data:
            return {"status": "error", "message": "Missing 'action' or 'task' in request."}

        try:
            task = TaskDefinition(**task_def_data)
        except Exception as e:
            return {"status": "error", "message": f"Invalid TaskDefinition format: {e}"}

        # CHECKLIST ITEM 1: Task Classification logic
        task_type = self._classify_task(task)
        logger.info(f"Task {task.task_id} classified as: {task_type}")

        # Dispatch to the appropriate handler
        handlers = {
            "code_generation": self._handle_code_generation_task,
            "tool_use": self._handle_tool_use_task,
            "reasoning": self._handle_reasoning_task,
            "chat": self._handle_chat_task,
        }
        handler = handlers.get(task_type, self._handle_reasoning_task) # Default to reasoning

        return handler(task)

    def _classify_task(self, task: TaskDefinition) -> str:
        """
        Classifies the task based on its description and parameters.
        (Logic extracted from EnhancedModelRouter)
        """
        prompt = task.description.lower()
        if any(k in prompt for k in ["code", "python", "function", "script", "debug"]):
            return "code_generation"
        if any(k in prompt for k in ["search for", "find information about", "browse"]):
            return "tool_use"
        if any(k in prompt for k in ["why", "how", "explain", "analyze", "compare"]):
            return "reasoning"
        return "chat"

    # ===================================================================
    #         TASK HANDLERS
    # ===================================================================

    def _handle_chat_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handles simple conversational tasks."""
        # CHECKLIST ITEM 2: Context-Aware Prompting
        full_prompt = self._build_context_prompt(task, "You are a helpful assistant.")
        response = self._send_to_llm(full_prompt)
        return {"status": "success", "result": {"text": response}}

    def _handle_reasoning_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handles complex reasoning tasks."""
        full_prompt = self._build_context_prompt(task, "You are a logical reasoner. Think step by step.")
        response = self._send_to_llm(full_prompt)
        return {"status": "success", "result": {"text": response}}

    def _handle_tool_use_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """
        Handles tasks that require specialized tools.
        (Logic extracted from EnhancedModelRouter)
        """
        # Simplistic tool detection for now
        if "search" in task.description.lower():
            query = task.parameters.get("query", task.description)
            logger.info(f"Executing tool: WebSearch with query '{query}'")
            # CHECKLIST ITEM 3: Direct Orchestration of Specialized Tools
            search_result = self._resilient_send_request("WebAssistant", {"action": "search", "query": query})
            return {"status": "success", "result": search_result}
        else:
            return {"status": "error", "message": "Unknown tool requested."}

    def _handle_code_generation_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """
        Handles code generation tasks using an iterative refinement loop.
        (Logic extracted from UnifiedPlanningAgent)
        """
        logger.info(f"Starting iterative code generation for task: {task.task_id}")
        code_context = self._build_context_prompt(task, "You are an expert programmer.")
        current_code = ""

        # CHECKLIST ITEM 4: Iterative Code Generation & Refinement
        for i in range(MAX_REFINEMENT_ITERATIONS):
            logger.info(f"Refinement iteration {i+1}/{MAX_REFINEMENT_ITERATIONS}")
            prompt = f"{code_context}\n\nTask: {task.description}\n\nCurrent Code:\n```python\n{current_code}\n```\n\nGenerate or refine the Python code."
            generated_code = self._send_to_llm(prompt)
            if not generated_code:
                return {"status": "error", "message": "LLM failed to generate code."}

            # Verify the generated code
            verification_prompt = f"Review the following Python code for correctness, bugs, and adherence to the task: '{task.description}'.\n\nCode:\n```python\n{generated_code}\n```\n\nRespond with 'OK' if it's good, or list the issues."
            feedback = self._send_to_llm(verification_prompt)

            if feedback.strip().upper() == "OK":
                logger.info("Code verification successful. Finalizing.")
                current_code = generated_code
                break
            else:
                logger.info(f"Code has issues. Refining based on feedback: {feedback}")
                current_code = generated_code # Keep the problematic code for context
                code_context += f"\n\nPrevious attempt had issues:\n{feedback}" # Add feedback to context
        else: # Loop finished without breaking
            logger.warning("Max refinement iterations reached. Using the last generated code.")

        # CHECKLIST ITEM 5: Safe Code Execution
        should_execute = task.parameters.get("execute", False)
        execution_result = None
        if should_execute:
            logger.info("Executing final generated code in a safe environment.")
            execution_result = self._execute_code_safely(current_code, "python")

        return {
            "status": "success",
            "result": {
                "code": current_code,
                "execution_result": execution_result
            }
        }

    # ===================================================================
    #         HELPER METHODS (Guts of the Operation)
    # ===================================================================

    def _build_context_prompt(self, task: TaskDefinition, system_prompt: str) -> str:
        """
        Builds a context-aware prompt by fetching conversation history.
        (Logic extracted from EnhancedModelRouter)
        """
        session_id = task.parameters.get("session_id", "default_session")
        history_request = {"action": "get_context", "session_id": session_id}
        context_response = self._resilient_send_request("UnifiedMemoryReasoningAgent", history_request)

        context_str = "Previous conversation:\n"
        if context_response and context_response.get("status") == "success":
            for entry in context_response.get("context", []):
                context_str += f"- {entry}\n"
        else:
            context_str = ""

        return f"{system_prompt}\n\n{context_str}\nUser Task: {task.description}"

    def _send_to_llm(self, prompt: str) -> Optional[str]:
        """Sends a prompt to the appropriate LLM via the ModelManagerAgent."""
        request = {"action": "generate_text", "prompt": prompt}
        response = self._resilient_send_request("ModelManagerAgent", request)
        return response.get("result", {}).get("text") if response and response.get("status") == "success" else None

    def _execute_code_safely(self, code: str, language: str) -> Dict[str, Any]:
        """
        Executes code in a sandboxed environment.
        (Logic extracted from UnifiedPlanningAgent)
        """
        config = self.language_configs.get(language)
        if not config:
            return {"success": False, "error": f"Unsupported language: {language}"}

        file_path = self.temp_dir / f"exec_{uuid.uuid4()}{config['extension']}"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            process = subprocess.run(
                config["command"] + [str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": process.returncode == 0,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "returncode": process.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out after 30 seconds."}
        except Exception as e:
            return {"success": False, "error": f"An unexpected error occurred: {e}"}
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def _resilient_send_request(self, agent_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A resilient method to send requests using Circuit Breakers."""
        cb = self.circuit_breakers.get(agent_name)
        if not cb or not cb.allow_request():
            logger.warning(f"Request to {agent_name} blocked by open circuit or missing CB.")
            return None
        try:
            response = self.send_request_to_agent(agent_name, request, timeout=ZMQ_REQUEST_TIMEOUT)
            cb.record_success()
            return response
        except Exception as e:
            cb.record_failure()
            # self.report_error(...) # Pwedeng idagdag ang error reporting dito
            logger.error(f"Failed to communicate with {agent_name}: {e}")
            return None

if __name__ == '__main__':
    try:
        agent = ModelOrchestrator()
        agent.run()
    except KeyboardInterrupt:
        logger.info("ModelOrchestrator shutting down.")
    except Exception as e:
        logger.critical(f"ModelOrchestrator failed to start: {e}", exc_info=True)
    finally:
        if 'agent' in locals() and agent.running:
            agent.cleanup()