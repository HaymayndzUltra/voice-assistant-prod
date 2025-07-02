# Cursor AI Blueprint: Building the Voice-Assistant-Prod System

## Introduction

This document provides a complete, step-by-step set of instructions for an advanced AI assistant (like Cursor) to construct the entire `Voice-Assistant-Prod` AI system. The instructions are derived from the master `SYSTEM_DESIGN.md` document and the `source_of_truth_config.yaml`.

The goal is to automate the creation of the environment, core components, individual agents, configuration files, and utility scripts, resulting in a fully functional and verifiable system.

---

## Part 1: Environment & Core Setup

**Objective:** Prepare the foundational environment and create the core, abstract components that all other agents will depend on.

### Instruction 1.1: Create `requirements.txt`

Create a file named `requirements.txt` in the root directory with the following content. This file lists all the necessary Python packages for the project.

```python
numpy
pyzmq
PyYAML
python-dotenv
dotenv
psutil
requests
```

### Instruction 1.2: Create `.env` file

Create a file named `.env` in the root directory. This file will store environment variables, such as the host IP for PC2. Populate it with the following:

```
PC2_HOST=192.168.1.101
```

### Instruction 1.3: Create the BaseAgent Contract

Create the file `src/core/base_agent.py`. This is the most critical base class in the system. It must handle ZMQ socket initialization (main and health check), graceful shutdown via signal handlers, and provide a non-blocking background initialization method. Use the `SYSTEM_DESIGN.md` section "5.1 The `BaseAgent` Contract" as a detailed reference for its implementation.

### Instruction 1.4: Create the Agent Template

Create a template file at `src/core/agent_template.py`. This template should inherit from `BaseAgent` and provide a clear, commented structure for creating new agents. It should include placeholders for:
-   Argument parsing (for port and dependencies).
-   Connecting to dependency sockets.
-   The main request-handling loop.
-   The background initialization method.
-   A `main` block to instantiate and run the agent.

---

## Part 2: Configuration & Utilities

**Objective:** Create the single source of truth configuration file and the scripts required to interpret it for deployment and validation.

### Instruction 2.1: Create the Source of Truth Configuration

Create the file `config/source_of_truth_config.yaml`. This is the master blueprint for the entire system. Populate it with the exact content below. This configuration defines every agent, its location, port, dependencies, and on which machine it runs.

