# DETAILED PODMAN CONTAINERIZATION PLAN
## AI System Monorepo - MainPC Agents

## EXECUTIVE SUMMARY
Based on deep scan of 192 agent files, this plan provides a comprehensive phase-by-phase approach to containerize the AI system using Podman.

---

## PHASE 1: DEPENDENCY ANALYSIS

### Current System Analysis
**Total Agents:** 192 Python files
**Minimal System Config:** 8 core agents
**LLM-Dependent Agents:** 3 agents require transformers/torch

#### Core Agents (Minimal System):
1. **SystemDigitalTwin** - Port: 7120, Health: 7121, LLM: ❌ No
2. **ModelManagerAgent** - Port: 5570, Health: 5571, LLM: ⚠️ PyTorch for GPU monitoring
3. **CoordinatorAgent** - Port: 26002, Health: 26003, LLM: ❌ No
4. **ChainOfThoughtAgent** - Port: 5612, Health: 5613, LLM: ❌ No
5. **GoTToTAgent** - Port: 7000, Health: 7001, LLM: ✅ Transformers + PyTorch
6. **SelfTrainingOrchestrator** - Port: 5644, Health: 5645, LLM: ❌ No
7. **EmotionEngine** - Port: 5590, Health: 5591, LLM: ❌ No
8. **AudioCapture** - Port: 6575, Health: 6576, LLM: ⚠️ PyTorch for audio

### Dependency Categories
- **Heavy LLM**: GoTToTAgent, TinyLlamaService, NLLBAdapter, PhiTranslationService
- **Light ML**: ModelManagerAgent, AudioCapture, EmotionEngine
- **No ML**: SystemDigitalTwin, CoordinatorAgent, ChainOfThoughtAgent, SelfTrainingOrchestrator

---

## PHASE 2: CONTAINER ARCHITECTURE

### Container Grouping Strategy

#### Group 1: Core Services (No ML Dependencies)
```yaml
# core-services-pod
- SystemDigitalTwin
- CoordinatorAgent
- ChainOfThoughtAgent
- SelfTrainingOrchestrator
```

#### Group 2: GPU Services (Heavy LLM Dependencies)
```yaml
# gpu-services-pod
- GoTToTAgent
- TinyLlamaService (if needed)
- NLLBAdapter (if needed)
- PhiTranslationService (if needed)
```

#### Group 3: System Services (Light ML Dependencies)
```yaml
# system-services-pod
- ModelManagerAgent
- EmotionEngine
- AudioCapture
```

### Network Architecture
```bash
# Create networks
podman network create ai-system-network --subnet 172.20.0.0/16
podman network create core-services-network --subnet 172.21.0.0/16
podman network create gpu-services-network --subnet 172.22.0.0/16
podman network create system-services-network --subnet 172.23.0.0/16
```

---

## PHASE 3: BASE IMAGE CREATION

### Base Image Strategy

#### A. Core Base Image (No ML Dependencies)
```dockerfile
# Dockerfile.core
FROM python:3.11-slim
RUN apt-get update && apt-get install -y gcc g++ libzmq3-dev
COPY requirements.core.txt /app/
RUN pip install -r requirements.core.txt
WORKDIR /app
```

#### B. GPU Base Image (ML Dependencies)
```dockerfile
# Dockerfile.gpu
FROM nvidia/cuda:11.8-devel-ubuntu22.04
RUN apt-get update && apt-get install -y python3.11 python3.11-pip python3.11-dev gcc g++ libzmq3-dev
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
COPY requirements.gpu.txt /app/
RUN pip3 install -r requirements.gpu.txt
WORKDIR /app
```

#### C. Audio Base Image (Audio Dependencies)
```dockerfile
# Dockerfile.audio
FROM python:3.11-slim
RUN apt-get update && apt-get install -y gcc g++ libzmq3-dev ffmpeg portaudio19-dev
COPY requirements.audio.txt /app/
RUN pip install -r requirements.audio.txt
WORKDIR /app
```

### Requirements File Separation

#### requirements.core.txt:
```
pyzmq>=25.1.0
numpy>=1.24.0
psutil>=5.9.0
python-json-logger>=2.0.0
pynacl>=1.5.0
flask==2.3.3
requests==2.31.0
pyyaml==6.0.1
python-dotenv==1.0.0
pydantic==2.4.2
fastapi==0.103.1
uvicorn==0.23.2
websockets==12.0
aiohttp==3.9.1
```

