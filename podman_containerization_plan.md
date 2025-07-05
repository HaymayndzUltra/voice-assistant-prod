# Podman Containerization Plan for AI System

## Overview

After analyzing the system's architecture and agent configurations from both MainPC and PC2, this document outlines a comprehensive plan to containerize the AI System using Podman.

## Current System Analysis

### MainPC Configuration
- 60+ agents organized in functional groups in `main_pc_code/config/startup_config.yaml`
- Dependency-based startup sequence managed by Agent Supervisor
- Core services include ModelManagerAgent, CoordinatorAgent, ChainOfThoughtAgent, etc.

### PC2 Configuration
- 30+ agents defined in `pc2_code/config/startup_config.yaml`
- Integration layer agents for communication with MainPC
- Authentication and security-focused agents

## Containerization Strategy

### 1. Container Organization

#### 1.1 Base Container
```dockerfile
# Base Dockerfile (docker/Dockerfile.base)
FROM python:3.9-slim

# Install common dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libzmq3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models /app/config

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PROJECT_ROOT=/app
ENV PYTHONPATH=/app

# Default command
CMD ["python3", "-u", "agent_runner.py"]
```

#### 1.2 Functional Group Containers for MainPC

Group agents by functional area to reduce container count and resource overhead:

1. **Core Services Container**
   - ModelManagerAgent
   - CoordinatorAgent
   - ChainOfThoughtAgent
   - GoTToTAgent
   - SystemDigitalTwin
   - PredictiveHealthMonitor

2. **Memory System Container**
   - MemoryOrchestrator
   - SessionMemoryAgent
   - MemoryManager
   - MemoryClient
   - KnowledgeBase

3. **Audio Processing Container**
   - AudioCapture
   - FusedAudioPreprocessor
   - WakeWordDetector
   - StreamingSpeechRecognition
   - StreamingInterruptHandler
   - StreamingLanguageAnalyzer
   - LanguageAndTranslationCoordinator

4. **Language Processing Container**
   - NLUAgent
   - AdvancedCommandHandler
   - ChitchatAgent
   - Responder
   - FeedbackHandler
   - TaskRouter

5. **Emotion System Container**
   - EmotionEngine
   - MoodTrackerAgent
   - HumanAwarenessAgent
   - ToneDetector
   - VoiceProfiler
   - EmpathyAgent
   - EmotionSynthesisAgent

6. **GPU Services Container**
   - TinyLlamaService
   - SelfTrainingOrchestrator
   - EnhancedModelRouter
   - NLLBAdapter
   - ConsolidatedTranslator
   - CognitiveModelAgent
   - LearningAdjusterAgent
   - LocalFineTunerAgent

   > **Note on Path Handling**: The GPU Services container includes special path handling to accommodate inconsistent path references in the codebase. Some files reference paths as `FORMAINPC/file.py` while others use `main_pc_code/FORMAINPC/file.py`. The container creates a symlink structure that supports both formats, ensuring compatibility without modifying the source code.

7. **Planning & Execution Container**
   - GoalOrchestratorAgent
   - IntentionValidatorAgent
   - DynamicIdentityAgent
   - ProactiveAgent
   - PredictiveLoader
   - UnifiedPlanningAgent
   - MultiAgentSwarmManager
   - UnifiedSystemAgent

8. **TTS Services Container**
   - StreamingTTSAgent
   - TTSConnector
   - TTSCache
   - TTSAgent

9. **Code Generation Container**
   - CodeGenerator
   - Executor

10. **Vision Container**
    - VisionCaptureAgent
    - FaceRecognitionAgent

11. **Learning & Knowledge Container**
    - LearningManager
    - MetaCognitionAgent
    - ActiveLearningMonitor
    - VRAMOptimizerAgent

#### 1.3 Functional Group Containers for PC2

1. **PC2 Core Container**
   - AuthenticationAgent
   - UnifiedErrorAgent
   - UnifiedUtilsAgent
   - ResourceManager
   - HealthMonitor
   - AdvancedRouter

2. **PC2 Integration Container**
   - TieredResponder
   - AsyncProcessor
   - CacheManager
   - PerformanceMonitor
   - VisionProcessingAgent

3. **PC2 Memory Container**
   - UnifiedMemoryReasoningAgent
   - EpisodicMemoryAgent
   - MemoryManager
   - ContextManager
   - ExperienceTracker
   - ProactiveContextMonitor

4. **PC2 Learning Container**
   - DreamWorldAgent
   - LearningAgent
   - TutorAgent
   - TutoringServiceAgent
   - DreamingModeAgent

5. **PC2 Utility Container**
   - TaskScheduler
   - RCAAgent
   - AgentTrustScorer
   - FileSystemAssistantAgent
   - RemoteConnectorAgent
   - SelfHealingAgent
   - UnifiedWebAgent
   - PerformanceLoggerAgent

