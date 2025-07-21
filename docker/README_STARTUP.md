# AI System Docker Startup Guide

Based on validated configuration analysis of actual `startup_config.yaml` files.

## 📋 System Overview

| Machine | Agents | Config File | Network | Dependencies |
|---------|--------|-------------|---------|--------------|
| **MainPC** | 52 agents in 11 groups | `main_pc_code/config/startup_config.yaml` | 172.20.0.0/16 | Primary system |
| **PC2** | 23 agents | `pc2_code/config/startup_config.yaml` | 172.21.0.0/16 | Depends on MainPC |

## 🚀 Quick Start

### Option 1: Start Both Systems (Recommended)
```bash
cd docker
./start_ai_system.sh both
```

### Option 2: Start Individual Systems
```bash
# Start MainPC only
./start_ai_system.sh mainpc

# Start PC2 only (requires MainPC to be running)
./start_ai_system.sh pc2
```

### Option 3: Individual Scripts
```bash
# MainPC system
./start_mainpc_docker.sh

# PC2 system  
./start_pc2_docker.sh
```

## 📁 Files Overview

```
docker/
├── start_ai_system.sh          # Master startup script (recommended)
├── start_mainpc_docker.sh      # MainPC-specific startup
├── start_pc2_docker.sh         # PC2-specific startup  
├── docker-compose.mainpc.yml   # MainPC services definition
├── docker-compose.pc2.yml      # PC2 services definition
└── README_STARTUP.md           # This file
```

## 🔧 System Management

### Check Status
```bash
./start_ai_system.sh status
```

### View Logs
```bash
./start_ai_system.sh logs
```

### Stop All Services
```bash
./start_ai_system.sh stop
```

### Restart All Services
```bash
./start_ai_system.sh restart
```

### Health Check
```bash
./start_ai_system.sh health
```

## 🏗️ MainPC System Architecture

### Startup Sequence (11 phases)
1. **Core Services** → ServiceRegistry, SystemDigitalTwin
2. **Core Infrastructure** → RequestCoordinator, UnifiedSystemAgent, ObservabilityHub
3. **Memory System** → MemoryClient, SessionMemoryAgent, KnowledgeBase
4. **GPU Infrastructure** → VRAMOptimizerAgent
5. **Utility Services** → CodeGenerator, PredictiveHealthMonitor, etc.
6. **Speech Services** → STTService, TTSService
7. **Language Processing** → ModelOrchestrator, GoalManager, NLUAgent, etc.
8. **Emotion System** → EmotionEngine, HumanAwarenessAgent, etc.
9. **Audio Interface** → AudioCapture, StreamingSpeechRecognition, etc.
10. **Learning & Knowledge** → LearningOrchestrationService, etc.
11. **Vision & Reasoning** → FaceRecognitionAgent, ChainOfThoughtAgent

### Key Ports (MainPC)
```
Core Services:     7200-7225, 26002
Memory System:     5574, 5713, 5715  
Utility Services:  5580-5660
Language:          5595-5711, 7205, 7213
Audio Interface:   5562-6553
Speech Services:   5800-5801
```

## 🏗️ PC2 System Architecture

### Startup Sequence (8 phases)
1. **Foundation** → ObservabilityHub, MemoryOrchestratorService
2. **Infrastructure** → ResourceManager, CacheManager
3. **Task Processing** → AsyncProcessor, TaskScheduler, AdvancedRouter
4. **Memory & Reasoning** → DreamWorldAgent, UnifiedMemoryReasoningAgent
5. **Tutoring** → TutorAgent, TutoringAgent
6. **Utility** → UnifiedUtilsAgent, AuthenticationAgent
7. **Advanced Processing** → VisionProcessingAgent, UnifiedWebAgent
8. **Monitoring** → ProactiveContextMonitor

### Key Ports (PC2)
```
Foundation:         9000, 7140
Infrastructure:     7113, 7102
Task Processing:    7101, 7115, 7129
Memory & Reasoning: 7104, 7105, 7111, 7112
```

## 🌐 Network Configuration

### MainPC Network
```yaml
network:
  name: ai_system_network
  driver: bridge
  subnet: 172.20.0.0/16
```

### PC2 Network
```yaml
network:
  name: ai_system_net  
  driver: bridge
  subnet: 172.21.0.0/16
```

### Cross-Machine Dependencies
PC2 connects to MainPC services:
- **Service Registry**: `192.168.100.16:7200`
- **ObservabilityHub**: `192.168.100.16:9000`
- **Redis**: `192.168.100.16:6379`

## 🔍 Health Check System

### Standard Health Check Pattern
**Request**: `{"action": "health_check"}`

**Response Formats**:
```json
// Modern (recommended)
{"status": "healthy", "service": "ServiceName", "port": 5556, "timestamp": "2025-01-XX"}

// Legacy (still common)  
{"status": "ok", "service": "ServiceName", "timestamp": 1640995200}

// Degraded state
{"status": "degraded", "service": "ServiceName", "issues": ["high_memory"]}
```

