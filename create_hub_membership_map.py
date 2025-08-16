#!/usr/bin/env python3
"""
Creates hub_membership_report.csv based on our consolidation mapping
"""
import csv
from pathlib import Path

# Hub to agent mapping based on our analysis
HUB_MAPPINGS = {
    'AffectiveProcessingCenter': [
        'EmotionEngine',
        'EmotionSynthesisAgent',
        'MoodTrackerAgent',
        'EmpathyAgent',
        'ToneDetector',
        'DynamicIdentityAgent',
    ],
    'RealTimeAudioPipeline': [
        'STTService',
        'TTSService',
        'StreamingTTSAgent',
        'Responder',
        'VoiceProfilingAgent',
        'AudioCapture',
        'StreamingSpeechRecognition',
        'StreamingInterruptHandler',
        'StreamingLanguageAnalyzer',
        'NoiseReductionAgent',
    ],
    'ModelOpsCoordinator': [
        'ChainOfThoughtAgent',
        'TinyLlamaServiceEnhanced',
        'CognitiveModelAgent',
        'ModelManagerSuite',
        'VRAMOptimizerAgent',
        'RequestCoordinator',
    ],
    'UnifiedObservabilityCenter': [
        'PredictiveHealthMonitor',
        'ActiveLearningMonitor',
        'ObservabilityDashboardAPI',
        'ObservabilityHub',
    ],
    'MemoryFusionHub': [
        'LearningOpportunityDetector',
        'LearningManager',
        'MemoryClient',
        'SessionMemoryAgent',
    ],
    'RealTimeAudioPipelinePC2': [
        'SpeechRelayService',
    ]
}

def main():
    output_dir = Path('audits')
    output_dir.mkdir(exist_ok=True)
    
    rows = []
    
    # Generate mappings for each hub
    for hub, agents in HUB_MAPPINGS.items():
        for agent in agents:
            # Determine host based on hub name
            if 'PC2' in hub:
                host = 'PC2'
            elif hub == 'ModelOpsCoordinator':
                host = 'MainPC'  # ModelOpsCoordinator is MainPC only
            else:
                # Most hubs are on both machines, but agents might be specific
                # For simplicity, assign to MainPC unless it's SpeechRelayService
                if agent == 'SpeechRelayService':
                    host = 'PC2'
                else:
                    host = 'MainPC'
            
            # Set source based on known info
            source = 'mapping'
            
            # Determine group (from our earlier analysis)
            if agent in ['EmotionEngine', 'MoodTrackerAgent', 'ToneDetector', 'VoiceProfilingAgent', 'EmpathyAgent']:
                group = 'emotion_processing'
            elif agent in ['STTService', 'TTSService', 'AudioCapture', 'StreamingSpeechRecognition', 
                          'StreamingTTSAgent', 'StreamingInterruptHandler', 'StreamingLanguageAnalyzer']:
                group = 'audio_interface'
            elif agent in ['EmotionSynthesisAgent', 'DynamicIdentityAgent', 'Responder']:
                group = 'language_stack'
            elif agent in ['ChainOfThoughtAgent', 'TinyLlamaServiceEnhanced', 'CognitiveModelAgent']:
                group = 'reasoning_services'
            elif agent in ['LearningOpportunityDetector', 'LearningManager', 'ActiveLearningMonitor']:
                group = 'learning_pipeline'
            elif agent in ['PredictiveHealthMonitor']:
                group = 'gpu_infrastructure'
            elif agent in ['ObservabilityDashboardAPI']:
                group = 'translation_services'
            elif agent == 'SpeechRelayService':
                group = 'pc2_services'
            else:
                group = 'foundation_services'
            
            # Default values for other fields
            required = True  # Most are still required=true
            ports = 'n/a'  # We'll update this based on actual config
            signals = ''  # Will be filled by verification
            verdict = 'active'  # Default
            
            # Map target hub name for PC2 variant
            target_hub = hub.replace('PC2', '') if 'PC2' in hub else hub
            
            rows.append({
                'hub': target_hub,
                'agent': agent,
                'source': source,
                'host': host,
                'group': group,
                'required': required,
                'ports': ports,
                'signals': signals,
                'verdict': verdict,
                'source_file': f'{host.lower()}_code/config/startup_config.yaml'
            })
    
    # Write CSV
    csv_path = output_dir / 'hub_membership_report.csv'
    with open(csv_path, 'w', newline='') as f:
        fieldnames = ['hub', 'agent', 'source', 'host', 'group', 'required', 'ports', 'signals', 'verdict', 'source_file']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Created {csv_path} with {len(rows)} agent-to-hub mappings")
    
    # Summary
    print("\n📊 Summary by hub:")
    for hub in HUB_MAPPINGS:
        count = sum(1 for r in rows if r['hub'] == hub.replace('PC2', ''))
        print(f"  {hub}: {count} agents")

if __name__ == '__main__':
    main()