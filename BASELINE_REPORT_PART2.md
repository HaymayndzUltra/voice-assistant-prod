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