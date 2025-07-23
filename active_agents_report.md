# AI System Agents Report

Generated on: 2025-07-08 07:47:18

## Summary

- **Total Agents**: 272
- **Running Agents**: 2
- **Agents with Error Bus Integration**: 122
- **Main PC Agents**: 177
- **PC2 Agents**: 61

## Agent Dependency Graph

```mermaid
graph TD;
  HumanAwarenessAgent["🔴 💻 HumanAwarenessAgent🔄"];
  HumanAwareness["🔴 💻 HumanAwareness🔄"];
  CircuitBreaker["🔴 💻 CircuitBreaker🔄"];
  StreamingSpeechRecognition["🔴 💻 StreamingSpeechRecognition🔄"];
  ResourceManager["🔴 🖥️ 💻 ResourceManager🔄"];
  FixedStreamingTranslation["🔴 💻 FixedStreamingTranslation🔄"];
  super["🔴 💻 super"];
  AdvancedSuggestionSystem["🔴 💻 AdvancedSuggestionSystem"];
  base_suggestions["🔴 💻 base_suggestions"];
  TelemetryDashboardHandler["🔴 💻 TelemetryDashboardHandler"];
  TelemetryServer["🔴 💻 TelemetryServer"];
  ModelManager["🔴 💻 ModelManager🔄"];
  ModelManagerAgent["🔴 💻 ModelManagerAgent🔄"];
  TTS["🔴 💻 TTS🔄"];
  TTSAgent["🔴 💻 TTSAgent🔄"];
  SessionMemory["🔴 💻 SessionMemory🔄"];
  SessionMemoryAgent["🔴 💻 SessionMemoryAgent🔄"];
  TextRequest["🔴 💻 TextRequest🔄"];
  ChitchatAgent["🔴 💻 ChitchatAgent🔄"];
  Chitchat["🔴 💻 Chitchat🔄"];
  ContextManager["🔴 🖥️ 💻 ContextManager🔄"];
  ProactiveAgent["🔴 💻 ProactiveAgent🔄"];
  Proactive["🔴 💻 Proactive🔄"];
  PredictiveHealthMonitor["🔴 💻 PredictiveHealthMonitor🔄"];
  UnifiedSystem["🔴 💻 UnifiedSystem"];
  UnifiedSystemAgent["🔴 💻 UnifiedSystemAgent"];
  IntentionValidatorAgent["🔴 💻 IntentionValidatorAgent🔄"];
  IntentionValidator["🔴 💻 IntentionValidator🔄"];
  NLU["🔴 💻 NLU🔄"];
  NLUAgent["🔴 💻 NLUAgent🔄"];
  ConnectionPool["🔴 💻 ConnectionPool🔄"];
  PluginEventHandler["🔴 💻 PluginEventHandler"];
  EmpathyAgent["🔴 💻 EmpathyAgent🔄"];
  Empathy["🔴 💻 Empathy🔄"];
  TTSCache["🔴 💻 TTSCache🔄"];
  MemoryOrchestrator["🔴 🖥️ 💻 MemoryOrchestrator🔄"];
  WakeWordDetectorAgent["🔴 💻 WakeWordDetectorAgent🔄"];
  WakeWordDetector["🔴 💻 WakeWordDetector🔄"];
  VRAMOptimizer["🔴 💻 VRAMOptimizer🔄"];
  VRAMOptimizerAgent["🔴 💻 VRAMOptimizerAgent🔄"];
  VisionCapture["🔴 💻 VisionCapture🔄"];
  VisionCaptureAgent["🔴 💻 VisionCaptureAgent🔄"];
  AdvancedCommandHandler["🔴 💻 AdvancedCommandHandler🔄"];
  ToneDetector["🔴 💻 ToneDetector🔄"];
  FeedbackHandler["🔴 💻 FeedbackHandler🔄"];
  TriggerWordDetector["🔴 💻 TriggerWordDetector"];
  with["🔴 💻 with"];
  CodeGeneratorAgent["🔴 💻 CodeGeneratorAgent🔄"];
  CodeGenerator["🔴 💻 CodeGenerator🔄"];
  StreamingAudioCapture["🔴 💻 StreamingAudioCapture🔄"];
  StreamingAudioCaptureAgent["🔴 💻 StreamingAudioCaptureAgent🔄"];
  SystemDigitalTwinAgent["🔴 💻 SystemDigitalTwinAgent🔄"];
  SystemDigitalTwin["🔴 💻 SystemDigitalTwin🔄"];
  NoiseReduction["🔴 💻 NoiseReduction"];
  NoiseReductionAgent["🔴 💻 NoiseReductionAgent"];
  KnowledgeBase["🔴 💻 KnowledgeBase🔄"];
  SpeechProcessor["🔴 💻 SpeechProcessor"];
  FusedAudioPreprocessor["🔴 💻 FusedAudioPreprocessor🔄"];
  FusedAudioPreprocessorAgent["🔴 💻 FusedAudioPreprocessorAgent🔄"];
  StreamingWhisperASR["🔴 💻 StreamingWhisperASR"];
  VoiceMeeterControlAgent["🔴 💻 VoiceMeeterControlAgent"];
  VoiceMeeterControl["🔴 💻 VoiceMeeterControl"];
  StreamingPartialTranscripts["🔴 💻 StreamingPartialTranscripts"];
  LearningOpportunityDetector["🔴 💻 LearningOpportunityDetector🔄"];
  EmotionEngine["🔴 💻 EmotionEngine🔄"];
  DynamicIdentity["🔴 💻 DynamicIdentity🔄"];
  DynamicIdentityAgent["🔴 💻 DynamicIdentityAgent🔄"];
  VAD["🔴 💻 VAD"];
  VADAgent["🔴 💻 VADAgent"];
  SelfHealingDatabase["🔴 💻 SelfHealingDatabase"];
  class["🔴 🖥️ 💻 class🔄"];
  ZMQClient["🔴 💻 ZMQClient"];
  ZMQServer["🔴 💻 ZMQServer"];
  ZMQSubscriber["🔴 💻 ZMQSubscriber"];
  from["🔴 🖥️ 💻 from🔄"];
  SelfHealingAgent["🔴 💻 SelfHealingAgent"];
  RecoveryAction["🔴 💻 RecoveryAction"];
  SystemResourceSnapshot["🔴 💻 SystemResourceSnapshot"];
  SelfHealing["🔴 💻 SelfHealing"];
  if["🔴 💻 if"];
  AgentBase["🔴 💻 AgentBase"];
  AgentStatus["🔴 🖥️ 💻 AgentStatus"];
  for["🔴 🖥️ 💻 for"];
  ErrorRecord["🔴 💻 ErrorRecord"];
  ZMQPublisher["🔴 💻 ZMQPublisher"];
  LazyVotingSystem["🔴 💻 LazyVotingSystem"];
  PersonalityEngine["🔴 💻 PersonalityEngine"];
  MoodTrackerAgent["🔴 💻 MoodTrackerAgent🔄"];
  MoodTracker["🔴 💻 MoodTracker🔄"];
  ResponderAgent["🔴 💻 ResponderAgent🔄"];
  Responder["🔴 💻 Responder🔄"];
  StreamingLanguageAnalyzer["🔴 💻 StreamingLanguageAnalyzer🔄"];
  EmotionSynthesis["🔴 💻 EmotionSynthesis🔄"];
  EmotionSynthesisAgent["🔴 💻 EmotionSynthesisAgent🔄"];
  ModelVotingAdapter["🔴 💻 ModelVotingAdapter"];
  VoiceProfiling["🔴 💻 VoiceProfiling🔄"];
  VoiceProfilingAgent["🔴 💻 VoiceProfilingAgent🔄"];
  PrivacyManager["🔴 💻 PrivacyManager🔄"];
  FaceRecognitionAgent["🔴 💻 FaceRecognitionAgent🔄"];
  FaceRecognition["🔴 💻 FaceRecognition🔄"];
  LivenessDetector["🔴 💻 LivenessDetector🔄"];
  PredictiveLoader["🔴 💻 PredictiveLoader🔄"];
  ExecutorAgent["🟢 💻 ExecutorAgent🔄"];
  Executor["🔴 💻 Executor🔄"];
  PerformanceMetrics["🔴 💻 PerformanceMetrics🔄"];
  AdvancedTimeoutManager["🔴 💻 AdvancedTimeoutManager🔄"];
  TranslationCache["🔴 💻 TranslationCache🔄"];
  PerformanceMonitor["🔴 🖥️ 💻 PerformanceMonitor🔄"];
  UltimateTTS["🔴 💻 UltimateTTS🔄"];
  UltimateTTSAgent["🔴 💻 UltimateTTSAgent🔄"];
  StreamingLanguageToLLM["🔴 💻 StreamingLanguageToLLM"];
  StreamingInterruptHandler["🔴 💻 StreamingInterruptHandler🔄"];
  StreamingInterrupt["🔴 💻 StreamingInterrupt"];
  MetaCognitionAgent["🔴 💻 MetaCognitionAgent🔄"];
  MetaCognition["🔴 💻 MetaCognition🔄"];
  GGUFStateTracker["🔴 💻 GGUFStateTracker🔄"];
  GGUFModelManager["🔴 💻 GGUFModelManager🔄"];
  LearningManager["🔴 💻 LearningManager🔄"];
  ResourceType["🔴 💻 ResourceType🔄"];
  LearningOrchestration["🔴 💻 LearningOrchestration🔄"];
  DigitalTwin["🔴 💻 DigitalTwin"];
  UserProfile["🔴 💻 UserProfile"];
  DigitalTwinAgent["🔴 💻 DigitalTwinAgent"];
  ActiveLearningMonitor["🔴 💻 ActiveLearningMonitor🔄"];
  Translation["🔴 💻 Translation"];
  and["🔴 💻 and"];
  VoiceController["🔴 💻 VoiceController"];
  ModelOrchestrator["🔴 💻 ModelOrchestrator"];
  RemoteConnector["🔴 🖥️ 💻 RemoteConnector🔄"];
  RemoteConnectorAgent["🔴 🖥️ 💻 RemoteConnectorAgent🔄"];
  VRAMManager["🔴 💻 VRAMManager"];
  DynamicSTTModelManager["🔴 💻 DynamicSTTModelManager"];
  ContextSummarizer["🔴 💻 ContextSummarizer"];
  names["🔴 💻 names"];
  ContextSummarizerAgent["🔴 💻 ContextSummarizerAgent"];
  CodeGenerationIntentHandler["🔴 💻 CodeGenerationIntentHandler"];
  AIStudioAssistant["🔴 💻 AIStudioAssistant"];
  TimelineUIServer["🔴 💻 TimelineUIServer"];
  CommandClusteringEngine["🔴 💻 CommandClusteringEngine"];
  CoordinatorModule["🔴 💻 CoordinatorModule"];
  DiscoveryService["🔴 💻 DiscoveryService"];
  Discovery["🔴 💻 Discovery"];
  Task["🔴 💻 Task"];
  AgentRegistry["🔴 💻 AgentRegistry"];
  AutoGenFramework["🔴 💻 AutoGenFramework"];
  Message["🔴 💻 Message"];
  MessageBus["🔴 💻 MessageBus"];
  CommandConfirmation["🔴 💻 CommandConfirmation"];
  SessionAgent["🔴 💻 SessionAgent"];
  Session["🔴 💻 Session"];
  CodeCommandHandler["🔴 💻 CodeCommandHandler"];
  AutoFixer["🔴 💻 AutoFixer"];
  AutoFixerAgent["🔴 💻 AutoFixerAgent"];
  DistributedLauncher["🔴 💻 DistributedLauncher"];
  CommandSuggestionOptimized["🔴 💻 CommandSuggestionOptimized"];
  ContextBridge["🔴 💻 ContextBridge"];
  ContextBridgeAgent["🔴 💻 ContextBridgeAgent"];
  CommandSuggestion["🔴 💻 CommandSuggestion"];
  CommandQueue["🔴 💻 CommandQueue"];
  ErrorHandler["🔴 💻 ErrorHandler"];
  ErrorSeverity["🔴 💻 ErrorSeverity"];
  DataExtractionTool["🔴 💻 DataExtractionTool"];
  Plan["🔴 💻 Plan"];
  Tool["🔴 💻 Tool"];
  Goal["🔴 💻 Goal"];
  ExperienceMemory["🔴 💻 ExperienceMemory"];
  FileOperationTool["🔴 💻 FileOperationTool"];
  APIRequestTool["🔴 💻 APIRequestTool"];
  WebSearchTool["🔴 💻 WebSearchTool"];
  FileSystemAssistant["🔴 🖥️ 💻 FileSystemAssistant🔄"];
  FileSystemAssistantAgent["🔴 🖥️ 💻 FileSystemAssistantAgent🔄"];
  CustomCommandHandler["🔴 💻 CustomCommandHandler"];
  to["🟢 💻 to"];
  ZMQAuthenticator["🔴 💻 ZMQAuthenticator"];
  DiskUsageInfo["🔴 💻 DiskUsageInfo"];
  SecureClient["🔴 💻 SecureClient"];
  SecureServer["🔴 💻 SecureServer"];
  VisionProcessing["🔴 🖥️ VisionProcessing🔄"];
  VisionProcessingAgent["🔴 🖥️ VisionProcessingAgent🔄"];
  TieredResponder["🔴 🖥️ TieredResponder🔄"];
  DreamingMode["🔴 🖥️ DreamingMode🔄"];
  DreamingModeAgent["🔴 🖥️ DreamingModeAgent🔄"];
  TaskScheduler["🔴 🖥️ TaskScheduler🔄"];
  TaskSchedulerAgent["🔴 🖥️ TaskSchedulerAgent🔄"];
  ResourceMonitor["🔴 🖥️ ResourceMonitor🔄"];
  definitions["🔴 🖥️ definitions🔄"];
  AdvancedRouter["🔴 🖥️ AdvancedRouter🔄"];
  TestCompliant["🔴 🖥️ TestCompliant"];
  AdvancedTutoring["🔴 🖥️ AdvancedTutoring🔄"];
  AdvancedTutoringAgent["🔴 🖥️ AdvancedTutoringAgent🔄"];
  HealthMonitor["🔴 🖥️ HealthMonitor🔄"];
  HealthMonitorAgent["🔴 🖥️ HealthMonitorAgent🔄"];
  TutoringService["🔴 🖥️ TutoringService🔄"];
  TutoringServiceAgent["🔴 🖥️ TutoringServiceAgent🔄"];
  ExperienceTrackerAgent["🔴 🖥️ ExperienceTrackerAgent🔄"];
  ExperienceTracker["🔴 🖥️ ExperienceTracker🔄"];
  UnifiedWebAgent["🔴 🖥️ UnifiedWebAgent🔄"];
  UnifiedWeb["🔴 🖥️ UnifiedWeb🔄"];
  Tutor["🔴 🖥️ Tutor🔄"];
  TaskQueue["🔴 🖥️ TaskQueue🔄"];
  ScenarioType["🔴 🖥️ ScenarioType🔄"];
  DreamWorld["🔴 🖥️ DreamWorld🔄"];
  MemoryEntry["🔴 🖥️ MemoryEntry🔄"];
  CacheManager["🔴 🖥️ CacheManager🔄"];
  MemoryScheduler["🔴 🖥️ MemoryScheduler🔄"];
  LearningAdjuster["🔴 🖥️ LearningAdjuster"];
  LearningAdjusterAgent["🔴 🖥️ LearningAdjusterAgent"];
  ModelEvaluationFramework["🔴 🖥️ ModelEvaluationFramework🔄"];
  AgentTrustScorer["🔴 🖥️ AgentTrustScorer🔄"];
  PerformanceLoggerAgent["🔴 🖥️ PerformanceLoggerAgent🔄"];
  PerformanceLogger["🔴 🖥️ PerformanceLogger🔄"];
  ErrorCollectorModule["🔴 🖥️ ErrorCollectorModule"];
  DummyArgs["🔴 🖥️ DummyArgs🔄"];
  UnifiedUtils["🔴 🖥️ UnifiedUtils🔄"];
  UnifiedMonitor["🔴 🖥️ UnifiedMonitor"];
  Orchestrator["🔴 🖥️ Orchestrator"];
  OrchestratorAgent["🔴 🖥️ OrchestratorAgent"];
  SystemHealthManager["🔴 🖥️ SystemHealthManager🔄"];
  Authentication["🔴 🖥️ Authentication🔄"];
  ProactiveContextMonitor["🔴 🖥️ ProactiveContextMonitor"];
  EpisodicMemory["🔴 🖥️ EpisodicMemory"];
  EpisodicMemoryAgent["🔴 🖥️ EpisodicMemoryAgent"];
  ErrorPattern["🔴 🖥️ ErrorPattern"];
  UnifiedMemoryReasoningAgent["🔴 🖥️ UnifiedMemoryReasoningAgent"];
  UnifiedMemoryReasoning["🔴 🖥️ UnifiedMemoryReasoning"];
  MemoryManager["🔴 🖥️ MemoryManager"];
  MemoryDecayManager["🔴  MemoryDecayManager"];
  EnhancedContextualMemory["🔴  EnhancedContextualMemory"];
  AuthenticationAgent["🔴  AuthenticationAgent"];
  UnifiedErrorAgent["🔴  UnifiedErrorAgent"];
  UnifiedUtilsAgent["🔴  UnifiedUtilsAgent"];
  AsyncProcessor["🔴  AsyncProcessor"];
  RCAAgent["🔴  RCAAgent"];
  DreamWorldAgent["🔴  DreamWorldAgent"];
  TutorAgent["🔴  TutorAgent"];
  TutoringAgent["🔴  TutoringAgent"];
  UnifiedMemoryReasoningAgentAlt["🔴  UnifiedMemoryReasoningAgentAlt"];
  AgentUtils["🔴  AgentUtils"];
  ErrorBus["🔴  ErrorBus"];
  ServiceRegistry["🔴  ServiceRegistry"];
  MemoryClient["🔴  MemoryClient"];
  SpeechToText["🔴  SpeechToText"];
  IntentRecognizer["🔴  IntentRecognizer"];
  InputProcessor["🔴  InputProcessor"];
  RequestCoordinator["🔴  RequestCoordinator"];
  GoalManager["🔴  GoalManager"];
  ResponseGenerator["🔴  ResponseGenerator"];
  TranslationService["🔴  TranslationService"];
  StreamingTTS["🔴  StreamingTTS"];
  TaskRouter["🔴  TaskRouter"];
  ChainOfThoughtAgent["🔴  ChainOfThoughtAgent"];
  GOT_TOTAgent["🔴  GOT_TOTAgent"];
  GoalOrchestratorAgent["🔴  GoalOrchestratorAgent"];
  EnhancedModelRouter["🔴  EnhancedModelRouter"];
  TinyLlamaService["🔴  TinyLlamaService"];
  NLLBAdapter["🔴  NLLBAdapter"];
  LocalFineTunerAgent["🔴  LocalFineTunerAgent"];
  SelfTrainingOrchestrator["🔴  SelfTrainingOrchestrator"];
  CognitiveModelAgent["🔴  CognitiveModelAgent"];
  ConsolidatedTranslator["🔴  ConsolidatedTranslator"];
  VoiceProfiler["🔴  VoiceProfiler"];
  UnifiedPlanningAgent["🔴  UnifiedPlanningAgent"];
  MultiAgentSwarmManager["🔴  MultiAgentSwarmManager"];
  TTSConnector["🔴  TTSConnector"];
  StreamingTTSAgent["🔴  StreamingTTSAgent"];
  AudioCapture["🔴  AudioCapture"];
  LanguageAndTranslationCoordinator["🔴  LanguageAndTranslationCoordinator"];
  LearningAgent["🔴  LearningAgent"];
  KnowledgeBaseAgent["🔴  KnowledgeBaseAgent"];
  HealthCheck["🔴  HealthCheck"];
  MetricsCollector["🔴  MetricsCollector"];
  AlertManager["🔴  AlertManager"];
  EmotionEngine --> HumanAwarenessAgent;
  TaskRouter --> StreamingSpeechRecognition;
  ErrorBus --> SessionMemoryAgent;
  MemoryClient --> SessionMemoryAgent;
  NLUAgent --> ChitchatAgent;
  SessionMemoryAgent --> ContextManager;
  MemoryManager --> ContextManager;
  ErrorBus --> ContextManager;
  MemoryClient --> ContextManager;
  TaskRouter --> ProactiveAgent;
  UnifiedPlanningAgent --> UnifiedSystemAgent;
  TaskRouter --> IntentionValidatorAgent;
  LanguageAndTranslationCoordinator --> NLUAgent;
  EmotionEngine --> EmpathyAgent;
  FusedAudioPreprocessor --> WakeWordDetector;
  AudioCapture --> WakeWordDetector;
  NLUAgent --> AdvancedCommandHandler;
  CodeGenerator --> AdvancedCommandHandler;
  EmotionEngine --> ToneDetector;
  NLUAgent --> FeedbackHandler;
  ModelManagerAgent --> CodeGenerator;
  MemoryClient --> SystemDigitalTwin;
  ErrorBus --> SystemDigitalTwin;
  ServiceRegistry --> SystemDigitalTwin;
  ErrorBus --> KnowledgeBase;
  MemoryClient --> KnowledgeBase;
  AudioCapture --> FusedAudioPreprocessor;
  TaskRouter --> DynamicIdentityAgent;
  PerformanceLoggerAgent --> SelfHealingAgent;
  EmotionEngine --> MoodTrackerAgent;
  EmotionEngine --> Responder;
  NLUAgent --> Responder;
  ModelManagerAgent --> EmotionSynthesisAgent;
  ModelManagerAgent --> FaceRecognitionAgent;
  TaskRouter --> FaceRecognitionAgent;
  TaskRouter --> PredictiveLoader;
  HealthMonitor --> PerformanceMonitor;
  KnowledgeBase --> MetaCognitionAgent;
  MemoryClient --> LearningManager;
  MemoryClient --> ActiveLearningMonitor;
  LearningManager --> ActiveLearningMonitor;
  ErrorBus --> ActiveLearningMonitor;
  ServiceRegistry --> ActiveLearningMonitor;
  MemoryClient --> ModelOrchestrator;
  ContextManager --> ModelOrchestrator;
  ErrorBus --> ModelOrchestrator;
  ServiceRegistry --> ModelOrchestrator;
  AdvancedRouter --> RemoteConnectorAgent;
  MemoryClient --> ContextSummarizer;
  ContextManager --> ContextSummarizer;
  ErrorBus --> ContextSummarizer;
  ServiceRegistry --> ContextSummarizer;
  HealthMonitor --> AutoFixerAgent;
  UnifiedUtilsAgent --> FileSystemAssistantAgent;
  ResourceManager --> TieredResponder;
  DreamWorldAgent --> DreamingModeAgent;
  HealthMonitor --> TaskScheduler;
  AsyncProcessor --> TaskScheduler;
  TaskScheduler --> AdvancedRouter;
  ServiceRegistry --> HealthMonitor;
  ErrorBus --> HealthMonitor;
  ResourceManager --> HealthMonitor;
  UnifiedMemoryReasoningAgent --> TutoringServiceAgent;
  EpisodicMemoryAgent --> ExperienceTracker;
  UnifiedMemoryReasoningAgent --> UnifiedWebAgent;
  FileSystemAssistantAgent --> UnifiedWebAgent;
  AsyncProcessor --> CacheManager;
  HealthMonitor --> AgentTrustScorer;
  PerformanceMonitor --> PerformanceLoggerAgent;
  ContextManager --> ProactiveContextMonitor;
  UnifiedMemoryReasoningAgent --> EpisodicMemoryAgent;
  HealthMonitor --> UnifiedMemoryReasoningAgent;
  MemoryOrchestrator --> UnifiedMemoryReasoningAgent;
  CacheManager --> UnifiedMemoryReasoningAgent;
  UnifiedMemoryReasoningAgent --> MemoryManager;
  UnifiedMemoryReasoningAgent --> MemoryDecayManager;
  MemoryManager --> EnhancedContextualMemory;
  HealthMonitor --> AuthenticationAgent;
  HealthMonitor --> UnifiedErrorAgent;
  UnifiedErrorAgent --> UnifiedUtilsAgent;
  ResourceManager --> AsyncProcessor;
  HealthMonitor --> RCAAgent;
  SelfHealingAgent --> RCAAgent;
  UnifiedMemoryReasoningAgent --> DreamWorldAgent;
  TutoringServiceAgent --> TutorAgent;
  TutoringServiceAgent --> TutoringAgent;
  CacheManager --> UnifiedMemoryReasoningAgentAlt;
  UnifiedUtilsAgent --> AgentUtils;
  ErrorBus --> ServiceRegistry;
  ErrorBus --> MemoryClient;
  ServiceRegistry --> MemoryClient;
  ErrorBus --> SpeechToText;
  ServiceRegistry --> SpeechToText;
  MemoryClient --> IntentRecognizer;
  ErrorBus --> IntentRecognizer;
  ServiceRegistry --> IntentRecognizer;
  SpeechToText --> InputProcessor;
  IntentRecognizer --> InputProcessor;
  SessionMemoryAgent --> InputProcessor;
  SessionMemoryAgent --> RequestCoordinator;
  ContextManager --> RequestCoordinator;
  ErrorBus --> RequestCoordinator;
  ServiceRegistry --> RequestCoordinator;
  MemoryClient --> GoalManager;
  ErrorBus --> GoalManager;
  ServiceRegistry --> GoalManager;
  ModelOrchestrator --> ResponseGenerator;
  MemoryClient --> ResponseGenerator;
  MemoryClient --> TranslationService;
  ErrorBus --> TranslationService;
  ServiceRegistry --> TranslationService;
  ErrorBus --> StreamingTTS;
  ServiceRegistry --> StreamingTTS;
  TaskRouter --> GoalOrchestratorAgent;
  EmotionEngine --> VoiceProfiler;
  IntentionValidatorAgent --> UnifiedPlanningAgent;
  GoalOrchestratorAgent --> UnifiedPlanningAgent;
  UnifiedPlanningAgent --> MultiAgentSwarmManager;
  TaskRouter --> LanguageAndTranslationCoordinator;
  EpisodicMemoryAgent --> LearningAgent;
  CacheManager --> KnowledgeBaseAgent;
```

