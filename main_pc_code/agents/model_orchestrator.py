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
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pickle
from datetime import datetime
import psutil # Added for health check


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
# --- Path Setup ---
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import TaskDefinition, TaskResult, TaskStatus, ErrorSeverity
from main_pc_code.utils.config_loader import load_config
from main_pc_code.agents.request_coordinator import CircuitBreaker # Pansamantalang import

# --- Logging Setup ---
logger = logging.getLogger('ModelOrchestrator')

# Load configuration at the module level
config = load_config()

# --- Constants ---
DEFAULT_PORT = config.get('model_orchestrator_port', 7010)
HEALTH_CHECK_PORT = config.get('model_orchestrator_health_port', 8010)
ZMQ_REQUEST_TIMEOUT = config.get('zmq_request_timeout', 30000) # Mas mahabang timeout para sa LLM at code execution
MAX_REFINEMENT_ITERATIONS = config.get('max_refinement_iterations', 3) # Limitasyon para sa code refinement loop

# --- Embedding Model Constants ---
EMBEDDING_MODEL_NAME = config.get('embedding_model', "all-MiniLM-L6-v2")  # Lightweight but effective sentence embedding model
EMBEDDING_CACHE_FILE = config.get('embedding_cache_file', join_path("data", "task_embeddings_cache.pkl"))
EMBEDDING_DIMENSION = 384  # Dimension of embeddings from the model

# --- Metrics Constants ---
METRICS_LOG_INTERVAL = config.get('metrics_log_interval', 60)  # Log metrics every 60 seconds
METRICS_SAVE_INTERVAL = config.get('metrics_save_interval', 300)  # Save metrics to file every 5 minutes
METRICS_FILE = config.get('metrics_file', join_path("logs", "model_orchestrator_metrics.json"))

