# PC2 Agent Port Mapping Documentation

## Overview
This document provides a comprehensive mapping of all ports used by PC2 agents to ensure no conflicts with MainPC agents and proper inter-container communication.

## Port Ranges
- **PC2 Agent Service Ports**: 7100-7199
- **PC2 Health Check Ports**: 8100-8199
- **PC2 Monitoring Ports**: 9000-9100
- **MainPC Agent Ports**: 5000-6999 (Reserved - Do not use)

## PC2 Agent Port Assignments

### Integration Layer Agents
| Agent Name | Service Port | Health Port | Container Name |
|------------|--------------|-------------|----------------|
| MemoryOrchestratorService | 7140 | 8140 | pc2-memory-orchestrator |
| TieredResponder | 7100 | 8100 | pc2-tiered-responder |
| AsyncProcessor | 7101 | 8101 | pc2-async-processor |
| CacheManager | 7102 | 8102 | pc2-cache-manager |
| VisionProcessingAgent | 7150 | 8150 | pc2-vision-processor |

### Core Agents
| Agent Name | Service Port | Health Port | Container Name |
|------------|--------------|-------------|----------------|
| DreamWorldAgent | 7104 | 8104 | pc2-dream-world |
| UnifiedMemoryReasoningAgent | 7105 | 8105 | pc2-memory-reasoning |
| TutorAgent | 7108 | 8108 | pc2-tutor-services |
| TutoringAgent | 7131 | 8131 | pc2-tutor-services |
| ContextManager | 7111 | 8111 | pc2-context-manager |
| ExperienceTracker | 7112 | 8112 | pc2-experience-tracker |
| ResourceManager | 7113 | 8113 | pc2-resource-manager |
| TaskScheduler | 7115 | 8115 | pc2-task-scheduler |

### Specialized Services
| Agent Name | Service Port | Health Port | Container Name |
|------------|--------------|-------------|----------------|
| AuthenticationAgent | 7116 | 8116 | pc2-authentication |
| UnifiedUtilsAgent | 7118 | 8118 | pc2-unified-utils |
| ProactiveContextMonitor | 7119 | 8119 | pc2-proactive-monitor |
| AgentTrustScorer | 7122 | 8122 | pc2-trust-scorer |
| FileSystemAssistantAgent | 7123 | 8123 | pc2-filesystem-assistant |
| RemoteConnectorAgent | 7124 | 8124 | pc2-remote-connector |
| UnifiedWebAgent | 7126 | 8126 | pc2-web-agent |
| DreamingModeAgent | 7127 | 8127 | pc2-dreaming-mode |
| AdvancedRouter | 7129 | 8129 | pc2-advanced-router |

### Monitoring & Infrastructure
| Service Name | Service Port | Health Port | Container Name |
|--------------|--------------|-------------|----------------|
| ObservabilityHub | 9000 | 9100 | pc2-observability-hub |
| Redis | 6379 | - | pc2-redis |

## Inter-Container Communication

### Network Architecture
- **pc2_network**: Internal bridge network for PC2 agent communication (172.22.0.0/16)
- **mainpc_bridge**: External network for PC2 ↔ MainPC communication

### Communication Patterns
1. **Internal PC2 Communication**: All agents communicate via container names on pc2_network
2. **Cross-Machine Communication**: 
   - RemoteConnectorAgent (7124) bridges to MainPC
   - ObservabilityHub (9000) syncs with MainPC hub at 192.168.100.16:9000

### Environment Variables for Service Discovery
```yaml
# Example for dependent services
MEMORY_SERVICE_HOST: memory-orchestrator
MEMORY_SERVICE_PORT: 7140

RESOURCE_MANAGER_HOST: resource-manager
RESOURCE_MANAGER_PORT: 7113

OBSERVABILITY_HUB_HOST: observability-hub
OBSERVABILITY_HUB_PORT: 9000
```

## Port Conflict Resolution
1. All PC2 ports are in the 7xxx and 8xxx range
2. MainPC uses 5xxx and 6xxx ranges
3. No overlapping port assignments between systems
4. Error bus port (7150) conflicts with VisionProcessingAgent - needs resolution

## Testing Connectivity
```bash
# Test internal connectivity
docker exec pc2-memory-orchestrator curl http://cache-manager:7102/health

# Test cross-machine connectivity
curl http://192.168.100.17:7124/health  # RemoteConnectorAgent from MainPC
```

## Notes
- All health check ports are 1000 + service port (e.g., 7100 → 8100)
- Exception: ObservabilityHub uses 9000/9100 for Prometheus compatibility
- All services bind to 0.0.0.0 internally but are accessed via container names