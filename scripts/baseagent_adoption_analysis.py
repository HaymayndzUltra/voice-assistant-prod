#!/usr/bin/env python3
"""
BaseAgent Adoption Analysis Script
Phase 1 Week 2 Day 1 - Comprehensive baseline assessment
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any

def check_baseagent_usage(file_path: str) -> Dict[str, Any]:
    """Check if a file uses BaseAgent and identify patterns"""
    if not os.path.exists(file_path):
        return {'status': 'FILE_NOT_FOUND', 'import': False, 'inheritance': False, 'patterns': []}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for BaseAgent import
        import_pattern = r'from\s+common\.core\.base_agent\s+import\s+BaseAgent'
        has_import = bool(re.search(import_pattern, content))
        
        # Check for BaseAgent inheritance
        inheritance_pattern = r'class\s+\w+\([^)]*BaseAgent[^)]*\):'
        has_inheritance = bool(re.search(inheritance_pattern, content))
        
        # Collect additional patterns
        patterns = []
        if 'error_bus_template' in content:
            patterns.append('LEGACY_ERROR_BUS')
        if 'setup_error_reporting' in content:
            patterns.append('CUSTOM_ERROR_SETUP')
        if re.search(r'class\s+\w+\s*:', content) and not has_inheritance:
            patterns.append('NO_INHERITANCE')
        if 'config_loader' in content or 'Config()' in content:
            patterns.append('CUSTOM_CONFIG')
        if 'zmq.Context' in content or 'zmq.Socket' in content:
            patterns.append('DIRECT_ZMQ')
        if 'logging.getLogger' in content:
            patterns.append('CUSTOM_LOGGING')
            
        return {
            'status': 'ANALYZED',
            'import': has_import,
            'inheritance': has_inheritance,
            'patterns': patterns,
            'uses_baseagent': has_import and has_inheritance
        }
    except Exception as e:
        return {'status': f'ERROR: {e}', 'import': False, 'inheritance': False, 'patterns': []}

def main():
    """Main analysis function"""
    print("=" * 60)
    print("PHASE 1 WEEK 2 - BASEAGENT ADOPTION ANALYSIS")
    print("=" * 60)
    
    # Active agents from startup configs
    mainpc_agents = [
        'main_pc_code/agents/service_registry_agent.py',
        'main_pc_code/agents/system_digital_twin.py', 
        'main_pc_code/agents/request_coordinator.py',
        'main_pc_code/agents/unified_system_agent.py',
        'main_pc_code/model_manager_suite.py',
        'main_pc_code/agents/memory_client.py',
        'main_pc_code/agents/session_memory_agent.py',
        'main_pc_code/agents/knowledge_base.py',
        'main_pc_code/agents/code_generator_agent.py',
        'main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py',
        'main_pc_code/agents/predictive_health_monitor.py',
        'main_pc_code/agents/fixed_streaming_translation.py',
        'main_pc_code/agents/executor.py',
        'main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py',
        'main_pc_code/FORMAINPC/LocalFineTunerAgent.py',
        'main_pc_code/FORMAINPC/NLLBAdapter.py',
        'main_pc_code/agents/vram_optimizer_agent.py',
        'main_pc_code/FORMAINPC/ChainOfThoughtAgent.py',
        'main_pc_code/FORMAINPC/GOT_TOTAgent.py',
        'main_pc_code/FORMAINPC/CognitiveModelAgent.py',
        'main_pc_code/agents/face_recognition_agent.py',
        'main_pc_code/agents/learning_orchestration_service.py',
        'main_pc_code/agents/learning_opportunity_detector.py',
        'main_pc_code/agents/learning_manager.py',
        'main_pc_code/agents/active_learning_monitor.py',
        'main_pc_code/FORMAINPC/LearningAdjusterAgent.py',
        'main_pc_code/agents/model_orchestrator.py',
        'main_pc_code/agents/goal_manager.py',
        'main_pc_code/agents/IntentionValidatorAgent.py',
        'main_pc_code/agents/nlu_agent.py',
        'main_pc_code/agents/advanced_command_handler.py',
        'main_pc_code/agents/chitchat_agent.py',
        'main_pc_code/agents/feedback_handler.py',
        'main_pc_code/agents/responder.py',
        'main_pc_code/agents/translation_service.py',
        'main_pc_code/agents/DynamicIdentityAgent.py',
        'main_pc_code/agents/emotion_synthesis_agent.py',
        'main_pc_code/services/stt_service.py',
        'main_pc_code/services/tts_service.py',
        'main_pc_code/agents/streaming_audio_capture.py',
        'main_pc_code/agents/fused_audio_preprocessor.py',
        'main_pc_code/agents/streaming_interrupt_handler.py',
        'main_pc_code/agents/streaming_speech_recognition.py',
        'main_pc_code/agents/streaming_tts_agent.py',
        'main_pc_code/agents/wake_word_detector.py',
        'main_pc_code/agents/streaming_language_analyzer.py',
        'main_pc_code/agents/ProactiveAgent.py',
        'main_pc_code/agents/emotion_engine.py',
        'main_pc_code/agents/mood_tracker_agent.py',
        'main_pc_code/agents/human_awareness_agent.py',
        'main_pc_code/agents/tone_detector.py',
        'main_pc_code/agents/voice_profiling_agent.py',
        'main_pc_code/agents/EmpathyAgent.py'
    ]

    pc2_agents = [
        'pc2_code/agents/memory_orchestrator_service.py',
        'pc2_code/agents/tiered_responder.py',
        'pc2_code/agents/async_processor.py',
        'pc2_code/agents/cache_manager.py',
        'pc2_code/agents/VisionProcessingAgent.py',
        'pc2_code/agents/DreamWorldAgent.py',
        'pc2_code/agents/unified_memory_reasoning_agent.py',
        'pc2_code/agents/tutor_agent.py',
        'pc2_code/agents/tutoring_agent.py',
        'pc2_code/agents/context_manager.py',
        'pc2_code/agents/experience_tracker.py',
        'pc2_code/agents/resource_manager.py',
        'pc2_code/agents/task_scheduler.py',
        'pc2_code/agents/ForPC2/AuthenticationAgent.py',
        'pc2_code/agents/ForPC2/unified_utils_agent.py',
        'pc2_code/agents/ForPC2/proactive_context_monitor.py',
        'pc2_code/agents/AgentTrustScorer.py',
        'pc2_code/agents/filesystem_assistant_agent.py',
        'pc2_code/agents/remote_connector_agent.py',
        'pc2_code/agents/unified_web_agent.py',
        'pc2_code/agents/DreamingModeAgent.py',
        'pc2_code/agents/advanced_router.py'
    ]
    
    # Analyze MainPC agents
    print("\n🔍 MAINPC AGENTS ANALYSIS:")
    print("-" * 40)
    mainpc_baseagent_agents = []
    mainpc_legacy_agents = []
    mainpc_patterns = {}
    
    for agent_path in mainpc_agents:
        result = check_baseagent_usage(agent_path)
        agent_name = os.path.basename(agent_path)
        
        if result['uses_baseagent']:
            print(f"✅ {agent_name}: USES BASEAGENT")
            mainpc_baseagent_agents.append(agent_name)
        else:
            status_info = []
            if result['import']:
                status_info.append('HAS_IMPORT')
            if result['inheritance']:
                status_info.append('HAS_INHERITANCE')
            if result['patterns']:
                status_info.extend(result['patterns'])
                for pattern in result['patterns']:
                    if pattern not in mainpc_patterns:
                        mainpc_patterns[pattern] = []
                    mainpc_patterns[pattern].append(agent_name)
                    
            print(f"❌ {agent_name}: NO BASEAGENT [{', '.join(status_info) if status_info else 'NONE'}]")
            mainpc_legacy_agents.append((agent_name, status_info))
    
    # Analyze PC2 agents
    print("\n🔍 PC2 AGENTS ANALYSIS:")
    print("-" * 40)
    pc2_baseagent_agents = []
    pc2_legacy_agents = []
    pc2_patterns = {}
    
    for agent_path in pc2_agents:
        result = check_baseagent_usage(agent_path)
        agent_name = os.path.basename(agent_path)
        
        if result['uses_baseagent']:
            print(f"✅ {agent_name}: USES BASEAGENT")
            pc2_baseagent_agents.append(agent_name)
        else:
            status_info = []
            if result['import']:
                status_info.append('HAS_IMPORT')
            if result['inheritance']:
                status_info.append('HAS_INHERITANCE')
            if result['patterns']:
                status_info.extend(result['patterns'])
                for pattern in result['patterns']:
                    if pattern not in pc2_patterns:
                        pc2_patterns[pattern] = []
                    pc2_patterns[pattern].append(agent_name)
                    
            print(f"❌ {agent_name}: NO BASEAGENT [{', '.join(status_info) if status_info else 'NONE'}]")
            pc2_legacy_agents.append((agent_name, status_info))
    
    # Summary statistics
    total_mainpc = len(mainpc_agents)
    total_pc2 = len(pc2_agents)
    total_agents = total_mainpc + total_pc2
    
    mainpc_baseagent_count = len(mainpc_baseagent_agents)
    pc2_baseagent_count = len(pc2_baseagent_agents)
    total_baseagent_count = mainpc_baseagent_count + pc2_baseagent_count
    
    print("\n" + "=" * 60)
    print("📊 BASELINE ADOPTION SUMMARY")
    print("=" * 60)
    print(f"MainPC BaseAgent Adoption: {mainpc_baseagent_count}/{total_mainpc} ({mainpc_baseagent_count/total_mainpc*100:.1f}%)")
    print(f"PC2 BaseAgent Adoption: {pc2_baseagent_count}/{total_pc2} ({pc2_baseagent_count/total_pc2*100:.1f}%)")
    print(f"TOTAL BaseAgent Adoption: {total_baseagent_count}/{total_agents} ({total_baseagent_count/total_agents*100:.1f}%)")
    
    print(f"\n🎯 WEEK 2 MIGRATION REQUIREMENTS:")
    print(f"Agents Requiring Migration: {total_agents - total_baseagent_count}")
    print(f"Week 2 Target (+6 agents): {total_baseagent_count + 6}/{total_agents} ({(total_baseagent_count + 6)/total_agents*100:.1f}%)")
    
    # Pattern analysis
    all_patterns = {**mainpc_patterns, **pc2_patterns}
    if all_patterns:
        print(f"\n🔍 LEGACY PATTERN ANALYSIS:")
        for pattern, agents in all_patterns.items():
            print(f"  {pattern}: {len(agents)} agents")
    
    print("\n✅ Day 1 Task 1 Complete: BaseAgent Adoption Analysis")
    return {
        'total_agents': total_agents,
        'total_baseagent': total_baseagent_count,
        'mainpc_baseagent': mainpc_baseagent_agents,
        'pc2_baseagent': pc2_baseagent_agents,
        'mainpc_legacy': mainpc_legacy_agents,
        'pc2_legacy': pc2_legacy_agents,
        'patterns': all_patterns
    }

if __name__ == "__main__":
    main() 