# ===================================================================
#         ANG BAGONG UNIFIED MODEL ORCHESTRATOR
# ===================================================================
class ModelOrchestrator(BaseAgent):
    """
    Orchestrates all model interactions, from simple chat to complex,
    iterative code generation and safe execution.
    """

    def __init__(self, **kwargs):
        super().__init__(name="ModelOrchestrator", port=DEFAULT_PORT, 
                         health_check_port=HEALTH_CHECK_PORT, **kwargs)

        # --- State Management ---
        self.language_configs = self._get_language_configs()
        self.temp_dir = Path(tempfile.gettempdir()) / "model_orchestrator_sandbox"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # --- Task Classification Components ---
        self.embedding_model = None
        self.task_type_embeddings = {}
        self.embedding_cache_path = Path(EMBEDDING_CACHE_FILE)
        self._init_embedding_model()
        self._load_task_embeddings()

        # --- Metrics and Telemetry ---
        self.metrics = {
            "requests_total": 0,
            "requests_by_type": {
                "code_generation": 0,
                "tool_use": 0,
                "reasoning": 0,
                "chat": 0
            },
            "response_times": {
                "code_generation": [],
                "tool_use": [],
                "reasoning": [],
                "chat": []
            },
            "success_rate": {
                "code_generation": {"success": 0, "failure": 0},
                "tool_use": {"success": 0, "failure": 0},
                "reasoning": {"success": 0, "failure": 0},
                "chat": {"success": 0, "failure": 0}
            },
            "classification": {
                "embedding_based": 0,
                "keyword_based": 0
            }
        }
        self.metrics_lock = threading.Lock()
        self.last_metrics_log = time.time()
        self.last_metrics_save = time.time()
        self._load_metrics()

        # --- Downstream Services & Resilience ---
        self.downstream_services = [
            "ModelManagerAgent", "UnifiedMemoryReasoningAgent", "WebAssistant"
        ]
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

        # --- Setup Error Reporting ---
        self.error_bus = self.setup_error_reporting()

        # --- Start Background Threads ---
        self.running = True
        self.metrics_thread = threading.Thread(target=self._metrics_reporting_loop, daemon=True)
        self.metrics_thread.start()

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
            
    def _init_embedding_model(self):
        """Initialize the sentence transformer embedding model for task classification."""
        try:
            # Import here to avoid dependency issues if not available
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.warning("sentence_transformers not available. Falling back to keyword-based classification.")
            self.embedding_model = None
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None

    def setup_error_reporting(self):
        """Set up error reporting to the central error bus."""
        try:
            # Import here to avoid circular imports
            from main_pc_code.agents.error_bus_client import ErrorBusClient
            error_bus = ErrorBusClient(
                component_name=self.name,
                component_type="agent",
                max_retry=3
            )
            logger.info("Error reporting set up successfully")
            return error_bus
        except Exception as e:
            logger.error(f"Failed to set up error reporting: {e}")
            return None

    def report_error(self, error_message, severity=ErrorSeverity.WARNING, 
                    context=None, exception=None):
        """Report an error to the error bus."""
        if self.error_bus:
            try:
                self.error_bus.report_error(
                    error_message=error_message,
                    severity=severity,
                    context=context or {},
                    exception=exception
                )
            except Exception as e:
                logger.error(f"Failed to report error to error bus: {e}")
        else:
            logger.error(f"Error bus not available. Error: {error_message}")

    def _load_task_embeddings(self):
        """Load or initialize task type embeddings."""
        # Define example tasks for each category
        task_examples = {
            "code_generation": [
                "Write a Python function to calculate fibonacci numbers",
                "Create a JavaScript class for handling API requests",
                "Debug this code that has an infinite loop",
                "Implement a sorting algorithm in Python",
                "Fix the syntax error in this function",
                "Create a script to process CSV files",
                "Write a function that validates email addresses"
            ],
            "tool_use": [
                "Search for information about climate change",
                "Find the latest news about AI advancements",
                "Look up the weather forecast for tomorrow",
                "Browse for articles about machine learning",
                "Find information about the history of computers",
                "Search for recent research papers on natural language processing",
                "Find documentation for the pandas library"
            ],
            "reasoning": [
                "Explain how quantum computing works",
                "Analyze the impact of social media on mental health",
                "Compare and contrast different machine learning algorithms",
                "Why does the sky appear blue?",
                "How does climate change affect biodiversity?",
                "Explain the principles of object-oriented programming",
                "What are the ethical implications of AI development?"
            ],
            "chat": [
                "Hello, how are you today?",
                "What's your name?",
                "Tell me a joke",
                "Can you help me with something?",
                "What can you do?",
                "I'm feeling sad today",
                "Let's talk about movies"
            ]
        }
        
        # Try to load cached embeddings
        if self.embedding_cache_path.exists() and self.embedding_model:
            try:
                with open(self.embedding_cache_path, 'rb') as f:
                    self.task_type_embeddings = pickle.load(f)
                logger.info(f"Loaded task embeddings from cache: {len(self.task_type_embeddings)} task types")
                return
            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")
        
        # Generate embeddings if model is available
        if self.embedding_model:
            logger.info("Generating task type embeddings...")
            for task_type, examples in task_examples.items():
                try:
                    # Generate embeddings for all examples of this task type
                    embeddings = self.embedding_model.encode(examples)
                    # Store the mean embedding as the prototype for this task type
                    self.task_type_embeddings[task_type] = np.mean(embeddings, axis=0)
                except Exception as e:
                    logger.error(f"Error generating embeddings for {task_type}: {e}")
            
            # Save the embeddings to cache
            try:
                os.makedirs(os.path.dirname(self.embedding_cache_path), exist_ok=True)
                with open(self.embedding_cache_path, 'wb') as f:
                    pickle.dump(self.task_type_embeddings, f)
                logger.info(f"Saved task embeddings to cache")
            except Exception as e:
                logger.warning(f"Failed to save embedding cache: {e}")
    
    def _load_metrics(self):
        """Load metrics from file if it exists."""
        try:
            metrics_path = Path(METRICS_FILE)
            if metrics_path.exists():
                with open(metrics_path, 'r') as f:
                    saved_metrics = json.load(f)
                    with self.metrics_lock:
                        # Only load the counts and rates, not the detailed timing data
                        self.metrics["requests_total"] = saved_metrics.get("requests_total", 0)
                        self.metrics["requests_by_type"] = saved_metrics.get("requests_by_type", self.metrics["requests_by_type"])
                        self.metrics["success_rate"] = saved_metrics.get("success_rate", self.metrics["success_rate"])
                        self.metrics["classification"] = saved_metrics.get("classification", self.metrics["classification"])
                logger.info(f"Loaded metrics from {metrics_path}")
        except Exception as e:
            logger.warning(f"Failed to load metrics from file: {e}")
    
    def _save_metrics(self):
        """Save metrics to file."""
        try:
            metrics_path = Path(METRICS_FILE)
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            
            # Create a copy of metrics with summarized response times
            metrics_to_save = {}
            with self.metrics_lock:
                metrics_to_save = {k: v for k, v in self.metrics.items() if k != "response_times"}
                
                # Calculate average response times
                avg_response_times = {}
                for task_type, times in self.metrics["response_times"].items():
                    if times:
                        avg_response_times[task_type] = sum(times) / len(times)
                    else:
                        avg_response_times[task_type] = 0
                
                metrics_to_save["avg_response_times"] = avg_response_times
                
                # Add timestamp
                metrics_to_save["last_updated"] = datetime.now().isoformat()
            
            with open(metrics_path, 'w') as f:
                json.dump(metrics_to_save, f, indent=2)
            
            logger.info(f"Saved metrics to {metrics_path}")
        except Exception as e:
            logger.warning(f"Failed to save metrics to file: {e}")
    
    def _metrics_reporting_loop(self):
        """Background thread for metrics reporting and saving."""
        while True:
            current_time = time.time()
            
            # Log metrics at regular intervals
            if current_time - self.last_metrics_log >= METRICS_LOG_INTERVAL:
                self._log_metrics()
                self.last_metrics_log = current_time
            
            # Save metrics to file at regular intervals
            if current_time - self.last_metrics_save >= METRICS_SAVE_INTERVAL:
                self._save_metrics()
                self.last_metrics_save = current_time
            
            # Sleep to avoid high CPU usage
            time.sleep(5)
    
    def _log_metrics(self):
        """Log current metrics."""
        with self.metrics_lock:
            logger.info(f"ModelOrchestrator Metrics - Total Requests: {self.metrics['requests_total']}")
            
            # Calculate success rates
            success_rates = {}
            for task_type, counts in self.metrics["success_rate"].items():
                total = counts["success"] + counts["failure"]
                rate = (counts["success"] / total * 100) if total > 0 else 0
                success_rates[task_type] = f"{rate:.1f}%"
            
            # Calculate average response times
            avg_times = {}
            for task_type, times in self.metrics["response_times"].items():
                if times:
                    # Only consider the last 100 requests for average
                    recent_times = times[-100:]
                    avg_times[task_type] = f"{sum(recent_times) / len(recent_times):.2f}s"
                else:
                    avg_times[task_type] = "N/A"
            
            # Log detailed metrics
            logger.info(f"Requests by Type: {self.metrics['requests_by_type']}")
            logger.info(f"Success Rates: {success_rates}")
            logger.info(f"Avg Response Times: {avg_times}")
            logger.info(f"Classification Method: Embedding: {self.metrics['classification']['embedding_based']}, " +
                       f"Keyword: {self.metrics['classification']['keyword_based']}")

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

    # ===================================================================
    #         CORE API & DISPATCHER
    # ===================================================================

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point. Classifies the task and dispatches to the correct handler.
        """
        start_time = time.time()
        
        action = request.get("action")
        task_def_data = request.get("task")
        if not action or not task_def_data:
            return {"status": "error", "message": "Missing 'action' or 'task' in request."}

        try:
            task = TaskDefinition(**task_def_data)
        except Exception as e:
            return {"status": "error", "message": f"Invalid TaskDefinition format: {e}"}

        # Enhanced task classification
        task_type = self._classify_task(task)
        logger.info(f"Task {task.task_id} classified as: {task_type}")
        
        # Update request metrics
        with self.metrics_lock:
            self.metrics["requests_total"] += 1
            if task_type in self.metrics["requests_by_type"]:
                self.metrics["requests_by_type"][task_type] += 1

        # Dispatch to the appropriate handler
        handlers = {
            "code_generation": self._handle_code_generation_task,
            "tool_use": self._handle_tool_use_task,
            "reasoning": self._handle_reasoning_task,
            "chat": self._handle_chat_task,
        }
        handler = handlers.get(task_type, self._handle_reasoning_task) # Default to reasoning

        try:
            result = handler(task)
            
            # Record success and response time
            with self.metrics_lock:
                if task_type in self.metrics["success_rate"]:
                    if result.get("status") == "success":
                        self.metrics["success_rate"][task_type]["success"] += 1
                    else:
                        self.metrics["success_rate"][task_type]["failure"] += 1
                
                # Record response time (in seconds)
                response_time = time.time() - start_time
                if task_type in self.metrics["response_times"]:
                    self.metrics["response_times"][task_type].append(response_time)
                    # Keep only the last 1000 response times to limit memory usage
                    self.metrics["response_times"][task_type] = self.metrics["response_times"][task_type][-1000:]
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling task {task.task_id}: {e}", exc_info=True)
            
            # Record failure
            with self.metrics_lock:
                if task_type in self.metrics["success_rate"]:
                    self.metrics["success_rate"][task_type]["failure"] += 1
            
            return {"status": "error", "message": f"Error processing task: {str(e)}"}

    def _classify_task(self, task: TaskDefinition) -> str:
        """
        Enhanced task classification using embeddings when available,
        with fallback to keyword-based classification.
        """
        # Extract the task description
        prompt = task.description.lower()
        
        # Check if embedding-based classification is available
        if self.embedding_model and self.task_type_embeddings:
            try:
                # Generate embedding for the current task
                task_embedding = self.embedding_model.encode(prompt)
                
                # Calculate cosine similarity with each task type
                similarities = {}
                for task_type, type_embedding in self.task_type_embeddings.items():
                    # Compute cosine similarity
                    similarity = np.dot(task_embedding, type_embedding) / (
                        np.linalg.norm(task_embedding) * np.linalg.norm(type_embedding)
                    )
                    similarities[task_type] = similarity
                
                # Get the task type with highest similarity
                best_match = max(similarities.items(), key=lambda x: x[1])
                task_type, similarity = best_match
                
                logger.info(f"Task classified as '{task_type}' with confidence {similarity:.4f}")
                
                # Update classification metrics
                with self.metrics_lock:
                    self.metrics["classification"]["embedding_based"] += 1
                
                # If similarity is too low, use keyword-based classification as fallback
                if similarity < 0.5:
                    logger.info(f"Low confidence ({similarity:.4f}), falling back to keyword classification")
                    return self._keyword_based_classification(prompt)
                    
                return task_type
                
            except Exception as e:
                logger.error(f"Error in embedding-based classification: {e}")
                # Fall back to keyword-based classification
                return self._keyword_based_classification(prompt)
        else:
            # Fall back to keyword-based classification
            return self._keyword_based_classification(prompt)
    
    def _keyword_based_classification(self, prompt: str) -> str:
        """Legacy keyword-based classification as fallback."""
        # Update classification metrics
        with self.metrics_lock:
            self.metrics["classification"]["keyword_based"] += 1
            
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

            if feedback and feedback.strip().upper() == "OK":
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

    # Override _get_health_status to include metrics
    def _get_health_status(self):
        """Get health status including metrics summary."""
        base_status = super()._get_health_status()
        
        # Add metrics summary to health status
        with self.metrics_lock:
            metrics_summary = {
                "requests_total": self.metrics["requests_total"],
                "requests_by_type": self.metrics["requests_by_type"],
                "classification_methods": {
                    "embedding_based": self.metrics["classification"]["embedding_based"],
                    "keyword_based": self.metrics["classification"]["keyword_based"]
                }
            }
            
            # Calculate success rates
            success_rates = {}
            for task_type, counts in self.metrics["success_rate"].items():
                total = counts["success"] + counts["failure"]
                rate = (counts["success"] / total * 100) if total > 0 else 0
                success_rates[task_type] = f"{rate:.1f}%"
            
            metrics_summary["success_rates"] = success_rates
        
        base_status["metrics"] = metrics_summary
        return base_status

    def health_check(self):
        """Performs a health check on the agent, returning a dictionary with its status."""
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # Check if embedding model is initialized if it should be
            if not self.embedding_model and self.metrics["classification"]["embedding_based"] > 0:
                is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "requests_total": self.metrics["requests_total"],
                    "embedding_model_loaded": self.embedding_model is not None,
                    "circuit_breaker_states": {name: cb.state for name, cb in self.circuit_breakers.items()}
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            logger.error(f"Health check failed with exception: {str(e)}")
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

    def cleanup(self):
        """Clean up resources when the agent is stopping."""
        try:
            # Stop all background threads
            self.running = False
            
            # Join metrics thread if it exists and is alive
            if hasattr(self, 'metrics_thread') and self.metrics_thread and self.metrics_thread.is_alive():
                self.metrics_thread.join(timeout=2.0)
            
            # Save final metrics before shutting down
            self._save_metrics()
            
            # Close all ZMQ sockets if they exist
            for service_name, circuit_breaker in self.circuit_breakers.items():
                if hasattr(circuit_breaker, 'socket') and circuit_breaker.socket:
                    try:
                        circuit_breaker.socket.close()
                    except Exception as e:
                        logger.error(f"Error closing circuit breaker socket for {service_name}: {e}")
            
            # Close error bus connection if it exists
            if hasattr(self, 'error_bus') and self.error_bus:
                try:
                    self.error_bus.close()
                except Exception as e:
                    logger.error(f"Error closing error bus connection: {e}")
            
            # Clean up any temporary files
            try:
                if hasattr(self, 'temp_dir') and self.temp_dir.exists():
                    for temp_file in self.temp_dir.glob('*'):
                        if temp_file.is_file():
                            temp_file.unlink()
                    logger.info(f"Cleaned up temporary files in {self.temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temporary files: {e}")
            
            logger.info("ModelOrchestrator cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        # Always call parent's cleanup to ensure complete resource release
        super().cleanup()

if __name__ == "__main__":
    agent = None
    try:
        agent = ModelOrchestrator()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