### Legend

- 🟢 Running agent
- 🔴 Not running agent
- 💻 Main PC agent
- 🖥️ PC2 agent
- 🔄 Has Error Bus integration

## Agents by Machine

### Main PC Agents

 | Agent | Status | Error Bus | Ports | Health Ports | Dependencies | 
 | ------- | -------- | ----------- | ------- | -------------- | ------------- | 
 | AIStudioAssistant | 🔴 Not Running | ❌ | - | - | - | 
 | APIRequestTool | 🔴 Not Running | ❌ | - | - | - | 
 | ActiveLearningMonitor | 🔴 Not Running | ✅ | 5638, 7150, 5591 | 6591 | MemoryClient, LearningManager, ErrorBus, ServiceRegistry | 
 | AdvancedCommandHandler | 🔴 Not Running | ✅ | 5710, 7150 | - | NLUAgent, CodeGenerator | 
 | AdvancedSuggestionSystem | 🔴 Not Running | ❌ | - | - | - | 
 | AdvancedTimeoutManager | 🔴 Not Running | ✅ | 5595, 7150 | - | - | 
 | AgentBase | 🔴 Not Running | ❌ | - | - | - | 
 | AgentRegistry | 🔴 Not Running | ❌ | - | - | - | 
 | AgentStatus | 🔴 Not Running | ❌ | - | - | - | 
 | AutoFixer | 🔴 Not Running | ❌ | - | - | - | 
 | AutoFixerAgent | 🔴 Not Running | ❌ | 7135 | 8135 | HealthMonitor | 
 | AutoGenFramework | 🔴 Not Running | ❌ | - | - | - | 
 | Chitchat | 🔴 Not Running | ✅ | 7150 | - | - | 
 | ChitchatAgent | 🔴 Not Running | ✅ | 7150, 5711 | - | NLUAgent | 
 | CircuitBreaker | 🔴 Not Running | ✅ | 5713, 7140, 7150 | - | - | 
 | CodeCommandHandler | 🔴 Not Running | ❌ | - | - | - | 
 | CodeGenerationIntentHandler | 🔴 Not Running | ❌ | - | - | - | 
 | CodeGenerator | 🔴 Not Running | ✅ | 5604, 7150 | - | ModelManagerAgent | 
 | CodeGeneratorAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | CommandClusteringEngine | 🔴 Not Running | ❌ | - | - | - | 
 | CommandConfirmation | 🔴 Not Running | ❌ | - | - | - | 
 | CommandQueue | 🔴 Not Running | ❌ | - | - | - | 
 | CommandSuggestion | 🔴 Not Running | ❌ | - | - | - | 
 | CommandSuggestionOptimized | 🔴 Not Running | ❌ | - | - | - | 
 | ConnectionPool | 🔴 Not Running | ✅ | 7150 | - | - | 
 | ContextBridge | 🔴 Not Running | ❌ | - | - | - | 
 | ContextBridgeAgent | 🔴 Not Running | ❌ | - | - | - | 
 | ContextManager | 🔴 Not Running | ✅ | 7112, 5716, 7150, 7111 | 7112, 6716, 8111 | SessionMemoryAgent, MemoryManager, ErrorBus, MemoryClient | 
 | ContextSummarizer | 🔴 Not Running | ❌ | 5592 | 6592 | MemoryClient, ContextManager, ErrorBus, ServiceRegistry | 
 | ContextSummarizerAgent | 🔴 Not Running | ❌ | - | - | - | 
 | CoordinatorModule | 🔴 Not Running | ❌ | - | - | - | 
 | CustomCommandHandler | 🔴 Not Running | ❌ | - | - | - | 
 | DataExtractionTool | 🔴 Not Running | ❌ | - | - | - | 
 | DigitalTwin | 🔴 Not Running | ❌ | - | - | - | 
 | DigitalTwinAgent | 🔴 Not Running | ❌ | - | - | - | 
 | Discovery | 🔴 Not Running | ❌ | - | - | - | 
 | DiscoveryService | 🔴 Not Running | ❌ | - | - | - | 
 | DiskUsageInfo | 🔴 Not Running | ❌ | - | - | - | 
 | DistributedLauncher | 🔴 Not Running | ❌ | - | - | - | 
 | DynamicIdentity | 🔴 Not Running | ✅ | 7150 | - | - | 
 | DynamicIdentityAgent | 🔴 Not Running | ✅ | 5702, 7150 | - | TaskRouter | 
 | DynamicSTTModelManager | 🔴 Not Running | ❌ | - | - | - | 
 | EmotionEngine | 🔴 Not Running | ✅ | 7150, 5575 | - | - | 
 | EmotionSynthesis | 🔴 Not Running | ✅ | 7150 | - | - | 
 | EmotionSynthesisAgent | 🔴 Not Running | ✅ | 5706, 7150 | - | CoordinatorAgent, ModelManagerAgent | 
 | Empathy | 🔴 Not Running | ✅ | 7150 | - | - | 
 | EmpathyAgent | 🔴 Not Running | ✅ | 7150, 5703 | - | EmotionEngine | 
 | ErrorHandler | 🔴 Not Running | ❌ | - | - | - | 
 | ErrorRecord | 🔴 Not Running | ❌ | - | - | - | 
 | ErrorSeverity | 🔴 Not Running | ❌ | - | - | - | 
 | Executor | 🔴 Not Running | ✅ | 5606, 7150 | - | - | 
 | ExecutorAgent | 🟢 Running | ✅ | 7150 | - | - | 
 | ExperienceMemory | 🔴 Not Running | ❌ | - | - | - | 
 | FaceRecognition | 🔴 Not Running | ✅ | 7150 | - | - | 
 | FaceRecognitionAgent | 🔴 Not Running | ✅ | 5610, 7150 | - | ModelManagerAgent, TaskRouter | 
 | FeedbackHandler | 🔴 Not Running | ✅ | 5636, 7150 | - | NLUAgent | 
 | FileOperationTool | 🔴 Not Running | ❌ | - | - | - | 
 | FileSystemAssistant | 🔴 Not Running | ✅ | 7150 | - | - | 
 | FileSystemAssistantAgent | 🔴 Not Running | ✅ | 7123, 7150 | 8123 | UnifiedUtilsAgent | 
 | FixedStreamingTranslation | 🔴 Not Running | ✅ | 7150 | - | - | 
 | FusedAudioPreprocessor | 🔴 Not Running | ✅ | 6578, 7150 | - | AudioCapture | 
 | FusedAudioPreprocessorAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | GGUFModelManager | 🔴 Not Running | ✅ | 7150 | - | - | 
 | GGUFStateTracker | 🔴 Not Running | ✅ | 7150 | - | - | 
 | Goal | 🔴 Not Running | ❌ | - | - | - | 
 | HumanAwareness | 🔴 Not Running | ✅ | 7150 | - | - | 
 | HumanAwarenessAgent | 🔴 Not Running | ✅ | 5705, 7150 | - | EmotionEngine | 
 | IntentionValidator | 🔴 Not Running | ✅ | 7150 | - | - | 
 | IntentionValidatorAgent | 🔴 Not Running | ✅ | 5701, 7150 | - | TaskRouter | 
 | KnowledgeBase | 🔴 Not Running | ✅ | 5578, 5715, 7150 | 6715 | ErrorBus, MemoryClient | 
 | LazyVotingSystem | 🔴 Not Running | ❌ | - | - | - | 
 | LearningManager | 🔴 Not Running | ✅ | 5579, 7150 | - | CoordinatorAgent, MemoryClient | 
 | LearningOpportunityDetector | 🔴 Not Running | ✅ | 7150, 5710 | - | - | 
 | LearningOrchestration | 🔴 Not Running | ✅ | 5720, 7150 | - | - | 
 | LivenessDetector | 🔴 Not Running | ✅ | 7150 | - | - | 
 | MemoryOrchestrator | 🔴 Not Running | ✅ | 5576, 7150 | - | - | 
 | Message | 🔴 Not Running | ❌ | - | - | - | 
 | MessageBus | 🔴 Not Running | ❌ | - | - | - | 
 | MetaCognition | 🔴 Not Running | ✅ | 7150 | - | - | 
 | MetaCognitionAgent | 🔴 Not Running | ✅ | 5630, 7150 | - | CoordinatorAgent, KnowledgeBase | 
 | ModelManager | 🔴 Not Running | ✅ | 5604, 7150 | - | - | 
 | ModelManagerAgent | 🔴 Not Running | ✅ | 5570, 5604, 7150 | - | - | 
 | ModelOrchestrator | 🔴 Not Running | ❌ | 5571 | 6571 | MemoryClient, ContextManager, ErrorBus, ServiceRegistry | 
 | ModelVotingAdapter | 🔴 Not Running | ❌ | - | - | - | 
 | MoodTracker | 🔴 Not Running | ✅ | 7150 | - | - | 
 | MoodTrackerAgent | 🔴 Not Running | ✅ | 5704, 7150 | - | EmotionEngine | 
 | NLU | 🔴 Not Running | ✅ | 7150 | - | - | 
 | NLUAgent | 🔴 Not Running | ✅ | 5709, 7150 | - | LanguageAndTranslationCoordinator | 
 | NoiseReduction | 🔴 Not Running | ❌ | - | - | - | 
 | NoiseReductionAgent | 🔴 Not Running | ❌ | - | - | - | 
 | PerformanceMetrics | 🔴 Not Running | ✅ | 7150 | - | - | 
 | PerformanceMonitor | 🔴 Not Running | ✅ | 7150, 7103 | 8103 | HealthMonitor | 
 | PersonalityEngine | 🔴 Not Running | ❌ | - | - | - | 
 | Plan | 🔴 Not Running | ❌ | - | - | - | 
 | PluginEventHandler | 🔴 Not Running | ❌ | - | - | - | 
 | PredictiveHealthMonitor | 🔴 Not Running | ✅ | 5613, 7150 | - | - | 
 | PredictiveLoader | 🔴 Not Running | ✅ | 5617, 7150 | - | TaskRouter | 
 | PrivacyManager | 🔴 Not Running | ✅ | 7150 | - | - | 
 | Proactive | 🔴 Not Running | ✅ | 5624, 7150 | - | - | 
 | ProactiveAgent | 🔴 Not Running | ✅ | 5624, 7150 | - | TaskRouter | 
 | RecoveryAction | 🔴 Not Running | ❌ | - | - | - | 
 | RemoteConnector | 🔴 Not Running | ✅ | 7150 | - | - | 
 | RemoteConnectorAgent | 🔴 Not Running | ✅ | 7124, 7150 | 8124 | AdvancedRouter | 
 | ResourceManager | 🔴 Not Running | ✅ | 7113, 7114, 7150 | 8113, 7114 | - | 
 | ResourceType | 🔴 Not Running | ✅ | 5720, 7150 | - | - | 
 | Responder | 🔴 Not Running | ✅ | 5637, 7150 | - | EmotionEngine, NLUAgent | 
 | ResponderAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | SecureClient | 🔴 Not Running | ❌ | 5555 | - | - | 
 | SecureServer | 🔴 Not Running | ❌ | 5555 | - | - | 
 | SelfHealing | 🔴 Not Running | ❌ | - | - | - | 
 | SelfHealingAgent | 🔴 Not Running | ❌ | 7125 | 8125 | PerformanceLoggerAgent | 
 | SelfHealingDatabase | 🔴 Not Running | ❌ | - | - | - | 
 | Session | 🔴 Not Running | ❌ | - | - | - | 
 | SessionAgent | 🔴 Not Running | ❌ | - | - | - | 
 | SessionMemory | 🔴 Not Running | ✅ | 7150 | - | - | 
 | SessionMemoryAgent | 🔴 Not Running | ✅ | 5572, 5574, 7150 | 6583 | CoordinatorAgent, ErrorBus, MemoryClient | 
 | SpeechProcessor | 🔴 Not Running | ❌ | - | - | - | 
 | StreamingAudioCapture | 🔴 Not Running | ✅ | 7150, 6575 | - | - | 
 | StreamingAudioCaptureAgent | 🔴 Not Running | ✅ | 7150, 6575 | - | - | 
 | StreamingInterrupt | 🔴 Not Running | ❌ | - | - | - | 
 | StreamingInterruptHandler | 🔴 Not Running | ✅ | 7150 | - | - | 
 | StreamingLanguageAnalyzer | 🔴 Not Running | ✅ | 7150 | - | - | 
 | StreamingLanguageToLLM | 🔴 Not Running | ❌ | - | - | - | 
 | StreamingPartialTranscripts | 🔴 Not Running | ❌ | - | - | - | 
 | StreamingSpeechRecognition | 🔴 Not Running | ✅ | 6580, 7150 | - | TaskRouter | 
 | StreamingWhisperASR | 🔴 Not Running | ❌ | - | - | - | 
 | SystemDigitalTwin | 🔴 Not Running | ✅ | 7120, 5590, 7150 | 6590 | MemoryClient, ErrorBus, ServiceRegistry | 
 | SystemDigitalTwinAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | SystemResourceSnapshot | 🔴 Not Running | ❌ | - | - | - | 
 | TTS | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TTSAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TTSCache | 🔴 Not Running | ✅ | 5628, 7150 | - | - | 
 | Task | 🔴 Not Running | ❌ | - | - | - | 
 | TelemetryDashboardHandler | 🔴 Not Running | ❌ | - | - | - | 
 | TelemetryServer | 🔴 Not Running | ❌ | - | - | - | 
 | TextRequest | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TimelineUIServer | 🔴 Not Running | ❌ | - | - | - | 
 | ToneDetector | 🔴 Not Running | ✅ | 5625, 7150 | - | EmotionEngine | 
 | Tool | 🔴 Not Running | ❌ | - | - | - | 
 | Translation | 🔴 Not Running | ❌ | 5595 | - | - | 
 | TranslationCache | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TriggerWordDetector | 🔴 Not Running | ❌ | - | - | - | 
 | UltimateTTS | 🔴 Not Running | ✅ | 7150 | - | - | 
 | UltimateTTSAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | UnifiedSystem | 🔴 Not Running | ❌ | - | - | - | 
 | UnifiedSystemAgent | 🔴 Not Running | ❌ | 5640 | - | UnifiedPlanningAgent | 
 | UserProfile | 🔴 Not Running | ❌ | - | - | - | 
 | VAD | 🔴 Not Running | ❌ | - | - | - | 
 | VADAgent | 🔴 Not Running | ❌ | - | - | - | 
 | VRAMManager | 🔴 Not Running | ❌ | - | - | - | 
 | VRAMOptimizer | 🔴 Not Running | ✅ | 7120, 7150 | - | - | 
 | VRAMOptimizerAgent | 🔴 Not Running | ✅ | 7120, 7150 | - | - | 
 | VisionCapture | 🔴 Not Running | ✅ | 7150 | - | - | 
 | VisionCaptureAgent | 🔴 Not Running | ✅ | 5592, 7150 | - | - | 
 | VoiceController | 🔴 Not Running | ❌ | - | - | - | 
 | VoiceMeeterControl | 🔴 Not Running | ❌ | - | - | - | 
 | VoiceMeeterControlAgent | 🔴 Not Running | ❌ | - | - | - | 
 | VoiceProfiling | 🔴 Not Running | ✅ | 7150 | - | - | 
 | VoiceProfilingAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | WakeWordDetector | 🔴 Not Running | ✅ | 6577, 7150 | - | FusedAudioPreprocessor, AudioCapture | 
 | WakeWordDetectorAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | WebSearchTool | 🔴 Not Running | ❌ | - | - | - | 
 | ZMQAuthenticator | 🔴 Not Running | ❌ | - | - | - | 
 | ZMQClient | 🔴 Not Running | ❌ | - | - | - | 
 | ZMQPublisher | 🔴 Not Running | ❌ | - | - | - | 
 | ZMQServer | 🔴 Not Running | ❌ | - | - | - | 
 | ZMQSubscriber | 🔴 Not Running | ❌ | - | - | - | 
 | and | 🔴 Not Running | ❌ | 8120 | 8120 | - | 
 | base_suggestions | 🔴 Not Running | ❌ | - | - | - | 
 | class | 🔴 Not Running | ✅ | 7150 | - | - | 
 | for | 🔴 Not Running | ❌ | - | - | - | 
 | from | 🔴 Not Running | ✅ | 7150 | - | - | 
 | if | 🔴 Not Running | ❌ | - | - | - | 
 | names | 🔴 Not Running | ❌ | - | - | - | 
 | super | 🔴 Not Running | ❌ | - | - | - | 
 | to | 🟢 Running | ❌ | - | - | - | 
 | with | 🔴 Not Running | ❌ | - | - | - | 

