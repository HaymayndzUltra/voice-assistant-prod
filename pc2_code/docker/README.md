# PC2 Containerized AI Agent System

## Overview

This directory contains the complete Docker containerization setup for the PC2 (Personal Computer 2) subsystem of the AI Agent system. PC2 serves as the **Cognitive/Memory Hub** and hosts 19 specialized agents across multiple functional areas.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                          PC2 System                            │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1: Integration Layer                                    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │MemoryOrchestrator│ │ TieredResponder │ │ AsyncProcessor  │   │
│  │   Service       │ │                 │ │                 │   │
│  │   Port: 7140    │ │   Port: 7100    │ │   Port: 7101    │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│  ┌─────────────────┐ ┌─────────────────┐                       │
│  │  CacheManager   │ │VisionProcessing │                       │
│  │   Port: 7102    │ │     Agent       │                       │
│  │                 │ │   Port: 7150    │                       │
│  └─────────────────┘ └─────────────────┘                       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2: Core Cognitive Agents                               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ DreamWorldAgent │ │UnifiedMemory    │ │ ContextManager  │   │
│  │   Port: 7104    │ │ReasoningAgent   │ │   Port: 7111    │   │
│  │                 │ │   Port: 7105    │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3: Cross-Machine Communication                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │RemoteConnector  │ │ AdvancedRouter  │ │ObservabilityHub │   │
│  │     Agent       │ │   Port: 7129    │ │   Port: 9000    │   │
│  │   Port: 7124    │ │                 │ │                 │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
           │                                            │
           ▼                                            ▼
┌─────────────────┐                            ┌─────────────────┐
│    MainPC       │◄──── Cross-Machine ──────►│   External      │
│ 192.168.100.16  │     Communication         │   Services      │
│   Port: 26002   │                            │                 │
└─────────────────┘                            └─────────────────┘
```

### Container Architecture

- **4 Specialized Docker Images:**
  - `pc2-base`: Core runtime for most agents
  - `pc2-vision`: Computer vision processing capabilities
  - `pc2-web`: Web scraping and browser automation
  - `pc2-monitoring`: ObservabilityHub with metrics collection

- **19 Agent Containers:** Each agent runs in its own isolated container
- **2 Networks:** Internal (pc2_network) and external communication
- **4 Persistent Volumes:** Logs, data, models, and cache storage

## Quick Start

### Prerequisites

- Docker Engine (>= 20.10)
- Docker Compose (>= 1.29)
- 8GB+ RAM (for all agents)
- Linux environment (Ubuntu 20.04+ recommended)

### Installation

1. **Clone and navigate to project:**
   ```bash
   cd /path/to/AI_System_Monorepo
   ```

2. **Build all images:**
   ```bash
   chmod +x pc2_code/docker/start_pc2_system.sh
   ./pc2_code/docker/start_pc2_system.sh build
   ```

3. **Start the system:**
   ```bash
   ./pc2_code/docker/start_pc2_system.sh start
   ```

4. **Check status:**
   ```bash
   ./pc2_code/docker/start_pc2_system.sh status
   ```

## Detailed Usage

### Management Script

The `start_pc2_system.sh` script provides comprehensive system management:

```bash
# Build all Docker images
./pc2_code/docker/start_pc2_system.sh build

# Start all services (with dependency ordering)
./pc2_code/docker/start_pc2_system.sh start

# Check system status
./pc2_code/docker/start_pc2_system.sh status

# Run health checks
./pc2_code/docker/start_pc2_system.sh health

# Test cross-machine connectivity
./pc2_code/docker/start_pc2_system.sh test

# View logs (all or specific service)
./pc2_code/docker/start_pc2_system.sh logs
./pc2_code/docker/start_pc2_system.sh logs memory-orchestrator-service

# Stop all services
./pc2_code/docker/start_pc2_system.sh stop

# Restart all services
./pc2_code/docker/start_pc2_system.sh restart

# Clean up system
./pc2_code/docker/start_pc2_system.sh clean

# Open monitoring dashboard
./pc2_code/docker/start_pc2_system.sh monitor
```

### Manual Docker Compose

If you prefer direct Docker Compose commands:

```bash
# Start all services
docker-compose -f pc2_code/docker-compose.pc2.yml up -d

