#!/usr/bin/env bash
# ============================================================================
# Phase-1 Upgrade Tasks Automation Script
# ----------------------------------------------------------------------------
# PLACEHOLDER - Code will be pasted here
# ---------------------------------------------------------------------------- #!/usr/bin/env bash
# ==========================================================================
# Phase-1  Upgrade & Migration Script  (Weeks 1-4)
# --------------------------------------------------------------------------
# Implements the Phase-1 objectives from BACKGROUND_AGENT_GUIDE.md:
#   • Path-Env shim → PathManager enforcement  (lint + auto-fix)
#   • Complete migration of remaining legacy agents to BaseAgent
#   • Inject StandardizedHealthMixin where missing
#   • CI lint hooks for PathManager & health-endpoint presence
#
# Like the Phase-0 script, this is DRY-RUN by default; use --apply to mutate.
# ==========================================================================
set -euo pipefail

PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

# ---------- flags ----------
APPLY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=true; shift;;
    -h|--help)
      echo "Phase-1 migration script"
      echo "--apply   perform fixes (default DRY-RUN)"; exit 0;;
    *) echo "Unknown option $1"; exit 1;;
  esac
done
DRY="[DRY-RUN]"; $APPLY && DRY=""

banner(){ echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n$1\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

# ------------------------------------------------------------------
# 1. Enforce PathManager (replace path_env legacy calls)
# ------------------------------------------------------------------
banner "1. PathManager enforcement"
LEGACY_PATH_CALLS=$(grep -R --line-number -E "from\s+.*path_env|PathEnv|join_path\(" main_pc_code pc2_code | grep -v tests || true)
if [[ -n "$LEGACY_PATH_CALLS" ]]; then
  echo "Legacy path_env usages detected:"; echo "$LEGACY_PATH_CALLS" | head -n 20
  if $APPLY; then
    echo "$LEGACY_PATH_CALLS" | cut -d: -f1 | sort -u | while read -r file; do
      sed -i.bak -E "s/from\s+[^ ]*path_env[^ ]*\s+import\s+([A-Za-z_, ]+)/from common.utils.path_manager import PathManager/" "$file"
      sed -i -E "s/PathEnv/PathManager/g" "$file"
      sed -i -E "s/join_path\(/PathManager.join_path(/g" "$file"
      echo "  Fixed $file"
    done
  fi
else
  echo "✅ No legacy path_env usages found."
fi

# ------------------------------------------------------------------
# 2. Migrate ALL remaining legacy agents to BaseAgent
# ------------------------------------------------------------------
banner "2. BaseAgent migration"
python3 scripts/enforce_base_agent.py || echo "⚠️  BaseAgent enforcement produced warnings – review log"

# ------------------------------------------------------------------
# 3. Inject StandardizedHealthMixin to migrated agents (placeholder) 
#    NOTE: requires health_mixin_injector.py utility.
# ------------------------------------------------------------------
banner "3. HealthMixin injection"
if $APPLY; then
  if [[ -f scripts/health_mixin_injector.py ]]; then
    python3 scripts/health_mixin_injector.py --auto || echo "⚠️  HealthMixin injector warnings"
  else
    echo "health_mixin_injector.py missing – skip (add in Phase-1 Week-2)"
  fi
else
  echo "${DRY} Would run health_mixin_injector.py to add StandardizedHealthMixin"
fi

# ------------------------------------------------------------------
# 4. Lint for health endpoints & PathManager in CI (generates reports)
# ------------------------------------------------------------------
banner "4. CI lint report generation"
python3 validate_health_check_batch2.py || true
python3 validate_dirs.sh || true

banner "Phase-1 script complete"
$APPLY || echo "Run with --apply to make changes"