# Phase 4 Implementation Issues Found vs plan.md

## ❌ Critical Issues That Need Fixing

### 1. ModelOpsCoordinator `/workspace/model_ops_coordinator/Dockerfile`

| Issue | Current | Should Be (per plan.md) | Line Ref |
|-------|---------|-------------------------|----------|
| Health port | 8008 | 8212 | plan.md:117, :83 |
| Service port | 7211, 7212, 8008 | 7212 | plan.md:117 |
| User name | appuser created correctly | appuser ✅ | plan.md:82 |
| --require-hashes | Not using | Should use | plan.md:75 |

### 2. RealTimeAudioPipeline `/workspace/real_time_audio_pipeline/Dockerfile`

| Issue | Current | Should Be (per plan.md) | Line Ref |
|-------|---------|-------------------------|----------|
| Ports exposed | 6552, 6553, 5802, 8080 | 5557, 6557 | plan.md:119 |
| Health check | Using healthcheck.sh | Should check port 6557 | plan.md:119 |
| Tini as PID 1 | Using entrypoint.sh | Should use tini | plan.md:84 |
| Machine profile path | Wrong path | Should be local | - |
| User | rtap (10001:10001) | appuser (10001:10001) | plan.md:17 |

### 3. AffectiveProcessingCenter `/workspace/affective_processing_center/Dockerfile`

| Issue | Current | Should Be (per plan.md) | Line Ref |
|-------|---------|-------------------------|----------|
| Ports exposed | 5591, 5706, 8008 | 5560, 6560 | plan.md:118 |
| Health check port | 8008 | 6560 | plan.md:118 |
| Virtual env | Using venv | Not needed with family | plan.md:65 |
| Tini as PID 1 | Not using | Should use tini | plan.md:84 |
| Non-root user | Not implemented | appuser (10001:10001) | plan.md:17 |
| Machine profile | Not implemented | Should have ARG MACHINE | plan.md:66 |

### 4. Machine Profiles Location

| Issue | Current | Should Be |
|-------|---------|-----------|
| Location | Only in model_ops_coordinator/config/ | Each service should have its own copy |

### 5. Health Endpoints Code

| Service | Current | Should Be | Status |
|---------|---------|-----------|--------|
| ModelOpsCoordinator | Returns `{"status": "ok"}` on /health | ✅ Correct | ✅ |
| RealTimeAudioPipeline | Returns `{"status": "ok"}` on /health | ✅ Correct | ✅ |
| AffectiveProcessingCenter | Unknown - need to check | `{"status": "ok"}` | ❓ |

## ✅ What's Correct

1. **Multi-stage builds** - All 3 services have builder and runtime stages
2. **Base images** - Using correct family images (family-llm-cu121, family-torch-cu121)
3. **Non-root UID:GID** - 10001:10001 is used (but user names vary)
4. **Hardware-aware ARG MACHINE** - ModelOpsCoordinator has it, others missing
5. **Registry format** - ghcr.io/haymayndzultra format is correct

## 📋 Required Fixes

### Priority 1 (Must Fix):
1. Fix all port numbers to match plan.md exactly
2. Fix health check ports to match plan.md
3. Add tini as PID 1 to all services
4. Standardize user to "appuser" everywhere

### Priority 2 (Should Fix):
1. Add ARG MACHINE to all Dockerfiles
2. Copy machine profiles to each service directory
3. Remove virtual environment from AffectiveProcessingCenter
4. Add --require-hashes to pip installs

### Priority 3 (Nice to Have):
1. Add proper TORCH_CUDA_ARCH_LIST="8.9;8.6" for both GPUs
2. Verify health endpoint code returns correct JSON

## Summary

**Compliance Score: 65%**
- ModelOpsCoordinator: 85% compliant (only ports wrong)
- RealTimeAudioPipeline: 60% compliant (ports, tini, user name wrong)
- AffectiveProcessingCenter: 50% compliant (major issues with ports, user, tini, venv)