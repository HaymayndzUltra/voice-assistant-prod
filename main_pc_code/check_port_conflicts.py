#!/usr/bin/env python3


# Define the target agent batches
TARGET_AGENT_BATCHES = [
    # Batch 1: Core services with no dependencies
    [
        {"name": "ChainOfThoughtAgent", "script": "FORMAINPC/ChainOfThoughtAgent.py", "port": 5612},
        {"name": "GOT_TOTAgent", "script": "FORMAINPC/GOT_TOTAgent.py", "port": 5646},
        {"name": "ModelManagerAgent", "script": "agents/model_manager_agent.py", "port": 5570},
        {"name": "CoordinatorAgent", "script": "agents/coordinator_agent.py", "port": 26002},
        {"name": "EnhancedModelRouter", "script": "FORMAINPC/EnhancedModelRouter.py", "port": 5598},
        {"name": "TinyLlamaService", "script": "FORMAINPC/TinyLlamaServiceEnhanced.py", "port": 5615},
        {"name": "NLLBAdapter", "script": "FORMAINPC/NLLBAdapter.py", "port": 5581},
        {"name": "LearningAdjusterAgent", "script": "FORMAINPC/LearningAdjusterAgent.py", "port": 5643},
        {"name": "LocalFineTunerAgent", "script": "FORMAINPC/LocalFineTunerAgent.py", "port": 5645},
        {"name": "SelfTrainingOrchestrator", "script": "FORMAINPC/SelfTrainingOrchestrator.py", "port": 5644},
        {"name": "CognitiveModelAgent", "script": "FORMAINPC/CognitiveModelAgent.py", "port": 5641},
        {"name": "ConsolidatedTranslator", "script": "FORMAINPC/consolidated_translator.py", "port": 5563},
        {"name": "EmotionEngine", "script": "agents/emotion_engine.py", "port": 5590},
        {"name": "MemoryOrchestrator", "script": "src/memory/memory_orchestrator.py", "port": 5576},
        {"name": "MemoryClient", "script": "src/memory/memory_client.py", "port": 5577},
        {"name": "TTSCache", "script": "agents/tts_cache.py", "port": 5628},
        {"name": "Executor", "script": "agents/executor.py", "port": 5606},
        {"name": "AudioCapture", "script": "agents/streaming_audio_capture.py", "port": 6575},
        {"name": "VisionCaptureAgent", "script": "src/vision/vision_capture_agent.py", "port": 5592},
        {"name": "PredictiveHealthMonitor", "script": "agents/predictive_health_monitor.py", "port": 5613}
    ],
    # Batch 2: Services dependent on Batch 1
    [
        {"name": "TaskRouter", "script": "src/core/task_router.py", "port": 8571},
        {"name": "GoalOrchestratorAgent", "script": "agents/GoalOrchestratorAgent.py", "port": 7001},
        {"name": "IntentionValidatorAgent", "script": "agents/IntentionValidatorAgent.py", "port": 5701},
        {"name": "DynamicIdentityAgent", "script": "agents/DynamicIdentityAgent.py", "port": 5802},
        {"name": "EmpathyAgent", "script": "agents/EmpathyAgent.py", "port": 5703},
        {"name": "ProactiveAgent", "script": "agents/ProactiveAgent.py", "port": 5624},
        {"name": "PredictiveLoader", "script": "agents/predictive_loader.py", "port": 5617},
        {"name": "MoodTrackerAgent", "script": "agents/mood_tracker_agent.py", "port": 5704},
        {"name": "HumanAwarenessAgent", "script": "agents/human_awareness_agent.py", "port": 5705},
        {"name": "EmotionSynthesisAgent", "script": "agents/emotion_synthesis_agent.py", "port": 5706},
        {"name": "ToneDetector", "script": "agents/tone_detector.py", "port": 5625},
        {"name": "VoiceProfiler", "script": "agents/voice_profiling_agent.py", "port": 5708},
        {"name": "SessionMemoryAgent", "script": "agents/session_memory_agent.py", "port": 5572},
        {"name": "UnifiedMemoryReasoningAgent", "script": "agents/_referencefolderpc2/UnifiedMemoryReasoningAgent.py", "port": 5596},
        {"name": "CodeGenerator", "script": "agents/code_generator_agent.py", "port": 5604},
        {"name": "TTSConnector", "script": "agents/tts_connector.py", "port": 5582},
        {"name": "StreamingTTSAgent", "script": "agents/streaming_tts_agent.py", "port": 5562},
        {"name": "FusedAudioPreprocessor", "script": "src/audio/fused_audio_preprocessor.py", "port": 6578},
        {"name": "LanguageAndTranslationCoordinator", "script": "agents/language_and_translation_coordinator.py", "port": 6581},
        {"name": "FaceRecognitionAgent", "script": "agents/face_recognition_agent.py", "port": 5610},
        {"name": "StreamingSpeechRecognition", "script": "agents/streaming_speech_recognition.py", "port": 6580}
    ],
    # Batch 3: Services dependent on Batch 2
    [
        {"name": "MemoryClient", "script": "agents/memory_client.py", "port": 5713},
        {"name": "EpisodicMemoryAgent", "script": "agents/_referencefolderpc2/EpisodicMemoryAgent.py", "port": 5597},
        {"name": "WakeWordDetector", "script": "agents/wake_word_detector.py", "port": 6577},
        {"name": "NLUAgent", "script": "agents/nlu_agent.py", "port": 5709}
    ],
    # Batch 4: Services dependent on Batch 3
    [
        {"name": "LearningManager", "script": "agents/learning_manager.py", "port": 5579},
        {"name": "KnowledgeBase", "script": "agents/knowledge_base.py", "port": 5578},
        {"name": "AdvancedCommandHandler", "script": "agents/advanced_command_handler.py", "port": 5710},
        {"name": "ChitchatAgent", "script": "agents/chitchat_agent.py", "port": 5711},
        {"name": "FeedbackHandler", "script": "agents/feedback_handler.py", "port": 5636},
        {"name": "Responder", "script": "agents/responder.py", "port": 5637}
    ],
    # Batch 5: Services dependent on Batch 4
    [
        {"name": "MetaCognitionAgent", "script": "agents/MetaCognitionAgent.py", "port": 5630},
        {"name": "ActiveLearningMonitor", "script": "agents/active_learning_monitor.py", "port": 5638},
        {"name": "UnifiedPlanningAgent", "script": "agents/unified_planning_agent.py", "port": 5634}
    ],
    # Batch 6: Services dependent on Batch 5
    [
        {"name": "MultiAgentSwarmManager", "script": "agents/MultiAgentSwarmManager.py", "port": 5639},
        {"name": "UnifiedSystemAgent", "script": "agents/unified_system_agent.py", "port": 5640}
    ]
]

# Check for port conflicts
port_to_agent = {}
conflicts = []

for batch_idx, batch in enumerate(TARGET_AGENT_BATCHES):
    for agent in batch:
        port = agent["port"]
        name = agent["name"]
        
        if port in port_to_agent:
            conflicts.append({
                "port": port,
                "agents": [port_to_agent[port], name]
            })
        else:
            port_to_agent[port] = name

# Print results
if conflicts:
    print("Port conflicts found:")
    for conflict in conflicts:
        print(f"Port {conflict['port']} is used by agents: {conflict['agents']}")
else:
    print("No internal port conflicts found in TARGET_AGENT_BATCHES.") 