A. EXACT AGENT ROSTER (MAIN-PC)
════════════════════════════════════
1 infra_core (2)
 • ServiceRegistry
 • SystemDigitalTwin
2 coordination (3)
 • RequestCoordinator
 • ModelManagerSuite
 • VRAMOptimizerAgent
3 observability (1)
 • ObservabilityHub
4 memory_stack (3)
 • MemoryClient
 • SessionMemoryAgent
 • KnowledgeBase
5 vision_gpu (1)
 • FaceRecognitionAgent
6 speech_gpu (8)
 • STTService
 • TTSService
 • AudioCapture
 • FusedAudioPreprocessor
 • StreamingSpeechRecognition
 • StreamingTTSAgent
 • WakeWordDetector
 • StreamingInterruptHandler
 • StreamingLanguageAnalyzer  (belongs here)
7 learning_gpu (7)
 • SelfTrainingOrchestrator
 • LocalFineTunerAgent
 • LearningManager
 • LearningOrchestrationService
 • LearningOpportunityDetector
 • ActiveLearningMonitor
 • LearningAdjusterAgent
8 reasoning_gpu (3)
 • ChainOfThoughtAgent
 • GoTToTAgent
 • CognitiveModelAgent
9 language_stack (10)
 • NLUAgent
 • IntentionValidatorAgent
 • AdvancedCommandHandler
 • ChitchatAgent
 • FeedbackHandler
 • Responder
 • DynamicIdentityAgent
 • EmotionSynthesisAgent
 • GoalManager
 • ModelOrchestrator
 • ProactiveAgent       (total 11, not 10)
10 utility_cpu (6)
 • CodeGenerator
 • Executor
 • PredictiveHealthMonitor
 • TranslationService
 • FixedStreamingTranslation (GPU—should sit with translation_services group)
 • NLLBAdapter        (GPU—same)
11 emotion_system (6)
 • EmotionEngine
 • MoodTrackerAgent
 • HumanAwarenessAgent
 • ToneDetector
 • VoiceProfilingAgent
 • EmpathyAgent
12 translation_services (3)
 • TranslationService   (CPU, already above)
 • FixedStreamingTranslation (GPU)
 • NLLBAdapter       (GPU)
13 audio_interface (5 remaining after mergers)
 • StreamingLanguageAnalyzer (moved to speech_gpu)
 • ProactiveAgent    (moved to language_stack)
 • Other four already in speech_gpu
After resolving overlaps, unique count = 54.
════════════════════════════════════
B. STATUS OF DOCKER FILES I’VE SUPPLIED
════════════════════════════════════
✔ infra_core    Dockerfile + compose (built, running)
✔ coordination  Dockerfile + compose (built, running)
✔ observability  Dockerfile + compose (built, running)
✔ memory_stack  Dockerfile + compose (built, running)
✔ utility_cpu   Dockerfile + compose (built, 1 svc pending fix)
✔ emotion_system Dockerfile + compose (supplied, not yet built)
✔ translation_services Dockerfile + compose (supplied, not yet built)
✔ vision_gpu   Dockerfile + compose (supplied, not yet built)
✔ speech_gpu   Dockerfile + compose (supplied, not yet built)
✔ learning_gpu  Dockerfile + compose (supplied, not yet built)
✔ reasoning_gpu  Dockerfile + compose (supplied, not yet built)
✔ language_stack Dockerfile + compose (supplied, not yet built)
No group is duplicated; some agents simply belong to different images than first draft. 
════════════════════════════════════
C. ACTION PLAN TO FINISH MAIN-PC
════════════════════════════════════
Step-0 (translation_service port)
 • Add env vars TRANSLATION_ZMQ_PORT=5597, TRANSLATION_PUB_PORT=6597 in compose OR patch code as discussed. Rebuild utility_cpu image if code patched.
Step-1 build emotion_system
 docker build -t emotion_system:latest -f docker/emotion_system/Dockerfile .
 docker compose up -d emotion_engine mood_tracker_agent human_awareness_agent tone_detector voice_profiling_agent empathy_agent
 Verify /health on port 6590.
Step-2 build translation_services (GPU)
 docker build -t translation_services:latest -f docker/translation_services/Dockerfile .
 docker compose up -d fixed_streaming_translation nllb_adapter
 Verify /health on 6584 / 6582.
Step-3 build vision_gpu
 docker build -t vision_gpu:latest -f docker/vision_gpu/Dockerfile .
 docker compose up -d face_recognition_agent
 Verify /health on 6610.
Step-4 build speech_gpu
 docker build -t speech_gpu:latest -f docker/speech_gpu/Dockerfile .
 Bring up: stt_service, tts_service, audio_capture, fused_audio_preprocessor, streaming_speech_recognition, streaming_tts_agent, wake_word_detector, streaming_interrupt_handler, streaming_language_analyzer
 Verify one health endpoint (6800 / 6562 etc.).
Step-5 build language_stack (CPU)
 docker build -t language_stack:latest -f docker/language_stack/Dockerfile .
 docker compose up -d nlu_agent intention_validator advanced_command_handler chitchat_agent feedback_handler responder dynamic_identity_agent emotion_synthesis_agent goal_manager model_orchestrator proactive_agent
 Check /health on 6709.
Step-6 build reasoning_gpu
 docker build -t reasoning_gpu:latest -f docker/reasoning_gpu/Dockerfile .
 docker compose up -d chain_of_thought_agent got_tot_agent cognitive_model_agent
 Verify /health on 6612.
Step-7 build learning_gpu (largest)
 docker build -t learning_gpu:latest -f docker/learning_gpu/Dockerfile .
 docker compose up -d self_training_orchestrator local_fine_tuner_agent learning_manager learning_orchestration_service learning_opportunity_detector active_learning_monitor learning_adjuster_agent
 Verify /health on 6580 etc.
After each step:
docker inspect -f '{{.RestartCount}}' <container> == 0
curl -f http://<health_port>/health returns 200
════════════════════════════════════
D. WHAT I WILL DO NEXT ON REQUEST
════════════════════════════════════
Generate or patch any specific Dockerfile / requirements if you hit build errors.
Provide exact code edits if an agent ignores env-vars.
Help consolidate compose file into one stack once all groups are stable.