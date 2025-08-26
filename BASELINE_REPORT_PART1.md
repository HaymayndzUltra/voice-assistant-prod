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