```yaml
main_pc_host: &main_pc_host localhost

pc2_host: &pc2_host ${PC2_HOST}

main_pc_services:
  # Core Orchestration & Routing
  GoalOrchestratorAgent: { script: 'agents/GoalOrchestratorAgent.py', port: 7000, dependencies: { TaskRouter: 5559, ModelManagerAgent: 5560 } }
  TaskRouter: { script: 'agents/TaskRouter.py', port: 5559, dependencies: {} }
  ModelManagerAgent: { script: 'agents/ModelManagerAgent.py', port: 5560, dependencies: { EnhancedModelRouter: 5635 } }
  IntentionValidatorAgent: { script: 'agents/IntentionValidatorAgent.py', port: 5558, dependencies: { GoalOrchestratorAgent: 7000 } }

  # Personality & Proactivity
  DynamicIdentityAgent: { script: 'FORMAINPC/DynamicIdentityAgent.py', port: 5640, dependencies: {} }
  EmpathyAgent: { script: 'FORMAINPC/EmpathyAgent.py', port: 5642, dependencies: { EmotionEngine: 5575 } }
  ProactiveAgent: { script: 'FORMAINPC/ProactiveAgent.py', port: 5630, dependencies: { PredictiveLoader: 5631 } }
  PredictiveLoader: { script: 'FORMAINPC/PredictiveLoader.py', port: 5631, dependencies: {} }

  # GPU & Advanced Reasoning
  EnhancedModelRouter: { script: 'FORMAINPC/EnhancedModelRouter.py', port: 5635, dependencies: { TinyLlamaService: 5561, NLLBAdapter: 5562 } }
  TinyLlamaService: { script: 'FORMAINPC/TinyLlamaService.py', port: 5561, dependencies: {} }
  NLLBAdapter: { script: 'FORMAINPC/NLLBAdapter.py', port: 5562, dependencies: {} }
  ChainOfThoughtAgent: { script: 'FORMAINPC/ChainOfThoughtAgent.py', port: 5647, dependencies: {} }
  GOT_TOTAgent: { script: 'FORMAINPC/GOT_TOTAgent.py', port: 5646, dependencies: {} }

  # Learning & Adaptation
  LearningAdjusterAgent: { script: 'FORMAINPC/LearningAdjusterAgent.py', port: 5643, dependencies: { PerformanceMonitoringAgent: 5632, SelfTrainingOrchestrator: 5644 } }
  LocalFineTunerAgent: { script: 'FORMAINPC/LocalFineTunerAgent.py', port: 5645, dependencies: { SelfTrainingOrchestrator: 5644, ModelManagerAgent: 5560 } }
  SelfTrainingOrchestrator: { script: 'FORMAINPC/SelfTrainingOrchestrator.py', port: 5644, dependencies: { LearningAdjusterAgent: 5643, LocalFineTunerAgent: 5645 } }
  CognitiveModelAgent: { script: 'FORMAINPC/CognitiveModelAgent.py', port: 5641, dependencies: { TaskRouter: 5559, ProactiveAgent: 5630, PredictiveLoader: 5631 } }

  # Emotion Subsystem
  EmotionEngine: { script: 'agents/emotion_engine.py', port: 5575, dependencies: { ToneDetector: 5625, EmpathyAgent: 5642, MoodTrackerAgent: 5704 } }
  MoodTrackerAgent: { script: 'agents/mood_tracker_agent.py', port: 5704, dependencies: { EmotionEngine: 5575 } }
  HumanAwarenessAgent: { script: 'agents/human_awareness_agent.py', port: 5705, dependencies: { EmotionEngine: 5575 } }
  EmotionSynthesisAgent: { script: 'agents/emotion_synthesis_agent.py', port: 5706, dependencies: { EmotionEngine: 5575 } }

  # Utilities & System Monitoring
  ConsolidatedTranslator: { script: 'FORMAINPC/consolidated_translator.py', port: 5563, dependencies: { NLLBAdapter: 5562 } }
  ToneDetector: { script: 'agents/tone_detector.py', port: 5625, dependencies: { EmotionEngine: 5575 } }
  VoiceProfiler: { script: 'agents/voice_profiling_agent.py', port: 5626, dependencies: { CognitiveModelAgent: 5641 } }
  ChitChatAgent: { script: 'agents/chitchat_agent.py', port: 5627, dependencies: {} }
  UnifiedSystemAgent: { script: 'agents/unified_system_agent.py', port: 5628, dependencies: { PerformanceMonitoringAgent: 5632, PredictiveHealthMonitor: 5633 } }
  PerformanceMonitoringAgent: { script: 'agents/performance_monitoring_agent.py', port: 5632, dependencies: {} }
  PredictiveHealthMonitor: { script: 'agents/predictive_health_monitor.py', port: 5633, dependencies: {} }

pc2_services:
  PC2_ExampleAgent1: { script: 'agents/_referencefolderpc2/pc2_agent1.py', port: 8001, dependencies: {} }
  PC2_ExampleAgent2: { script: 'agents/_referencefolderpc2/pc2_agent2.py', port: 8002, dependencies: { PC2_ExampleAgent1: 8001 } }
```

### Instruction 2.2: Create the Docker Compose Generator

Create the file `generate_compose_from_sot.py`. This script must read `config/source_of_truth_config.yaml` and dynamically generate a `docker-compose.yml` file for all services listed under `main_pc_services`. It should inject dependency connection details as command-line arguments into the `command` field for each service. Use the `SYSTEM_DESIGN.md` section "5.2 Configuration-Driven Startup" as a reference.

### Instruction 2.3: Create the System Integrity Validator

Create the file `validate_system_integrity.py`. This script must read `config/source_of_truth_config.yaml` and perform two critical checks:
1.  Verify that the `script` path for every agent in `main_pc_services` and `pc2_services` exists.
2.  Analyze the `dependencies` graph to detect any circular dependencies (e.g., Agent A depends on B, and B depends on A).

The script should output a clear success or failure message.

---

## Part 3: Agent Implementation

**Objective:** Create the Python scripts for each individual agent defined in `source_of_truth_config.yaml`. Each agent should be built according to its profile in `SYSTEM_DESIGN.md`.

