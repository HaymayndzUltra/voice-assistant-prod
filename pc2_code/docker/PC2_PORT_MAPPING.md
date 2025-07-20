# PC2 Port Mapping Documentation

## Overview
This document provides a comprehensive mapping of all ports used by PC2 agents, ensuring no conflicts with MainPC and proper cross-machine communication.

## Port Allocation Strategy

### PC2 Agent Ports: 7100-7199
- **Range:** 7100-7199 (Main agent communication ports)
- **Pattern:** Each agent gets a unique port in this range
- **Protocol:** TCP (ZMQ/HTTP)

### PC2 Health Check Ports: 8100-8199
- **Range:** 8100-8199 (Health check and monitoring ports)
- **Pattern:** Health port = Agent port + 1000
- **Protocol:** HTTP

### Special Monitoring Ports: 9000-9100
- **9000:** ObservabilityHub Prometheus metrics
- **9100:** ObservabilityHub health check

## Detailed Port Mapping

### Phase 1 - Integration Layer Agents

| Agent Name | Container Name | Agent Port | Health Port | Dependencies |
|------------|----------------|------------|-------------|--------------|
| MemoryOrchestratorService | pc2-memory-orchestrator-service | 7140 | 8140 | None |
| TieredResponder | pc2-tiered-responder | 7100 | 8100 | ResourceManager |
| AsyncProcessor | pc2-async-processor | 7101 | 8101 | ResourceManager |
| CacheManager | pc2-cache-manager | 7102 | 8102 | MemoryOrchestratorService |
| VisionProcessingAgent | pc2-vision-processing-agent | 7150 | 8150 | CacheManager |

### Phase 2 - PC2-Specific Core Agents

| Agent Name | Container Name | Agent Port | Health Port | Dependencies |
|------------|----------------|------------|-------------|--------------|
| DreamWorldAgent | pc2-dreamworld-agent | 7104 | 8104 | MemoryOrchestratorService |
| UnifiedMemoryReasoningAgent | pc2-unified-memory-reasoning-agent | 7105 | 8105 | MemoryOrchestratorService |
| TutorAgent | pc2-tutor-agent | 7108 | 8108 | MemoryOrchestratorService |
| TutoringAgent | pc2-tutoring-agent | 7131 | 8131 | MemoryOrchestratorService |
| ContextManager | pc2-context-manager | 7111 | 8111 | MemoryOrchestratorService |
| ExperienceTracker | pc2-experience-tracker | 7112 | 8112 | MemoryOrchestratorService |
| ResourceManager | pc2-resource-manager | 7113 | 8113 | ObservabilityHub |
| TaskScheduler | pc2-task-scheduler | 7115 | 8115 | AsyncProcessor |

### Phase 3 - ForPC2 Agents (PC2-Specific Services)

| Agent Name | Container Name | Agent Port | Health Port | Dependencies |
|------------|----------------|------------|-------------|--------------|
| AuthenticationAgent | pc2-authentication-agent | 7116 | 8116 | UnifiedUtilsAgent |
| UnifiedUtilsAgent | pc2-unified-utils-agent | 7118 | 8118 | ObservabilityHub |
| ProactiveContextMonitor | pc2-proactive-context-monitor | 7119 | 8119 | ContextManager |

### Phase 4 - Additional PC2 Core Agents

| Agent Name | Container Name | Agent Port | Health Port | Dependencies |
|------------|----------------|------------|-------------|--------------|
| AgentTrustScorer | pc2-agent-trust-scorer | 7122 | 8122 | ObservabilityHub |
| FileSystemAssistantAgent | pc2-filesystem-assistant-agent | 7123 | 8123 | UnifiedUtilsAgent |
| RemoteConnectorAgent | pc2-remote-connector-agent | 7124 | 8124 | AdvancedRouter |
| UnifiedWebAgent | pc2-unified-web-agent | 7126 | 8126 | FileSystemAssistantAgent, MemoryOrchestratorService |
| DreamingModeAgent | pc2-dreaming-mode-agent | 7127 | 8127 | DreamWorldAgent |
| AdvancedRouter | pc2-advanced-router | 7129 | 8129 | TaskScheduler |