#### requirements.gpu.txt:
```
-r requirements.core.txt
torch>=2.0.0
transformers>=4.34.0
sentencepiece>=0.1.99
accelerate>=0.23.0
bitsandbytes>=0.41.1
optimum>=1.13.2
peft>=0.5.0
trl>=0.7.4
einops>=0.7.0
xformers>=0.0.22.post7
```

#### requirements.audio.txt:
```
-r requirements.core.txt
librosa>=0.10.1
sounddevice>=0.4.6
soundfile>=0.12.1
noisereduce>=2.0.1
webrtcvad>=2.0.10
pydub>=0.25.1
ffmpeg-python>=0.2.0
openai-whisper>=20231117
pvporcupine>=3.0.0
torchaudio>=2.1.0
```

---

## PHASE 4: CONTAINER IMPLEMENTATION

### Core Services Container

#### docker-compose.core-services.yml:
```yaml
version: '3.8'

services:
  system-digital-twin:
    build:
      context: .
      dockerfile: Dockerfile.core-services
    container_name: system-digital-twin
    networks:
      core-services-network:
        ipv4_address: 172.21.0.10
    ports:
      - "7120:7120"
      - "7121:7121"
    environment:
      - AGENT_NAME=SystemDigitalTwin
      - PORT=7120
      - HEALTH_CHECK_PORT=7121
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    command: ["python3", "main_pc_code/agents/system_digital_twin.py"]

  coordinator-agent:
    build:
      context: .
      dockerfile: Dockerfile.core-services
    container_name: coordinator-agent
    networks:
      core-services-network:
        ipv4_address: 172.21.0.11
    ports:
      - "26002:26002"
      - "26003:26003"
    environment:
      - AGENT_NAME=CoordinatorAgent
      - PORT=26002
      - HEALTH_CHECK_PORT=26003
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    command: ["python3", "main_pc_code/agents/coordinator_agent.py"]
    depends_on:
      - system-digital-twin

  chain-of-thought-agent:
    build:
      context: .
      dockerfile: Dockerfile.core-services
    container_name: chain-of-thought-agent
    networks:
      core-services-network:
        ipv4_address: 172.21.0.12
    ports:
      - "5612:5612"
      - "5613:5613"
    environment:
      - AGENT_NAME=ChainOfThoughtAgent
      - PORT=5612
      - HEALTH_CHECK_PORT=5613
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    command: ["python3", "main_pc_code/FORMAINPC/ChainOfThoughtAgent.py"]
    depends_on:
      - coordinator-agent

  self-training-orchestrator:
    build:
      context: .
      dockerfile: Dockerfile.core-services
    container_name: self-training-orchestrator
    networks:
      core-services-network:
        ipv4_address: 172.21.0.13
    ports:
      - "5644:5644"
      - "5645:5645"
    environment:
      - AGENT_NAME=SelfTrainingOrchestrator
      - PORT=5644
      - HEALTH_CHECK_PORT=5645
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
      - ./models:/app/models
    command: ["python3", "main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py"]
    depends_on:
      - chain-of-thought-agent

networks:
  core-services-network:
    external: true
```

### GPU Services Container

#### docker-compose.gpu-services.yml:
```yaml
version: '3.8'

services:
  got-tot-agent:
    build:
      context: .
      dockerfile: Dockerfile.gpu-services
    container_name: got-tot-agent
    networks:
      gpu-services-network:
        ipv4_address: 172.22.0.10
    ports:
      - "7000:7000"
      - "7001:7001"
    environment:
      - AGENT_NAME=GoTToTAgent
      - PORT=7000
      - HEALTH_CHECK_PORT=7001
      - CUDA_VISIBLE_DEVICES=0
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
      - ./models:/app/models
    command: ["python3", "main_pc_code/FORMAINPC/GOT_TOTAgent.py"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

networks:
  gpu-services-network:
    external: true
```

### System Services Container

