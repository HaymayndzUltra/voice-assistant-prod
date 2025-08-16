#!/usr/bin/env bash
set -euo pipefail

# ====== CONFIG (edit or export before run) ======
: "${ORG:=haymayndzultra}"      # e.g., haymayndzultra
: "${TAG:=20250814-latest}"     # e.g., 20250814-latest
: "${CHECK_GHCR:=true}"         # set to "false" to skip GHCR checks
# ===============================================

# Try to source ghcr.env if present (quiet)
if [ -f "./ghcr.env" ]; then
  # shellcheck disable=SC1091
  source ./ghcr.env || true
fi

# Prefer GHCR_TOKEN; fallback to GHCR_NEW if present
if [ -z "${GHCR_TOKEN:-}" ] && [ -n "${GHCR_NEW:-}" ]; then
  export GHCR_TOKEN="$GHCR_NEW"
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1"; exit 2; }; }

echo "== Repo structure check =="
root_ok=true
for d in \
  "entrypoints" \
  "affective_processing_center" \
  "real_time_audio_pipeline" \
  "memory_fusion_hub" \
  "model_ops_coordinator" \
  "unified_observability_center" \
  "services/central_error_bus" \
  "services/cross_gpu_scheduler" \
  "services/obs_dashboard_api" \
  "services/self_healing_supervisor" \
  "services/speech_relay" \
  "services/streaming_translation_proxy"
do
  if [ -d "$d" ]; then
    printf " - %-45s OK\n" "$d/"
  else
    printf " - %-45s MISSING\n" "$d/"
    root_ok=false
  fi
done
$root_ok || echo "NOTE: Some directories missing—review above."

echo
echo "== Entrypoints mapping =="
declare -A E2DIR=(
  [affective_processing_center_entrypoint.sh]="affective_processing_center"
  [real_time_audio_pipeline_entrypoint.sh]="real_time_audio_pipeline"
  [model_ops_entrypoint.sh]="model_ops_coordinator"
  [unified_observability_center_entrypoint.sh]="unified_observability_center"
  [central_error_bus_entrypoint.sh]="services/central_error_bus"
  [self_healing_supervisor_entrypoint.sh]="services/self_healing_supervisor"
)

missing_any=false
while IFS= read -r -d '' ep; do
  ep_base="$(basename "$ep")"
  target="${E2DIR[$ep_base]:-UNKNOWN}"
  printf "\n • %s\n" "$ep_base"
  echo "   - Target dir: $target"
  if [ "$target" != "UNKNOWN" ] && [ -d "$target" ]; then
    test -f "$target/Dockerfile" && echo "   - Dockerfile: OK" || echo "   - Dockerfile: MISSING"
    test -f "$target/Dockerfile.optimized" && echo "   - Dockerfile.optimized: OK" || echo "   - Dockerfile.optimized: MISSING"
    test -f "$target/app.py" && echo "   - app.py: OK" || echo "   - app.py: MISSING (some services may not use app.py)"
  else
    echo "   - Target dir missing or unknown"
    missing_any=true
  fi

  if grep -Eiq '(python|uvicorn|gunicorn|exec|docker run)' "$ep"; then
    echo "   - Entrypoint contains launch commands (keywords found)"
  else
    echo "   - Entrypoint: no obvious launch keywords (ok if delegated)"
  fi
done < <(find entrypoints -maxdepth 1 -type f -name "*_entrypoint.sh" -print0 2>/dev/null || true)
$missing_any && echo "NOTE: Some entrypoint targets missing—see above."

echo
echo "== Hub summary =="
for hub in affective_processing_center real_time_audio_pipeline memory_fusion_hub model_ops_coordinator unified_observability_center; do
  echo " [$hub]"
  test -d "$hub" || { echo "  - dir: MISSING"; continue; }
  test -f "$hub/Dockerfile" && echo "  - Dockerfile: OK" || echo "  - Dockerfile: MISSING"
  test -f "$hub/Dockerfile.optimized" && echo "  - Dockerfile.optimized: OK" || echo "  - Dockerfile.optimized: MISSING"
  test -f "$hub/app.py" && echo "  - app.py: OK" || echo "  - app.py: MISSING"
done

echo
echo "== Services summary =="
for svc in central_error_bus cross_gpu_scheduler obs_dashboard_api self_healing_supervisor speech_relay streaming_translation_proxy; do
  p="services/$svc"
  echo " [$p]"
  test -d "$p" && echo "  - dir: OK" || { echo "  - dir: MISSING"; continue; }
  if compgen -G "$p/*Dockerfile*" >/dev/null; then
    echo "  - Dockerfile(s):"
    ls -1 "$p"/Dockerfile* 2>/dev/null | sed 's/^/    • /'
  else
    echo "  - Dockerfile(s): NONE"
  fi
done

if [ "${CHECK_GHCR}" = "true" ]; then
  echo
  echo "== GHCR manifest checks (ORG=$ORG, TAG=$TAG) =="
  need docker
  need jq
  if [ -n "${GHCR_TOKEN:-}" ]; then
    echo "$GHCR_TOKEN" | docker login ghcr.io -u "$ORG" --password-stdin >/dev/null
  else
    echo "WARN: No GHCR_TOKEN/GHCR_NEW; will try public manifest inspect."
  fi
  imgs="affective_processing_center real_time_audio_pipeline memory_fusion_hub model_ops_coordinator unified_observability_center"
  for img in $imgs; do
    ref="ghcr.io/$ORG/$img:$TAG"
    echo ">> $ref"
    if docker manifest inspect "$ref" >/dev/null 2>&1; then
      docker manifest inspect "$ref" | jq -r '
        if .manifests then
          (.manifests[] | "   • " + (.platform.os // "?") + "/" + (.platform.architecture // "?") + "  " + (.digest // ""))
        else
          "   • single-arch (no manifest list)"
        end
      '
    else
      echo "   • NOT FOUND (private or wrong tag)"
    fi
  done
fi

echo
echo "== Done =="
