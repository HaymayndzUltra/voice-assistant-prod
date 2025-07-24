graph TD
    subgraph MainPC [MainPC (RTX 4090)]
        direction TB

        subgraph core_services [Core Services & Orchestration]
            direction LR
            ServiceRegistry_M[ServiceRegistry]
            SystemDigitalTwin_M[SystemDigitalTwin]
            RequestCoordinator_M[RequestCoordinator]
            ObservabilityHub_M[ObservabilityHub]
            UnifiedSystemAgent_M[UnifiedSystemAgent]
        end

        subgraph model_infra [Model Infrastructure]
            direction LR
            ModelManagerSuite_M[ModelManagerSuite]
            CodeGenerator_M[CodeGenerator]
            Executor_M[Executor]
        end

        subgraph io_and_perception [I/O & Perception]
            direction LR
            subgraph audio_interface_m [Audio Interface]
                AudioCapture_M[AudioCapture]
                StreamingSpeechRecognition_M[StreamingSpeechRecognition]
                StreamingTTSAgent_M[StreamingTTSAgent]
                WakeWordDetector_M[WakeWordDetector]
            end
            subgraph language_and_emotion [Language & Emotion]
                NLUAgent_M[NLUAgent]
                EmotionEngine_M[EmotionEngine]
                Responder_M[Responder]
                EmpathyAgent_M[EmpathyAgent]
            end
        end

        subgraph memory_system_m [Memory System Client]
            MemoryClient_M[MemoryClient]
        end
    end

    subgraph PC2 [PC2 (RTX 3060) - Heavy Processing & Memory]
        direction TB

        subgraph pc2_core [Core Memory & Response]
            direction LR
            MemoryOrchestratorService_P[MemoryOrchestratorService]
            TieredResponder_P[TieredResponder]
            CacheManager_P[CacheManager]
        end

        subgraph pc2_processing [Task Processing & Routing]
            direction LR
            AsyncProcessor_P[AsyncProcessor]
            AdvancedRouter_P[AdvancedRouter]
            TaskScheduler_P[TaskScheduler]
            RemoteConnectorAgent_P[RemoteConnectorAgent]
        end

        subgraph pc2_reasoning [Memory & Reasoning]
            direction LR
            UnifiedMemoryReasoningAgent_P[UnifiedMemoryReasoningAgent]
            ContextManager_P[ContextManager]
            ExperienceTracker_P[ExperienceTracker]
        end

        subgraph pc2_specialized [Specialized Services]
            direction LR
            VisionProcessingAgent_P[VisionProcessingAgent]
            DreamWorldAgent_P[DreamWorldAgent]
            TutorAgent_P[TutorAgent]
            TutoringAgent_P[TutoringAgent]
            DreamingModeAgent_P[DreamingModeAgent]
        end

        subgraph pc2_system [System & Security]
            direction LR
            ResourceManager_P[ResourceManager]
            AuthenticationAgent_P[AuthenticationAgent]
            UnifiedUtilsAgent_P[UnifiedUtilsAgent]
            FileSystemAssistantAgent_P[FileSystemAssistantAgent]
        end

        subgraph pc2_monitoring [Monitoring & Analysis]
            direction LR
            ObservabilityHub_P[ObservabilityHub]
            ProactiveContextMonitor_P[ProactiveContextMonitor]
            AgentTrustScorer_P[AgentTrustScorer]
            UnifiedWebAgent_P[UnifiedWebAgent]
        end
    end

    subgraph Shared_Infrastructure [Shared Infrastructure]
        direction LR
        Redis[Redis Cache]
        ErrorBus[Error Bus (ZMQ PUB/SUB)]
        SQLite_DBs[SQLite Databases]
        Prometheus[Prometheus Metrics]
    end

    %% MainPC Internal Dependencies
    RequestCoordinator_M --> SystemDigitalTwin_M
    RequestCoordinator_M --> EmotionEngine_M
    EmotionEngine_M --> SystemDigitalTwin_M
    UnifiedSystemAgent_M --> SystemDigitalTwin_M
    ObservabilityHub_M --> SystemDigitalTwin_M
    MemoryClient_M --> SystemDigitalTwin_M
    CodeGenerator_M --> ModelManagerSuite_M
    Executor_M --> CodeGenerator_M

    %% PC2 Internal Dependencies
    TieredResponder_P --> ResourceManager_P
    TaskScheduler_P --> AsyncProcessor_P
    
    UnifiedMemoryReasoningAgent_P --> MemoryOrchestratorService_P
    ContextManager_P --> MemoryOrchestratorService_P
    CacheManager_P --> MemoryOrchestratorService_P
    DreamWorldAgent_P --> MemoryOrchestratorService_P
    TutorAgent_P --> MemoryOrchestratorService_P
    TutoringAgent_P --> MemoryOrchestratorService_P
    UnifiedWebAgent_P --> MemoryOrchestratorService_P
    ExperienceTracker_P --> MemoryOrchestratorService_P
    
    AuthenticationAgent_P --> UnifiedUtilsAgent_P
    UnifiedUtilsAgent_P --> ObservabilityHub_P
    ProactiveContextMonitor_P --> MemoryOrchestratorService_P
    AgentTrustScorer_P --> MemoryOrchestratorService_P
    FileSystemAssistantAgent_P --> MemoryOrchestratorService_P
    RemoteConnectorAgent_P --> MemoryOrchestratorService_P


    %% Cross-Machine Dependencies (MainPC <--> PC2)
    RequestCoordinator_M -.->|ZMQ REQ/REP - Complex Tasks| RemoteConnectorAgent_P
    MemoryClient_M -.->|ZMQ REQ/REP - Memory Ops| MemoryOrchestratorService_P
    ObservabilityHub_M -.->|HTTP Sync| ObservabilityHub_P

    %% Shared Infrastructure Dependencies
    ServiceRegistry_M --> Redis
    SystemDigitalTwin_M --> Redis
    CacheManager_P --> Redis

    MemoryOrchestratorService_P --> SQLite_DBs
    SystemDigitalTwin_M --> SQLite_DBs

    RequestCoordinator_M --> ErrorBus
    MemoryOrchestratorService_P --> ErrorBus
    TieredResponder_P --> ErrorBus
    ObservabilityHub_M --> ErrorBus
    ObservabilityHub_P --> ErrorBus

    SystemDigitalTwin_M --> Prometheus
    ObservabilityHub_M --> Prometheus
    ObservabilityHub_P --> Prometheus


    %% Styling
    classDef mainpc fill:#e6f2ff,stroke:#333,stroke-width:2px;
    classDef pc2 fill:#e6ffe6,stroke:#333,stroke-width:2px;
    classDef shared fill:#fdf5e6,stroke:#333,stroke-width:2px;

    class MainPC,core_services,model_infra,io_and_perception,memory_system_m,audio_interface_m,language_and_emotion mainpc;
    class PC2,pc2_core,pc2_processing,pc2_reasoning,pc2_specialized,pc2_system,pc2_monitoring pc2;
    class Shared_Infrastructure shared;