### PC2 Agents

 | Agent | Status | Error Bus | Ports | Health Ports | Dependencies | 
 | ------- | -------- | ----------- | ------- | -------------- | ------------- | 
 | AdvancedRouter | 🔴 Not Running | ✅ | 7129, 5555, 7150 | 8129 | TaskScheduler | 
 | AdvancedTutoring | 🔴 Not Running | ✅ | 5650, 7150 | - | - | 
 | AdvancedTutoringAgent | 🔴 Not Running | ✅ | 5650, 7150 | - | - | 
 | AgentStatus | 🔴 Not Running | ❌ | - | - | - | 
 | AgentTrustScorer | 🔴 Not Running | ✅ | 7122, 5626, 7150 | 8122 | HealthMonitor | 
 | Authentication | 🔴 Not Running | ✅ | 7150 | - | - | 
 | CacheManager | 🔴 Not Running | ✅ | 7102, 7150 | 8102 | AsyncProcessor | 
 | ContextManager | 🔴 Not Running | ✅ | 7112, 5716, 7150, 7111 | 7112, 6716, 8111 | SessionMemoryAgent, MemoryManager, ErrorBus, MemoryClient | 
 | DreamWorld | 🔴 Not Running | ✅ | 7150 | - | - | 
 | DreamingMode | 🔴 Not Running | ✅ | 7150 | - | - | 
 | DreamingModeAgent | 🔴 Not Running | ✅ | 7150, 7127 | 8127 | DreamWorldAgent | 
 | DummyArgs | 🔴 Not Running | ✅ | 7150 | - | - | 
 | EpisodicMemory | 🔴 Not Running | ❌ | 7106 | - | - | 
 | EpisodicMemoryAgent | 🔴 Not Running | ❌ | 7106, 5596 | 8106 | UnifiedMemoryReasoningAgent | 
 | ErrorCollectorModule | 🔴 Not Running | ❌ | - | - | - | 
 | ErrorPattern | 🔴 Not Running | ❌ | - | - | - | 
 | ExperienceTracker | 🔴 Not Running | ✅ | 7112, 7113, 7106, 7150 | 8112, 7113 | EpisodicMemoryAgent | 
 | ExperienceTrackerAgent | 🔴 Not Running | ✅ | 7112, 7113, 7106, 7150 | 7113 | - | 
 | FileSystemAssistant | 🔴 Not Running | ✅ | 7150 | - | - | 
 | FileSystemAssistantAgent | 🔴 Not Running | ✅ | 7123, 7150 | 8123 | UnifiedUtilsAgent | 
 | HealthMonitor | 🔴 Not Running | ✅ | 7152, 7114, 7115, 7150 | 7153, 8114, 7115 | ServiceRegistry, ErrorBus, ResourceManager | 
 | HealthMonitorAgent | 🔴 Not Running | ✅ | 7114, 7115, 7150 | 7115 | - | 
 | LearningAdjuster | 🔴 Not Running | ❌ | - | - | - | 
 | LearningAdjusterAgent | 🔴 Not Running | ❌ | 5643 | - | - | 
 | MemoryEntry | 🔴 Not Running | ✅ | 7150 | - | - | 
 | MemoryManager | 🔴 Not Running | ❌ | 7110 | 8110 | UnifiedMemoryReasoningAgent | 
 | MemoryOrchestrator | 🔴 Not Running | ✅ | 5576, 7150 | - | - | 
 | MemoryScheduler | 🔴 Not Running | ✅ | 7140, 7150 | - | - | 
 | ModelEvaluationFramework | 🔴 Not Running | ✅ | 7150 | - | - | 
 | Orchestrator | 🔴 Not Running | ❌ | - | - | - | 
 | OrchestratorAgent | 🔴 Not Running | ❌ | - | - | - | 
 | PerformanceLogger | 🔴 Not Running | ✅ | 7150 | - | - | 
 | PerformanceLoggerAgent | 🔴 Not Running | ✅ | 7128, 7150 | 8128 | PerformanceMonitor | 
 | PerformanceMonitor | 🔴 Not Running | ✅ | 7150, 7103 | 8103 | HealthMonitor | 
 | ProactiveContextMonitor | 🔴 Not Running | ❌ | 7119 | 8119 | ContextManager | 
 | RemoteConnector | 🔴 Not Running | ✅ | 7150 | - | - | 
 | RemoteConnectorAgent | 🔴 Not Running | ✅ | 7124, 7150 | 8124 | AdvancedRouter | 
 | ResourceManager | 🔴 Not Running | ✅ | 7113, 7114, 7150 | 8113, 7114 | - | 
 | ResourceMonitor | 🔴 Not Running | ✅ | 7102, 7150, 7103 | - | - | 
 | ScenarioType | 🔴 Not Running | ✅ | 7150 | - | - | 
 | SystemHealthManager | 🔴 Not Running | ✅ | 7140, 7150, 7142 | - | - | 
 | TaskQueue | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TaskScheduler | 🔴 Not Running | ✅ | 7115, 7116, 5555, 7150 | 8115, 7116 | HealthMonitor, AsyncProcessor | 
 | TaskSchedulerAgent | 🔴 Not Running | ✅ | 7115, 7116, 5555, 7150 | 7116 | - | 
 | TestCompliant | 🔴 Not Running | ❌ | - | - | - | 
 | TieredResponder | 🔴 Not Running | ✅ | 7100, 7150 | 8100 | ResourceManager | 
 | Tutor | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TutoringService | 🔴 Not Running | ✅ | 7150 | - | - | 
 | TutoringServiceAgent | 🔴 Not Running | ✅ | 7130, 7150 | 8130 | UnifiedMemoryReasoningAgent | 
 | UnifiedMemoryReasoning | 🔴 Not Running | ❌ | - | - | - | 
 | UnifiedMemoryReasoningAgent | 🔴 Not Running | ❌ | 7105, 5596 | 8105 | HealthMonitor, MemoryOrchestrator, CacheManager | 
 | UnifiedMonitor | 🔴 Not Running | ❌ | - | - | - | 
 | UnifiedUtils | 🔴 Not Running | ✅ | 7150 | - | - | 
 | UnifiedWeb | 🔴 Not Running | ✅ | 7150 | - | - | 
 | UnifiedWebAgent | 🔴 Not Running | ✅ | 7126, 7150 | 8126 | UnifiedMemoryReasoningAgent, FileSystemAssistantAgent | 
 | VisionProcessing | 🔴 Not Running | ✅ | 7150 | - | - | 
 | VisionProcessingAgent | 🔴 Not Running | ✅ | 7150 | - | - | 
 | class | 🔴 Not Running | ✅ | 7150 | - | - | 
 | definitions | 🔴 Not Running | ✅ | 5555, 7150 | - | - | 
 | for | 🔴 Not Running | ❌ | - | - | - | 
 | from | 🔴 Not Running | ✅ | 7150 | - | - | 