#### docker-compose.system-services.yml:
```yaml
version: '3.8'

services:
  model-manager-agent:
    build:
      context: .
      dockerfile: Dockerfile.system-services
    container_name: model-manager-agent
    networks:
      system-services-network:
        ipv4_address: 172.23.0.10
    ports:
      - "5570:5570"
      - "5571:5571"
    environment:
      - AGENT_NAME=ModelManagerAgent
      - PORT=5570
      - HEALTH_CHECK_PORT=5571
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
      - ./models:/app/models
    command: ["python3", "main_pc_code/agents/model_manager_agent.py"]

  emotion-engine:
    build:
      context: .
      dockerfile: Dockerfile.system-services
    container_name: emotion-engine
    networks:
      system-services-network:
        ipv4_address: 172.23.0.11
    ports:
      - "5590:5590"
      - "5591:5591"
    environment:
      - AGENT_NAME=EmotionEngine
      - PORT=5590
      - HEALTH_CHECK_PORT=5591
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    command: ["python3", "main_pc_code/agents/emotion_engine.py"]
    depends_on:
      - model-manager-agent

  audio-capture:
    build:
      context: .
      dockerfile: Dockerfile.system-services
    container_name: audio-capture
    networks:
      system-services-network:
        ipv4_address: 172.23.0.12
    ports:
      - "6575:6575"
      - "6576:6576"
    environment:
      - AGENT_NAME=AudioCapture
      - PORT=6575
      - HEALTH_CHECK_PORT=6576
      - USE_DUMMY_AUDIO=true
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
      - /dev/snd:/dev/snd
    command: ["python3", "main_pc_code/agents/streaming_audio_capture.py"]
    depends_on:
      - emotion-engine

networks:
  system-services-network:
    external: true
```

---

## PHASE 5: DEPLOYMENT SCRIPTS

### setup-networks.sh:
```bash
# !/bin/bash
echo "Setting up Podman networks for AI System..."

podman network create ai-system-network --subnet 172.20.0.0/16
podman network create core-services-network --subnet 172.21.0.0/16
podman network create gpu-services-network --subnet 172.22.0.0/16
podman network create system-services-network --subnet 172.23.0.0/16

podman network connect ai-system-network core-services-network
podman network connect ai-system-network gpu-services-network
podman network connect ai-system-network system-services-network

echo "Networks created successfully!"
```

### build-images.sh:
```bash
# !/bin/bash
echo "Building AI System container images..."

podman build -f Dockerfile.core -t ai-system-core:latest .
podman build -f Dockerfile.gpu -t ai-system-gpu:latest .
podman build -f Dockerfile.audio -t ai-system-audio:latest .

echo "All base images built successfully!"
```

### deploy-system.sh:
```bash
# !/bin/bash
echo "Deploying AI System containers..."

echo "Starting core services..."
podman-compose -f docker-compose.core-services.yml up -d
sleep 30

echo "Starting system services..."
podman-compose -f docker-compose.system-services.yml up -d
sleep 30

echo "Starting GPU services..."
podman-compose -f docker-compose.gpu-services.yml up -d

echo "All services deployed successfully!"
```

### health-check.sh:
```bash
# !/bin/bash
echo "Checking AI System health..."

# Check core services
echo "Core Services Health:"
| podman exec system-digital-twin python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:7121'); s.send(b'health'); print('SystemDigitalTwin:', s.recv().decode()); s.close()" |  | echo "SystemDigitalTwin: FAILED" |

| podman exec coordinator-agent python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:26003'); s.send(b'health'); print('CoordinatorAgent:', s.recv().decode()); s.close()" |  | echo "CoordinatorAgent: FAILED" |

| podman exec chain-of-thought-agent python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:5613'); s.send(b'health'); print('ChainOfThoughtAgent:', s.recv().decode()); s.close()" |  | echo "ChainOfThoughtAgent: FAILED" |

# Check system services
echo "System Services Health:"
| podman exec model-manager-agent python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:5571'); s.send(b'health'); print('ModelManagerAgent:', s.recv().decode()); s.close()" |  | echo "ModelManagerAgent: FAILED" |

| podman exec emotion-engine python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:5591'); s.send(b'health'); print('EmotionEngine:', s.recv().decode()); s.close()" |  | echo "EmotionEngine: FAILED" |

| podman exec audio-capture python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:6576'); s.send(b'health'); print('AudioCapture:', s.recv().decode()); s.close()" |  | echo "AudioCapture: FAILED" |

# Check GPU services
echo "GPU Services Health:"
| podman exec got-tot-agent python3 -c "import zmq; ctx = zmq.Context(); s = ctx.socket(zmq.REQ); s.connect('tcp://localhost:7001'); s.send(b'health'); print('GoTToTAgent:', s.recv().decode()); s.close()" |  | echo "GoTToTAgent: FAILED" |

echo "Health check completed!"
```

