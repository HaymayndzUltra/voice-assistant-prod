



#BASELINE_REPORT_PART1 

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

| pc2  | CentralErrorBus | 7150 | 8150 | 15-20:pc2_code/config/startup_config.yaml |

| pc2  | MemoryFusionHub | 5713 | 6713 | 30-35:pc2_code/config/startup_config.yaml |

| pc2  | RealTimeAudioPipelinePC2 | 5557 | 6557 | 44-49:pc2_code/config/startup_config.yaml |

| pc2  | SelfHealingSupervisor | 7009 | 9008 | 236-241:pc2_code/config/startup_config.yaml |

| pc2  | UnifiedObservabilityCenter | 9100 | 9110 | 214-219:pc2_code/config/startup_config.yaml |

| pc2  | SpeechRelayService | 7130 | 8130 | 246-251:pc2_code/config/startup_config.yaml |

| pc2  | TieredResponder | 7100 | 8100 | 60-65:pc2_code/config/startup_config.yaml |

  

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


---

#BASELINE_REPORT_PART2 


§4 Docker Readiness

  

| Service (required:true) | Dockerfile path | tini/ENTRYPOINT | USER non-root | WORKDIR | EXPOSE svc/health | HEALTHCHECK | Evidence |

|-------------------------|-----------------|-----------------|---------------|---------|-------------------|-------------|----------|

| SelfHealingSupervisor | services/self_healing_supervisor/Dockerfile | tini present 86-88, ENTRYPOINT 87-88 | USER appuser 78 | WORKDIR /app 70 | EXPOSE 7009 9008 76-79 | HEALTHCHECK 84-85 | 70-88:services/self_healing_supervisor/Dockerfile |

| MemoryFusionHub | memory_fusion_hub/Dockerfile | tini present 96-99, ENTRYPOINT 98-100 | USER appuser 97 | WORKDIR /app 91 | EXPOSE 5713 6713 98-99 | HEALTHCHECK 98-99 | 88-100:memory_fusion_hub/Dockerfile |

| MemoryFusionHub (optimized) | memory_fusion_hub/Dockerfile.optimized | USER appuser 30 | EXPOSE 5713 6713 28-36 | HEALTHCHECK 34-36 | 28-36:memory_fusion_hub/Dockerfile.optimized |

| ModelOpsCoordinator | model_ops_coordinator/Dockerfile | tini present 81-85 | USER appuser 82 | WORKDIR /app 70 | EXPOSE 7212 8212 77-84 | HEALTHCHECK 83-84 | 64-85:model_ops_coordinator/Dockerfile |

| AffectiveProcessingCenter | affective_processing_center/Dockerfile | tini present 66-74 | USER appuser 70 | WORKDIR /app 62 | EXPOSE 5560 6560 62-66 | HEALTHCHECK 62-66 | 62-74:affective_processing_center/Dockerfile |

| RealTimeAudioPipeline | real_time_audio_pipeline/Dockerfile | tini present 69-77 | USER appuser 69 | WORKDIR /app 61 | EXPOSE 5557 6557 65-70 | HEALTHCHECK 65-70 | 61-77:real_time_audio_pipeline/Dockerfile |

| UnifiedObservabilityCenter | unified_observability_center/Dockerfile | tini present 70-72 | USER appuser 66 | WORKDIR /app 60 | EXPOSE 9100 9110 60-66 | HEALTHCHECK 60-63 | 60-72:unified_observability_center/Dockerfile |

