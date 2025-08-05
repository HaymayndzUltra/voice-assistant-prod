#!/usr/bin/env python3
"""
Agent Coverage Analysis
Check if all agents defined in Docker groups were properly hardened
"""

import re
from pathlib import Path

def extract_agents_from_docker_compose():
    """Extract all agent commands from docker-compose.yml files"""
    agents_by_group = {}
    
    docker_groups = [
        "infra_core", "coordination", "memory_stack", "language_stack",
        "reasoning_gpu", "learning_gpu", "vision_gpu", "speech_gpu",
        "translation_services", "emotion_system", "utility_cpu"
    ]
    
    for group in docker_groups:
        compose_file = Path(f"/workspace/docker/{group}/docker-compose.yml")
        if not compose_file.exists():
            continue
            
        with open(compose_file, 'r') as f:
            content = f.read()
        
        # Find all main_pc_code.agents commands (active ones, not commented)
        pattern = r'^\s*command:\s*\[.*"main_pc_code\.agents\.([^"]+)".*\]'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        if matches:
            agents_by_group[group] = matches
    
    return agents_by_group

def agents_i_claimed_to_harden():
    """List of agents I claimed to have hardened"""
    return [
        # infra_core
        "system_digital_twin",
        "service_registry_agent",
        
        # coordination  
        "request_coordinator",
        "vram_optimizer_agent",
        "model_manager_suite",  # NOT FOUND IN DOCKER!
        
        # memory_stack
        "session_memory_agent", 
        "knowledge_base",
        "memory_client",
        
        # language_stack
        "nlu_agent",
        "advanced_command_handler", 
        "chitchat_agent",
        
        # reasoning_gpu
        "learning_manager",
        
        # learning_gpu
        "learning_orchestration_service",
        
        # vision_gpu
        "face_recognition_agent",
        
        # speech_gpu
        "streaming_tts_agent",
        
        # translation_services
        "cloud_translation_service",
        
        # emotion_system
        "emotion_engine",
        "mood_tracker_agent", 
        "EmpathyAgent",
        
        # utility_cpu
        "code_generator_agent"
    ]

def main():
    print("🔍 AGENT COVERAGE ANALYSIS")
    print("=" * 50)
    
    actual_agents = extract_agents_from_docker_compose()
    claimed_agents = agents_i_claimed_to_harden()
    
    total_actual = 0
    total_claimed = len(claimed_agents)
    missing_agents = []
    false_claims = []
    
    print("\n📊 AGENTS BY GROUP:")
    for group, agents in actual_agents.items():
        print(f"\n🔧 {group.upper()}:")
        for agent in agents:
            total_actual += 1
            if agent in claimed_agents:
                print(f"   ✅ {agent} - HARDENED")
            else:
                print(f"   ❌ {agent} - MISSED!")
                missing_agents.append((group, agent))
    
    # Check for false claims
    all_actual_flat = []
    for agents in actual_agents.values():
        all_actual_flat.extend(agents)
    
    for claimed in claimed_agents:
        if claimed not in all_actual_flat:
            false_claims.append(claimed)
    
    print(f"\n🎯 COVERAGE SUMMARY:")
    print(f"   Actual agents in Docker: {total_actual}")
    print(f"   Agents I claimed: {total_claimed}")
    print(f"   Missing agents: {len(missing_agents)}")
    print(f"   False claims: {len(false_claims)}")
    
    coverage_rate = ((total_actual - len(missing_agents)) / total_actual * 100) if total_actual > 0 else 0
    print(f"   Coverage rate: {coverage_rate:.1f}%")
    
    if missing_agents:
        print(f"\n❌ MISSING AGENTS ({len(missing_agents)}):")
        for group, agent in missing_agents:
            print(f"   - {group}/{agent}")
    
    if false_claims:
        print(f"\n⚠️ FALSE CLAIMS ({len(false_claims)}):")
        for agent in false_claims:
            print(f"   - {agent} (not found in any Docker group)")
    
    if coverage_rate < 95:
        print(f"\n🚨 CRITICAL: Coverage is only {coverage_rate:.1f}%!")
        print("   Must harden all missing agents before completion!")
        return False
    else:
        print(f"\n✅ GOOD: Coverage is {coverage_rate:.1f}%")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)