## Detailed Agent Information

### AIStudioAssistant

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/ai_studio_assistant.py`

### APIRequestTool

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### ActiveLearningMonitor

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5638, 7150, 5591
- **Health Check Ports**: 6591
- **Dependencies**: MemoryClient, LearningManager, ErrorBus, ServiceRegistry
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/active_learning_monitor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AdvancedCommandHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5710, 7150
- **Dependencies**: NLUAgent, CodeGenerator
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/advanced_command_handler.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AdvancedRouter

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7129, 5555, 7150
- **Health Check Ports**: 8129
- **Dependencies**: TaskScheduler
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/advanced_router.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/advanced_router.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/advanced_router.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/advanced_router.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/advanced_router.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AdvancedSuggestionSystem

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/advanced_suggestion_system.py`

### AdvancedTimeoutManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5595, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fixed_streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/translation_service.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/fixed_streaming_translation.py`

### AdvancedTutoring

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 5650, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tutoring_agent.py`

### AdvancedTutoringAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 5650, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tutoring_agent.py`

### AgentBase

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/agent_utils.py`

### AgentRegistry

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autogen_framework.py`

### AgentStatus

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/self_healing_agent.py`

### AgentTrustScorer

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7122, 5626, 7150
- **Health Check Ports**: 8122
- **Dependencies**: HealthMonitor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/AgentTrustScorer.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/AgentTrustScorer.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/AgentTrustScorer.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/AgentTrustScorer.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/AgentTrustScorer.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/AgentTrustScorer.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AgentUtils

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7136
- **Health Check Ports**: 8136
- **Dependencies**: UnifiedUtilsAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/agent_utils.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/agent_utils.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/agent_utils.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/agent_utils.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### AlertManager

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5593
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AsyncProcessor

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7101
- **Health Check Ports**: 8101
- **Dependencies**: ResourceManager
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/async_processor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/async_processor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/async_processor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/async_processor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AudioCapture

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 6575
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### Authentication

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/AuthenticationAgent.py`

### AuthenticationAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7116
- **Health Check Ports**: 8116
- **Dependencies**: HealthMonitor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/AuthenticationAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/AuthenticationAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/AuthenticationAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/AuthenticationAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### AutoFixer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/auto_fixer_agent.py`

### AutoFixerAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 7135
- **Health Check Ports**: 8135
- **Dependencies**: HealthMonitor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/auto_fixer_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/auto_fixer_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/auto_fixer_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/auto_fixer_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/auto_fixer_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### AutoGenFramework

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autogen_framework.py`

### CacheManager

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7102, 7150
- **Health Check Ports**: 8102
- **Dependencies**: AsyncProcessor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/cache_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/cache_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/cache_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/cache_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/cache_manager.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ChainOfThoughtAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5612
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### Chitchat

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/chitchat_agent.py`

### ChitchatAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 5711
- **Dependencies**: NLUAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/chitchat_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### CircuitBreaker

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5713, 7140, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/memory_client.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/goal_manager.py`

### CodeCommandHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/code_command_handler.py`

### CodeGenerationIntentHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/intent_handlers/code_generation_intent.py`

### CodeGenerator

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5604, 7150
- **Dependencies**: ModelManagerAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/code_generator_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### CodeGeneratorAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/code_generator_agent.py`

### CognitiveModelAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5641
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### CommandClusteringEngine

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/command_clustering.py`

### CommandConfirmation

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/command_confirmation.py`

