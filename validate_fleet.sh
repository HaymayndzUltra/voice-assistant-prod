#!/usr/bin/env bash
# Fleet validation script - checks health, CUDA, and UID compliance
set -euo pipefail

FAIL=0

echo "================================================"
echo "🔍 VALIDATING DOCKER FLEET COMPLIANCE"
echo "================================================"

for cid in $(docker ps -q); do
  name=$(docker inspect -f '{{.Name}}' "$cid" | cut -c2-)
  
  # Get IP address (handle different network modes)
  ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$cid")
  if [ -z "$ip" ]; then
    # For host network mode
    ip="localhost"
  fi
  
  # Get health check port from labels or use default
  port=$(docker inspect -f '{{(index .Config.Labels "health_check_port")}}' "$cid" 2>/dev/null || echo "")
  
  # If no label, try to extract from EXPOSE
  if [ -z "$port" ]; then
    port=$(docker inspect "$cid" | grep -oP '"ExposedPorts".*?"(\d{4})/tcp"' | grep -oP '\d{4}' | tail -1)
  fi
  
  echo ""
  echo "Checking: $name"
  echo "  IP: $ip, Port: $port"
  
  # 1. /health endpoint check
  if [ ! -z "$port" ]; then
    if curl -sf "http://${ip}:${port}/health" >/dev/null 2>&1; then
      echo "  ✅ /health endpoint OK"
    else
      echo "  ❌ ${name}: /health failed on port $port"
      FAIL=1
    fi
  else
    echo "  ⚠️  No health port found"
  fi
  
  # 2. CUDA runtime check (skip for CPU images)
  if docker exec "$cid" test -f /usr/local/cuda/version.txt 2>/dev/null; then
    cuda=$(docker exec "$cid" cat /usr/local/cuda/version.txt 2>/dev/null | grep -oP 'CUDA Version \K[\d.]+' || echo "unknown")
    if [[ "$cuda" == "12.1"* ]]; then
      echo "  ✅ CUDA $cuda OK"
    else
      echo "  ❌ ${name}: CUDA $cuda ≠ 12.1"
      FAIL=1
    fi
  else
    echo "  ℹ️  CPU-only container (no CUDA)"
  fi
  
  # 3. Non-root enforcement
  uid=$(docker exec "$cid" id -u 2>/dev/null || echo "unknown")
  if [[ "$uid" == "10001" ]]; then
    echo "  ✅ Running as UID 10001 (appuser)"
  else
    echo "  ❌ ${name}: running as UID $uid (should be 10001)"
    FAIL=1
  fi
done

echo ""
echo "================================================"
if [ $FAIL -eq 0 ]; then
  echo "✅ ALL CHECKS PASSED!"
else
  echo "❌ VALIDATION FAILED!"
fi
echo "================================================"

exit $FAIL