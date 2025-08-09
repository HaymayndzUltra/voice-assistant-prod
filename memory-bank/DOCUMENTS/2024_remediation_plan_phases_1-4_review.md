# 2024 Remediation Plan – Phases 1–4 Review and Implementation Notes

Date: 2025-08-09
Owner: Background Agent (to be merged by maintainer)

## Executive Summary
All phases (0–4) of `2024_remediation_plan` have been implemented and marked DONE. The changes restore correctness of TTS discovery, remove legacy coordinator dependencies, converge the emotion pipeline to APC framing, centralize observability to UOC, make RTAP authoritative, and add CI safeguards (contract tests and migration gates).

Key outcomes:
- Unified TTS service name (`StreamingTTSAgent`) with a constants module to prevent string drift.
- SSR no longer depends on `RequestCoordinator`; health checks and status align to `ModelOpsCoordinator` (MOC).
- Legacy emotion consumers now support APC ZMQ multipart framing and `EmotionalContext` schema.
- Observability centralized on `UnifiedObservabilityCenter` (UOC); dashboard proxies UOC `/metrics`.
- RTAP is authoritative; legacy streaming_* agents can be gated via feature flag, avoiding duplication.
- CI safeguards ensure framing/schema contracts and prevent regressions to deprecated semantics.

---

## Phase 1 – P0 Blockers (DONE)

### 1. TTS Service Name Standardization
- Created: `common/constants/service_names.py` (single source of truth for service names).
- Updated registration and logs to use the exact name `StreamingTTSAgent`:
  - `main_pc_code/agents/streaming_tts_agent.py`: registration, status updates, shutdown logs.
  - Consumers switched to constants (`ServiceNames.StreamingTTSAgent`):
    - `main_pc_code/agents/streaming_interrupt_handler.py`
    - `main_pc_code/agents/responder.py`
  - Support files:
    - `main_pc_code/utils/docker_network_utils.py`: default port map key
    - `scripts/docker_health_check.py`: health check uses `StreamingTTSAgent`

Verification:
- grep for legacy name (active code only): no remaining usages outside backups/archives.

### 2. SSR Migration to ModelOpsCoordinator
- Removed `RequestCoordinator` REQ/REP connection in `main_pc_code/agents/streaming_speech_recognition.py`.
- Added MOC liveness monitor via `core/GpuLeaseClient` using `MOC_GRPC_ADDR`.
- Configured dependencies (removed `RequestCoordinator`):
  - `config/startup_config.yaml`
  - `config/unified_startup_core.yaml`
  - `config/unified_startup_phase2.yaml`

Verification:
- SSR file has no `RequestCoordinator` references; configs no longer require it for SSR/TTS.

### 3. Emotion Pipeline Convergence (APC)
- `main_pc_code/agents/mood_tracker_agent.py` and `main_pc_code/agents/EmpathyAgent.py` now:
  - Subscribe to APC topic ("affect") and parse multipart `[topic, json]`.
  - Translate `EmotionalContext` → internal representation; fallback to legacy EmotionEngine framing if APC is unavailable.

Verification:
- Contract test added later in Phase 4; manual inspection confirms multipart handling.

---

## Phase 2 – P1 High Priority (DONE)

### 1. Rewire PC2 RemoteConnectorAgent to MOC
- `pc2_code/agents/remote_connector_agent.py`:
  - Removed ZMQ REQ/REP to legacy Model Manager (MMA) on ports 5555/5556 and SUB on 5556.
  - Introduced `GpuLeaseClient` (gRPC, `MOC_GRPC_ADDR`, default `localhost:7212`).
  - `check_model_status`: performs a lightweight lease probe for availability, caches, and releases.
  - Cleaned up shutdown/cleanup to exclude legacy sockets.

Verification:
- New CI test (Phase 4) ensures no deprecated MMA strings reappear in active code.

### 2. Centralize Observability on UOC; Retire ObservabilityHub
- Dashboard API (`services/obs_dashboard_api/server.py`):
  - Now proxies `UOC_URL/metrics` with optional `UOC_TOKEN`.
- Startup configuration:
  - `main_pc_code/config/startup_config.yaml`: commented out `ObservabilityHub`; added `UnifiedObservabilityCenter` (port `${PORT_OFFSET}+9100`).
- PredictiveHealthMonitor (`main_pc_code/agents/predictive_health_monitor.py`):
  - Now prefers UOC-provided `/metrics` (Prometheus text) when available; falls back to local metric computation.

Verification:
- Dashboard returns UOC metrics (no 502). UOC present in startup config; ObservabilityHub disabled.

---

## Phase 3 – P2 Stability & Cleanup (DONE)

### 1. RTAP Authoritative; Gate Legacy streaming_* Agents
- Feature flag `RTAP_ENABLED` added in `main_pc_code/config/startup_config.yaml`.
- Gating (when `RTAP_ENABLED=true`, the following are not started):
  - `AudioCapture`, `FusedAudioPreprocessor`, `StreamingSpeechRecognition`, `WakeWordDetector`.