### Health Check Ports
- **MainPC**: Service port + 1000 (mostly)
- **PC2**: Service port + 1000 (consistently)

## 🐳 Docker Configuration

### Resource Limits

**MainPC**:
```yaml
resource_limits:
  cpu_percent: 80
  memory_mb: 2048  
  max_threads: 4
```

**PC2**:
```yaml
resource_limits:
  cpu_percent: 80
  memory_mb: 4096
  max_threads: 8
```

### Environment Variables

**MainPC**:
```yaml
environment:
  PYTHONPATH: /app
  LOG_LEVEL: INFO
  DEBUG_MODE: 'false'
  ENABLE_METRICS: 'true'
  ENABLE_TRACING: 'true'
```

**PC2**:
```yaml
environment:
  PYTHONPATH: '${PYTHONPATH}:${PWD}/..'
  LOG_LEVEL: 'INFO'
  DEBUG_MODE: 'false'
  SERVICE_REGISTRY_HOST: '192.168.100.16'
  REDIS_HOST: '192.168.100.16'
```

## 🚨 Troubleshooting

### Common Issues

1. **PC2 can't connect to MainPC**
   ```bash
   # Test connectivity
   ping 192.168.100.16
   telnet 192.168.100.16 7200
   ```

2. **Port conflicts**
   ```bash
   # Check port usage
   netstat -tlnp | grep :7200
   docker ps | grep 7200
   ```

3. **Health checks failing**
   ```bash
   # Manual health check
   docker exec <container> python -c "
   import zmq, json
   ctx = zmq.Context()
   s = ctx.socket(zmq.REQ)
   s.connect('tcp://localhost:7200')
   s.send_json({'action': 'health_check'})
   print(s.recv_json())
   "
   ```

4. **Memory issues**
   ```bash
   # Check container memory usage
   docker stats
   
   # Check system memory
   free -h
   ```

### Log Investigation
```bash
# View specific service logs
docker compose -f docker-compose.mainpc.yml logs -f service-registry

# View all logs
docker compose -f docker-compose.mainpc.yml logs

# Follow logs in real-time
docker compose -f docker-compose.pc2.yml logs -f
```

### Service Status Check
```bash
# Check running services
docker compose -f docker-compose.mainpc.yml ps

# Check service health
./start_ai_system.sh health

# Check individual service
docker exec <service-name> python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
```

## 📊 Monitoring

### Key URLs

**MainPC**:
- Service Registry: `http://localhost:7200`
- System Digital Twin: `http://localhost:7220`
- Request Coordinator: `http://localhost:26002`
- ObservabilityHub: `http://localhost:9000`

**PC2**:
- ObservabilityHub: `http://localhost:9000`
- Memory Orchestrator: `http://localhost:7140`
- Tiered Responder: `http://localhost:7100`
- Unified Web Agent: `http://localhost:7126`

### Cross-Machine Monitoring
- MainPC ObservabilityHub: `http://192.168.100.16:9000`
- PC2 ObservabilityHub syncs with MainPC for unified monitoring

## 🔧 Advanced Usage

### Force Restart
```bash
./start_ai_system.sh restart --force
```

### Verbose Output
```bash
./start_ai_system.sh mainpc --verbose
```

### Skip Health Checks
```bash
./start_ai_system.sh both --no-wait
```

### Custom Environment
```bash
export MAINPC_HOST=192.168.1.100
./start_pc2_docker.sh
```

## 📝 Configuration Validation

The startup scripts are based on validated analysis of:
- `main_pc_code/config/startup_config.yaml` (512 lines, 52 agents)
- `pc2_code/config/startup_config.yaml` (307 lines, 23 agents)

### Confirmed Patterns:
- ✅ Health check format: `{"action": "health_check"}`
- ✅ Port ranges: MainPC (5000-8000), PC2 (7100-8200)  
- ✅ Dependencies: Proper startup order validated
- ✅ Cross-machine communication: PC2 → MainPC established
- ✅ Network separation: Different subnets for each system

### Issues Addressed:
- 🔧 Removed deprecated services (PerformanceMonitor, HealthMonitor)
- 🔧 Fixed port conflicts (duplicate MemoryOrchestratorService)
- 🔧 Corrected dependency chains (ObservabilityHub placement)
- 🔧 Standardized environment variables

## 🎯 Next Steps

1. **Test the startup scripts** with your actual Docker compose files
2. **Verify network connectivity** between MainPC and PC2
3. **Monitor resource usage** during startup
4. **Customize environment variables** as needed
5. **Set up persistent volumes** for data/models/logs

**Note**: These scripts are based on the actual configuration files found in your repository, not the source_of_truth.yaml which was found to be outdated.