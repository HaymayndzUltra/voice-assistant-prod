graph TD
    subgraph MainPC [MainPC (RTX 4090)]
        direction TB

        subgraph core_services [Core Services & Orchestration]
            direction LR
            ServiceRegistry_M[ServiceRegistry]
            SystemDigitalTwin_M[SystemDigitalTwin]
            RequestCoordinator_M[RequestCoordinator]
            ObservabilityHub_M[ObservabilityHub]
        end

        subgraph model_infra [Model & Utility Services]
            direction LR
            ModelManagerSuite_M[ModelManagerSuite]
            CodeGenerator_M[CodeGenerator]
            Executor_M[Executor]
        end

        subgraph perception [I/O & Perception]
            direction LR
            NLUAgent_M[NLUAgent]
            EmotionEngine_M[EmotionEngine]
            AudioCapture_M[AudioCapture]
            StreamingTTSAgent_M[StreamingTTSAgent]
        end
        
        subgraph memory_client [Memory Client]
             MemoryClient_M[MemoryClient]
        end
    end

    subgraph PC2 [PC2 (RTX 3060) - Heavy Processing & Memory]
        direction TB

        subgraph pc2_entry [Entry & Task Management]
            direction LR
            RemoteConnectorAgent_P[RemoteConnectorAgent]
            AdvancedRouter_P[AdvancedRouter]
            TaskScheduler_P[TaskScheduler]
            AsyncProcessor_P[AsyncProcessor]
        end

        subgraph pc2_memory [Unified Memory & Reasoning]
            direction LR
            MemoryOrchestratorService_P[MemoryOrchestratorService]
            UnifiedMemoryReasoningAgent_P[UnifiedMemoryReasoningAgent]
            ContextManager_P[ContextManager]
            CacheManager_P[CacheManager]
        end

        subgraph pc2_specialized [Specialized & Learning Agents]
            direction LR
            DreamWorldAgent_P[DreamWorldAgent]
            TutorAgent_P[TutorAgent]
            UnifiedWebAgent_P[UnifiedWebAgent]
            VisionProcessingAgent_P[VisionProcessingAgent]
        end

        subgraph pc2_monitoring [Monitoring]
            ObservabilityHub_P[ObservabilityHub]
        end
    end

    subgraph Shared_Infrastructure [Shared Infrastructure]
        direction LR
        Redis[Redis Cache]
        ErrorBus[Error Bus (ZMQ PUB/SUB)]
    end

    %% MainPC Internal Dependencies
    SystemDigitalTwin_M --> ServiceRegistry_M
    RequestCoordinator_M --> SystemDigitalTwin_M
    ModelManagerSuite_M --> SystemDigitalTwin_M
    ObservabilityHub_M --> SystemDigitalTwin_M
    MemoryClient_M --> SystemDigitalTwin_M
    NLUAgent_M --> SystemDigitalTwin_M
    CodeGenerator_M --> ModelManagerSuite_M
    Executor_M --> CodeGenerator_M

    %% PC2 Internal Dependencies
    RemoteConnectorAgent_P --> AdvancedRouter_P
    AdvancedRouter_P --> TaskScheduler_P
    TaskScheduler_P --> AsyncProcessor_P
    AsyncProcessor_P --> ResourceManager_P(ResourceManager)

    UnifiedMemoryReasoningAgent_P --> MemoryOrchestratorService_P
    ContextManager_P --> MemoryOrchestratorService_P
    CacheManager_P --> MemoryOrchestratorService_P
    DreamWorldAgent_P --> MemoryOrchestratorService_P
    TutorAgent_P --> MemoryOrchestratorService_P
    UnifiedWebAgent_P --> MemoryOrchestratorService_P
    
    ResourceManager_P --> ObservabilityHub_P


    %% Cross-Machine Dependencies (MainPC <--> PC2)
    RequestCoordinator_M -.->|ZMQ REQ/REP - Complex Tasks| RemoteConnectorAgent_P
    MemoryClient_M -.->|ZMQ REQ/REP - Memory Ops| MemoryOrchestratorService_P
    ObservabilityHub_M -.->|HTTP Sync| ObservabilityHub_P

    %% Shared Infrastructure Dependencies
    ServiceRegistry_M --> Redis
    CacheManager_P --> Redis

    ModelManagerSuite_M --> ErrorBus
    RequestCoordinator_M --> ErrorBus
    ObservabilityHub_P --> ErrorBus


    %% Styling
    classDef mainpc fill:#e6f2ff,stroke:#333,stroke-width:2px;
    classDef pc2 fill:#e6ffe6,stroke:#333,stroke-width:2px;
    classDef shared fill:#fdf5e6,stroke:#333,stroke-width:2px;

    class MainPC,core_services,model_infra,perception,memory_client mainpc;
    class PC2,pc2_entry,pc2_memory,pc2_specialized,pc2_monitoring pc2;
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