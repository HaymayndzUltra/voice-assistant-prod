#!/usr/bin/env bash
# Quick functional test for a single container group inside the dev stack.
set -euo pipefail
GROUP=${1:-}
if [[ -z "$GROUP" ]]; then
  echo "Usage: $0 <group-name>" >&2
  exit 1
fi

# Ensure dev stack is up (but don't recreate if already running)
docker compose -f docker/docker-compose.dev.yml up -d $GROUP redis

# Allow services to boot
sleep 10

echo "▶ Running health check for $GROUP …"
docker compose -f docker/docker-compose.dev.yml exec -T $GROUP \
  python tools/healthcheck_all_services.py || {
    echo "❌ Health check failed for $GROUP" >&2
    exit 1
  }

echo "✅ $GROUP is healthy"