- `StreamingInterruptHandler` dependency on SSR removed to avoid hard requirement under RTAP.
- RTAP configuration updates:
  - `real_time_audio_pipeline/config/default.yaml`: authoritative outputs, consistent ports (6552 events, 6553 transcripts).
  - `real_time_audio_pipeline/docker/entrypoint.sh`: exports `RTAP_AUTHORITY=true`.

### 2–4. Minor Cleanup (Contextual)
- VRAM optimizer legacy references not present in active code; tests added in Phase 4 prevent reintroduction.
- PredictiveHealthMonitor metrics path already aligned to UOC in Phase 2.

Verification:
- With `RTAP_ENABLED=true`, no legacy streaming_* agents start; no port contention.

---

## Phase 4 – Cross-Cutting Safeguards (DONE)

### 1. Contract Tests for APC → Consumers
- `tests/test_contracts_apc_multipart.py` validates ZMQ multipart `[topic, json]` framing and required `EmotionalContext` fields.

### 2. Discovery Constants Enforcement
- `tests/test_service_name_constants.py` parses active Python files and fails build when service name string literals (e.g., `StreamingTTSAgent`) are used instead of `ServiceNames`.

### 3. Migration Gates for Deprecated Components
- `tests/test_no_legacy_mma_refs.py` fails build when active code references deprecated components or legacy MMA semantics (`RequestCoordinator`, `MODEL_MANAGER_HOST`, etc.).

---

## Configuration & Environment
- Core ENV:
  - `MOC_GRPC_ADDR` (default `localhost:7212`) – MOC gRPC endpoint.
  - `RTAP_ENABLED` (`true|false`) – Gate legacy streaming_* agents when RTAP is active.
  - `UOC_URL` (default `http://localhost:9100`) – UOC metrics endpoint; `UOC_TOKEN` optional.
- Startup configs:
  - `main_pc_code/config/startup_config.yaml` – Observability/UOC, RTAP gating.
  - `config/unified_startup_core.yaml` / `config/unified_startup_phase2.yaml` – removed RequestCoordinator for SSR/TTS.

---

## Verification Checklist
- Naming: active code uses `StreamingTTSAgent` exclusively; no `StreamingTtsAgent` outside backups.
- SSR: no `RequestCoordinator` references in `streaming_speech_recognition.py`; configs updated.
- APC: consumers parse multipart; contract test passes locally/CI.
- Observability: dashboard proxies UOC metrics; hub retired in config.
- RTAP: with `RTAP_ENABLED=true`, legacy streaming_* agents do not start.
- CI: tests added under `tests/` for contracts/constants/migration gates.

---

## Deployment Notes
1) Set environment variables appropriate to deployment:
- `RTAP_ENABLED=true`
- `MOC_GRPC_ADDR=<host:port>`
- `UOC_URL=http://<uoc-host>:9100` (and `UOC_TOKEN` if needed)

2) Run targeted tests:
```bash
pytest -q tests/test_contracts_apc_multipart.py \
           tests/test_service_name_constants.py \
           tests/test_no_legacy_mma_refs.py
```

3) Sanity checks:
- Validate streaming path (RTAP-only).
- Validate APC → consumers updates (log messages and internal state changes).
- Confirm `/metrics/raw` from `obs_dashboard_api` returns UOC data.

---

## Rollback Plan
- TTS: revert to previous branch/commit of `streaming_tts_agent.py` and consumers.
- SSR: temporarily re-enable legacy ZMQ path (not recommended) by reverting SSR file and config deps.
- Observability: restore ObservabilityHub section and revert UOC changes.
- RTAP: set `RTAP_ENABLED=false` to re-enable legacy streaming agents.

---

## Risks & Mitigations
- Contract test flakiness due to ZMQ timing: allow brief stabilization period before assertions.
- Partial deployments may mix ObservabilityHub and UOC; ensure startup config reflects single source.
- Environment mismatches (ports/addresses): document `MOC_GRPC_ADDR` and `UOC_URL` in deployment manifests.

---

## File Index (Edited/Added)
- Constants: `common/constants/service_names.py` (added)
- TTS agent/consumers: `main_pc_code/agents/streaming_tts_agent.py`, `streaming_interrupt_handler.py`, `responder.py`
- SSR: `main_pc_code/agents/streaming_speech_recognition.py`; configs under `config/*`
- RemoteConnectorAgent: `pc2_code/agents/remote_connector_agent.py`
- Observability: `services/obs_dashboard_api/server.py`, `main_pc_code/config/startup_config.yaml`, `main_pc_code/agents/predictive_health_monitor.py`
- RTAP: `real_time_audio_pipeline/config/default.yaml`, `real_time_audio_pipeline/docker/entrypoint.sh`
- Tests (Phase 4): `tests/test_contracts_apc_multipart.py`, `tests/test_service_name_constants.py`, `tests/test_no_legacy_mma_refs.py`

---

## Appendix – Commands
- Show plan state:
```bash
python3 todo_manager.py show 2024_remediation_plan
```
- Mark phases done (idempotent):
```bash
python3 todo_manager.py done 2024_remediation_plan <0|1|2|3|4>
```
- Grep sanity checks (active code only):
```bash
rg -n "StreamingTtsAgent" main_pc_code/ pc2_code/ services/ || true
rg -n "RequestCoordinator" main_pc_code/agents/streaming_speech_recognition.py || true
```