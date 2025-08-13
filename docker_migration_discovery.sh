#!/usr/bin/env bash
##############################################################################
# DOCKER-MIGRATION TRUTH DISCOVERY + OPTIMIZATION PLAN (HARDENED v4)
# - Works for Cursor background agents and local shells
# - Strict mode, bounded run-time, scoped filesystem, secure secrets
##############################################################################
set -euo pipefail
IFS=$'\n\t'

#################### 0-Z  Finalizer (define before any usage) ##################
finalized=0
finalize_and_exit() {
  (( finalized )) && exit 0
  finalized=1
  cat <<'EOF'

===== DELIVERABLES =====
A) Executive Summary
B) Strategy Matrix  (CPU/GPU, Build-Loc vs Pull, Tags, Cache)
C) Risks & Mitigations
D) Top 5 Immediate Actions
E) Confidence Scores (0-100 %)
EOF
  exit 0
}

#################### 0-A  Secrets ################################################
# Optional override via env GHCR_ENV_FILE; defaults to absolute path
readonly GHCR_ENV_FILE="${GHCR_ENV_FILE:-/workspace/.cursor_secrets/ghcr.env}"
if [[ -r "$GHCR_ENV_FILE" ]]; then
  umask 077
  export HISTFILE=/dev/null
  # shellcheck source=/dev/null
  source "$GHCR_ENV_FILE"
  echo "🟢 GHCR token loaded"
else
  printf '❌ Missing %s\n' "$GHCR_ENV_FILE" >&2
  exit 1
fi
: "${GHCR_NEW:?GHCR_NEW not set}"

# Allow overriding GHCR username; default to your current value for compatibility
readonly GHCR_USER="${GHCR_USER:-haymayndzultra}"

#################### 0-B  Globals / Guards #######################################
readonly LOG_MAX=3000
safe_head(){ head -n "$LOG_MAX"; }

readonly START_TS=$(date +%s)
readonly MAX_SECONDS=540
must_stop(){ (( $(date +%s) - START_TS > MAX_SECONDS )); }

trap 'echo "⛔ Time budget reached — summarising"; finalize_and_exit' INT TERM

readonly SCOPE_DIRS=(affective_processing_center real_time_audio_pipeline \
 model_ops_coordinator memory_fusion_hub unified_observability_center \
 main_pc_code pc2_code memory-bank)
in_scope(){ [[ " ${SCOPE_DIRS[*]} " == *" $1 "* ]]; }

# Build an Authorization header suitable for GHCR v2 or GitHub REST fallback
ghcr_auth_header() {
  if [[ -n "${GHCR_USER:-}" ]]; then
    # Cross-platform base64 without newlines
    local b64
    b64="$(printf '%s:%s' "$GHCR_USER" "$GHCR_NEW" | base64 | tr -d '\r\n')"
    printf 'Authorization: Basic %s' "$b64"
  else
    printf 'Authorization: Bearer %s' "$GHCR_NEW"
  fi
}

curl_safe() {
  local url="$1"
  curl --connect-timeout 5 --max-time 10 --retry 2 --retry-delay 1 \
       --proto-default https --fail --silent --show-error \
       -H "$(ghcr_auth_header)" \
       "https://ghcr.io${url}"
}

gh_list_images_registry_or_api() {
  # Try GHCR registry v2 catalog first, then fallback to GitHub REST API
  if curl_safe '/v2/_catalog?n=100' | { command -v jq >/dev/null && jq . || cat; } | safe_head; then
    return 0
  fi
  # Fallback: GitHub REST API (requires read:packages)
  curl --connect-timeout 5 --max-time 10 --retry 2 --retry-delay 1 \
       --fail --silent --show-error \
       -H "Authorization: Bearer ${GHCR_NEW}" \
       -H "Accept: application/vnd.github+json" \
       "https://api.github.com/users/${GHCR_USER}/packages?package_type=container" \
       | { command -v jq >/dev/null && jq -r '.[].name' || cat; } | safe_head
}

#################### 0-C  Docker Daemon ##########################################
if command -v docker >/dev/null 2>&1 && sudo -n docker ps >/dev/null 2>&1; then
  echo "🟢 Docker daemon already running"
  export DOCKER_FALLBACK=
elif command -v docker >/dev/null 2>&1; then
  echo "🔄 Starting sudo dockerd (20 s timeout)…"
  if timeout 20s sudo -n nohup dockerd \
        -H unix:///var/run/docker.sock \
        --storage-driver=vfs --iptables=false --bridge=none \
        > /tmp/dockerd.log 2>&1; then
    for _ in {1..10}; do sudo -n docker ps >/dev/null 2>&1 && break; sleep 1; done
    sudo -n docker ps >/dev/null 2>&1 || export DOCKER_FALLBACK=1
  else
    echo "🔴 dockerd start failed (see /tmp/dockerd.log) → registry-only mode"
    export DOCKER_FALLBACK=1
  fi
else
  echo "🔴 docker CLI absent — registry-only mode"
  export DOCKER_FALLBACK=1
fi

#################### 0-D  GHCR Login #############################################
if [[ -z "${DOCKER_FALLBACK:-}" ]]; then
  if printf '%s\n' "${GHCR_NEW}" | sudo -n docker login ghcr.io \
        -u "${GHCR_USER}" --password-stdin >/dev/null 2>&1; then
    echo "🟢 GHCR login OK"
  else
    echo "🔴 Login failed → registry-only mode"
    export DOCKER_FALLBACK=1
  fi
fi

echo "BOOTSTRAP DONE  (DOCKER_FALLBACK=${DOCKER_FALLBACK:-0})"

##############################################################################
# SECTION 1 — INVENTORY VERIFICATION
##############################################################################
echo "── Python agents ──"
find . -type f -name '*.py' -path '*/agents/*' | safe_head

echo "── Dockerfiles count ──"
find . -type f -name 'Dockerfile*' | wc -l | safe_head

echo "── docker-compose files count ──"
find . \( -name 'docker-compose*.yml' -o -name 'docker-compose*.yaml' \) -type f \
     | wc -l | safe_head

echo "── Docker / GHCR images ──"
if [[ -z "${DOCKER_FALLBACK:-}" ]]; then
  sudo -n docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' | safe_head
else
  gh_list_images_registry_or_api || true
fi
must_stop && finalize_and_exit

##############################################################################
# SECTION 2 — CONSOLIDATION HUB ANALYSIS (sample for one hub)
##############################################################################
GREP_OPTS=(--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv \
           --binary-files=without-match)
echo "── AffectiveProcessingCenter modules ──"
grep -R "${GREP_OPTS[@]}" -E \
     'MoodTracker|HumanAwareness|ToneDetector|VoiceProfile|Empathy' \
     affective_processing_center/ | safe_head || true
must_stop && finalize_and_exit

# …………… Sections 3-8 would continue similarly with safe_head + must_stop ……………

##############################################################################
# SECTION 9 — STRATEGIC OPTIMIZATION & RECOMMENDATIONS
##############################################################################
cat <<'EOF'
Provide three options:
A) Full Consolidation, GHCR-Centric Build
B) Hybrid (GPU builds local, CPU pulls)
C) Legacy + Gradual Hub Roll-In

For each: reasoning | risks | dependencies | timeline | rollback
EOF

##############################################################################
# FINALIZATION
##############################################################################
finalize_and_exit