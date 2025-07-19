graph TD
    subgraph MainPC [MainPC (RTX 4090)]
        direction TB

        subgraph core_services [Core Services]
            direction LR
            ServiceRegistry_M[ServiceRegistry]
            SystemDigitalTwin_M[SystemDigitalTwin]
            RequestCoordinator_M[RequestCoordinator]
            UnifiedSystemAgent_M[UnifiedSystemAgent]
            ObservabilityHub_M[ObservabilityHub]
            ModelManagerSuite_M[ModelManagerSuite]
        end

        subgraph memory_system_m [Memory System]
            direction LR
            MemoryClient_M[MemoryClient]
            SessionMemoryAgent_M[SessionMemoryAgent]
            KnowledgeBase_M[KnowledgeBase]
        end

        subgraph language_processing_m [Language Processing]
            direction LR
            NLUAgent_M[NLUAgent]
            AdvancedCommandHandler_M[AdvancedCommandHandler]
            Responder_M[Responder]
            TranslationService_M[TranslationService]
        end

        subgraph audio_interface_m [Audio Interface]
            direction LR
            AudioCapture_M[AudioCapture]
            FusedAudioPreprocessor_M[FusedAudioPreprocessor]
            StreamingSpeechRecognition_M[StreamingSpeechRecognition]
            StreamingTTSAgent_M[StreamingTTSAgent]
            WakeWordDetector_M[WakeWordDetector]
        end

        subgraph emotion_system_m [Emotion System]
            direction LR
            EmotionEngine_M[EmotionEngine]
            ToneDetector_M[ToneDetector]
            EmpathyAgent_M[EmpathyAgent]
        end

        subgraph utility_services_m [Utility Services]
            CodeGenerator_M[CodeGenerator]
            Executor_M[Executor]
        end

    end

    subgraph PC2 [PC2 (RTX 3060)]
        direction TB

        subgraph pc2_integration [Integration & Routing]
            direction LR
            RemoteConnectorAgent_P[RemoteConnectorAgent]
            AdvancedRouter_P[AdvancedRouter]
            TieredResponder_P[TieredResponder]
            AsyncProcessor_P[AsyncProcessor]
            TaskScheduler_P[TaskScheduler]
        end

        subgraph pc2_memory [Unified Memory & Reasoning]
            direction LR
            UnifiedMemoryReasoningAgent_P[UnifiedMemoryReasoningAgent]
            EpisodicMemoryAgent_P[EpisodicMemoryAgent]
            ContextManager_P[ContextManager]
            CacheManager_P[CacheManager]
            DreamWorldAgent_P[DreamWorldAgent]
        end

        subgraph pc2_monitoring [Health & Self-Healing]
            direction LR
            HealthMonitor_P[HealthMonitor]
            PerformanceMonitor_P[PerformanceMonitor]
            UnifiedErrorAgent_P[UnifiedErrorAgent]
            RCAAgent_P[RCAAgent]
            SelfHealingAgent_P[SelfHealingAgent]
        end

        subgraph pc2_learning [Learning & Knowledge]
            direction LR
            LearningAgent_P[LearningAgent]
            TutoringAgent_P[TutoringAgent]
            KnowledgeBaseAgent_P[KnowledgeBaseAgent]
            ExperienceTracker_P[ExperienceTracker]
        end
    end

    subgraph Shared_Infrastructure [Shared Infrastructure]
        direction LR
        Redis[Redis Cache]
        ErrorBus[Error Bus (ZMQ PUB/SUB)]
        Prometheus[Prometheus / Grafana]
    end

    %% MainPC Internal Dependencies
    SystemDigitalTwin_M --> ServiceRegistry_M
    RequestCoordinator_M --> SystemDigitalTwin_M
    ModelManagerSuite_M --> SystemDigitalTwin_M
    ObservabilityHub_M --> SystemDigitalTwin_M
    MemoryClient_M --> SystemDigitalTwin_M
    NLUAgent_M --> SystemDigitalTwin_M
    AudioCapture_M --> FusedAudioPreprocessor_M
    StreamingSpeechRecognition_M --> FusedAudioPreprocessor_M
    WakeWordDetector_M --> FusedAudioPreprocessor_M
    StreamingSpeechRecognition_M --> RequestCoordinator_M
    AdvancedCommandHandler_M --> NLUAgent_M
    AdvancedCommandHandler_M --> CodeGenerator_M
    CodeGenerator_M --> ModelManagerSuite_M
    Executor_M --> CodeGenerator_M
    ToneDetector_M --> EmotionEngine_M
    EmpathyAgent_M --> EmotionEngine_M
    Responder_M --> NLUAgent_M
    Responder_M --> EmotionEngine_M
    Responder_M --> StreamingTTSAgent_M

    %% PC2 Internal Dependencies
    AdvancedRouter_P --> TieredResponder_P
    TaskScheduler_P --> AsyncProcessor_P
    UnifiedMemoryReasoningAgent_P --> CacheManager_P
    EpisodicMemoryAgent_P --> UnifiedMemoryReasoningAgent_P
    DreamWorldAgent_P --> UnifiedMemoryReasoningAgent_P
    ContextManager_P --> UnifiedMemoryReasoningAgent_P
    KnowledgeBaseAgent_P --> CacheManager_P
    LearningAgent_P --> EpisodicMemoryAgent_P
    ExperienceTracker_P --> EpisodicMemoryAgent_P
    RCAAgent_P --> HealthMonitor_P
    SelfHealingAgent_P --> RCAAgent_P
    HealthMonitor_P --> UnifiedErrorAgent_P
    PerformanceMonitor_P --> HealthMonitor_P


    %% Cross-Machine Dependencies (MainPC <--> PC2)
    RequestCoordinator_M -.->|ZMQ REQ/REP| AdvancedRouter_P
    MemoryClient_M -.->|ZMQ REQ/REP| UnifiedMemoryReasoningAgent_P
    ObservabilityHub_M -.->|HTTP Poll| HealthMonitor_P
    HealthMonitor_P -.->|ZMQ PUB/SUB| ObservabilityHub_M
    SystemDigitalTwin_M -.->|Sync| SystemDigitalTwin_P(SystemDigitalTwin)

    %% Shared Infrastructure Dependencies
    SystemDigitalTwin_M --> Redis
    ServiceRegistry_M --> Redis
    UnifiedMemoryReasoningAgent_P --> Redis

    EmotionEngine_M --> ErrorBus
    UnifiedErrorAgent_P --> ErrorBus
    RequestCoordinator_M --> ErrorBus

    ObservabilityHub_M --> Prometheus
    PerformanceMonitor_P --> Prometheus


    %% Styling
    classDef mainpc fill:#e6f2ff,stroke:#333,stroke-width:2px;
    classDef pc2 fill:#e6ffe6,stroke:#333,stroke-width:2px;
    classDef shared fill:#fdf5e6,stroke:#333,stroke-width:2px;

    class MainPC,core_services,memory_system_m,language_processing_m,audio_interface_m,emotion_system_m,utility_services_m mainpc;
    class PC2,pc2_integration,pc2_memory,pc2_monitoring,pc2_learning pc2;
    class Shared_Infrastructure shared;