**General Guidance for All Agents:**
-   All agents must inherit from `src.core.base_agent.BaseAgent`.
-   All agents must use `argparse` to accept their own port and the ports of their dependencies.
-   All agents must establish ZMQ `REQ` sockets to connect to their dependencies as defined in the SOT config.
-   The core logic for each agent should be implemented based on the "Responsibilities" and "Interactions" described in its profile in `SYSTEM_DESIGN.md`.

### Instruction 3.1: Create Core Orchestration & Routing Agents

Create the following agent scripts. These form the central backbone of task management and model interaction.

1.  **`agents/GoalOrchestratorAgent.py`**: Implement the logic for receiving goals, breaking them into tasks, and managing the overall state of a user request. It must connect to `TaskRouter` and `ModelManagerAgent`.
2.  **`agents/TaskRouter.py`**: Implement the logic for receiving tasks from the orchestrator and routing them to the appropriate specialist agent. This agent will eventually need a mapping of task types to agent addresses, but for now, a placeholder implementation is sufficient.
3.  **`agents/ModelManagerAgent.py`**: Implement the logic for loading, unloading, and managing different AI models. It must connect to the `EnhancedModelRouter`.
4.  **`agents/IntentionValidatorAgent.py`**: Implement the logic to receive raw user input, validate it, and transform it into a structured goal for the `GoalOrchestratorAgent`. It must connect to the `GoalOrchestratorAgent`.

### Instruction 3.2: Create Personality & Proactivity Agents

Create the following agent scripts. These agents give the system its character and its ability to act with foresight.

1.  **`FORMAINPC/DynamicIdentityAgent.py`**: Implement the logic to manage the AI's persona. This could involve adjusting response style, tone, and personality based on context or user preference.
2.  **`FORMAINPC/EmpathyAgent.py`**: Implement the ability to formulate empathetic responses. It must connect to the `EmotionEngine` to get context about the user's emotional state and use that to tailor the interaction.
3.  **`FORMAINPC/ProactiveAgent.py`**: Implement the logic for taking initiative. It should connect to the `PredictiveLoader` to get suggestions for actions that might be helpful to the user and decide when to present them.
4.  **`FORMAINPC/PredictiveLoader.py`**: Implement the logic to anticipate user needs based on patterns, context, or triggers from the `CognitiveModelAgent`. Its job is to pre-load data or prepare actions that the user might need next.

### Instruction 3.3: Create GPU & Advanced Reasoning Agents

Create the following agent scripts. These are specialized, often GPU-dependent, agents for powerful language processing and complex reasoning.

1.  **`FORMAINPC/EnhancedModelRouter.py`**: Implement a sophisticated router that selects the best model for a given task. It must connect to `TinyLlamaService` and `NLLBAdapter` and decide which one to use based on the request's requirements (e.g., speed, language, complexity).
2.  **`FORMAINPC/TinyLlamaService.py`**: Implement a wrapper for the TinyLlama model. This agent's responsibility is to expose the model's generation capabilities via a ZMQ API.
3.  **`FORMAINPC/NLLBAdapter.py`**: Implement a wrapper for the NLLB translation model. This agent's responsibility is to expose the model's translation capabilities via a ZMQ API.
4.  **`FORMAINPC/ChainOfThoughtAgent.py`**: Implement the Chain-of-Thought (CoT) reasoning process. This agent should be able to take a complex problem, break it down into a series of sequential reasoning steps, and articulate that process to arrive at a solution.
5.  **`FORMAINPC/GOT_TOTAgent.py`**: Implement the Graph-of-Thoughts (GoT) or Tree-of-Thoughts (ToT) reasoning process. This is more advanced than CoT, allowing the agent to explore multiple reasoning paths, evaluate them, and select the most promising one.

### Instruction 3.4: Create Learning & Adaptation Agents

Create the following agent scripts. These agents form a closed loop that allows the system to learn from its interactions and improve over time.

1.  **`FORMAINPC/LearningAdjusterAgent.py`**: Implement the logic to modify learning parameters. It must connect to `PerformanceMonitoringAgent` and `SelfTrainingOrchestrator` to get feedback and coordinate changes.
2.  **`FORMAINPC/LocalFineTunerAgent.py`**: Implement the core logic for fine-tuning a local model. It should be able to receive a command, load a dataset, run the training process, and save the resulting model. It must connect to `SelfTrainingOrchestrator` and `ModelManagerAgent`.
3.  **`FORMAINPC/SelfTrainingOrchestrator.py`**: Implement the master logic for the self-improvement cycle. It must connect to `LearningAdjusterAgent` and `LocalFineTunerAgent` to coordinate the entire process, from deciding when to train to deploying the new model.
4.  **`FORMAINPC/CognitiveModelAgent.py`**: Implement the logic to build and maintain a dynamic model of the user's preferences, habits, and knowledge. It must connect to `TaskRouter`, `ProactiveAgent`, and `PredictiveLoader` to both gather data and provide insights.