# Start specific service
docker-compose -f pc2_code/docker-compose.pc2.yml up -d memory-orchestrator-service

# View logs
docker-compose -f pc2_code/docker-compose.pc2.yml logs -f

# Stop all services
docker-compose -f pc2_code/docker-compose.pc2.yml down

# Scale a service (if needed)
docker-compose -f pc2_code/docker-compose.pc2.yml up -d --scale tiered-responder=2
```

## Port Configuration

### Port Ranges
- **7100-7199:** Agent communication ports
- **8100-8199:** Health check ports
- **9000-9100:** Monitoring and metrics

### Key Endpoints
- **TieredResponder:** `http://localhost:7100` (Main response handler)
- **MemoryOrchestratorService:** `http://localhost:7140` (Core memory)
- **AdvancedRouter:** `http://localhost:7129` (Request routing)
- **ObservabilityHub:** `http://localhost:9000` (Monitoring dashboard)
- **RemoteConnectorAgent:** `http://localhost:7124` (Cross-machine bridge)

See [PC2_PORT_MAPPING.md](./PC2_PORT_MAPPING.md) for complete port documentation.

## Cross-Machine Communication

### PC2 → MainPC
```bash
# MainPC endpoints that PC2 connects to
MainPC RequestCoordinator: http://192.168.100.16:26002
MainPC ObservabilityHub: http://192.168.100.16:9000
```

### MainPC → PC2
```bash
# PC2 endpoints accessible from MainPC
PC2 TieredResponder: http://<PC2_IP>:7100
PC2 AdvancedRouter: http://<PC2_IP>:7129
PC2 ObservabilityHub: http://<PC2_IP>:9000
```

### Environment Variables
```bash
# Set these before starting the system
export PC2_IP="192.168.100.17"    # Your PC2 IP address
export MAINPC_IP="192.168.100.16" # MainPC IP address
```

## Agent Dependencies

The system starts agents in dependency order:

1. **Infrastructure:** ObservabilityHub
2. **Core Services:** MemoryOrchestratorService, ResourceManager
3. **Integration Layer:** TieredResponder, AsyncProcessor, CacheManager
4. **Core Agents:** Memory, context, and cognitive agents
5. **Specialized Services:** Web, vision, and utility agents

### Dependency Graph
```
ObservabilityHub (no deps)
├── ResourceManager
│   ├── TieredResponder
│   └── AsyncProcessor
│       └── TaskScheduler
│           └── AdvancedRouter
│               └── RemoteConnectorAgent
└── UnifiedUtilsAgent
    ├── AuthenticationAgent
    └── FileSystemAssistantAgent

MemoryOrchestratorService (no deps)
├── CacheManager
│   └── VisionProcessingAgent
├── DreamWorldAgent
│   └── DreamingModeAgent
├── UnifiedMemoryReasoningAgent
├── TutorAgent
├── TutoringAgent
├── ContextManager
│   └── ProactiveContextMonitor
├── ExperienceTracker
└── UnifiedWebAgent
```

## Monitoring and Health Checks

### Health Check System
- Each agent exposes health endpoint at `:{health_port}/health`
- Automated health checks every 30 seconds
- 3 retry attempts with 10-second timeout
- Startup grace period: 60-300 seconds (depending on agent)

### Prometheus Metrics
Access metrics at `http://localhost:9000/metrics`:
- Agent uptime and health status
- Resource utilization (CPU, memory, disk)
- Cross-machine communication latency
- Request/response patterns and error rates

### Log Aggregation
- All logs stored in persistent `pc2_logs` volume
- Structured JSON logging with correlation IDs
- Access logs: `docker-compose logs [service-name]`

## Resource Management

### Resource Limits
Each agent has defined resource limits:

| Agent Type | CPU Limit | Memory Limit | Typical Usage |
|------------|-----------|--------------|---------------|
| Core Memory | 2.0 cores | 4-6GB | MemoryOrchestratorService, UnifiedMemoryReasoningAgent |
| Processing | 1.5 cores | 3GB | TieredResponder, VisionProcessingAgent |
| Standard | 1.0 cores | 2GB | Most agents |
| Lightweight | 0.5 cores | 1GB | Utility and monitoring agents |

