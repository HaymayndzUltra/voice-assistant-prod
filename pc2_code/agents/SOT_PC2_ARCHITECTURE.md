# PC2 Architecture - Source of Truth

## The Subconscious Mind & Knowledge Base

This document serves as the definitive source of truth for the PC2 ecosystem, which functions as the subconscious mind and knowledge base of our AI system. PC2 handles advanced cognitive functions, memory management, and complex decision-making processes.

## High-Level Architecture

```
[Main PC] <---> [PC2] <---> [External Services]
   |            /|\
   |             |
   |        [Core Agents]
   |             |
   |        [Advanced Agents]
   |             |
   |        [Memory System]
   |             |
   |        [Learning System]
```

## Agent Profiles

### Core Agents

#### 1. UnifiedMemoryReasoningAgent (Port 5631)

- **Primary Purpose**: Central memory management and reasoning
- **Key Dependencies**:
  - EpisodicMemoryAgent
  - EnhancedModelRouter
  - PerformanceLoggerAgent
- **Communication**: Handles memory queries and updates from all other agents

#### 2. EnhancedModelRouter (Port 5632)

- **Primary Purpose**: Intelligent routing of requests to appropriate models
- **Key Dependencies**:
  - PerformanceLoggerAgent
  - ConsolidatedTranslator
- **Communication**: Routes requests between agents and models

#### 3. PerformanceLoggerAgent (Port 5633)

- **Primary Purpose**: System-wide performance monitoring
- **Key Dependencies**: None
- **Communication**: Receives metrics from all agents

#### 4. CoordinatorAgent (Port 5634)

- **Primary Purpose**: Task orchestration and agent coordination
- **Key Dependencies**:
  - All core agents
  - MultiAgentSwarmManager
- **Communication**: Coordinates complex tasks across agents

### Advanced Agents

#### 1. DreamingModeAgent (Port 5640)

- **Primary Purpose**: Simulates AI "dreaming" for pattern discovery
- **Key Dependencies**:
  - EpisodicMemoryAgent
  - EnhancedModelRouter
- **Communication**: Analyzes memories during "dreaming" sessions

#### 2. CognitiveModelAgent (Port 5641)

- **Primary Purpose**: Maintains belief system using graph database
- **Key Dependencies**: None (uses internal networkx)
- **Communication**: Manages and queries belief relationships

#### 3. DreamWorldAgent (Port 5642)

- **Primary Purpose**: Runs simulations using MCTS
- **Key Dependencies**: None
- **Communication**: Simulates scenarios and returns outcomes

#### 4. MultiAgentSwarmManager (Port 5643)

- **Primary Purpose**: Orchestrates complex tasks using multiple agents
- **Key Dependencies**:
  - AutonomousWebAssistant
  - EnhancedModelRouter
  - CoordinatorAgent
- **Communication**: Breaks down and executes complex tasks

#### 5. DynamicIdentityAgent (Port 5644)

- **Primary Purpose**: Manages AI persona and voice settings
- **Key Dependencies**:
  - EnhancedModelRouter
  - EmpathyAgent
- **Communication**: Updates system behavior based on persona

### Memory System Agents

#### 1. EpisodicMemoryAgent (Port 5631)

- **Primary Purpose**: Manages episodic memories
- **Key Dependencies**:
  - UnifiedMemoryReasoningAgent
  - MemoryDecayManager
- **Communication**: Stores and retrieves episodic memories

#### 2. MemoryDecayManager

- **Primary Purpose**: Manages memory decay and retention
- **Key Dependencies**: None
- **Communication**: Updates memory weights and importance

### Learning System Agents

#### 1. LearningAdjusterAgent

- **Primary Purpose**: Adapts learning parameters
- **Key Dependencies**:
  - PerformanceLoggerAgent
  - SelfTrainingOrchestrator
- **Communication**: Adjusts learning rates and strategies

#### 2. SelfTrainingOrchestrator

- **Primary Purpose**: Manages self-training processes
- **Key Dependencies**:
  - LocalFineTunerAgent
  - ActiveLearningMonitor
- **Communication**: Coordinates training sessions

## Communication Diagram

```
[Main PC]
   |
   |---> [RemoteConnectorAgent] <---|
   |                               |
   |---> [UnifiedWebAgent] <-------|
   |                               |
   |---> [CoordinatorAgent] <------|
   |        |
   |        |---> [EnhancedModelRouter]
   |        |        |
   |        |        |---> [ConsolidatedTranslator]
   |        |        |
   |        |        |---> [DynamicIdentityAgent]
   |        |
   |        |---> [UnifiedMemoryReasoningAgent]
   |        |        |
   |        |        |---> [EpisodicMemoryAgent]
   |        |        |
   |        |        |---> [MemoryDecayManager]
   |        |
   |        |---> [MultiAgentSwarmManager]
   |        |        |
   |        |        |---> [DreamingModeAgent]
   |        |        |
   |        |        |---> [CognitiveModelAgent]
   |        |        |
   |        |        |---> [DreamWorldAgent]
   |        |
   |        |---> [PerformanceLoggerAgent]
   |
   |---> [SelfHealingAgent]
```

## System Requirements

### Hardware Requirements

- CPU: 8+ cores recommended
- RAM: 16GB minimum, 32GB recommended
- Storage: 100GB+ SSD
- GPU: NVIDIA GPU with 8GB+ VRAM (for ML tasks)

### Software Requirements

- Python 3.10+
- CUDA 11.8+ (for GPU support)
- See requirements_pc2.txt for detailed package versions

## Deployment Notes

1. **Installation**:

   ```bash
   pip install -r requirements_pc2.txt
   ```

2. **Configuration**:

   - Update config/system_config.py with appropriate settings
   - Set up environment variables in .env file

3. **Starting the System**:

   ```bash
   python start_all_pc2_agents.bat
   ```

4. **Monitoring**:
   - Check logs/ directory for detailed logs
   - Use Mission Control Dashboard for real-time monitoring

## Maintenance

1. **Regular Tasks**:

   - Monitor log files for errors
   - Check system performance metrics
   - Backup memory database regularly

2. **Troubleshooting**:
   - Check agent status in Mission Control Dashboard
   - Review agent-specific logs
   - Verify network connectivity between agents

## Security Considerations

1. **Network Security**:

   - All inter-agent communication uses ZMQ
   - Ports 5630-5644 must be accessible
   - Consider using VPN for remote connections

2. **Data Security**:
   - Sensitive data is encrypted at rest
   - Memory data is regularly backed up
   - Access logs are maintained for audit purposes
