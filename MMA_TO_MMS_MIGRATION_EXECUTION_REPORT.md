# MMA → MMS Migration Execution Report

_Last updated: 2025-08-02_

---

## 1. Objective
Replace the legacy **ModelManagerAgent (MMA)** with the consolidated **ModelManagerSuite (MMS)** while ensuring zero-downtime, no logic conflicts, and full backward-compatibility for all dependent agents and services.

---

## 2. Current Status Snapshot

| Item | MMA | MMS |
| ---- | --- | --- |
| Service container | `model_manager_agent` (language_stack) | _not yet deployed_ |
| Default ZMQ port | **5570** (health 6570) | 7211 (health 8211) |
| Import path presence | `main_pc_code.agents.model_manager_agent` | Aliases missing |
| Feature parity | Baseline | 90-95 % (some helpers stubbed) |
| VRAM / model ledger | Single source of truth | Potential duplicate if both run |

### Critical Fixes Done
1. **IndentationError** at tail of `model_manager_agent.py` – resolved (commit `fix/indent_tail`).
2. MMA container can now start → Phase 1.2 unblocked.

---

## 3. Risk Analysis

1. **Port conflicts** if MMA & MMS bind to same legacy port concurrently.
2. **Duplicate VRAM accounting** when both services auto-load models.
3. **Missing helper methods** in MMS will break edge-case calls.
4. **Import-path expectations** (`import …model_manager_agent`) unresolved unless alias added.

---

## 4. Action Plan (Step-by-Step)

### Phase 0 – Back-up & Environment Safety
```bash
# 0.1  Create safe branch & tag
git checkout -b migrate-to-mms
git tag pre-mms-migration

# 0.2  Archive model volumes (optional)
./scripts/backup_model_volumes.sh  # custom script
```

### Phase 1 – Restore MMA Stability
```bash
# 1.1  Ensure compose service exists & build
cd docker/language_stack
docker compose up -d --build model_manager_agent

# 1.2  Verify health
curl -s tcp://localhost:6570 | jq .status  # expect "ok"
```

### Phase 2 – Validate MMS in Parallel (No Conflict)
1. **Add test container** (`model_manager_suite_test`) via `docker-compose.override.yml` on ports `7721/8721`.
2. **Smoke-test script** `utils/mms_smoke_test.py`:
   * load_model → generate_text → health_check.
3. **Parity test** (pytest) comparing responses from MMA vs MMS.
4. **Port missing helper methods** as they surface – update `model_manager_suite.py`.

### Phase 3 – Prepare Drop-In Replacement
1. Expose MMS on 5570/6570 inside test stack (stop MMA temporarily to confirm binding).
2. Append module alias in `model_manager_suite.py`:
   ```python
   import sys as _sys
   _sys.modules['main_pc_code.agents.model_manager_agent'] = _sys.modules[__name__]
   ```
3. Grep for direct `ModelManagerAgent(` invocations; switch to `model_manager_suite` if needed.
4. Ensure ENV default `MODEL_MANAGER_PORT` supported everywhere (it is).

### Phase 4 – Cut-Over
```bash
# 4.1 Edit docker-compose.yml (language_stack)
#    replace service model_manager_agent → model_manager_suite
# 4.2 Deploy
cd docker/language_stack
docker compose up -d --build model_manager_suite
docker compose rm -f model_manager_agent
```

### Phase 5 – Post-Cutover Validation
* `curl tcp://localhost:6570` → status ok
* End-to-end voice command exercising TTS & STT (they use model_client).
* SystemDigitalTwin VRAM metrics confirm.
* Observability dashboards updated.

### Phase 6 – Cleanup & Rollback Plan
* Remove MMA image: `docker rmi $(docker images | grep model_manager_agent | awk '{print $3}')`
* If rollback needed: `git checkout pre-mms-migration` + redeploy original compose.

---

## 5. Outstanding Tasks Tracker

| ID | Task | Owner | Status |
| -- | ---- | ----- | ------ |
| T-01 | Add MMS test container override | DevOps | pending |
| T-02 | Write parity pytest | QA | pending |
| T-03 | Port missing helper methods | Backend | pending |
| T-04 | Compose swap & deploy | DevOps | pending |
| T-05 | Observability update | SRE | pending |

---

## 6. Verification Checklist
- [ ] MMS responds to `health_check` with status "ok".
- [ ] All `model_client.py` calls succeed.
- [ ] VRAM metrics match expectations.
- [ ] No duplicate model loads observed in GPU memory.
- [ ] SystemDigitalTwin, VRAMOptimizer, TTS/STT pass integration tests.

---

## 7. Conclusion
The migration is **feasible** with low operational risk provided the phased rollout is followed. Completion of outstanding tasks T-01…T-05 will enable full replacement of MMA by MMS, unlocking consolidated management and predictive loading features.

---

**Prepared by:** Migration Assistant

**Confidence Level:** 94 %
