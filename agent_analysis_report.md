=== MAINPC AGENT ANALYSIS FROM startup_config.yaml ===

## MainPC Agent Groups and Counts:
- core_services: 6 agents
  └── ServiceRegistry: main_pc_code/agents/service_registry_agent.py
  └── SystemDigitalTwin: main_pc_code/agents/system_digital_twin.py
  └── RequestCoordinator: main_pc_code/agents/request_coordinator.py
  └── UnifiedSystemAgent: main_pc_code/agents/unified_system_agent.py
  └── ObservabilityHub: phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py
  └── ModelManagerSuite: main_pc_code/model_manager_suite.py
- memory_system: 3 agents
  └── MemoryClient: main_pc_code/agents/memory_client.py
  └── SessionMemoryAgent: main_pc_code/agents/session_memory_agent.py
  └── KnowledgeBase: main_pc_code/agents/knowledge_base.py
- utility_services: 8 agents
  └── CodeGenerator: main_pc_code/agents/code_generator_agent.py
  └── SelfTrainingOrchestrator: main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
  └── PredictiveHealthMonitor: main_pc_code/agents/predictive_health_monitor.py
  └── FixedStreamingTranslation: main_pc_code/agents/fixed_streaming_translation.py
  └── Executor: main_pc_code/agents/executor.py
  └── TinyLlamaServiceEnhanced: main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
  └── LocalFineTunerAgent: main_pc_code/FORMAINPC/LocalFineTunerAgent.py
  └── NLLBAdapter: main_pc_code/FORMAINPC/NLLBAdapter.py
- gpu_infrastructure: 1 agents
  └── VRAMOptimizerAgent: main_pc_code/agents/vram_optimizer_agent.py
- reasoning_services: 3 agents
  └── ChainOfThoughtAgent: main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
  └── GoTToTAgent: main_pc_code/FORMAINPC/GOT_TOTAgent.py
  └── CognitiveModelAgent: main_pc_code/FORMAINPC/CognitiveModelAgent.py
- vision_processing: 1 agents
  └── FaceRecognitionAgent: main_pc_code/agents/face_recognition_agent.py
- learning_knowledge: 5 agents
  └── LearningOrchestrationService: main_pc_code/agents/learning_orchestration_service.py
  └── LearningOpportunityDetector: main_pc_code/agents/learning_opportunity_detector.py
  └── LearningManager: main_pc_code/agents/learning_manager.py
  └── ActiveLearningMonitor: main_pc_code/agents/active_learning_monitor.py
  └── LearningAdjusterAgent: main_pc_code/FORMAINPC/LearningAdjusterAgent.py
- language_processing: 11 agents
  └── ModelOrchestrator: main_pc_code/agents/model_orchestrator.py
  └── GoalManager: main_pc_code/agents/goal_manager.py
  └── IntentionValidatorAgent: main_pc_code/agents/IntentionValidatorAgent.py
  └── NLUAgent: main_pc_code/agents/nlu_agent.py
  └── AdvancedCommandHandler: main_pc_code/agents/advanced_command_handler.py
  └── ChitchatAgent: main_pc_code/agents/chitchat_agent.py
  └── FeedbackHandler: main_pc_code/agents/feedback_handler.py
  └── Responder: main_pc_code/agents/responder.py
  └── TranslationService: main_pc_code/agents/translation_service.py
  └── DynamicIdentityAgent: main_pc_code/agents/DynamicIdentityAgent.py
  └── EmotionSynthesisAgent: main_pc_code/agents/emotion_synthesis_agent.py
- speech_services: 2 agents
  └── STTService: main_pc_code/services/stt_service.py
  └── TTSService: main_pc_code/services/tts_service.py
- audio_interface: 8 agents
  └── AudioCapture: main_pc_code/agents/streaming_audio_capture.py
  └── FusedAudioPreprocessor: main_pc_code/agents/fused_audio_preprocessor.py
  └── StreamingInterruptHandler: main_pc_code/agents/streaming_interrupt_handler.py
  └── StreamingSpeechRecognition: main_pc_code/agents/streaming_speech_recognition.py
  └── StreamingTTSAgent: main_pc_code/agents/streaming_tts_agent.py
  └── WakeWordDetector: main_pc_code/agents/wake_word_detector.py
  └── StreamingLanguageAnalyzer: main_pc_code/agents/streaming_language_analyzer.py
  └── ProactiveAgent: main_pc_code/agents/ProactiveAgent.py
- emotion_system: 6 agents
  └── EmotionEngine: main_pc_code/agents/emotion_engine.py
  └── MoodTrackerAgent: main_pc_code/agents/mood_tracker_agent.py
  └── HumanAwarenessAgent: main_pc_code/agents/human_awareness_agent.py
  └── ToneDetector: main_pc_code/agents/tone_detector.py
  └── VoiceProfilingAgent: main_pc_code/agents/voice_profiling_agent.py
  └── EmpathyAgent: main_pc_code/agents/EmpathyAgent.py

📊 **Total MainPC Agents: 54**

=== PC2 AGENT ANALYSIS FROM startup_config.yaml ===

## PC2 Services:
- Total PC2 Agents: 23
  └── MemoryOrchestratorService: pc2_code/agents/memory_orchestrator_service.py (port: 7140)
  └── TieredResponder: pc2_code/agents/tiered_responder.py (port: 7100)
  └── AsyncProcessor: pc2_code/agents/async_processor.py (port: 7101)
  └── CacheManager: pc2_code/agents/cache_manager.py (port: 7102)
  └── VisionProcessingAgent: pc2_code/agents/VisionProcessingAgent.py (port: 7150)
  └── DreamWorldAgent: pc2_code/agents/DreamWorldAgent.py (port: 7104)
  └── UnifiedMemoryReasoningAgent: pc2_code/agents/unified_memory_reasoning_agent.py (port: 7105)
  └── TutorAgent: pc2_code/agents/tutor_agent.py (port: 7108)
  └── TutoringAgent: pc2_code/agents/tutoring_agent.py (port: 7131)
  └── ContextManager: pc2_code/agents/context_manager.py (port: 7111)
  └── ExperienceTracker: pc2_code/agents/experience_tracker.py (port: 7112)
  └── ResourceManager: pc2_code/agents/resource_manager.py (port: 7113)
  └── TaskScheduler: pc2_code/agents/task_scheduler.py (port: 7115)
  └── AuthenticationAgent: pc2_code/agents/ForPC2/AuthenticationAgent.py (port: 7116)
  └── UnifiedUtilsAgent: pc2_code/agents/ForPC2/unified_utils_agent.py (port: 7118)
  └── ProactiveContextMonitor: pc2_code/agents/ForPC2/proactive_context_monitor.py (port: 7119)
  └── AgentTrustScorer: pc2_code/agents/AgentTrustScorer.py (port: 7122)
  └── FileSystemAssistantAgent: pc2_code/agents/filesystem_assistant_agent.py (port: 7123)
  └── RemoteConnectorAgent: pc2_code/agents/remote_connector_agent.py (port: 7124)
  └── UnifiedWebAgent: pc2_code/agents/unified_web_agent.py (port: 7126)
  └── DreamingModeAgent: pc2_code/agents/DreamingModeAgent.py (port: 7127)
  └── AdvancedRouter: pc2_code/agents/advanced_router.py (port: 7129)
  └── ObservabilityHub: phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py (port: 9000)

📊 **Total PC2 Agents: 23**
