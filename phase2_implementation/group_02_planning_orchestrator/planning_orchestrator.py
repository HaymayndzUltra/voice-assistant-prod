# File: phase2_implementation/group_02_planning_orchestrator/planning_orchestrator.py
#
# PlanningOrchestrator - Unified service consolidating ModelOrchestrator and GoalManager
# Combines task classification, goal decomposition, and swarm coordination

import sys
import os
import time
import logging
import threading
import json
import uuid
import heapq
import subprocess
import tempfile
import pickle
import asyncio
import zmq
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import psutil

# Import path manager for containerization-friendly paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'main_pc_code')))
from common.utils.path_env import get_path, join_path, get_file_path

# --- Standardized Imports ---
from common.core.base_agent import BaseAgent
from common.utils.data_models import TaskDefinition, TaskResult, TaskStatus, ErrorSeverity
from main_pc_code.utils.config_loader import load_config

# Try to import optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# --- Circuit Breaker (will be extracted to common utils) ---
class CircuitBreaker:
    """Circuit breaker for resilient service connections."""
    CLOSED, OPEN, HALF_OPEN = 'closed', 'open', 'half_open'
    
    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 30):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = threading.Lock()
        logging.info(f"Circuit Breaker initialized for service: {self.name}")
    
    def record_success(self):
        with self._lock:
            if self.state == self.HALF_OPEN:
                logging.info(f"Circuit for {self.name} is now CLOSED.")
            self.state = self.CLOSED
            self.failure_count = 0
    
    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == self.HALF_OPEN or self.failure_count >= self.failure_threshold:
                if self.state != self.OPEN:
                    logging.warning(f"Circuit for {self.name} has TRIPPED and is now OPEN.")
                self.state = self.OPEN
    
    def allow_request(self) -> bool:
        with self._lock:
            if self.state == self.OPEN:
                if time.time() - self.last_failure_time > self.reset_timeout:
                    self.state = self.HALF_OPEN
                    logging.info(f"Circuit for {self.name} is now HALF-OPEN.")
                    return True
                return False
            return True

# --- Configuration ---
config = load_config()
DEFAULT_PORT = config.get('planning_orchestrator_port', 7021)
HEALTH_CHECK_PORT = config.get('planning_orchestrator_health_port', 8021)
ZMQ_REQUEST_TIMEOUT = config.get('zmq_request_timeout', 30000)
MAX_REFINEMENT_ITERATIONS = config.get('max_refinement_iterations', 3)

# --- Embedding Constants ---
EMBEDDING_MODEL_NAME = config.get('embedding_model', "all-MiniLM-L6-v2")
EMBEDDING_CACHE_FILE = config.get('embedding_cache_file', join_path("data", "planning_task_embeddings_cache.pkl"))
EMBEDDING_DIMENSION = 384

# --- Metrics Constants ---
METRICS_LOG_INTERVAL = config.get('metrics_log_interval', 60)
METRICS_SAVE_INTERVAL = config.get('metrics_save_interval', 300)
METRICS_FILE = config.get('metrics_file', join_path("logs", "planning_orchestrator_metrics.json"))

# --- Logging Setup ---
logger = logging.getLogger('PlanningOrchestrator')

