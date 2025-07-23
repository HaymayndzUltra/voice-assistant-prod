#!/usr/bin/env bash
# ============================================================================
# Phase-0 Remaining Tasks Automation Script
# ----------------------------------------------------------------------------
# Executes the outstanding remediation actions described in BACKGROUND_AGENT_GUIDE.md
# that were not fully covered by the initial Phase-0 Day-1 – Day-5 commits.
#
# The script is SAFE-BY-DEFAULT: nothing is executed on production agents.
# Use the --apply flag to perform in-place migrations; otherwise a DRY-RUN is
# performed that only reports what *would* change.
#
# Usage examples:
#   # Dry-run (default)
#   ./scripts/phase0_remaining_tasks.sh
#
#   # Execute all fixes
#   ./scripts/phase0_remaining_tasks.sh --apply
# ----------------------------------------------------------------------------
set -euo pipefail

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

# -----------------------------------------------------------
# CLI flags
# -----------------------------------------------------------
APPLY_CHANGES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY_CHANGES=true
      shift
      ;;
    -h|--help)
      echo "Phase-0 automation script"
      echo "Options:"
      echo "  --apply   Actually perform migrations/fixes (default is dry-run)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

DRY_RUN_MSG="[DRY-RUN]"
if $APPLY_CHANGES; then
  DRY_RUN_MSG=""
fi

echo "============================================================="
echo "PHASE-0 REMEDIATION – REMAINING TASKS $( $APPLY_CHANGES && echo '(APPLY)')" 
echo "============================================================="

# Helper for section banners
section() {
  echo "\n┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "┃ $1"
  echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ---------------------------------------------------------------------------
# 1. Validate configs against JSON schema (strict)
# ---------------------------------------------------------------------------
section "1. JSON-Schema validation of startup configs"
python3 scripts/validate_config.py --all --strict || {
  echo "❌ Configuration validation failed. Please fix the YAML files above." >&2
  exit 1
}

# ---------------------------------------------------------------------------
# 2. Port linter – detect cross-system conflicts
# ---------------------------------------------------------------------------
section "2. Port usage audit"
python3 scripts/port_linter.py || {
  echo "⚠️  Port linter reported issues. Review output above." >&2
}

# ---------------------------------------------------------------------------
# 3. Secrets scanner – locate hard-coded credentials
# ---------------------------------------------------------------------------
section "3. Secrets scan (NATS / REDIS / API_KEY / TOKEN)"
GREP_PATTERN='(NATS_|REDIS_|API_KEY|TOKEN).*[=:]'
SECRETS_FOUND=$(grep -R --line-number -E "$GREP_PATTERN" main_pc_code pc2_code || true)
if [[ -n "$SECRETS_FOUND" ]]; then
  echo "❌ Plain-text secrets detected:\n$SECRETS_FOUND"
  if ! $APPLY_CHANGES; then
    echo "Run again with --apply after moving secrets to SecretManager." >&2
  else
    echo "\nAttempting automatic placeholder replacement…"
    while IFS= read -r line; do
      FILE="$(echo "$line" | cut -d: -f1)"
      sed -i.bak -E "s/$GREP_PATTERN/\${SECRET_PLACEHOLDER}/g" "$FILE"
      echo "  Replaced secrets in $FILE"
    done <<< "$SECRETS_FOUND"
    echo "✅ Secret placeholders injected. Commit .bak files if needed for diff review."
  fi
else
  echo "✅ No hard-coded secrets found."
fi

# ---------------------------------------------------------------------------
# 4. Legacy agent migration to BaseAgent
# ---------------------------------------------------------------------------
section "4. Legacy agent migration"
python3 scripts/enforce_base_agent.py || {
  echo "⚠️  BaseAgent enforcement script produced warnings (see above)." >&2
}

# ---------------------------------------------------------------------------
# 5. Deep source-code scan for imports / issues
# ---------------------------------------------------------------------------
section "5. Deep source-code scan & dependency graph"
python3 source_code_scanner.py || {
  echo "⚠️  Source-code scanner found issues (see above JSON reports)." >&2
}

# ---------------------------------------------------------------------------
# 6. Observability Hub dual-deployment checks
# ---------------------------------------------------------------------------
section "6. Observability Hub dual-deployment status"
EDGE_HUB_PORT=9100
CENTRAL_HUB_PORT=9000

# Simple check if Edge hub already running (localhost)
if lsof -i :$EDGE_HUB_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "✅ Edge ObservabilityHub already running on port $EDGE_HUB_PORT"
else
  echo "ℹ️  Edge ObservabilityHub not detected on port $EDGE_HUB_PORT"
  if $APPLY_CHANGES; then
    echo "${DRY_RUN_MSG} Launching EdgeHub …"
    # Use Python for now; replace with container invocation later
    python3 phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py --port $EDGE_HUB_PORT &
    EDGE_PID=$!
    echo "$EDGE_PID" > observability_edgehub.pid
    echo "✅ EdgeHub started (PID $EDGE_PID)"
  else
    echo "Run with --apply to auto-start EdgeHub." >&2
  fi
fi

# ---------------------------------------------------------------------------
# 7. Prometheus exporter flag verification
# ---------------------------------------------------------------------------
section "7. Prometheus metrics toggle verification"
MISSING_METRICS=$(grep -R --line-number -L "ENABLE_PROMETHEUS_METRICS" main_pc_code pc2_code  | grep -E "agents/.+\.py$" | head -n 20 || true)
if [[ -n "$MISSING_METRICS" ]]; then
  echo "⚠️  Some agents may not enable Prometheus metrics by default:" 
  echo "$MISSING_METRICS"
  echo "Add env var ENABLE_PROMETHEUS_METRICS=true in their startup or ensure migration to BaseAgent."
else
  echo "✅ All agents reference Prometheus metrics env flag."
fi

# ---------------------------------------------------------------------------
# 8. Final report
# ---------------------------------------------------------------------------
section "8. Phase-0 automation summary"
echo "All checks/scripts executed. Review warnings above."
if ! $APPLY_CHANGES; then
  echo "No destructive changes were applied (dry-run mode). Use --apply to perform migrations/fixes."
fi

exit 0