### Storage Volumes
- **pc2_logs:** Agent logs and system logs
- **pc2_data:** Persistent data (databases, caches)
- **pc2_models:** ML model files and embeddings
- **pc2_cache:** Temporary cache and session data

## Security

### Container Security
- All containers run as non-root user (`pc2user`)
- Read-only filesystem where possible
- Resource limits prevent resource exhaustion
- Network segmentation between internal and external traffic

### Network Security
- Internal communication via encrypted Docker networks
- External ports only exposed where necessary
- Firewall rules for cross-machine communication
- Health checks validate proper authentication

### Data Security
- Persistent volumes with proper permissions
- Secrets management via environment variables
- No sensitive data in container images
- Audit logging for all cross-machine communication

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check for port conflicts
netstat -tulpn | grep :7[0-9][0-9][0-9]

# Solution: Stop conflicting services or change PC2 ports
```

#### 2. Memory Issues
```bash
# Check container memory usage
docker stats

# Solution: Increase system RAM or reduce agent limits
```

#### 3. Cross-Machine Connectivity
```bash
# Test MainPC connectivity
curl -f http://192.168.100.16:26002/health

# Check firewall rules
sudo ufw status

# Solution: Configure firewall rules or check network routing
```

#### 4. Agent Startup Failures
```bash
# Check specific agent logs
docker-compose -f pc2_code/docker-compose.pc2.yml logs memory-orchestrator-service

# Check dependencies
./pc2_code/docker/start_pc2_system.sh health

# Solution: Start dependencies first or check configuration
```

#### 5. Health Check Failures
```bash
# Manual health check
docker exec pc2-tiered-responder curl -f http://localhost:8100/health

# Check agent status
docker-compose -f pc2_code/docker-compose.pc2.yml ps

# Solution: Restart failing agents or check configuration
```

### Debug Mode

Enable debug mode for detailed logging:
```bash
# Set debug environment variables
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG

# Restart with debug mode
./pc2_code/docker/start_pc2_system.sh restart
```

### Performance Monitoring

Monitor system performance:
```bash
# Container resource usage
docker stats

# Disk usage
docker system df

# Network monitoring
docker network ls
```

## Development

### Custom Configuration

1. **Modify agent settings:**
   ```bash
   # Edit startup configuration
   vim pc2_code/config/startup_config.yaml
   
   # Rebuild and restart
   ./pc2_code/docker/start_pc2_system.sh build
   ./pc2_code/docker/start_pc2_system.sh restart
   ```

2. **Add new agents:**
   ```bash
   # Add to startup_config.yaml
   # Add to docker-compose.pc2.yml
   # Update port mapping documentation
   ```

3. **Custom Docker images:**
   ```bash
   # Create new Dockerfile in pc2_code/docker/
   # Update build_images.sh
   # Reference in docker-compose.pc2.yml
   ```

### Testing

Run comprehensive tests:
```bash
# System integration test
./pc2_code/docker/start_pc2_system.sh test

# Individual agent testing
docker exec pc2-memory-orchestrator-service python -m pytest tests/

# Load testing
# Use tools like curl or Apache Bench against agent endpoints
```

## Support

### Documentation
- [Port Mapping](./PC2_PORT_MAPPING.md): Complete port configuration
- [Startup Configuration](../config/startup_config.yaml): Agent definitions
- [SOT Documentation](../../DOCUMENTS_SOT/DOCUMENTS_AGENTS_PC2): Agent specifications

### Getting Help
1. Check logs: `./pc2_code/docker/start_pc2_system.sh logs`
2. Run health check: `./pc2_code/docker/start_pc2_system.sh health`
3. Test connectivity: `./pc2_code/docker/start_pc2_system.sh test`
4. Review troubleshooting section above

### Performance Optimization
- Adjust resource limits based on actual usage
- Use persistent volumes for frequently accessed data
- Configure caching strategies for memory-intensive agents
- Monitor cross-machine latency and optimize network configuration

---

**Built for:** PC2 Cognitive/Memory Hub  
**Containerization:** Docker + Docker Compose  
**Cross-Machine:** PC2 ↔ MainPC Communication  
**Monitoring:** ObservabilityHub + Prometheus  
**Security:** Non-root containers + Network segmentation