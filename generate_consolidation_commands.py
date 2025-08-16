#!/usr/bin/env python3
import yaml
from pathlib import Path

# Services to set to required=false (based on analysis)
MAINPC_TO_DISABLE = [
    'PredictiveHealthMonitor',     # -> UnifiedObservabilityCenter
    'ChainOfThoughtAgent',          # -> ModelOpsCoordinator
    'LearningOpportunityDetector',  # -> MemoryFusionHub
    'LearningManager',              # -> MemoryFusionHub
    'ActiveLearningMonitor',        # -> UnifiedObservabilityCenter
    'Responder',                    # -> RealTimeAudioPipeline
    'DynamicIdentityAgent',         # -> AffectiveProcessingCenter
    'EmotionSynthesisAgent',        # -> AffectiveProcessingCenter
    'STTService',                   # -> RealTimeAudioPipeline
    'TTSService',                   # -> RealTimeAudioPipeline
    'StreamingTTSAgent',            # -> RealTimeAudioPipeline
    'EmotionEngine',                # -> AffectiveProcessingCenter
    'MoodTrackerAgent',             # -> AffectiveProcessingCenter
    'ToneDetector',                 # -> AffectiveProcessingCenter
    'VoiceProfilingAgent',          # -> RealTimeAudioPipeline
    'EmpathyAgent',                 # -> AffectiveProcessingCenter
]

PC2_TO_DISABLE = [
    'SpeechRelayService',           # -> RealTimeAudioPipelinePC2
]

def generate_yq_commands():
    commands = []
    
    # Generate commands for MainPC
    mainpc_config = 'main_pc_code/config/startup_config.yaml'
    for agent in MAINPC_TO_DISABLE:
        # yq command to set required=false for nested structure
        cmd = f"yq -i '(.agent_groups.*.{agent}.required) = false' {mainpc_config}"
        commands.append(cmd)
    
    # Generate commands for PC2
    pc2_config = 'pc2_code/config/startup_config.yaml'
    for agent in PC2_TO_DISABLE:
        # yq command to set required=false for array structure
        cmd = f"yq -i '(.pc2_services[] | select(.name == \"{agent}\")).required = false' {pc2_config}"
        commands.append(cmd)
    
    return commands

def main():
    commands = generate_yq_commands()
    
    print("=" * 60)
    print("YQ COMMANDS TO CONSOLIDATE SERVICES INTO 5 HUBS")
    print("=" * 60)
    
    print("\n📝 Commands to set consolidated services to required=false:\n")
    
    # Write to shell script
    with open('apply_consolidation.sh', 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Script to set consolidated services to required=false\n")
        f.write("# This implements the 5-hub consolidation strategy\n\n")
        
        f.write("echo 'Setting MainPC consolidated services to required=false...'\n")
        for cmd in commands:
            if 'main_pc_code' in cmd:
                print(cmd)
                f.write(f"{cmd}\n")
        
        f.write("\necho 'Setting PC2 consolidated services to required=false...'\n")
        for cmd in commands:
            if 'pc2_code' in cmd:
                print(cmd)
                f.write(f"{cmd}\n")
        
        f.write("\necho 'Consolidation complete!'\n")
    
    print("\n✅ Commands saved to: apply_consolidation.sh")
    print("\n📋 Summary:")
    print(f"  - MainPC: {len(MAINPC_TO_DISABLE)} services to consolidate")
    print(f"  - PC2: {len(PC2_TO_DISABLE)} services to consolidate")
    print(f"  - Total: {len(MAINPC_TO_DISABLE) + len(PC2_TO_DISABLE)} services")
    
    print("\n🚀 To apply changes:")
    print("  1. Review: cat apply_consolidation.sh")
    print("  2. Make executable: chmod +x apply_consolidation.sh")
    print("  3. Run: ./apply_consolidation.sh")
    
    print("\n⚠️ WARNING: This will modify your config files!")
    print("Make sure to backup first: cp main_pc_code/config/startup_config.yaml{,.bak}")

if __name__ == '__main__':
    main()