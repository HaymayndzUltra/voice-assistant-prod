#!/usr/bin/env python3
"""
Port Registry Module
Centralized port management for AI System agents with fallback support.
"""

import os
from typing import Dict, Optional


# Main PC Port Assignments (from startup_config.yaml analysis)
MAIN_PC_PORTS = {
    "ServiceRegistry": 7200,
    "SystemDigitalTwin": 7220,
    "RequestCoordinator": 26002,
    "ModelManagerSuite": 7211,
    "VRAMOptimizerAgent": 5572,
    "ObservabilityHub": 9000,
    "UnifiedSystemAgent": 7201,
    "MemoryClient": 5713,
    "SessionMemoryAgent": 5574,
    "KnowledgeBase": 5715,
    "CodeGenerator": 5650,
    "SelfTrainingOrchestrator": 5660,
    "PredictiveHealthMonitor": 5613,
    "Executor": 5606,
    "TinyLlamaServiceEnhanced": 5615,
    "LocalFineTunerAgent": 5662,
    "ChainOfThoughtAgent": 5612,
    "GotTotAgent": 5664,
    "CognitiveModelAgent": 5666,
    "FaceRecognitionAgent": 5668,
    "LearningOrchestrationService": 5670,
    "LearningOpportunityDetector": 5672,
    "LearningManager": 5674,
    "ActiveLearningMonitor": 5676,
    "LearningAdjusterAgent": 5678,
    "ModelOrchestrator": 5601,
    "GoalManager": 5602,
    "IntentionValidatorAgent": 5603,
    "NLUAgent": 5604,
    "AdvancedCommandHandler": 5605,
    "ChitchatAgent": 5607,
    "FeedbackHandler": 5608,
    "Responder": 5609,
    "DynamicIdentityAgent": 5610,
    "EmotionSynthesisAgent": 5611,
    "STTService": 8001,
    "TTSService": 8002,
    "StreamingAudioCapture": 5580,
    "FusedAudioPreprocessor": 5581,
    "StreamingInterruptHandler": 5582,
    "StreamingSpeechRecognition": 5583,
    "StreamingTTSAgent": 5584,
    "WakeWordDetector": 5585,
    "StreamingLanguageAnalyzer": 5586,
    "ProactiveAgent": 5587,
    "EmotionEngine": 5588,
    "MoodTrackerAgent": 5589,
    "HumanAwarenessAgent": 5590,
    "ToneDetector": 5591,
    "VoiceProfilingAgent": 5592,
    "EmpathyAgent": 5593,
    "TranslationService": 5594,
    "FixedStreamingTranslation": 5595,
    "NLLBAdapter": 5596,
}

# PC2 Port Assignments (from PC2 startup_config.yaml analysis)
PC2_PORTS = {
    "MemoryOrchestratorService": 5596,
    "TieredResponder": 5597,
    "AsyncProcessor": 5598,
    "CacheManager": 5599,
    "VisionProcessingAgent": 5600,
    "DreamWorldAgent": 5601,
    "UnifiedMemoryReasoningAgent": 5602,
    "TutorAgent": 5603,
    "TutoringAgent": 5604,
    "ContextManager": 5605,
    "ExperienceTracker": 5606,
    "ResourceManager": 5607,
    "TaskScheduler": 5608,
    "AuthenticationAgent": 5609,
    "UnifiedUtilsAgent": 5610,
    "ProactiveContextMonitor": 5611,
    "AgentTrustScorer": 5612,
    "FilesystemAssistantAgent": 5613,
    "RemoteConnectorAgent": 5614,
    "UnifiedWebAgent": 5615,
    "DreamingModeAgent": 5616,
    "AdvancedRouter": 5617,
}

# Health check ports (typically main port + 1000)
def get_health_port(main_port: int) -> int:
    """Get health check port for a given main port."""
    return main_port + 1000


def get_port(agent_name: str, system_type: str = "main_pc") -> int:
    """
    Get port number for an agent with environment variable fallback.
    
    Args:
        agent_name: Name of the agent (e.g., "ServiceRegistry")
        system_type: System type ("main_pc" or "pc2")
    
    Returns:
        Port number for the agent
        
    Raises:
        ValueError: If agent is not found and no fallback available
    """
    # Choose the appropriate port registry
    if system_type.lower() == "pc2":
        port_registry = PC2_PORTS
        env_prefix = "PC2_"
    else:
        port_registry = MAIN_PC_PORTS
        env_prefix = ""
    
    # Try to get from registry first
    if agent_name in port_registry:
        return port_registry[agent_name]
    
    # Fallback to environment variable
    env_var = f"{env_prefix}{agent_name.upper()}_PORT"
    env_port = os.getenv(env_var)
    
    if env_port:
        try:
            port = int(env_port)
            if 1024 <= port <= 65535:
                return port
            else:
                raise ValueError(f"Port {port} outside valid range (1024-65535)")
        except ValueError as e:
            raise ValueError(f"Invalid port in {env_var}: {env_port}") from e
    
    # No port found
    raise ValueError(f"No port configured for agent '{agent_name}' on {system_type}")


def get_agent_ports(agent_name: str, system_type: str = "main_pc") -> Dict[str, int]:
    """
    Get both main and health check ports for an agent.
    
    Returns:
        Dictionary with 'main' and 'health' port numbers
    """
    main_port = get_port(agent_name, system_type)
    health_port = get_health_port(main_port)
    
    return {
        "main": main_port,
        "health": health_port
    }


def list_available_agents(system_type: str = "main_pc") -> list:
    """List all available agent names for a system type."""
    if system_type.lower() == "pc2":
        return list(PC2_PORTS.keys())
    else:
        return list(MAIN_PC_PORTS.keys())


# Compatibility functions for existing code patterns
def get_service_port(service_name: str) -> int:
    """Legacy compatibility function."""
    return get_port(service_name, "main_pc")


if __name__ == "__main__":
    # Test the port registry
    print("Port Registry Test:")
    print(f"ServiceRegistry: {get_port('ServiceRegistry')}")
    print(f"ServiceRegistry Health: {get_health_port(get_port('ServiceRegistry'))}")
    print(f"Total Main PC agents: {len(MAIN_PC_PORTS)}")
    print(f"Total PC2 agents: {len(PC2_PORTS)}")
