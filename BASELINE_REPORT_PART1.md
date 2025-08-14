§1 Inventory & Consolidation

(a) In YAML/code but missing in plan.md
- CrossMachineGPUScheduler – main_pc_code/config/startup_config.yaml:284-291 (present)
- StreamingTranslationProxy – main_pc_code/config/startup_config.yaml:597-604 (present)
- SpeechRelayService – pc2_code/config/startup_config.yaml:246-253 (present)

(b) In plan.md but absent in YAML & code (deprecated)
- GoalManager – memory-bank/DOCUMENTS/plan.md:375-381 (present), not in configs.

(c) Present only in code (orphan)
- PerformanceLoggerAgent – main_pc_code/integration/performance.py:26-27 (class listing) [citation pending]

(d) Sub-agents launched standalone but should be internal to hubs
- MoodTrackerAgent – main_pc_code/config/startup_config.yaml:548-555
- HumanAwarenessAgent – main_pc_code/config/startup_config.yaml:556-563
- ToneDetector – main_pc_code/config/startup_config.yaml:564-571
- VoiceProfilingAgent – main_pc_code/config/startup_config.yaml:572-579
- EmpathyAgent – main_pc_code/config/startup_config.yaml:580-587
- AudioCapture – main_pc_code/config/startup_config.yaml:471-478
- FusedAudioPreprocessor – main_pc_code/config/startup_config.yaml:478-485
- StreamingInterruptHandler – main_pc_code/config/startup_config.yaml:486-494
- StreamingSpeechRecognition – main_pc_code/config/startup_config.yaml:495-503
- WakeWordDetector – main_pc_code/config/startup_config.yaml:514-522
- StreamingLanguageAnalyzer – main_pc_code/config/startup_config.yaml:523-531

§2 Ports & Health Ports

PORT_OFFSET definition: NOT FOUND in configs; thus default 0 (CRITICAL).

Matrix (excerpt):
| host | service | service_port | health_port | citation |
| main | SelfHealingSupervisor | 7009 | 9008 | 136-140:main_pc_code/config/startup_config.yaml |
| main | MemoryFusionHub | 5713 | 6713 | 145-149:main_pc_code/config/startup_config.yaml |
| main | RealTimeAudioPipeline | 5557 | 6557 | 196-200:main_pc_code/config/startup_config.yaml |
| pc2 | SelfHealingSupervisor | 7009 | 9008 | 236-241:pc2_code/config/startup_config.yaml |
| pc2 | MemoryFusionHub | 5713 | 6713 | 30-35:pc2_code/config/startup_config.yaml |
| pc2 | UnifiedObservabilityCenter | 9100 | 9110 | 214-219:pc2_code/config/startup_config.yaml |

Conflicts: within-host none; cross-machine duplicates allowed.

PC2 range exceptions (outside 7100–7199): listed above services.

§3 Machine Assignment

| service | design (plan.md) | actual | citation |
| MemoryFusionHub | both | both | 145-149 main config; 30-35 pc2 config |
| RealTimeAudioPipeline | both | both (PC2 variant) | 196-204 main; 44-50 pc2 |
| UnifiedObservabilityCenter | both | pc2 only | 214-219 pc2; absence in main (reference 627-637) |