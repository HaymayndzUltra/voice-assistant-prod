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

        subgraph pc2_entry [Entry & Task Management]
            direction LR
            RemoteConnectorAgent_P[RemoteConnectorAgent]
            AdvancedRouter_P[AdvancedRouter]
            TaskScheduler_P[TaskScheduler]
            AsyncProcessor_P[AsyncProcessor]
        end

        subgraph pc2_memory [Unified Memory & Reasoning]
            direction LR
            UnifiedMemoryReasoningAgent_P[UnifiedMemoryReasoningAgent]
            EpisodicMemoryAgent_P[EpisodicMemoryAgent]
            ContextManager_P[ContextManager]
            CacheManager_P[CacheManager]
        end

        subgraph pc2_learning_healing [Learning, Healing & Simulation]
            direction LR
            DreamWorldAgent_P[DreamWorldAgent]
            LearningAgent_P[LearningAgent]
            HealthMonitor_P[HealthMonitor]
            SelfHealingAgent_P[SelfHealingAgent]
        end
    end

    subgraph Shared_Infrastructure [Shared Infrastructure]
        direction LR
        Redis[Redis Cache]
        ErrorBus[Error Bus (ZMQ PUB/SUB)]
        Prometheus[Prometheus / Grafana]
        SQLite_DBs[SQLite DBs (Per-agent)]
    end

    %% MainPC Internal Dependencies
    SystemDigitalTwin_M --> ServiceRegistry_M
    RequestCoordinator_M --> SystemDigitalTwin_M
    RequestCoordinator_M --> NLUAgent_M
    RequestCoordinator_M --> EmotionEngine_M
    RequestCoordinator_M --> StreamingSpeechRecognition_M
    
    NLUAgent_M --> RequestCoordinator_M
    EmotionEngine_M --> NLUAgent_M

    Responder_M --> NLUAgent_M
    Responder_M --> EmotionEngine_M
    Responder_M --> StreamingTTSAgent_M
    EmpathyAgent_M --> EmotionEngine_M

    CodeGenerator_M --> ModelManagerSuite_M
    Executor_M --> CodeGenerator_M
    
    ModelManagerSuite_M --> SystemDigitalTwin_M

    MemoryClient_M --> SystemDigitalTwin_M

    %% PC2 Internal Dependencies
    AdvancedRouter_P --> TaskScheduler_P
    TaskScheduler_P --> AsyncProcessor_P
    
    UnifiedMemoryReasoningAgent_P --> CacheManager_P
    EpisodicMemoryAgent_P --> UnifiedMemoryReasoningAgent_P
    ContextManager_P --> UnifiedMemoryReasoningAgent_P
    DreamWorldAgent_P --> UnifiedMemoryReasoningAgent_P
    LearningAgent_P --> EpisodicMemoryAgent_P
    
    SelfHealingAgent_P --> HealthMonitor_P
    HealthMonitor_P --> UnifiedErrorAgent_P(UnifiedErrorAgent)


    %% Cross-Machine Dependencies (MainPC <--> PC2)
    RequestCoordinator_M -.->|ZMQ REQ/REP - Complex Tasks| AdvancedRouter_P
    MemoryClient_M -.->|ZMQ REQ/REP - Memory Ops| UnifiedMemoryReasoningAgent_P
    ObservabilityHub_M -.->|HTTP Poll - Health| HealthMonitor_P
    SystemDigitalTwin_M -.->|Sync| SystemDigitalTwin_P(SystemDigitalTwin)

    %% Shared Infrastructure Dependencies
    SystemDigitalTwin_M --> Redis
    ServiceRegistry_M --> Redis
    CacheManager_P --> Redis

    ModelManagerSuite_M --> SQLite_DBs
    UnifiedMemoryReasoningAgent_P --> SQLite_DBs

    RequestCoordinator_M --> ErrorBus
    ModelManagerSuite_M --> ErrorBus
    UnifiedErrorAgent_P --> ErrorBus

    ObservabilityHub_M --> Prometheus
    HealthMonitor_P --> Prometheus


    %% Styling
    classDef mainpc fill:#e6f2ff,stroke:#333,stroke-width:2px;
    classDef pc2 fill:#e6ffe6,stroke:#333,stroke-width:2px;
    classDef shared fill:#fdf5e6,stroke:#333,stroke-width:2px;

    class MainPC,core_services,model_infra,io_and_perception,memory_system_m,audio_interface_m,language_and_emotion mainpc;
    class PC2,pc2_entry,pc2_memory,pc2_learning_healing pc2;
    class Shared_Infrastructure shared;

### Legend and Explanations (Updated)

This diagram illustrates the distributed architecture of the AI system, split between two main compute nodes: **MainPC** and **PC2**.

*   **Boxes**: Represent individual agents or logical groups of agents (subsystems).
    *   <span style="color:blue">■</span> **Blue (MainPC)**: Agents running on the primary, more powerful machine (RTX 4090). These typically handle real-time user interaction, core orchestration, and direct model management.
    *   <span style="color:green">■</span> **Green (PC2)**: Agents running on the secondary machine (RTX 3060). These handle heavier, asynchronous, and memory-intensive tasks like advanced reasoning, long-term memory consolidation, and system self-healing.
    *   <span style="color:orange">■</span> **Orange (Shared Infrastructure)**: External or shared services used by agents on both machines.

*   **Arrows**: Represent dependencies and communication flow.
    *   `-->` **Solid Arrow**: Represents a direct, critical dependency where one agent relies on another to function. This is typically a ZMQ REQ/REP or direct function call pattern within the same machine.
    - `-.->` **Dotted Arrow**: Represents a primary communication link, especially for cross-machine interaction or to indicate a less tightly coupled relationship (e.g., publishing to a bus or polling an endpoint).

#### Key Architectural Patterns:

*   **Distributed Responsibility**: MainPC handles the immediate "thinking" and "talking" (`RequestCoordinator`, `NLUAgent`, `ModelManagerSuite`). Complex or non-real-time tasks are offloaded to PC2 via the `AdvancedRouter`.
*   **Centralized Model Management**: The `ModelManagerSuite` on MainPC is the single point of contact for loading, unloading, and running inference on all models, including those used by PC2 agents (which would access it via the cross-node link).
*   **Distributed Memory**: The `MemoryClient` on MainPC provides a simple interface to the much more complex and powerful `UnifiedMemoryReasoningAgent` on PC2. This keeps the MainPC agents lightweight while centralizing heavy memory operations on PC2.
*   **Federated Monitoring**: Each node has its own health monitor (`ObservabilityHub` on MainPC, `HealthMonitor` on PC2). The PC2 monitor reports its status up to the MainPC monitor, which provides a single pane of glass for the entire system's health.
*   **Shared Error Bus**: Agents from both machines publish structured errors to a shared `Error Bus` (ZMQ PUB/SUB). This allows for centralized logging and enables cross-machine responses, such as PC2's `SelfHealingAgent` reacting to an error that originated on MainPC.