---

## PHASE 6: TESTING & VALIDATION

### test-containers.sh:
```bash
# !/bin/bash
echo "Running container unit tests..."

# Test core services
echo "Testing core services..."
podman exec system-digital-twin python3 -m pytest main_pc_code/tests/test_system_digital_twin.py -v
podman exec coordinator-agent python3 -m pytest main_pc_code/tests/test_coordinator_agent.py -v
podman exec chain-of-thought-agent python3 -m pytest main_pc_code/tests/test_chain_of_thought_agent.py -v

# Test system services
echo "Testing system services..."
podman exec model-manager-agent python3 -m pytest main_pc_code/tests/test_model_manager_agent.py -v
podman exec emotion-engine python3 -m pytest main_pc_code/tests/test_emotion_engine.py -v
podman exec audio-capture python3 -m pytest main_pc_code/tests/test_audio_capture.py -v

# Test GPU services
echo "Testing GPU services..."
podman exec got-tot-agent python3 -m pytest main_pc_code/tests/test_got_tot_agent.py -v

echo "All unit tests completed!"
```

### test-integration.sh:
```bash
# !/bin/bash
echo "Running integration tests..."

# Test inter-service communication
echo "Testing inter-service communication..."
python3 main_pc_code/tests/test_inter_service_communication.py

# Test end-to-end workflow
echo "Testing end-to-end workflow..."
python3 main_pc_code/tests/test_end_to_end_workflow.py

# Test resource management
echo "Testing resource management..."
python3 main_pc_code/tests/test_resource_management.py

echo "Integration tests completed!"
```

---

## PHASE 7: MONITORING & MAINTENANCE

### docker-compose.monitoring.yml:
```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - ai-system-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
    networks:
      - ai-system-network

volumes:
  grafana-storage:

networks:
  ai-system-network:
    external: true
```

---

## IMPLEMENTATION CHECKLIST

### Pre-Implementation:
- [ ] Verify Podman installation and GPU support
- [ ] Check available system resources
- [ ] Backup current system configuration
- [ ] Test network connectivity between containers

### Phase 1-2:
- [ ] Create base images
- [ ] Set up networks
- [ ] Test base image functionality

### Phase 3-4:
- [ ] Build service containers
- [ ] Test individual containers
- [ ] Verify health checks

### Phase 5-6:
- [ ] Deploy complete system
- [ ] Run integration tests
- [ ] Validate system functionality

### Phase 7-8:
- [ ] Set up monitoring
- [ ] Configure logging
- [ ] Optimize performance

---

## TROUBLESHOOTING GUIDE

### Common Issues:
1. **GPU Access**: Ensure nvidia-container-toolkit is installed
2. **Network Connectivity**: Check firewall rules and network configuration
3. **Resource Limits**: Monitor memory and CPU usage
4. **Model Loading**: Verify model files are accessible in containers

### Debug Commands:
```bash
# Check container status
podman ps -a

# Check container logs
podman logs <container-name>

# Check network connectivity
podman exec <container-name> ping <target-ip>

# Check resource usage
podman stats

# Check GPU access
podman exec <gpu-container> nvidia-smi
```

---

## CONCLUSION

This detailed plan provides a comprehensive approach to containerizing the AI system using Podman. The phase-by-phase implementation ensures a smooth transition while maintaining system functionality and performance. Each phase builds upon the previous one, allowing for incremental testing and validation.

The plan addresses:
- **Dependency Management**: Proper separation of ML and non-ML dependencies
- **Resource Optimization**: Efficient use of GPU and CPU resources
- **Network Architecture**: Secure and scalable communication between services
- **Monitoring & Maintenance**: Comprehensive logging and monitoring setup
- **Testing & Validation**: Thorough testing at each phase

This approach ensures that the containerized system will be robust, scalable, and maintainable while preserving all existing functionality.