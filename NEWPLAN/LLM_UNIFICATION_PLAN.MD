# LLM Unification Plan Report

## Active Agent Inventory

### MainPC Agents
| Agent Name | Script Path |
| --- | --- |
| SystemDigitalTwin | main_pc_code/agents/system_digital_twin.py |
| RequestCoordinator | main_pc_code/agents/request_coordinator.py |
| UnifiedSystemAgent | main_pc_code/agents/unified_system_agent.py |
| MemoryClient | main_pc_code/agents/memory_client.py |
| SessionMemoryAgent | main_pc_code/agents/session_memory_agent.py |
| KnowledgeBase | main_pc_code/agents/knowledge_base.py |
| CodeGenerator | main_pc_code/agents/code_generator.py |
| SelfTrainingOrchestrator | main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py |
| GGUFModelManager | main_pc_code/agents/gguf_model_manager.py |
| ModelManagerAgent | main_pc_code/agents/model_manager_agent.py |
| VRAMOptimizerAgent | main_pc_code/agents/vram_optimizer_agent.py |
| PredictiveLoader | main_pc_code/agents/predictive_loader.py |
| FaceRecognitionAgent | main_pc_code/agents/face_recognition_agent.py |
| ModelEvaluationFramework | main_pc_code/agents/model_evaluation_framework.py |
| LearningOrchestrationService | main_pc_code/agents/learning_orchestration_service.py |
| LearningOpportunityDetector | main_pc_code/agents/learning_opportunity_detector.py |
| LearningManager | main_pc_code/agents/learning_manager.py |
| ActiveLearningMonitor | main_pc_code/agents/active_learning_monitor.py |
| LearningAdjusterAgent | main_pc_code/FORMAINPC/LearningAdjusterAgent.py |
| ModelOrchestrator | main_pc_code/agents/model_orchestrator.py |
| GoalManager | main_pc_code/agents/goal_manager.py |
| IntentionValidatorAgent | main_pc_code/agents/IntentionValidatorAgent.py |
| NLUAgent | main_pc_code/agents/nlu_agent.py |
| AdvancedCommandHandler | main_pc_code/agents/advanced_command_handler.py |
| ChitchatAgent | main_pc_code/agents/chitchat_agent.py |
| FeedbackHandler | main_pc_code/agents/feedback_handler.py |
| Responder | main_pc_code/agents/responder.py |
| TranslationService | main_pc_code/agents/translation_service.py |
| DynamicIdentityAgent | main_pc_code/agents/DynamicIdentityAgent.py |
| AudioCapture | main_pc_code/agents/streaming_audio_capture.py |
| FusedAudioPreprocessor | main_pc_code/agents/fused_audio_preprocessor.py |
| StreamingInterruptHandler | main_pc_code/agents/streaming_interrupt_handler.py |
| StreamingSpeechRecognition | main_pc_code/agents/streaming_speech_recognition.py |
| StreamingTTSAgent | main_pc_code/agents/streaming_tts_agent.py |
| WakeWordDetector | main_pc_code/agents/wake_word_detector.py |
| StreamingLanguageAnalyzer | main_pc_code/agents/streaming_language_analyzer.py |
| ProactiveAgent | main_pc_code/agents/ProactiveAgent.py |
| EmotionEngine | main_pc_code/agents/emotion_engine.py |
| MoodTrackerAgent | main_pc_code/agents/mood_tracker_agent.py |
| HumanAwarenessAgent | main_pc_code/agents/human_awareness_agent.py |
| ToneDetector | main_pc_code/agents/tone_detector.py |
| VoiceProfilingAgent | main_pc_code/agents/voice_profiling_agent.py |
| EmpathyAgent | main_pc_code/agents/EmpathyAgent.py |
| EmotionSynthesisAgent | main_pc_code/agents/emotion_synthesis_agent.py |
| PredictiveHealthMonitor | main_pc_code/agents/predictive_health_monitor.py |
| FixedStreamingTranslation | main_pc_code/agents/fixed_streaming_translation.py |
| Executor | main_pc_code/agents/executor.py |
| TinyLlamaServiceEnhanced | main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py |
| LocalFineTunerAgent | main_pc_code/FORMAINPC/LocalFineTunerAgent.py |
| NLLBAdapter | main_pc_code/FORMAINPC/NLLBAdapter.py |
| ChainOfThoughtAgent | main_pc_code/FORMAINPC/ChainOfThoughtAgent.py |
| GoTToTAgent | main_pc_code/FORMAINPC/GOT_TOTAgent.py |
| CognitiveModelAgent | main_pc_code/FORMAINPC/CognitiveModelAgent.py |

