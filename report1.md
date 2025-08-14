#BASELINE_REPORT_PART1

## §1 Inventory & Consolidation

  

- **Counts**

  - **YAML/code but missing in plan.md (a)**: 4

  - **In plan.md but absent in YAML & code (b)**: 0 (UNVERIFIABLE)

  - **Present only in code (c)**: 4

  - **Sub-agents launched standalone but should be internal (d)**: 12

  

- **(a) YAML/code but missing in plan.md**

  - GoTToTAgent (mainpc)

    - YAML: 301:309:main_pc_code/config/startup_config.yaml

  - FusedAudioPreprocessor (mainpc)

    - YAML: 479:485:main_pc_code/config/startup_config.yaml

  - StreamingInterruptHandler (mainpc)

    - YAML: 486:494:main_pc_code/config/startup_config.yaml

  - StreamingLanguageAnalyzer (mainpc)

    - YAML: 523:531:main_pc_code/config/startup_config.yaml

  

- **(b) In plan.md but absent in YAML & code (true deprecated)**

  - None proven (UNVERIFIABLE).

  

- **(c) Present only in code (orphans, not launched in YAML)**

  - NoiseReductionAgent

    - Code: 53:55:main_pc_code/agents/noise_reduction_agent.py

  - NoiseReductionAgent (optimized variant)

    - Code: 58:60:main_pc_code/agents/noise_reduction_agent_day4_optimized.py

  - VisionCaptureAgent

    - Code: 60:62:main_pc_code/agents/vision_capture_agent.py

  - PerformanceLoggerAgent (PC2 integration/tests)

    - Code: 20:22:pc2_code/agents/integration/performance.py

  

- **(d) Sub-agents that should be internal to hubs but launched standalone**

  - Affective subsystem (should be internal to AffectiveProcessingCenter)

    - MoodTrackerAgent: 548:555:main_pc_code/config/startup_config.yaml

    - HumanAwarenessAgent: 556:563:main_pc_code/config/startup_config.yaml

    - ToneDetector: 564:571:main_pc_code/config/startup_config.yaml

    - VoiceProfilingAgent: 572:579:main_pc_code/config/startup_config.yaml

    - EmpathyAgent: 580:588:main_pc_code/config/startup_config.yaml

    - EmotionSynthesisAgent: 445:452:main_pc_code/config/startup_config.yaml

  - Legacy audio chain (should be internal to RealTimeAudioPipeline)

    - AudioCapture: 471:478:main_pc_code/config/startup_config.yaml

    - FusedAudioPreprocessor: 479:485:main_pc_code/config/startup_config.yaml

    - StreamingInterruptHandler: 486:494:main_pc_code/config/startup_config.yaml

    - StreamingSpeechRecognition: 495:503:main_pc_code/config/startup_config.yaml

    - WakeWordDetector: 514:522:main_pc_code/config/startup_config.yaml

    - StreamingLanguageAnalyzer: 523:531:main_pc_code/config/startup_config.yaml

  

Cross-match anchors:

- Design hubs & ports: 113:121:memory-bank/DOCUMENTS/plan.md

- MainPC hub defs: 145:171, 179:187, 196:204:main_pc_code/config/startup_config.yaml

- PC2 hub defs: 30:38, 44:51, 214:221:pc2_code/config/startup_config.yaml

  
  

## §2 Ports & Health Ports

  

- **PORT_OFFSET verdict**

  - Found defined in script used for containerization: 65:69:batch_containerize_foundation.sh

  - Not defined in .env/.ini or YAML defaults (no matches in `.env*` and `.ini`; none in workflows): UNVERIFIABLE as a global runtime default.

  - For computation in this baseline, use 0.

  

