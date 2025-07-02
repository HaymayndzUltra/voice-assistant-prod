# Active PC2 Agents Documentation

## List of All Active PC2 Agents

### [UNIFIED MEMORY REASONING AGENT]

- **File:** unified_memory_reasoning_agent.py
- **Purpose:** Provides unified memory access, reasoning, and migration for PC2.
- **Key Features:**
  - Handles memory queries, supports migration, integrates with other agents.
  - **NEW:** Memory coordination with other memory agents (episodic, dreamworld, etc.)
  - **NEW:** Priority management for memory operations (low, normal, high)
  - **NEW:** Conflict resolution for simultaneous/conflicting memory operations
- **Integration Points:**
  - **Reply socket:** Handles memory requests (REP 5596)
  - **Port:** 5596
  - **Health check:** Monitors agent health
  - **Memory operations:** Manages memory queries and updates
  - **Coordination:** Communicates with other memory agents via ZMQ (e.g., episodic: 5597, dreamworld: 5642)
- **Usage Example:**
  - To coordinate with another agent, include in the request:
    ```json
    {
      "coordinate_with": "episodic",
      "operation": "read",
      "data": { "key": "value" },
      "priority": "high"
    }
    ```
- **Conflict Policy:**
  - Higher-priority operations preempt lower-priority ones (low < normal < high)
  - Lower-priority operations are rejected if a conflict exists

### [DREAMWORLD AGENT]

- **File:** DreamWorldAgent.py
- **Purpose:** Simulates and analyzes complex scenarios with enhanced reasoning capabilities.
- **Key Features:**
  - Advanced Monte Carlo Tree Search with uncertainty tracking
  - Causal reasoning and counterfactual analysis
  - Scenario template management
  - Simulation history and persistence
  - Parallel simulation support
  - Ethical reasoning framework
- **Integration Points:**
  - **Reply socket:** Handles dreaming requests (REP 5642)
  - **Publish socket:** Broadcasts dream world updates (PUB 5599)
  - **Health check:** Monitors agent health
  - **Memory integration:** Connects to EpisodicMemoryAgent (Port 5629)
  - **Model selection:** Routes to appropriate models via EnhancedModelRouter (Port 5632)

### [COGNITIVE MODEL AGENT]

- **File:** CognitiveModelAgent.py
- **Purpose:** Provides cognitive modeling and reasoning capabilities.
- **Key Features:** Model-based reasoning, context inference, supports other agents.
- **Integration:** Integrates with other agents for advanced reasoning tasks.
- **Ports:** [Specify ZMQ ports if available]
- **Dependencies:** [List key dependencies]
- **Notes:** [Additional notes or context]

### [LEARNING ADJUSTER AGENT]

- **File:** learning_adjuster_agent.py
- **Purpose:** Manages and optimizes learning parameters for PC2 agents.
- **Key Features:**
  - Learning rate adjustment
  - Parameter optimization
  - Performance monitoring
  - Trend analysis
  - Automated parameter tuning
- **Integration Points:**
  - **Reply socket:** Handles learning adjustments (REP 5643)
  - **Connects to Self Training Orchestrator:** (Port 5644)
  - **Connects to Local Fine Tuner Agent:** (Port 5645)
- **API Actions:**
  1. `register_parameter`
     - Registers a new parameter for adjustment
     - Parameters: config (name, type, min_value, max_value, current_value, step_size, description)
     - Returns: success status
  2. `adjust_parameter`
     - Adjusts a parameter's value
     - Parameters: parameter_name, new_value
     - Returns: success status
  3. `record_performance`
     - Records a performance metric
     - Parameters: metric_name, value, parameters (optional)
     - Returns: success status
  4. `optimize_parameters`
     - Optimizes parameters based on performance metrics
     - Parameters: metric_name
     - Returns: suggested adjustments
- **Parameter Types:**
  - LEARNING_RATE: Learning rate parameters
  - BATCH_SIZE: Batch size parameters
  - OPTIMIZER: Optimizer parameters
  - REGULARIZATION: Regularization parameters
  - CUSTOM: User-defined parameters
- **Database Schema:**
  1. `parameter_history`
     - Tracks parameter value changes
     - Records timestamps and performance metrics
  2. `parameter_configs`
     - Stores parameter configurations
     - Defines valid ranges and step sizes
  3. `performance_metrics`
     - Records performance measurements
     - Links metrics to parameter values