### CommandQueue

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/command_queue.py`

### CommandSuggestion

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/command_suggestion.py`

### CommandSuggestionOptimized

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/command_suggestion_optimized.py`

### ConnectionPool

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_connector.py`

### ConsolidatedTranslator

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5563
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ContextBridge

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/context_bridge_agent.py`

### ContextBridgeAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/context_bridge_agent.py`

### ContextManager

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7112, 5716, 7150, 7111
- **Health Check Ports**: 7112, 6716, 8111
- **Dependencies**: SessionMemoryAgent, MemoryManager, ErrorBus, MemoryClient
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/context_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/context_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/context_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/context_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/context_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/context_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/context_manager.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ContextSummarizer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 5592
- **Health Check Ports**: 6592
- **Dependencies**: MemoryClient, ContextManager, ErrorBus, ServiceRegistry
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/core_memory/context_summarizer_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### ContextSummarizerAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/core_memory/context_summarizer_agent.py`

### CoordinatorModule

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/coordinator.py`

### CustomCommandHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/custom_command_handler.py`

### DataExtractionTool

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### DigitalTwin

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/digital_twin_agent.py`

### DigitalTwinAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/digital_twin_agent.py`

### Discovery

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/discovery_service.py`

### DiscoveryService

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/discovery_service.py`

### DiskUsageInfo

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/src/core/unified_monitoring.py`

### DistributedLauncher

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/distributed_launcher.py`

### DreamWorld

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`

### DreamWorldAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7104
- **Health Check Ports**: 8104
- **Dependencies**: UnifiedMemoryReasoningAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### DreamingMode

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamingModeAgent.py`

### DreamingModeAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150, 7127
- **Health Check Ports**: 8127
- **Dependencies**: DreamWorldAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamingModeAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamingModeAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamingModeAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamingModeAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamingModeAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### DummyArgs

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/proactive_context_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_utils_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/AuthenticationAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/proactive_context_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/unified_utils_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/DreamingModeAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/rca_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/UnifiedErrorAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/AuthenticationAgent.py`

### DynamicIdentity

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/DynamicIdentityAgent.py`

### DynamicIdentityAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5702, 7150
- **Dependencies**: TaskRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/DynamicIdentityAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### DynamicSTTModelManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/stt/dynamic_stt_manager.py`

### EmotionEngine

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 5575
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/emotion_engine.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### EmotionSynthesis

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/emotion_synthesis_agent.py`

### EmotionSynthesisAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5706, 7150
- **Dependencies**: CoordinatorAgent, ModelManagerAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/emotion_synthesis_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### Empathy

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/EmpathyAgent.py`

### EmpathyAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 5703
- **Dependencies**: EmotionEngine
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/EmpathyAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### EnhancedContextualMemory

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7134
- **Health Check Ports**: 8134
- **Dependencies**: MemoryManager
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### EnhancedModelRouter

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5598
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### EpisodicMemory

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Ports**: 7106
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/EpisodicMemoryAgent.py`

### EpisodicMemoryAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Ports**: 7106, 5596
- **Health Check Ports**: 8106
- **Dependencies**: UnifiedMemoryReasoningAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/EpisodicMemoryAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ErrorBus

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7150
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### ErrorCollectorModule

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/Error_Management_System.py`

### ErrorHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/error_handler.py`

### ErrorPattern

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/rca_agent.py`

### ErrorRecord

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`

### ErrorSeverity

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/error_handler.py`

### Executor

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5606, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/executor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ExecutorAgent

- **Status**: 🟢 Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/executor.py`

### ExperienceMemory

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### ExperienceTracker

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7112, 7113, 7106, 7150
- **Health Check Ports**: 8112, 7113
- **Dependencies**: EpisodicMemoryAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/experience_tracker.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/experience_tracker.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/experience_tracker.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/experience_tracker.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/experience_tracker.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/experience_tracker.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ExperienceTrackerAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7112, 7113, 7106, 7150
- **Health Check Ports**: 7113
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/experience_tracker.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/experience_tracker.py`

### FaceRecognition

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/face_recognition_agent.py`

### FaceRecognitionAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5610, 7150
- **Dependencies**: ModelManagerAgent, TaskRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/face_recognition_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### FeedbackHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5636, 7150
- **Dependencies**: NLUAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/feedback_handler.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### FileOperationTool

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### FileSystemAssistant

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/filesystem_assistant_agent.py`

### FileSystemAssistantAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7123, 7150
- **Health Check Ports**: 8123
- **Dependencies**: UnifiedUtilsAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/filesystem_assistant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/filesystem_assistant_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### FixedStreamingTranslation

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fixed_streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/fixed_streaming_translation.py`

### FusedAudioPreprocessor

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 6578, 7150
- **Dependencies**: AudioCapture
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fused_audio_preprocessor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### FusedAudioPreprocessorAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fused_audio_preprocessor.py`

### GGUFModelManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/gguf_model_manager.py`

### GGUFStateTracker

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/gguf_model_manager.py`

### GOT_TOTAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5646
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### Goal

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### GoalManager

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5572
- **Health Check Ports**: 6572
- **Dependencies**: MemoryClient, ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### GoalOrchestratorAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7001
- **Dependencies**: TaskRouter
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### HealthCheck

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5591
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### HealthMonitor

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7152, 7114, 7115, 7150
- **Health Check Ports**: 7153, 8114, 7115
- **Dependencies**: ServiceRegistry, ErrorBus, ResourceManager
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/src/core/health_monitor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### HealthMonitorAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7114, 7115, 7150
- **Health Check Ports**: 7115
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/health_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/health_monitor.py`

