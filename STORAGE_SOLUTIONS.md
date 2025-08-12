# 💾 STORAGE SOLUTIONS - 140GB Used, 60GB Left!

## 🔴 THE PROBLEM
- **60+ agents** need containerization (per plan.md)
- Each image: 1-3GB (GPU images up to 5GB!)
- Total needed: **~150-200GB just for Docker!**
- You only have 60GB left = **NOT ENOUGH!**

## ✅ IMMEDIATE SOLUTIONS

### Option 1: Emergency Cleanup (Free ~50-100GB)
```bash
# Run on MainPC
bash EMERGENCY_CLEANUP.sh
```

### Option 2: Remove Old/Broken Images
```bash
# Remove specific broken images
docker rmi $(docker images -f "dangling=true" -q)

# Remove old tags
docker images | grep "576dfae" | awk '{print $3}' | xargs docker rmi -f
```

### Option 3: Move Docker to External Drive
```bash
# Stop Docker
sudo systemctl stop docker

# Move Docker directory to external drive
sudo mv /var/lib/docker /mnt/external-drive/docker

# Create symlink
sudo ln -s /mnt/external-drive/docker /var/lib/docker

# Start Docker
sudo systemctl start docker
```

## 🎯 SUSTAINABLE SOLUTIONS

### 1. **SELECTIVE CONTAINERIZATION**
Instead of 60+ agents, only containerize CRITICAL ones:

**Phase 1 - Core Only (10 agents, ~20GB)**
- ServiceRegistry ✅
- SystemDigitalTwin ✅
- UnifiedSystemAgent ✅
- ModelOpsCoordinator ✅
- RealTimeAudioPipeline ✅
- AffectiveProcessingCenter ✅
- UnifiedObservabilityCenter ✅
- SelfHealingSupervisor ✅
- CentralErrorBus ✅
- MemoryFusionHub ✅

**Run others as Python scripts** (no containers)

### 2. **USE DOCKER COMPOSE WITH VOLUMES**
Share base layers between containers:
```yaml
version: '3.8'
services:
  base-image:
    image: ghcr.io/haymayndzultra/base-cpu-pydeps
    command: /bin/true
  
  agent1:
    depends_on: [base-image]
    volumes_from: [base-image]
    # Saves ~1GB per agent
```

### 3. **REMOTE BUILD & PULL**
Build on cloud, pull only what you need:
```bash
# Use GitHub Actions to build
# Then pull only running services
docker pull ghcr.io/haymayndzultra/ai_system/model_ops_coordinator:latest
```

### 4. **HYBRID APPROACH** (RECOMMENDED)
- **Containerize:** Core 10 agents only
- **Python scripts:** Everything else
- **Total storage:** ~30GB instead of 200GB!

## 📊 STORAGE BREAKDOWN

### Current Usage (140GB):
- Docker images: ~100GB
- Docker build cache: ~30GB
- Containers/volumes: ~10GB

### After Cleanup:
- Essential images only: ~30GB
- No build cache: 0GB
- Minimal volumes: ~5GB
- **Total: ~35GB** ✅

## 🚀 RECOMMENDED ACTION PLAN

### Step 1: Clean Everything
```bash
docker system prune -a --volumes -f
```

### Step 2: Pull Only Essential Images
```bash
# Only the 6 we already fixed
docker pull ghcr.io/haymayndzultra/ai_system/model_ops_coordinator:latest
docker pull ghcr.io/haymayndzultra/ai_system/real_time_audio_pipeline:latest
docker pull ghcr.io/haymayndzultra/ai_system/affective_processing_center:latest
docker pull ghcr.io/haymayndzultra/ai_system/unified_observability_center:latest
docker pull ghcr.io/haymayndzultra/ai_system/self_healing_supervisor:latest
docker pull ghcr.io/haymayndzultra/ai_system/central_error_bus:latest
```

### Step 3: Run Other Agents as Scripts
```bash
# No containers, just Python
cd /home/haymayndz/AI_System_Monorepo
python main_pc_code/agents/service_registry.py &
python main_pc_code/agents/system_digital_twin.py &
# etc...
```

## 💡 THE TRUTH

**You DON'T need to containerize all 60+ agents!**

Plan.md shows the "ideal" state, but for development:
- **6-10 containerized agents** is enough
- Run the rest as Python scripts
- Save 150GB+ of storage!

## 🎯 Final Recommendation

1. **Clean Docker completely** (save ~100GB)
2. **Only containerize core 10 agents** (use ~30GB)
3. **Run others as scripts** (no extra storage)
4. **Total storage needed: ~30GB** instead of 200GB!

---

**This is more realistic for your 60GB remaining space!**