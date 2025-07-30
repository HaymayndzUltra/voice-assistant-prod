from pathlib import Path

# ===================================================================
#         DATA STRUCTURES FOR ALL AGENTS AND GROUPS
# ===================================================================

main_pc_groups = {
    "core_services": [
        "SystemDigitalTwin", "RequestCoordinator", "UnifiedSystemAgent"
    ],
    "memory_system": [
        "MemoryClient", "SessionMemoryAgent", "KnowledgeBase"
    ],
    "utility_services": [
        "CodeGenerator", "SelfTrainingOrchestrator"
    ],
    "ai_models_gpu_services": [
        "GGUFModelManager", "ModelManagerAgent", "VRAMOptimizerAgent", "PredictiveLoader"
    ],
    "vision_system": [
        "FaceRecognitionAgent"
    ],
    "learning_knowledge": [
        "ModelEvaluationFramework", "LearningOrchestrationService", "LearningOpportunityDetector",
        "LearningManager", "ActiveLearningMonitor", "LearningAdjusterAgent"
    ],
    "language_processing": [
        "ModelOrchestrator", "GoalManager", "IntentionValidatorAgent", "NLUAgent",
        "AdvancedCommandHandler", "ChitchatAgent", "FeedbackHandler", "Responder",
        "TranslationService", "DynamicIdentityAgent"
    ],
    "audio_processing": [
        "AudioCapture", "FusedAudioPreprocessor", "StreamingInterruptHandler",
        "StreamingSpeechRecognition", "StreamingTTSAgent", "WakeWordDetector",
        "StreamingLanguageAnalyzer", "ProactiveAgent"
    ],
    "emotion_system": [
        "EmotionEngine", "MoodTrackerAgent", "HumanAwarenessAgent", "ToneDetector",
        "VoiceProfilingAgent", "EmpathyAgent", "EmotionSynthesisAgent"
    ],
    "utilities_support": [
        "PredictiveHealthMonitor", "FixedStreamingTranslation", "Executor",
        "TinyLlamaServiceEnhanced", "LocalFineTunerAgent", "NLLBAdapter"
    ],
    "reasoning_services": [
        "ChainOfThoughtAgent", "GoTToTAgent", "CognitiveModelAgent"
    ]
}

# Re-structured PC2 agents into logical groups for documentation
pc2_groups = {
    "Integration_Layer": [
        "TieredResponder", "AsyncProcessor", "CacheManager", "PerformanceMonitor", "VisionProcessingAgent"
    ],
    "PC2_Core_Agents": [
        "DreamWorldAgent", "UnifiedMemoryReasoningAgent", "TutorAgent", "TutoringServiceAgent",
        "ContextManager", "ExperienceTracker", "ResourceManager", "HealthMonitor", "TaskScheduler"
    ],
    "ForPC2_Services": [
        "AuthenticationAgent", "SystemHealthManager", "UnifiedUtilsAgent", "ProactiveContextMonitor"
    ],
    "Additional_Core_Agents": [
        "AgentTrustScorer", "FileSystemAssistantAgent", "RemoteConnectorAgent", "UnifiedWebAgent",
        "DreamingModeAgent", "PerformanceLoggerAgent", "AdvancedRouter"
    ],
    "Additional_Agents": [
        "TutoringAgent"
    ],
    "Central_Services": [
        "MemoryOrchestratorService"
    ]
}

def create_template(agent_name):
    """Creates the blank markdown template for a single agent."""
    return f"""### 🧠 AGENT PROFILE: {agent_name}
- **Main Class:** 
- **Host Machine:** 
- **Role:** 
- **🎯 Responsibilities:** 
- **🔗 Interactions:** 
- **🧬 Technical Deep Dive:** 
- **⚠️ Panganib:** 
- **📡 Communication Details:** 
  - **🔌 Health Port:** 
  - **🛰️ Port:** 

---
"""

def generate_docs():
    """Generates the entire documentation folder and file structure."""
    base_dir = Path("SYSTEM_DOCUMENTATION")
    all_systems = {"MAIN_PC": main_pc_groups, "PC2": pc2_groups}

    print("Generating documentation structure...")

    for system_name, groups in all_systems.items():
        system_dir = base_dir / system_name
        system_dir.mkdir(parents=True, exist_ok=True)
        
        # Using enumerate to get a numbered prefix for files
        for i, (group_name, agents) in enumerate(groups.items(), 1):
            # Create a clean filename
            file_name = f"{i:02d}_{group_name}.md"
            file_path = system_dir / file_name

            with file_path.open("w", encoding="utf-8") as f:
                # Write the group title
                title = group_name.replace('_', ' ').title()
                f.write(f"# Group: {title}\n\n")
                f.write("Ito ang mga agents na kabilang sa grupong ito:\n\n---\n\n")
                
                # Write the template for each agent in the group
                for agent_name in agents:
                    f.write(create_template(agent_name))
            
            print(f"  - Created: {file_path}")

    print("\nDocumentation structure generated successfully in the 'SYSTEM_DOCUMENTATION' folder!")

if __name__ == "__main__":
    generate_docs()
