#!/usr/bin/env bash
# Usage: ./scripts/update_traffic_percent.sh 25   # route 25 % to suite

set -euo pipefail

PERCENT=${1:-5}
if [[ $PERCENT -lt 0 || $PERCENT -gt 100 ]]; then
    echo "Percentage must be between 0 and 100" >&2
    exit 1
fi

echo "Updating SUITE_TRAFFIC_PERCENT to $PERCENT on mm-router container…"
docker container update --env-add SUITE_TRAFFIC_PERCENT=$PERCENT mm-router

echo "Restarting mm-router to apply changes…"
docker restart mm-router