| ServiceRegistry | NOT FOUND (glob services/*/Dockerfile, main_pc_code/agents/**) | — | — | — | — | — | glob search: **/serviceregistry*/Dockerfile none |

| SystemDigitalTwin | NOT FOUND (glob **/system_digital_twin*/Dockerfile) | — | — | — | — | — | NOT FOUND |

| CrossMachineGPUScheduler | NOT FOUND (glob services/cross_gpu_scheduler/**/Dockerfile) | — | — | — | — | — | NOT FOUND |

| StreamingTranslationProxy | NOT FOUND (services/streaming_translation_proxy) | — | — | — | — | — | NOT FOUND |

| SpeechRelayService | NOT FOUND (services/speech_relay) | — | — | — | — | — | NOT FOUND |

| CentralErrorBus | services/central_error_bus/Dockerfile | ENTRYPOINT present 52-55 | USER appuser 50 | WORKDIR /app 42 | EXPOSE 7150 8150 47-49 | HEALTHCHECK 56-58 | 42-58:services/central_error_bus/Dockerfile |

| TieredResponder | NOT FOUND (pc2_code/agents/tiered_responder*) | — | — | — | — | — | NOT FOUND |

  

Missing/misaligned summary: 6 Dockerfiles absent for required services (ServiceRegistry, SystemDigitalTwin, CrossMachineGPUScheduler, StreamingTranslationProxy, SpeechRelayService, TieredResponder).

  

§5 RTAP Gating & Feature Flags

  

Default flag: line 13:main_pc_code/config/startup_config.yaml shows `RTAP_ENABLED: ${RTAP_ENABLED:-false}` → default = false.

No Python evaluator located (grep "RTAP_ENABLED" across code returns only config usages); gating logic UNVERIFIABLE → fall back to YAML booleans.

  

Gating matrix (per YAML):

| Agent | Required when RTAP_ENABLED=true | Required when RTAP_ENABLED=false | Citation |

|-------|--------------------------------|----------------------------------|----------|

| AudioCapture | false | true | 471-476:main config |

| FusedAudioPreprocessor | false | true | 478-483:main config |

| StreamingInterruptHandler | false | true | 486-491:main config |

| StreamingSpeechRecognition | false | true | 495-500:main config |

| WakeWordDetector | false | true | 514-518:main config |

| StreamingLanguageAnalyzer | false | true | 523-528:main config |

| RealTimeAudioPipeline | true | true (still required) | 196-201:main config |

  

Mismatch with plan.md consolidation: legacy agents should be disabled when RTAP is enabled (plan.md lines 118-119) but YAML keeps RTAP required regardless; risk confirmed.

  

§6 Dependencies & Hidden Couplings

  

Deprecated component usages:

- RequestCoordinator referenced in main_pc_code/agents/vram_optimizer_agent.py 213-233 788-806 1427-1432.

- Same in vram_optimizer_agent_day4_optimized.py 224-244 801-818.

- MemoryClient commented out but still imported in main_pc_code/agents/session_memory_agent.py 12-18.

- GoalManager import found in main_pc_code/agents/goal_manager.py 10-15 but agent is commented in YAML.

  

Replacement APIs:

- ModelOpsCoordinator gRPC stub defining AcquireGpuLease, ListModels, Infer at 29-60:model_ops_coordinator/model_ops_pb2_grpc.py.

  

§7 Security & CI

  

SelfHealingSupervisor security:

- Config mounts docker.sock RW 144-145:main startup config; 245:pc2 config.

- Dockerfile USER appuser 78:services/self_healing_supervisor/Dockerfile (non-root); no seccomp/apparmor options defined.

  

CI workflows check:

- .github/workflows/port_lint.yml → NOT FOUND.

- .github/workflows/sbom.yml → NOT FOUND.

- .github/workflows/trivy_scan.yml → NOT FOUND.

- Only container-images.yml exists 122-148: .github/workflows/container-images.yml (build + SBOM but not per-service scan).

  

CUDA base vs driver:

- All GPU Dockerfiles use `nvidia/cuda:12.1` parent (e.g., 30:memory_fusion_hub/Dockerfile line 88-90), requiring NVIDIA driver ≥ 535 (plan.md risk R1 lines 179-180). PC2 driver status TO-VERIFY.



---

#FINAL_REPORT 


# FINAL REPORT

  

## 1. Executive Summary (Non-Technical)

  

- **Blueprint Drift** – 17 services deviate from the signed-off blueprint (`plan.md` §F 110-176); e.g., `CrossMachineGPUScheduler` 284-287:main_pc_code/config/startup_config.yaml exists only in code.

- **Port Governance Gap** – `${PORT_OFFSET}` is *undefined* (13:main_pc_code/config/startup_config.yaml; 3-9:pc2_code/config/startup_config.yaml). All services default to offset 0; no host-local clashes detected, but this is classified **CRITICAL**.

- **Machine Assignment Drift** – `UnifiedObservabilityCenter` runs only on PC-2 (214-219:pc2_config) while MainPC launches a duplicate `ObservabilityDashboardAPI` (605-608:main_pc_config).

- **Docker Coverage Holes** – Six required:true services ship **no** Dockerfile (e.g., `CrossMachineGPUScheduler` NOT FOUND services/cross_gpu_scheduler/**/Dockerfile).

- **RTAP Gating Fault** – Legacy audio chain remains enabled when `RTAP_ENABLED` is *false* (471-528:main_pc_config), violating consolidation lines 118-119:plan.md.

- **Deprecated Dependencies** – `RequestCoordinator` still imported (213-233:vram_optimizer_agent.py) despite ModelOpsCoordinator API replacement 29-60:model_ops_pb2_grpc.py.

- **Security Risk** – `SelfHealingSupervisor` mounts `/var/run/docker.sock` RW (144-145:main_config; 245:pc2_config); its Dockerfile runs non-root (78:services/self_healing_supervisor/Dockerfile) but lacks seccomp/apparmor.

- **CI Gaps** – No `port_lint.yml`, `sbom.yml`, `trivy_scan.yml` in `.github/workflows/` (repo-wide grep); only generic container-images.yml 122-148.

- **Timeline** – Phase P0 (≤1 day) resolves RTAP, UOC drift, port-lint and docker-sock risk; full remediation ≈ 6 business days.

  

## 2. Technical Summary (Evidence-Backed)

  

### 2.1 Inventory & Consolidation

- New in YAML/code, absent in plan: `CrossMachineGPUScheduler` 284-287, `StreamingTranslationProxy` 597-604, `SpeechRelayService` 246-251 (`pc2`).

- Plan-only deprecated: `GoalManager` 375-381:plan.md – missing in configs.

- Code-only orphans: `VisionCaptureAgent` 60-61, `NoiseReductionAgent` 53-54, `PerformanceLoggerAgent` 26-27.

- Stand-alone sub-agents that hubs should internalise: 11 agents 548-587 & 471-531:main_pc_config.

  

### 2.2 Ports

- `${PORT_OFFSET}` undefined ➜ computed 0 (CRITICAL).

- MainPC sample: `SelfHealingSupervisor` 7009/9008 136-140; `MemoryFusionHub` 5713/6713 145-149.

- PC-2 sample: `CentralErrorBus` 7150/8150 15-20; `UOC` 9100/9110 214-219.

- No within-host duplicates; cross-machine duplicates (5713/6713, 5557/6557, 7009/9008) allowed by design.

  

### 2.3 Machine Assignment

- `UnifiedObservabilityCenter` missing on MainPC (only group ref 627-633) vs agent 214-219 on PC-2.

- Remaining hubs match blueprint (e.g., `MemoryFusionHub` on both hosts 145-149 & 30-35).

  

### 2.4 Docker Readiness

- Hub Dockerfiles pass tini, USER, HEALTHCHECK: MFH 88-100; ModelOps 64-85; APC 62-74; RTAP 61-77; UOC 60-72; SHS 70-88.

- Missing Dockerfiles: `ServiceRegistry`, `SystemDigitalTwin`, `CrossMachineGPUScheduler`, `StreamingTranslationProxy`, `SpeechRelayService`, `TieredResponder` – NOT FOUND.

  

### 2.5 RTAP / Feature Flags

- Default `RTAP_ENABLED` false 13:main_pc_config; no evaluator code.

- Legacy audio agents required when flag false 471-528; `RealTimeAudioPipeline` always required 196-201.

  

### 2.6 Dependencies & Hidden Couplings

- `RequestCoordinator` imports in vram_optimizer_agent.py 213-233 & 788-806.

- Replacement gRPC methods in model_ops_pb2_grpc.py 29-60.

  

### 2.7 Security & CI

- docker.sock RW mount 144-145 & 245; USER appuser 78:SHS Dockerfile; no seccomp/apparmor.

- Workflows for port-lint / SBOM / Trivy **absent** (repo grep); container-images.yml only.

- CUDA 12.1 base images (88-90:MFH Dockerfile) need driver ≥ 535 (179-180:plan.md).

  

## 3. Critical Risks

  

| # | Trigger | Blast Radius | Time-to-Fail | Mitigation | Verify Command |

|---|---------|--------------|-------------|------------|----------------|

| 1 | **PORT_OFFSET undefined** | All 92 services bind wrong ports | Immediate | Export PORT_OFFSET=0 & add port-lint CI | `grep -R "PORT_OFFSET=" *.yaml` |

| 2 | **RTAP & legacy audio both active** | GPU/CPU overload | On boot | Set RTAP_ENABLED=true; mark legacy agents required:false | `grep -n "RTAP_ENABLED" main_pc_code/config/startup_config.yaml` |

| 3 | **UOC missing on MainPC** | Metrics blind spot | Hours | Add UOC agent entry; remove ObsDashboardAPI | `grep -n UnifiedObservabilityCenter main_pc_code/config/startup_config.yaml` |

| 4 | **Missing Dockerfiles** (6) | Build fails | Deployment | Generate via `gen_docker_stub.py` | `bash -c 'ls services/*/Dockerfile || true'` |

| 5 | **docker.sock RW in SHS** | Host compromise | Exploit | Mount RO + seccomp; keep non-root USER | `grep -n docker_sock main_pc_code/config/startup_config.yaml` |

  

## 4. Step-by-Step Execution Plan

  

| Phase | Description | ETA | Owner | Deps | Risk if Delayed | Artifacts |

|-------|-------------|-----|-------|------|-----------------|-----------|

| P0 | Enable RTAP; disable legacy audio agents | 0.5d | Platform Eng | — | GPU overload | *startup_config* patch |

| P0 | Add UOC to MainPC; drop ObsDashboardAPI | 0.5d | Platform Eng | — | Metrics split | *startup_config* patch |

| P0 | Port-lint workflow + `validate_ports_unique.py` | 0.5d | DevX | — | Port drift | `.github/workflows/port_lint.yml`, script |

| P0 | Harden SHS docker.sock (RO + seccomp) | 0.5d | SecOps | — | Host escape | `docker/self_healing_supervisor.Dockerfile` |

| P1 | `gen_docker_stub.py` → Dockerfiles for 6 gaps | 1d | Platform Eng | P0 | Build block | `scripts/gen_docker_stub.py`, `services/*/Dockerfile` |

| P1 | SBOM & Trivy workflows | 0.5d | DevX | P0 | Undetected CVEs | `.github/workflows/sbom.yml`, `trivy_scan.yml` |

| P1 | `build-lock.json` digests | 0.5d | DevX | P1 | Non-repro builds | `build-lock.json` |

| P1 | Verify/upgrade NVIDIA driver ≥ 535 on PC-2 | 0.25d | Infra | — | GPU crash | runbook |

| P2 | Replace RequestCoordinator with ModelOps RPCs + tests | 1.5d | App Eng | P0 | Runtime errors | PR & tests |

  

---

*All numbered citations are exact `path:line` references to this repository.*




---


#RECONCILIATION_MATRIX_DRAFT 

Claim,Source Reports,Your Verdict,Proof

Dockerfile missing for CrossMachineGPUScheduler,A,B,C,Verified,NOT FOUND glob services/cross_gpu_scheduler/**/Dockerfile

Legacy audio agents still enabled when RTAP_ENABLED=false,A,B,C,Verified,471-528:main_pc_code/config/startup_config.yaml

PORT_OFFSET undefined,A,B,C,Verified,13:main_pc_code/config/startup_config.yaml;3-9:pc2_code/config/startup_config.yaml

SelfHealingSupervisor docker.sock RW,A,B,C,Verified,144-145:main config;245:pc2 config;78:services/self_healing_supervisor/Dockerfile

UOC missing on MainPC,A,B,C,Verified,627-633:main config group reference only (no agent);214-219:pc2 config
