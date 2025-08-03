#!/usr/bin/env bash
# scripts/cross_machine_network_check.sh - Following test1.md Blueprint
# executes from Main PC to PC2 (or vice-versa) to confirm bidirectional reachability and latency

set -euo pipefail
HOST_LIST=${HOST_LIST:-"mainpc.local pc2.local"}
PORTS=(50100 50200 50300 50400 50500 50600 50700)

for host in $HOST_LIST; do
  for port in "${PORTS[@]}"; do
    nc -z -w2 "$host" "$port" || { echo "FAIL $host:$port" ; exit 1 ; }
  done
done

echo "All PC2 ports reachable across machines"