### Instruction 3.5: Create Emotion Subsystem Agents

Create the following agent scripts. These agents work together to make the AI emotionally intelligent.

1.  **`agents/emotion_engine.py`**: Implement the central logic for processing emotional data. It must connect to `ToneDetector`, `EmpathyAgent`, and `MoodTrackerAgent`. Its main role is to aggregate emotional inputs into a coherent model of the user's current state.
2.  **`agents/mood_tracker_agent.py`**: Implement the logic to log emotional states over time. It must connect to the `EmotionEngine` to receive data points. Its purpose is to identify long-term emotional trends.
3.  **`agents/human_awareness_agent.py`**: Implement the logic to infer the user's broader context, such as focus or cognitive load. It must connect to the `EmotionEngine` to help it make more nuanced judgments about the user's state.
4.  **`agents/emotion_synthesis_agent.py`**: Implement the logic for generating emotionally appropriate responses. It must connect to the `EmotionEngine` to understand the required emotional tone and then craft a response (e.g., choosing specific words or vocal inflections) to match.

### Instruction 3.6: Create Utilities & System Monitoring Agents

Create the following agent scripts. These provide essential support services and ensure the stability of the entire system.

1.  **`FORMAINPC/consolidated_translator.py`**: Implement a unified interface for translation. It must connect to the `NLLBAdapter`.
2.  **`agents/tone_detector.py`**: Implement the logic to analyze audio and detect emotional tone. It must connect to the `EmotionEngine` to send its findings.
3.  **`agents/voice_profiling_agent.py`**: Implement logic for voice recognition to identify different users. It must connect to the `CognitiveModelAgent` to load the appropriate user profile.
4.  **`agents/chitchat_agent.py`**: Implement logic to handle non-goal-oriented, conversational small talk.
5.  **`agents/unified_system_agent.py`**: Implement a single point of control for system-wide commands (e.g., status checks, restarts). It must connect to `PerformanceMonitoringAgent` and `PredictiveHealthMonitor`.
6.  **`agents/performance_monitoring_agent.py`**: Implement logic to track and log performance metrics (CPU, memory, latency) for all other agents.
7.  **`agents/predictive_health_monitor.py`**: Implement logic to perform regular health checks on all agents and predict potential failures by analyzing trends.

---

## Part 4: System Launch & Verification

**Objective:** Create the main launch script and provide the final commands to run and verify the entire system.

### Instruction 4.1: Create the Main System Launcher

Create the file `start_ai_system.py`. This script is the primary entry point for running the system locally. It must:
1.  Load the `source_of_truth_config.yaml`.
2.  Load environment variables from the `.env` file (specifically for `PC2_HOST`).
3.  Iterate through the `main_pc_services`.
4.  For each service, launch its corresponding script as a new subprocess using Python's `subprocess` module.
5.  Dynamically construct and pass command-line arguments for the agent's own port and the ports of all its dependencies.
6.  Include logic to monitor the health of the started subprocesses and manage their lifecycle.

### Instruction 4.2: Final Execution Order

Provide the following sequence of commands to be executed in the terminal from the root directory to build, validate, and run the system.

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Validate System Integrity:**
    ```bash
    python validate_system_integrity.py
    ```
    *(This should pass without errors.)*

3.  **Generate Docker Compose File:**
    ```bash
    python generate_compose_from_sot.py
    ```
4.  **Launch the System (Choose one):**
    -   **Option A: Local Launch (via script)**
        ```bash
        python start_ai_system.py
        ```
    -   **Option B: Docker Launch**
        ```bash
        docker-compose up -d
        ```

---

## Conclusion

Following these instructions will result in a complete, running instance of the `Voice-Assistant-Prod` system. The architecture is modular, configuration-driven, and verifiable at each step. This blueprint provides a repeatable and automated path for system deployment and maintenance.
