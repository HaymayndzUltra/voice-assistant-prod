#!/usr/bin/env bash
# ============================================================================
# Phase-4  Containerisation & Blue-Green Deployment (Weeks 12-16)
# ----------------------------------------------------------------------------
# • Build docker images for all agents using docker-requirements.txt
# • Generate Kubernetes manifests (kustomize overlays) + secrets
# • Push images to registry & perform blue-green rollout via kubectl
# ============================================================================
set -euo pipefail
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"
APPLY=false; while [[ $# -gt 0 ]]; do case "$1" in --apply) APPLY=true; shift;; -h|--help) echo "Phase-4 script"; exit 0;; *) echo "Unknown opt $1"; exit 1;; esac; done
DRY="[DRY-RUN]"; $APPLY && DRY=""

banner(){ echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n$1\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

# 1. Build agent Docker images (multi-arch buildx)
banner "1. Docker image build"
if $APPLY; then
  docker buildx create --use default || true
  docker buildx build -f docker/Dockerfile -t ai-system/agent-suite:latest --push --platform linux/amd64,linux/arm64 .
else
  echo "${DRY} Would run docker buildx build …"
fi

# 2. Generate K8s manifests using kustomize
banner "2. Generate K8s manifests"
MANIFEST_DIR=k8s/overlays/prod
if $APPLY; then
  mkdir -p "$MANIFEST_DIR"
  cat > "$MANIFEST_DIR/kustomization.yaml" <<EOF
resources:
  - ../../base
images:
  - name: ai-system/agent-suite
    newTag: latest
EOF
  echo "✅ Generated $MANIFEST_DIR/kustomization.yaml"
else
  echo "${DRY} Would generate kustomization.yaml in $MANIFEST_DIR"
fi

# 3. Create/update secrets via kubectl
banner "3. Secrets upload"
if $APPLY; then
  kubectl delete secret ai-system-secrets --namespace ai-system --ignore-not-found
  kubectl create secret generic ai-system-secrets --namespace ai-system \
    --from-file=redis_password=<(common/utils/secret_manager.py get_redis_url) \
    --from-literal=nats_password="$(common/utils/secret_manager.py get_nats_url)"
  echo "✅ K8s secret updated"
else
  echo "${DRY} Would kubectl create secret ai-system-secrets …"
fi

# 4. Blue-green deployment via kubectl rollout
banner "4. Blue-green rollout"
if $APPLY; then
  kubectl apply -k $MANIFEST_DIR
  kubectl rollout status deployment/agent-suite -n ai-system
  echo "✅ Blue-green rollout applied"
else
  echo "${DRY} Would kubectl apply -k $MANIFEST_DIR and monitor rollout"
fi

banner "Phase-4 script complete"
$APPLY || echo "Run with --apply to execute container build & K8s rollout"