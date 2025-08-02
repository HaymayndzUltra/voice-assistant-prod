# Vision GPU Group - Container Status Report
**Report Generated:** 2025-08-02 16:16:00

## Group Overview
- **Total Containers:** 3
- **Healthy:** 1
- **Problematic:** 2

## ✅ HEALTHY CONTAINERS

### redis_vision
- **Status:** Up 7 hours (healthy)
- **Ports:** 0.0.0.0:6386->6379/tcp
- **Issue:** None - Working correctly

## ❌ PROBLEMATIC CONTAINERS

### face_recognition_agent
- **Status:** Restarting (1) 34 seconds ago
- **Issue:** Missing filterpy module for Kalman filtering
- **Error:** `ModuleNotFoundError: No module named 'filterpy'`

**Logs:**
```
File "/app/main_pc_code/agents/face_recognition_agent.py", line 35, in <module>
    from filterpy.kalman import KalmanFilter
ModuleNotFoundError: No module named 'filterpy'
```

**Additional Info:**
- Albumentations warning about version mismatch (1.4.21 vs 2.0.8)
- Restart loop due to import failure

### nats_vision
- **Status:** Restarting (1) 6 seconds ago
- **Issue:** JetStream cluster configuration error (same as reasoning group)
- **Error:** `nats-server: jetstream cluster requires server_name to be set`

**Logs:**
```
nats-server: jetstream cluster requires `server_name` to be set
nats-server: jetstream cluster requires `server_name` to be set
nats-server: jetstream cluster requires `server_name` to be set
[repeated multiple times]
```

## Root Cause Analysis

### Missing Dependencies
1. **filterpy** - Required for Kalman filtering in face tracking
2. **Albumentations version mismatch** - Using older version (1.4.21 vs 2.0.8)

### NATS Configuration Issue
- Same JetStream `server_name` configuration problem as reasoning group

## Required Fixes

### For face_recognition_agent:
1. Add `filterpy` to vision_gpu/requirements.txt
2. Update `albumentations` to latest version
3. Rebuild vision_gpu Docker image

### For nats_vision:
1. Update NATS configuration file to include `server_name` parameter
2. Restart nats_vision container

## Summary
Vision GPU group is 33% functional. Needs dependency updates and NATS configuration fix.
