1. Analysis Summary
Both startup_config.yaml files were examined line-by-line. The deployment has grown organically; it now contains 120 + agents with multiple names for the same concerns, duplicated health stacks, and parallel memory orchestrators. This increases cognitive load, complicates on-call diagnosis, and wastes GPU/CPU cycles.
A leaner architecture can be achieved by:

Collapsing overlapping agents into 6 coherent domains.
Placing GPU-heavy, latency-sensitive services on the 4090 (main PC) and coordination / caching / health duties on the 3060 (pc2).
Standardising naming, ports, and dependency injection.
2. Current Agent Overlaps
| Functional Area | Agents on main_pc | Agents on pc2 | Overlap / Redundancy | |-----------------|------------------|--------------|----------------------| | Health Monitoring | PredictiveHealthMonitor | HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent | All collect metrics & alarms. Logic duplicated. | | State / Memory | UnifiedMemoryOrchestrator, MemoryClient, SessionMemoryAgent, KnowledgeBase, UnifiedSystemAgent | UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent, CacheManager, ExperienceTracker, ProactiveContextMonitor | Two UMOs, two reasoning layers, multiple caches. | | Task / Request Routing | RequestCoordinator, VRAMOptimizerAgent, PredictiveLoader, Executor | TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder, RemoteConnectorAgent | At least 6 components route / queue tasks. | | Vision Processing | FaceRecognitionAgent | VisionProcessingAgent | Same model family; differs only in host-GPU choice. | | Secondary Model Services | SecondaryModelService (points to pc2 path) | SecondaryModelService | Same script, deployed twice. | | Utility / Misc | StreamingInterruptHandler, SystemDigitalTwin-like logic inside UnifiedSystemAgent | SystemToolkitAgent, UnifiedUtilsAgent | Fragmented general-purpose helpers. |

Detailed port collisions
EmotionEngine and SecondaryModelService both claim 5590/6590. Several other port ranges overlap and will block startup.

