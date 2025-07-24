#!/usr/bin/env bash
# Rolling upgrade helper – shift traffic weight via ServiceRegistry
AGENT=$1; NEW_VER=$2; WEIGHT=${3:-10}
if [[ -z "$AGENT" || -z "$NEW_VER" ]]; then echo "Usage: $0 <agent> <new_ver> [weight]"; exit 1; fi
curl -X POST "http://$(common/config_manager.py get_service_ip service_registry):7001/shift_weight" \
     -d "agent=$AGENT&new=$NEW_VER&weight=$WEIGHT"
echo "✅ Shifted $WEIGHT% traffic of $AGENT → $NEW_VER"
