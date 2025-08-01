#!/usr/bin/env bash
# AI System Deployment and Testing Script
# Covers Phases 4-6 of the remediation plan

set -euo pipefail

echo "=== AI System Deployment and Testing Script ==="
echo "Starting at: $(date)"

# Phase 4: Compose Validation
echo ""
echo "=== PHASE 4: Compose Validation ==="

echo "Linting MainPC compose file..."
docker compose -f main_pc_code/config/docker-compose.yml config --quiet
if [ $? -eq 0 ]; then
    echo "✅ MainPC compose file valid"
else
    echo "❌ MainPC compose file validation failed"
    exit 1
fi

echo "Linting PC2 compose file..."
docker compose -f pc2_code/config/docker-compose.yml config --quiet
if [ $? -eq 0 ]; then
    echo "✅ PC2 compose file valid"
else
    echo "❌ PC2 compose file validation failed"
    exit 1
fi

echo "Performing dry-run Swarm conversion..."
docker stack deploy --compose-file main_pc_code/config/docker-compose.yml dummy --dry-run
echo "✅ Swarm conversion test passed"

# Security scan (optional, may require additional tools)
echo ""
echo "Security scanning images..."
if command -v trivy &> /dev/null; then
    trivy image ai_system/mainpc_stack:latest
    trivy image ai_system/pc2_stack:latest
else
    echo "⚠️  Trivy not installed, skipping security scan"
    echo "   Install with: sudo apt-get install trivy"
fi

# Phase 5: Deploy, Health & Monitoring
echo ""
echo "=== PHASE 5: Deploy, Health & Monitoring ==="

echo "Deploying MainPC stack..."
docker compose -f main_pc_code/config/docker-compose.yml up -d
if [ $? -eq 0 ]; then
    echo "✅ MainPC stack deployed"
else
    echo "❌ MainPC stack deployment failed"
    exit 1
fi

echo "Deploying PC2 stack..."
docker compose -f pc2_code/config/docker-compose.yml up -d
if [ $? -eq 0 ]; then
    echo "✅ PC2 stack deployed"
else
    echo "❌ PC2 stack deployment failed"
    exit 1
fi

# Wait for services to start
echo "Waiting 30 seconds for services to initialize..."
sleep 30

# Check Prometheus targets
echo ""
echo "Checking Prometheus scrape targets..."
curl -s http://localhost:9000/metrics > /dev/null 2>&1 && echo "✅ MainPC metrics endpoint active" || echo "⚠️  MainPC metrics endpoint not responding"
curl -s http://localhost:9100/metrics > /dev/null 2>&1 && echo "✅ PC2 metrics endpoint active" || echo "⚠️  PC2 metrics endpoint not responding"

# Check GPU allocation
echo ""
echo "Checking GPU allocation..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
else
    echo "⚠️  nvidia-smi not available, cannot verify GPU allocation"
fi

# Phase 6: Load Testing & Smoke Tests
echo ""
echo "=== PHASE 6: Load Testing & Smoke Tests ==="

# Check if test scripts exist
if [ -f "/workspace/main_pc_code/tests/load/generate_requests.py" ]; then
    echo "Running load tests..."
    python3 /workspace/main_pc_code/tests/load/generate_requests.py --duration 300 --qps 25 &
    LOAD_PID=$!
    
    # Monitor GPU during load test
    echo "Monitoring GPU usage during load test..."
    for i in {1..10}; do
        sleep 30
        echo "GPU Status at $(date):"
        nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total --format=csv || echo "GPU monitoring unavailable"
    done
    
    # Wait for load test to complete
    wait $LOAD_PID
    echo "✅ Load test completed"
else
    echo "⚠️  Load test script not found at expected location"
fi

# Run smoke tests
if [ -f "/workspace/main_pc_code/scripts/smoke_test_agents.py" ]; then
    echo ""
    echo "Running smoke tests..."
    python3 /workspace/main_pc_code/scripts/smoke_test_agents.py --target pc2
    if [ $? -eq 0 ]; then
        echo "✅ Smoke tests passed"
    else
        echo "❌ Smoke tests failed"
    fi
else
    echo "⚠️  Smoke test script not found at expected location"
fi

echo ""
echo "=== Deployment and Testing Complete ==="
echo "Completed at: $(date)"
echo "Next steps: Run security_hardening.sh for Phase 7"