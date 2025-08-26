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