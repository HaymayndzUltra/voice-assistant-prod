#!/usr/bin/env bash
set -euo pipefail

# Build and optionally push base/family Docker images in the correct order.

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ Docker is not installed or not in PATH. Please install/start Docker." >&2
  exit 1
fi

ORG=${GHCR_ORG:-}
if [[ -z "${ORG}" ]]; then
  # Try to infer org from git remote
  REMOTE_URL=$(git config --get remote.origin.url || true)
  if [[ "${REMOTE_URL}" =~ github.com[:/]{1}([^/]+)/([^/.]+) ]]; then
    ORG="${BASH_REMATCH[1]}"
  else
    echo "ℹ️  Could not infer GHCR org from git remote. Set GHCR_ORG env var." >&2
    ORG="unknown-org"
  fi
fi

# Enforce lowercase for GHCR repository path
ORG_LOWER=$(echo -n "${ORG}" | tr '[:upper:]' '[:lower:]')

DATE_TAG=$(date -u +%Y%m%d)
GIT_SHA=$(git rev-parse --short HEAD)
TAG_SUFFIX="${DATE_TAG}-${GIT_SHA}"

# Toggle pushing with PUSH=1
PUSH=${PUSH:-0}
SKIP_GPU=${SKIP_GPU:-0}
USE_REGISTRY_CACHE=${USE_REGISTRY_CACHE:-0}
USE_BUILDX=${USE_BUILDX:-}

if [[ -z "${USE_BUILDX}" ]]; then
  # Default: use buildx only when pushing; local builds use classic docker
  if [[ "${PUSH}" == "1" ]]; then USE_BUILDX=1; else USE_BUILDX=0; fi
fi

# Prepare buildx builder if not available
if ! docker buildx inspect baseimg-builder >/dev/null 2>&1; then
  docker buildx create --name baseimg-builder --use >/dev/null
fi

CACHE_REF="ghcr.io/${ORG_LOWER}/cache"

build() {
  local name="$1"; shift
  local context_dir="$1"; shift
  local dockerfile_path="$1"; shift
  local base_image_arg="${1:-}"; shift || true

  local remote_tag="ghcr.io/${ORG_LOWER}/${name}:${TAG_SUFFIX}"
  local local_tag="${name}:${TAG_SUFFIX}"

  local push_args=(--load)
  if [[ "${PUSH}" == "1" ]]; then
    push_args=(--push)
  fi

  echo "\n🚧 Building ${name} → ${remote_tag} (+ local tag ${local_tag})"

  if [[ "${USE_BUILDX}" == "1" ]]; then
    # Compose cache args conditionally
    CACHE_ARGS=()
    if [[ "${USE_REGISTRY_CACHE}" == "1" ]]; then
      CACHE_ARGS+=(--cache-from type=registry,ref="${CACHE_REF}" --cache-to type=registry,ref="${CACHE_REF}",mode=max)
    fi

    docker buildx build "${context_dir}" \
      -f "${dockerfile_path}" \
      --tag "${remote_tag}" \
      --tag "${local_tag}" \
      ${base_image_arg:+--build-arg BASE_IMAGE=${base_image_arg}} \
      --provenance=false \
      "${CACHE_ARGS[@]}" \
      "${push_args[@]}"
  else
    docker build "${context_dir}" \
      -f "${dockerfile_path}" \
      --tag "${remote_tag}" \
      --tag "${local_tag}" \
      ${base_image_arg:+--build-arg BASE_IMAGE=${base_image_arg}}
  fi
}

# Login if pushing
if [[ "${PUSH}" == "1" ]]; then
  if [[ -z "${GHCR_TOKEN:-}" || -z "${GHCR_USER:-}" ]]; then
    echo "❌ To push, set GHCR_USER and GHCR_TOKEN environment variables." >&2
    exit 1
  fi
  echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin
fi

# Build order (parents before children)
ROOT=/home/haymayndz/AI_System_Monorepo

# 1) base-python
build base-python "${ROOT}/docker/base-images/base-python" "${ROOT}/docker/base-images/base-python/Dockerfile"

# 2) base-utils (from base-python)
BASE_BP_LOCAL="base-python:${TAG_SUFFIX}"
build base-utils "${ROOT}/docker/base-images/base-utils" "${ROOT}/docker/base-images/base-utils/Dockerfile" "${BASE_BP_LOCAL}"

# 3) base-cpu-pydeps (from base-utils)
BASE_BU_LOCAL="base-utils:${TAG_SUFFIX}"
build base-cpu-pydeps "${ROOT}/docker/base-images/base-cpu-pydeps" "${ROOT}/docker/base-images/base-cpu-pydeps/Dockerfile" "${BASE_BU_LOCAL}"

# 4) family-web (from base-cpu-pydeps)
BASE_CPU_LOCAL="base-cpu-pydeps:${TAG_SUFFIX}"
build family-web "${ROOT}/docker/families/family-web" "${ROOT}/docker/families/family-web/Dockerfile" "${BASE_CPU_LOCAL}"

if [[ "${SKIP_GPU}" != "1" ]]; then
  # 5) base-gpu-cu121
  build base-gpu-cu121 "${ROOT}/docker/base-images/base-gpu-cu121" "${ROOT}/docker/base-images/base-gpu-cu121/Dockerfile"

  # 6) family-torch-cu121 (from base-gpu-cu121)
  BASE_GPU_LOCAL="base-gpu-cu121:${TAG_SUFFIX}"
  build family-torch-cu121 "${ROOT}/docker/families/family-torch-cu121" "${ROOT}/docker/families/family-torch-cu121/Dockerfile" "${BASE_GPU_LOCAL}"

  # 7) family-llm-cu121 (from family-torch-cu121)
  BASE_TORCH_LOCAL="family-torch-cu121:${TAG_SUFFIX}"
  build family-llm-cu121 "${ROOT}/docker/families/family-llm-cu121" "${ROOT}/docker/families/family-llm-cu121/Dockerfile" "${BASE_TORCH_LOCAL}"

  # 8) family-vision-cu121 (from base-gpu-cu121)
  build family-vision-cu121 "${ROOT}/docker/families/family-vision-cu121" "${ROOT}/docker/families/family-vision-cu121/Dockerfile" "${BASE_GPU_LOCAL}"
else
  echo "⚠️  SKIP_GPU=1 → Skipping GPU images (base-gpu-cu121, family-torch-cu121, family-llm-cu121, family-vision-cu121)"
fi

# 9) legacy-py310-cpu
build legacy-py310-cpu "${ROOT}/docker/legacy/legacy-py310-cpu" "${ROOT}/docker/legacy/legacy-py310-cpu/Dockerfile"

echo "\n✅ Build sequence completed."
if [[ "${PUSH}" == "1" ]]; then
  echo "📤 Images pushed with tag: ${TAG_SUFFIX}"
else
  echo "ℹ️  Images loaded locally (not pushed). To push, re-run with PUSH=1 GHCR_USER=... GHCR_TOKEN=..."
fi


