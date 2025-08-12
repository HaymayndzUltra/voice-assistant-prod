#!/usr/bin/env bash
set -euo pipefail

TAG="20250812-latest"              # <-- ito ang eksaktong tag na nasa FROM refs mo
REG="ghcr.io"
ORG="haymayndzultra"

BASE=(
  "docker/base-images/base-python/Dockerfile       base-python"
  "docker/base-images/base-utils/Dockerfile        base-utils"
  "docker/base-images/base-cpu-pydeps/Dockerfile   base-cpu-pydeps"
  "docker/base-images/base-gpu-cu121/Dockerfile    base-gpu-cu121"
)

FAMILY=(
  "docker/base-images/family-web/Dockerfile          family-web"
  "docker/base-images/family-torch-cu121/Dockerfile  family-torch-cu121"
  "docker/base-images/family-llm-cu121/Dockerfile    family-llm-cu121"
  "docker/base-images/family-vision-cu121/Dockerfile family-vision-cu121"
)

log(){ printf "\n[%s] %s\n" "$(date +'%H:%M:%S')" "$*"; }

log "Setting up buildx…"
docker buildx create --use || true
docker buildx inspect --bootstrap >/dev/null

build_one() {
  local df="$1" name="$2"
  log "BUILD => $name"
  docker buildx build -f "$df" -t "$REG/$ORG/$name:$TAG" --load .
}

# 1) Base (sequential)
log "Building BASE images (sequential)…"
for it in "${BASE[@]}"; do read -r df name <<<"$it"; build_one "$df" "$name"; done

# 2) Family (parallel, limit 3 para di mabulunan ang disk/CPU)
log "Building FAMILY images (parallel=3)…"
build_one "{}" "{}" >/dev/null 2>&1 || true  # warm function in subshells
export -f build_one log
export REG ORG TAG
printf '%s\n' "${FAMILY[@]}" | xargs -L1 -P3 bash -lc 'read -r df name <<<"$0"; build_one "$df" "$name"'

# 3) Optional: rebuild a downstream service locally
# docker buildx build -f model_ops_coordinator/Dockerfile.optimized -t local/model-ops-coordinator:dev --load .

# 4) Quick validator: siguraduhing available LOCALLY ang lahat ng FROM refs
log "Validating that FROM image tags exist locally…"
# Hanapin lahat ng FROM na tumutukoy sa ghcr.io/$ORG/*:$TAG at tiyaking present sa `docker images`
missing=0
while read -r img; do
  if ! docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^$img$"; then
    echo "MISSING: $img"
    missing=1
  fi
done < <(grep -RhoE "FROM[[:space:]]+$REG/$ORG/[a-z0-9._-]+:$TAG" -- */Dockerfile* \
        | awk '{print $2}' | sort -u)

if [[ $missing -eq 0 ]]; then
  log "OK: all FROM refs with tag $TAG are available locally."
else
  log "Some FROM refs are missing locally. Build/retag those images."
  exit 1
fi
