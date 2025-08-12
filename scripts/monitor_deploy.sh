#!/usr/bin/env bash
set -euo pipefail

# Monitor latest deploy log for completion and summarize health

LOG_FILE=$(ls -1t deploy_mainpc_*.log 2>/dev/null | head -1 || true)
if [[ -z "${LOG_FILE}" ]]; then
  echo "No deploy_mainpc_*.log found. Exiting." >&2
  exit 2
fi

STATUS_OUT="deploy_status_summary.txt"
echo "Monitoring ${LOG_FILE} ..." | tee "${STATUS_OUT}"

# Wait until completion marker appears
until grep -q "Deployment Complete" "${LOG_FILE}" 2>/dev/null; do
  sleep 15
done

echo "Deployment reported complete in log: ${LOG_FILE}" | tee -a "${STATUS_OUT}"

# Run health checks
echo "\nHealth checks:" | tee -a "${STATUS_OUT}"
declare -A checks=(
  ["ModelOpsCoordinator (8212)"]=8212
  ["RealTimeAudioPipeline (6557)"]=6557
  ["AffectiveProcessingCenter (6560)"]=6560
  ["UnifiedObservabilityCenter (9110)"]=9110
  ["CentralErrorBus (8150)"]=8150
  ["SelfHealingSupervisor (9008)"]=9008
)

for name in "${!checks[@]}"; do
  port=${checks[$name]}
  if curl -sf "http://localhost:${port}/health" >/dev/null; then
    echo "${name}: OK" | tee -a "${STATUS_OUT}"
  else
    echo "${name}: FAIL" | tee -a "${STATUS_OUT}"
  fi
done

echo "\nSummary written to ${STATUS_OUT}" | tee -a "${STATUS_OUT}"