### PC2 Agents
| Agent Name | Script Path |
| --- | --- |
| TieredResponder | pc2_code/agents/tiered_responder.py |
| AsyncProcessor | pc2_code/agents/async_processor.py |
| CacheManager | pc2_code/agents/cache_manager.py |
| PerformanceMonitor | pc2_code/agents/performance_monitor.py |
| VisionProcessingAgent | pc2_code/agents/VisionProcessingAgent.py |
| DreamWorldAgent | pc2_code/agents/DreamWorldAgent.py |
| UnifiedMemoryReasoningAgent | pc2_code/agents/UnifiedMemoryReasoningAgent.py |
| TutorAgent | pc2_code/agents/tutor_agent.py |
| TutoringServiceAgent | pc2_code/agents/tutoring_service_agent.py |
| ContextManager | pc2_code/agents/context_manager.py |
| ExperienceTracker | pc2_code/agents/experience_tracker.py |
| ResourceManager | pc2_code/agents/resource_manager.py |
| HealthMonitor | pc2_code/agents/health_monitor.py |
| TaskScheduler | pc2_code/agents/task_scheduler.py |
| AuthenticationAgent | pc2_code/agents/ForPC2/AuthenticationAgent.py |
| SystemHealthManager | pc2_code/agents/ForPC2/system_health_manager.py |
| UnifiedUtilsAgent | pc2_code/agents/ForPC2/unified_utils_agent.py |
| ProactiveContextMonitor | pc2_code/agents/ForPC2/proactive_context_monitor.py |
| AgentTrustScorer | pc2_code/agents/AgentTrustScorer.py |
| FileSystemAssistantAgent | pc2_code/agents/filesystem_assistant_agent.py |
| RemoteConnectorAgent | pc2_code/agents/remote_connector_agent.py |
| UnifiedWebAgent | pc2_code/agents/unified_web_agent.py |
| DreamingModeAgent | pc2_code/agents/DreamingModeAgent.py |
| PerformanceLoggerAgent | pc2_code/agents/PerformanceLoggerAgent.py |
| AdvancedRouter | pc2_code/agents/advanced_router.py |
| TutoringAgent | pc2_code/agents/tutoring_agent.py |
| MemoryOrchestratorService | pc2_code/agents/memory_orchestrator_service.py |

## Independent Model Loaders Audit

Based on the code analysis, these agents are loading models independently:

1. **StreamingTTSAgent** (main_pc_code/agents/streaming_tts_agent.py:346-356): 
   ```python
   self.tts_engines["xtts"] = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
   ```
   This agent loads XTTS v2 models directly in its initialization process.

2. **StreamingSpeechRecognition** (main_pc_code/agents/streaming_speech_recognition.py:396-422):
   While this agent doesn't directly load models, it requests models from ModelManagerAgent but handles its own model management logic.

3. **ChainOfThoughtAgent** (main_pc_code/FORMAINPC/ChainOfThoughtAgent.py:117-171):
   This agent doesn't directly load models but sends requests to RemoteConnectorAgent for model inference.

## ModelManagerAgent Current API

The ModelManagerAgent provides the following API actions:

| Command | Description |
| --- | --- |
| HEALTH_CHECK | Performs a health check on the agent |
| LOAD_MODEL | Loads a specific model with optional parameters (model_name, device, quantization_level) |
| UNLOAD_MODEL | Unloads a specific model |
| GET_LOADED_MODELS_STATUS | Returns information about all loaded models |
| SELECT_MODEL | Selects an appropriate model based on task_type and context_size |
| PROCESS | Processes various request types (load_model, unload_model, get_model_status, get_all_models, get_memory_status, health_check) |
| VERIFY_SERVICES | Verifies PC2 services |

Additionally, the agent supports these request types via the PROCESS command:
- load_model: Loads a specific model
- unload_model: Unloads a specific model
- get_model_status: Gets status of a specific model
- get_all_models: Gets status of all models
- get_memory_status: Gets memory status
- health_check: Performs a health check
- get_model_status: Gets status of a specific model

## Proposed Migration Checklist

| Agent Name | File Path | Current Model Loading Code Snippet |
| :--- | :--- | :--- |
| StreamingTTSAgent | main_pc_code/agents/streaming_tts_agent.py:346-356 | `self.tts_engines["xtts"] = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)` |
| StreamingSpeechRecognition | main_pc_code/agents/streaming_speech_recognition.py:396-422 | Uses custom model loading request logic with ModelManagerAgent |
| ChainOfThoughtAgent | main_pc_code/FORMAINPC/ChainOfThoughtAgent.py:117-171 | Uses RemoteConnectorAgent for inference but has custom model selection logic |

## Next Steps for LLM Unification

1. **Extend ModelManagerAgent API**:
   - Add support for TTS models (XTTS v2)
   - Standardize the inference request format across all model types
   - Implement a unified model registry for all model types

2. **Refactor StreamingTTSAgent**:
   - Remove direct model loading code
   - Use ModelManagerAgent for all TTS model management
   - Implement fallback mechanisms through ModelManagerAgent

3. **Standardize ChainOfThoughtAgent**:
   - Route all inference requests through ModelManagerAgent instead of RemoteConnectorAgent
   - Adopt standardized request/response format

4. **Enhance StreamingSpeechRecognition**:
   - Fully integrate with ModelManagerAgent's standard API
   - Remove custom model loading request logic

5. **Documentation and Testing**:
   - Document the unified API for all agent developers
   - Create integration tests for the unified model management system
   - Verify performance and latency are maintained or improved

This unification will centralize all model management, reduce VRAM usage through better sharing, and provide a consistent interface for all agents requiring LLM capabilities.