### 2. Network Configuration

#### 2.1 Podman Pod-based Networking

```bash
# Create network for MainPC
podman network create ai_system_mainpc

# Create network for PC2
podman network create ai_system_pc2

# Create pod for core services
podman pod create --name core-services-pod --network ai_system_mainpc \
  -p 7120:7120 -p 5570:5570 -p 26002:26002 -p 5612:5612 -p 5646:5646
```

#### 2.2 Cross-Machine Communication

```yaml
# docker-compose.mainpc.yml network section
networks:
  ai_system_mainpc:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 3. Volume Management

```yaml
volumes:
  - ./logs:/app/logs
  - ./models:/app/models
  - ./data:/app/data
  - ./config:/app/config
```

### 4. Health Check Implementation

```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.connect('tcp://localhost:5571'); socket.send_json({'action': 'health_check'}); socket.setsockopt(zmq.RCVTIMEO, 5000); print(socket.recv_json())"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 20s
```

### 5. Agent Supervisor Integration

Modify the Agent Supervisor to work within the containerized environment:

1. Update path resolution to work with container paths
2. Configure health checks to use container networking
3. Implement container-aware process management

## Implementation Plan

### Phase 1: Base Infrastructure (Week 1)

1. Create base container image
2. Set up Podman networking
3. Create volume mounts
4. Implement container-specific path resolution

### Phase 2: Core Services (Week 1-2)

1. Containerize Core Services group
2. Implement health checks
3. Test stability and communication
4. Document configuration

### Phase 3: Functional Groups (Week 2-3)

1. Containerize remaining functional groups
2. Test inter-group communication
3. Validate health monitoring
4. Optimize resource allocation
5. **Address Missing Dependencies**: 
   - The `PhiTranslationService` referenced in the startup config is missing from the codebase
   - Modify the `ConsolidatedTranslator` to use the `fixed_streaming_translation.py` as a fallback when PhiTranslationService is unavailable
   - Add a startup check in the GPU Services container to verify all required services are available

### Phase 4: PC2 Integration (Week 3-4)

1. Containerize PC2 services
2. Configure cross-machine communication
3. Test MainPC-PC2 interaction
4. Document deployment process

## Deployment Configuration

### MainPC Podman Compose File

```yaml
# podman-compose.mainpc.yml
version: '3'

networks:
  ai_system_mainpc:
    external: true

volumes:
  logs_volume:
  models_volume:
  data_volume:
  config_volume:

services:
  core-services:
    image: ai_system/core-services:latest
    container_name: core-services
    ports:
      - "7120:7120"  # SystemDigitalTwin
      - "5570:5570"  # ModelManagerAgent
      - "26002:26002"  # CoordinatorAgent
      - "5612:5612"  # ChainOfThoughtAgent
      - "5646:5646"  # GoTToTAgent
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - MACHINE_TYPE=mainpc
      - LOG_LEVEL=INFO
      - ENABLE_METRICS=true
      - PC2_IP=192.168.1.102
    healthcheck:
      test: ["CMD", "python3", "-c", "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.connect('tcp://localhost:7121'); socket.send_json({'action': 'health_check'}); socket.setsockopt(zmq.RCVTIMEO, 5000); print(socket.recv_json())"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      ai_system_mainpc:
        ipv4_address: 172.20.0.10
    restart: unless-stopped
    command: ["python3", "-u", "/app/main_pc_code/utils/agent_supervisor.py", "--config", "/app/config/core_services.yaml"]

  memory-system:
    image: ai_system/memory-system:latest
    container_name: memory-system
    depends_on:
      core-services:
        condition: service_healthy
    ports:
      - "5575:5575"  # MemoryOrchestrator
      - "5574:5574"  # SessionMemoryAgent
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - MACHINE_TYPE=mainpc
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "python3", "-c", "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.connect('tcp://localhost:5576'); socket.send_json({'action': 'health_check'}); socket.setsockopt(zmq.RCVTIMEO, 5000); print(socket.recv_json())"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      ai_system_mainpc:
        ipv4_address: 172.20.0.20
    restart: unless-stopped
    command: ["python3", "-u", "/app/main_pc_code/utils/agent_supervisor.py", "--config", "/app/config/memory_system.yaml"]

  gpu-services:
    image: ai_system/gpu-services:latest
    container_name: gpu-services
    depends_on:
      core-services:
        condition: service_healthy
      memory-system:
        condition: service_healthy
    ports:
      - "5615:5615"  # TinyLlamaService
      - "5581:5581"  # NLLBAdapter
      - "5598:5598"  # EnhancedModelRouter
      - "5641:5641"  # CognitiveModelAgent
      - "5563:5563"  # ConsolidatedTranslator
      - "5643:5643"  # LearningAdjusterAgent
      - "5645:5645"  # LocalFineTunerAgent
      - "5644:5644"  # SelfTrainingOrchestrator
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - MACHINE_TYPE=mainpc
      - LOG_LEVEL=INFO
      - ENABLE_GPU=true
      - NLTK_DATA=/app/data/nltk_data
      - PYTHONPATH=/app:/app/main_pc_code:${PYTHONPATH}
    healthcheck:
      test: ["CMD", "python3", "-c", "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.connect('tcp://localhost:5563'); socket.send_json({'action': 'health_check'}); socket.setsockopt(zmq.RCVTIMEO, 5000); print(socket.recv_json())"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      ai_system_mainpc:
        ipv4_address: 172.20.0.30
    restart: unless-stopped
    command: ["python3", "-u", "/app/main_pc_code/utils/agent_supervisor.py", "--config", "/app/config/gpu_services.yaml"]

  # Additional service definitions for other functional groups...
```

### PC2 Podman Compose File

```yaml
# podman-compose.pc2.yml
version: '3'

networks:
  ai_system_pc2:
    external: true

volumes:
  logs_volume:
  data_volume:
  config_volume:

services:
  pc2-core:
    image: ai_system/pc2-core:latest
    container_name: pc2-core
    ports:
      - "7116:7116"  # AuthenticationAgent
      - "7118:7118"  # UnifiedUtilsAgent
      - "7129:7129"  # AdvancedRouter
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - MACHINE_TYPE=pc2
      - LOG_LEVEL=INFO
      - MAINPC_IP=192.168.1.101
    healthcheck:
      test: ["CMD", "python3", "-c", "import zmq; context = zmq.Context(); socket = context.socket(zmq.REQ); socket.connect('tcp://localhost:8116'); socket.send_json({'action': 'health_check'}); socket.setsockopt(zmq.RCVTIMEO, 5000); print(socket.recv_json())"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      ai_system_pc2:
        ipv4_address: 172.21.0.10
    restart: unless-stopped
    command: ["python3", "-u", "/app/pc2_code/utils/agent_supervisor.py", "--config", "/app/config/pc2_core.yaml"]

  # Additional service definitions for PC2...
```

## Deployment Scripts

### MainPC Deployment Script

```bash
#!/bin/bash
# deploy_mainpc.sh

# Set environment variables
export MACHINE_TYPE=mainpc

# Navigate to project root
cd "$(dirname "$0")/.."

# Build images
echo "Building base image..."
podman build -t ai_system/base:latest -f docker/Dockerfile.base .

echo "Building core services image..."
podman build -t ai_system/core-services:latest -f docker/Dockerfile.core-services .

echo "Building memory system image..."
podman build -t ai_system/memory-system:latest -f docker/Dockerfile.memory-system .

# Create network if it doesn't exist
podman network exists ai_system_mainpc || podman network create ai_system_mainpc

# Deploy using podman-compose
echo "Deploying MainPC services..."
podman-compose -f docker/podman-compose.mainpc.yml up -d

echo "MainPC deployment complete"
```

### PC2 Deployment Script

```bash
#!/bin/bash
# deploy_pc2.sh

# Set environment variables
export MACHINE_TYPE=pc2

# Navigate to project root
cd "$(dirname "$0")/.."

# Build images
echo "Building base image..."
podman build -t ai_system/base:latest -f docker/Dockerfile.base .

echo "Building PC2 core image..."
podman build -t ai_system/pc2-core:latest -f docker/Dockerfile.pc2-core .

# Create network if it doesn't exist
podman network exists ai_system_pc2 || podman network create ai_system_pc2

# Deploy using podman-compose
echo "Deploying PC2 services..."
podman-compose -f docker/podman-compose.pc2.yml up -d

echo "PC2 deployment complete"
```

## Configuration Split

Create separate configuration files for each container group:

```
config/
  core_services.yaml
  memory_system.yaml
  audio_processing.yaml
  language_processing.yaml
  emotion_system.yaml
  gpu_services.yaml
  planning_execution.yaml
  tts_services.yaml
  code_generation.yaml
  vision.yaml
  learning_knowledge.yaml
  pc2_core.yaml
  pc2_integration.yaml
  pc2_memory.yaml
  pc2_learning.yaml
  pc2_utility.yaml
```

## Conclusion

This containerization plan provides a structured approach to migrate the AI System to Podman containers while maintaining system stability and performance. By grouping agents functionally and using Podman's pod feature, we can simplify networking while preserving the complex interactions between agents.

The phased implementation approach allows for incremental validation and testing, reducing the risk of system-wide failures. The container-native health checks ensure that the system remains robust and self-healing in the containerized environment.

Once implemented, this containerized architecture will provide better resource isolation, simpler deployment, and improved system reliability. 

## Appendix: Additional Configuration Files

### GPU Services Dockerfile

```dockerfile
# docker/Dockerfile.gpu-services
FROM ai_system/base:latest

# Install GPU services specific dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcudnn8 \
    cuda-toolkit-11-8 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.gpu-services.txt /app/
RUN pip install --no-cache-dir -r requirements.gpu-services.txt

# Install NLTK data
RUN python -m nltk.downloader punkt -d /app/data/nltk_data

# Set up directory structure
RUN mkdir -p /app/main_pc_code/FORMAINPC \
    /app/main_pc_code/src/core \
    /app/main_pc_code/src/memory \
    /app/main_pc_code/src/network \
    /app/main_pc_code/utils \
    /app/main_pc_code/config \
    /app/main_pc_code/agents \
    /app/main_pc_code/agents/needtoverify \
    /app/FORMAINPC \
    /app/agents

# Copy necessary files
COPY main_pc_code/src/core /app/main_pc_code/src/core/
COPY main_pc_code/src/memory /app/main_pc_code/src/memory/
COPY main_pc_code/src/network /app/main_pc_code/src/network/
COPY main_pc_code/utils /app/main_pc_code/utils/
COPY main_pc_code/config /app/main_pc_code/config/
COPY main_pc_code/FORMAINPC/*.py /app/main_pc_code/FORMAINPC/
COPY main_pc_code/agents/needtoverify/fixed_streaming_translation.py /app/main_pc_code/agents/needtoverify/
COPY main_pc_code/agents/language_and_translation_coordinator.py /app/main_pc_code/agents/

# Create symlinks for compatibility with different path references
# This allows scripts to work with both path styles: FORMAINPC/file.py and main_pc_code/FORMAINPC/file.py
RUN ln -sf /app/main_pc_code/FORMAINPC/*.py /app/FORMAINPC/ && \
    ln -sf /app/main_pc_code/agents/* /app/agents/ && \
    ln -sf /app/main_pc_code /app/src

# Set PYTHONPATH to include all possible paths
ENV PYTHONPATH=/app:/app/main_pc_code:${PYTHONPATH}

# Create config file
COPY config/gpu_services.yaml /app/config/

# Set working directory
WORKDIR /app

# Default command
CMD ["python3", "-u", "/app/main_pc_code/utils/agent_supervisor.py", "--config", "/app/config/gpu_services.yaml"]
```

### GPU Services Requirements File

```
# requirements.gpu-services.txt
torch>=2.0.0
transformers>=4.30.0
nltk>=3.8.1
langdetect>=1.0.9
pyzmq>=24.0.0
requests>=2.28.0
psutil>=5.9.0
numpy>=1.24.0
scikit-learn>=1.2.0
sentencepiece>=0.1.99
protobuf>=3.20.0
googletrans>=4.0.0-rc1
```

### GPU Services Configuration

```yaml
# config/gpu_services.yaml
agents:
  - name: TinyLlamaService
    script_path: FORMAINPC/TinyLlamaServiceEnhanced.py
    host: 0.0.0.0
    port: 5615
    required: true
    dependencies: [ModelManagerAgent]
    
  - name: NLLBAdapter
    script_path: FORMAINPC/NLLBAdapter.py
    host: 0.0.0.0
    port: 5581
    required: true
    dependencies: [ModelManagerAgent]
    
  - name: EnhancedModelRouter
    script_path: FORMAINPC/EnhancedModelRouter.py
    host: 0.0.0.0
    port: 5598
    required: true
    dependencies: [ModelManagerAgent, ChainOfThoughtAgent]
    
  - name: CognitiveModelAgent
    script_path: FORMAINPC/CognitiveModelAgent.py
    host: 0.0.0.0
    port: 5641
    required: true
    dependencies: [ChainOfThoughtAgent]
    
  - name: ConsolidatedTranslator
    script_path: FORMAINPC/consolidated_translator.py
    host: 0.0.0.0
    port: 5563
    dependencies: [MemoryOrchestrator, ModelManagerAgent, NLLBAdapter]
    required: true
    
  - name: LearningAdjusterAgent
    script_path: FORMAINPC/LearningAdjusterAgent.py
    host: 0.0.0.0
    port: 5643
    required: true
    dependencies: [SelfTrainingOrchestrator]
    
  - name: LocalFineTunerAgent
    script_path: FORMAINPC/LocalFineTunerAgent.py
    host: 0.0.0.0
    port: 5645
    required: true
    dependencies: [SelfTrainingOrchestrator]
    
  - name: SelfTrainingOrchestrator
    script_path: FORMAINPC/SelfTrainingOrchestrator.py
    host: 0.0.0.0
    port: 5644
    required: true
``` 