§1 Inventory & Consolidation

Total services/agents evaluated: 92 (plan.md §F rows + additional YAML entries)

(a) In YAML/code but missing in plan.md – count: **3**
- CrossMachineGPUScheduler – 284-287:main_pc_code/config/startup_config.yaml
- StreamingTranslationProxy – 597-604:main_pc_code/config/startup_config.yaml
- SpeechRelayService – 246-251:pc2_code/config/startup_config.yaml

(b) In plan.md but absent in YAML & code (deprecated) – count: **1**
- GoalManager – 375-381:memory-bank/DOCUMENTS/plan.md

(c) Present only in code (orphans) – count: **3**
- VisionCaptureAgent – 60-61:main_pc_code/agents/vision_capture_agent.py
- NoiseReductionAgent – 53-54:main_pc_code/agents/noise_reduction_agent.py
- PerformanceLoggerAgent – 26-27:main_pc_code/integration/performance.py

(d) Standalone sub-agents that should be internal to hubs – count: **11**
- MoodTrackerAgent – 548-555:main_pc_code/config/startup_config.yaml
- HumanAwarenessAgent – 556-563:main_pc_code/config/startup_config.yaml
- ToneDetector – 564-571:main_pc_code/config/startup_config.yaml
- VoiceProfilingAgent – 572-579:main_pc_code/config/startup_config.yaml
- EmpathyAgent – 580-587:main_pc_code/config/startup_config.yaml
- AudioCapture – 471-478:main_pc_code/config/startup_config.yaml
- FusedAudioPreprocessor – 478-485:main_pc_code/config/startup_config.yaml
- StreamingInterruptHandler – 486-494:main_pc_code/config/startup_config.yaml
- StreamingSpeechRecognition – 495-503:main_pc_code/config/startup_config.yaml
- WakeWordDetector – 514-522:main_pc_code/config/startup_config.yaml
- StreamingLanguageAnalyzer – 523-531:main_pc_code/config/startup_config.yaml

*Risk note:* Lists (d) overlap with design consolidation rows (§F plan.md lines 118–119) but remain active in configs, indicating partial consolidation.

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

Additional machine assignment (selected utility/vision/audio groups):

| service | design (plan.md §F) | actual YAML | citation |
|---------|--------------------|-------------|----------|
| FaceRecognitionAgent | main | main | 319-324 main config |
| VisionProcessingAgent | pc2 | pc2 | 84-90 pc2 config |
| DreamWorldAgent | pc2 | pc2 | 92-99 pc2 config |
| STTService | main | main | 454-458 main config |
| TTSService | main | main | 462-466 main config |
| AudioCapture | main (legacy) | main (conditional) | 471-478 main config |
| SpeechRelayService | pc2 | pc2 | 246-251 pc2 config |
| TieredResponder | pc2 | pc2 | 60-65 pc2 config |
| LearningManager | main | main | 346-354 main config |
| TutoringServiceAgent | pc2 | pc2 | 228-234 pc2 config |

Orphan code additions (present in code, no YAML entry):
- VisionCaptureAgent – main_pc_code/agents/vision_capture_agent.py:60-61
- NoiseReductionAgent – main_pc_code/agents/noise_reduction_agent.py:53-54
- PerformanceLoggerAgent – main_pc_code/integration/performance.py:26-27

Counts updated:
(a) YAML/code missing in plan.md: 3 items
(b) Plan-only deprecated: 1 item
(c) Code-only orphans: 3 items
(d) Standalone sub-agents needing consolidation: 11 items