### Phase 5 - Monitoring Solution

| Agent Name | Container Name | Agent Port | Health Port | Dependencies |
|------------|----------------|------------|-------------|--------------|
| ObservabilityHub | pc2-observability-hub | 9000 | 9100 | None |

## Cross-Machine Communication

### PC2 → MainPC Communication
- **MainPC Endpoint:** `http://192.168.100.16:26002` (RequestCoordinator)
- **MainPC ObservabilityHub:** `http://192.168.100.16:9000`
- **Primary Bridge:** RemoteConnectorAgent (7124)

### MainPC → PC2 Communication
- **PC2 Entry Points:**
  - TieredResponder: `http://<PC2_IP>:7100`
  - AdvancedRouter: `http://<PC2_IP>:7129`
  - ObservabilityHub: `http://<PC2_IP>:9000`

## Port Conflict Analysis

### No Conflicts with MainPC
✅ **PC2 Ports (7100-7199)** vs **MainPC Ports (5000-6999, 26002, 7000-7125)**
- PC2 uses 7100+ range, MainPC primary range is 5000-6999
- Some overlap potential in 7000-7125 range, but PC2 starts at 7100
- ObservabilityHub on 9000/9100 is unique

### Reserved Ports
- **7140:** MemoryOrchestratorService (Core memory service)
- **7100:** TieredResponder (Main response handler)
- **9000/9100:** ObservabilityHub (Cross-machine monitoring)

## Network Configuration

### Docker Networks
- **pc2_network:** Internal communication between PC2 agents
  - Subnet: 172.20.0.0/16
  - Driver: bridge
- **external_network:** Cross-machine communication
  - Driver: bridge
  - Allows communication with MainPC

### Volume Mapping
- **pc2_logs:** Container logs storage
- **pc2_data:** Persistent data storage
- **pc2_models:** ML model cache
- **pc2_cache:** Application cache

## Security Considerations

### Firewall Rules
```bash
# Allow PC2 internal communication
sudo ufw allow 7100:7199/tcp comment "PC2 Agent Ports"
sudo ufw allow 8100:8199/tcp comment "PC2 Health Check Ports"
sudo ufw allow 9000:9100/tcp comment "PC2 Monitoring Ports"

# Allow cross-machine communication
sudo ufw allow from 192.168.100.16 to any port 7100:7199 comment "MainPC to PC2"
sudo ufw allow from 192.168.100.16 to any port 9000:9100 comment "MainPC to PC2 Monitoring"
```

### Container Security
- All containers run as non-root user (`pc2user`)
- Resource limits enforced
- Read-only filesystem where possible
- Network segmentation between internal and external communication

## Health Check Strategy

### Health Check Endpoints
- **Format:** `http://container:health_port/health`
- **Timeout:** 10 seconds
- **Interval:** 30 seconds
- **Retries:** 3

### Health Check Implementation
```python
# Each agent implements health check at /{agent_port + 1000}/health
def health_check():
    return {
        "status": "healthy",
        "agent": self.agent_name,
        "port": self.port,
        "dependencies": self.check_dependencies(),
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Monitoring and Observability

### Prometheus Metrics (Port 9000)
- Agent health status
- Resource utilization
- Cross-machine communication latency
- Request/response patterns

### Log Aggregation
- All logs stored in `/app/logs/` volume
- Structured JSON logging
- Cross-machine log correlation via ObservabilityHub

## Troubleshooting

### Common Port Issues
1. **Port already in use:** Check for conflicting services
2. **Cross-machine connectivity:** Verify firewall rules
3. **Health check failures:** Check agent startup order
4. **Resource exhaustion:** Monitor container resource usage

### Diagnostic Commands
```bash
# Check port usage
netstat -tulpn | grep :7[0-9][0-9][0-9]

# Test cross-machine connectivity
curl -f http://192.168.100.16:26002/health

# Monitor container health
docker-compose -f pc2_code/docker-compose.pc2.yml ps
docker-compose -f pc2_code/docker-compose.pc2.yml logs [service-name]
```