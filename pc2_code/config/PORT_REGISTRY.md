# PC2 Port Registry

This file is the single source of truth for all network port assignments on PC2.
Do not assign a port without documenting it here first.

## Port Assignment Rules
- ZMQ ports use the 71xx range (7100-7199)
- Health check ports use the 81xx range (8100-8199)
- Each agent must have unique port numbers
- Do not change ports for confirmed working services without proper testing

## Port Registry Table

| # | Agent Name                  | ZMQ Port | Health Check Port | Notes                               |
|---|-----------------------------|----------|-------------------|-------------------------------------|
| 1 | TieredResponder             | 7100     | 8100              | Integration Layer Agent             |
| 2 | AsyncProcessor              | 7101     | 8101              | Integration Layer Agent             |
| 3 | CacheManager                | 7102     | 8102              | Integration Layer Agent             |
| 4 | PerformanceMonitor          | 7103     | 8103              | Integration Layer Agent             |
| 5 | DreamWorldAgent             | 7104     | 8104              | PC2-Specific Core Agent             |
| 6 | UnifiedMemoryReasoningAgent | 7105     | 8105              | PC2-Specific Core Agent             |
| 7 | EpisodicMemoryAgent         | 7106     | 8106              | PC2-Specific Core Agent             |
| 8 | LearningAgent               | 7107     | 8107              | PC2-Specific Core Agent             |
| 9 | TutoringAgent               | 7108     | 8108              | PC2-Specific Core Agent             |
| 10| KnowledgeBaseAgent          | 7109     | 8109              | PC2-Specific Core Agent             |
| 11| MemoryManager               | 7110     | 8110              | PC2-Specific Core Agent             |
| 12| ContextManager              | 7111     | 8111              | PC2-Specific Core Agent             |
| 13| ExperienceTracker           | 7112     | 8112              | PC2-Specific Core Agent             |
| 14| ResourceManager             | 7113     | 8113              | PC2-Specific Core Agent             |
| 15| HealthMonitor               | 7114     | 8114              | PC2-Specific Core Agent             |
| 16| TaskScheduler               | 7115     | 8115              | PC2-Specific Core Agent             |
| 17| AuthenticationAgent         | 7116     | 8116              | ForPC2 Agent                        |
| 18| UnifiedErrorAgent           | 7117     | 8117              | ForPC2 Agent                        |
| 19| UnifiedUtilsAgent           | 7118     | 8118              | ForPC2 Agent                        |
| 20| ProactiveContextMonitor     | 7119     | 8119              | ForPC2 Agent                        |
| 21| SystemDigitalTwin           | 7120     | 8100              | Moved to MainPC. This is the system's central hub. |
| 22| RCAAgent                    | 7121     | 8121              | ForPC2 Agent                        |
| 23| AgentTrustScorer            | 7122     | 8122              | Additional PC2 Core Agent           |
| 24| FileSystemAssistantAgent    | 7123     | 8123              | Additional PC2 Core Agent           |
| 25| RemoteConnectorAgent        | 7124     | 8124              | Additional PC2 Core Agent           |
| 26| SelfHealingAgent            | 7125     | 8125              | Additional PC2 Core Agent           |
| 27| UnifiedWebAgent             | 7126     | 8126              | Additional PC2 Core Agent           |
| 28| DreamingModeAgent           | 7127     | 8127              | Additional PC2 Core Agent           |
| 29| PerformanceLoggerAgent      | 7128     | 8128              | Additional PC2 Core Agent           |
| 30| AdvancedRouter              | 7129     | 8129              | Additional PC2 Core Agent           |

## Change History
- Initial registry creation: All agents assigned unique ZMQ and health check ports
- SystemDigitalTwin confirmed working on port 7120, marked as stable 
- SystemDigitalTwin moved to MainPC, remains on port 7120 with health check port 8100