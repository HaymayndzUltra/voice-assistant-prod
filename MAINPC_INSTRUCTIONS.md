# MainPC - Phase 4 Docker Build Instructions

## Quick Start (Pinakamabilis)

### 1. SSH to MainPC
```bash
ssh haymayndz@mainpc
# or kung local ka na:
cd /home/haymayndz/AI_System_Monorepo
```

### 2. Get Latest Code
```bash
git pull origin main
```

### 3. Run the Build Script
```bash
# Make sure may GHCR_PAT ka
export GHCR_PAT=your_github_token_here

# Run the quick build
bash phase4_quick_build.sh
```

### 4. Verify Success
Tignan kung lahat ng health checks ay `{"status":"ok"}`

## Alternative: Step by Step

Kung gusto mo manual:

```bash
# 1. Setup
cd /home/haymayndz/AI_System_Monorepo
export ORG=haymayndzultra
export TAG=20250111-$(git rev-parse --short HEAD)

# 2. Login to GHCR
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# 3. Build each service
docker buildx build -f model_ops_coordinator/Dockerfile \
  --build-arg BASE_IMAGE=ghcr.io/$ORG/family-llm-cu121:20250810-9c99cc9 \
  --build-arg MACHINE=mainpc \
  -t ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG \
  --push model_ops_coordinator

# 4. Deploy
export FORCE_IMAGE_TAG=$TAG
docker compose up -d

# 5. Check health
curl http://localhost:8212/health
```

## Troubleshooting

### Docker daemon not running?
```bash
sudo systemctl start docker
# or
sudo service docker start
```

### Buildx not found?
```bash
docker buildx create --name mybuilder --use
docker buildx inspect --bootstrap
```

### GHCR authentication failed?
```bash
# Get new token from GitHub Settings > Developer settings > Personal access tokens
export GHCR_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
echo "$GHCR_PAT" | docker login ghcr.io -u haymayndzultra --password-stdin
```

## Success Indicators

✅ All builds complete without errors
✅ Images pushed to ghcr.io/haymayndzultra/ai_system/*
✅ Health endpoints return `{"status":"ok"}`
✅ No ERROR in logs: `docker compose logs --tail=50`

## After Success

```bash
# Mark Phase 4 complete
python3 todo_manager.py done docker_arch_impl_20250810 4

# Commit changes
git add -A
git commit -m "Phase 4: Docker architecture complete"
git push origin main
```

---

**IMPORTANT**: The code changes are already done. You just need to build and push!