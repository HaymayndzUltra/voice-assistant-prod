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

PORT_OFFSET definition: NOT FOUND in any *.env, compose, or script files (grep PORT_OFFSET showed only templated usages); therefore computed as 0 → CRITICAL.

Complete per-host matrix (required:true services only; PORT_OFFSET=0):

| host | service | svc_port | health_port | citation |
|------|---------|----------|-------------|----------|
| main | ServiceRegistry | 7200 | 8200 | 60-64:main_pc_code/config/startup_config.yaml |
| main | SystemDigitalTwin | 7220 | 8220 | 71-75:main_pc_code/config/startup_config.yaml |
| main | SelfHealingSupervisor | 7009 | 9008 | 136-140:main_pc_code/config/startup_config.yaml |
| main | MemoryFusionHub | 5713 | 6713 | 145-149:main_pc_code/config/startup_config.yaml |
| main | ModelOpsCoordinator | 7212 | 8212 | 159-163:main_pc_code/config/startup_config.yaml |
| main | AffectiveProcessingCenter | 5560 | 6560 | 179-183:main_pc_code/config/startup_config.yaml |
| main | RealTimeAudioPipeline | 5557 | 6557 | 196-200:main_pc_code/config/startup_config.yaml |
| main | CrossMachineGPUScheduler | 7155 | 8155 | 284-287:main_pc_code/config/startup_config.yaml |
| main | CodeGenerator | 241-245 | 5650 | 6650 | 241-245:main_pc_code/config/startup_config.yaml |
| main | PredictiveHealthMonitor | 5613 | 6613 | 250-253:main_pc_code/config/startup_config.yaml |
| main | Executor | 5606 | 6606 | 256-259:main_pc_code/config/startup_config.yaml |
| main | ObservabilityDashboardAPI | 8001 | 9007 | 605-608:main_pc_code/config/startup_config.yaml |
| pc2  | CentralErrorBus | 7150 | 8150 | 15-20:pc2_code/config/startup_config.yaml |
| pc2  | MemoryFusionHub | 5713 | 6713 | 30-35:pc2_code/config/startup_config.yaml |
| pc2  | RealTimeAudioPipelinePC2 | 5557 | 6557 | 44-49:pc2_code/config/startup_config.yaml |
| pc2  | SelfHealingSupervisor | 7009 | 9008 | 236-241:pc2_code/config/startup_config.yaml |
| pc2  | UnifiedObservabilityCenter | 9100 | 9110 | 214-219:pc2_code/config/startup_config.yaml |
| pc2  | SpeechRelayService | 7130 | 8130 | 246-251:pc2_code/config/startup_config.yaml |
| pc2  | TieredResponder | 7100 | 8100 | 60-65:pc2_code/config/startup_config.yaml |

Conflict classification:
• within-host: none detected (all svc/health pairs unique on each host).
• cross-machine duplicates (allowed by design): {5713/6713 MemoryFusionHub, 5557/6557 RTAP, 7009/9008 SelfHealingSupervisor}.
• documented exceptions outside PC2 7100–7199 range: 5713/6713 (MFH), 5557/6557 (RTAP), 7009/9008 (Supervisor), 9100/9110 (UOC).

Counts: total rows in matrix = 19; duplicates flagged = 3 sets → 6 ports.

§3 Machine Assignment (full list of hubs & infra services)

| service | design (plan.md §F) | actual YAML+code | citation |
|---------|--------------------|------------------|----------|
| ServiceRegistry | main | main | 60-64 main config |
| SystemDigitalTwin | main | main | 71-75 main config |
| UnifiedSystemAgent | main | main | 129-134 main config |
| SelfHealingSupervisor | both | both | 136-140 main; 236-241 pc2 |
| MemoryFusionHub | both | both | 145-149 main; 30-35 pc2 |
| ModelOpsCoordinator | main | main | 159-163 main config |
| AffectiveProcessingCenter | main | main | 179-183 main config |
| RealTimeAudioPipeline | both | both (PC2 variant) | 196-204 main; 44-50 pc2 |
| UnifiedObservabilityCenter | both | pc2 only (missing main agent) | 214-219 pc2; 627-633 main group reference |
| CrossMachineGPUScheduler | main | main | 284-287 main config |
| ObservabilityDashboardAPI | main | main (duplicates UOC) | 605-608 main config |
| CentralErrorBus | pc2 | pc2 | 15-20 pc2 config |
| SpeechRelayService | pc2 | pc2 | 246-251 pc2 config |

Summary: Out of 12 blueprint critical services, 1 drift (UOC absent on main).