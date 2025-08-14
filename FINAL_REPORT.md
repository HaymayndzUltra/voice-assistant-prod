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