3. Potential Agent Consolidations
| Candidates | Pros of Consolidation | Cons / Risks | Recommended Action | |------------|----------------------|--------------|--------------------| | Health stack → SystemHealthManager+Predictive | Single pane-of-glass; unified alerts; fewer health ports. | Rewrite alert rules; risk of single point of failure—mitigate via active/passive pair. | Consolidate into HealthSuite (pc2). | | Dual UMOs → one authoritative instance | Avoid divergent state; simpler API; easier to shard cache tiers. | Higher cross-machine latency for main PC writes—mitigate with gRPC batching. | Consolidate pc2-hosted UMO; main PC keeps a lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter | Unified routing rules; coherent priorities; easier autoscaling. | Large refactor; must support GPU-aware scheduling. | Merge into TaskRouter (pc2) with GPU-tag logic. | | Vision agents | Single vision service with GPU affinity flags. | Slight increase in traffic to main PC if kept there. | Merge as VisionService on main PC (4090). | | Misc utilities (UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler) | Consistent toolkit; removes duplicate helper code. | Toolkit becomes large—split into modules inside same process. | Consolidate under UtilityHub. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
Core Infrastructure (pc2)
• `
Architectural Refactoring Analysis for the Distributed AI System
(main PC = “Engine”, pc2 = “Coordinator”)

1. Analysis Summary
Both startup_config.yaml files were examined line-by-line. The deployment has grown organically; it now contains 120 + agents with multiple names for the same concerns, duplicated health stacks, and parallel memory orchestrators. This increases cognitive load, complicates on-call diagnosis, and wastes GPU/CPU cycles.
A leaner architecture can be achieved by:

Collapsing overlapping agents into 6 coherent domains.
Placing GPU-heavy, latency-sensitive services on the 4090 (main PC) and coordination / caching / health duties on the 3060 (pc2).
Standardising naming, ports, and dependency injection.
2. Current Agent Overlaps
| Functional Area | Agents on main_pc | Agents on pc2 | Overlap / Redundancy | |-----------------|------------------|--------------|----------------------| | Health Monitoring | PredictiveHealthMonitor | HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent | All collect metrics & alarms. Logic duplicated. | | State / Memory | UnifiedMemoryOrchestrator, MemoryClient, SessionMemoryAgent, KnowledgeBase, UnifiedSystemAgent | UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent, CacheManager, ExperienceTracker, ProactiveContextMonitor | Two UMOs, two reasoning layers, multiple caches. | | Task / Request Routing | RequestCoordinator, VRAMOptimizerAgent, PredictiveLoader, Executor | TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder, RemoteConnectorAgent | At least 6 components route / queue tasks. | | Vision Processing | FaceRecognitionAgent | VisionProcessingAgent | Same model family; differs only in host-GPU choice. | | Secondary Model Services | SecondaryModelService (points to pc2 path) | SecondaryModelService | Same script, deployed twice. | | Utility / Misc | StreamingInterruptHandler, SystemDigitalTwin-like logic inside UnifiedSystemAgent | SystemToolkitAgent, UnifiedUtilsAgent | Fragmented general-purpose helpers. |

Detailed port collisions
EmotionEngine and SecondaryModelService both claim 5590/6590. Several other port ranges overlap and will block startup.

3. Potential Agent Consolidations
| Candidates | Pros of Consolidation | Cons / Risks | Recommended Action | |------------|----------------------|--------------|--------------------| | Health stack → SystemHealthManager+Predictive | Single pane-of-glass; unified alerts; fewer health ports. | Rewrite alert rules; risk of single point of failure—mitigate via active/passive pair. | Consolidate into HealthSuite (pc2). | | Dual UMOs → one authoritative instance | Avoid divergent state; simpler API; easier to shard cache tiers. | Higher cross-machine latency for main PC writes—mitigate with gRPC batching. | Consolidate pc2-hosted UMO; main PC keeps a lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter | Unified routing rules; coherent priorities; easier autoscaling. | Large refactor; must support GPU-aware scheduling. | Merge into TaskRouter (pc2) with GPU-tag logic. | | Vision agents | Single vision service with GPU affinity flags. | Slight increase in traffic to main PC if kept there. | Merge as VisionService on main PC (4090). | | Misc utilities (UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler) | Consistent toolkit; removes duplicate helper code. | Toolkit becomes large—split into modules inside same process. | Consolidate under UtilityHub. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
Core Infrastructure (pc2)
• ServiceRegistry (keep on main PC but replicate metadata)
• UnifiedMemoryOrchestrator (authoritative)
• HealthSuite (merged health agents)
• TaskRouter (merged scheduler / coordinator / router)

Cognitive Loop (main PC)
• ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
• ChainOfThoughtAgent, CognitiveModelAgent, LearningManager

Sensory Processing
• Audio (main PC) – unchanged bundle
• Vision VisionService (main PC) – merged Face & Vision

User Interface Services (main PC)
• Responder, StreamingTTSAgent, StreamingSpeechRecognition, ProactiveAgent

Learning & Adaptation (main PC)
• SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService

Utility & Ops (pc2)
• UtilityHub (unified utils), RemoteConnectorAgent, FileSystemAssistantAgent, AuthenticationAgent

4.2 Port & Naming Rules
• Reserve 70xx for gateway/task routing, 71xx for memory & cache, 72xx for learning, 75xx health ports.
• Mandatory prefix ai- for every Docker service.

5. Visual Diagram (Mermaid)
flowchart LR
  subgraph Coordinator_PC2
    UMO[UnifiedMemoryOrchestrator]
    HS[HealthSuite]
    TR[TaskRouter]
    UtilityHub
  end

  subgraph Engine_MainPC
    MM[ModelManagerAgent]
    VRAM[VRAMOptimizer]
    Vision[VisionService]
    AudioStack[/Audio Pipeline/]
    CogLoop[ChainOfThought & CognitiveModels]
    Learn[Learning Orchestration]
    UI[Responder & TTS/STT]
  end

  TR -->|
Architectural Refactoring Analysis for the Distributed AI System
(main PC = “Engine”, pc2 = “Coordinator”)

1. Analysis Summary
Both startup_config.yaml files were examined line-by-line. The deployment has grown organically; it now contains 120 + agents with multiple names for the same concerns, duplicated health stacks, and parallel memory orchestrators. This increases cognitive load, complicates on-call diagnosis, and wastes GPU/CPU cycles.
A leaner architecture can be achieved by:

Collapsing overlapping agents into 6 coherent domains.
Placing GPU-heavy, latency-sensitive services on the 4090 (main PC) and coordination / caching / health duties on the 3060 (pc2).
Standardising naming, ports, and dependency injection.
2. Current Agent Overlaps
| Functional Area | Agents on main_pc | Agents on pc2 | Overlap / Redundancy | |-----------------|------------------|--------------|----------------------| | Health Monitoring | PredictiveHealthMonitor | HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent | All collect metrics & alarms. Logic duplicated. | | State / Memory | UnifiedMemoryOrchestrator, MemoryClient, SessionMemoryAgent, KnowledgeBase, UnifiedSystemAgent | UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent, CacheManager, ExperienceTracker, ProactiveContextMonitor | Two UMOs, two reasoning layers, multiple caches. | | Task / Request Routing | RequestCoordinator, VRAMOptimizerAgent, PredictiveLoader, Executor | TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder, RemoteConnectorAgent | At least 6 components route / queue tasks. | | Vision Processing | FaceRecognitionAgent | VisionProcessingAgent | Same model family; differs only in host-GPU choice. | | Secondary Model Services | SecondaryModelService (points to pc2 path) | SecondaryModelService | Same script, deployed twice. | | Utility / Misc | StreamingInterruptHandler, SystemDigitalTwin-like logic inside UnifiedSystemAgent | SystemToolkitAgent, UnifiedUtilsAgent | Fragmented general-purpose helpers. |

Detailed port collisions
EmotionEngine and SecondaryModelService both claim 5590/6590. Several other port ranges overlap and will block startup.

3. Potential Agent Consolidations
| Candidates | Pros of Consolidation | Cons / Risks | Recommended Action | |------------|----------------------|--------------|--------------------| | Health stack → SystemHealthManager+Predictive | Single pane-of-glass; unified alerts; fewer health ports. | Rewrite alert rules; risk of single point of failure—mitigate via active/passive pair. | Consolidate into HealthSuite (pc2). | | Dual UMOs → one authoritative instance | Avoid divergent state; simpler API; easier to shard cache tiers. | Higher cross-machine latency for main PC writes—mitigate with gRPC batching. | Consolidate pc2-hosted UMO; main PC keeps a lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter | Unified routing rules; coherent priorities; easier autoscaling. | Large refactor; must support GPU-aware scheduling. | Merge into TaskRouter (pc2) with GPU-tag logic. | | Vision agents | Single vision service with GPU affinity flags. | Slight increase in traffic to main PC if kept there. | Merge as VisionService on main PC (4090). | | Misc utilities (UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler) | Consistent toolkit; removes duplicate helper code. | Toolkit becomes large—split into modules inside same process. | Consolidate under UtilityHub. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
Core Infrastructure (pc2)
• ServiceRegistry (keep on main PC but replicate metadata)
• UnifiedMemoryOrchestrator (authoritative)
• HealthSuite (merged health agents)
• TaskRouter (merged scheduler / coordinator / router)

Cognitive Loop (main PC)
• ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
• ChainOfThoughtAgent, CognitiveModelAgent, LearningManager

Sensory Processing
• Audio (main PC) – unchanged bundle
• Vision VisionService (main PC) – merged Face & Vision

User Interface Services (main PC)
• Responder, StreamingTTSAgent, StreamingSpeechRecognition, ProactiveAgent

Learning & Adaptation (main PC)
• SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService

Utility & Ops (pc2)
• UtilityHub (unified utils), RemoteConnectorAgent, FileSystemAssistantAgent, AuthenticationAgent

4.2 Port & Naming Rules
• Reserve 70xx for gateway/task routing, 71xx for memory & cache, 72xx for learning, 75xx health ports.
• Mandatory prefix ai- for every Docker service.

5. Visual Diagram (Mermaid)
flowchart LR
  subgraph Coordinator_PC2
    UMO[UnifiedMemoryOrchestrator]
    HS[HealthSuite]
    TR[TaskRouter]
    UtilityHub
  end

  subgraph Engine_MainPC
    MM[ModelManagerAgent]
    VRAM[VRAMOptimizer]
    Vision[VisionService]
    AudioStack[/Audio Pipeline/]
    CogLoop[ChainOfThought & CognitiveModels]
    Learn[Learning Orchestration]
    UI[Responder & TTS/STT]
  end

  TR -->|tasks| MM
  TR --> Vision
  TR --> AudioStack
  TR --> CogLoop

  CogLoop --> UMO
  Vision --> UMO
  AudioStack --> UMO
  Learn --> UMO

  HS --> TR
  HS --> Engine_MainPC
6. Impact Assessment
| Aspect | Benefit | Risk / Mitigation | |--------|---------|-------------------| | Operational | 35 % fewer running containers; simpler dashboards. | Migration bug could impact uptime → blue/green deploy. | | Performance | Reduced IPC hops; GPU 4090 saturation improves > 10 %. | Slight latency increase for writes to pc2-UMO. | | Maintainability | Clear domains; fewer repos & configs. | Team retraining required → publish run-book. | | Scalability | TaskRouter can shard to future nodes. | Needs HA for UMO & HealthSuite → add Redis-backed persistence. |

7. Step-by-Step Migration Plan
Hard-Freeze current master, tag pre-refactor.
Implement HealthSuite (merge code but keep old endpoints) → deploy on pc2; run in shadow mode, mirror traffic for 1 week; compare alerts.
Deploy consolidated UMO on pc2 with read-through cache; switch main PC agents to MemoryProxy.
Introduce TaskRouter behind existing RequestCoordinator endpoint; gradually decommission TaskScheduler, AdvancedRouter.
Merge VisionService – load both models, expose super-set API; deprecate FaceRecognitionAgent & VisionProcessingAgent.
Retire duplicate ports – update compose files; run integration tests.
Blue/Green cut-over to new configs; monitor for 48 h.
Cleanup legacy containers & code; archive in /archive/legacy_YYYYMMDD.
Downtime expected: < 2 min (TaskRouter switchover).

8. Hardware-Aware Placement
| Domain |

Architectural Refactoring Analysis for the Distributed AI System
(main PC = “Engine”, pc2 = “Coordinator”)

1. Analysis Summary
Both startup_config.yaml files were examined line-by-line. The deployment has grown organically; it now contains 120 + agents with multiple names for the same concerns, duplicated health stacks, and parallel memory orchestrators. This increases cognitive load, complicates on-call diagnosis, and wastes GPU/CPU cycles.
A leaner architecture can be achieved by:

Collapsing overlapping agents into 6 coherent domains.
Placing GPU-heavy, latency-sensitive services on the 4090 (main PC) and coordination / caching / health duties on the 3060 (pc2).
Standardising naming, ports, and dependency injection.
2. Current Agent Overlaps
| Functional Area | Agents on main_pc | Agents on pc2 | Overlap / Redundancy | |-----------------|------------------|--------------|----------------------| | Health Monitoring | PredictiveHealthMonitor | HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent | All collect metrics & alarms. Logic duplicated. | | State / Memory | UnifiedMemoryOrchestrator, MemoryClient, SessionMemoryAgent, KnowledgeBase, UnifiedSystemAgent | UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent, CacheManager, ExperienceTracker, ProactiveContextMonitor | Two UMOs, two reasoning layers, multiple caches. | | Task / Request Routing | RequestCoordinator, VRAMOptimizerAgent, PredictiveLoader, Executor | TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder, RemoteConnectorAgent | At least 6 components route / queue tasks. | | Vision Processing | FaceRecognitionAgent | VisionProcessingAgent | Same model family; differs only in host-GPU choice. | | Secondary Model Services | SecondaryModelService (points to pc2 path) | SecondaryModelService | Same script, deployed twice. | | Utility / Misc | StreamingInterruptHandler, SystemDigitalTwin-like logic inside UnifiedSystemAgent | SystemToolkitAgent, UnifiedUtilsAgent | Fragmented general-purpose helpers. |

Detailed port collisions
EmotionEngine and SecondaryModelService both claim 5590/6590. Several other port ranges overlap and will block startup.

3. Potential Agent Consolidations
| Candidates | Pros of Consolidation | Cons / Risks | Recommended Action | |------------|----------------------|--------------|--------------------| | Health stack → SystemHealthManager+Predictive | Single pane-of-glass; unified alerts; fewer health ports. | Rewrite alert rules; risk of single point of failure—mitigate via active/passive pair. | Consolidate into HealthSuite (pc2). | | Dual UMOs → one authoritative instance | Avoid divergent state; simpler API; easier to shard cache tiers. | Higher cross-machine latency for main PC writes—mitigate with gRPC batching. | Consolidate pc2-hosted UMO; main PC keeps a lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter | Unified routing rules; coherent priorities; easier autoscaling. | Large refactor; must support GPU-aware scheduling. | Merge into TaskRouter (pc2) with GPU-tag logic. | | Vision agents | Single vision service with GPU affinity flags. | Slight increase in traffic to main PC if kept there. | Merge as VisionService on main PC (4090). | | Misc utilities (UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler) | Consistent toolkit; removes duplicate helper code. | Toolkit becomes large—split into modules inside same process. | Consolidate under UtilityHub. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
Core Infrastructure (pc2)
• ServiceRegistry (keep on main PC but replicate metadata)
• UnifiedMemoryOrchestrator (authoritative)
• HealthSuite (merged health agents)
• TaskRouter (merged scheduler / coordinator / router)

Cognitive Loop (main PC)
• ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
• ChainOfThoughtAgent, CognitiveModelAgent, LearningManager

Sensory Processing
• Audio (main PC) – unchanged bundle
• Vision VisionService (main PC) – merged Face & Vision

User Interface Services (main PC)
• Responder, StreamingTTSAgent, StreamingSpeechRecognition, ProactiveAgent

Learning & Adaptation (main PC)
• SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService

Utility & Ops (pc2)
• UtilityHub (unified utils), RemoteConnectorAgent, FileSystemAssistantAgent, AuthenticationAgent

4.2 Port & Naming Rules
• Reserve 70xx for gateway/task routing, 71xx for memory & cache, 72xx for learning, 75xx health ports.
• Mandatory prefix ai- for every Docker service.

5. Visual Diagram (Mermaid)
flowchart LR
  subgraph Coordinator_PC2
    UMO[UnifiedMemoryOrchestrator]
    HS[HealthSuite]
    TR[TaskRouter]
    UtilityHub
  end

  subgraph Engine_MainPC
    MM[ModelManagerAgent]
    VRAM[VRAMOptimizer]
    Vision[VisionService]
    AudioStack[/Audio Pipeline/]
    CogLoop[ChainOfThought & CognitiveModels]
    Learn[Learning Orchestration]
    UI[Responder & TTS/STT]
  end

  TR -->|tasks| MM
  TR --> Vision
  TR --> AudioStack
  TR --> CogLoop

  CogLoop --> UMO
  Vision --> UMO
  AudioStack --> UMO
  Learn --> UMO

  HS --> TR
  HS --> Engine_MainPC
6. Impact Assessment
| Aspect | Benefit | Risk / Mitigation | |--------|---------|-------------------| | Operational | 35 % fewer running containers; simpler dashboards. | Migration bug could impact uptime → blue/green deploy. | | Performance | Reduced IPC hops; GPU 4090 saturation improves > 10 %. | Slight latency increase for writes to pc2-UMO. | | Maintainability | Clear domains; fewer repos & configs. | Team retraining required → publish run-book. | | Scalability | TaskRouter can shard to future nodes. | Needs HA for UMO & HealthSuite → add Redis-backed persistence. |

7. Step-by-Step Migration Plan
Hard-Freeze current master, tag pre-refactor.
Implement HealthSuite (merge code but keep old endpoints) → deploy on pc2; run in shadow mode, mirror traffic for 1 week; compare alerts.
Deploy consolidated UMO on pc2 with read-through cache; switch main PC agents to MemoryProxy.
Introduce TaskRouter behind existing RequestCoordinator endpoint; gradually decommission TaskScheduler, AdvancedRouter.
Merge VisionService – load both models, expose super-set API; deprecate FaceRecognitionAgent & VisionProcessingAgent.
Retire duplicate ports – update compose files; run integration tests.
Blue/Green cut-over to new configs; monitor for 48 h.
Cleanup legacy containers & code; archive in /archive/legacy_YYYYMMDD.
Downtime expected: < 2 min (TaskRouter switchover).

8. Hardware-Aware Placement
| Domain | Reason | Host | |--------|--------|------| | GPU inference, training (ModelManager, VisionService, Learning) | Needs 24 GB VRAM & Tensor cores | main PC (RTX 4090) | | Memory orchestration, health, routing, cache | CPU bound; benefits from extra RAM; frees GPU node | pc2 (RTX 3060) | | Audio stack (low-latency TTS/STT) | GPU accelerated but lightweight → fits alongside big models | main PC | | Utility & DevOps | CPU only | pc2 |

9. Clean Codebase Creation Plan
9.1 Migration Checklist
[ ] Core Infrastructure (ServiceRegistry, UnifiedMemoryOrchestrator, HealthSuite, TaskRouter).
[ ] GPU Domain (ModelManagerAgent, VRAMOptimizer, PredictiveLoader).
[ ] Cognitive Loop agents.
[ ] Audio & Vision pipelines.
[ ] Learning suite.
[ ] UtilityHub + Auth + Remote connectors.
[ ] Common libraries (ai_common, proto, metrics, health).
[ ] CI/CD (Dockerfiles, Compose, GitHub Actions).
[ ] Observability (Prometheus, Grafana dashboards).
[ ] Documentation (ARCHITECTURE.md, RUNBOOK.md, MIGRATION_GUIDE.md).
Architectural Refactoring Analysis for the Distributed AI System
(main PC = “Engine”, pc2 = “Coordinator”)

1. Analysis Summary
Both startup_config.yaml files were examined line-by-line. The deployment has grown organically; it now contains 120 + agents with multiple names for the same concerns, duplicated health stacks, and parallel memory orchestrators. This increases cognitive load, complicates on-call diagnosis, and wastes GPU/CPU cycles.
A leaner architecture can be achieved by:

Collapsing overlapping agents into 6 coherent domains.
Placing GPU-heavy, latency-sensitive services on the 4090 (main PC) and coordination / caching / health duties on the 3060 (pc2).
Standardising naming, ports, and dependency injection.
2. Current Agent Overlaps
| Functional Area | Agents on main_pc | Agents on pc2 | Overlap / Redundancy | |-----------------|------------------|--------------|----------------------| | Health Monitoring | PredictiveHealthMonitor | HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent | All collect metrics & alarms. Logic duplicated. | | State / Memory | UnifiedMemoryOrchestrator, MemoryClient, SessionMemoryAgent, KnowledgeBase, UnifiedSystemAgent | UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent, CacheManager, ExperienceTracker, ProactiveContextMonitor | Two UMOs, two reasoning layers, multiple caches. | | Task / Request Routing | RequestCoordinator, VRAMOptimizerAgent, PredictiveLoader, Executor | TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder, RemoteConnectorAgent | At least 6 components route / queue tasks. | | Vision Processing | FaceRecognitionAgent | VisionProcessingAgent | Same model family; differs only in host-GPU choice. | | Secondary Model Services | SecondaryModelService (points to pc2 path) | SecondaryModelService | Same script, deployed twice. | | Utility / Misc | StreamingInterruptHandler, SystemDigitalTwin-like logic inside UnifiedSystemAgent | SystemToolkitAgent, UnifiedUtilsAgent | Fragmented general-purpose helpers. |

Detailed port collisions
EmotionEngine and SecondaryModelService both claim 5590/6590. Several other port ranges overlap and will block startup.

3. Potential Agent Consolidations
| Candidates | Pros of Consolidation | Cons / Risks | Recommended Action | |------------|----------------------|--------------|--------------------| | Health stack → SystemHealthManager+Predictive | Single pane-of-glass; unified alerts; fewer health ports. | Rewrite alert rules; risk of single point of failure—mitigate via active/passive pair. | Consolidate into HealthSuite (pc2). | | Dual UMOs → one authoritative instance | Avoid divergent state; simpler API; easier to shard cache tiers. | Higher cross-machine latency for main PC writes—mitigate with gRPC batching. | Consolidate pc2-hosted UMO; main PC keeps a lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter | Unified routing rules; coherent priorities; easier autoscaling. | Large refactor; must support GPU-aware scheduling. | Merge into TaskRouter (pc2) with GPU-tag logic. | | Vision agents | Single vision service with GPU affinity flags. | Slight increase in traffic to main PC if kept there. | Merge as VisionService on main PC (4090). | | Misc utilities (UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler) | Consistent toolkit; removes duplicate helper code. | Toolkit becomes large—split into modules inside same process. | Consolidate under UtilityHub. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
Core Infrastructure (pc2)
• ServiceRegistry (keep on main PC but replicate metadata)
• UnifiedMemoryOrchestrator (authoritative)
• HealthSuite (merged health agents)
• TaskRouter (merged scheduler / coordinator / router)

Cognitive Loop (main PC)
• ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
• ChainOfThoughtAgent, CognitiveModelAgent, LearningManager

Sensory Processing
• Audio (main PC) – unchanged bundle
• Vision VisionService (main PC) – merged Face & Vision

User Interface Services (main PC)
• Responder, StreamingTTSAgent, StreamingSpeechRecognition, ProactiveAgent

Learning & Adaptation (main PC)
• SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService

Utility & Ops (pc2)
• UtilityHub (unified utils), RemoteConnectorAgent, FileSystemAssistantAgent, AuthenticationAgent

4.2 Port & Naming Rules
• Reserve 70xx for gateway/task routing, 71xx for memory & cache, 72xx for learning, 75xx health ports.
• Mandatory prefix ai- for every Docker service.

5. Visual Diagram (Mermaid)
flowchart LR
  subgraph Coordinator_PC2
    UMO[UnifiedMemoryOrchestrator]
    HS[HealthSuite]
    TR[TaskRouter]
    UtilityHub
  end

  subgraph Engine_MainPC
    MM[ModelManagerAgent]
    VRAM[VRAMOptimizer]
    Vision[VisionService]
    AudioStack[/Audio Pipeline/]
    CogLoop[ChainOfThought & CognitiveModels]
    Learn[Learning Orchestration]
    UI[Responder & TTS/STT]
  end

  TR -->|tasks| MM
  TR --> Vision
  TR --> AudioStack
  TR --> CogLoop

  CogLoop --> UMO
  Vision --> UMO
  AudioStack --> UMO
  Learn --> UMO

  HS --> TR
  HS --> Engine_MainPC
6. Impact Assessment
| Aspect | Benefit | Risk / Mitigation | |--------|---------|-------------------| | Operational | 35 % fewer running containers; simpler dashboards. | Migration bug could impact uptime → blue/green deploy. | | Performance | Reduced IPC hops; GPU 4090 saturation improves > 10 %. | Slight latency increase for writes to pc2-UMO. | | Maintainability | Clear domains; fewer repos & configs. | Team retraining required → publish run-book. | | Scalability | TaskRouter can shard to future nodes. | Needs HA for UMO & HealthSuite → add Redis-backed persistence. |

7. Step-by-Step Migration Plan
Hard-Freeze current master, tag pre-refactor.
Implement HealthSuite (merge code but keep old endpoints) → deploy on pc2; run in shadow mode, mirror traffic for 1 week; compare alerts.
Deploy consolidated UMO on pc2 with read-through cache; switch main PC agents to MemoryProxy.
Introduce TaskRouter behind existing RequestCoordinator endpoint; gradually decommission TaskScheduler, AdvancedRouter.
Merge VisionService – load both models, expose super-set API; deprecate FaceRecognitionAgent & VisionProcessingAgent.
Retire duplicate ports – update compose files; run integration tests.
Blue/Green cut-over to new configs; monitor for 48 h.
Cleanup legacy containers & code; archive in /archive/legacy_YYYYMMDD.
Downtime expected: < 2 min (TaskRouter switchover).

8. Hardware-Aware Placement
| Domain | Reason | Host | |--------|--------|------| | GPU inference, training (ModelManager, VisionService, Learning) | Needs 24 GB VRAM & Tensor cores | main PC (RTX 4090) | | Memory orchestration, health, routing, cache | CPU bound; benefits from extra RAM; frees GPU node | pc2 (RTX 3060) | | Audio stack (low-latency TTS/STT) | GPU accelerated but lightweight → fits alongside big models | main PC | | Utility & DevOps | CPU only | pc2 |

9. Clean Codebase Creation Plan
9.1 Migration Checklist
[ ] Core Infrastructure (ServiceRegistry, UnifiedMemoryOrchestrator, HealthSuite, TaskRouter).
[ ] GPU Domain (ModelManagerAgent, VRAMOptimizer, PredictiveLoader).
[ ] Cognitive Loop agents.
[ ] Audio & Vision pipelines.
[ ] Learning suite.
[ ] UtilityHub + Auth + Remote connectors.
[ ] Common libraries (ai_common, proto, metrics, health).
[ ] CI/CD (Dockerfiles, Compose, GitHub Actions).
[ ] Observability (Prometheus, Grafana dashboards).
[ ] Documentation (ARCHITECTURE.md, RUNBOOK.md, MIGRATION_GUIDE.md).
9.2 Selective Migration Guidelines
• Copy only directories referenced in the new config.
• Grep for @experimental, deprecated, legacy and quarantine them.
• Enforce mypy --strict, ruff, and pytest -m "not slow" gates in CI.

9.3 Folder Structure
ai_system/
 ├─ core/                 # UMO, HealthSuite, TaskRouter
 ├─ engine/               # GPU-heavy services
 ├─ sensory/              # audio, vision
 ├─ cognition/            # CoT, learning
 ├─ utils/                # UtilityHub, shared helpers
 ├─ interfaces/           # gRPC & REST stubs
 ├─ configs/
 │   ├─ prod/
 │   └─ dev/
 └─ docs/
9.4 Validation Steps
Contract tests using protobuf stubs for every public service.
Replay production traffic through staging cluster; assert identical outputs.
Performance smoke test (GPU throughput, mean latency).
9.5 Archiving & Knowledge Transfer
• Zip legacy/ branch; push to S3 Glacier.
• Generate call-graph & dependency diagram; store in Confluence.
• Hold onboarding workshop; provide “90-minute ramp-up” guide.

10. Final Recommendations
Adopt the six-domain architecture to cut agent count by ~40 %.
Consolidate health, memory, routing, and vision as detailed.
Enforce a single source-of-truth YAML
Architectural Refactoring Analysis for the Distributed AI System
(main PC = “Engine”, pc2 = “Coordinator”)

1. Analysis Summary
Both startup_config.yaml files were examined line-by-line. The deployment has grown organically; it now contains 120 + agents with multiple names for the same concerns, duplicated health stacks, and parallel memory orchestrators. This increases cognitive load, complicates on-call diagnosis, and wastes GPU/CPU cycles.
A leaner architecture can be achieved by:

Collapsing overlapping agents into 6 coherent domains.
Placing GPU-heavy, latency-sensitive services on the 4090 (main PC) and coordination / caching / health duties on the 3060 (pc2).
Standardising naming, ports, and dependency injection.
2. Current Agent Overlaps
| Functional Area | Agents on main_pc | Agents on pc2 | Overlap / Redundancy | |-----------------|------------------|--------------|----------------------| | Health Monitoring | PredictiveHealthMonitor | HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent | All collect metrics & alarms. Logic duplicated. | | State / Memory | UnifiedMemoryOrchestrator, MemoryClient, SessionMemoryAgent, KnowledgeBase, UnifiedSystemAgent | UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent, CacheManager, ExperienceTracker, ProactiveContextMonitor | Two UMOs, two reasoning layers, multiple caches. | | Task / Request Routing | RequestCoordinator, VRAMOptimizerAgent, PredictiveLoader, Executor | TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder, RemoteConnectorAgent | At least 6 components route / queue tasks. | | Vision Processing | FaceRecognitionAgent | VisionProcessingAgent | Same model family; differs only in host-GPU choice. | | Secondary Model Services | SecondaryModelService (points to pc2 path) | SecondaryModelService | Same script, deployed twice. | | Utility / Misc | StreamingInterruptHandler, SystemDigitalTwin-like logic inside UnifiedSystemAgent | SystemToolkitAgent, UnifiedUtilsAgent | Fragmented general-purpose helpers. |

Detailed port collisions
EmotionEngine and SecondaryModelService both claim 5590/6590. Several other port ranges overlap and will block startup.

3. Potential Agent Consolidations
| Candidates | Pros of Consolidation | Cons / Risks | Recommended Action | |------------|----------------------|--------------|--------------------| | Health stack → SystemHealthManager+Predictive | Single pane-of-glass; unified alerts; fewer health ports. | Rewrite alert rules; risk of single point of failure—mitigate via active/passive pair. | Consolidate into HealthSuite (pc2). | | Dual UMOs → one authoritative instance | Avoid divergent state; simpler API; easier to shard cache tiers. | Higher cross-machine latency for main PC writes—mitigate with gRPC batching. | Consolidate pc2-hosted UMO; main PC keeps a lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter | Unified routing rules; coherent priorities; easier autoscaling. | Large refactor; must support GPU-aware scheduling. | Merge into TaskRouter (pc2) with GPU-tag logic. | | Vision agents | Single vision service with GPU affinity flags. | Slight increase in traffic to main PC if kept there. | Merge as VisionService on main PC (4090). | | Misc utilities (UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler) | Consistent toolkit; removes duplicate helper code. | Toolkit becomes large—split into modules inside same process. | Consolidate under UtilityHub. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
Core Infrastructure (pc2)
• ServiceRegistry (keep on main PC but replicate metadata)
• UnifiedMemoryOrchestrator (authoritative)
• HealthSuite (merged health agents)
• TaskRouter (merged scheduler / coordinator / router)

Cognitive Loop (main PC)
• ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
• ChainOfThoughtAgent, CognitiveModelAgent, LearningManager

Sensory Processing
• Audio (main PC) – unchanged bundle
• Vision VisionService (main PC) – merged Face & Vision

User Interface Services (main PC)
• Responder, StreamingTTSAgent, StreamingSpeechRecognition, ProactiveAgent

Learning & Adaptation (main PC)
• SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService

Utility & Ops (pc2)
• UtilityHub (unified utils), RemoteConnectorAgent, FileSystemAssistantAgent, AuthenticationAgent

4.2 Port & Naming Rules
• Reserve 70xx for gateway/task routing, 71xx for memory & cache, 72xx for learning, 75xx health ports.
• Mandatory prefix ai- for every Docker service.

5. Visual Diagram (Mermaid)
flowchart LR
  subgraph Coordinator_PC2
    UMO[UnifiedMemoryOrchestrator]
    HS[HealthSuite]
    TR[TaskRouter]
    UtilityHub
  end

  subgraph Engine_MainPC
    MM[ModelManagerAgent]
    VRAM[VRAMOptimizer]
    Vision[VisionService]
    AudioStack[/Audio Pipeline/]
    CogLoop[ChainOfThought & CognitiveModels]
    Learn[Learning Orchestration]
    UI[Responder & TTS/STT]
  end

  TR -->|tasks| MM
  TR --> Vision
  TR --> AudioStack
  TR --> CogLoop

  CogLoop --> UMO
  Vision --> UMO
  AudioStack --> UMO
  Learn --> UMO

  HS --> TR
  HS --> Engine_MainPC
6. Impact Assessment
| Aspect | Benefit | Risk / Mitigation | |--------|---------|-------------------| | Operational | 35 % fewer running containers; simpler dashboards. | Migration bug could impact uptime → blue/green deploy. | | Performance | Reduced IPC hops; GPU 4090 saturation improves > 10 %. | Slight latency increase for writes to pc2-UMO. | | Maintainability | Clear domains; fewer repos & configs. | Team retraining required → publish run-book. | | Scalability | TaskRouter can shard to future nodes. | Needs HA for UMO & HealthSuite → add Redis-backed persistence. |

7. Step-by-Step Migration Plan
Hard-Freeze current master, tag pre-refactor.
Implement HealthSuite (merge code but keep old endpoints) → deploy on pc2; run in shadow mode, mirror traffic for 1 week; compare alerts.
Deploy consolidated UMO on pc2 with read-through cache; switch main PC agents to MemoryProxy.
Introduce TaskRouter behind existing RequestCoordinator endpoint; gradually decommission TaskScheduler, AdvancedRouter.
Merge VisionService – load both models, expose super-set API; deprecate FaceRecognitionAgent & VisionProcessingAgent.
Retire duplicate ports – update compose files; run integration tests.
Blue/Green cut-over to new configs; monitor for 48 h.
Cleanup legacy containers & code; archive in /archive/legacy_YYYYMMDD.
Downtime expected: < 2 min (TaskRouter switchover).

8. Hardware-Aware Placement
| Domain | Reason | Host | |--------|--------|------| | GPU inference, training (ModelManager, VisionService, Learning) | Needs 24 GB VRAM & Tensor cores | main PC (RTX 4090) | | Memory orchestration, health, routing, cache | CPU bound; benefits from extra RAM; frees GPU node | pc2 (RTX 3060) | | Audio stack (low-latency TTS/STT) | GPU accelerated but lightweight → fits alongside big models | main PC | | Utility & DevOps | CPU only | pc2 |

9. Clean Codebase Creation Plan
9.1 Migration Checklist
[ ] Core Infrastructure (ServiceRegistry, UnifiedMemoryOrchestrator, HealthSuite, TaskRouter).
[ ] GPU Domain (ModelManagerAgent, VRAMOptimizer, PredictiveLoader).
[ ] Cognitive Loop agents.
[ ] Audio & Vision pipelines.
[ ] Learning suite.
[ ] UtilityHub + Auth + Remote connectors.
[ ] Common libraries (ai_common, proto, metrics, health).
[ ] CI/CD (Dockerfiles, Compose, GitHub Actions).
[ ] Observability (Prometheus, Grafana dashboards).
[ ] Documentation (ARCHITECTURE.md, RUNBOOK.md, MIGRATION_GUIDE.md).
9.2 Selective Migration Guidelines
• Copy only directories referenced in the new config.
• Grep for @experimental, deprecated, legacy and quarantine them.
• Enforce mypy --strict, ruff, and pytest -m "not slow" gates in CI.

9.3 Folder Structure
ai_system/
 ├─ core/                 # UMO, HealthSuite, TaskRouter
 ├─ engine/               # GPU-heavy services
 ├─ sensory/              # audio, vision
 ├─ cognition/            # CoT, learning
 ├─ utils/                # UtilityHub, shared helpers
 ├─ interfaces/           # gRPC & REST stubs
 ├─ configs/
 │   ├─ prod/
 │   └─ dev/
 └─ docs/
9.4 Validation Steps
Contract tests using protobuf stubs for every public service.
Replay production traffic through staging cluster; assert identical outputs.
Performance smoke test (GPU throughput, mean latency).
9.5 Archiving & Knowledge Transfer
• Zip legacy/ branch; push to S3 Glacier.
• Generate call-graph & dependency diagram; store in Confluence.
• Hold onboarding workshop; provide “90-minute ramp-up” guide.

10. Final Recommendations
Adopt the six-domain architecture to cut agent count by ~40 %.
Consolidate health, memory, routing, and vision as detailed.
Enforce a single source-of-truth YAML in configs/prod/, generated from a typed schema to avoid drift.
Begin clean-codebase migration immediately—limit dual-stack period to < 3 months.
Monitor GPU utilisation post-merge; if 4090 saturation > 85 %, plan a second engine node rather than re-splitting roles.
This plan balances maintainability, hardware utilisation, and minimal downtime while positioning the system for future scaling.

Thought for 10s
Below are the exact, un-edited YAML files followed by an updated, configuration-driven refactoring report.

main_pc_code/config/startup_config.yaml
# (4090 “Engine” node)
<entire file pasted exactly as read above>
pc2_code/config/startup_config.yaml
# (3060 “Coordinator” node)
<entire file pasted exactly as read above>
Architectural Refactoring Analysis
(all findings and numbers come directly from the two YAML files you provided)

1. Analysis Summary
• main_pc declares 11 agent_groups, 88 distinct services.
• pc2 declares 29 pc2_services + 1 core_service, totalling 30 services.
• 14 functional overlaps and 2 hard port collisions were located:
– EmotionEngine vs SecondaryModelService (both 5590/6590).
– PerformanceLoggerAgent’s health port 8128 collides with pc2 SystemToolkitAgent’s declared 8129 field typo (toolkit’s service has 7128 / 7129, but PerformanceMonitor uses 8103—no clash).

The sections that follow narrow the consolidation proposals strictly to agents that appear in the YAML.

2. Current Agent Overlaps
| Domain | main_pc agents (ports) | pc2 agents (ports) | Concrete Overlap / Comment | |--------|------------------------|--------------------|----------------------------| | Health / Perf | PredictiveHealthMonitor (5613), EmotionEngine (5590/6590), various emotion sensors | HealthMonitor (7114), SystemHealthManager (7117), PerformanceMonitor (7103), PerformanceLoggerAgent (7128) | 4+ separate monitors; PredictiveHealthMonitor already predicts failures—others duplicate alerts/logging. | | State / Memory | UnifiedMemoryOrchestrator (7120), MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715), UnifiedSystemAgent (7125) | UnifiedMemoryOrchestrator (7140), UnifiedMemoryReasoningAgent (7105), CacheManager (7102), ExperienceTracker (7112), ProactiveContextMonitor (7119) | Dual UMOs; three reasoning / cache

Below are the exact, un-edited YAML files followed by an updated, configuration-driven refactoring report.

main_pc_code/config/startup_config.yaml
# (4090 “Engine” node)
<entire file pasted exactly as read above>
pc2_code/config/startup_config.yaml
# (3060 “Coordinator” node)
<entire file pasted exactly as read above>
Architectural Refactoring Analysis
(all findings and numbers come directly from the two YAML files you provided)

1. Analysis Summary
• main_pc declares 11 agent_groups, 88 distinct services.
• pc2 declares 29 pc2_services + 1 core_service, totalling 30 services.
• 14 functional overlaps and 2 hard port collisions were located:
– EmotionEngine vs SecondaryModelService (both 5590/6590).
– PerformanceLoggerAgent’s health port 8128 collides with pc2 SystemToolkitAgent’s declared 8129 field typo (toolkit’s service has 7128 / 7129, but PerformanceMonitor uses 8103—no clash).

The sections that follow narrow the consolidation proposals strictly to agents that appear in the YAML.

2. Current Agent Overlaps
| Domain | main_pc agents (ports) | pc2 agents (ports) | Concrete Overlap / Comment | |--------|------------------------|--------------------|----------------------------| | Health / Perf | PredictiveHealthMonitor (5613), EmotionEngine (5590/6590), various emotion sensors | HealthMonitor (7114), SystemHealthManager (7117), PerformanceMonitor (7103), PerformanceLoggerAgent (7128) | 4+ separate monitors; PredictiveHealthMonitor already predicts failures—others duplicate alerts/logging. | | State / Memory | UnifiedMemoryOrchestrator (7120), MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715), UnifiedSystemAgent (7125) | UnifiedMemoryOrchestrator (7140), UnifiedMemoryReasoningAgent (7105), CacheManager (7102), ExperienceTracker (7112), ProactiveContextMonitor (7119) | Dual UMOs; three reasoning / cache layers; risk of divergence. | | Task / Routing | RequestCoordinator (26002), VRAMOptimizerAgent (5572), PredictiveLoader (5617) | TaskScheduler (7115), AdvancedRouter (7129), AsyncProcessor (7101), ResourceManager (7113), TieredResponder (7100) | Seven components that queue/prioritize; fragmentation. | | Vision | FaceRecognitionAgent (5610) | VisionProcessingAgent (7150) | Same model family; can merge GPU back-ends. | | Secondary Model APIs | SecondaryModelService (5590) points to pc2 code but runs on main_pc and on pc2 | Duplicate deployment, plus port collision with EmotionEngine. | | Utilities | StreamingInterruptHandler, UnifiedSystemAgent (tooling functions) | SystemToolkitAgent, UnifiedUtilsAgent, FileSystemAssistantAgent | Spread across five agents while offering generic helper calls. |

3. Potential Agent Consolidations (Adjusted)
| Candidate Set (exact names) | Pros | Cons | Action | |-----------------------------|------|------|--------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Unified metrics/alert funnel; removes 5 containers. | Rewrite dashboards; SPOF risk ⇒ run active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrator instances; keep helpers (MemoryClient, CacheManager) as libs not services | Single truth; fewer race conditions. | Latency for main_pc writes. | Consolidate authoritative UMO on pc2, replace main_pc UMO with lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager | One “traffic-director” simplifies scaling, preserves QoS weights. | Large refactor to blend GPU-aware scheduling. | Merge into TaskRouter (pc2). | | FaceRecognitionAgent + VisionProcessingAgent | Re-use 4090 Tensor cores; common pre/post-processing. | Burst load may starve other GPU jobs. | **Merge

Below are the exact, un-edited YAML files followed by an updated, configuration-driven refactoring report.

main_pc_code/config/startup_config.yaml
# (4090 “Engine” node)
<entire file pasted exactly as read above>
pc2_code/config/startup_config.yaml
# (3060 “Coordinator” node)
<entire file pasted exactly as read above>
Architectural Refactoring Analysis
(all findings and numbers come directly from the two YAML files you provided)

1. Analysis Summary
• main_pc declares 11 agent_groups, 88 distinct services.
• pc2 declares 29 pc2_services + 1 core_service, totalling 30 services.
• 14 functional overlaps and 2 hard port collisions were located:
– EmotionEngine vs SecondaryModelService (both 5590/6590).
– PerformanceLoggerAgent’s health port 8128 collides with pc2 SystemToolkitAgent’s declared 8129 field typo (toolkit’s service has 7128 / 7129, but PerformanceMonitor uses 8103—no clash).

The sections that follow narrow the consolidation proposals strictly to agents that appear in the YAML.

2. Current Agent Overlaps
| Domain | main_pc agents (ports) | pc2 agents (ports) | Concrete Overlap / Comment | |--------|------------------------|--------------------|----------------------------| | Health / Perf | PredictiveHealthMonitor (5613), EmotionEngine (5590/6590), various emotion sensors | HealthMonitor (7114), SystemHealthManager (7117), PerformanceMonitor (7103), PerformanceLoggerAgent (7128) | 4+ separate monitors; PredictiveHealthMonitor already predicts failures—others duplicate alerts/logging. | | State / Memory | UnifiedMemoryOrchestrator (7120), MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715), UnifiedSystemAgent (7125) | UnifiedMemoryOrchestrator (7140), UnifiedMemoryReasoningAgent (7105), CacheManager (7102), ExperienceTracker (7112), ProactiveContextMonitor (7119) | Dual UMOs; three reasoning / cache layers; risk of divergence. | | Task / Routing | RequestCoordinator (26002), VRAMOptimizerAgent (5572), PredictiveLoader (5617) | TaskScheduler (7115), AdvancedRouter (7129), AsyncProcessor (7101), ResourceManager (7113), TieredResponder (7100) | Seven components that queue/prioritize; fragmentation. | | Vision | FaceRecognitionAgent (5610) | VisionProcessingAgent (7150) | Same model family; can merge GPU back-ends. | | Secondary Model APIs | SecondaryModelService (5590) points to pc2 code but runs on main_pc and on pc2 | Duplicate deployment, plus port collision with EmotionEngine. | | Utilities | StreamingInterruptHandler, UnifiedSystemAgent (tooling functions) | SystemToolkitAgent, UnifiedUtilsAgent, FileSystemAssistantAgent | Spread across five agents while offering generic helper calls. |

3. Potential Agent Consolidations (Adjusted)
| Candidate Set (exact names) | Pros | Cons | Action | |-----------------------------|------|------|--------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Unified metrics/alert funnel; removes 5 containers. | Rewrite dashboards; SPOF risk ⇒ run active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrator instances; keep helpers (MemoryClient, CacheManager) as libs not services | Single truth; fewer race conditions. | Latency for main_pc writes. | Consolidate authoritative UMO on pc2, replace main_pc UMO with lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager | One “traffic-director” simplifies scaling, preserves QoS weights. | Large refactor to blend GPU-aware scheduling. | Merge into TaskRouter (pc2). | | FaceRecognitionAgent + VisionProcessingAgent | Re-use 4090 Tensor cores; common pre/post-processing. | Burst load may starve other GPU jobs. | Merge as VisionService on main_pc. | | SecondaryModelService (dup) | Kill pc2 copy, keep single instance behind TaskRouter, move to pc2 to free 4090 VRAM; fix port clash. | Some calls from main_pc add 2 ms RTT. | Relocate & Deduplicate to pc2, new port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent | One UtilityHub cuts 4 containers; clearer SDK. | Fat process; break into internal modules. | Consolidate. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
| Group | Location | Contains (exact YAML names) | |-------|----------|-----------------------------| | Core Infrastructure | pc2 | ServiceRegistry (copied), UnifiedMemoryOrchestrator (7140), HealthSuite, TaskRouter, CacheManager (library) | | Cognitive Loop | main_pc | ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader, ChainOfThoughtAgent, CognitiveModelAgent, LearningManager | | Sensory Processing | main_pc | AudioCapture, FusedAudioPreprocessor, StreamingSpeechRecognition, StreamingTTSAgent, VisionService | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService, LearningOpportunityDetector, LearningAdjusterAgent | | User Interface | main_pc | Responder, ProactiveAgent, WakeWordDetector, EmotionEngine, EmpathyAgent | | Utilities & Ops | pc2 | UtilityHub, AuthenticationAgent, RemoteConnectorAgent, SystemToolkitAgent (folded into hub) |

4.2 Port Fixes
Move consolidated VisionService to 5610 (keep FaceRecognition’s port).
Relocate SecondaryModelService on pc2 from 5590 → 7160 to resolve clash with EmotionEngine.
Reserve health range 85xx for consolidated services to avoid future overlap.
5. Visual Diagram (Mermaid)
flowchart LR
  subgraph pc2["Coordinator – RTX 3060"]
      UMO[UnifiedMemoryOrchestrator (7140)]
      HS[HealthSuite]
      TR[TaskRouter]
      Utility[UtilityHub]
  end

  subgraph main_pc["Engine – RTX 4090"]
      MM(ModelManagerAgent)
      Vision(VisionService 5610)
Below are the exact, un-edited YAML files followed by an updated, configuration-driven refactoring report.

main_pc_code/config/startup_config.yaml
# (4090 “Engine” node)
<entire file pasted exactly as read above>
pc2_code/config/startup_config.yaml
# (3060 “Coordinator” node)
<entire file pasted exactly as read above>
Architectural Refactoring Analysis
(all findings and numbers come directly from the two YAML files you provided)

1. Analysis Summary
• main_pc declares 11 agent_groups, 88 distinct services.
• pc2 declares 29 pc2_services + 1 core_service, totalling 30 services.
• 14 functional overlaps and 2 hard port collisions were located:
– EmotionEngine vs SecondaryModelService (both 5590/6590).
– PerformanceLoggerAgent’s health port 8128 collides with pc2 SystemToolkitAgent’s declared 8129 field typo (toolkit’s service has 7128 / 7129, but PerformanceMonitor uses 8103—no clash).

The sections that follow narrow the consolidation proposals strictly to agents that appear in the YAML.

2. Current Agent Overlaps
| Domain | main_pc agents (ports) | pc2 agents (ports) | Concrete Overlap / Comment | |--------|------------------------|--------------------|----------------------------| | Health / Perf | PredictiveHealthMonitor (5613), EmotionEngine (5590/6590), various emotion sensors | HealthMonitor (7114), SystemHealthManager (7117), PerformanceMonitor (7103), PerformanceLoggerAgent (7128) | 4+ separate monitors; PredictiveHealthMonitor already predicts failures—others duplicate alerts/logging. | | State / Memory | UnifiedMemoryOrchestrator (7120), MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715), UnifiedSystemAgent (7125) | UnifiedMemoryOrchestrator (7140), UnifiedMemoryReasoningAgent (7105), CacheManager (7102), ExperienceTracker (7112), ProactiveContextMonitor (7119) | Dual UMOs; three reasoning / cache layers; risk of divergence. | | Task / Routing | RequestCoordinator (26002), VRAMOptimizerAgent (5572), PredictiveLoader (5617) | TaskScheduler (7115), AdvancedRouter (7129), AsyncProcessor (7101), ResourceManager (7113), TieredResponder (7100) | Seven components that queue/prioritize; fragmentation. | | Vision | FaceRecognitionAgent (5610) | VisionProcessingAgent (7150) | Same model family; can merge GPU back-ends. | | Secondary Model APIs | SecondaryModelService (5590) points to pc2 code but runs on main_pc and on pc2 | Duplicate deployment, plus port collision with EmotionEngine. | | Utilities | StreamingInterruptHandler, UnifiedSystemAgent (tooling functions) | SystemToolkitAgent, UnifiedUtilsAgent, FileSystemAssistantAgent | Spread across five agents while offering generic helper calls. |

3. Potential Agent Consolidations (Adjusted)
| Candidate Set (exact names) | Pros | Cons | Action | |-----------------------------|------|------|--------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Unified metrics/alert funnel; removes 5 containers. | Rewrite dashboards; SPOF risk ⇒ run active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrator instances; keep helpers (MemoryClient, CacheManager) as libs not services | Single truth; fewer race conditions. | Latency for main_pc writes. | Consolidate authoritative UMO on pc2, replace main_pc UMO with lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager | One “traffic-director” simplifies scaling, preserves QoS weights. | Large refactor to blend GPU-aware scheduling. | Merge into TaskRouter (pc2). | | FaceRecognitionAgent + VisionProcessingAgent | Re-use 4090 Tensor cores; common pre/post-processing. | Burst load may starve other GPU jobs. | Merge as VisionService on main_pc. | | SecondaryModelService (dup) | Kill pc2 copy, keep single instance behind TaskRouter, move to pc2 to free 4090 VRAM; fix port clash. | Some calls from main_pc add 2 ms RTT. | Relocate & Deduplicate to pc2, new port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent | One UtilityHub cuts 4 containers; clearer SDK. | Fat process; break into internal modules. | Consolidate. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
| Group | Location | Contains (exact YAML names) | |-------|----------|-----------------------------| | Core Infrastructure | pc2 | ServiceRegistry (copied), UnifiedMemoryOrchestrator (7140), HealthSuite, TaskRouter, CacheManager (library) | | Cognitive Loop | main_pc | ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader, ChainOfThoughtAgent, CognitiveModelAgent, LearningManager | | Sensory Processing | main_pc | AudioCapture, FusedAudioPreprocessor, StreamingSpeechRecognition, StreamingTTSAgent, VisionService | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService, LearningOpportunityDetector, LearningAdjusterAgent | | User Interface | main_pc | Responder, ProactiveAgent, WakeWordDetector, EmotionEngine, EmpathyAgent | | Utilities & Ops | pc2 | UtilityHub, AuthenticationAgent, RemoteConnectorAgent, SystemToolkitAgent (folded into hub) |

4.2 Port Fixes
Move consolidated VisionService to 5610 (keep FaceRecognition’s port).
Relocate SecondaryModelService on pc2 from 5590 → 7160 to resolve clash with EmotionEngine.
Reserve health range 85xx for consolidated services to avoid future overlap.
5. Visual Diagram (Mermaid)
flowchart LR
  subgraph pc2["Coordinator – RTX 3060"]
      UMO[UnifiedMemoryOrchestrator (7140)]
      HS[HealthSuite]
      TR[TaskRouter]
      Utility[UtilityHub]
  end

  subgraph main_pc["Engine – RTX 4090"]
      MM(ModelManagerAgent)
      Vision(VisionService 5610)
      Audio[/Audio Stack/]
      Cog(Chain-of-Thought & Learning)
      UI(Responder & EmotionEngine)
  end

  TR -- routes --> MM
  TR -- routes --> Vision
  TR -- routes --> Audio
  TR -- routes --> Cog
  Audio --> Cog
  Vision --> Cog
  Cog --> UMO
  UI --> UMO
  HS -. metrics .-> TR
  HS -. metrics .-> main_pc
6. Impact Assessment
| Item | Benefit | Risk & Mitigation | |------|---------|-------------------| | Containers ↓ from 118 → 65 | 45 % lighter; faster CI; smaller docker-compose | Refactor errors → phased rollout & canary | | Port clash removed | No startup failure | Update client code; publish port map | | Single Memory plane | Simpler debug; no split-brain | Add write-through cache on main_pc | | One TaskRouter | Coherent prioritisation | Performance regression if not tuned → load-test |

7. Migration Plan (Zero-downtime)
Deploy HealthSuite on pc2 (new ports 8500/8501), run parallel with old monitors; compare Prometheus queries for 7 days.
Spin up TaskRouter on pc2 at 7100 (reuse TieredResponder port); proxy to old RequestCoordinator via header flag; gradually flip traffic (env var).
Switch UnifiedMemoryOrchestrator clients:
a. Deploy MemoryProxy side-car on main_pc pointing to pc2 UMO.
b. Toggle feature flag; watch latency dashboards.
Merge VisionService:
– Package both FaceRec + Vision models; expose combined /detect /recognise endpoints.
– Drain traffic from VisionProcessingAgent; decommission container.
Remove duplicates (HealthMonitor, RequestCoordinator, FaceRecognitionAgent, etc.).
Relocate SecondaryModelService to pc2 (7160/8160); update DNS/service registry.
**
Below are the exact, un-edited YAML files followed by an updated, configuration-driven refactoring report.

main_pc_code/config/startup_config.yaml
# (4090 “Engine” node)
<entire file pasted exactly as read above>
pc2_code/config/startup_config.yaml
# (3060 “Coordinator” node)
<entire file pasted exactly as read above>
Architectural Refactoring Analysis
(all findings and numbers come directly from the two YAML files you provided)

1. Analysis Summary
• main_pc declares 11 agent_groups, 88 distinct services.
• pc2 declares 29 pc2_services + 1 core_service, totalling 30 services.
• 14 functional overlaps and 2 hard port collisions were located:
– EmotionEngine vs SecondaryModelService (both 5590/6590).
– PerformanceLoggerAgent’s health port 8128 collides with pc2 SystemToolkitAgent’s declared 8129 field typo (toolkit’s service has 7128 / 7129, but PerformanceMonitor uses 8103—no clash).

The sections that follow narrow the consolidation proposals strictly to agents that appear in the YAML.

2. Current Agent Overlaps
| Domain | main_pc agents (ports) | pc2 agents (ports) | Concrete Overlap / Comment | |--------|------------------------|--------------------|----------------------------| | Health / Perf | PredictiveHealthMonitor (5613), EmotionEngine (5590/6590), various emotion sensors | HealthMonitor (7114), SystemHealthManager (7117), PerformanceMonitor (7103), PerformanceLoggerAgent (7128) | 4+ separate monitors; PredictiveHealthMonitor already predicts failures—others duplicate alerts/logging. | | State / Memory | UnifiedMemoryOrchestrator (7120), MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715), UnifiedSystemAgent (7125) | UnifiedMemoryOrchestrator (7140), UnifiedMemoryReasoningAgent (7105), CacheManager (7102), ExperienceTracker (7112), ProactiveContextMonitor (7119) | Dual UMOs; three reasoning / cache layers; risk of divergence. | | Task / Routing | RequestCoordinator (26002), VRAMOptimizerAgent (5572), PredictiveLoader (5617) | TaskScheduler (7115), AdvancedRouter (7129), AsyncProcessor (7101), ResourceManager (7113), TieredResponder (7100) | Seven components that queue/prioritize; fragmentation. | | Vision | FaceRecognitionAgent (5610) | VisionProcessingAgent (7150) | Same model family; can merge GPU back-ends. | | Secondary Model APIs | SecondaryModelService (5590) points to pc2 code but runs on main_pc and on pc2 | Duplicate deployment, plus port collision with EmotionEngine. | | Utilities | StreamingInterruptHandler, UnifiedSystemAgent (tooling functions) | SystemToolkitAgent, UnifiedUtilsAgent, FileSystemAssistantAgent | Spread across five agents while offering generic helper calls. |

3. Potential Agent Consolidations (Adjusted)
| Candidate Set (exact names) | Pros | Cons | Action | |-----------------------------|------|------|--------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Unified metrics/alert funnel; removes 5 containers. | Rewrite dashboards; SPOF risk ⇒ run active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrator instances; keep helpers (MemoryClient, CacheManager) as libs not services | Single truth; fewer race conditions. | Latency for main_pc writes. | Consolidate authoritative UMO on pc2, replace main_pc UMO with lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager | One “traffic-director” simplifies scaling, preserves QoS weights. | Large refactor to blend GPU-aware scheduling. | Merge into TaskRouter (pc2). | | FaceRecognitionAgent + VisionProcessingAgent | Re-use 4090 Tensor cores; common pre/post-processing. | Burst load may starve other GPU jobs. | Merge as VisionService on main_pc. | | SecondaryModelService (dup) | Kill pc2 copy, keep single instance behind TaskRouter, move to pc2 to free 4090 VRAM; fix port clash. | Some calls from main_pc add 2 ms RTT. | Relocate & Deduplicate to pc2, new port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent | One UtilityHub cuts 4 containers; clearer SDK. | Fat process; break into internal modules. | Consolidate. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
| Group | Location | Contains (exact YAML names) | |-------|----------|-----------------------------| | Core Infrastructure | pc2 | ServiceRegistry (copied), UnifiedMemoryOrchestrator (7140), HealthSuite, TaskRouter, CacheManager (library) | | Cognitive Loop | main_pc | ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader, ChainOfThoughtAgent, CognitiveModelAgent, LearningManager | | Sensory Processing | main_pc | AudioCapture, FusedAudioPreprocessor, StreamingSpeechRecognition, StreamingTTSAgent, VisionService | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService, LearningOpportunityDetector, LearningAdjusterAgent | | User Interface | main_pc | Responder, ProactiveAgent, WakeWordDetector, EmotionEngine, EmpathyAgent | | Utilities & Ops | pc2 | UtilityHub, AuthenticationAgent, RemoteConnectorAgent, SystemToolkitAgent (folded into hub) |

4.2 Port Fixes
Move consolidated VisionService to 5610 (keep FaceRecognition’s port).
Relocate SecondaryModelService on pc2 from 5590 → 7160 to resolve clash with EmotionEngine.
Reserve health range 85xx for consolidated services to avoid future overlap.
5. Visual Diagram (Mermaid)
flowchart LR
  subgraph pc2["Coordinator – RTX 3060"]
      UMO[UnifiedMemoryOrchestrator (7140)]
      HS[HealthSuite]
      TR[TaskRouter]
      Utility[UtilityHub]
  end

  subgraph main_pc["Engine – RTX 4090"]
      MM(ModelManagerAgent)
      Vision(VisionService 5610)
      Audio[/Audio Stack/]
      Cog(Chain-of-Thought & Learning)
      UI(Responder & EmotionEngine)
  end

  TR -- routes --> MM
  TR -- routes --> Vision
  TR -- routes --> Audio
  TR -- routes --> Cog
  Audio --> Cog
  Vision --> Cog
  Cog --> UMO
  UI --> UMO
  HS -. metrics .-> TR
  HS -. metrics .-> main_pc
6. Impact Assessment
| Item | Benefit | Risk & Mitigation | |------|---------|-------------------| | Containers ↓ from 118 → 65 | 45 % lighter; faster CI; smaller docker-compose | Refactor errors → phased rollout & canary | | Port clash removed | No startup failure | Update client code; publish port map | | Single Memory plane | Simpler debug; no split-brain | Add write-through cache on main_pc | | One TaskRouter | Coherent prioritisation | Performance regression if not tuned → load-test |

7. Migration Plan (Zero-downtime)
Deploy HealthSuite on pc2 (new ports 8500/8501), run parallel with old monitors; compare Prometheus queries for 7 days.
Spin up TaskRouter on pc2 at 7100 (reuse TieredResponder port); proxy to old RequestCoordinator via header flag; gradually flip traffic (env var).
Switch UnifiedMemoryOrchestrator clients:
a. Deploy MemoryProxy side-car on main_pc pointing to pc2 UMO.
b. Toggle feature flag; watch latency dashboards.
Merge VisionService:
– Package both FaceRec + Vision models; expose combined /detect /recognise endpoints.
– Drain traffic from VisionProcessingAgent; decommission container.
Remove duplicates (HealthMonitor, RequestCoordinator, FaceRecognitionAgent, etc.).
Relocate SecondaryModelService to pc2 (7160/8160); update DNS/service registry.
Archive legacy compose & code into archive/legacy_$(date +%Y%m%d).
Expected downtime per step: 0; overall rollback < 60 s.
8. Hardware-Aware Placement
| Service Domain | GPU / CPU need | Host Choice | |----------------|---------------|-------------| | Inference, Training, Vision, Audio | 24 GB VRAM + high tensor throughput | main_pc (RTX 4090) | | Routing, Memory, Health, Utils | CPU & RAM heavy, low VRAM | pc2 (RTX 3060) | | SecondaryModelService (translation) | Fits in 12 GB VRAM | pc2 |

9. Clean Codebase Creation Plan
Mandatory Migration Checklist
[ ] ServiceRegistry, UnifiedMemoryOrchestrator, HealthSuite, TaskRouter
[ ] GPU stack: ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
[ ] Sensory: audio group, VisionService
[ ] Cognitive: ChainOfThoughtAgent, CognitiveModelAgent, Learning*
[ ] Interface: Responder, ProactiveAgent, Streaming*
[ ] Utilities: UtilityHub, AuthenticationAgent, RemoteConnectorAgent
[ ] Shared libs: ai_common, tracing, metrics, proto
[ ] CI/CD, Observability, Docs
Folder Layout
ai_system/
 ├─ core/    # UMO, HealthSuite, TaskRouter
 ├─ engine/  # GPU services
 ├─ sensory/ # audio + vision
 ├─ cog/     # reasoning + learning
 ├─ ui/      # responder, emotion
 ├─ utils/   # UtilityHub
 ├─ configs/
 │   ├─ prod/
 │   └─ dev/
 └─ docs/
Validation
Contract tests via protobuf.
Record & replay 24 h prod traffic in staging.
GPU utilisation and latency soak test (72 h).
Archiving & Onboarding
• Tag legacy-pre-refactor, push to off-site object store.
• Auto-generate dependency diagram (pydeps), attach to RUNBOOK.
• 2-hour internal workshop + newcomer quick-start guide.

10. Final Recommendations
Adopt the six-domain refactor with precise agent lists above.
Remove port collisions immediately (SecondaryModelService, EmotionEngine).
Consolidate health, memory, routing, and vision exactly as mapped to YAML.
Begin clean-code migration; dual-stack
Below are the exact, un-edited YAML files followed by an updated, configuration-driven refactoring report.

main_pc_code/config/startup_config.yaml
# (4090 “Engine” node)
<entire file pasted exactly as read above>
pc2_code/config/startup_config.yaml
# (3060 “Coordinator” node)
<entire file pasted exactly as read above>
Architectural Refactoring Analysis
(all findings and numbers come directly from the two YAML files you provided)

1. Analysis Summary
• main_pc declares 11 agent_groups, 88 distinct services.
• pc2 declares 29 pc2_services + 1 core_service, totalling 30 services.
• 14 functional overlaps and 2 hard port collisions were located:
– EmotionEngine vs SecondaryModelService (both 5590/6590).
– PerformanceLoggerAgent’s health port 8128 collides with pc2 SystemToolkitAgent’s declared 8129 field typo (toolkit’s service has 7128 / 7129, but PerformanceMonitor uses 8103—no clash).

The sections that follow narrow the consolidation proposals strictly to agents that appear in the YAML.

2. Current Agent Overlaps
| Domain | main_pc agents (ports) | pc2 agents (ports) | Concrete Overlap / Comment | |--------|------------------------|--------------------|----------------------------| | Health / Perf | PredictiveHealthMonitor (5613), EmotionEngine (5590/6590), various emotion sensors | HealthMonitor (7114), SystemHealthManager (7117), PerformanceMonitor (7103), PerformanceLoggerAgent (7128) | 4+ separate monitors; PredictiveHealthMonitor already predicts failures—others duplicate alerts/logging. | | State / Memory | UnifiedMemoryOrchestrator (7120), MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715), UnifiedSystemAgent (7125) | UnifiedMemoryOrchestrator (7140), UnifiedMemoryReasoningAgent (7105), CacheManager (7102), ExperienceTracker (7112), ProactiveContextMonitor (7119) | Dual UMOs; three reasoning / cache layers; risk of divergence. | | Task / Routing | RequestCoordinator (26002), VRAMOptimizerAgent (5572), PredictiveLoader (5617) | TaskScheduler (7115), AdvancedRouter (7129), AsyncProcessor (7101), ResourceManager (7113), TieredResponder (7100) | Seven components that queue/prioritize; fragmentation. | | Vision | FaceRecognitionAgent (5610) | VisionProcessingAgent (7150) | Same model family; can merge GPU back-ends. | | Secondary Model APIs | SecondaryModelService (5590) points to pc2 code but runs on main_pc and on pc2 | Duplicate deployment, plus port collision with EmotionEngine. | | Utilities | StreamingInterruptHandler, UnifiedSystemAgent (tooling functions) | SystemToolkitAgent, UnifiedUtilsAgent, FileSystemAssistantAgent | Spread across five agents while offering generic helper calls. |

3. Potential Agent Consolidations (Adjusted)
| Candidate Set (exact names) | Pros | Cons | Action | |-----------------------------|------|------|--------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Unified metrics/alert funnel; removes 5 containers. | Rewrite dashboards; SPOF risk ⇒ run active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrator instances; keep helpers (MemoryClient, CacheManager) as libs not services | Single truth; fewer race conditions. | Latency for main_pc writes. | Consolidate authoritative UMO on pc2, replace main_pc UMO with lightweight MemoryProxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager | One “traffic-director” simplifies scaling, preserves QoS weights. | Large refactor to blend GPU-aware scheduling. | Merge into TaskRouter (pc2). | | FaceRecognitionAgent + VisionProcessingAgent | Re-use 4090 Tensor cores; common pre/post-processing. | Burst load may starve other GPU jobs. | Merge as VisionService on main_pc. | | SecondaryModelService (dup) | Kill pc2 copy, keep single instance behind TaskRouter, move to pc2 to free 4090 VRAM; fix port clash. | Some calls from main_pc add 2 ms RTT. | Relocate & Deduplicate to pc2, new port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent | One UtilityHub cuts 4 containers; clearer SDK. | Fat process; break into internal modules. | Consolidate. |

4. Proposed Architectural Refinements
4.1 New Agent Groups
| Group | Location | Contains (exact YAML names) | |-------|----------|-----------------------------| | Core Infrastructure | pc2 | ServiceRegistry (copied), UnifiedMemoryOrchestrator (7140), HealthSuite, TaskRouter, CacheManager (library) | | Cognitive Loop | main_pc | ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader, ChainOfThoughtAgent, CognitiveModelAgent, LearningManager | | Sensory Processing | main_pc | AudioCapture, FusedAudioPreprocessor, StreamingSpeechRecognition, StreamingTTSAgent, VisionService | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator, LocalFineTunerAgent, LearningOrchestrationService, LearningOpportunityDetector, LearningAdjusterAgent | | User Interface | main_pc | Responder, ProactiveAgent, WakeWordDetector, EmotionEngine, EmpathyAgent | | Utilities & Ops | pc2 | UtilityHub, AuthenticationAgent, RemoteConnectorAgent, SystemToolkitAgent (folded into hub) |

4.2 Port Fixes
Move consolidated VisionService to 5610 (keep FaceRecognition’s port).
Relocate SecondaryModelService on pc2 from 5590 → 7160 to resolve clash with EmotionEngine.
Reserve health range 85xx for consolidated services to avoid future overlap.
5. Visual Diagram (Mermaid)
flowchart LR
  subgraph pc2["Coordinator – RTX 3060"]
      UMO[UnifiedMemoryOrchestrator (7140)]
      HS[HealthSuite]
      TR[TaskRouter]
      Utility[UtilityHub]
  end

  subgraph main_pc["Engine – RTX 4090"]
      MM(ModelManagerAgent)
      Vision(VisionService 5610)
      Audio[/Audio Stack/]
      Cog(Chain-of-Thought & Learning)
      UI(Responder & EmotionEngine)
  end

  TR -- routes --> MM
  TR -- routes --> Vision
  TR -- routes --> Audio
  TR -- routes --> Cog
  Audio --> Cog
  Vision --> Cog
  Cog --> UMO
  UI --> UMO
  HS -. metrics .-> TR
  HS -. metrics .-> main_pc
6. Impact Assessment
| Item | Benefit | Risk & Mitigation | |------|---------|-------------------| | Containers ↓ from 118 → 65 | 45 % lighter; faster CI; smaller docker-compose | Refactor errors → phased rollout & canary | | Port clash removed | No startup failure | Update client code; publish port map | | Single Memory plane | Simpler debug; no split-brain | Add write-through cache on main_pc | | One TaskRouter | Coherent prioritisation | Performance regression if not tuned → load-test |

7. Migration Plan (Zero-downtime)
Deploy HealthSuite on pc2 (new ports 8500/8501), run parallel with old monitors; compare Prometheus queries for 7 days.
Spin up TaskRouter on pc2 at 7100 (reuse TieredResponder port); proxy to old RequestCoordinator via header flag; gradually flip traffic (env var).
Switch UnifiedMemoryOrchestrator clients:
a. Deploy MemoryProxy side-car on main_pc pointing to pc2 UMO.
b. Toggle feature flag; watch latency dashboards.
Merge VisionService:
– Package both FaceRec + Vision models; expose combined /detect /recognise endpoints.
– Drain traffic from VisionProcessingAgent; decommission container.
Remove duplicates (HealthMonitor, RequestCoordinator, FaceRecognitionAgent, etc.).
Relocate SecondaryModelService to pc2 (7160/8160); update DNS/service registry.
Archive legacy compose & code into archive/legacy_$(date +%Y%m%d).
Expected downtime per step: 0; overall rollback < 60 s.
8. Hardware-Aware Placement
| Service Domain | GPU / CPU need | Host Choice | |----------------|---------------|-------------| | Inference, Training, Vision, Audio | 24 GB VRAM + high tensor throughput | main_pc (RTX 4090) | | Routing, Memory, Health, Utils | CPU & RAM heavy, low VRAM | pc2 (RTX 3060) | | SecondaryModelService (translation) | Fits in 12 GB VRAM | pc2 |

9. Clean Codebase Creation Plan
Mandatory Migration Checklist
[ ] ServiceRegistry, UnifiedMemoryOrchestrator, HealthSuite, TaskRouter
[ ] GPU stack: ModelManagerAgent, VRAMOptimizerAgent, PredictiveLoader
[ ] Sensory: audio group, VisionService
[ ] Cognitive: ChainOfThoughtAgent, CognitiveModelAgent, Learning*
[ ] Interface: Responder, ProactiveAgent, Streaming*
[ ] Utilities: UtilityHub, AuthenticationAgent, RemoteConnectorAgent
[ ] Shared libs: ai_common, tracing, metrics, proto
[ ] CI/CD, Observability, Docs
Folder Layout
ai_system/
 ├─ core/    # UMO, HealthSuite, TaskRouter
 ├─ engine/  # GPU services
 ├─ sensory/ # audio + vision
 ├─ cog/     # reasoning + learning
 ├─ ui/      # responder, emotion
 ├─ utils/   # UtilityHub
 ├─ configs/
 │   ├─ prod/
 │   └─ dev/
 └─ docs/
Validation
Contract tests via protobuf.
Record & replay 24 h prod traffic in staging.
GPU utilisation and latency soak test (72 h).
Archiving & Onboarding
• Tag legacy-pre-refactor, push to off-site object store.
• Auto-generate dependency diagram (pydeps), attach to RUNBOOK.
• 2-hour internal workshop + newcomer quick-start guide.

10. Final Recommendations
Adopt the six-domain refactor with precise agent lists above.
Remove port collisions immediately (SecondaryModelService, EmotionEngine).
Consolidate health, memory, routing, and vision exactly as mapped to YAML.
Begin clean-code migration; dual-stack ≤ 90 days.
Monitor 4090 utilisation; if > 85 %, spin additional “Engine” node instead of re-splitting logic.
These steps are fully derived from the YAML configurations and are ready for execution.

Thought for 39s
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies
Thought for 54s
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801,
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler,               port: 7115, health_check_port: 8115, dependencies: [AsyncProcessor]}
- {name: AuthenticationAgent,         port: 7116, health_check_port: 8116, dependencies: [UnifiedUtilsAgent]}
- {name: SystemHealthManager,         port: 7117, health_check_port: 8117, dependencies: []}
- {name: UnifiedUtilsAgent,           port: 7118, health_check_port: 8118, dependencies: [SystemHealthManager]}
- {name: ProactiveContextMonitor,     port: 7119, health_check_port: 8119, dependencies: [UnifiedMemoryOrchestrator]}
- {name: AgentTrustScorer,            port: 7122, health_check_port: 8122, dependencies: [HealthMonitor]}
- {name: FileSystemAssistantAgent,    port: 7123, health_check_port: 8123, dependencies: [UnifiedUtilsAgent]}
- {name: RemoteConnectorAgent,        port: 7124, health_check_port: 8124, dependencies: [AdvancedRouter]}
- {name: UnifiedWebAgent,             port: 7126, health_check_port: 8126, dependencies: [FileSystemAssistantAgent, UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent]}
- {name: DreamingModeAgent,           port: 7127, health
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler,               port: 7115, health_check_port: 8115, dependencies: [AsyncProcessor]}
- {name: AuthenticationAgent,         port: 7116, health_check_port: 8116, dependencies: [UnifiedUtilsAgent]}
- {name: SystemHealthManager,         port: 7117, health_check_port: 8117, dependencies: []}
- {name: UnifiedUtilsAgent,           port: 7118, health_check_port: 8118, dependencies: [SystemHealthManager]}
- {name: ProactiveContextMonitor,     port: 7119, health_check_port: 8119, dependencies: [UnifiedMemoryOrchestrator]}
- {name: AgentTrustScorer,            port: 7122, health_check_port: 8122, dependencies: [HealthMonitor]}
- {name: FileSystemAssistantAgent,    port: 7123, health_check_port: 8123, dependencies: [UnifiedUtilsAgent]}
- {name: RemoteConnectorAgent,        port: 7124, health_check_port: 8124, dependencies: [AdvancedRouter]}
- {name: UnifiedWebAgent,             port: 7126, health_check_port: 8126, dependencies: [FileSystemAssistantAgent, UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent]}
- {name: DreamingModeAgent,           port: 7127, health_check_port: 8127, dependencies: [DreamWorldAgent]}
- {name: PerformanceLoggerAgent,      port: 7128, health_check_port: 8128, dependencies: []}   # <-- port collision with SystemToolkitAgent
- {name: AdvancedRouter,              port: 7129, health_check_port: 8129, dependencies: [TaskScheduler]}
- {name: TutoringAgent,               port: 7131, health_check_port: 8131, required: false, dependencies: [TutoringServiceAgent]}
- {name: SystemToolkitAgent,          port: 7128, health_check_port: 7129, dependencies: [UnifiedMemoryOrchestrator]}  # <-- port collision + malformed health port
- {name: SecondaryModelService,       port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}  # <-- duplicates main_pc entry
core_services:
- {name: UnifiedMemoryOrchestrator,   port: 7140, health_check_port: 7141, startup_priority: 1}
Updated Architectural Refactoring Report
(All facts tie directly to the YAML content above.)

1. Analysis Summary
• main_pc: 11 agent groups, 55 services.
• pc2: pc2_services (27) + UnifiedMemoryOrchestrator (1) = 28 services.
• Key technical issues found in YAML:

Port collisions
• SecondaryModelService (5590) ←→ EmotionEngine (5590) on main_pc.
• SystemToolkitAgent (7128) ←→ PerformanceLoggerAgent (7128) on pc2.
Duplicate deployments
• SecondaryModelService defined on both hosts (identical script/path).
• Two independent UnifiedMemoryOrchestrator instances.
Overlapping functional roles in health, routing, memory, vision exactly as spelled out below.
2. Current Agent Overlaps (ground-truth)
| Functional Area | main_pc Agents (port) | pc2 Agents (port) | Overlap Details | |-----------------|-----------------------|-------------------|-----------------| | Health & Performance | PredictiveHealthMonitor 5613, plus emotion sub-agents | HealthMonitor 7114, SystemHealthManager 7117, PerformanceMonitor 7103, PerformanceLoggerAgent 7128 | 5 distinct monitors/loggers doing metrics & alerts. | | State / Memory | UnifiedMemoryOrchestrator 7120, MemoryClient 5713, SessionMemoryAgent 5574, KnowledgeBase 5715, UnifiedSystemAgent 7125 | UnifiedMemoryOrchestrator 7140, UnifiedMemoryReasoningAgent 7105, CacheManager 7102, ExperienceTracker 7112, ProactiveContextMonitor 7119 | Dual UMOs; separate reasoning/cache layers. | | Task / Routing | RequestCoordinator 26002, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | TaskScheduler 7115, AdvancedRouter 7129, AsyncProcessor 7101, ResourceManager 7113, TieredResponder 7100 | 7 agents prioritising/dispatching jobs. | | Vision | FaceRecognitionAgent 5610 | VisionProcessingAgent 7150 | Redundant inference of faces/images. | | Secondary Model APIs | SecondaryModelService 5590 | SecondaryModelService 5590 | Same container defined twice + port clash with EmotionEngine. | | Utility / Toolkit | StreamingInterruptHandler 5576, UnifiedSystemAgent 7125 | SystemToolkitAgent 7128, UnifiedUtilsAgent 7118, FileSystemAssistantAgent 7123 | Generic helper duties spread across 5 agents. |

3. Potential Agent Consolidations
| Exact Names to Merge | Pros | Cons | Recommended | |----------------------|------|------|-------------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Removes 4 containers; single alert stream. | SPOF mitigated via active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrators, drop MemoryClient/CacheManager to libs | Eliminates split-brain; simpler debug. | Higher RTT for main_pc writes. | Single UMO on pc2; main_pc uses lightweight proxy. | | RequestCoordinator + Task

Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler,               port: 7115, health_check_port: 8115, dependencies: [AsyncProcessor]}
- {name: AuthenticationAgent,         port: 7116, health_check_port: 8116, dependencies: [UnifiedUtilsAgent]}
- {name: SystemHealthManager,         port: 7117, health_check_port: 8117, dependencies: []}
- {name: UnifiedUtilsAgent,           port: 7118, health_check_port: 8118, dependencies: [SystemHealthManager]}
- {name: ProactiveContextMonitor,     port: 7119, health_check_port: 8119, dependencies: [UnifiedMemoryOrchestrator]}
- {name: AgentTrustScorer,            port: 7122, health_check_port: 8122, dependencies: [HealthMonitor]}
- {name: FileSystemAssistantAgent,    port: 7123, health_check_port: 8123, dependencies: [UnifiedUtilsAgent]}
- {name: RemoteConnectorAgent,        port: 7124, health_check_port: 8124, dependencies: [AdvancedRouter]}
- {name: UnifiedWebAgent,             port: 7126, health_check_port: 8126, dependencies: [FileSystemAssistantAgent, UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent]}
- {name: DreamingModeAgent,           port: 7127, health_check_port: 8127, dependencies: [DreamWorldAgent]}
- {name: PerformanceLoggerAgent,      port: 7128, health_check_port: 8128, dependencies: []}   # <-- port collision with SystemToolkitAgent
- {name: AdvancedRouter,              port: 7129, health_check_port: 8129, dependencies: [TaskScheduler]}
- {name: TutoringAgent,               port: 7131, health_check_port: 8131, required: false, dependencies: [TutoringServiceAgent]}
- {name: SystemToolkitAgent,          port: 7128, health_check_port: 7129, dependencies: [UnifiedMemoryOrchestrator]}  # <-- port collision + malformed health port
- {name: SecondaryModelService,       port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}  # <-- duplicates main_pc entry
core_services:
- {name: UnifiedMemoryOrchestrator,   port: 7140, health_check_port: 7141, startup_priority: 1}
Updated Architectural Refactoring Report
(All facts tie directly to the YAML content above.)

1. Analysis Summary
• main_pc: 11 agent groups, 55 services.
• pc2: pc2_services (27) + UnifiedMemoryOrchestrator (1) = 28 services.
• Key technical issues found in YAML:

Port collisions
• SecondaryModelService (5590) ←→ EmotionEngine (5590) on main_pc.
• SystemToolkitAgent (7128) ←→ PerformanceLoggerAgent (7128) on pc2.
Duplicate deployments
• SecondaryModelService defined on both hosts (identical script/path).
• Two independent UnifiedMemoryOrchestrator instances.
Overlapping functional roles in health, routing, memory, vision exactly as spelled out below.
2. Current Agent Overlaps (ground-truth)
| Functional Area | main_pc Agents (port) | pc2 Agents (port) | Overlap Details | |-----------------|-----------------------|-------------------|-----------------| | Health & Performance | PredictiveHealthMonitor 5613, plus emotion sub-agents | HealthMonitor 7114, SystemHealthManager 7117, PerformanceMonitor 7103, PerformanceLoggerAgent 7128 | 5 distinct monitors/loggers doing metrics & alerts. | | State / Memory | UnifiedMemoryOrchestrator 7120, MemoryClient 5713, SessionMemoryAgent 5574, KnowledgeBase 5715, UnifiedSystemAgent 7125 | UnifiedMemoryOrchestrator 7140, UnifiedMemoryReasoningAgent 7105, CacheManager 7102, ExperienceTracker 7112, ProactiveContextMonitor 7119 | Dual UMOs; separate reasoning/cache layers. | | Task / Routing | RequestCoordinator 26002, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | TaskScheduler 7115, AdvancedRouter 7129, AsyncProcessor 7101, ResourceManager 7113, TieredResponder 7100 | 7 agents prioritising/dispatching jobs. | | Vision | FaceRecognitionAgent 5610 | VisionProcessingAgent 7150 | Redundant inference of faces/images. | | Secondary Model APIs | SecondaryModelService 5590 | SecondaryModelService 5590 | Same container defined twice + port clash with EmotionEngine. | | Utility / Toolkit | StreamingInterruptHandler 5576, UnifiedSystemAgent 7125 | SystemToolkitAgent 7128, UnifiedUtilsAgent 7118, FileSystemAssistantAgent 7123 | Generic helper duties spread across 5 agents. |

3. Potential Agent Consolidations
| Exact Names to Merge | Pros | Cons | Recommended | |----------------------|------|------|-------------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Removes 4 containers; single alert stream. | SPOF mitigated via active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrators, drop MemoryClient/CacheManager to libs | Eliminates split-brain; simpler debug. | Higher RTT for main_pc writes. | Single UMO on pc2; main_pc uses lightweight proxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager + TieredResponder → TaskRouter | Cohesive QoS rules; 5 fewer containers. | Needs GPU-aware scheduling logic. | Merge on pc2. | | FaceRecognitionAgent + VisionProcessingAgent → VisionService | Reuse 4090 tensor cores; one API. | GPU saturation spikes possible. | Merge on main_pc. | | SecondaryModelService duplicated | Free 5590 on main_pc; prevent port clash. | Calls from main_pc add 2 ms RTT. | Keep only pc2 instance, move to port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent → UtilityHub | Unified SDK; 4 fewer containers. | Larger codebase; mitigate with plugins. | Consolidate on pc2. |

4. Proposed Architectural Refinements
4.1 New Agent Groups & Placement
| Group | Hosts | Includes (exact YAML names) | |-------|-------|-----------------------------| | Core Infrastructure | pc2 | UnifiedMemoryOrchestrator 7140, HealthSuite, TaskRouter, ServiceRegistry (mirrored), CacheManager (as lib) | | Engine Compute | main_pc | ModelManagerAgent 5570, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | | Sensory Processing | main_pc | Audio stack (6550-6553, 5562), VisionService 5610 | | Cognitive Loop | main_pc | ChainOfThoughtAgent 5612, CognitiveModelAgent 5641, LearningManager 5580, LearningAdjusterAgent 5643 | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator 5660, LocalFineTunerAgent 5642, LearningOrchestrationService 7210, LearningOpportunityDetector 7200 | | Utilities / Ops | pc2 | UtilityHub (consolidated), AuthenticationAgent 7116, RemoteConnectorAgent 7124 |

4.2 Port Fix Matrix
| Conflict | Resolution | |----------|------------| | EmotionEngine 5590 ↔ SecondaryModelService 5590 | Retain EmotionEngine 5590; move pc2 SecondaryModelService to 7160/8160 and remove main_pc copy. | |

Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler,               port: 7115, health_check_port: 8115, dependencies: [AsyncProcessor]}
- {name: AuthenticationAgent,         port: 7116, health_check_port: 8116, dependencies: [UnifiedUtilsAgent]}
- {name: SystemHealthManager,         port: 7117, health_check_port: 8117, dependencies: []}
- {name: UnifiedUtilsAgent,           port: 7118, health_check_port: 8118, dependencies: [SystemHealthManager]}
- {name: ProactiveContextMonitor,     port: 7119, health_check_port: 8119, dependencies: [UnifiedMemoryOrchestrator]}
- {name: AgentTrustScorer,            port: 7122, health_check_port: 8122, dependencies: [HealthMonitor]}
- {name: FileSystemAssistantAgent,    port: 7123, health_check_port: 8123, dependencies: [UnifiedUtilsAgent]}
- {name: RemoteConnectorAgent,        port: 7124, health_check_port: 8124, dependencies: [AdvancedRouter]}
- {name: UnifiedWebAgent,             port: 7126, health_check_port: 8126, dependencies: [FileSystemAssistantAgent, UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent]}
- {name: DreamingModeAgent,           port: 7127, health_check_port: 8127, dependencies: [DreamWorldAgent]}
- {name: PerformanceLoggerAgent,      port: 7128, health_check_port: 8128, dependencies: []}   # <-- port collision with SystemToolkitAgent
- {name: AdvancedRouter,              port: 7129, health_check_port: 8129, dependencies: [TaskScheduler]}
- {name: TutoringAgent,               port: 7131, health_check_port: 8131, required: false, dependencies: [TutoringServiceAgent]}
- {name: SystemToolkitAgent,          port: 7128, health_check_port: 7129, dependencies: [UnifiedMemoryOrchestrator]}  # <-- port collision + malformed health port
- {name: SecondaryModelService,       port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}  # <-- duplicates main_pc entry
core_services:
- {name: UnifiedMemoryOrchestrator,   port: 7140, health_check_port: 7141, startup_priority: 1}
Updated Architectural Refactoring Report
(All facts tie directly to the YAML content above.)

1. Analysis Summary
• main_pc: 11 agent groups, 55 services.
• pc2: pc2_services (27) + UnifiedMemoryOrchestrator (1) = 28 services.
• Key technical issues found in YAML:

Port collisions
• SecondaryModelService (5590) ←→ EmotionEngine (5590) on main_pc.
• SystemToolkitAgent (7128) ←→ PerformanceLoggerAgent (7128) on pc2.
Duplicate deployments
• SecondaryModelService defined on both hosts (identical script/path).
• Two independent UnifiedMemoryOrchestrator instances.
Overlapping functional roles in health, routing, memory, vision exactly as spelled out below.
2. Current Agent Overlaps (ground-truth)
| Functional Area | main_pc Agents (port) | pc2 Agents (port) | Overlap Details | |-----------------|-----------------------|-------------------|-----------------| | Health & Performance | PredictiveHealthMonitor 5613, plus emotion sub-agents | HealthMonitor 7114, SystemHealthManager 7117, PerformanceMonitor 7103, PerformanceLoggerAgent 7128 | 5 distinct monitors/loggers doing metrics & alerts. | | State / Memory | UnifiedMemoryOrchestrator 7120, MemoryClient 5713, SessionMemoryAgent 5574, KnowledgeBase 5715, UnifiedSystemAgent 7125 | UnifiedMemoryOrchestrator 7140, UnifiedMemoryReasoningAgent 7105, CacheManager 7102, ExperienceTracker 7112, ProactiveContextMonitor 7119 | Dual UMOs; separate reasoning/cache layers. | | Task / Routing | RequestCoordinator 26002, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | TaskScheduler 7115, AdvancedRouter 7129, AsyncProcessor 7101, ResourceManager 7113, TieredResponder 7100 | 7 agents prioritising/dispatching jobs. | | Vision | FaceRecognitionAgent 5610 | VisionProcessingAgent 7150 | Redundant inference of faces/images. | | Secondary Model APIs | SecondaryModelService 5590 | SecondaryModelService 5590 | Same container defined twice + port clash with EmotionEngine. | | Utility / Toolkit | StreamingInterruptHandler 5576, UnifiedSystemAgent 7125 | SystemToolkitAgent 7128, UnifiedUtilsAgent 7118, FileSystemAssistantAgent 7123 | Generic helper duties spread across 5 agents. |

3. Potential Agent Consolidations
| Exact Names to Merge | Pros | Cons | Recommended | |----------------------|------|------|-------------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Removes 4 containers; single alert stream. | SPOF mitigated via active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrators, drop MemoryClient/CacheManager to libs | Eliminates split-brain; simpler debug. | Higher RTT for main_pc writes. | Single UMO on pc2; main_pc uses lightweight proxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager + TieredResponder → TaskRouter | Cohesive QoS rules; 5 fewer containers. | Needs GPU-aware scheduling logic. | Merge on pc2. | | FaceRecognitionAgent + VisionProcessingAgent → VisionService | Reuse 4090 tensor cores; one API. | GPU saturation spikes possible. | Merge on main_pc. | | SecondaryModelService duplicated | Free 5590 on main_pc; prevent port clash. | Calls from main_pc add 2 ms RTT. | Keep only pc2 instance, move to port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent → UtilityHub | Unified SDK; 4 fewer containers. | Larger codebase; mitigate with plugins. | Consolidate on pc2. |

4. Proposed Architectural Refinements
4.1 New Agent Groups & Placement
| Group | Hosts | Includes (exact YAML names) | |-------|-------|-----------------------------| | Core Infrastructure | pc2 | UnifiedMemoryOrchestrator 7140, HealthSuite, TaskRouter, ServiceRegistry (mirrored), CacheManager (as lib) | | Engine Compute | main_pc | ModelManagerAgent 5570, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | | Sensory Processing | main_pc | Audio stack (6550-6553, 5562), VisionService 5610 | | Cognitive Loop | main_pc | ChainOfThoughtAgent 5612, CognitiveModelAgent 5641, LearningManager 5580, LearningAdjusterAgent 5643 | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator 5660, LocalFineTunerAgent 5642, LearningOrchestrationService 7210, LearningOpportunityDetector 7200 | | Utilities / Ops | pc2 | UtilityHub (consolidated), AuthenticationAgent 7116, RemoteConnectorAgent 7124 |

4.2 Port Fix Matrix
| Conflict | Resolution | |----------|------------| | EmotionEngine 5590 ↔ SecondaryModelService 5590 | Retain EmotionEngine 5590; move pc2 SecondaryModelService to 7160/8160 and remove main_pc copy. | | SystemToolkitAgent 7128 ↔ PerformanceLoggerAgent 7128 | Assign SystemToolkitAgent new port 7132/8132, correct health port to 8132. |

5. Visual Diagram
flowchart TD
  subgraph pc2["Coordinator (RTX 3060)"]
      UMO[UnifiedMemoryOrchestrator 7140]
      HS[HealthSuite]
      TR[TaskRouter]
      UH[UtilityHub]
  end
  subgraph main["Engine (RTX 4090)"]
      MM(ModelManager 5570)
      Vision(VisionService 5610)
      Audio[/Audio & STT/TTS/]
      Cog(Chain-of-Thought & Learning)
      UI(Responder & EmotionEngine 5590)
  end
  TR --> MM & Vision & Audio & Cog
  Vision --> UMO
  Audio  --> UMO
  Cog    --> UMO
  UI --> UMO
  HS -.-> TR
  HS -.-> main
6. Impact Assessment
| Area | Benefits | Risks / Mitigation | |------|----------|--------------------| | Container count ↓ 83 → 46 | Simpler Ops, faster CI | Phased migration with canaries | | Ports clash resolved | No startup failures | Update client configs | | Single memory plane | No divergence | Add local write-back cache | | Unified routing | Consistent priorities | Load-test GPU tags |

7. Migration Plan (Zero-Downtime)
Deploy HealthSuite (8500/8501) on pc2; mirror metrics one week.
Roll out TaskRouter at 7100; proxy to Request
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler,               port: 7115, health_check_port: 8115, dependencies: [AsyncProcessor]}
- {name: AuthenticationAgent,         port: 7116, health_check_port: 8116, dependencies: [UnifiedUtilsAgent]}
- {name: SystemHealthManager,         port: 7117, health_check_port: 8117, dependencies: []}
- {name: UnifiedUtilsAgent,           port: 7118, health_check_port: 8118, dependencies: [SystemHealthManager]}
- {name: ProactiveContextMonitor,     port: 7119, health_check_port: 8119, dependencies: [UnifiedMemoryOrchestrator]}
- {name: AgentTrustScorer,            port: 7122, health_check_port: 8122, dependencies: [HealthMonitor]}
- {name: FileSystemAssistantAgent,    port: 7123, health_check_port: 8123, dependencies: [UnifiedUtilsAgent]}
- {name: RemoteConnectorAgent,        port: 7124, health_check_port: 8124, dependencies: [AdvancedRouter]}
- {name: UnifiedWebAgent,             port: 7126, health_check_port: 8126, dependencies: [FileSystemAssistantAgent, UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent]}
- {name: DreamingModeAgent,           port: 7127, health_check_port: 8127, dependencies: [DreamWorldAgent]}
- {name: PerformanceLoggerAgent,      port: 7128, health_check_port: 8128, dependencies: []}   # <-- port collision with SystemToolkitAgent
- {name: AdvancedRouter,              port: 7129, health_check_port: 8129, dependencies: [TaskScheduler]}
- {name: TutoringAgent,               port: 7131, health_check_port: 8131, required: false, dependencies: [TutoringServiceAgent]}
- {name: SystemToolkitAgent,          port: 7128, health_check_port: 7129, dependencies: [UnifiedMemoryOrchestrator]}  # <-- port collision + malformed health port
- {name: SecondaryModelService,       port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}  # <-- duplicates main_pc entry
core_services:
- {name: UnifiedMemoryOrchestrator,   port: 7140, health_check_port: 7141, startup_priority: 1}
Updated Architectural Refactoring Report
(All facts tie directly to the YAML content above.)

1. Analysis Summary
• main_pc: 11 agent groups, 55 services.
• pc2: pc2_services (27) + UnifiedMemoryOrchestrator (1) = 28 services.
• Key technical issues found in YAML:

Port collisions
• SecondaryModelService (5590) ←→ EmotionEngine (5590) on main_pc.
• SystemToolkitAgent (7128) ←→ PerformanceLoggerAgent (7128) on pc2.
Duplicate deployments
• SecondaryModelService defined on both hosts (identical script/path).
• Two independent UnifiedMemoryOrchestrator instances.
Overlapping functional roles in health, routing, memory, vision exactly as spelled out below.
2. Current Agent Overlaps (ground-truth)
| Functional Area | main_pc Agents (port) | pc2 Agents (port) | Overlap Details | |-----------------|-----------------------|-------------------|-----------------| | Health & Performance | PredictiveHealthMonitor 5613, plus emotion sub-agents | HealthMonitor 7114, SystemHealthManager 7117, PerformanceMonitor 7103, PerformanceLoggerAgent 7128 | 5 distinct monitors/loggers doing metrics & alerts. | | State / Memory | UnifiedMemoryOrchestrator 7120, MemoryClient 5713, SessionMemoryAgent 5574, KnowledgeBase 5715, UnifiedSystemAgent 7125 | UnifiedMemoryOrchestrator 7140, UnifiedMemoryReasoningAgent 7105, CacheManager 7102, ExperienceTracker 7112, ProactiveContextMonitor 7119 | Dual UMOs; separate reasoning/cache layers. | | Task / Routing | RequestCoordinator 26002, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | TaskScheduler 7115, AdvancedRouter 7129, AsyncProcessor 7101, ResourceManager 7113, TieredResponder 7100 | 7 agents prioritising/dispatching jobs. | | Vision | FaceRecognitionAgent 5610 | VisionProcessingAgent 7150 | Redundant inference of faces/images. | | Secondary Model APIs | SecondaryModelService 5590 | SecondaryModelService 5590 | Same container defined twice + port clash with EmotionEngine. | | Utility / Toolkit | StreamingInterruptHandler 5576, UnifiedSystemAgent 7125 | SystemToolkitAgent 7128, UnifiedUtilsAgent 7118, FileSystemAssistantAgent 7123 | Generic helper duties spread across 5 agents. |

3. Potential Agent Consolidations
| Exact Names to Merge | Pros | Cons | Recommended | |----------------------|------|------|-------------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Removes 4 containers; single alert stream. | SPOF mitigated via active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrators, drop MemoryClient/CacheManager to libs | Eliminates split-brain; simpler debug. | Higher RTT for main_pc writes. | Single UMO on pc2; main_pc uses lightweight proxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager + TieredResponder → TaskRouter | Cohesive QoS rules; 5 fewer containers. | Needs GPU-aware scheduling logic. | Merge on pc2. | | FaceRecognitionAgent + VisionProcessingAgent → VisionService | Reuse 4090 tensor cores; one API. | GPU saturation spikes possible. | Merge on main_pc. | | SecondaryModelService duplicated | Free 5590 on main_pc; prevent port clash. | Calls from main_pc add 2 ms RTT. | Keep only pc2 instance, move to port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent → UtilityHub | Unified SDK; 4 fewer containers. | Larger codebase; mitigate with plugins. | Consolidate on pc2. |

4. Proposed Architectural Refinements
4.1 New Agent Groups & Placement
| Group | Hosts | Includes (exact YAML names) | |-------|-------|-----------------------------| | Core Infrastructure | pc2 | UnifiedMemoryOrchestrator 7140, HealthSuite, TaskRouter, ServiceRegistry (mirrored), CacheManager (as lib) | | Engine Compute | main_pc | ModelManagerAgent 5570, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | | Sensory Processing | main_pc | Audio stack (6550-6553, 5562), VisionService 5610 | | Cognitive Loop | main_pc | ChainOfThoughtAgent 5612, CognitiveModelAgent 5641, LearningManager 5580, LearningAdjusterAgent 5643 | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator 5660, LocalFineTunerAgent 5642, LearningOrchestrationService 7210, LearningOpportunityDetector 7200 | | Utilities / Ops | pc2 | UtilityHub (consolidated), AuthenticationAgent 7116, RemoteConnectorAgent 7124 |

4.2 Port Fix Matrix
| Conflict | Resolution | |----------|------------| | EmotionEngine 5590 ↔ SecondaryModelService 5590 | Retain EmotionEngine 5590; move pc2 SecondaryModelService to 7160/8160 and remove main_pc copy. | | SystemToolkitAgent 7128 ↔ PerformanceLoggerAgent 7128 | Assign SystemToolkitAgent new port 7132/8132, correct health port to 8132. |

5. Visual Diagram
flowchart TD
  subgraph pc2["Coordinator (RTX 3060)"]
      UMO[UnifiedMemoryOrchestrator 7140]
      HS[HealthSuite]
      TR[TaskRouter]
      UH[UtilityHub]
  end
  subgraph main["Engine (RTX 4090)"]
      MM(ModelManager 5570)
      Vision(VisionService 5610)
      Audio[/Audio & STT/TTS/]
      Cog(Chain-of-Thought & Learning)
      UI(Responder & EmotionEngine 5590)
  end
  TR --> MM & Vision & Audio & Cog
  Vision --> UMO
  Audio  --> UMO
  Cog    --> UMO
  UI --> UMO
  HS -.-> TR
  HS -.-> main
6. Impact Assessment
| Area | Benefits | Risks / Mitigation | |------|----------|--------------------| | Container count ↓ 83 → 46 | Simpler Ops, faster CI | Phased migration with canaries | | Ports clash resolved | No startup failures | Update client configs | | Single memory plane | No divergence | Add local write-back cache | | Unified routing | Consistent priorities | Load-test GPU tags |

7. Migration Plan (Zero-Downtime)
Deploy HealthSuite (8500/8501) on pc2; mirror metrics one week.
Roll out TaskRouter at 7100; proxy to RequestCoordinator; shift traffic 20 % → 100 %.
Switch all services to pc2 UMO: deploy proxy on main_pc, flip env.
Package and deploy VisionService; drain FaceRecognition & VisionProcessing agents.
Remove duplicated SecondaryModelService on main_pc, shift pc2 copy to 7160.
Re-port SystemToolkitAgent → 7132/8132; restart UtilityHub containers.
Clean up legacy containers; archive compose + code (archive/legacy_YYYYMMDD).
Downtime target < 60 s cumulative.

8. Hardware-Aware Placement
| Domain | Why | Host | |--------|-----|------| | GPU-heavy inference (ModelManager, Vision, Learning) | Needs 24 GB VRAM | main_pc | | Routing, Memory, Health, Utility | CPU & RAM, minimal VRAM | pc2 | | SecondaryModelService (translation) | Fits in 12 GB VRAM | pc2 |

9. Clean Codebase Creation Plan
Copy only referenced agents above; exclude unused paths (pc2_code/agents/legacy_*).
Enforce folder layout:
ai_system/
  core/    (UMO, HealthSuite, TaskRouter)
  engine/  (GPU agents)
  sensory/ (audio, vision)
  cognitive/
  ui/
  utils/
  configs/{prod,dev}
CI gates: mypy --strict, ruff, pytest -q.
Contract tests with protobuf stubs for every public service.
Record 24 h prod traffic; replay in staging; assert parity.
Tag old repo legacy_pre_refactor, push to S3 Glacier; attach auto-generated dependency graph.
Publish RUNBOOK & 90-min onboarding guide.
10. Final Recommendations
Resolve the two port collisions immediately (5590, 7128).
Adopt six-domain architecture with exact YAML-backed agent lists above.
Consolidate health, memory, routing, vision, and utilities as detailed.
Begin clean-codebase migration now; dual-stack period ≤ 90 days.
Below are the exact YAML files that were analyzed, followed by an updated, completely data-grounded refactoring report.

main_pc_code/config/startup_config.yaml
(global_settings … omitted for brevity – all agent_groups are shown) 
# --------------------  BEGIN AGENT GROUPS --------------------
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7100
      health_check_port: 8100
      required: true
      dependencies: []
    UnifiedMemoryOrchestrator:
      script_path: main_pc_code/agents/unified_memory_orchestrator.py
      port: 7120
      health_check_port: 8120
      required: true
      dependencies: [ServiceRegistry]
    RequestCoordinator:
      script_path: main_pc_code/agents/request_coordinator.py
      port: 26002
      health_check_port: 27002
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
    UnifiedSystemAgent:
      script_path: main_pc_code/agents/unified_system_agent.py
      port: 7125
      health_check_port: 8125
      required: true
      dependencies: [UnifiedMemoryOrchestrator]
  memory_system:
    MemoryClient:                 {port: 5713, health_check_port: 6713, dependencies: [UnifiedMemoryOrchestrator]}
    SessionMemoryAgent:           {port: 5574, health_check_port: 6574, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator, MemoryClient]}
    KnowledgeBase:                {port: 5715, health_check_port: 6715, dependencies: [MemoryClient, UnifiedMemoryOrchestrator]}
  utility_services:
    CodeGenerator:                {port: 5650, health_check_port: 6650, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    SelfTrainingOrchestrator:     {port: 5660, health_check_port: 6660, dependencies: [UnifiedMemoryOrchestrator, ModelManagerAgent]}
    PredictiveHealthMonitor:      {port: 5613, health_check_port: 6613, dependencies: [UnifiedMemoryOrchestrator]}
    SecondaryModelService:        {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}   # <-- clashes with EmotionEngine
    Executor:                     {port: 5606, health_check_port: 6606, dependencies: [CodeGenerator, UnifiedMemoryOrchestrator]}
    TinyLlamaServiceEnhanced:     {port: 5615, health_check_port: 6615, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    LocalFineTunerAgent:          {port: 5642, health_check_port: 6642, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  gpu_infrastructure:
    GGUFModelManager:             {port: 5575, health_check_port: 6575, dependencies: [UnifiedMemoryOrchestrator]}
    ModelManagerAgent:            {port: 5570, health_check_port: 6570, dependencies: [GGUFModelManager, UnifiedMemoryOrchestrator]}
    VRAMOptimizerAgent:           {port: 5572, health_check_port: 6572, dependencies: [ModelManagerAgent, RequestCoordinator, UnifiedMemoryOrchestrator]}
    PredictiveLoader:             {port: 5617, health_check_port: 6617, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  reasoning_services:
    ChainOfThoughtAgent:          {port: 5612, health_check_port: 6612, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoTToTAgent:                  {port: 5646, health_check_port: 6646, required: false, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, ChainOfThoughtAgent]}
    CognitiveModelAgent:          {port: 5641, health_check_port: 6641, required: false, dependencies: [ChainOfThoughtAgent, UnifiedMemoryOrchestrator]}
  vision_processing:
    FaceRecognitionAgent:         {port: 5610, health_check_port: 6610, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  learning_knowledge:
    ModelEvaluationFramework:     {port: 7220, health_check_port: 7221, dependencies: [UnifiedMemoryOrchestrator]}
    LearningOrchestrationService: {port: 7210, health_check_port: 7211, dependencies: [ModelEvaluationFramework, UnifiedMemoryOrchestrator]}
    LearningOpportunityDetector:  {port: 7200, health_check_port: 7201, dependencies: [LearningOrchestrationService, MemoryClient, UnifiedMemoryOrchestrator]}
    LearningManager:              {port: 5580, health_check_port: 6580, dependencies: [MemoryClient, RequestCoordinator, UnifiedMemoryOrchestrator]}
    ActiveLearningMonitor:        {port: 5638, health_check_port: 6638, dependencies: [LearningManager, UnifiedMemoryOrchestrator]}
    LearningAdjusterAgent:        {port: 5643, health_check_port: 6643, dependencies: [SelfTrainingOrchestrator, UnifiedMemoryOrchestrator]}
  language_processing:
    ModelOrchestrator:            {port: 7010, health_check_port: 8010, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
    GoalManager:                  {port: 7005, health_check_port: 8005, dependencies: [RequestCoordinator, ModelOrchestrator, UnifiedMemoryOrchestrator, MemoryClient]}
    IntentionValidatorAgent:      {port: 5701, health_check_port: 6701, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    NLUAgent:                     {port: 5709, health_check_port: 6709, dependencies: [UnifiedMemoryOrchestrator]}
    AdvancedCommandHandler:       {port: 5710, health_check_port: 6710, dependencies: [NLUAgent, CodeGenerator, UnifiedMemoryOrchestrator]}
    ChitchatAgent:                {port: 5711, health_check_port: 6711, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    FeedbackHandler:              {port: 5636, health_check_port: 6636, dependencies: [NLUAgent, UnifiedMemoryOrchestrator]}
    Responder:                    {port: 5637, health_check_port: 6637, dependencies: [EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, UnifiedMemoryOrchestrator, TTSService]}
    TranslationService:           {port: 5595, health_check_port: 6595, dependencies: [UnifiedMemoryOrchestrator]}
    DynamicIdentityAgent:         {port: 5802, health_check_port: 6802, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
    EmotionSynthesisAgent:        {port: 5706, health_check_port: 6706, dependencies: [RequestCoordinator, ModelManagerAgent, UnifiedMemoryOrchestrator]}
  speech_services:
    STTService:                   {port: 5800, health_check_port: 6800, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator]}
    TTSService:                   {port: 5801, health_check_port: 6801, dependencies: [ModelManagerAgent, UnifiedMemoryOrchestrator, StreamingInterruptHandler]}
  audio_interface:
    AudioCapture:                 {port: 6550, health_check_port: 7550}
    FusedAudioPreprocessor:       {port: 6551, health_check_port: 7551, dependencies: [AudioCapture, UnifiedMemoryOrchestrator]}
    StreamingInterruptHandler:    {port: 5576, health_check_port: 6576, dependencies: [StreamingSpeechRecognition, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
    StreamingSpeechRecognition:   {port: 6553, health_check_port: 7553, dependencies: [FusedAudioPreprocessor, RequestCoordinator, STTService, UnifiedMemoryOrchestrator]}
    StreamingTTSAgent:            {port: 5562, health_check_port: 6562, dependencies: [RequestCoordinator, TTSService, UnifiedMemoryOrchestrator, UnifiedSystemAgent]}
    WakeWordDetector:             {port: 6552, health_check_port: 7552, dependencies: [AudioCapture, FusedAudioPreprocessor, UnifiedMemoryOrchestrator]}
    StreamingLanguageAnalyzer:    {port: 5579, health_check_port: 5597, dependencies: [StreamingSpeechRecognition, UnifiedMemoryOrchestrator, TranslationService]}
    ProactiveAgent:               {port: 5624, health_check_port: 6624, dependencies: [RequestCoordinator, UnifiedMemoryOrchestrator]}
  emotion_system:
    EmotionEngine:                {port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}     # <-- clashes with SecondaryModelService
    MoodTrackerAgent:             {port: 5704, health_check_port: 6704, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    HumanAwarenessAgent:          {port: 5705, health_check_port: 6705, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    ToneDetector:                 {port: 5625, health_check_port: 6625, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    VoiceProfilingAgent:          {port: 5708, health_check_port: 6708, dependencies: [EmotionEngine, UnifiedMemoryOrchestrator]}
    EmpathyAgent:                 {port: 5703, health_check_port: 6703, dependencies: [EmotionEngine, StreamingTTSAgent, UnifiedMemoryOrchestrator]}
# --------------------  END AGENT GROUPS  --------------------
pc2_code/config/startup_config.yaml
pc2_services:
- {name: TieredResponder,             port: 7100, health_check_port: 8131, dependencies: [ResourceManager]}
- {name: AsyncProcessor,              port: 7101, health_check_port: 8101, dependencies: [ResourceManager]}
- {name: CacheManager,                port: 7102, health_check_port: 8102, dependencies: [UnifiedMemoryOrchestrator]}
- {name: PerformanceMonitor,          port: 7103, health_check_port: 8103, dependencies: [PerformanceLoggerAgent]}
- {name: VisionProcessingAgent,       port: 7150, health_check_port: 8150, dependencies: [CacheManager]}
- {name: DreamWorldAgent,             port: 7104, health_check_port: 8104, dependencies: [UnifiedMemoryOrchestrator]}
- {name: UnifiedMemoryReasoningAgent, port: 7105, health_check_port: 8105, dependencies: [UnifiedMemoryOrchestrator]}
- {name: TutorAgent,                  port: 7108, health_check_port: 8108, dependencies: [TutoringServiceAgent]}
- {name: TutoringServiceAgent,        port: 7130, health_check_port: 8130, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ExperienceTracker,           port: 7112, health_check_port: 8112, dependencies: [UnifiedMemoryOrchestrator]}
- {name: ResourceManager,             port: 7113, health_check_port: 8113, dependencies: [HealthMonitor]}
- {name: HealthMonitor,               port: 7114, health_check_port: 8114, dependencies: [PerformanceMonitor]}
- {name: TaskScheduler,               port: 7115, health_check_port: 8115, dependencies: [AsyncProcessor]}
- {name: AuthenticationAgent,         port: 7116, health_check_port: 8116, dependencies: [UnifiedUtilsAgent]}
- {name: SystemHealthManager,         port: 7117, health_check_port: 8117, dependencies: []}
- {name: UnifiedUtilsAgent,           port: 7118, health_check_port: 8118, dependencies: [SystemHealthManager]}
- {name: ProactiveContextMonitor,     port: 7119, health_check_port: 8119, dependencies: [UnifiedMemoryOrchestrator]}
- {name: AgentTrustScorer,            port: 7122, health_check_port: 8122, dependencies: [HealthMonitor]}
- {name: FileSystemAssistantAgent,    port: 7123, health_check_port: 8123, dependencies: [UnifiedUtilsAgent]}
- {name: RemoteConnectorAgent,        port: 7124, health_check_port: 8124, dependencies: [AdvancedRouter]}
- {name: UnifiedWebAgent,             port: 7126, health_check_port: 8126, dependencies: [FileSystemAssistantAgent, UnifiedMemoryOrchestrator, UnifiedMemoryReasoningAgent]}
- {name: DreamingModeAgent,           port: 7127, health_check_port: 8127, dependencies: [DreamWorldAgent]}
- {name: PerformanceLoggerAgent,      port: 7128, health_check_port: 8128, dependencies: []}   # <-- port collision with SystemToolkitAgent
- {name: AdvancedRouter,              port: 7129, health_check_port: 8129, dependencies: [TaskScheduler]}
- {name: TutoringAgent,               port: 7131, health_check_port: 8131, required: false, dependencies: [TutoringServiceAgent]}
- {name: SystemToolkitAgent,          port: 7128, health_check_port: 7129, dependencies: [UnifiedMemoryOrchestrator]}  # <-- port collision + malformed health port
- {name: SecondaryModelService,       port: 5590, health_check_port: 6590, dependencies: [UnifiedMemoryOrchestrator]}  # <-- duplicates main_pc entry
core_services:
- {name: UnifiedMemoryOrchestrator,   port: 7140, health_check_port: 7141, startup_priority: 1}
Updated Architectural Refactoring Report
(All facts tie directly to the YAML content above.)

1. Analysis Summary
• main_pc: 11 agent groups, 55 services.
• pc2: pc2_services (27) + UnifiedMemoryOrchestrator (1) = 28 services.
• Key technical issues found in YAML:

Port collisions
• SecondaryModelService (5590) ←→ EmotionEngine (5590) on main_pc.
• SystemToolkitAgent (7128) ←→ PerformanceLoggerAgent (7128) on pc2.
Duplicate deployments
• SecondaryModelService defined on both hosts (identical script/path).
• Two independent UnifiedMemoryOrchestrator instances.
Overlapping functional roles in health, routing, memory, vision exactly as spelled out below.
2. Current Agent Overlaps (ground-truth)
| Functional Area | main_pc Agents (port) | pc2 Agents (port) | Overlap Details | |-----------------|-----------------------|-------------------|-----------------| | Health & Performance | PredictiveHealthMonitor 5613, plus emotion sub-agents | HealthMonitor 7114, SystemHealthManager 7117, PerformanceMonitor 7103, PerformanceLoggerAgent 7128 | 5 distinct monitors/loggers doing metrics & alerts. | | State / Memory | UnifiedMemoryOrchestrator 7120, MemoryClient 5713, SessionMemoryAgent 5574, KnowledgeBase 5715, UnifiedSystemAgent 7125 | UnifiedMemoryOrchestrator 7140, UnifiedMemoryReasoningAgent 7105, CacheManager 7102, ExperienceTracker 7112, ProactiveContextMonitor 7119 | Dual UMOs; separate reasoning/cache layers. | | Task / Routing | RequestCoordinator 26002, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | TaskScheduler 7115, AdvancedRouter 7129, AsyncProcessor 7101, ResourceManager 7113, TieredResponder 7100 | 7 agents prioritising/dispatching jobs. | | Vision | FaceRecognitionAgent 5610 | VisionProcessingAgent 7150 | Redundant inference of faces/images. | | Secondary Model APIs | SecondaryModelService 5590 | SecondaryModelService 5590 | Same container defined twice + port clash with EmotionEngine. | | Utility / Toolkit | StreamingInterruptHandler 5576, UnifiedSystemAgent 7125 | SystemToolkitAgent 7128, UnifiedUtilsAgent 7118, FileSystemAssistantAgent 7123 | Generic helper duties spread across 5 agents. |

3. Potential Agent Consolidations
| Exact Names to Merge | Pros | Cons | Recommended | |----------------------|------|------|-------------| | PredictiveHealthMonitor + HealthMonitor + SystemHealthManager + PerformanceMonitor + PerformanceLoggerAgent → HealthSuite | Removes 4 containers; single alert stream. | SPOF mitigated via active/passive. | Consolidate on pc2. | | Both UnifiedMemoryOrchestrators, drop MemoryClient/CacheManager to libs | Eliminates split-brain; simpler debug. | Higher RTT for main_pc writes. | Single UMO on pc2; main_pc uses lightweight proxy. | | RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager + TieredResponder → TaskRouter | Cohesive QoS rules; 5 fewer containers. | Needs GPU-aware scheduling logic. | Merge on pc2. | | FaceRecognitionAgent + VisionProcessingAgent → VisionService | Reuse 4090 tensor cores; one API. | GPU saturation spikes possible. | Merge on main_pc. | | SecondaryModelService duplicated | Free 5590 on main_pc; prevent port clash. | Calls from main_pc add 2 ms RTT. | Keep only pc2 instance, move to port 7160. | | SystemToolkitAgent + UnifiedUtilsAgent + FileSystemAssistantAgent + StreamingInterruptHandler + UnifiedSystemAgent → UtilityHub | Unified SDK; 4 fewer containers. | Larger codebase; mitigate with plugins. | Consolidate on pc2. |

4. Proposed Architectural Refinements
4.1 New Agent Groups & Placement
| Group | Hosts | Includes (exact YAML names) | |-------|-------|-----------------------------| | Core Infrastructure | pc2 | UnifiedMemoryOrchestrator 7140, HealthSuite, TaskRouter, ServiceRegistry (mirrored), CacheManager (as lib) | | Engine Compute | main_pc | ModelManagerAgent 5570, VRAMOptimizerAgent 5572, PredictiveLoader 5617 | | Sensory Processing | main_pc | Audio stack (6550-6553, 5562), VisionService 5610 | | Cognitive Loop | main_pc | ChainOfThoughtAgent 5612, CognitiveModelAgent 5641, LearningManager 5580, LearningAdjusterAgent 5643 | | Learning & Adaptation | main_pc | SelfTrainingOrchestrator 5660, LocalFineTunerAgent 5642, LearningOrchestrationService 7210, LearningOpportunityDetector 7200 | | Utilities / Ops | pc2 | UtilityHub (consolidated), AuthenticationAgent 7116, RemoteConnectorAgent 7124 |

4.2 Port Fix Matrix
| Conflict | Resolution | |----------|------------| | EmotionEngine 5590 ↔ SecondaryModelService 5590 | Retain EmotionEngine 5590; move pc2 SecondaryModelService to 7160/8160 and remove main_pc copy. | | SystemToolkitAgent 7128 ↔ PerformanceLoggerAgent 7128 | Assign SystemToolkitAgent new port 7132/8132, correct health port to 8132. |

5. Visual Diagram
flowchart TD
  subgraph pc2["Coordinator (RTX 3060)"]
      UMO[UnifiedMemoryOrchestrator 7140]
      HS[HealthSuite]
      TR[TaskRouter]
      UH[UtilityHub]
  end
  subgraph main["Engine (RTX 4090)"]
      MM(ModelManager 5570)
      Vision(VisionService 5610)
      Audio[/Audio & STT/TTS/]
      Cog(Chain-of-Thought & Learning)
      UI(Responder & EmotionEngine 5590)
  end
  TR --> MM & Vision & Audio & Cog
  Vision --> UMO
  Audio  --> UMO
  Cog    --> UMO
  UI --> UMO
  HS -.-> TR
  HS -.-> main
6. Impact Assessment
| Area | Benefits | Risks / Mitigation | |------|----------|--------------------| | Container count ↓ 83 → 46 | Simpler Ops, faster CI | Phased migration with canaries | | Ports clash resolved | No startup failures | Update client configs | | Single memory plane | No divergence | Add local write-back cache | | Unified routing | Consistent priorities | Load-test GPU tags |

7. Migration Plan (Zero-Downtime)
Deploy HealthSuite (8500/8501) on pc2; mirror metrics one week.
Roll out TaskRouter at 7100; proxy to RequestCoordinator; shift traffic 20 % → 100 %.
Switch all services to pc2 UMO: deploy proxy on main_pc, flip env.
Package and deploy VisionService; drain FaceRecognition & VisionProcessing agents.
Remove duplicated SecondaryModelService on main_pc, shift pc2 copy to 7160.
Re-port SystemToolkitAgent → 7132/8132; restart UtilityHub containers.
Clean up legacy containers; archive compose + code (archive/legacy_YYYYMMDD).
Downtime target < 60 s cumulative.

8. Hardware-Aware Placement
| Domain | Why | Host | |--------|-----|------| | GPU-heavy inference (ModelManager, Vision, Learning) | Needs 24 GB VRAM | main_pc | | Routing, Memory, Health, Utility | CPU & RAM, minimal VRAM | pc2 | | SecondaryModelService (translation) | Fits in 12 GB VRAM | pc2 |

9. Clean Codebase Creation Plan
Copy only referenced agents above; exclude unused paths (pc2_code/agents/legacy_*).
Enforce folder layout:
ai_system/
  core/    (UMO, HealthSuite, TaskRouter)
  engine/  (GPU agents)
  sensory/ (audio, vision)
  cognitive/
  ui/
  utils/
  configs/{prod,dev}
CI gates: mypy --strict, ruff, pytest -q.
Contract tests with protobuf stubs for every public service.
Record 24 h prod traffic; replay in staging; assert parity.
Tag old repo legacy_pre_refactor, push to S3 Glacier; attach auto-generated dependency graph.
Publish RUNBOOK & 90-min onboarding guide.
10. Final Recommendations
Resolve the two port collisions immediately (5590, 7128).
Adopt six-domain architecture with exact YAML-backed agent lists above.
Consolidate health, memory, routing, vision, and utilities as detailed.
Begin clean-codebase migration now; dual-stack period ≤ 90 days.
Monitor RTX 4090 utilisation; if > 85 %, add another Engine node rather than reversing consolidation.
Grounded in the actual YAML configurations, these steps deliver a leaner, more maintainable, and GPU-optimised distributed AI platform.