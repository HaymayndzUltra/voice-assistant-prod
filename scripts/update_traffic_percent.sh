#!/bin/bash
# scripts/update_traffic_percent.sh
# Update traffic percentage for canary rollout

if [ $# -ne 1 ]; then
    echo "Usage: $0 <percentage>"
    echo "Example: $0 25"
    exit 1
fi

PERCENT=$1

# Validate percentage
if [ "$PERCENT" -lt 0 ] || [ "$PERCENT" -gt 100 ]; then
    echo "Error: Percentage must be between 0-100"
    exit 1
fi

echo "Setting ModelManagerSuite traffic to ${PERCENT}%..."

# Update environment variable and restart router
export SUITE_TRAFFIC_PERCENT=$PERCENT
docker compose -f docker/docker-compose.router.yml restart mm-router

echo "Traffic percentage updated to ${PERCENT}%"
echo "Check logs: docker logs -f mm-router"