- **Per-host matrix (selected required and all services/*)**

  

| host | service | service_port | health_port | source |

|------|---------|--------------|-------------|--------|

| mainpc | ServiceRegistry | ${PORT_OFFSET}+7200 | ${PORT_OFFSET}+8200 | 62:64:main_pc_code/config/startup_config.yaml |

| mainpc | SystemDigitalTwin | ${PORT_OFFSET}+7220 | ${PORT_OFFSET}+8220 | 71:75:main_pc_code/config/startup_config.yaml |

| mainpc | SelfHealingSupervisor | ${PORT_OFFSET}+7009 | ${PORT_OFFSET}+9008 | 136:140:main_pc_code/config/startup_config.yaml |

| mainpc | MemoryFusionHub | ${PORT_OFFSET}+5713 | ${PORT_OFFSET}+6713 | 145:149:main_pc_code/config/startup_config.yaml |

| mainpc | ModelOpsCoordinator | ${PORT_OFFSET}+7212 | ${PORT_OFFSET}+8212 | 159:163:main_pc_code/config/startup_config.yaml |

| mainpc | AffectiveProcessingCenter | ${PORT_OFFSET}+5560 | ${PORT_OFFSET}+6560 | 179:183:main_pc_code/config/startup_config.yaml |

| mainpc | RealTimeAudioPipeline | ${PORT_OFFSET}+5557 | ${PORT_OFFSET}+6557 | 196:200:main_pc_code/config/startup_config.yaml |

| mainpc | StreamingTranslationProxy | ${PORT_OFFSET}+5596 | ${PORT_OFFSET}+6596 | 597:601:main_pc_code/config/startup_config.yaml |

| mainpc | ObservabilityDashboardAPI | ${PORT_OFFSET}+8001 | ${PORT_OFFSET}+9007 | 605:609:main_pc_code/config/startup_config.yaml |

| pc2 | CentralErrorBus | ${PORT_OFFSET}+7150 | ${PORT_OFFSET}+8150 | 15:20:pc2_code/config/startup_config.yaml |

| pc2 | MemoryFusionHub | ${PORT_OFFSET}+5713 | ${PORT_OFFSET}+6713 | 30:35:pc2_code/config/startup_config.yaml |

| pc2 | RealTimeAudioPipelinePC2 | ${PORT_OFFSET}+5557 | ${PORT_OFFSET}+6557 | 44:49:pc2_code/config/startup_config.yaml |

| pc2 | UnifiedObservabilityCenter | ${PORT_OFFSET}+9100 | ${PORT_OFFSET}+9110 | 214:219:pc2_code/config/startup_config.yaml |

| pc2 | SelfHealingSupervisor | ${PORT_OFFSET}+7009 | ${PORT_OFFSET}+9008 | 236:241:pc2_code/config/startup_config.yaml |

| pc2 | SpeechRelayService | ${PORT_OFFSET}+7130 | ${PORT_OFFSET}+8130 | 246:251:pc2_code/config/startup_config.yaml |

  

- **Explicit verifications**

  - SelfHealingSupervisor

    - Requires docker.sock, exposes metrics: 6:11, 21:23, 48:50:services/self_healing_supervisor/supervisor.py; 30:36:services/self_healing_supervisor/Dockerfile.optimized

    - Config refs: 136:145:main_pc_code/config/startup_config.yaml; 236:246:pc2_code/config/startup_config.yaml

  - UnifiedObservabilityCenter

    - Health endpoint: 88:96:unified_observability_center/api/rest.py

    - Dockerfile EXPOSE/HEALTHCHECK 9100/9110: 30:35:unified_observability_center/Dockerfile.optimized

    - PC2 config: 214:219:pc2_code/config/startup_config.yaml

  - RealTimeAudioPipeline

    - Ports in YAML: 196:200:main_pc_code/config/startup_config.yaml; 44:49:pc2_code/config/startup_config.yaml

    - Dockerfile EXPOSE/HEALTHCHECK 5557/6557: 34:41:real_time_audio_pipeline/Dockerfile.optimized

    - Health handler provided by BaseAgent (/health): 1198:1213:common/core/base_agent.py

  - Legacy audio chain (6550–6553/7550–7553)

    - YAML: 472:475, 480:482, 496:499, 515:518:main_pc_code/config/startup_config.yaml

  - MemoryFusionHub

    - Ports in YAML: 145:149:main_pc_code/config/startup_config.yaml; 30:35:pc2_code/config/startup_config.yaml

    - Dockerfile EXPOSE/HEALTHCHECK 5713/6713: 30:36:memory_fusion_hub/Dockerfile.optimized

  - services/* entrypoints

    - central_error_bus/error_bus.py (main): 39:40:services/central_error_bus/error_bus.py

    - cross_gpu_scheduler/app.py (main): 53:53:services/cross_gpu_scheduler/app.py

    - speech_relay/relay.py (main): 95:97:services/speech_relay/relay.py

    - obs_dashboard_api/server.py (FastAPI + metrics): 9:12,16:22:services/obs_dashboard_api/server.py

  

- **Port issue classification**

  - Within-host conflicts: None observed in a single host config with PORT_OFFSET=0 (ports unique per file)

    - Validator aligns on base-port uniqueness: 49:60:tools/validate_ports_unique.py

  - Cross-machine duplicates (allowed by design): MemoryFusionHub 5713/6713; RealTimeAudioPipeline 5557/6557; SelfHealingSupervisor 7009/9008

    - MainPC cites: 145:149, 196:200, 136:140:main_pc_code/config/startup_config.yaml

    - PC2 cites: 30:35, 44:49, 236:241:pc2_code/config/startup_config.yaml

  - PC2 declared ranges: agent 7100–7199; health 8100–8199

    - 259:264:pc2_code/config/startup_config.yaml

  - Out-of-range justified on PC2: UOC (9100/9110), MFH (5713/6713), RTAP (5557/6557), SelfHealingSupervisor (7009/9008)

    - 214:219, 30:35, 44:49, 236:241:pc2_code/config/startup_config.yaml

  

- **RTAP gating**

  - Feature flag default: RTAP_ENABLED: ${RTAP_ENABLED:-false}

    - 12:14:main_pc_code/config/startup_config.yaml

  - Legacy audio agents are required when flag is false

    - 475:491, 499:503, 518:522, 523:527:main_pc_code/config/startup_config.yaml

  
  

## §3 Machine Assignment (Design vs Actual)

  

| service | design (plan.md) | actual (YAML+code) | plan cite | actual cite |

|---------|-------------------|--------------------|-----------|-------------|

| MemoryFusionHub | both | both | 116:116:memory-bank/DOCUMENTS/plan.md | 147:152:main_pc_code/config/startup_config.yaml; 30:37:pc2_code/config/startup_config.yaml |

| ModelOpsCoordinator | main | main | 117:117:memory-bank/DOCUMENTS/plan.md | 159:167:main_pc_code/config/startup_config.yaml |

| AffectiveProcessingCenter | main | main | 118:118:memory-bank/DOCUMENTS/plan.md | 179:187:main_pc_code/config/startup_config.yaml |

| RealTimeAudioPipeline | both | both (MainPC + PC2 variant) | 119:119:memory-bank/DOCUMENTS/plan.md | 196:204:main_pc_code/config/startup_config.yaml; 44:51:pc2_code/config/startup_config.yaml |

| UnifiedObservabilityCenter | both | PC2 only (explicit); mainpc references only | 120:120:memory-bank/DOCUMENTS/plan.md | 214:221:pc2_code/config/startup_config.yaml; 626:637:main_pc_code/config/startup_config.yaml |

| SelfHealingSupervisor | both | both | 115:115:memory-bank/DOCUMENTS/plan.md | 136:145:main_pc_code/config/startup_config.yaml; 236:246:pc2_code/config/startup_config.yaml |

| ObservabilityDashboardAPI | 4090 | main | 155:155:memory-bank/DOCUMENTS/plan.md | 605:611:main_pc_code/config/startup_config.yaml; 1:25:services/obs_dashboard_api/server.py |

| CentralErrorBus | 3060 | pc2 | 156:156:memory-bank/DOCUMENTS/plan.md | 15:21:pc2_code/config/startup_config.yaml |

  

Notes:

- MainPC depends on UnifiedObservabilityCenter but lacks an explicit agent block (139:144, 150:152, 163:167:main_pc_code/config/startup_config.yaml).

- Decommissioned legacy items are commented in MainPC YAML (85:114, 214:240, 364:376:main_pc_code/config/startup_config.yaml).

---


#BASELINE_REPORT_PART2

## §4 Docker Readiness

  

- Scope: required:true services in `main_pc_code/config/startup_config.yaml` and `pc2_code/config/startup_config.yaml`.

  

- MainPC required:true (service → Dockerfile checks)

  - ModelOpsCoordinator

    - Dockerfile: 1:41:model_ops_coordinator/Dockerfile.optimized

    - USER appuser: 27:27:model_ops_coordinator/Dockerfile.optimized

    - HEALTHCHECK /health: 32:35:model_ops_coordinator/Dockerfile.optimized

    - EXPOSE 7212 8212: 36:38:model_ops_coordinator/Dockerfile.optimized

    - ENTRYPOINT tini: 39:40:model_ops_coordinator/Dockerfile.optimized

    - WORKDIR /app: 10:10:model_ops_coordinator/Dockerfile.optimized

  - MemoryFusionHub

    - Dockerfile (optimized): 1:39:memory_fusion_hub/Dockerfile.optimized

    - USER appuser: 25:25:memory_fusion_hub/Dockerfile.optimized

    - HEALTHCHECK /health 6713: 31:33:memory_fusion_hub/Dockerfile.optimized

    - EXPOSE 5713 6713: 34:35:memory_fusion_hub/Dockerfile.optimized

    - ENTRYPOINT tini: 37:38:memory_fusion_hub/Dockerfile.optimized

    - WORKDIR /app: 8:8:memory_fusion_hub/Dockerfile.optimized

    - Legacy Dockerfile exposes mismatched ports 8080/50051/5555: 66:73:memory_fusion_hub/Dockerfile

  - AffectiveProcessingCenter

    - Dockerfile: 1:41:affective_processing_center/Dockerfile.optimized

    - USER appuser: 27:27:affective_processing_center/Dockerfile.optimized

    - HEALTHCHECK /health 6560: 32:34:affective_processing_center/Dockerfile.optimized

    - EXPOSE 5560 6560: 36:37:affective_processing_center/Dockerfile.optimized

    - ENTRYPOINT tini: 39:40:affective_processing_center/Dockerfile.optimized

    - WORKDIR /app: 10:10:affective_processing_center/Dockerfile.optimized

  - RealTimeAudioPipeline

    - Dockerfile: 1:43:real_time_audio_pipeline/Dockerfile.optimized

    - USER appuser: 29:29:real_time_audio_pipeline/Dockerfile.optimized

    - HEALTHCHECK /health 6557: 34:36:real_time_audio_pipeline/Dockerfile.optimized

    - EXPOSE 5557 6557: 38:39:real_time_audio_pipeline/Dockerfile.optimized

    - ENTRYPOINT tini: 41:42:real_time_audio_pipeline/Dockerfile.optimized

    - WORKDIR /app: 12:12:real_time_audio_pipeline/Dockerfile.optimized

  - SelfHealingSupervisor

    - Dockerfile (optimized): 1:39:services/self_healing_supervisor/Dockerfile.optimized

    - USER appuser: 25:25:services/self_healing_supervisor/Dockerfile.optimized

    - HEALTHCHECK /health 9008: 30:32:services/self_healing_supervisor/Dockerfile.optimized

    - EXPOSE 7009 9008: 34:35:services/self_healing_supervisor/Dockerfile.optimized

    - ENTRYPOINT tini: 37:38:services/self_healing_supervisor/Dockerfile.optimized

    - WORKDIR /app: 8:8:services/self_healing_supervisor/Dockerfile.optimized

  - CodeGenerator

    - Dockerfile: NOT FOUND (searched `**/code_generator*/Dockerfile*`)

  - PredictiveHealthMonitor

    - Dockerfile: NOT FOUND (searched `**/predictive_health_monitor*/Dockerfile*`)

  - Executor

    - Dockerfile: NOT FOUND (searched `**/executor*/Dockerfile*`)

  - FaceRecognitionAgent (required:true)

    - Dockerfile optimized present: 2:4:main_pc_code/agents/facerecognitionagent/Dockerfile.optimized (base), check health/expose in agent image (EXPOSE/HEALTHCHECK present: 31:37:main_pc_code/agents/visionprocessingagent/Dockerfile.optimized for a similar pattern; specific FaceRecognitionAgent Dockerfile content not shown here)

  - LearningOpportunityDetector (required:true)

    - Dockerfile optimized present: 2:4:main_pc_code/agents/learningopportunitydetector/Dockerfile.optimized (base); EXPOSE/HEALTHCHECK likely present in same directory (content not retrieved in this report)

  - LearningManager (required:true)

    - Dockerfile optimized present: 2:4:main_pc_code/agents/learningmanager/Dockerfile.optimized (base); EXPOSE/HEALTHCHECK likely present (content not retrieved in this report)

  - ActiveLearningMonitor (required:true)

    - Dockerfile optimized: NOT FOUND (searched `**/activelearningmonitor*/Dockerfile*`)

  - IntentionValidatorAgent (required:true)

    - Dockerfile: NOT FOUND (searched `**/intentionvalidatoragent*/Dockerfile*`)

  - NLUAgent (required:true)

    - Dockerfile: NOT FOUND (searched `**/nluagent*/Dockerfile*`)

  - AdvancedCommandHandler (required:true)

    - Dockerfile: NOT FOUND (searched `**/advancedcommandhandler*/Dockerfile*`)

  - ChitchatAgent (required:true)

    - Dockerfile: NOT FOUND (searched `**/chitchatagent*/Dockerfile*`)

  - FeedbackHandler (required:true)

    - Dockerfile: NOT FOUND (searched `**/feedbackhandler*/Dockerfile*`)

  - Responder (required:true)

    - Dockerfile optimized present: 2:4:main_pc_code/agents/responder/Dockerfile.optimized; HEALTHCHECK/EXPOSE: 33:39:main_pc_code/agents/responder/Dockerfile.optimized; ENTRYPOINT tini: 35:35:main_pc_code/agents/responder/Dockerfile.optimized

  - DynamicIdentityAgent (required:true)

    - Dockerfile optimized present: 2:4:main_pc_code/agents/dynamicidentityagent/Dockerfile.optimized

  - EmotionSynthesisAgent (required:true)

    - Dockerfile optimized present: 2:4:main_pc_code/agents/emotionsynthesisagent/Dockerfile.optimized; HEALTHCHECK/EXPOSE present: 31:37:main_pc_code/agents/emotionsynthesisagent/Dockerfile.optimized

  - STTService (required:true)

    - Dockerfile optimized present: 31:39:main_pc_code/agents/sttservice/Dockerfile.optimized

  - TTSService (required:true)

    - Dockerfile optimized present: 31:39:main_pc_code/agents/ttsservice/Dockerfile.optimized

  - StreamingTTSAgent (required:true)

    - Dockerfile optimized present: 31:39:main_pc_code/agents/streamingttsagent/Dockerfile.optimized

  - CrossMachineGPUScheduler (required:true)

    - Dockerfile: NOT FOUND under `services/cross_gpu_scheduler` (listing shows no Dockerfile: 1:6:services/cross_gpu_scheduler)

  - StreamingTranslationProxy (required:true)

    - Dockerfile: NOT FOUND under `services/streaming_translation_proxy` (listing shows only proxy.py/requirements.txt: 1:2:services/streaming_translation_proxy)

  - ObservabilityDashboardAPI (required:true)

    - Dockerfile: NOT FOUND under `services/obs_dashboard_api` (listing shows only server.py/requirements.txt: 1:2:services/obs_dashboard_api)

  

- PC2 required:true (service → Dockerfile checks)

  - UnifiedObservabilityCenter

    - PC2 Dockerfile optimized: 1:5:pc2_code/services/unifiedobservabilitycenter/Dockerfile.optimized (base)

    - UOC main repo Dockerfile has HEALTHCHECK/EXPOSE/USER/ENTRYPOINT: 25:38:unified_observability_center/Dockerfile.optimized

  - CentralErrorBus

    - Dockerfile optimized: 1:39:services/central_error_bus/Dockerfile.optimized (USER/HEALTHCHECK/EXPOSE/ENTRYPOINT present)

  - RealTimeAudioPipelinePC2

    - Dockerfile optimized: 1:5:pc2_code/services/realtimeaudiopipeline/Dockerfile.optimized; mirrors RTAP settings (base image cu121) 2:4:pc2_code/services/realtimeaudiopipeline/Dockerfile.optimized

  - SelfHealingSupervisor

    - Dockerfile optimized: 1:39:services/self_healing_supervisor/Dockerfile.optimized

  - SpeechRelayService

    - Dockerfile optimized present: 31:37:main_pc_code/agents/speechrelayservice/Dockerfile.optimized (agent path; PC2 service uses services/speech_relay which has no Dockerfile listing: 1:??:services/speech_relay)

  

Missing/misaligned Dockerfiles summary:

- Missing under service paths:

  - services/cross_gpu_scheduler/Dockerfile* (NOT FOUND) — 1:6:services/cross_gpu_scheduler

  - services/streaming_translation_proxy/Dockerfile* (NOT FOUND) — 1:2:services/streaming_translation_proxy

  - services/obs_dashboard_api/Dockerfile* (NOT FOUND) — 1:2:services/obs_dashboard_api

  - services/speech_relay/Dockerfile* (NOT FOUND) — 1:??:services/speech_relay

- Legacy MFH Dockerfile exposes ports not aligned to config (8080/50051/5555): 66:73:memory_fusion_hub/Dockerfile

  
  

## §5 RTAP Gating & Feature Flags

  

- Default and gating expressions

  - Default: RTAP_ENABLED: ${RTAP_ENABLED:-false} — 12:14:main_pc_code/config/startup_config.yaml

  - Legacy agents required when `${RTAP_ENABLED:-false} == 'false'` — 475:491, 499:503, 518:522, 523:527:main_pc_code/config/startup_config.yaml

  - Evaluator for expressions: NOT FOUND (no templating interpreter located; gating logic evaluation UNVERIFIABLE). Fall back to literal YAML expressions for intent.

  

- Gating matrix (by intent expressed in YAML)

  - When RTAP_ENABLED=true → conditions `${RTAP_ENABLED:-false} == 'false'` evaluate to false; legacy agents disabled (intent):

    - AudioCapture (471:478), FusedAudioPreprocessor (479:485), StreamingInterruptHandler (486:494), StreamingSpeechRecognition (495:503), WakeWordDetector (515:522), StreamingLanguageAnalyzer (523:531): main_pc_code/config/startup_config.yaml

  - When RTAP_ENABLED=false → conditions evaluate to true; legacy agents enabled (intent): lines above.

  - RTAP itself is required:true — 198:200:main_pc_code/config/startup_config.yaml

  

- Plan comparison (RTAP columns)

  - Plan lists RealTimeAudioPipeline as both machines — 119:120:memory-bank/DOCUMENTS/plan.md

  - Plan does not enumerate legacy audio sub-agents as standalone; consolidation implied by RTAP hub definition (no explicit table rows for them; UNVERIFIABLE exact deprecation).

  
  

## §6 Dependencies & Hidden Couplings

  

- Deprecated components still referenced (file:line):

  - RequestCoordinator usage in VRAMOptimizerAgent

    - 213:231, 223:237, 300:302, 788:793, 795:806, 831:838, 1427:1431, 1478:1481:main_pc_code/agents/vram_optimizer_agent.py

    - 224:244, 233:240, 311:313, 800:805, 807:818, 843:849, 1428:1432, 1469:1472:main_pc_code/agents/vram_optimizer_agent_day4_optimized.py

  - ModelManagerSuite class present (legacy)

    - 297:311, 339:341, 352:383, 940:942, 960:962, 989:996, 1092:1094, 1546:1553, 1602:1611:model_manager_suite.py

  - RequestCoordinator agent class exists

    - 157:165, 209:213, 803:809:main_pc_code/agents/request_coordinator.py

  - Scripts referencing MemoryClient legacy

    - 82:83:main_pc_code/scripts/start_agents_new.py; 51:56:main_pc_code/scripts/health_check_client.py

  

- ModelOpsCoordinator replacement API (file:line):

  - model_ops_coordinator/model_ops_pb2_grpc.py

    - Infer: 39:43

    - LoadModel: 44:48

    - UnloadModel: 49:53

    - ListModels: 54:58

    - AcquireGpuLease: 59:63

    - ReleaseGpuLease: 64:68

  
  

## §7 Security & CI

  

- SelfHealingSupervisor docker.sock usage and security posture

  - Requires RW docker.sock per source header: 6:7:services/self_healing_supervisor/supervisor.py

  - Connects to unix socket: 21:22:services/self_healing_supervisor/supervisor.py

  - MainPC config includes docker_sock path: 142:144:main_pc_code/config/startup_config.yaml

  - PC2 config includes docker_sock path: 243:245:pc2_code/config/startup_config.yaml

  - Non-root USER in Dockerfile: 25:25:services/self_healing_supervisor/Dockerfile.optimized

  - ENTRYPOINT tini present: 37:38:services/self_healing_supervisor/Dockerfile.optimized

  - No seccomp/apparmor/user-namespaces options are specified in Dockerfiles or YAML configs (no occurrences found; UNVERIFIABLE from repo alone)

  - Example run scripts mount docker.sock read-only: 84:88:FIX_MAINPC_DEPLOYMENT.sh; 82:86:deploy_native_linux.sh; 71:75:WSL2_FIX_DEPLOYMENT.sh

  

- CI checks presence

  - Port uniqueness validator in CI: 16:20:.github/workflows/quality-gates.yml

  - Additional port linter workflow: 70:86:.github/workflows/config-validation.yml

  - Trivy scan workflow: 27:35:.github/workflows/security-scan.yml

  - SBOM generation in container-images workflow: 122:149:.github/workflows/container-images.yml

  - No dedicated sbom.yml or port_lint.yml standalone files found (listing shows workflows present above; file names differ): 1:4:.github/workflows (files list)

  

- CUDA base images and NVIDIA driver baseline

  - GPU images use CUDA 12.1 family tags (cu121): e.g., 2:4:real_time_audio_pipeline/Dockerfile.optimized; 2:4:affective_processing_center/Dockerfile.optimized; 2:4:model_ops_coordinator/Dockerfile.optimized

  - Plan requires CUDA 12.1 and indicates driver ≥ 535 on PC2: 39:41, 179:181:memory-bank/DOCUMENTS/plan.md

  - Machine driver version verification is environment-dependent (TO-VERIFY in runtime; not present in repo).



---

#FINAL_REPORT

## 1) FINAL EXECUTIVE SUMMARY (non-technical)

  

- Consolidation gaps remain: legacy emotion and audio sub-agents still launch alongside hubs (APC/RTAP) per YAML required flags (548:588; 471:531:main_pc_code/config/startup_config.yaml).

- Observability drift: MainPC references UOC but does not define an agent block; PC2 runs UOC (626:637:main_pc_code/config/startup_config.yaml; 214:221:pc2_code/config/startup_config.yaml).

- Ports: ${PORT_OFFSET} appears widely with no repo-wide default env; baseline uses 0 (62:608:main_pc_code/config/startup_config.yaml; 18:265:pc2_code/config/startup_config.yaml; 65:69:batch_containerize_foundation.sh).

- Within-host port conflicts not observed in configs; cross-machine duplicates are by design (145:149; 196:200:main_pc_code/config/startup_config.yaml; 30:35; 44:49:pc2_code/config/startup_config.yaml; 49:60:tools/validate_ports_unique.py).

- Docker readiness: Hubs have compliant Dockerfiles; several required services under services/* lack Dockerfiles (1:39:real_time_audio_pipeline/Dockerfile.optimized; 1:39:memory_fusion_hub/Dockerfile.optimized; 1:39:services/self_healing_supervisor/Dockerfile.optimized vs NOT FOUND in services/cross_gpu_scheduler, services/streaming_translation_proxy, services/speech_relay).

- Security: SelfHealingSupervisor requires docker.sock; code implies RW use; some scripts mount RO (6:7; 21:22:services/self_healing_supervisor/supervisor.py; 84:88:FIX_MAINPC_DEPLOYMENT.sh).

- CI: Port uniqueness and dependency validators present; Trivy and SBOM in workflows; no standalone port_lint.yml/sbom.yml files (16:20:.github/workflows/quality-gates.yml; 27:35:.github/workflows/security-scan.yml; 122:149:.github/workflows/container-images.yml).

- Timeline impact: Missing Dockerfiles and gating logic ambiguity are immediate blockers for containerized rollout (1:6:services/cross_gpu_scheduler; 1:2:services/streaming_translation_proxy; 1:4:.github/workflows).

  
  

## 2) FINAL TECHNICAL SUMMARY (engineer-focused)

  

### Inventory & Consolidation

- Emotion sub-agents still required:true: MoodTracker/HumanAwareness/Tone/VoiceProfile/Empathy (548:588:main_pc_code/config/startup_config.yaml).

- Legacy audio chain gated by RTAP flag expression (471:531:main_pc_code/config/startup_config.yaml).

- UOC referenced in groups/deps on MainPC but no agent block; PC2 defines UOC agent (626:637:main_pc_code/config/startup_config.yaml; 214:221:pc2_code/config/startup_config.yaml).

  

### Ports

- PORT_OFFSET macros used; no repo-wide env default found; baseline uses 0 (62:608:main_pc_code/config/startup_config.yaml; 18:265:pc2_code/config/startup_config.yaml; 1:0:.env* none; 65:69:batch_containerize_foundation.sh).

- Validator scans for per-file uniqueness; no within-host duplicates detected (49:60:tools/validate_ports_unique.py).

- PC2 port ranges declared 7100–7199 (svc) and 8100–8199 (health) (259:264:pc2_code/config/startup_config.yaml). Exceptions: UOC/MFH/RTAP/SHS (214:219; 30:35; 44:49; 236:241:pc2_code/config/startup_config.yaml).

  

### Machine Assignment

- Hubs on MainPC: MFH/MOC/APC/RTAP present (145:171; 179:187; 196:204:main_pc_code/config/startup_config.yaml).

- UOC only on PC2 explicitly (214:221:pc2_code/config/startup_config.yaml); MainPC lacks agent block (626:637:main_pc_code/config/startup_config.yaml).

  

### Docker

- ModelOpsCoordinator Dockerfile: USER/HEALTHCHECK/EXPOSE/tini present (27:40:model_ops_coordinator/Dockerfile.optimized).

- MemoryFusionHub Dockerfile optimized OK; legacy Dockerfile exposes 8080/50051/5555 (30:38:memory_fusion_hub/Dockerfile.optimized; 66:73:memory_fusion_hub/Dockerfile).

- RTAP Dockerfile optimized OK (29:42:real_time_audio_pipeline/Dockerfile.optimized).

- SelfHealingSupervisor Dockerfile optimized OK (25:38:services/self_healing_supervisor/Dockerfile.optimized).

- Missing Dockerfiles under services/*: cross_gpu_scheduler, streaming_translation_proxy, speech_relay (1:6:services/cross_gpu_scheduler; 1:2:services/streaming_translation_proxy; 1:5:services/speech_relay).

  

### RTAP / Flags

- Default RTAP_ENABLED false (12:14:main_pc_code/config/startup_config.yaml).

- Legacy audio `required: ${RTAP_ENABLED:-false} == 'false'` (475; 482; 490; 499; 518; 527:main_pc_code/config/startup_config.yaml).

- No evaluator implementation found; treat expressions as intent (UNVERIFIABLE interpreter) (1:0:repo-wide search context via absence in tools/ scripts).

  

### Dependencies & Hidden Couplings

- RequestCoordinator still referenced in VRAMOptimizerAgent variants (213:231; 788:806; 1427:1431; 1478:1481:main_pc_code/agents/vram_optimizer_agent.py; 224:244; 800:818; 1428:1432; 1469:1472:main_pc_code/agents/vram_optimizer_agent_day4_optimized.py).

- Legacy ModelManagerSuite present (297:311; 339:341; 352:383:model_manager_suite.py).

- ModelOpsCoordinator RPCs available: Infer/ListModels/AcquireGpuLease (39:68:model_ops_coordinator/model_ops_pb2_grpc.py).

  

### Security / CI

- SelfHealingSupervisor docker.sock required; code opens socket (6:7; 21:22:services/self_healing_supervisor/supervisor.py).

- CI: port validation and dependency checks present; Trivy+SBOM workflows present (16:20:.github/workflows/quality-gates.yml; 70:86:.github/workflows/config-validation.yml; 27:35:.github/workflows/security-scan.yml; 122:149:.github/workflows/container-images.yml).

  
  

## 3) CRITICAL RISKS (ranked)

  

1. Undefined PORT_OFFSET at runtime

- Trigger: Deployment without env defining PORT_OFFSET.

- Blast radius: Ports bind literally; multi-stack collisions possible.

- Time-to-fail: Immediate on startup.

- Mitigation: Define PORT_OFFSET per machine; add port lint in CI.

- Verify:

```bash

rg -n "\$\{PORT_OFFSET\}" /workspace/main_pc_code/config/startup_config.yaml /workspace/pc2_code/config/startup_config.yaml | wc -l

python /workspace/tools/validate_ports_unique.py

```

Citations: 62:608:main_pc_code/config/startup_config.yaml; 18:265:pc2_code/config/startup_config.yaml; 49:60:tools/validate_ports_unique.py.

  

2. Missing Dockerfiles for required services

- Trigger: Build/deploy services under services/* with no Dockerfile.

- Blast radius: Container rollout blocked for those services.

- Time-to-fail: During build/deploy.

- Mitigation: Create Dockerfiles with tini/USER/HEALTHCHECK/EXPOSE.

- Verify:

```bash

ls -1 /workspace/services/cross_gpu_scheduler | cat

ls -1 /workspace/services/streaming_translation_proxy | cat

ls -1 /workspace/services/speech_relay | cat

```

Citations: 1:6:services/cross_gpu_scheduler; 1:2:services/streaming_translation_proxy; 1:5:services/speech_relay.

  

3. UOC not launched on MainPC (observability drift)

- Trigger: MainPC depends on UOC but lacks agent block.

- Blast radius: Metrics/health gaps on MainPC.

- Time-to-fail: Latent; during incident.

- Mitigation: Add UOC agent to MainPC or remove duplicative ObservabilityDashboardAPI.

- Verify:

```bash

rg -n "UnifiedObservabilityCenter" /workspace/main_pc_code/config/startup_config.yaml | cat

rg -n "name: UnifiedObservabilityCenter" /workspace/pc2_code/config/startup_config.yaml | cat

```

Citations: 626:637:main_pc_code/config/startup_config.yaml; 214:221:pc2_code/config/startup_config.yaml; 604:606:main_pc_code/config/startup_config.yaml.

  

4. RTAP dual-run ambiguity due to gating

- Trigger: RTAP_ENABLED=false enables legacy chain while RTAP required:true.

- Blast radius: Duplicate audio pipelines; resource waste.

- Time-to-fail: On audio workload.

- Mitigation: Set RTAP_ENABLED=true and auto-disable legacy agents.

- Verify:

```bash

rg -n "RTAP_ENABLED" /workspace/main_pc_code/config/startup_config.yaml | cat

rg -n "required: \$\{RTAP_ENABLED:-false\} == 'false'" /workspace/main_pc_code/config/startup_config.yaml | cat

```

Citations: 12:14; 475; 482; 490; 499; 518; 527:main_pc_code/config/startup_config.yaml.

  

5. SelfHealingSupervisor docker.sock risk

- Trigger: RW docker.sock access within container.

- Blast radius: Daemon control; elevated compromise risk.

- Time-to-fail: Upon exploit.

- Mitigation: Run with RO socket; add seccomp/apparmor; least privileges.

- Verify:

```bash

rg -n "docker.sock" /workspace/services/self_healing_supervisor/supervisor.py | cat

```

Citations: 6:7; 21:22:services/self_healing_supervisor/supervisor.py; 142:144:main_pc_code/config/startup_config.yaml.

  
  

## 4) STEP-BY-STEP EXECUTION PLAN

  

| Phase | Description | ETA | Owner Role | Dependencies | Risks if Delayed | Artifacts (PRs/scripts/paths) |

|------|-------------|-----|------------|--------------|------------------|-------------------------------|

| P0 | Define PORT_OFFSET per machine; add port lint CI | 0.5d | DevOps | — | Bind failures | .github/workflows/port_lint.yml; tools/validate_ports_unique.py (49:60:tools/validate_ports_unique.py) |

| P0 | Add UOC on MainPC or remove ObservabilityDashboardAPI | 0.5d | Platform Eng | — | Observability gaps | main_pc_code/config/startup_config.yaml (626:637; 604:606); unified_observability_center/app.py |

| P0 | Fix RTAP gating: enable RTAP and disable legacy chain | 0.5d | Audio Lead | — | Dual pipeline | main_pc_code/config/startup_config.yaml (12:14; 471:531) |

| P1 | Create Dockerfiles for missing services | 1.0d | Platform Eng | P0 | Blocked rollout | services/cross_gpu_scheduler/Dockerfile; services/streaming_translation_proxy/Dockerfile; services/speech_relay/Dockerfile |

| P1 | Generate SBOM workflow; optional trivy_scan.yml | 0.5d | DevX | P0 | Compliance | .github/workflows/sbom.yml; .github/workflows/security-scan.yml (27:35) |

| P1 | Build-lock digests for reproducibility | 0.5d | DevX | P1 | Drift | build-lock.json; container-images.yml (46:54) |

| P2 | Replace RequestCoordinator calls with ModelOps RPCs + tests | 1.5d | App Eng | P0 | Legacy failures | main_pc_code/agents/vram_optimizer_agent*.py (citations above); model_ops_coordinator/model_ops_pb2_grpc.py (39:68) |

| P2 | SelfHealingSupervisor hardening (RO socket + seccomp) | 0.5d | SecOps | P0 | Privilege risk | services/self_healing_supervisor/Dockerfile; profiles/seccomp.json; scripts (84:88:FIX_MAINPC_DEPLOYMENT.sh) |

| P2 | Driver verify/upgrade note for PC2 (>= 535) | 0.25d | Infra | P1 | GPU runtime | memory-bank/DOCUMENTS/plan.md (39:41; 179:181) |

  
  

## 5) MACHINE-READABLE HANDOFF (handoff.json)

  

```json

{

  "findings": [

    {

      "type": "consolidation_gap",

      "details": "Emotion and legacy audio sub-agents still required alongside hubs",

      "evidence": [

        "main_pc_code/config/startup_config.yaml:548-588",

        "main_pc_code/config/startup_config.yaml:471-531"

      ]

    },

    {

      "type": "observability_drift",

      "details": "UOC defined only on PC2; MainPC references but no agent block",

      "evidence": [

        "main_pc_code/config/startup_config.yaml:626-637",

        "pc2_code/config/startup_config.yaml:214-221"

      ]

    },

    {

      "type": "ports_config",

      "details": "PORT_OFFSET macros used; default undefined in env; use 0",

      "evidence": [

        "main_pc_code/config/startup_config.yaml:62-608",

        "pc2_code/config/startup_config.yaml:18-265",

        "batch_containerize_foundation.sh:65-69"

      ]

    },

    {

      "type": "docker_gap",

      "details": "Missing Dockerfiles under services/*",

      "evidence": [

        "services/cross_gpu_scheduler (no Dockerfile):1-6",

        "services/streaming_translation_proxy (no Dockerfile):1-2",

        "services/speech_relay (no Dockerfile):1-5"

      ]

    },

    {

      "type": "deprecated_dependency",

      "details": "RequestCoordinator referenced in VRAMOptimizerAgent variants",

      "evidence": [

        "main_pc_code/agents/vram_optimizer_agent.py:213-231,788-806,1427-1431,1478-1481",

        "main_pc_code/agents/vram_optimizer_agent_day4_optimized.py:224-244,800-818,1428-1432,1469-1472"

      ]

    }

  ],

  "ports": {

    "computed": {

      "mainpc_required": {

        "ModelOpsCoordinator": {"service": 7212, "health": 8212, "source": "main_pc_code/config/startup_config.yaml:159-163"},

        "MemoryFusionHub": {"service": 5713, "health": 6713, "source": "main_pc_code/config/startup_config.yaml:145-149"},

        "AffectiveProcessingCenter": {"service": 5560, "health": 6560, "source": "main_pc_code/config/startup_config.yaml:179-183"},

        "RealTimeAudioPipeline": {"service": 5557, "health": 6557, "source": "main_pc_code/config/startup_config.yaml:196-200"},

        "SelfHealingSupervisor": {"service": 7009, "health": 9008, "source": "main_pc_code/config/startup_config.yaml:136-140"}

      },

      "pc2_required": {

        "CentralErrorBus": {"service": 7150, "health": 8150, "source": "pc2_code/config/startup_config.yaml:15-20"},

        "MemoryFusionHub": {"service": 5713, "health": 6713, "source": "pc2_code/config/startup_config.yaml:30-35"},

        "RealTimeAudioPipelinePC2": {"service": 5557, "health": 6557, "source": "pc2_code/config/startup_config.yaml:44-49"},

        "UnifiedObservabilityCenter": {"service": 9100, "health": 9110, "source": "pc2_code/config/startup_config.yaml:214-219"},

        "SelfHealingSupervisor": {"service": 7009, "health": 9008, "source": "pc2_code/config/startup_config.yaml:236-241"},

        "SpeechRelayService": {"service": 7130, "health": 8130, "source": "pc2_code/config/startup_config.yaml:246-251"}

      }

    },

    "conflicts": [],

    "notes": [

      "PORT_OFFSET default=0 unless defined at batch_containerize_foundation.sh:65-69",

      "PC2 declared ranges 7100–7199 / 8100–8199 at pc2_code/config/startup_config.yaml:259-264",

      "Cross-machine duplicates allowed by design"

    ]

  },

  "actions": [

    {

      "phase": "P0",

      "description": "Define PORT_OFFSET per machine; add port lint CI",

      "owner_role": "DevOps",

      "eta_days": 0.5,

      "dependencies": [],

      "artifacts": [".github/workflows/port_lint.yml", "tools/validate_ports_unique.py"],

      "commands": [

        "python /workspace/tools/validate_ports_unique.py"

      ],

      "risk_if_delayed": "Bind failures across stacks"

    },

    {

      "phase": "P0",

      "description": "Add UOC agent on MainPC or remove ObservabilityDashboardAPI",

      "owner_role": "Platform Eng",

      "eta_days": 0.5,

      "dependencies": [],

      "artifacts": ["/workspace/main_pc_code/config/startup_config.yaml"],

      "commands": [

        "rg -n 'UnifiedObservabilityCenter' /workspace/main_pc_code/config/startup_config.yaml | cat"

      ],

      "risk_if_delayed": "Observability gaps on MainPC"

    },

    {

      "phase": "P0",

      "description": "Enable RTAP; disable legacy audio chain",

      "owner_role": "Audio Lead",

      "eta_days": 0.5,

      "dependencies": [],

      "artifacts": ["/workspace/main_pc_code/config/startup_config.yaml"],

      "commands": [

        "rg -n ""required: \$\{RTAP_ENABLED:-false\} == 'false'"" /workspace/main_pc_code/config/startup_config.yaml | cat"

      ],

      "risk_if_delayed": "Dual audio pipelines"

    },

    {

      "phase": "P1",

      "description": "Create Dockerfiles for missing services",

      "owner_role": "Platform Eng",

      "eta_days": 1.0,

      "dependencies": ["P0"],

      "artifacts": [

        "services/cross_gpu_scheduler/Dockerfile",

        "services/streaming_translation_proxy/Dockerfile",

        "services/speech_relay/Dockerfile"

      ],

      "commands": [

        "ls -1 /workspace/services/cross_gpu_scheduler | cat",

        "ls -1 /workspace/services/streaming_translation_proxy | cat",

        "ls -1 /workspace/services/speech_relay | cat"

      ],

      "risk_if_delayed": "Container rollout blocked"

    }

  ],

  "success_criteria": {

    "must_have": [

      "No within-host port conflicts (tools/validate_ports_unique.py passes)",

      "UOC deployed on MainPC or ObservabilityDashboardAPI removed",

      "Legacy audio chain disabled when RTAP is enabled",

      "Missing service Dockerfiles implemented with USER/tini/EXPOSE/HEALTHCHECK"

    ],

    "should_have": [

      "SBOM workflow added and artifacts published",

      "SelfHealingSupervisor hardened (RO socket + seccomp profile)",

      "ModelOpsCoordinator RPCs replace legacy RequestCoordinator code paths"

    ],

    "nice_to_have": [

      "build-lock.json committed",

      "Driver verification for PC2 (>= 535) documented"

    ]

  }

}

```


---

#RECONCILIATION_MATRIX_DRAFT

Claim,Source Report(s) A/B/C,Your Verdict {Verified|Refuted|Unverifiable},Proof (path:lines)

"Missing Dockerfiles for cross_gpu_scheduler, streaming_translation_proxy, speech_relay","A,B","Verified","services/cross_gpu_scheduler (no Dockerfile): 1:6:services/cross_gpu_scheduler | services/streaming_translation_proxy (no Dockerfile): 1:2:services/streaming_translation_proxy | services/speech_relay (no Dockerfile): 93:97:services/speech_relay/relay.py (no Dockerfile listed)"

"SelfHealingSupervisor requires docker.sock (RW) and restarts","A,B,C","Verified","services/self_healing_supervisor/supervisor.py:6-7,21-23 | main_pc_code/config/startup_config.yaml:142-144 | pc2_code/config/startup_config.yaml:243-245"

"PORT_OFFSET undefined in runtime configs (use 0)","A,B,C","Verified",".env*: 1:0:(none) | .ini: 1:0:(none) | .github/workflows (no PORT_OFFSET): 1:4:.github/workflows | batch_containerize_foundation.sh sets PORT_OFFSET=0: 65-69:batch_containerize_foundation.sh"

"Legacy MFH Dockerfile exposes 8080/50051/5555 not aligned with 5713/6713","A","Verified","memory_fusion_hub/Dockerfile:66-73 | memory_fusion_hub/Dockerfile.optimized:30-36"

"UOC missing on MainPC; PC2 defines UOC","A,B","Verified","main_pc_code/config/startup_config.yaml:626-637 (group refs only) | pc2_code/config/startup_config.yaml:214-221"

"RTAP_ENABLED default false; legacy audio agents required when false","A,B,C","Verified","main_pc_code/config/startup_config.yaml:12-14,475,482,490,499,518,527"

"Deprecated RequestCoordinator still referenced in VRAMOptimizerAgent","A,B","Verified","main_pc_code/agents/vram_optimizer_agent.py:213-231,788-806,1427-1431,1478-1481 | main_pc_code/agents/vram_optimizer_agent_day4_optimized.py:224-244,800-818,1428-1432,1469-1472"

"ModelOpsCoordinator replacement API available (Infer/ListModels/AcquireGpuLease)","A","Verified","model_ops_coordinator/model_ops_pb2_grpc.py:39-68"

"CI lacks dedicated port_lint.yml and sbom.yml but has equivalent checks","B","Verified",".github/workflows/quality-gates.yml:16-20 | .github/workflows/config-validation.yml:70-86 | .github/workflows/container-images.yml:122-149"

"GPU base requires NVIDIA driver >=535 on PC2","B,C","Verified","memory-bank/DOCUMENTS/plan.md:39-41,179-181 (design); runtime verification TO-VERIFY"
