# 🖥️ PC2 DEPLOYMENT (After MainPC)

## Important: Run MainPC FIRST!
MainPC builds and pushes all images to GHCR. PC2 just pulls and runs them.

## PC2 Services:
- **CentralErrorBus** (Primary) - Port 8150
- **UnifiedObservabilityCenter** (Backup) - Port 9111  
- **SelfHealingSupervisor** (Monitor) - Port 9009

## Simple 3 Steps on PC2:

### 1️⃣ Open Terminal on PC2
```bash
cd /home/haymayndz/AI_System_Monorepo
```

### 2️⃣ Get Latest Code
```bash
git fetch origin
git checkout cursor/build-and-deploy-ai-system-services-0e14
git pull
```

### 3️⃣ Run PC2 Script
```bash
bash PC2_EXECUTE_NOW.sh
```

## That's it! 🎉

The script will:
- ✅ Pull images from GHCR (no building needed)
- ✅ Deploy PC2-specific services
- ✅ Run health checks
- ✅ Show you results

**Expected time:** 2-3 minutes (just pulling and starting)

## Deployment Order:
1. **MainPC FIRST** - Builds everything, pushes to GHCR
2. **PC2 SECOND** - Pulls from GHCR, runs services

---

**Confidence: 99%** - Simple pull and run!