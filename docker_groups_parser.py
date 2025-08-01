#!/usr/bin/env python3
"""
Docker Groups Parser - Extracts and validates docker_groups structure
Validates against the documented MainPC and PC2 docker group organization
"""
import yaml, pathlib, pprint, sys, itertools, json
from collections import defaultdict

files = [
    "main_pc_code/config/startup_config.yaml",
    "pc2_code/config/startup_config.yaml",
]

def load(p):
    with open(p) as f:
        return yaml.safe_load(f)

def extract_docker_groups():
    """Extract docker_groups from configuration files"""
    results = {}
    
    for f in files:
        cfg = load(f)
        docker_groups = {}
        
        if "docker_groups" in cfg:
            # Both files already have docker_groups defined
            docker_groups = cfg["docker_groups"]
        elif "agent_groups" in cfg:
            # Fallback: MainPC uses agent_groups, need to map to docker_groups
            docker_groups = map_agent_groups_to_docker(cfg["agent_groups"])
        elif "pc2_services" in cfg:
            # Fallback: PC2 uses flat list, need to map to docker_groups
            docker_groups = map_pc2_services_to_docker(cfg["pc2_services"])
        
        results[f] = docker_groups
    
    return results

def map_agent_groups_to_docker(agent_groups):
    """Map MainPC agent_groups to docker_groups structure"""
    docker_groups = {
        "infra_core": [],
        "coordination": [],
        "observability": [],
        "memory_stack": [],
        "vision_gpu": [],
        "speech_gpu": [],
        "learning_gpu": [],
        "reasoning_gpu": [],
        "language_stack": [],
        "utility_cpu": [],
        "emotion_system": []
    }
    
    # Map agent groups to docker groups based on documentation
    group_mapping = {
        "foundation_services": ["infra_core", "coordination"],
        "memory_system": ["memory_stack"],
        "utility_services": ["utility_cpu"],
        "reasoning_services": ["reasoning_gpu"],
        "vision_processing": ["vision_gpu"],
        "learning_knowledge": ["learning_gpu"],
        "language_processing": ["language_stack"],
        "speech_services": ["speech_gpu"],
        "audio_interface": ["speech_gpu"],
        "emotion_system": ["emotion_system"],
        "translation_services": ["utility_cpu"]
    }
    
    for agent_group, agents in agent_groups.items():
        if agent_group in group_mapping and agents is not None:
            docker_groups_to_add = group_mapping[agent_group]
            for docker_group in docker_groups_to_add:
                if isinstance(agents, dict):
                    for agent_name, agent_config in agents.items():
                        if isinstance(agent_config, dict) and "script_path" in agent_config:
                            docker_groups[docker_group].append({
                                "name": agent_name,
                                "script_path": agent_config["script_path"]
                            })
    
    return docker_groups

def map_pc2_services_to_docker(pc2_services):
    """Map PC2 services to docker_groups structure"""
    docker_groups = {
        "infra_core": [],
        "memory_stack": [],
        "async_pipeline": [],
        "tutoring_cpu": [],
        "vision_dream_gpu": [],
        "utility_suite": [],
        "web_interface": []
    }
    
    # Define which services go to which docker groups
    service_mapping = {
        "ObservabilityHub": "infra_core",
        "ResourceManager": "infra_core",
        "MemoryOrchestratorService": "memory_stack",
        "CacheManager": "memory_stack",
        "UnifiedMemoryReasoningAgent": "memory_stack",
        "ContextManager": "memory_stack",
        "ExperienceTracker": "memory_stack",
        "AsyncProcessor": "async_pipeline",
        "TaskScheduler": "async_pipeline",
        "AdvancedRouter": "async_pipeline",
        "TieredResponder": "async_pipeline",
        "TutorAgent": "tutoring_cpu",
        "TutoringAgent": "tutoring_cpu",
        "VisionProcessingAgent": "vision_dream_gpu",
        "DreamWorldAgent": "vision_dream_gpu",
        "DreamingModeAgent": "vision_dream_gpu",
        "UnifiedUtilsAgent": "utility_suite",
        "FileSystemAssistantAgent": "utility_suite",
        "RemoteConnectorAgent": "utility_suite",
        "AuthenticationAgent": "utility_suite",
        "AgentTrustScorer": "utility_suite",
        "ProactiveContextMonitor": "utility_suite",
        "UnifiedWebAgent": "web_interface"
    }
    
    for service in pc2_services:
        if isinstance(service, dict) and "name" in service and "script_path" in service:
            service_name = service["name"]
            if service_name in service_mapping:
                docker_group = service_mapping[service_name]
                docker_groups[docker_group].append({
                    "name": service_name,
                    "script_path": service["script_path"]
                })
    
    return docker_groups

