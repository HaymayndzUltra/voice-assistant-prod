#!/usr/bin/env bash
set -euo pipefail
COMPOSE="docker compose -f docker/docker-compose.mainpc.yml"

echo "⏳  Waiting 20 s para makapag-spin-up ang lahat ng containers…"
sleep 20

echo "📋  === CONTAINER STATUS ==="
$COMPOSE ps --all

echo "📋  === HEALTH DETAILS ==="
for c in $($COMPOSE ps --format '{{.Name}}'); do
    echo -e "\n🔸 $c -------------"
    docker inspect --format '{{json .State.Health}}' "$c" 2>/dev/null || echo "No HC defined"
done

echo -e "\n📋  === LAST 150 LOG LINES (only for unhealthy / exited) ==="
for c in $($COMPOSE ps --filter 'health=unhealthy' --filter 'status=exited' --format '{{.Name}}'); do
    echo -e "\n🔸 $c -------------"
    docker logs --tail 150 "$c" || true
done

echo -e "\n📋  === CURL CHECKS ON HEALTH ENDPOINTS ==="
while read -r line; do
    cname=$(echo "$line" | cut -d':' -f1)
    hostport=$(echo "$line" | cut -d':' -f2)
    echo -e "\n🔸 $cname → http://localhost:$hostport/health"
    curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:$hostport/health" || true
done <<'MAP'
core-services:8220
core-services:8211
gpu-infrastructure:5575
gpu-infrastructure:5570
memory-system:5713
utility-services:5650
reasoning-services:6612
language-processing:8213
speech-services:6800
audio-interface:7553
emotion-system:6590
vision-processing:6610
MAP