### HumanAwareness

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/human_awareness_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/HumanAwarenessAgent.py`

### HumanAwarenessAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5705, 7150
- **Dependencies**: EmotionEngine
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/human_awareness_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/HumanAwarenessAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### InputProcessor

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5562
- **Health Check Ports**: 6562
- **Dependencies**: SpeechToText, IntentRecognizer, SessionMemoryAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### IntentRecognizer

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5561
- **Health Check Ports**: 6561
- **Dependencies**: MemoryClient, ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### IntentionValidator

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/IntentionValidatorAgent.py`

### IntentionValidatorAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5701, 7150
- **Dependencies**: TaskRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/IntentionValidatorAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### KnowledgeBase

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5578, 5715, 7150
- **Health Check Ports**: 6715
- **Dependencies**: ErrorBus, MemoryClient
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/knowledge_base.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### KnowledgeBaseAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7109
- **Dependencies**: CacheManager
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### LanguageAndTranslationCoordinator

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 6581
- **Dependencies**: TaskRouter
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### LazyVotingSystem

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/lazy_voting.py`

### LearningAdjuster

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/LearningAdjusterAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/LearningAdjusterAgent.py`

### LearningAdjusterAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Ports**: 5643
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/LearningAdjusterAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/LearningAdjusterAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### LearningAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7107
- **Dependencies**: EpisodicMemoryAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### LearningManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5579, 7150
- **Dependencies**: CoordinatorAgent, MemoryClient
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/learning_manager.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### LearningOpportunityDetector

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 5710
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/learning_opportunity_detector.py`

### LearningOrchestration

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5720, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/learning_orchestration_service.py`

### LivenessDetector

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/face_recognition_agent.py`

### LocalFineTunerAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5645
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### MemoryClient

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5713
- **Dependencies**: ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### MemoryDecayManager

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7133
- **Health Check Ports**: 8133
- **Dependencies**: UnifiedMemoryReasoningAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### MemoryEntry

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/memory_orchestrator_service.py`

### MemoryManager

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Ports**: 7110
- **Health Check Ports**: 8110
- **Dependencies**: UnifiedMemoryReasoningAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/memory_manager.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### MemoryOrchestrator

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5576, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/memory_orchestrator.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/memory_orchestrator_service.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### MemoryScheduler

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7140, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/memory_scheduler.py`

### Message

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autogen_framework.py`

### MessageBus

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autogen_framework.py`

### MetaCognition

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/MetaCognitionAgent.py`

### MetaCognitionAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5630, 7150
- **Dependencies**: CoordinatorAgent, KnowledgeBase
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/MetaCognitionAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### MetricsCollector

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5592
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ModelEvaluationFramework

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/model_evaluation_framework.py`

### ModelManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5604, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/model_manager_agent.py`

### ModelManagerAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5570, 5604, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/model_manager_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ModelOrchestrator

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 5571
- **Health Check Ports**: 6571
- **Dependencies**: MemoryClient, ContextManager, ErrorBus, ServiceRegistry
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/model_orchestrator.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### ModelVotingAdapter

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/model_voting_adapter.py`

### MoodTracker

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/mood_tracker_agent.py`

### MoodTrackerAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5704, 7150
- **Dependencies**: EmotionEngine
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/mood_tracker_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### MultiAgentSwarmManager

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5639
- **Dependencies**: UnifiedPlanningAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### NLLBAdapter

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5581
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### NLU

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/nlu_agent.py`

### NLUAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5709, 7150
- **Dependencies**: LanguageAndTranslationCoordinator
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/nlu_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### NoiseReduction

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/noise_reduction_agent.py`

### NoiseReductionAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/noise_reduction_agent.py`

### Orchestrator

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_monitoring.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/health_monitor.py`

### OrchestratorAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/health_monitor.py`

### PerformanceLogger

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/PerformanceLoggerAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/PerformanceLoggerAgent.py`

### PerformanceLoggerAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7128, 7150
- **Health Check Ports**: 8128
- **Dependencies**: PerformanceMonitor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/PerformanceLoggerAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/PerformanceLoggerAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/PerformanceLoggerAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/PerformanceLoggerAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/PerformanceLoggerAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/PerformanceLoggerAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### PerformanceMetrics

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fixed_streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/fixed_streaming_translation.py`

### PerformanceMonitor

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 7103
- **Health Check Ports**: 8103
- **Dependencies**: HealthMonitor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fixed_streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/fixed_streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/performance_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/performance_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/performance_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/performance_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/performance_monitor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### PersonalityEngine

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/personality_engine.py`

### Plan

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### PluginEventHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/plugin_manager.py`

### PredictiveHealthMonitor

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5613, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/predictive_health_monitor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### PredictiveLoader

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5617, 7150
- **Dependencies**: TaskRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/predictive_loader.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### PrivacyManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/face_recognition_agent.py`

### Proactive

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5624, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/ProactiveAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/proactive.py`

### ProactiveAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5624, 7150
- **Dependencies**: TaskRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/ProactiveAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/proactive.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ProactiveContextMonitor

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Ports**: 7119
- **Health Check Ports**: 8119
- **Dependencies**: ContextManager
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/proactive_context_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/proactive_context_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/proactive_context_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/proactive_context_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/proactive_context_monitor.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### RCAAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7121
- **Health Check Ports**: 8121
- **Dependencies**: HealthMonitor, SelfHealingAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### RecoveryAction

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`

### RemoteConnector

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/remote_connector_agent.py`

### RemoteConnectorAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7124, 7150
- **Health Check Ports**: 8124
- **Dependencies**: AdvancedRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/remote_connector_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/remote_connector_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### RequestCoordinator

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5570
- **Health Check Ports**: 6570
- **Dependencies**: SessionMemoryAgent, ContextManager, ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### ResourceManager

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7113, 7114, 7150
- **Health Check Ports**: 8113, 7114
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_speech_recognition.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/resource_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/async_processor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/resource_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/async_processor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/resource_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/resource_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/resource_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/resource_manager.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ResourceMonitor

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7102, 7150, 7103
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/performance_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/cache_manager.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/performance_monitor.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/cache_manager.py`

### ResourceType

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5720, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/learning_orchestration_service.py`

### Responder

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5637, 7150
- **Dependencies**: EmotionEngine, NLUAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/responder.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ResponderAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/responder.py`

### ResponseGenerator

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5580
- **Health Check Ports**: 6580
- **Dependencies**: ModelOrchestrator, MemoryClient
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### ScenarioType

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`

### SecureClient

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 5555
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/src/core/secure_agent_template.py`

### SecureServer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 5555
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/src/core/secure_agent_template.py`

### SelfHealing

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`

### SelfHealingAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 7125
- **Health Check Ports**: 8125
- **Dependencies**: PerformanceLoggerAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### SelfHealingDatabase

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`

### SelfTrainingOrchestrator

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5644
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ServiceRegistry

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7151
- **Dependencies**: ErrorBus
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### Session

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/SessionAgent.py`

### SessionAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/SessionAgent.py`

### SessionMemory

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/session_memory_agent.py`

### SessionMemoryAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5572, 5574, 7150
- **Health Check Ports**: 6583
- **Dependencies**: CoordinatorAgent, ErrorBus, MemoryClient
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/session_memory_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### SpeechProcessor

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/speech_processor.py`

### SpeechToText

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5560
- **Health Check Ports**: 6560
- **Dependencies**: ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### StreamingAudioCapture

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 6575
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_audio_capture.py`

### StreamingAudioCaptureAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150, 6575
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_audio_capture.py`

### StreamingInterrupt

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_interrupt.py`

### StreamingInterruptHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_interrupt_handler.py`

### StreamingLanguageAnalyzer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_language_analyzer.py`

### StreamingLanguageToLLM

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_language_to_llm.py`

### StreamingPartialTranscripts

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_partial_transcripts.py`

### StreamingSpeechRecognition

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 6580, 7150
- **Dependencies**: TaskRouter
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_speech_recognition.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### StreamingTTS

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5582
- **Health Check Ports**: 6582
- **Dependencies**: ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### StreamingTTSAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5562
- **Dependencies**: CoordinatorAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### StreamingWhisperASR

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_whisper_asr.py`

### SystemDigitalTwin

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7120, 5590, 7150
- **Health Check Ports**: 6590
- **Dependencies**: MemoryClient, ErrorBus, ServiceRegistry
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/system_digital_twin.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### SystemDigitalTwinAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/system_digital_twin.py`

### SystemHealthManager

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7140, 7150, 7142
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/system_health_manager.py`

### SystemResourceSnapshot

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`

### TTS

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_agent.py`

### TTSAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_agent.py`

### TTSCache

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5628, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tts_cache.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### TTSConnector

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5582
- **Dependencies**: CoordinatorAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### Task

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autogen_framework.py`

### TaskQueue

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/async_processor.py`

### TaskRouter

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 8570
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### TaskScheduler

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7115, 7116, 5555, 7150
- **Health Check Ports**: 8115, 7116
- **Dependencies**: HealthMonitor, AsyncProcessor
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/task_scheduler.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/task_scheduler.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/task_scheduler.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/task_scheduler.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/task_scheduler.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/task_scheduler.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### TaskSchedulerAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7115, 7116, 5555, 7150
- **Health Check Ports**: 7116
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/task_scheduler.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/task_scheduler.py`

### TelemetryDashboardHandler

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/llm_runtime_tools.py`

### TelemetryServer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/llm_runtime_tools.py`

### TestCompliant

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_compliant_agent.py`

### TextRequest

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/request_coordinator.py`

### TieredResponder

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7100, 7150
- **Health Check Ports**: 8100
- **Dependencies**: ResourceManager
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tiered_responder.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tiered_responder.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### TimelineUIServer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/TimelineUIServer.py`

