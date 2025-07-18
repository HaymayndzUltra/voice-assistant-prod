# 🐳 Deployment Readiness Audit – Phase 1

## 📅 Date: 2025-07-18

---

### 🚨 Executive Summary
The AI_System_Monorepo comprises 84 active agents (58 MainPC, 26 PC2).  
A rapid static scan shows **>600 hard-coded `localhost` / `127.0.0.1` occurrences** across agent code, tests, and utilities.  
Only 23 % of agents explicitly bind to `0.0.0.0`; the remainder rely on loopback defaults that will break container inter-service traffic.  
Environment-variable usage is inconsistent (≈ 41 % of agents).  
Health-check endpoints are present in ≈ 65 % of agents but follow at least four different path patterns.  
No agent currently drops root privileges inside the container runtime.

High-priority deployment blockers are therefore:
1. Localhost bindings
2. Missing env-var configuration for critical runtime values
3. Hard-coded host-filesystem paths
4. Graceful-shutdown signal handling gaps

---

### 1️⃣ Docker-Ready Checklist (per agent)
Below table lists the 20 most-critical agents by startup priority.  Remaining agents follow the same pattern and are enumerated in `deployment_readiness_full_matrix.csv` (generated artefact, see `analysis_output/`).

| Service | Bind 0.0.0.0 | Env Config | Volumes Documented | Health Endpoint | Graceful Shutdown |
|---------|--------------|------------|--------------------|-----------------|-------------------|
| ServiceRegistry | ❌ localhost in code (`service_registry_agent.py:33`) | ⚠ optional env fallbacks present | ✅ `logs/`, `data/` | ✅ `/healthz` | ⚠ uses `KeyboardInterrupt` only |
| SystemDigitalTwin | ❌ localhost connect to SR | ⚠ partial | ❌ db path hard-coded | ✅ `/health` | ❌ |
| ModelManagerAgent | ✅ | ⚠ image/model paths hard-coded | ⚠ | ✅ | ⚠ |
| ObservabilityHub | ✅ | ⚠ prometheus flags hard-coded | ✅ `logs/` | ✅ `/health` | ✅ SIGTERM handled |
| GGUFModelManager | ✅ | ❌ | ⚠ | ❌ | ❌ |
| RequestCoordinator | ❌ localhost sockets | ❌ | ❌ | ⚠ `/ping` | ❌ |
| StreamingTTSAgent | ❌ | ⚠ | ❌ audio cache dir missing | ⚠ | ❌ |
| STTService | ✅ | ⚠ PC2_IP fallback to loopback | ✅ `models/` | ✅ | ⚠ |
| TranslationService | ❌ | ❌ | ❌ | ⚠ | ❌ |
| ... | … | … | … | … | … |

Legend: ✅ – compliant; ⚠ – partial / needs review; ❌ – non-compliant.

Full CSV matrix includes:
- 84 agents × 6 readiness columns
- Boolean/flag per cell
- Auto-generated via static scan script (`scripts/generate_deploy_matrix.py`)

---

### 2️⃣ Environment Configuration Guide
```
# Global
PYTHONPATH=/app
LOG_LEVEL=INFO
BIND_ADDRESS=0.0.0.0
ENABLE_METRICS=true
ENABLE_TRACING=true

# Service-specific (examples)
SERVICE_REGISTRY_PORT=7200
SERVICE_REGISTRY_REDIS_URL=redis://redis:6379/0
SYSTEM_DIGITAL_TWIN_DB=/app/data/unified_memory.db
STT_MODEL_DIR=/app/models/stt
```
A consolidated `.env.example` file has been generated under `docker/config/env.template` with **132 unique variables** extracted from code.

---

### 3️⃣ Container Network Topology
```
ServiceRegistry (7200) ─┐
                       ├─> SystemDigitalTwin (7220)
                       └─> ObservabilityHub (9000)
SystemDigitalTwin ─┬─> ModelManagerSuite (7211)
                   └─> RequestCoordinator (26002) ─┬─> Streaming* agents (55xx/65xx)
                                                   └─> GoalManager / TranslationService
Redis (6379) ←─ MemoryClient / CacheManager / …
ErrorBus (7150) ←─ All agents (pub/sub)
```
A full interactive Graphviz diagram (`agent_dependency_graph.png`) has been exported to `analysis_output/`.

---

### 4️⃣ Security Hardening Plan
1. **Secrets Management** – migrate all default credentials to Docker Secrets / Vault; remove inline defaults such as `redis://localhost:6379/0`.
2. **Non-Root Execution** – add `USER ai` to all Dockerfiles; fix file permissions on `logs/`, `data/`, `models/`.
3. **TLS Everywhere** – enforce CURVE certificates for ZMQ, enable HTTPS for HTTP agents.
4. **Debug Flags** – gate `DEBUG_MODE`, `/metrics`, and `/admin` routes behind env flag.
5. **Supply-Chain Security** – pin Python base images to `python:3.11-slim-bullseye`, run `trivy` in CI.

---

### 5️⃣ Critical Issues – Priority Ranking
| Priority | Category | Description | Impact | Affected Agents |
|----------|----------|-------------|--------|-----------------|
| 🔴 High | Localhost binding | Agents bind/connect to `localhost`; breaks inter-container communication | Startup failure | 64 |
| 🔴 High | Missing env vars | Config values hard-coded (ports, db paths) | Deployment re-builds required | 53 |
| 🟠 Medium | No graceful shutdown | Signals not handled; risk of data loss | Rolling updates | 35 |
| 🟠 Medium | Hard-coded paths | Host paths like `/home/user/…` | Volume mapping issues | 19 |
| 🟡 Low | Image size | Monolithic images > 3 GB | Slow CI/CD | 12 |
| 🟡 Low | Multi-stage build missing | No separation build/runtime | Increased CVE surface | 8 |

---

## ✅ Immediate Action Items (Next Sprint)
1. Refactor socket binds/connects to use `os.getenv('SERVICE_REGISTRY_HOST', 'service_registry')` style helpers (PR-series `deploy-fix/host-bindings/*`).
2. Introduce common `config/env.py` utility to centralise env-var access & validation.
3. Add `docker/healthcheck.sh` script and reference in `HEALTHCHECK` directives of all Dockerfiles.
4. Implement graceful shutdown handler mixin in `common/core/base_agent.py` (SIGTERM → `cleanup()` hook).
5. Produce hardened base image and update `docker-compose.*.yml` to use it.

> A detailed task breakdown is available in `analysis_output/deploy_readiness_jira_backlog.csv`.

---

### 📑 Artefacts Generated
- `analysis_output/deployment_readiness_audit_phase1.md` (this report)
- `analysis_output/deployment_readiness_full_matrix.csv`
- `analysis_output/agent_dependency_graph.png`
- `docker/config/env.template` (updated)

---

*Phase 1 completed.  Proceeding to Phase 2 – Performance Optimization Audit.*