- **Usage Example:**

  ```python
  # Register a learning rate parameter
  config = {
      "name": "model_learning_rate",
      "type": "learning_rate",
      "min_value": 0.0001,
      "max_value": 0.1,
      "current_value": 0.001,
      "step_size": 0.0001,
      "description": "Learning rate for main model"
  }

  # Register parameter
  response = agent.register_parameter(config)

  # Record performance
  agent.record_performance(
      metric_name="accuracy",
      value=0.85,
      parameters={"model_learning_rate": 0.001}
  )

  # Optimize parameters
  optimization = agent.optimize_parameters("accuracy")
  ```

- **Performance Features:**
  - Correlation-based trend analysis
  - Automated parameter adjustment
  - Performance history tracking
  - Bounded parameter ranges
  - Step size control
- **Error Handling:**
  - Parameter validation
  - Range checking
  - Database consistency
  - Connection management
  - Detailed error logging

### [PERFORMANCE LOGGER AGENT]

- **File:** PerformanceLoggerAgent.py
- **Purpose:** Logs performance metrics and resource usage for all agents.
- **Key Features:** Tracks response times, CPU/memory usage, historical data.
- **Integration Points:**
  - **Reply socket:** Handles logging requests
  - **Health check:** Monitors agent health
  - **Metrics collection:** Gathers performance data

### [EPISODIC MEMORY AGENT]

- **File:** EpisodicMemoryAgent.py
- **Purpose:** Manages and retrieves episodic memories with enhanced context awareness and relationship tracking.
- **Key Features:**
  - Advanced episode management with importance scoring
  - Context-aware memory organization
  - Relationship tracking between episodes
  - Full-text search with relevance ranking
  - Context group management
  - Episode lifecycle management
- **Integration Points:**
  - **Reply socket:** Handles memory requests (REP 5629)
  - **Health check:** Monitors agent health
  - **Memory integration:** Connects to Unified Memory Reasoning Agent
  - **Provides memory context:** To other agents

### [MEMORY DECAY MANAGER]

- **File:** memory_decay_manager.py
- **Purpose:** Manages memory decay and forgetting mechanisms.
- **Key Features:** Periodic decay, memory pruning, retention policy.
- **Integration:** Integrates with memory agents to manage memory lifecycle.
- **Ports:** [Specify ZMQ ports if available]
- **Dependencies:** [List key dependencies]
- **Notes:** [Additional notes or context]

### [ENHANCED CONTEXTUAL MEMORY AGENT]

- **File:** enhanced_contextual_memory.py
- **Purpose:** Provides advanced context management using a hierarchical memory system (short, medium, long-term) with intelligent summarization.
- **Key Features:**
  - Hierarchical memory organization (short, medium, long-term).
  - Intelligent summarization for code and conversations.
  - Memory promotion based on importance and access.
  - Priority levels for memory entries.
  - Handles various memory types (Code, Query, Error, etc.).
- **Integration Points:**
  - **Reply socket:** Handles memory requests (REP 5596).
  - **Health check:** Responds to `health_check` action.
- **API Actions:** `add_memory`, `get_context`, `health_check`.

### [SELF-HEALING AGENT]

- **File:** self_healing_agent.py
- **Purpose:** Monitors, recovers, and restarts failed agents automatically.
- **Key Features:** Heartbeat monitoring, dependency management, auto-recovery.
- **Integration Points:**
  - **Reply socket:** Handles health requests (REP 5611)
  - **Health check:** Monitors agent health
  - **Agent monitoring:** Tracks all agent health

### [ENHANCED MODEL ROUTER]

- **File:** enhanced_model_router.py
- **Purpose:** Central intelligence hub for model routing with load balancing and fallback handling.
- **Key Features:**
  - Model selection based on capabilities and load
  - Load balancing across multiple models
  - Automatic fallback handling
  - Performance monitoring
  - Task classification
  - Context-aware prompting
- **Integration Points:**
  - **Reply socket:** Handles routing requests (REP 5598)
  - **Health check:** Monitors agent health
  - **Model selection:** Routes to appropriate models
  - **Publisher socket:** Handles model inference requests (PUB 5603)
  - **Connects to Model Manager:** (Port 5555)
  - **Connects to Contextual Memory:** (Port 5596)
  - **Connects to Chain of Thought:** (Port 5612)
  - **Connects to Remote Connector:** (Port 5557)
