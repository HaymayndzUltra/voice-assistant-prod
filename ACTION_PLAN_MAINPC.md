# 🚀 ACTION PLAN FOR MAINPC (WSL2)

## Current Status:
- ✅ Images exist in GHCR 
- ❌ Containers keep restarting
- ❌ Audio device `/dev/snd` doesn't exist (WSL2 limitation)
- ❓ Images might be missing application code

## DO THIS NOW (In Order):

### Step 1: Pull Latest & Try WSL2 Fix
```bash
cd /home/haymayndz/AI_System_Monorepo
git pull
bash WSL2_FIX_DEPLOYMENT.sh
```

### Step 2: Check if Fixed
Wait 30 seconds, then check:
```bash
docker ps | grep -E "(model_ops|real_time|affective|unified|self_healing)"
```

### Step 3A: If Containers Still Restarting
Run diagnostics to see what's wrong:
```bash
bash DIAGNOSE_STARTUP_ISSUE.sh
```

### Step 3B: If Diagnostics Show Missing Files
The images need rebuilding. Run:
```bash
bash AUTOMATED_MAINPC_CRON.sh
```
This will take ~20 minutes but will fix everything.

## Expected Outcomes:

### ✅ Success Looks Like:
```
NAME                          STATUS
model_ops_coordinator         Up 2 minutes
real_time_audio_pipeline      Up 2 minutes  
affective_processing_center   Up 2 minutes
unified_observability_center  Up 2 minutes
self_healing_supervisor       Up 2 minutes
```

### ❌ If Still Failing:
```
NAME                          STATUS
model_ops_coordinator         Restarting (1) 10 seconds ago
```

## WSL2 Limitations to Know:

1. **No Audio Device** - We use dummy audio backend
2. **GPU Passthrough** - May not work fully with CUDA
3. **Network** - localhost works, but external access needs forwarding

## Quick Commands:

```bash
# Check logs
docker logs model_ops_coordinator

# Stop everything
docker stop $(docker ps -q)

# Remove all
docker rm -f $(docker ps -aq)

# Check what's in an image
docker run --rm --entrypoint ls ghcr.io/haymayndzultra/ai_system/model_ops_coordinator:20250812-576dfae -la /app
```

## If All Else Fails:

The images were built incorrectly. You need to:
1. Fix the Dockerfiles to properly COPY application code
2. Rebuild with `AUTOMATED_MAINPC_CRON.sh`
3. Or move to actual Linux (not WSL2) for production

---

**Start with Step 1 NOW!** The WSL2 fix should help.