### Legend and Explanations (Corrected)

This diagram illustrates the distributed architecture of the AI system, split between two main compute nodes: **MainPC** and **PC2**, based *strictly* on the provided `startup_config.yaml` files.

*   **Boxes**: Represent individual agents or logical groups of agents (subsystems).
    *   <span style="color:blue">■</span> **Blue (MainPC)**: Agents defined in `main_pc_code/config/startup_config.yaml`. These handle real-time user interaction and core orchestration.
    *   <span style="color:green">■</span> **Green (PC2)**: Agents defined in `pc2_code/config/startup_config.yaml`. These handle heavier, asynchronous tasks and centralized memory management.
    *   <span style="color:orange">■</span> **Orange (Shared Infrastructure)**: External or shared services like Redis and a conceptual Error Bus.

*   **Arrows**: Represent dependencies and communication flow as defined in the SOT configs.
    *   `-->` **Solid Arrow**: Represents a direct dependency listed in the YAML file (e.g., `dependencies: [ServiceRegistry]`).
    *   `-.->` **Dotted Arrow**: Represents a primary cross-machine communication link, inferred from the system's distributed nature (e.g., MainPC's `RequestCoordinator` must talk to PC2's `RemoteConnectorAgent`).

#### Key Architectural Patterns (Corrected):

*   **Distributed Responsibility**: MainPC handles the immediate user-facing tasks. Complex or non-real-time tasks are offloaded to PC2 via the `RemoteConnectorAgent`.
*   **Centralized PC2 Memory**: The `MemoryOrchestratorService` on PC2 is the single source of truth for all memory operations on that machine. All other PC2 agents that require memory access depend on it. MainPC agents access it via the `MemoryClient`.
*   **Consolidated Monitoring**: Both systems have an `ObservabilityHub`. The PC2 hub is configured to sync with the MainPC hub, providing a single point for overall system monitoring. Legacy monitors on PC2 have been removed in favor of this consolidated agent.
*   **Strict SOT Adherence**: This diagram **only** reflects the agents and dependencies explicitly listed in the two specified `startup_config.yaml` files. There is no `SystemDigitalTwin` on PC2 as it was not in its SOT. Legacy agents commented out in the configs have been excluded.