### Legend and Explanations

This diagram illustrates the distributed architecture of the AI system, split between two main compute nodes: **MainPC** and **PC2**.

*   **Boxes**: Represent individual agents or groups of agents (subsystems).
    *   <span style="color:blue">■</span> **Blue (MainPC)**: Agents running on the primary, more powerful machine (RTX 4090). These typically handle real-time interaction, core orchestration, and I/O.
    *   <span style="color:green">■</span> **Green (PC2)**: Agents running on the secondary machine (RTX 3060). These handle heavier, asynchronous tasks like advanced reasoning, memory consolidation, self-healing, and learning.
    *   <span style="color:orange">■</span> **Orange (Shared Infrastructure)**: External services that are used by agents on both machines.

*   **Arrows**: Represent dependencies and communication flow.
    *   `-->` **Solid Arrow**: Represents a direct, critical dependency where one agent relies on another to function. This is typically a ZMQ REQ/REP or direct function call pattern.
    *   `-.->` **Dotted Arrow**: Represents a primary communication link, especially for cross-machine interaction or to indicate a less tightly coupled relationship (e.g., publishing to a bus).

#### Key Communication Patterns:

*   **Cross-Node Communication**: The link between MainPC and PC2 is primarily managed by a few key agents:
    *   `RequestCoordinator` on MainPC sends complex tasks to the `AdvancedRouter` on PC2.
    *   `MemoryClient` on MainPC allows agents to access the powerful `UnifiedMemoryReasoningAgent` on PC2.
    *   Monitoring data flows from PC2's `HealthMonitor` back to the central `ObservabilityHub` on MainPC.

*   **Error Bus**: Agents from both machines publish error messages to a shared `Error Bus` (implemented with ZMQ PUB/SUB). The `UnifiedErrorAgent` on PC2 subscribes to this bus to centralize error logging and trigger healing processes.

*   **Health Checks**: All agents have health check endpoints (typically HTTP and/or ZMQ). The `ObservabilityHub` (MainPC) and `HealthMonitor` (PC2) are responsible for polling these endpoints to ensure the entire system is operational.

*   **Shared State (Redis)**: A shared Redis instance is used for fast, ephemeral data sharing, service discovery (`ServiceRegistry`), and caching (`CacheManager` on PC2).

*   **Global Configuration**: All agents inherit global settings for resource limits (CPU/RAM), environment variables, and default health check intervals as defined in their respective configuration files.