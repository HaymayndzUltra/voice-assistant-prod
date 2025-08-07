# 🚀 PC2 IMAGE PULL GUIDE - OPTIMIZED SHARED BASES

## ⚡ QUICK PULL COMMANDS (PC2 Machine)

### 🔧 **STEP 1: Setup Environment Variables**
```bash
cd /home/haymayndz/AI_System_Monorepo
export REGISTRY=ghcr.io/haymayndzultra
export TAG=pc2-latest
```

### 📦 **STEP 2: Login to Registry**
```bash
echo "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" | docker login ghcr.io -u haymayndzultra --password-stdin
```

### 🎯 **STEP 3A: Pull Shared Base Images (OPTIMIZED)**
```bash
# Pull the 3 shared base images first (for caching)
docker pull ghcr.io/haymayndzultra/pc2-base-minimal:latest
docker pull ghcr.io/haymayndzultra/pc2-base-cache_redis:latest  
docker pull ghcr.io/haymayndzultra/pc2-base-ml_heavy:latest
```

### 🐳 **STEP 3B: Pull All PC2 Agent Images (FAST!)**
```bash
# These will be MUCH faster since they inherit from cached bases
docker pull ghcr.io/haymayndzultra/memoryorchestratorservice:pc2-latest
docker pull ghcr.io/haymayndzultra/tieredresponder:pc2-latest
docker pull ghcr.io/haymayndzultra/asyncprocessor:pc2-latest
docker pull ghcr.io/haymayndzultra/cachemanager:pc2-latest
docker pull ghcr.io/haymayndzultra/visionprocessingagent:pc2-latest
docker pull ghcr.io/haymayndzultra/dreamworldagent:pc2-latest
docker pull ghcr.io/haymayndzultra/unifiedmemoryreasoningagent:pc2-latest
docker pull ghcr.io/haymayndzultra/tutoragent:pc2-latest
docker pull ghcr.io/haymayndzultra/tutoringagent:pc2-latest
docker pull ghcr.io/haymayndzultra/contextmanager:pc2-latest
docker pull ghcr.io/haymayndzultra/experiencetracker:pc2-latest
docker pull ghcr.io/haymayndzultra/resourcemanager:pc2-latest
docker pull ghcr.io/haymayndzultra/taskscheduler:pc2-latest
docker pull ghcr.io/haymayndzultra/authenticationagent:pc2-latest
docker pull ghcr.io/haymayndzultra/unifiedutilsagent:pc2-latest
docker pull ghcr.io/haymayndzultra/proactivecontextmonitor:pc2-latest
docker pull ghcr.io/haymayndzultra/agenttrustscorer:pc2-latest
docker pull ghcr.io/haymayndzultra/filesystemassistantagent:pc2-latest
docker pull ghcr.io/haymayndzultra/remoteconnectoragent:pc2-latest
docker pull ghcr.io/haymayndzultra/unifiedwebagent:pc2-latest
docker pull ghcr.io/haymayndzultra/dreamingmodeagent:pc2-latest
docker pull ghcr.io/haymayndzultra/advancedrouter:pc2-latest
docker pull ghcr.io/haymayndzultra/observabilityhub:pc2-latest
```

### 🔄 **ALTERNATIVE: Automated Pull Script**
```bash
# Create automated pull script
cat > pull_pc2_images.sh << 'EOF'
#!/bin/bash
set -euo pipefail

REGISTRY="ghcr.io/haymayndzultra"
TAG="pc2-latest"

echo "🚀 Pulling PC2 Optimized Images..."

# Pull base images first
echo "📦 Pulling shared base images..."
docker pull ${REGISTRY}/pc2-base-minimal:latest
docker pull ${REGISTRY}/pc2-base-cache_redis:latest  
docker pull ${REGISTRY}/pc2-base-ml_heavy:latest

echo "🐳 Pulling PC2 agent images..."
agents=(
    "memoryorchestratorservice"
    "tieredresponder"
    "asyncprocessor"
    "cachemanager"
    "visionprocessingagent"
    "dreamworldagent"
    "unifiedmemoryreasoningagent"
    "tutoragent"
    "tutoringagent"
    "contextmanager"
    "experiencetracker"
    "resourcemanager"
    "taskscheduler"
    "authenticationagent"
    "unifiedutilsagent"
    "proactivecontextmonitor"
    "agenttrustscorer"
    "filesystemassistantagent"
    "remoteconnectoragent"
    "unifiedwebagent"
    "dreamingmodeagent"
    "advancedrouter"
    "observabilityhub"
)

for agent in "${agents[@]}"; do
    echo "  → Pulling ${agent}..."
    docker pull ${REGISTRY}/${agent}:${TAG}
done

echo "✅ All PC2 images pulled successfully!"
docker images | grep haymayndzultra
EOF

chmod +x pull_pc2_images.sh
./pull_pc2_images.sh
```

## 🎯 **IMAGE SIZE BENEFITS**

### **Before Optimization:**
- Each agent: 500MB - 2.5GB (full dependency stack)
- Total storage: ~15-25GB for 23 agents

### **After Optimization:**  
- Base images: ~3GB total (shared across all agents)
- Agent images: ~50-200MB each (code + agent-specific deps only)
- Total storage: ~6-8GB (60-70% reduction!)

### **Network Benefits:**
- Base layers cached locally after first pull
- Subsequent agent pulls only download code layers (~50MB each)
- 70-80% reduction in network transfer time

## 🔍 **VERIFICATION COMMANDS**

### **Check Downloaded Images:**
```bash
docker images | grep haymayndzultra | sort
```

### **Check Image Sizes:**
```bash
docker images | grep haymayndzultra | awk '{print $1 ":" $2 "\t" $7 $8}' | column -t
```

### **Verify Base Image Inheritance:**
```bash
docker inspect ghcr.io/haymayndzultra/cachemanager:pc2-latest | grep -A5 "Config"
```

## 📊 **EXPECTED RESULTS:**
- **Pull Speed**: 3-5x faster than individual builds
- **Storage Usage**: 60-70% reduction  
- **Network Transfer**: Minimal after base images cached
- **Total Pull Time**: ~15-30 minutes vs 2-3 hours

## 🚨 **TROUBLESHOOTING:**

### **If Registry Login Fails:**
```bash
# Check Docker login status
docker system info | grep Username

# Re-login if needed
docker logout ghcr.io
echo "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" | docker login ghcr.io -u haymayndzultra --password-stdin
```

### **If Images Not Found:**
```bash
# Check if images were pushed successfully from MainPC
curl -u haymayndzultra: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 \
  https://ghcr.io/v2/haymayndzultra/pc2-base-minimal/tags/list
```

## 🎉 **SUCCESS INDICATORS:**
- All 26 images pulled (3 bases + 23 agents)
- Total storage < 10GB
- Pull time < 30 minutes
- Ready for Phase 3: PC2 deployment with docker-compose
