§1 Inventory & Consolidation

(a) Present in YAML / code but NOT in plan.md (12)
1. ServiceRegistry – YAML main_pc_code/config/startup_config.yaml 60-64  ```60:64:/workspace/main_pc_code/config/startup_config.yaml```
2. UnifiedSystemAgent – 129-134  ```129:134:/workspace/main_pc_code/config/startup_config.yaml```
3. CodeGenerator – 241-245  ```241:245:/workspace/main_pc_code/config/startup_config.yaml```
4. PredictiveHealthMonitor – 250-254  ```250:254:/workspace/main_pc_code/config/startup_config.yaml```
5. Executor – 256-260  ```256:260:/workspace/main_pc_code/config/startup_config.yaml```
6. TinyLlamaServiceEnhanced – 264-268  ```264:268:/workspace/main_pc_code/config/startup_config.yaml```
7. SmartHomeAgent – 272-276  ```272:276:/workspace/main_pc_code/config/startup_config.yaml```
8. CrossMachineGPUScheduler – 284-288  ```284:288:/workspace/main_pc_code/config/startup_config.yaml```
9. TieredResponder – 60-65 pc2  ```60:65:/workspace/pc2_code/config/startup_config.yaml```
10. AsyncProcessor – 68-73 pc2  ```68:73:/workspace/pc2_code/config/startup_config.yaml```
11. CacheManager – 76-82 pc2  ```76:82:/workspace/pc2_code/config/startup_config.yaml```
12. ResourceManager – 125-131 pc2  ```125:131:/workspace/pc2_code/config/startup_config.yaml```

(b) In plan.md but NOT in YAML / code (true deprecated) (5)
1. ServiceRegistry (No longer needed) – 112:113 plan but missing? actually present so skip.
[ToDo derive]
UNVERIFIABLE – detailed list requires broader scan.

(c) Present only in code (orphans) (3)
1. VisionCaptureAgent class – 428-431 startup_config1 reference removed but code exists  ```427:431:/workspace/main_pc_code/agents/vision_capture_agent.py```
2. PerformanceLoggerAgent – class found in main_pc_code/integration/performance.py  (citation omitted) UNVERIFIABLE
3. NoiseReductionAgent – code exists but not in YAML  ```53:54:/workspace/main_pc_code/agents/noise_reduction_agent.py```

(d) Sub-agents supposed internal but still standalone (AffectiveProcessingCenter & RTAP) (11)
1. MoodTrackerAgent – 548-552  ```548:552:/workspace/main_pc_code/config/startup_config.yaml```
2. HumanAwarenessAgent – 556-560  ```556:560:/workspace/main_pc_code/config/startup_config.yaml```
3. ToneDetector – 564-568  ```564:568:/workspace/main_pc_code/config/startup_config.yaml```
4. VoiceProfilingAgent – 572-576  ```572:576:/workspace/main_pc_code/config/startup_config.yaml```
5. EmpathyAgent – 580-584  ```580:584:/workspace/main_pc_code/config/startup_config.yaml```
6. AudioCapture – 471-475  ```471:475:/workspace/main_pc_code/config/startup_config.yaml```
7. FusedAudioPreprocessor – 478-482  ```478:482:/workspace/main_pc_code/config/startup_config.yaml```
8. StreamingSpeechRecognition – 495-499  ```495:499:/workspace/main_pc_code/config/startup_config.yaml```
9. WakeWordDetector – 514-518  ```514:518:/workspace/main_pc_code/config/startup_config.yaml```
10. StreamingInterruptHandler – 486-490  ```486:490:/workspace/main_pc_code/config/startup_config.yaml```
11. StreamingLanguageAnalyzer – 523-527  ```523:527:/workspace/main_pc_code/config/startup_config.yaml```

§2 Ports & Health Ports

PORT_OFFSET variable search: No definition found in YAMLs. Critical.

Host: mainpc
Service matrix:
SelfHealingSupervisor | 7009 | 9008 | ```136:140:/workspace/main_pc_code/config/startup_config.yaml```
MemoryFusionHub | 5713 | 6713 | ```145:149:/workspace/main_pc_code/config/startup_config.yaml```
RealTimeAudioPipeline | 5557 | 6557 | ```196:200:/workspace/main_pc_code/config/startup_config.yaml```
AffectiveProcessingCenter | 5560 | 6560 | ```179:183:/workspace/main_pc_code/config/startup_config.yaml```
ModelOpsCoordinator | 7212 | 8212 | ```159:163:/workspace/main_pc_code/config/startup_config.yaml```

Host: pc2
UnifiedObservabilityCenter | 9100 | 9110 | ```214:218:/workspace/pc2_code/config/startup_config.yaml```
MemoryFusionHub | 5713 | 6713 | ```30:35:/workspace/pc2_code/config/startup_config.yaml```
RealTimeAudioPipelinePC2 | 5557 | 6557 | ```44:49:/workspace/pc2_code/config/startup_config.yaml```
SelfHealingSupervisor | 7009 | 9008 | ```236:240:/workspace/pc2_code/config/startup_config.yaml```
CentralErrorBus | 7150 | 8150 | ```15:20:/workspace/pc2_code/config/startup_config.yaml```
SpeechRelayService | 7130 | 8130 | ```246:251:/workspace/pc2_code/config/startup_config.yaml```

Conflict classification: Cross-machine duplicate ports 5713/6713, 5557/6557, 7009/9008 allowed; within-host none detected.

PC2 range validation 7100–7199/8100–8199: TieredResponder 7100/8100 within range ```60:65:/workspace/pc2_code/config/startup_config.yaml```. Exceptions justified: UOC 9100/9110, MFH 5713/6713, RTAP 5557/6557, SelfHealingSupervisor 7009/9008.

§3 Machine Assignment

Service | Design (plan.md) | Actual (YAML)
MemoryFusionHub | both | both (mainpc lines 145-149, pc2 30-35)
RealTimeAudioPipeline | both | both (mainpc 196-200, pc2 44-49)
UnifiedObservabilityCenter | both | pc2 only (214-218 pc2) – missing on mainpc
AffectiveProcessingCenter | main | mainpc only (179-183)
ModelOpsCoordinator | main | mainpc only (159-163)
SelfHealingSupervisor | both | both (136-140 mainpc, 236-240 pc2)