#!/bin/bash
set -e
for d in docker/*/ ; do
  if [ -f "$d/docker-compose.yml" ]; then
    echo "===== Building and starting $d ====="
    (cd "$d" && docker-compose up -d --build)
    sleep 8
    services=$(cd "$d" && docker-compose ps --services)
    for svc in $services; do
      echo "===== Running tests in $svc ====="
      (cd "$d" && docker-compose exec $svc pytest || true)
      echo "===== Logs for $svc ====="
      (cd "$d" && docker-compose logs $svc --tail=50)
    done
  fi
done
