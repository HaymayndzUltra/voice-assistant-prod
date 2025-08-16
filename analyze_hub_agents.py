#!/usr/bin/env python3
import yaml
from pathlib import Path
import csv

# The 5 main hubs
HUBS = {
    'AffectiveProcessingCenter',
    'RealTimeAudioPipeline', 
    'ModelOpsCoordinator',
    'UnifiedObservabilityCenter',
    'MemoryFusionHub',
    'RealTimeAudioPipelinePC2'  # PC2 variant
}

# Services that might be consolidated into hubs
POTENTIALLY_CONSOLIDATED = {
    # Into AffectiveProcessingCenter
    'EmotionEngine', 'EmotionSynthesisAgent', 'MoodTrackerAgent', 'EmpathyAgent',
    'ToneDetector', 'DynamicIdentityAgent',
    
    # Into RealTimeAudioPipeline
    'AudioCapture', 'StreamingSpeechRecognition', 'StreamingTTSAgent',
    'STTService', 'TTSService', 'Responder', 'VoiceProfilingAgent',
    'StreamingInterruptHandler', 'StreamingLanguageAnalyzer',
    'SpeechRelayService', 'NoiseReductionAgent',
    
    # Into ModelOpsCoordinator
    'ModelManagerSuite', 'VRAMOptimizerAgent', 'RequestCoordinator',
    'TinyLlamaServiceEnhanced', 'ChainOfThoughtAgent', 'CognitiveModelAgent',
    
    # Into UnifiedObservabilityCenter
    'ObservabilityDashboardAPI', 'ObservabilityHub', 'ActiveLearningMonitor',
    'PredictiveHealthMonitor',
    
    # Into MemoryFusionHub
    'MemoryClient', 'SessionMemoryAgent', 'LearningManager',
    'LearningOpportunityDetector'
}

def analyze_agents():
    results = []
    
    # Analyze MainPC
    mainpc_path = Path('main_pc_code/config/startup_config.yaml')
    with open(mainpc_path) as f:
        doc = yaml.safe_load(f)
        agent_groups = doc.get('agent_groups', {})
        
        for group_name, group_content in agent_groups.items():
            if isinstance(group_content, dict):
                for agent_name, agent_data in group_content.items():
                    if isinstance(agent_data, dict):
                        category = 'hub' if agent_name in HUBS else \
                                   'potentially_consolidated' if agent_name in POTENTIALLY_CONSOLIDATED else \
                                   'active'
                        
                        required = agent_data.get('required', True)
                        port = agent_data.get('port', 'n/a')
                        health_port = agent_data.get('health_check_port', 'n/a')
                        
                        results.append({
                            'host': 'MainPC',
                            'group': group_name,
                            'agent': agent_name,
                            'category': category,
                            'required': required,
                            'port': port,
                            'health_check_port': health_port
                        })
    
    # Analyze PC2
    pc2_path = Path('pc2_code/config/startup_config.yaml')
    with open(pc2_path) as f:
        doc = yaml.safe_load(f)
        services = doc.get('pc2_services', [])
        
        for service in services:
            if isinstance(service, dict):
                agent_name = service.get('name', '')
                if agent_name:
                    # Treat RealTimeAudioPipelinePC2 as a hub
                    if agent_name == 'RealTimeAudioPipelinePC2':
                        category = 'hub'
                    else:
                        category = 'hub' if agent_name in HUBS else \
                                   'potentially_consolidated' if agent_name in POTENTIALLY_CONSOLIDATED else \
                                   'active'
                    
                    required = service.get('required', True)
                    port = service.get('port', 'n/a')
                    health_port = service.get('health_check_port', 'n/a')
                    
                    results.append({
                        'host': 'PC2',
                        'group': 'pc2_services',
                        'agent': agent_name,
                        'category': category,
                        'required': required,
                        'port': port,
                        'health_check_port': health_port
                    })
    
    return results

def main():
    results = analyze_agents()
    
    # Print summary
    print("=" * 60)
    print("AGENT ANALYSIS SUMMARY")
    print("=" * 60)
    
    # Group by category
    hubs = [r for r in results if r['category'] == 'hub']
    consolidated = [r for r in results if r['category'] == 'potentially_consolidated']
    active = [r for r in results if r['category'] == 'active']
    
    print(f"\n📍 HUB SERVICES ({len(hubs)} total):")
    for r in hubs:
        req_status = "✅" if r['required'] else "❌"
        print(f"  {req_status} {r['agent']} ({r['host']}) - required={r['required']}")
    
    print(f"\n⚠️ POTENTIALLY CONSOLIDATED ({len(consolidated)} total):")
    for r in consolidated:
        req_status = "✅" if r['required'] else "❌"
        print(f"  {req_status} {r['agent']} ({r['host']}) - required={r['required']}")
        
    print(f"\n✨ OTHER ACTIVE SERVICES ({len(active)} total):")
    # Just show count and first few
    for r in active[:10]:
        req_status = "✅" if r['required'] else "❌"
        print(f"  {req_status} {r['agent']} ({r['host']}) - required={r['required']}")
    if len(active) > 10:
        print(f"  ... and {len(active) - 10} more")
    
    # Write to CSV
    with open('agent_analysis.csv', 'w', newline='') as f:
        fieldnames = ['host', 'group', 'agent', 'category', 'required', 'port', 'health_check_port']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n📄 Full details written to agent_analysis.csv")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    
    consolidated_required = [r for r in consolidated if r['required']]
    if consolidated_required:
        print(f"\n🔴 {len(consolidated_required)} potentially consolidated services are still required=true:")
        for r in consolidated_required:
            print(f"  - {r['agent']} ({r['host']})")
        print("\nConsider setting these to required=false if they're truly consolidated into hubs.")

if __name__ == '__main__':
    main()