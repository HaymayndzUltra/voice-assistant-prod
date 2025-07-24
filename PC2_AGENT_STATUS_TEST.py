#!/usr/bin/env python3
"""
PC2 Agent Status Testing Script
Using MainPC AI's proven importlib.util methodology
"""

import sys
import os
import importlib.util
from pathlib import Path

def test_pc2_agents():
    print('🧪 PC2 AGENT STATUS VERIFICATION - USING MAINPC AI PROVEN METHOD')
    print('=' * 70)
    
    # PC2 agents from startup_config.yaml analysis
    pc2_agents = [
        # Core Integration Layer
        ('MemoryOrchestratorService', 'pc2_code/agents/memory_orchestrator_service.py'),
        ('TieredResponder', 'pc2_code/agents/tiered_responder.py'),
        ('AsyncProcessor', 'pc2_code/agents/async_processor.py'),
        ('CacheManager', 'pc2_code/agents/cache_manager.py'),
        
        # Vision & AI Processing
        ('VisionProcessingAgent', 'pc2_code/agents/VisionProcessingAgent.py'),
        ('DreamWorldAgent', 'pc2_code/agents/DreamWorldAgent.py'),
        ('UnifiedMemoryReasoningAgent', 'pc2_code/agents/unified_memory_reasoning_agent.py'),
        
        # Tutoring & Learning
        ('TutorAgent', 'pc2_code/agents/tutor_agent.py'),
        ('TutoringAgent', 'pc2_code/agents/tutoring_agent.py'),
        
        # System Management
        ('ContextManager', 'pc2_code/agents/context_manager.py'),
        ('ExperienceTracker', 'pc2_code/agents/experience_tracker.py'),
        ('ResourceManager', 'pc2_code/agents/resource_manager.py'),
        ('TaskScheduler', 'pc2_code/agents/task_scheduler.py'),
        
        # ForPC2 Specialized Agents
        ('AuthenticationAgent', 'pc2_code/agents/ForPC2/AuthenticationAgent.py'),
        ('UnifiedUtilsAgent', 'pc2_code/agents/ForPC2/unified_utils_agent.py'),
        ('ProactiveContextMonitor', 'pc2_code/agents/ForPC2/proactive_context_monitor.py'),
        
        # Advanced Services
        ('AgentTrustScorer', 'pc2_code/agents/AgentTrustScorer.py'),
        ('FileSystemAssistantAgent', 'pc2_code/agents/filesystem_assistant_agent.py'),
        ('RemoteConnectorAgent', 'pc2_code/agents/remote_connector_agent.py'),
        ('UnifiedWebAgent', 'pc2_code/agents/unified_web_agent.py'),
        ('DreamingModeAgent', 'pc2_code/agents/DreamingModeAgent.py'),
        ('AdvancedRouter', 'pc2_code/agents/advanced_router.py'),
        
        # Monitoring (different path)
        ('ObservabilityHub', 'phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py'),
    ]
    
    print(f'📋 Testing {len(pc2_agents)} PC2 agents from startup_config.yaml')
    print()
    
    working_agents = []
    broken_agents = []
    
    for agent_name, agent_path in pc2_agents:
        if not os.path.exists(agent_path):
            print(f'❌ {agent_name} - FILE NOT FOUND: {agent_path}')
            broken_agents.append((agent_name, 'FILE_NOT_FOUND', agent_path))
            continue
            
        try:
            spec = importlib.util.spec_from_file_location(agent_name, agent_path)
            if spec is None:
                print(f'❌ {agent_name} - SPEC CREATION FAILED')
                broken_agents.append((agent_name, 'SPEC_FAILED', agent_path))
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f'✅ {agent_name} - IMPORT SUCCESSFUL')
            working_agents.append((agent_name, agent_path))
            
            # Try to find agent classes
            try:
                agent_classes = [getattr(module, name) for name in dir(module) 
                               if name.endswith('Agent') and not name.startswith('_')]
                if agent_classes:
                    print(f'   📋 Found classes: {[cls.__name__ for cls in agent_classes]}')
            except:
                pass  # Skip if class inspection fails
                
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)[:80]  # Longer error message for better debugging
            print(f'❌ {agent_name} - {error_type}: {error_msg}')
            broken_agents.append((agent_name, f'{error_type}: {error_msg}', agent_path))
    
    print()
    print('📊 PC2 AGENT STATUS SUMMARY:')
    print('=' * 50)
    print(f'✅ Working: {len(working_agents)}/{len(pc2_agents)} ({len(working_agents)/len(pc2_agents)*100:.1f}%)')
    print(f'❌ Broken: {len(broken_agents)}/{len(pc2_agents)} ({len(broken_agents)/len(pc2_agents)*100:.1f}%)')
    print()
    
    if working_agents:
        print('✅ WORKING AGENTS:')
        for i, (agent, path) in enumerate(working_agents, 1):
            print(f'  {i:2d}. {agent}')
        print()
    
    if broken_agents:
        print('❌ BROKEN AGENTS:')
        for i, (agent, error, path) in enumerate(broken_agents, 1):
            print(f'  {i:2d}. {agent}: {error}')
            print(f'      Path: {path}')
        print()
    
    # Summary for coordination
    print('🤝 COORDINATION SUMMARY:')
    print(f'   PC2 AI Current Status: {len(working_agents)}/{len(pc2_agents)} working ({len(working_agents)/len(pc2_agents)*100:.1f}%)')
    
    if len(working_agents) >= len(pc2_agents) * 0.7:
        print('   🎯 Status: GOOD - Above 70% working')
    elif len(working_agents) >= len(pc2_agents) * 0.5:
        print('   ⚠️  Status: MODERATE - Need improvement')
    else:
        print('   🚨 Status: CRITICAL - Major fixes needed')
        
    return working_agents, broken_agents

if __name__ == "__main__":
    test_pc2_agents() 