def validate_against_documentation():
    """Validate extracted docker_groups against documented structure"""
    results = extract_docker_groups()
    
    # Expected structure from documentation
    expected_mainpc = {
        "infra_core": ["ServiceRegistry", "SystemDigitalTwin"],
        "coordination": ["RequestCoordinator", "ModelManagerSuite", "VRAMOptimizerAgent"],
        "observability": ["ObservabilityHub"],
        "memory_stack": ["MemoryClient", "SessionMemoryAgent", "KnowledgeBase"],
        "vision_gpu": ["FaceRecognitionAgent"],
        "speech_gpu": ["STTService", "TTSService", "AudioCapture", "FusedAudioPreprocessor", 
                      "StreamingSpeechRecognition", "StreamingTTSAgent", "WakeWordDetector",
                      "StreamingInterruptHandler", "StreamingLanguageAnalyzer"],
        "learning_gpu": ["SelfTrainingOrchestrator", "LocalFineTunerAgent", "LearningManager",
                        "LearningOrchestrationService", "LearningOpportunityDetector", 
                        "ActiveLearningMonitor", "LearningAdjusterAgent"],
        "reasoning_gpu": ["ChainOfThoughtAgent", "GoTToTAgent", "CognitiveModelAgent"],
        "language_stack": ["NLUAgent", "IntentionValidatorAgent", "AdvancedCommandHandler",
                          "ChitchatAgent", "FeedbackHandler", "Responder", "DynamicIdentityAgent",
                          "EmotionSynthesisAgent", "GoalManager", "ModelOrchestrator", "ProactiveAgent"],
        "utility_cpu": ["CodeGenerator", "Executor", "PredictiveHealthMonitor", "TranslationService",
                       "FixedStreamingTranslation", "NLLBAdapter"],
        "emotion_system": ["EmotionEngine", "MoodTrackerAgent", "HumanAwarenessAgent", "ToneDetector",
                          "VoiceProfilingAgent", "EmpathyAgent"]
    }
    
    expected_pc2 = {
        "infra_core": ["ObservabilityHub", "ResourceManager"],
        "memory_stack": ["MemoryOrchestratorService", "CacheManager", "UnifiedMemoryReasoningAgent",
                        "ContextManager", "ExperienceTracker"],
        "async_pipeline": ["AsyncProcessor", "TaskScheduler", "AdvancedRouter", "TieredResponder"],
        "tutoring_cpu": ["TutorAgent", "TutoringAgent"],
        "vision_dream_gpu": ["VisionProcessingAgent", "DreamWorldAgent", "DreamingModeAgent"],
        "utility_suite": ["UnifiedUtilsAgent", "FileSystemAssistantAgent", "RemoteConnectorAgent",
                         "AuthenticationAgent", "AgentTrustScorer", "ProactiveContextMonitor"],
        "web_interface": ["UnifiedWebAgent"]
    }
    
    validation_results = {}
    
    for config_file, docker_groups in results.items():
        if "main_pc_code" in config_file:
            expected = expected_mainpc
            system_name = "MainPC"
        else:
            expected = expected_pc2
            system_name = "PC2"
        
        validation_results[config_file] = {
            "system": system_name,
            "groups": {},
            "missing_agents": [],
            "unexpected_agents": [],
            "coverage_percentage": 0
        }
        
        total_expected = sum(len(agents) for agents in expected.values())
        total_found = 0
        
        for group_name, expected_agents in expected.items():
            # Handle both string lists and object lists
            docker_group = docker_groups.get(group_name, {})
            if isinstance(docker_group, dict) and "agents" in docker_group:
                found_agents = docker_group["agents"]
            elif isinstance(docker_group, list):
                found_agents = [agent["name"] if isinstance(agent, dict) else agent for agent in docker_group]
            else:
                found_agents = []
                
            validation_results[config_file]["groups"][group_name] = {
                "expected": expected_agents,
                "found": found_agents,
                "missing": [agent for agent in expected_agents if agent not in found_agents],
                "unexpected": [agent for agent in found_agents if agent not in expected_agents]
            }
            
            total_found += len(found_agents)
            validation_results[config_file]["missing_agents"].extend(
                [agent for agent in expected_agents if agent not in found_agents]
            )
            validation_results[config_file]["unexpected_agents"].extend(
                [agent for agent in found_agents if agent not in expected_agents]
            )
        
        validation_results[config_file]["coverage_percentage"] = (
            (total_found / total_expected * 100) if total_expected > 0 else 0
        )
    
    return results, validation_results

def main():
    docker_groups, validation = validate_against_documentation()
    
    print("=" * 80)
    print("DOCKER GROUPS VALIDATION REPORT")
    print("=" * 80)
    
    for config_file, validation_data in validation.items():
        print(f"\n📋 {validation_data['system']} System Validation:")
        print(f"   Coverage: {validation_data['coverage_percentage']:.1f}%")
        
        if validation_data['missing_agents']:
            print(f"   ❌ Missing Agents: {', '.join(validation_data['missing_agents'])}")
        
        if validation_data['unexpected_agents']:
            print(f"   ⚠️  Unexpected Agents: {', '.join(validation_data['unexpected_agents'])}")
        
        print(f"\n   📁 Docker Groups Breakdown:")
        for group_name, group_data in validation_data['groups'].items():
            if group_data['found']:
                print(f"      {group_name}: {len(group_data['found'])} agents")
                if group_data['missing']:
                    print(f"         Missing: {', '.join(group_data['missing'])}")
                if group_data['unexpected']:
                    print(f"         Unexpected: {', '.join(group_data['unexpected'])}")
    
    # Save detailed results
    with open('docker_groups_analysis.json', 'w') as f:
        json.dump({
            'docker_groups': docker_groups,
            'validation': validation
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: docker_groups_analysis.json")

if __name__ == "__main__":
    main() 