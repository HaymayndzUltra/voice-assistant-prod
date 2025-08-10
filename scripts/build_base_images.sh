#!/usr/bin/env bash
set -euo pipefail

# Inputs
: "${GHCR_ORG:?Set GHCR_ORG to your organization, e.g., export GHCR_ORG=your-org}"
CACHE_REF="ghcr.io/${GHCR_ORG}/cache"
DATE_TAG="${DATE_TAG:-$(date -u +%Y%m%d)}"
GIT_SHA="${GIT_SHA:-$(git rev-parse --short HEAD)}"
TAG="${DATE_TAG}-${GIT_SHA}"
# Optional: extra flags passed to all docker buildx build calls (e.g., --network=host)
BUILDX_EXTRA_FLAGS="${BUILDX_EXTRA_FLAGS:-}"

# Auth (optional for local; required for push). Use GHCR_PAT or GITHUB_TOKEN if provided
if [[ -n "${GHCR_PAT:-}" || -n "${GITHUB_TOKEN:-}" ]]; then
  echo "🔐 Logging into ghcr.io..."
  echo "${GHCR_PAT:-${GITHUB_TOKEN:-}}" | docker login ghcr.io -u "${GHCR_USER:-${USER:-ghcr}}" --password-stdin >/dev/null 2>&1 || true
else
  echo "⚠️  No GHCR_PAT/GITHUB_TOKEN provided; proceeding assuming you are already logged in."
fi

# Ensure buildx is available
if ! docker buildx version >/dev/null 2>&1; then
  echo "❌ docker buildx not available. Install via docker/setup-buildx-action or Docker Desktop."
  exit 1
fi

echo "🏷️  Using tag: ${TAG}"
echo "🏬 Registry org: ${GHCR_ORG}"
[[ -n "${BUILDX_EXTRA_FLAGS}" ]] && echo "➕ Extra buildx flags: ${BUILDX_EXTRA_FLAGS}"

build_push() {
  local name="$1"; shift
  echo "🚢 Building ghcr.io/${GHCR_ORG}/${name}:${TAG}"
  docker buildx build \
    --pull \
    --push \
    --cache-to type=registry,ref=${CACHE_REF},mode=max \
    --cache-from type=registry,ref=${CACHE_REF} \
    ${BUILDX_EXTRA_FLAGS} \
    "$@" \
    -t ghcr.io/${GHCR_ORG}/${name}:${TAG} \
    .
}

# Order matters
build_push base-python \
  -f docker/base/base-python.Dockerfile

build_push base-utils \
  -f docker/base/base-utils.Dockerfile \
  --build-arg ORG=${GHCR_ORG} \
  --build-arg BASE_TAG=${TAG}

build_push base-cpu-pydeps \
  -f docker/base/base-cpu-pydeps.Dockerfile \
  --build-arg ORG=${GHCR_ORG} \
  --build-arg BASE_TAG=${TAG}

build_push family-web \
  -f docker/base/family-web.Dockerfile \
  --build-arg ORG=${GHCR_ORG} \
  --build-arg BASE_TAG=${TAG}

build_push base-gpu-cu121 \
  -f docker/base/base-gpu-cu121.Dockerfile

build_push family-torch-cu121 \
  -f docker/base/family-torch-cu121.Dockerfile \
  --build-arg ORG=${GHCR_ORG} \
  --build-arg BASE_TAG=${TAG}

build_push family-llm-cu121 \
  -f docker/base/family-llm-cu121.Dockerfile \
  --build-arg ORG=${GHCR_ORG} \
  --build-arg BASE_TAG=${TAG}

build_push family-vision-cu121 \
  -f docker/base/family-vision-cu121.Dockerfile \
  --build-arg ORG=${GHCR_ORG} \
  --build-arg BASE_TAG=${TAG}

build_push legacy-py310-cpu \
  -f docker/base/legacy-py310-cpu.Dockerfile

cat <<EOF
✅ Base-family builds completed.
Images pushed with tag: ${TAG}
- ghcr.io/${GHCR_ORG}/base-python:${TAG}
- ghcr.io/${GHCR_ORG}/base-utils:${TAG}
- ghcr.io/${GHCR_ORG}/base-cpu-pydeps:${TAG}
- ghcr.io/${GHCR_ORG}/family-web:${TAG}
- ghcr.io/${GHCR_ORG}/base-gpu-cu121:${TAG}
- ghcr.io/${GHCR_ORG}/family-torch-cu121:${TAG}
- ghcr.io/${GHCR_ORG}/family-llm-cu121:${TAG}
- ghcr.io/${GHCR_ORG}/family-vision-cu121:${TAG}
- ghcr.io/${GHCR_ORG}/legacy-py310-cpu:${TAG}

Verify on GHCR: https://ghcr.io/v2/${GHCR_ORG}/<image>/tags/list
EOF