- **API Actions:**
  1. `model_inference`
     - Handles model inference requests
     - Parameters: task_type, prompt, context
     - Returns: model response with confidence
  2. `chain_of_thought`
     - Handles complex reasoning tasks
     - Parameters: prompt, context
     - Returns: step-by-step reasoning
  3. `contextual_inference`
     - Handles context-aware inference
     - Parameters: prompt, context, memory_key
     - Returns: context-aware response
  4. `memory_operation`
     - Handles memory operations
     - Parameters: operation, key, value
     - Returns: operation result
  5. `status`
     - Gets router status and statistics
     - Returns: current load, model stats, health
- **Load Balancing Features:**
  - Request window: 60 seconds
  - Max requests per model: 100 per window
  - Performance tracking:
    - Request count
    - Error count
    - Average latency
    - Success rate
- **Fallback Handling:**
  - Confidence threshold: 0.7
  - Max fallback attempts: 3
  - Fallback models:
    - tinyllama (default)
    - gpt2
    - phi-2
- **Model Capabilities:**
  - tinyllama: chat, text-generation
  - gpt2: text-generation, code-generation
  - phi-2: reasoning, code-generation
  - llama2: chat, reasoning, code-generation
- **Usage Example:**

  ```python
  # Create inference request
  request = {
      "action": "model_inference",
      "task_type": "code-generation",
      "prompt": "Write a Python function to sort a list",
      "context": ["Previous code examples", "User preferences"]
  }

  # Send request to router
  response = router.handle_request(request)

  # Check response
  if "error" in response:
      print(f"Error: {response['error']}")
  else:
      print(f"Response: {response['text']}")
      print(f"Confidence: {response['confidence']}")
  ```

- **Performance Features:**
  - Load-based model selection
  - Performance monitoring
  - Automatic fallback
  - Error recovery
  - Health monitoring
- **Error Handling:**
  - Model failure detection
  - Automatic fallback
  - Error logging
  - Performance tracking
  - Health checks

### [REMOTE CONNECTOR AGENT]

- **File:** remote_connector_agent.py
- **Purpose:** Manages API connections and model inference requests with enhanced reliability.
- **Key Features:**
  - API management and connection handling
  - Response caching with TTL
  - Async request processing
  - Connection state monitoring
  - Automatic retry logic
  - Performance tracking