### TinyLlamaService

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5615
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### ToneDetector

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5625, 7150
- **Dependencies**: EmotionEngine
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/tone_detector.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### Tool

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### Translation

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 5595
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/translation_service.py`

### TranslationCache

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/fixed_streaming_translation.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/fixed_streaming_translation.py`

### TranslationService

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5581
- **Health Check Ports**: 6581
- **Dependencies**: MemoryClient, ErrorBus, ServiceRegistry
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml`

### TriggerWordDetector

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/trigger_word_detector.py`

### Tutor

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutor_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tutor_agent.py`

### TutorAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7108
- **Health Check Ports**: 8108
- **Dependencies**: TutoringServiceAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutor_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutor_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutor_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutor_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### TutoringAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7131, 7108
- **Health Check Ports**: 8131
- **Dependencies**: TutoringServiceAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### TutoringService

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_service_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tutoring_service_agent.py`

### TutoringServiceAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7130, 7150
- **Health Check Ports**: 8130
- **Dependencies**: UnifiedMemoryReasoningAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_service_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tutoring_service_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_service_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_service_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_service_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutoring_service_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### UltimateTTS

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_tts_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/core_speech_output/streaming_tts_agent.py`

### UltimateTTSAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/streaming_tts_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/core_speech_output/streaming_tts_agent.py`

### UnifiedErrorAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7117
- **Health Check Ports**: 8117
- **Dependencies**: HealthMonitor
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### UnifiedMemoryReasoning

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/UnifiedMemoryReasoningAgent.py`

### UnifiedMemoryReasoningAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Ports**: 7105, 5596
- **Health Check Ports**: 8105
- **Dependencies**: HealthMonitor, MemoryOrchestrator, CacheManager
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/UnifiedMemoryReasoningAgent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### UnifiedMemoryReasoningAgentAlt

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7132
- **Health Check Ports**: 8132
- **Dependencies**: CacheManager
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_memory_reasoning_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_memory_reasoning_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_memory_reasoning_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_memory_reasoning_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`

### UnifiedMonitor

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_monitoring.py`

### UnifiedPlanningAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5634
- **Dependencies**: IntentionValidatorAgent, GoalOrchestratorAgent
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### UnifiedSystem

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent2.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent copy.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/UnifiedSystemAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent_backup.py`

### UnifiedSystemAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 5640
- **Dependencies**: UnifiedPlanningAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent2.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent copy.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/UnifiedSystemAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/unified_system_agent_backup.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### UnifiedUtils

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_utils_agent.py`

### UnifiedUtilsAgent

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 7118
- **Health Check Ports**: 8118
- **Dependencies**: UnifiedErrorAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_utils_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_utils_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_utils_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/unified_utils_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### UnifiedWeb

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_web_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/unified_web_agent.py`

### UnifiedWebAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7126, 7150
- **Health Check Ports**: 8126
- **Dependencies**: UnifiedMemoryReasoningAgent, FileSystemAssistantAgent
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_web_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/unified_web_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_web_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_web_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_web_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/unified_web_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config_fixed.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### UserProfile

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/digital_twin_agent.py`

### VAD

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vad_agent.py`

### VADAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vad_agent.py`

### VRAMManager

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_manager copy.py`

### VRAMOptimizer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7120, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_optimizer_agent.py`

### VRAMOptimizerAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7120, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_optimizer_agent.py`

### VisionCapture

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vision_capture_agent.py`

### VisionCaptureAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 5592, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vision_capture_agent.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### VisionProcessing

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/VisionProcessingAgent.py`

### VisionProcessingAgent

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/VisionProcessingAgent.py`

### VoiceController

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/voice_controller.py`

### VoiceMeeterControl

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/voicemeeter_control_agent.py`

### VoiceMeeterControlAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/voicemeeter_control_agent.py`

### VoiceProfiler

- **Status**: 🔴 Not Running
- **Machines**:
- **Error Bus Integration**: No
- **Ports**: 5708
- **Dependencies**: EmotionEngine
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### VoiceProfiling

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/voice_profiling_agent.py`

### VoiceProfilingAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/voice_profiling_agent.py`

### WakeWordDetector

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 6577, 7150
- **Dependencies**: FusedAudioPreprocessor, AudioCapture
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/wake_word_detector.py`
- **Configuration Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/config/source_of_truth_config.yaml`

### WakeWordDetectorAgent

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/wake_word_detector.py`

### WebSearchTool

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`

### ZMQAuthenticator

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/src/network/secure_zmq.py`

### ZMQClient

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/agent_utils.py`

### ZMQPublisher

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/agent_utils.py`

### ZMQServer

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/agent_utils.py`

### ZMQSubscriber

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/agent_utils.py`

### and

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Ports**: 8120
- **Health Check Ports**: 8120
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/system_digital_twin_launcher.py`

### base_suggestions

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/advanced_suggestion_system.py`

### class

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_manager copy.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/tutor_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/tutor_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/DreamWorldAgent.py`

### definitions

- **Status**: 🔴 Not Running
- **Machines**: pc2
- **Error Bus Integration**: Yes
- **Ports**: 5555, 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/advanced_router.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/advanced_router.py`

### for

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autogen_framework.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/agent_utils.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/needtoverify/autonomous_agent_framework.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_compliant_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/utils/pc2_agent_helpers.py`

### from

- **Status**: 🔴 Not Running
- **Machines**: pc2, main_pc
- **Error Bus Integration**: Yes
- **Ports**: 7150
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/face_recognition_agent.py`
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/vram_manager copy.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/DreamWorldAgent.py`
  - `/home/haymayndz/AI_System_Monorepo/pc2_code/agents/backups/DreamWorldAgent.py`

### if

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/self_healing_agent.py`

### names

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/core_memory/context_summarizer_agent.py`

### super

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/advanced_suggestion_system.py`

### to

- **Status**: 🟢 Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/src/network/secure_zmq.py`

### with

- **Status**: 🔴 Not Running
- **Machines**: main_pc
- **Error Bus Integration**: No
- **Implementation Files**:
  - `/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/base_agent.py`

## Recommendations

### Agents Missing Error Bus Integration

The following agents should be updated to integrate with the Error Bus:

- super
- AdvancedSuggestionSystem
- base_suggestions
- TelemetryDashboardHandler
- TelemetryServer
- UnifiedSystem
- UnifiedSystemAgent
- PluginEventHandler
- TriggerWordDetector
- with
- NoiseReduction
- NoiseReductionAgent
- SpeechProcessor
- StreamingWhisperASR
- VoiceMeeterControlAgent
- VoiceMeeterControl
- StreamingPartialTranscripts
- VAD
- VADAgent
- SelfHealingDatabase
- ZMQClient
- ZMQServer
- ZMQSubscriber
- SelfHealingAgent
- RecoveryAction
- SystemResourceSnapshot
- SelfHealing
- if
- AgentBase
- AgentStatus
- for
- ErrorRecord
- ZMQPublisher
- LazyVotingSystem
- PersonalityEngine
- ModelVotingAdapter
- StreamingLanguageToLLM
- StreamingInterrupt
- DigitalTwin
- UserProfile
- DigitalTwinAgent
- Translation
- and
- VoiceController
- ModelOrchestrator
- VRAMManager
- DynamicSTTModelManager
- ContextSummarizer
- names
- ContextSummarizerAgent
- CodeGenerationIntentHandler
- AIStudioAssistant
- TimelineUIServer
- CommandClusteringEngine
- CoordinatorModule
- DiscoveryService
- Discovery
- Task
- AgentRegistry
- AutoGenFramework
- Message
- MessageBus
- CommandConfirmation
- SessionAgent
- Session
- CodeCommandHandler
- AutoFixer
- AutoFixerAgent
- DistributedLauncher
- CommandSuggestionOptimized
- ContextBridge
- ContextBridgeAgent
- CommandSuggestion
- CommandQueue
- ErrorHandler
- ErrorSeverity
- DataExtractionTool
- Plan
- Tool
- Goal
- ExperienceMemory
- FileOperationTool
- APIRequestTool
- WebSearchTool
- CustomCommandHandler
- to
- ZMQAuthenticator
- DiskUsageInfo
- SecureClient
- SecureServer
- TestCompliant
- LearningAdjuster
- LearningAdjusterAgent
- ErrorCollectorModule
- UnifiedMonitor
- Orchestrator
- OrchestratorAgent
- ProactiveContextMonitor
- EpisodicMemory
- EpisodicMemoryAgent
- ErrorPattern
- UnifiedMemoryReasoningAgent
- UnifiedMemoryReasoning
- MemoryManager
- MemoryDecayManager
- EnhancedContextualMemory
- AuthenticationAgent
- UnifiedErrorAgent
- UnifiedUtilsAgent
- AsyncProcessor
- RCAAgent
- DreamWorldAgent
- TutorAgent
- TutoringAgent
- UnifiedMemoryReasoningAgentAlt
- AgentUtils
- ErrorBus
- ServiceRegistry
- MemoryClient
- SpeechToText
- IntentRecognizer
- InputProcessor
- RequestCoordinator
- GoalManager
- ResponseGenerator
- TranslationService
- StreamingTTS
- TaskRouter
- ChainOfThoughtAgent
- GOT_TOTAgent
- GoalOrchestratorAgent
- EnhancedModelRouter
- TinyLlamaService
- NLLBAdapter
- LocalFineTunerAgent
- SelfTrainingOrchestrator
- CognitiveModelAgent
- ConsolidatedTranslator
- VoiceProfiler
- UnifiedPlanningAgent
- MultiAgentSwarmManager
- TTSConnector
- StreamingTTSAgent
- AudioCapture
- LanguageAndTranslationCoordinator
- LearningAgent
- KnowledgeBaseAgent
- HealthCheck
- MetricsCollector
- AlertManager

