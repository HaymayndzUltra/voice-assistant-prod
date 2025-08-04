#!/usr/bin/env bash
set -euo pipefail
HOST=${MAINPC_HOST:-"mainpc.local"}
for port in 51100 51200 51300 51400 51500 51600 51700 51800 51900 52000 52100; do
  nc -z -w2 "$HOST" "$port" || { echo "UNREACHABLE $HOST:$port"; exit 1; }
done
echo "Main-PC ports reachable from $(hostname)"
