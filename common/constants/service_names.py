# Centralized service name constants to avoid string drift across the codebase
# New code should import from this module rather than hard-coding strings.

class ServiceNames:
    # Core/Discovery
    SystemDigitalTwin = "SystemDigitalTwin"
    ServiceRegistry = "ServiceRegistry"
    RequestCoordinator = "RequestCoordinator"
    UnifiedSystemAgent = "UnifiedSystemAgent"

    # Speech I/O
    StreamingTTSAgent = "StreamingTTSAgent"
    StreamingSpeechRecognition = "StreamingSpeechRecognition"
    StreamingInterruptHandler = "StreamingInterruptHandler"
    TTSService = "TTSService"
    STTService = "STTService"
    FusedAudioPreprocessor = "FusedAudioPreprocessor"
    WakeWordDetector = "WakeWordDetector"

    # Emotion / APC
    AffectiveProcessingCenter = "AffectiveProcessingCenter"

    # Observability
    UnifiedObservabilityCenter = "UnifiedObservabilityCenter"

    # Memory / Model Ops
    ModelOpsCoordinator = "ModelOpsCoordinator"
    MemoryOrchestrator = "MemoryOrchestrator"
    MemoryClient = "MemoryClient"