- **Integration Points:**
  - **Reply socket:** Handles connection requests (REP 5557)
  - **Health check:** Monitors agent health
  - **Connects to Model Manager:** (Port 5555)
  - **Supports multiple API endpoints:**
    - Ollama (http://localhost:11434)
    - Deepseek (http://localhost:8000)
- **API Actions:**
  1. `inference`
     - Handles model inference requests
     - Parameters: model, prompt, temperature
     - Returns: model response with status
  2. `status`
     - Gets connection and cache status
     - Returns: connection states and cache stats
  3. `cache_stats`
     - Gets cache statistics
     - Returns: hits, misses, expired entries
- **Connection States:**
  - DISCONNECTED: No active connection
  - CONNECTING: Connection attempt in progress
  - CONNECTED: Active connection
  - ERROR: Connection error
- **Cache Features:**
  - TTL-based caching (default: 1 hour)
  - Automatic cache invalidation
  - Cache statistics tracking
  - Configurable cache directory
- **API Configuration:**
  - Ollama:
    - Timeout: 30 seconds
    - Max retries: 3
    - Retry delay: 2 seconds
  - Deepseek:
    - Timeout: 60 seconds
    - Max retries: 3
    - Retry delay: 5 seconds
- **Usage Example:**

  ```python
  # Create inference request
  request = {
      "action": "inference",
      "model": "ollama/phi",
      "prompt": "Write a Python function",
      "temperature": 0.7
  }

  # Send request to connector
  response = connector.handle_request(request)

  # Check response
  if response["status"] == "success":
      print(f"Response: {response['response']}")
      print(f"Cached: {response.get('cached', False)}")
  else:
      print(f"Error: {response['message']}")
  ```

- **Performance Features:**
  - Async request processing
  - Connection pooling
  - Response caching
  - Automatic retries
  - Error recovery
- **Error Handling:**
  - Connection state tracking
  - Automatic retry logic
  - Error logging
  - Cache error recovery
  - Resource cleanup

### [UNIFIED WEB AGENT]

- **File:** unified_web_agent.py
- **Purpose:** Combines autonomous web assistance, scraping, and automation with enhanced context awareness.
- **Key Features:**
  - Proactive information gathering
  - Advanced web scraping with multiple strategies
  - Form filling and navigation
  - Caching and database storage
  - AutoGen framework integration
  - Conversation analysis
  - Dynamic browsing with context awareness
  - Real-time reference provision
  - Autonomous decision-making
  - Search query enhancement
  - Result ranking and summarization
- **Integration Points:**
  - **Reply socket:** Handles web requests (REP 5604)
  - **Health check:** Monitors agent health (REP 5605)
  - **Model Manager:** Connects to model inference (REQ 5610)
  - **AutoGen Framework:** Integrates with framework (REQ 5600)
  - **Executor:** Handles code execution (REQ 5603)
  - **Context Summarizer:** Enhances context (REQ 5610)
  - **Memory Agent:** Manages conversation context (REQ 5596)
- **Database Tables:**
  - Cache table for page content
  - Scraping history
  - Form submission history
  - Conversation context with relevance scoring

### [FILESYSTEM ASSISTANT AGENT]

- **File:** filesystem_assistant_agent.py
- **Purpose:** Provides file operations (list, read, write, check) via ZMQ.
- **Key Features:** Secure file access, usage statistics, error handling.
- **Integration Points:**
  - **Reply socket:** Handles file operations (REP 5606)
  - **Health check:** Monitors agent health
  - **File system:** Manages file operations

### [GOT/TOT AGENT]

- **File:** got_tot_agent.py
- **Purpose:** Handles "GoT/ToT" (possibly chain-of-thought or task orchestration).
- **Key Features:** Task orchestration, shutdown/cleanup, logging.
- **Integration:** Integrates with agents to orchestrate tasks.
- **Ports:** [Specify ZMQ ports if available]
- **Dependencies:** [List key dependencies]
- **Notes:** [Additional notes or context]

### [TUTOR AGENT]

- **File:** tutor_agent.py
- **Purpose:** Coordinates tutoring sessions, connects to TutoringServiceAgent.
- **Key Features:** Session management, ZMQ communication, integration with PC2 tutoring.
- **Integration:** Integrates with tutoring services to manage sessions.
- **Ports:** [Specify ZMQ ports if available]
- **Dependencies:** [List key dependencies]
- **Notes:** [Additional notes or context]

### [TUTORING SERVICE AGENT]

- **File:** core_agents/tutoring_service_agent.py
- **Purpose:** Provides tutoring services, responds to tutoring requests.
- **Key Features:** Session handling, response generation, logging.
- **Integration Points:**
  - **Reply socket:** Handles tutoring requests (REP 5568)
  - **Health check:** Monitors agent health
  - **Tutoring:** Manages tutoring sessions
  - **Port:** 5568

### [LOCAL FINE TUNER AGENT]

- **File:** local_fine_tuner_agent.py
- **Purpose:** Manages model fine-tuning and artifact management.
- **Key Features:**
  - Model fine-tuning
  - Artifact management
  - Job queuing
  - Progress tracking
  - Metric recording
- **Integration Points:**
  - **Reply socket:** Handles tuning requests (REP 5645)
  - **Port:** 5645
  - **Connects to Learning Adjuster Agent:** (Port 5643)
  - **Connects to Self Training Orchestrator:** (Port 5644)
  - **Model Manager:** Manages model artifacts (REQ 5610)
- **API Actions:**
  1. `create_job`
     - Creates a new tuning job
     - Parameters: model_id, config
     - Returns: job_id
  2. `start_job`
     - Starts a tuning job
     - Parameters: job_id
     - Returns: success status
  3. `get_status`
     - Gets status of a tuning job
     - Parameters: job_id
     - Returns: job status and metrics
- **Artifact Types:**
  - MODEL: Fine-tuned model files
  - CHECKPOINT: Training checkpoints
  - CONFIG: Model configurations
  - LOGS: Training logs
  - METRICS: Performance metrics
- **Tuning Status:**
  - PENDING: Job is queued
  - RUNNING: Job is executing
  - COMPLETED: Job finished successfully
  - FAILED: Job encountered an error
  - CANCELLED: Job was cancelled
- **Database Schema:**
  1. `tuning_jobs`
     - Stores job information
     - Tracks status and progress
  2. `artifacts`
     - Records artifact information
     - Links artifacts to jobs
  3. `tuning_metrics`
     - Stores performance metrics
     - Tracks training progress
- **Usage Example:**

  ```python
  # Create a tuning job
  config = {
      "model_id": "gpt2",
      "training_config": {
          "epochs": 3,
          "batch_size": 8,
          "learning_rate": 2e-4,
          "save_steps": 100
      },
      "data_config": {
          "train_file": "data/train.json",
          "validation_file": "data/val.json"
      }
  }

  # Create job
  response = agent.create_job(
      model_id="gpt2",
      config=config
  )
  job_id = response["job_id"]

  # Start job
  agent.start_job(job_id)

  # Check status
  status = agent.get_status(job_id)
  ```

- **Performance Features:**
  - Job queuing and prioritization
  - Artifact versioning
  - Metric tracking
  - Progress monitoring
  - Resource management
- **Error Handling:**
  - Job state validation
  - Artifact consistency
  - Error recovery
  - Resource cleanup
  - Detailed logging

### [AGENT TRUST SCORER]

- **File:** AgentTrustScorer.py
- **Purpose:** Scores and tracks trustworthiness of agents.
- **Key Features:** Trust metrics, scoring, logging.
- **Integration:** Integrates with agents to assess trustworthiness.
- **Ports:** [Specify ZMQ ports if available]
- **Dependencies:** [List key dependencies]
- **Notes:** [Additional notes or context]

### [SELF TRAINING ORCHESTRATOR]

- **File:** self_training_orchestrator.py
- **Purpose:** Manages training cycles and resource allocation for PC2 agents.
- **Key Features:**
  - Training cycle management
  - Resource allocation and monitoring
  - Progress tracking
  - Priority-based scheduling
  - Automated cycle execution
- **Integration Points:**
  - **Reply socket:** Handles training requests (REP 5644)
  - **Port:** 5644
  - **Connects to Learning Adjuster Agent:** (Port 5643)
  - **Connects to Local Fine Tuner Agent:** (Port 5645)
- **API Actions:**
  1. `create_cycle`
     - Creates a new training cycle
     - Parameters: agent_id, config, priority (optional)
     - Returns: cycle_id
  2. `start_cycle`
     - Starts a training cycle
     - Parameters: cycle_id
     - Returns: success status
  3. `get_status`
     - Gets status of a training cycle
     - Parameters: cycle_id
     - Returns: cycle status and metrics
- **Resource Types:**
  - CPU: CPU usage percentage
  - GPU: GPU usage percentage
  - MEMORY: Memory usage in GB
  - STORAGE: Storage usage in GB
  - NETWORK: Network bandwidth in Mbps
- **Training Status:**
  - PENDING: Cycle is queued
  - RUNNING: Cycle is executing
  - COMPLETED: Cycle finished successfully
  - FAILED: Cycle encountered an error
  - PAUSED: Cycle is temporarily stopped
- **Database Schema:**
  1. `training_cycles`
     - Stores cycle information
     - Tracks status and progress
  2. `resource_usage`
     - Records resource consumption
     - Links usage to cycles
  3. `cycle_metrics`
     - Stores performance metrics
     - Tracks cycle progress
- **Usage Example:**

  ```python
  # Create a training cycle
  config = {
      "agent_id": "model_1",
      "resources": {
          "cpu": 50.0,
          "gpu": 80.0,
          "memory": 8.0,
          "storage": 10.0,
          "network": 100.0
      },
      "training_config": {
          "epochs": 100,
          "batch_size": 32,
          "learning_rate": 0.001
      }
  }

  # Create cycle
  response = orchestrator.create_cycle(
      agent_id="model_1",
      config=config,
      priority=1
  )
  cycle_id = response["cycle_id"]

  # Start cycle
  orchestrator.start_cycle(cycle_id)

  # Check status
  status = orchestrator.get_status(cycle_id)
  ```

- **Performance Features:**
  - Priority-based scheduling
  - Resource allocation optimization
  - Progress monitoring
  - Metric tracking
  - Automated cleanup
- **Error Handling:**
  - Resource validation
  - Cycle state management
  - Error recovery
  - Resource cleanup
  - Detailed logging

### [AUTONOMOUS WEB ASSISTANT]

- **File:** autonomous_web_assistant.py
- **Purpose:** DEPRECATED - Functionality merged into Unified Web Agent
- **Notes:** This agent has been deprecated and its features have been integrated into the Unified Web Agent for better context awareness and autonomous decision-making.

### [ADVANCED ROUTER]

- **File:** advanced_router.py
- **Purpose:** Detects task type and provides intelligent routing utilities for model selection.
- **Key Features:** Task classification, prompt analysis.
- **Notes:** Utility module; imported by other agents (not a standalone ZMQ service).

### [CONSOLIDATED TRANSLATOR AGENT]

- **File:** consolidated_translator.py
- **Purpose:** Offers consolidated translation services across multiple models.
- **Key Features:** Multi-model fallback, language detection, Tagalog/English support.
- **Integration Points:**
  - **Reply socket:** Handles translation requests (REP 5563)
  - **Health check:** Monitors agent health

### [DREAMING MODE AGENT]

- **File:** DreamingModeAgent.py
- **Purpose:** Performs background memory replay to generate contextual insights.
- **Key Features:** Random memory sampling, insight generation.
- **Integration Points:**
  - **Reply socket:** Handles dreaming requests (REP 5640)
  - **Port:** 5640
  - **Health check:** Monitors agent health
  - **Memory integration:** Connects to EpisodicMemoryAgent (REQ 5596)

### [TINYLLAMA SERVICE]

- **File:** tinyllama_service_enhanced.py
- **Purpose:** Provides efficient access to the TinyLlama model with enhanced resource management and generation capabilities.
- **Key Features:**
  - On-demand model loading/unloading
  - Resource-aware model management
  - Enhanced generation configuration
  - Real-time resource monitoring
  - Automatic resource cleanup
  - Health status reporting
- **Integration Points:**
  - **Reply socket:** Handles service requests (REP 5615)
  - **Port:** 5615
  - **Connects to ModelManagerAgent:** (Port 5610)
  - Resource monitoring and management
- **API Actions:**
  1. `generate`
     - Parameters:
       - `prompt` (string): Input prompt
       - `max_tokens` (int, optional): Maximum tokens to generate
       - `temperature` (float, optional): Sampling temperature
       - `top_p` (float, optional): Top-p sampling parameter
     - Returns:
       - `status`: "success" or "error"
       - `text`: Generated text
       - `config`: Used generation parameters
  2. `ensure_loaded`
     - Parameters: None
     - Returns:
       - `status`: "success" or "error"
       - `message`: Loading status message
  3. `request_unload`
     - Parameters: None
     - Returns:
       - `status`: "success" or "error"
       - `message`: Unloading status message
  4. `health_check`
     - Parameters: None
     - Returns:
       - `status`: "ok"
       - `service`: "tinyllama_service"
       - `model_status`: Current model state
       - `timestamp`: Current timestamp
  5. `resource_stats`
     - Parameters: None
     - Returns:
       - `status`: "success"
       - `stats`: Resource usage statistics
- **Model States:**
  - UNLOADED: Model not in memory
  - LOADING: Model is being loaded
  - LOADED: Model is ready for use
  - UNLOADING: Model is being unloaded
  - ERROR: Error state
- **Generation Configuration:**
  - `max_tokens`: Maximum tokens to generate (default: 100)
  - `temperature`: Sampling temperature (default: 0.7)
  - `top_p`: Top-p sampling parameter (default: 0.9)
  - `top_k`: Top-k sampling parameter (default: 50)
  - `repetition_penalty`: Penalty for repetition (default: 1.1)
  - `do_sample`: Whether to use sampling (default: true)
- **Resource Management:**
  - Memory threshold: 90% of available memory
  - VRAM threshold: 90% of available VRAM (CUDA only)
  - Automatic resource cleanup
  - Real-time resource monitoring
  - Automatic model unloading on high resource usage
- **Usage Example:**

  ```python
  import zmq
  import json

  # Connect to TinyLlama service
  context = zmq.Context()
  socket = context.socket(zmq.REQ)
  socket.connect("tcp://localhost:5615")

  # Generate text
  request = {
      "action": "generate",
      "prompt": "What is machine learning?",
      "max_tokens": 100,
      "temperature": 0.7,
      "top_p": 0.9
  }
  socket.send_json(request)
  response = socket.recv_json()

  # Check resource stats
  socket.send_json({"action": "resource_stats"})
  stats = socket.recv_json()
  ```

- **Performance Features:**
  - Resource-aware model loading
  - Automatic resource cleanup
  - Efficient memory management
  - Real-time resource monitoring
  - Configurable generation parameters
- **Error Handling:**
  - Resource validation
  - Model state management
  - Generation error recovery
  - Connection error handling
  - Detailed error logging

### [TUTORING AGENT]

- **File:** tutoring_agent.py
- **Purpose:** Coordinates tutoring sessions and interfaces with TutoringServiceAgent.
- **Key Features:** Session management, progress tracking, ZMQ communication.
- **Integration:** Communicates with TutoringServiceAgent (REQ 5568)

### [CHAIN OF THOUGHT AGENT]

- **File:** chain_of_thought_agent.py
- **Purpose:** Implements multi-step reasoning (Chain-of-Thought) for reliable code generation.
- **Key Features:** Problem decomposition, solution verification, refinement, combination.
- **Integration Points:**
  - **Reply socket:** Handles reasoning requests (REP 5612)
  - **Health check:** Monitors agent health
  - **Model inference:** Uses Remote Connector Agent (REQ 5557)

### API Actions for DreamWorld Agent

1. `run_simulation`

   - Runs MCTS simulation with uncertainty tracking
   - Parameters: scenario, iterations
   - Returns: simulation results with causal analysis

2. `get_simulation_history`

   - Retrieves simulation history
   - Parameters: scenario (optional), limit
   - Returns: list of simulations with details

3. `create_scenario`

   - Creates new scenario from template
   - Parameters: template (name, type, description, etc.)
   - Returns: scenario_id

4. `get_scenario`

   - Retrieves scenario details
   - Parameters: scenario_id
   - Returns: scenario information

5. `update_scenario`
   - Updates scenario details
   - Parameters: scenario_id, updates
   - Returns: success status

### Scenario Types

- ETHICAL: Ethical dilemmas and moral reasoning
- RESOURCE: Resource allocation and optimization
- SOCIAL: Social interaction and group dynamics
- STRATEGIC: Strategic planning and decision making
- CUSTOM: User-defined scenarios

### Simulation Features

- Uncertainty tracking and propagation
- Causal relationship analysis
- Counterfactual scenario generation
- State persistence and history
- Parallel simulation execution

### Database Schema

1. `scenarios`

   - Stores scenario templates and metadata
   - Tracks creation and updates

2. `simulations`

   - Records simulation runs and results
   - Stores causal analysis and counterfactuals

3. `simulation_states`
   - Tracks state evolution during simulation
   - Stores action effects and values

### Usage Example

```python
# Create ethical scenario
scenario = {
    'name': 'trolley_problem',
    'type': 'ethical',
    'description': 'Classic trolley problem',
    'initial_state': {
        'trolley_moving': True,
        'track_1': {'people': 5, 'obstacle': False},
        'track_2': {'people': 1, 'obstacle': False},
        'lever_position': 'neutral'
    },
    'actions': [
        {
            'name': 'pull_lever',
            'target': 'track_1',
            'effects': [
                {'target': 'lever_position', 'value': 'track_1'},
                {'target': 'track_1.obstacle', 'value': True},
                {'target': 'track_2.obstacle', 'value': False}
            ]
        },
        {
            'name': 'pull_lever',
            'target': 'track_2',
            'effects': [
                {'target': 'lever_position', 'value': 'track_2'},
                {'target': 'track_1.obstacle', 'value': False},
                {'target': 'track_2.obstacle', 'value': True}
            ]
        },
        {
            'name': 'do_nothing',
            'effects': [
                {'target': 'lever_position', 'value': 'neutral'},
                {'target': 'track_1.obstacle', 'value': False},
                {'target': 'track_2.obstacle', 'value': False}
            ]
        }
    ],
    'constraints': [
        {
            'type': 'range',
            'target': 'track_1.people',
            'min': 0,
            'max': 10
        },
        {
            'type': 'range',
            'target': 'track_2.people',
            'min': 0,
            'max': 10
        }
    ],
    'evaluation_metrics': [
        'lives_saved',
        'moral_implications',
        'action_justification'
    ],
    'metadata': {
        'difficulty': 'medium',
        'category': 'ethics',
        'tags': ['trolley', 'moral', 'dilemma']
    }
}

# Create scenario
response = agent.create_scenario(scenario)
scenario_id = response['scenario_id']

# Run simulation
results = agent.run_simulation('trolley_problem', iterations=1000)

# Get simulation history
history = agent.get_simulation_history(
    scenario='trolley_problem',
    limit=5
)
```

### Performance Features

- Parallel simulation execution
- Efficient state tracking
- Optimized MCTS with uncertainty
- Causal analysis caching
- Database indexing for quick retrieval

### Error Handling

- Graceful error recovery
- Detailed error logging
- State consistency checks
- Resource cleanup
- Connection management

### Testing Strategy

**Purpose:** Ensure reliability and performance of the Model Management Hierarchy components.

**Test Components:**

1. Enhanced Model Router

   - Health check functionality
   - Model selection logic
   - Load balancing features
   - Fallback handling
   - Performance metrics

2. Remote Connector Agent

   - API management
   - Connection state handling
   - Request processing
   - Error recovery
   - Performance tracking

3. TinyLlama Service
   - Resource management
   - Model loading/unloading
   - Generation capabilities
   - Health monitoring
   - Performance metrics

**Test Categories:**

1. Unit Tests

   - Individual component functionality
   - API endpoint validation
   - Error handling
   - Resource management
   - State transitions

2. Integration Tests

   - Component interaction
   - Request flow
   - Error propagation
   - Resource sharing
   - State synchronization

3. Performance Tests

   - Response times
   - Resource utilization
   - Load handling
   - Memory management
   - Connection stability

4. Error Handling Tests
   - Invalid requests
   - Resource exhaustion
   - Connection failures
   - State inconsistencies
   - Recovery procedures

**Test Environment:**

- Python unittest framework
- ZMQ for component communication
- Logging for test tracking
- Resource monitoring
- Performance metrics collection

**Test Execution:**

```bash
# Run all tests
python test_model_management.py

# Run specific test category
python test_model_management.py TestModelManagementHierarchy.test_router_health_check
```

**Test Coverage:**

- API endpoints
- Component interactions
- Error scenarios
- Resource management
- Performance metrics
- State transitions
- Recovery procedures

**Monitoring and Reporting:**

- Test execution logs
- Performance metrics
- Error reports
- Resource utilization
- State transitions
- Recovery success rates

### Enhanced Contextual Memory

**Purpose:** Provides advanced context management with hierarchical memory organization and intelligent compression.

**Key Features:**

- Hierarchical memory organization (short, medium, long-term)
- Intelligent memory compression and summarization
- Priority-based memory management
- Automatic memory promotion and demotion
- Resource-aware memory optimization
- Performance tracking and monitoring

**Integration Points:**

- Reply socket on Port 5596
- Connects to ModelManagerAgent (Port 5610)
- Memory hierarchy management

**Memory Types:**

1. CODE: Code snippets and implementations
2. QUERY: User queries and requests
3. RESPONSE: System responses and outputs
4. ERROR: Error messages and stack traces
5. DECISION: Key decisions and choices
6. SUMMARY: Summarized content

**Memory Priorities:**

1. HIGH (3): Critical information
2. MEDIUM (2): Standard information
3. LOW (1): Supplementary information

**API Actions:**

1. `add_memory`

   - Parameters:
     - `content` (string): Memory content
     - `type` (string): Memory type
     - `priority` (string, optional): Memory priority
     - `metadata` (object, optional): Additional metadata
   - Returns:
     - `status`: "success" or "error"
     - `message`: Operation result message

2. `get_context`

   - Parameters:
     - `max_tokens` (int, optional): Maximum tokens in response
   - Returns:
     - `status`: "success"
     - `context`: Memory context object

3. `health_check`
   - Parameters: None
   - Returns:
     - `status`: "ok"
     - `service`: "enhanced_contextual_memory"
     - `uptime_seconds`: Service uptime
     - `total_requests`: Total requests handled
     - `successful_requests`: Successful requests
     - `failed_requests`: Failed requests

**Memory Hierarchy:**

1. Short-term Memory

   - Capacity: 50 entries
   - Detail: High
   - Retention: Recent interactions
   - Access: Frequent

2. Medium-term Memory

   - Capacity: 200 entries
   - Detail: Moderate
   - Retention: Less recent
   - Access: Occasional

3. Long-term Memory
   - Capacity: 1000 entries
   - Detail: Summarized
   - Retention: Historical
   - Access: Rare

**Memory Management:**

- Automatic promotion based on importance
- Intelligent summarization
- Resource-aware cleanup
- Access pattern tracking
- Importance scoring

**Usage Example:**

```python
import zmq
import json

# Connect to memory service
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5596")

# Add memory
request = {
    "action": "add_memory",
    "content": "Important code implementation",
    "type": "code",
    "priority": "HIGH",
    "metadata": {"file": "main.py"}
}
socket.send_json(request)
response = socket.recv_json()

# Get context
request = {"action": "get_context"}
socket.send_json(request)
context = socket.recv_json()
```

**Performance Features:**

- Memory hierarchy optimization
- Intelligent summarization
- Resource-aware management
- Access pattern tracking
- Performance monitoring

**Error Handling:**

- Memory validation
- Type checking
- Priority management
- Resource monitoring
- Detailed logging
