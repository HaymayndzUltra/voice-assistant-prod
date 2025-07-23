#!/usr/bin/env bash
# =============================================================================
# Phase-3  Dynamic Port Allocator & Rolling Upgrade (Weeks 8-12)
# -----------------------------------------------------------------------------
# • Introduce PortAllocator micro-service for dynamic port assignment.
# • Replace hard-coded ports (${PORT_OFFSET} macros) in both YAML configs.
# • Provide rolling-upgrade tooling (shadow traffic + weight) via ServiceRegistry.
# =============================================================================
set -euo pipefail
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"
APPLY=false; while [[ $# -gt 0 ]]; do case "$1" in --apply) APPLY=true; shift;; -h|--help) echo "Phase-3 script"; exit 0;; *) echo "unknown opt $1"; exit 1;; esac; done
DRY="[DRY-RUN]"; $APPLY && DRY=""

banner(){ echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n$1\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

# 1. Build / Launch PortAllocator micro-service (simple Flask placeholder)
banner "1. PortAllocator service"
PA_PORT=7555
if lsof -i :$PA_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "✅ PortAllocator already running on :$PA_PORT"
else
  if $APPLY; then
    python3 tools/port_allocator_service.py --port $PA_PORT &
    echo $! > port_allocator.pid
    echo "✅ Started PortAllocator (pid $(cat port_allocator.pid))"
  else
    echo "${DRY} Would start tools/port_allocator_service.py on :$PA_PORT"
  fi
fi

# 2. Macro-replace hard-coded ports with ${PORT_OFFSET}
banner "2. Replace hard-coded ports → macros"
for cfg in main_pc_code/config/startup_config.yaml pc2_code/config/startup_config.yaml; do
  if [[ -f "$cfg" ]]; then
    if grep -qE "port:\s*[5-9][0-9]{3}" "$cfg"; then
      if $APPLY; then
        sed -i.bak -E 's/port:\s*([5-9][0-9]{3})/port: "${PORT_OFFSET}+\1"/g' "$cfg"
        echo "  Patched $cfg"
      else
        echo "${DRY} Would patch $cfg to use \\${PORT_OFFSET} macros"
      fi
    fi
  fi
done

# 3. Rolling-upgrade helper script generation
banner "3. Generate rolling-upgrade helper (scripts/rolling_upgrade.sh)"
if $APPLY; then
  cat > scripts/rolling_upgrade.sh <<'EOF'
#!/usr/bin/env bash
# Rolling upgrade helper – shift traffic weight via ServiceRegistry
AGENT=$1; NEW_VER=$2; WEIGHT=${3:-10}
if [[ -z "$AGENT" || -z "$NEW_VER" ]]; then echo "Usage: $0 <agent> <new_ver> [weight]"; exit 1; fi
curl -X POST "http://$(common/config_manager.py get_service_ip service_registry):7001/shift_weight" \
     -d "agent=$AGENT&new=$NEW_VER&weight=$WEIGHT"
echo "✅ Shifted $WEIGHT% traffic of $AGENT → $NEW_VER"
EOF
  chmod +x scripts/rolling_upgrade.sh
  echo "  Created scripts/rolling_upgrade.sh"
else
  echo "${DRY} Would create scripts/rolling_upgrade.sh"
fi

banner "Phase-3 script complete"
$APPLY || echo "Run with --apply to mutate configs & generate tools"