class PlanningOrchestrator(BaseAgent):
    """
    Unified Planning Orchestrator that combines:
    - Task classification and routing (from ModelOrchestrator)
    - Goal decomposition and swarm coordination (from GoalManager)
    """

    def __init__(self, **kwargs):
        super().__init__(name="PlanningOrchestrator", port=DEFAULT_PORT, 
                         health_check_port=HEALTH_CHECK_PORT, **kwargs)

        # --- Core State Management ---
        # Task Classification State (from ModelOrchestrator)
        self.language_configs = self._get_language_configs()
        self.temp_dir = Path(tempfile.gettempdir()) / "planning_orchestrator_sandbox"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_model = None
        self.task_type_embeddings = {}
        self.embedding_cache_path = Path(EMBEDDING_CACHE_FILE)
        self._init_embedding_model()
        self._load_task_embeddings()

        # Goal Management State (from GoalManager)
        self.goals: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, TaskDefinition] = {}
        self.task_status: Dict[str, TaskStatus] = {}  # Track task status separately
        self.task_results: Dict[str, Any] = {}
        self.task_queue: List[Tuple[int, float, str]] = []
        self.queue_lock = threading.Lock()

        # --- Memory Integration ---
        self.memory_client = None
        self._init_memory_client()

        # --- Metrics and Telemetry ---
        self.metrics = {
            "requests_total": 0,
            "requests_by_type": {
                "goal_creation": 0,
                "task_classification": 0,
                "code_generation": 0,
                "tool_use": 0,
                "reasoning": 0,
                "chat": 0
            },
            "response_times": {
                "goal_creation": [],
                "task_classification": [],
                "code_generation": [],
                "tool_use": [],
                "reasoning": [],
                "chat": []
            },
            "success_rate": {
                "goal_creation": {"success": 0, "failure": 0},
                "task_classification": {"success": 0, "failure": 0},
                "code_generation": {"success": 0, "failure": 0},
                "tool_use": {"success": 0, "failure": 0},
                "reasoning": {"success": 0, "failure": 0},
                "chat": {"success": 0, "failure": 0}
            },
            "classification": {
                "embedding_based": 0,
                "keyword_based": 0
            },
            "goals": {
                "active": 0,
                "completed": 0,
                "failed": 0
            }
        }
        self.metrics_lock = threading.Lock()
        self.last_metrics_log = time.time()
        self.last_metrics_save = time.time()
        self._load_metrics()

        # --- Downstream Services & Resilience ---
        self.downstream_services = [
            "ModelManagerAgent", "UnifiedMemoryReasoningAgent", "WebAssistant", 
            "CodeGenerator", "AutoGenFramework"
        ]
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._init_circuit_breakers()

        # --- Error Reporting & ZMQ Setup ---
        self.error_bus = None
        self.zmq_context = zmq.Context()
        self.zmq_sockets = {}
        self.service_endpoints = {}
        
        # Load service endpoints and setup connections
        self._load_service_endpoints()
        self._setup_zmq_connections()
        self._setup_error_reporting()
        self._setup_error_bus_connection()

        # --- Background Threads ---
        self.running = True
        self._start_background_threads()

        logger.info("PlanningOrchestrator initialized successfully.")

    def _get_language_configs(self) -> Dict[str, Dict]:
        """Define supported languages for code execution."""
        return {
            "python": {"extension": ".py", "command": [sys.executable]},
            "javascript": {"extension": ".js", "command": ["node"]},
        }

    def _init_circuit_breakers(self):
        """Initialize Circuit Breakers for all downstream services."""
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)

    def _init_embedding_model(self):
        """Initialize embedding model for task classification."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence_transformers not available. Using keyword-based classification only.")
            return
            
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None

    def _init_memory_client(self):
        """Initialize memory client for goal/task persistence."""
        try:
            from main_pc_code.agents.memory_client import MemoryClient
            self.memory_client = MemoryClient()
            logger.info("Memory client initialized successfully")
        except ImportError:
            logger.warning("MemoryClient not available - using local cache only")
            self.memory_client = None
        except Exception as e:
            logger.warning(f"Memory client initialization failed: {e}")
            self.memory_client = None

    def _load_service_endpoints(self):
        """Load service endpoints from startup configuration files."""
        try:
            # Try to load from startup configs first (source of truth)
            mainpc_config_path = Path("main_pc_code/config/startup_config_complete.yaml")
            pc2_config_path = Path("pc2_code/config/startup_config_corrected.yaml")
            
            service_endpoints = {}
            
            # Load MainPC services
            if mainpc_config_path.exists():
                with open(mainpc_config_path, 'r') as f:
                    mainpc_config = yaml.safe_load(f)
                    
                # Extract network configuration for IP discovery
                network_config = mainpc_config.get('global_settings', {}).get('network', {})
                mainpc_ip = "localhost"  # Default for same machine
                
                # Find specific agents in the config
                agent_groups = mainpc_config.get('agent_groups', {})
                for group_name, group_services in agent_groups.items():
                    for service_name, service_config in group_services.items():
                        if not service_config.get('enabled', True):
                            continue  # Skip disabled services
                            
                        port = service_config.get('port')
                        if port:
                            # Map service names to expected endpoints
                            if service_name == "ModelManagerAgent":
                                service_endpoints["ModelManagerAgent"] = f"tcp://{mainpc_ip}:{port}"
                            elif service_name == "CodeGenerator":
                                service_endpoints["CodeGenerator"] = f"tcp://{mainpc_ip}:{port}"
                            # Add WebAssistant and AutoGenFramework when they exist in config
                
            # Load PC2 services  
            if pc2_config_path.exists():
                with open(pc2_config_path, 'r') as f:
                    pc2_config = yaml.safe_load(f)
                    
                # Get PC2 IP from cross-system integration config
                cross_system = pc2_config.get('phase1_config', {}).get('cross_system_integration', {})
                pc2_ip = "172.20.0.11"  # Default from network config
                
                agent_groups = pc2_config.get('agent_groups', {})
                for group_name, group_services in agent_groups.items():
                    for service_name, service_config in group_services.items():
                        if not service_config.get('enabled', True):
                            continue
                            
                        port = service_config.get('port')
                        if port:
                            if service_name == "MemoryHub":
                                # This is used for memory reasoning
                                service_endpoints["UnifiedMemoryReasoningAgent"] = f"tcp://{pc2_ip}:{port}"
                                
            # Add fallback endpoints for services not yet in startup configs
            if "WebAssistant" not in service_endpoints:
                service_endpoints["WebAssistant"] = "tcp://localhost:7080"
            if "AutoGenFramework" not in service_endpoints:
                service_endpoints["AutoGenFramework"] = "tcp://localhost:7100"
                
            # Fallback to local config.yaml if startup configs incomplete
            local_config_path = Path("phase2_implementation/group_02_planning_orchestrator/config.yaml")
            if local_config_path.exists():
                with open(local_config_path, 'r') as f:
                    local_config = yaml.safe_load(f)
                    
                external_services = local_config.get('external_services', {})
                
                # Only use local config for services not found in startup configs
                for service_key, endpoint_key in [
                    ("WebAssistant", "web_assistant"),
                    ("AutoGenFramework", "autogen_framework")
                ]:
                    if service_key not in service_endpoints:
                        service_data = external_services.get(endpoint_key, {})
                        host = service_data.get('host', 'localhost')
                        port = service_data.get('port', 7080 if service_key == "WebAssistant" else 7100)
                        service_endpoints[service_key] = f"tcp://{host}:{port}"
            
            self.service_endpoints = service_endpoints
            logger.info(f"Loaded service endpoints from startup configs: {list(self.service_endpoints.keys())}")
            
            # Load error bus and memory endpoints from startup config
            self._load_infrastructure_endpoints()
            
        except Exception as e:
            logger.warning(f"Failed to load service endpoints from startup configs: {e}")
            # Final fallback to hardcoded values
            self.service_endpoints = {
                "ModelManagerAgent": "tcp://localhost:5570",
                "WebAssistant": "tcp://localhost:7080", 
                "CodeGenerator": "tcp://localhost:7090",
                "UnifiedMemoryReasoningAgent": "tcp://172.20.0.11:7010",
                "AutoGenFramework": "tcp://localhost:7100"
            }
            logger.info("Using fallback hardcoded endpoints")

    def _load_infrastructure_endpoints(self):
        """Load infrastructure endpoints (error bus, memory) from startup configs."""
        try:
            # Get from MainPC startup config
            mainpc_config_path = Path("main_pc_code/config/startup_config_complete.yaml")
            if mainpc_config_path.exists():
                with open(mainpc_config_path, 'r') as f:
                    mainpc_config = yaml.safe_load(f)
                    
                # Find PlanningOrchestrator config
                planning_config = None
                agent_groups = mainpc_config.get('agent_groups', {})
                for group_services in agent_groups.values():
                    if 'PlanningOrchestrator' in group_services:
                        planning_config = group_services['PlanningOrchestrator'].get('config', {})
                        break
                
                if planning_config:
                    # Extract infrastructure endpoints
                    self.error_bus_endpoint = planning_config.get('error_bus_endpoint', "tcp://172.20.0.11:7150")
                    self.memory_hub_endpoint = planning_config.get('memory_hub_endpoint', "http://172.20.0.11:7010")
                    logger.info(f"Loaded infrastructure endpoints - Error Bus: {self.error_bus_endpoint}, Memory Hub: {self.memory_hub_endpoint}")
                    return
                    
            # Fallback to local config
            self.error_bus_endpoint = "tcp://172.20.0.11:7150"
            self.memory_hub_endpoint = "http://172.20.0.11:7010"
            logger.info("Using fallback infrastructure endpoints")
            
        except Exception as e:
            logger.warning(f"Failed to load infrastructure endpoints: {e}")
            self.error_bus_endpoint = "tcp://172.20.0.11:7150"
            self.memory_hub_endpoint = "http://172.20.0.11:7010"

    def _setup_zmq_connections(self):
        """Setup ZMQ REQ sockets for each service."""
        try:
            for service_name, endpoint in self.service_endpoints.items():
                socket = self.zmq_context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
                socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
                socket.connect(endpoint)
                self.zmq_sockets[service_name] = socket
                logger.info(f"Connected to {service_name} at {endpoint}")
                
        except Exception as e:
            logger.error(f"Failed to setup ZMQ connections: {e}")

    def _setup_error_bus_connection(self):
        """Setup ZMQ PUB socket for error bus communication."""
        try:
            # Setup error bus publisher
            self.error_bus_socket = self.zmq_context.socket(zmq.PUB)
            error_bus_endpoint = getattr(self, 'error_bus_endpoint', "tcp://172.20.0.11:7150")  # Use the loaded endpoint
            self.error_bus_socket.connect(error_bus_endpoint)
            logger.info(f"Connected to error bus at {error_bus_endpoint}")
            
        except Exception as e:
            logger.warning(f"Failed to setup error bus connection: {e}")
            self.error_bus_socket = None

    def _setup_error_reporting(self):
        """Set up error reporting to the central error bus."""
        try:
            # Try to import ErrorBusClient if available
            try:
                from main_pc_code.agents.error_bus_client import ErrorBusClient
                self.error_bus = ErrorBusClient(
                    component_name=self.name,
                    component_type="agent",
                    max_retry=3
                )
                logger.info("Error reporting set up successfully")
            except ImportError:
                logger.warning("ErrorBusClient not available - using local logging only")
                self.error_bus = None
        except Exception as e:
            logger.warning(f"Error reporting setup failed: {e}")
            self.error_bus = None

    def _load_task_embeddings(self):
        """Load or initialize task type embeddings."""
        if not self.embedding_model or not NUMPY_AVAILABLE:
            logger.info("Skipping embedding loading - requirements not met")
            return
            
        # Define example tasks for each category
        task_examples = {
            "code_generation": [
                "Write a Python function to calculate fibonacci numbers",
                "Create a JavaScript class for handling API requests",
                "Debug this code that has an infinite loop",
                "Implement a sorting algorithm in Python",
                "Fix the syntax error in this function"
            ],
            "tool_use": [
                "Search for information about climate change",
                "Find the latest news about AI advancements",
                "Look up the weather forecast for tomorrow",
                "Browse for articles about machine learning"
            ],
            "reasoning": [
                "Explain how quantum computing works",
                "Analyze the impact of social media on mental health",
                "Compare and contrast different machine learning algorithms",
                "Why does the sky appear blue?"
            ],
            "chat": [
                "Hello, how are you today?",
                "What's your name?",
                "Tell me a joke",
                "Can you help me with something?"
            ]
        }
        
        # Try to load cached embeddings
        if self.embedding_cache_path.exists():
            try:
                with open(self.embedding_cache_path, 'rb') as f:
                    self.task_type_embeddings = pickle.load(f)
                logger.info(f"Loaded task embeddings from cache: {len(self.task_type_embeddings)} task types")
                return
            except Exception as e:
                logger.warning(f"Failed to load embedding cache: {e}")
        
        # Generate embeddings
        logger.info("Generating task type embeddings...")
        for task_type, examples in task_examples.items():
            try:
                embeddings = self.embedding_model.encode(examples)
                self.task_type_embeddings[task_type] = np.mean(embeddings, axis=0)
            except Exception as e:
                logger.error(f"Error generating embeddings for {task_type}: {e}")
        
        # Save the embeddings to cache
        try:
            os.makedirs(os.path.dirname(self.embedding_cache_path), exist_ok=True)
            with open(self.embedding_cache_path, 'wb') as f:
                pickle.dump(self.task_type_embeddings, f)
            logger.info("Saved task embeddings to cache")
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
                        self.metrics["requests_total"] = saved_metrics.get("requests_total", 0)
                        self.metrics["requests_by_type"] = saved_metrics.get("requests_by_type", self.metrics["requests_by_type"])
                        self.metrics["success_rate"] = saved_metrics.get("success_rate", self.metrics["success_rate"])
                        self.metrics["classification"] = saved_metrics.get("classification", self.metrics["classification"])
                        self.metrics["goals"] = saved_metrics.get("goals", self.metrics["goals"])
                logger.info(f"Loaded metrics from {metrics_path}")
        except Exception as e:
            logger.warning(f"Failed to load metrics from file: {e}")

    def _start_background_threads(self):
        """Start all background processing threads."""
        threads = {
            "MetricsReporter": self._metrics_reporting_loop,
            "TaskProcessor": self._process_task_queue,
            "GoalMonitor": self._monitor_goals,
        }
        
        for name, target in threads.items():
            thread = threading.Thread(target=target, name=f"{self.name}-{name}", daemon=True)
            thread.start()
            logger.info(f"Started background thread: {name}")

    # ===================================================================
    #         CORE API & MAIN ENTRY POINT
    # ===================================================================

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for all requests."""
        action = request.get("action")
        data = request.get("data", {})
        
        start_time = time.time()
        
        # Update metrics
        with self.metrics_lock:
            self.metrics["requests_total"] += 1

        try:
            # Route to appropriate handler
            handlers = {
                # Goal management (from GoalManager)
                "set_goal": self._handle_set_goal,
                "get_goal_status": self._handle_get_goal_status,
                "list_goals": self._handle_list_goals,
                "search_goals": self._handle_search_goals,
                
                # Task processing (from ModelOrchestrator)
                "classify_task": self._handle_classify_task,
                "execute_task": self._handle_execute_task,
                
                # Unified planning operations
                "plan_and_execute": self._handle_plan_and_execute,
            }
            
            handler = handlers.get(action) if action else None
            if not handler:
                return {"status": "error", "message": f"Unknown action: {action}"}
            
            result = handler(data)
            
            # Update success metrics - handle potential None result
            response_time = time.time() - start_time
            action_str = str(action) if action else "unknown"
            status = "error"
            if result and isinstance(result, dict) and "status" in result:
                status = str(result["status"])
            self._update_success_metrics(action_str, response_time, status == "success")
            
            return result or {"status": "error", "message": "No result returned"}
            
        except Exception as e:
            response_time = time.time() - start_time
            action_str = str(action) if action else "unknown"
            self._update_success_metrics(action_str, response_time, False)
            logger.error(f"Error handling request {action}: {e}", exc_info=True)
            return {"status": "error", "message": f"Error processing request: {str(e)}"}

    # ===================================================================
    #         TASK CLASSIFICATION & EXECUTION (from ModelOrchestrator)
    # ===================================================================

    def _handle_classify_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a task based on its description."""
        try:
            description = data.get("description")
            if not description:
                return {"status": "error", "message": "Task description is required"}
            
            task = TaskDefinition(
                task_id=str(uuid.uuid4()),
                agent_id=self.name,
                task_type="unknown",
                parameters={"description": description, **data.get("parameters", {})}
            )
            
            task_type = self._classify_task(task)
            
            return {
                "status": "success",
                "result": {
                    "task_type": task_type,
                    "description": description,
                    "classification_method": "embedding" if self.embedding_model else "keyword"
                }
            }
        except Exception as e:
            logger.error(f"Error classifying task: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_execute_task(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task based on its type and description."""
        try:
            task_data = data.get("task")
            if not task_data:
                return {"status": "error", "message": "Task data is required"}
            
            # Ensure task has required fields
            if "agent_id" not in task_data:
                task_data["agent_id"] = self.name
            
            task = TaskDefinition(**task_data)
            
            # Classify if not already classified
            if task.task_type == "unknown":
                task.task_type = self._classify_task(task)
            
            # Execute based on type
            handlers = {
                "code_generation": self._handle_code_generation_task,
                "tool_use": self._handle_tool_use_task,
                "reasoning": self._handle_reasoning_task,
                "chat": self._handle_chat_task,
            }
            
            handler = handlers.get(task.task_type, self._handle_reasoning_task)
            return handler(task)
            
        except Exception as e:
            logger.error(f"Error executing task: {e}")
            return {"status": "error", "message": str(e)}

    def _classify_task(self, task: TaskDefinition) -> str:
        """Enhanced task classification using embeddings when available."""
        prompt = task.description.lower()
        
        # Try embedding-based classification first
        if self.embedding_model and self.task_type_embeddings and NUMPY_AVAILABLE:
            try:
                task_embedding = self.embedding_model.encode(prompt)
                
                similarities = {}
                for task_type, type_embedding in self.task_type_embeddings.items():
                    similarity = np.dot(task_embedding, type_embedding) / (
                        np.linalg.norm(task_embedding) * np.linalg.norm(type_embedding)
                    )
                    similarities[task_type] = similarity
                
                best_match = max(similarities.items(), key=lambda x: x[1])
                task_type, similarity = best_match
                
                with self.metrics_lock:
                    self.metrics["classification"]["embedding_based"] += 1
                
                if similarity > 0.5:  # Confidence threshold
                    return task_type
                    
            except Exception as e:
                logger.warning(f"Embedding classification failed: {e}")
        
        # Fall back to keyword-based classification
        with self.metrics_lock:
            self.metrics["classification"]["keyword_based"] += 1
            
        return self._keyword_based_classification(prompt)

    def _keyword_based_classification(self, prompt: str) -> str:
        """Keyword-based task classification fallback."""
        if any(k in prompt for k in ["code", "python", "function", "script", "debug"]):
            return "code_generation"
        if any(k in prompt for k in ["search for", "find information about", "browse"]):
            return "tool_use"
        if any(k in prompt for k in ["why", "how", "explain", "analyze", "compare"]):
            return "reasoning"
        return "chat"

    # ===================================================================
    #         GOAL MANAGEMENT (from GoalManager)
    # ===================================================================

    def _handle_set_goal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new goal and start planning."""
        try:
            goal_desc = data.get("description")
            if not goal_desc:
                return {"status": "error", "message": "Goal description is required"}

            goal_id = str(uuid.uuid4())
            goal_metadata = {
                "description": goal_desc,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "user_id": data.get("user_id", "default"),
                "priority": data.get("priority", 5)
            }
            
            # Store in memory system if available
            if self.memory_client:
                try:
                    response = self.memory_client.add_memory(
                        content=goal_desc,
                        metadata=goal_metadata,
                        tags=["goal", "planning"]
                    )
                    if response and response.get("status") == "success":
                        goal_id = response.get("memory_id", goal_id)
                except Exception as e:
                    logger.warning(f"Failed to store goal in memory system: {e}")
            
            # Store in local cache
            self.goals[goal_id] = {
                "id": goal_id,
                "tasks": [],
                **goal_metadata
            }
            
            # Update goal metrics
            with self.metrics_lock:
                self.metrics["goals"]["active"] += 1
            
            # Start planning in background
            threading.Thread(target=self._break_down_goal, args=(goal_id,), daemon=True).start()
            
            logger.info(f"Created goal: {goal_id} - '{goal_desc[:50]}...'")
            return {"status": "success", "goal_id": goal_id, "message": "Goal created and planning started"}
            
        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_get_goal_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get the status of a specific goal."""
        goal_id = data.get("goal_id")
        if not goal_id:
            return {"status": "error", "message": "Goal ID is required"}
            
        if goal_id in self.goals:
            goal = self.goals[goal_id].copy()
            
            # Add task details
            goal_tasks = [self.tasks[tid].dict() for tid in goal.get("tasks", []) if tid in self.tasks]
            goal["task_details"] = goal_tasks
            
            return {"status": "success", "goal": goal}
        else:
            return {"status": "error", "message": "Goal not found"}

    def _handle_list_goals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """List goals with optional filtering."""
        limit = data.get("limit", 20)
        status_filter = data.get("status")
        
        goals = list(self.goals.values())
        
        if status_filter:
            goals = [g for g in goals if g.get("status") == status_filter]
        
        goals = goals[:limit]
        return {"status": "success", "goals": goals}

    def _handle_search_goals(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Search goals by description."""
        query = data.get("query", "").lower()
        if not query:
            return {"status": "error", "message": "Search query is required"}
        
        matching_goals = [
            goal for goal in self.goals.values()
            if query in goal.get("description", "").lower()
        ]
        
        return {"status": "success", "goals": matching_goals}

    def _handle_plan_and_execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Unified endpoint for goal creation, planning, and execution."""
        # First create the goal
        goal_result = self._handle_set_goal(data)
        if goal_result.get("status") != "success":
            return goal_result
        
        goal_id = goal_result.get("goal_id")
        
        # Planning will happen in background
        return {
            "status": "success", 
            "goal_id": goal_id,
            "message": "Goal created, planning and execution will proceed in background"
        }

    # ===================================================================
    #         BACKGROUND PROCESSING
    # ===================================================================

    def _metrics_reporting_loop(self):
        """Background metrics collection and reporting."""
        while self.running:
            try:
                current_time = time.time()
                
                if current_time - self.last_metrics_log >= METRICS_LOG_INTERVAL:
                    self._log_metrics()
                    self.last_metrics_log = current_time
                
                if current_time - self.last_metrics_save >= METRICS_SAVE_INTERVAL:
                    self._save_metrics()
                    self.last_metrics_save = current_time
                
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in metrics reporting: {e}")
                time.sleep(30)

    def _process_task_queue(self):
        """Background task queue processor."""
        while self.running:
            try:
                with self.queue_lock:
                    if self.task_queue:
                        _, _, task_id = heapq.heappop(self.task_queue)
                        threading.Thread(target=self._execute_task_async, args=(task_id,), daemon=True).start()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in task queue processing: {e}")
                time.sleep(5)

    def _monitor_goals(self):
        """Background goal monitoring."""
        while self.running:
            try:
                # Monitor goal progress and update statuses
                for goal_id, goal in self.goals.items():
                    if goal.get("status") == "active":
                        self._check_goal_progress(goal_id)
                time.sleep(30)
            except Exception as e:
                logger.error(f"Error in goal monitoring: {e}")
                time.sleep(60)

    # ===================================================================
    #         HELPER METHODS
    # ===================================================================

    def _break_down_goal(self, goal_id: str):
        """Break down a goal into tasks using LLM."""
        try:
            goal = self.goals.get(goal_id)
            if not goal:
                return
                
            goal["status"] = "planning"
            
            # Use LLM for actual goal decomposition
            prompt = f"""
            You are a planning AI. Break down the following high-level goal into a sequence of specific, executable tasks.
            For each task, define 'task_type' and 'description'.
            
            Goal: "{goal['description']}"
            
            Respond with a JSON list of task objects in this format:
            [
                {{"description": "task description", "task_type": "reasoning|code_generation|tool_use|chat"}},
                ...
            ]
            """
            
            llm_response = self._send_to_llm(prompt)
            
            if llm_response:
                try:
                    tasks = json.loads(llm_response)
                except json.JSONDecodeError:
                    # Fallback to simple decomposition
                    tasks = [
                        {"description": f"Analyze and understand: {goal['description']}", "task_type": "reasoning"},
                        {"description": f"Execute main action for: {goal['description']}", "task_type": "reasoning"},
                        {"description": f"Verify completion of: {goal['description']}", "task_type": "reasoning"}
                    ]
            else:
                # Fallback decomposition
                tasks = [
                    {"description": f"Step 1 for goal: {goal['description']}", "task_type": "reasoning"},
                    {"description": f"Step 2 for goal: {goal['description']}", "task_type": "reasoning"},
                ]
            
            for i, task_data in enumerate(tasks):
                task_id = str(uuid.uuid4())
                task = TaskDefinition(
                    task_id=task_id,
                    agent_id=self.name,
                    task_type=task_data["task_type"],
                    parameters={"description": task_data["description"], "goal_id": goal_id, "sequence": i}
                )
                
                self.tasks[task_id] = task
                self.task_status[task_id] = TaskStatus.PENDING
                goal["tasks"].append(task_id)
                
                # Store in memory system if available
                if self.memory_client:
                    try:
                        self.memory_client.add_memory(
                            content=task_data["description"],
                            metadata={"task_type": task_data["task_type"], "goal_id": goal_id},
                            tags=["task"]
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store task in memory: {e}")
                
                # Add to task queue
                with self.queue_lock:
                    heapq.heappush(self.task_queue, (5, time.time(), task_id))
            
            goal["status"] = "active"
            logger.info(f"Goal {goal_id} broken down into {len(tasks)} tasks")
            
        except Exception as e:
            logger.error(f"Error breaking down goal {goal_id}: {e}")
            if goal_id in self.goals:
                self.goals[goal_id]["status"] = "error"

    def _execute_task_async(self, task_id: str):
        """Execute a task asynchronously."""
        try:
            if task_id not in self.tasks:
                return
                
            task = self.tasks[task_id]
            self.task_status[task_id] = TaskStatus.RUNNING
            
            logger.info(f"Executing task {task_id}: {task.description[:50]}...")
            
            # Route to appropriate agent based on task type
            agent_mapping = {
                "code_generation": "CodeGenerator", 
                "tool_use": "WebAssistant",
                "reasoning": "ModelOrchestrator",
                "chat": "ModelOrchestrator"
            }
            
            target_agent = agent_mapping.get(task.task_type, "ModelOrchestrator")
            
            # Send task to appropriate agent
            request = {
                "action": "execute_task" if target_agent != "ModelOrchestrator" else "handle_request",
                "task": task.dict() if target_agent != "ModelOrchestrator" else {"action": "generate_text", "prompt": task.description}
            }
            
            response = self._resilient_send_request(target_agent, request)
            
            if response and response.get("status") == "success":
                # Mark as completed
                self.task_status[task_id] = TaskStatus.COMPLETED
                self.task_results[task_id] = response.get("result", {})
                logger.info(f"Task {task_id} completed successfully")
            else:
                # Mark as failed
                self.task_status[task_id] = TaskStatus.FAILED
                self.task_results[task_id] = {"error": "Failed to get response from agent"}
                logger.error(f"Task {task_id} failed: no response from {target_agent}")
            
            # Update goal progress
            self._update_goal_progress(task_id)
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            if task_id in self.task_status:
                self.task_status[task_id] = TaskStatus.FAILED

    def _check_goal_progress(self, goal_id: str):
        """Check and update goal progress."""
        goal = self.goals.get(goal_id)
        if not goal:
            return
            
        task_ids = goal.get("tasks", [])
        if not task_ids:
            return
            
        completed_tasks = [tid for tid in task_ids if self.task_status.get(tid) == TaskStatus.COMPLETED]
        failed_tasks = [tid for tid in task_ids if self.task_status.get(tid) == TaskStatus.FAILED]
        
        if len(completed_tasks) == len(task_ids):
            goal["status"] = "completed"
            with self.metrics_lock:
                self.metrics["goals"]["completed"] += 1
                self.metrics["goals"]["active"] -= 1
        elif failed_tasks and len(failed_tasks) >= len(task_ids) / 2:
            goal["status"] = "failed"
            with self.metrics_lock:
                self.metrics["goals"]["failed"] += 1
                self.metrics["goals"]["active"] -= 1

    def _update_goal_progress(self, task_id: str):
        """Update goal progress when a task completes."""
        task = self.tasks.get(task_id)
        if not task:
            return
            
        goal_id = task.parameters.get("goal_id")
        if goal_id:
            self._check_goal_progress(goal_id)

    def _update_success_metrics(self, operation: str, response_time: float, success: bool):
        """Update metrics for an operation."""
        with self.metrics_lock:
            if operation in self.metrics["success_rate"]:
                if success:
                    self.metrics["success_rate"][operation]["success"] += 1
                else:
                    self.metrics["success_rate"][operation]["failure"] += 1
            
            if operation in self.metrics["response_times"]:
                self.metrics["response_times"][operation].append(response_time)
                # Keep only last 1000 entries
                self.metrics["response_times"][operation] = self.metrics["response_times"][operation][-1000:]

    def _log_metrics(self):
        """Log current metrics."""
        with self.metrics_lock:
            logger.info(f"PlanningOrchestrator Metrics - Total Requests: {self.metrics['requests_total']}")
            logger.info(f"Active Goals: {self.metrics['goals']['active']}, "
                       f"Completed: {self.metrics['goals']['completed']}, "
                       f"Failed: {self.metrics['goals']['failed']}")

    def _save_metrics(self):
        """Save metrics to file."""
        try:
            metrics_path = Path(METRICS_FILE)
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            
            with self.metrics_lock:
                metrics_to_save = {k: v for k, v in self.metrics.items() if k != "response_times"}
                metrics_to_save["last_updated"] = datetime.now().isoformat()
            
            with open(metrics_path, 'w') as f:
                json.dump(metrics_to_save, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

    # ===================================================================
    #         CRITICAL MISSING FUNCTION - CODE EXECUTION SECURITY
    # ===================================================================

    def _execute_code_safely(self, code: str, language: str) -> Dict[str, Any]:
        """Execute code in sandboxed environment with security controls."""
        config = self.language_configs.get(language)
        if not config:
            return {"success": False, "error": f"Unsupported language: {language}"}

        file_path = self.temp_dir / f"exec_{uuid.uuid4()}{config['extension']}"
        try:
            # Write code to temporary file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Execute with security constraints
            process = subprocess.run(
                config["command"] + [str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=self.temp_dir,  # Restrict to temp directory
                env={"PATH": os.environ.get("PATH", "")},  # Minimal environment
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
            # Always clean up temporary file
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

    def _send_to_llm(self, prompt: str) -> Optional[str]:
        """Send prompt to LLM via ModelManagerAgent."""
        request = {"action": "generate_text", "prompt": prompt}
        response = self._resilient_send_request("ModelManagerAgent", request)
        return response.get("result", {}).get("text") if response and response.get("status") == "success" else None

    def _build_context_prompt(self, task: TaskDefinition, system_prompt: str) -> str:
        """Build context-aware prompt by fetching conversation history."""
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

    # ===================================================================
    #         TASK HANDLERS (Enhanced implementations)
    # ===================================================================

    def _handle_code_generation_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handle code generation tasks with iterative refinement."""
        try:
            logger.info(f"Starting code generation for task: {task.task_id}")
            code_context = self._build_context_prompt(task, "You are an expert programmer.")
            current_code = ""

            # Iterative refinement loop
            for i in range(MAX_REFINEMENT_ITERATIONS):
                logger.info(f"Code refinement iteration {i+1}/{MAX_REFINEMENT_ITERATIONS}")
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
                    current_code = generated_code
                    code_context += f"\n\nPrevious attempt had issues:\n{feedback}"
            else:
                logger.warning("Max refinement iterations reached. Using the last generated code.")

            # Execute code if requested
            should_execute = task.parameters.get("execute", False)
            execution_result = None
            if should_execute:
                logger.info("Executing final generated code in a safe environment.")
                execution_result = self._execute_code_safely(current_code, "python")

            return {
                "status": "success",
                "result": {
                    "code": current_code,
                    "execution_result": execution_result,
                    "type": "code_generation"
                }
            }
        except Exception as e:
            logger.error(f"Error in code generation: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_tool_use_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handle tool use tasks with proper routing."""
        try:
            # Determine specific tool needed
            if "search" in task.description.lower():
                query = task.parameters.get("query", task.description)
                logger.info(f"Executing tool: WebSearch with query '{query}'")
                search_result = self._resilient_send_request("WebAssistant", {"action": "search", "query": query})
                
                if search_result and search_result.get("status") == "success":
                    return {"status": "success", "result": {"tool_result": search_result.get("result"), "type": "tool_use"}}
                else:
                    return {"status": "error", "message": "Search tool failed"}
            else:
                return {"status": "error", "message": "Unknown tool requested."}
                
        except Exception as e:
            logger.error(f"Error in tool use: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_reasoning_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handle reasoning tasks with enhanced prompting."""
        try:
            full_prompt = self._build_context_prompt(task, "You are a logical reasoner. Think step by step.")
            response = self._send_to_llm(full_prompt)
            
            if response:
                return {"status": "success", "result": {"reasoning": response, "type": "reasoning"}}
            else:
                return {"status": "error", "message": "Failed to get reasoning response"}
                
        except Exception as e:
            logger.error(f"Error in reasoning: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_chat_task(self, task: TaskDefinition) -> Dict[str, Any]:
        """Handle chat tasks with context awareness."""
        try:
            full_prompt = self._build_context_prompt(task, "You are a helpful assistant.")
            response = self._send_to_llm(full_prompt)
            
            if response:
                return {"status": "success", "result": {"response": response, "type": "chat"}}
            else:
                return {"status": "error", "message": "Failed to get chat response"}
                
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return {"status": "error", "message": str(e)}

    def _resilient_send_request(self, agent_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send request with circuit breaker protection using direct ZMQ sockets."""
        circuit = self.circuit_breakers.get(agent_name)
        if circuit and not circuit.allow_request():
            logger.warning(f"Circuit open for {agent_name}, request rejected")
            return None
            
        try:
            # Use direct ZMQ socket if available, otherwise fallback to BaseAgent method
            if agent_name in self.zmq_sockets:
                socket = self.zmq_sockets[agent_name]
                
                # Send request via ZMQ
                request_json = json.dumps(request)
                socket.send_string(request_json)
                
                # Wait for response
                response_json = socket.recv_string()
                response = json.loads(response_json)
                
                if circuit:
                    circuit.record_success()
                    
                logger.debug(f"ZMQ request to {agent_name} successful")
                return response
            else:
                # Fallback to BaseAgent method
                response = self.send_request_to_agent(agent_name, request, timeout=ZMQ_REQUEST_TIMEOUT)
                if circuit:
                    circuit.record_success()
                return response
                
        except zmq.error.Again:
            # Timeout error
            if circuit:
                circuit.record_failure()
            logger.warning(f"Timeout communicating with {agent_name}")
            self._report_error_to_bus("communication_timeout", f"Timeout communicating with {agent_name}")
            return None
        except Exception as e:
            if circuit:
                circuit.record_failure()
            logger.error(f"Failed to communicate with {agent_name}: {e}")
            self._report_error_to_bus("communication_error", f"Failed to communicate with {agent_name}: {e}")
            return None

    def _report_error_to_bus(self, error_type: str, message: str):
        """Report error to ZMQ error bus."""
        if hasattr(self, 'error_bus_socket') and self.error_bus_socket:
            try:
                error_data = {
                    "timestamp": time.time(),
                    "agent": self.name,
                    "error_type": error_type,
                    "message": message,
                    "severity": "ERROR"
                }
                self.error_bus_socket.send_string(f"ERROR:{json.dumps(error_data)}")
            except Exception as e:
                logger.error(f"Failed to report error to bus: {e}")

    def _get_health_status(self):
        """Get health status including metrics and connection status."""
        base_status = super()._get_health_status()
        
        # Test service connections
        connection_status = self._test_service_connections()
        healthy_connections = sum(1 for status in connection_status.values() if status)
        total_connections = len(connection_status)
        
        with self.metrics_lock:
            base_status.update({
                "service": "PlanningOrchestrator",
                "requests_total": self.metrics["requests_total"],
                "active_goals": self.metrics["goals"]["active"],
                "completed_goals": self.metrics["goals"]["completed"],
                "task_queue_size": len(self.task_queue),
                "embedding_model_loaded": self.embedding_model is not None,
                "memory_client_available": self.memory_client is not None,
                "error_bus_available": self.error_bus is not None,
                "zmq_connections": {
                    "total": total_connections,
                    "healthy": healthy_connections,
                    "status": connection_status
                },
                "service_endpoints": self.service_endpoints,
                "circuit_breaker_states": {name: cb.state for name, cb in self.circuit_breakers.items()}
            })
        
        return base_status

    def report_error(self, error_type: str, message: str, severity: ErrorSeverity, **kwargs):
        """Report an error to the central error bus."""
        # Try ErrorBusClient first if available
        if self.error_bus:
            try:
                self.error_bus.report_error(
                    error_message=message,
                    severity=severity,
                    context={"error_type": error_type, **kwargs}
                )
            except Exception as e:
                logger.error(f"Failed to report error via ErrorBusClient: {e}")
        
        # Also report via direct ZMQ error bus
        self._report_error_to_bus(error_type, message)
        
        # Always log locally
        logger.error(f"{error_type}: {message}")

    def _test_service_connections(self) -> Dict[str, bool]:
        """Test connections to all downstream services."""
        connection_status = {}
        
        for service_name in self.service_endpoints:
            try:
                # Send a simple ping request
                ping_request = {"action": "ping", "timestamp": time.time()}
                response = self._resilient_send_request(service_name, ping_request)
                
                # Consider connection good if we get any response
                connection_status[service_name] = response is not None
                
            except Exception as e:
                logger.warning(f"Connection test failed for {service_name}: {e}")
                connection_status[service_name] = False
        
        return connection_status

    def cleanup(self):
        """Clean up resources when stopping."""
        try:
            self.running = False
            self._save_metrics()
            
            # Close all ZMQ sockets
            if hasattr(self, 'zmq_sockets'):
                for service_name, socket in self.zmq_sockets.items():
                    try:
                        socket.close()
                        logger.info(f"Closed ZMQ socket for {service_name}")
                    except Exception as e:
                        logger.error(f"Error closing socket for {service_name}: {e}")
            
            # Close error bus socket
            if hasattr(self, 'error_bus_socket') and self.error_bus_socket:
                try:
                    self.error_bus_socket.close()
                    logger.info("Closed error bus socket")
                except Exception as e:
                    logger.error(f"Error closing error bus socket: {e}")
            
            # Close ZMQ context
            if hasattr(self, 'zmq_context') and self.zmq_context:
                try:
                    self.zmq_context.term()
                    logger.info("Terminated ZMQ context")
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")
            
            # Close error bus client
            if hasattr(self, 'error_bus') and self.error_bus:
                try:
                    self.error_bus.close()
                except Exception as e:
                    logger.error(f"Error closing error bus client: {e}")
            
            # Clean temporary files
            if hasattr(self, 'temp_dir') and self.temp_dir.exists():
                for temp_file in self.temp_dir.glob('*'):
                    if temp_file.is_file():
                        temp_file.unlink()
            
            logger.info("PlanningOrchestrator cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        super().cleanup()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(join_path("logs", "planning_orchestrator.log")),
            logging.StreamHandler()
        ]
    )
    
    agent = None
    try:
        agent = PlanningOrchestrator()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup() 