# PC2 Agent Port Mapping

This document lists exposed host ports for each PC2 agent container defined in `docker-compose.pc2.individual.yml`.

| Agent | Container Port | Host Port |
|-------|----------------|-----------|
| MemoryOrchestratorService | 7140 | 7140 |
| TieredResponder | 7100 | 7100 |
| AsyncProcessor | 7101 | 7101 |
| CacheManager | 7102 | 7102 |
| VisionProcessingAgent | 7150 | 7150 |
| DreamWorldAgent | 7104 | 7104 |
| UnifiedMemoryReasoningAgent | 7105 | 7105 |
| TutorAgent | 7108 | 7108 |
| TutoringAgent | 7131 | 7131 |
| ContextManager | 7111 | 7111 |
| ExperienceTracker | 7112 | 7112 |
| ResourceManager | 7113 | 7113 |
| TaskScheduler | 7115 | 7115 |
| AuthenticationAgent | 7116 | 7116 |
| UnifiedUtilsAgent | 7118 | 7118 |
| ProactiveContextMonitor | 7119 | 7119 |
| AgentTrustScorer | 7122 | 7122 |
| FileSystemAssistantAgent | 7123 | 7123 |
| RemoteConnectorAgent | 7124 | 7124 |
| UnifiedWebAgent | 7126 | 7126 |
| DreamingModeAgent | 7127 | 7127 |
| AdvancedRouter | 7129 | 7129 |
| ObservabilityHub | 9000, 9100 | 9000, 9100 |

All health-check ports (8100-8199) remain internal to the Docker network and are **not** published to the host, preventing accidental collisions.

MainPC’s exposed ports start at 7200+, so this mapping guarantees no overlap.