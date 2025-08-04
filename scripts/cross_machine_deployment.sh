#!/usr/bin/env bash
# 🚀 CROSS-MACHINE DEPLOYMENT SCRIPT
# Usage: ./cross_machine_deployment.sh [PC2_HOST] [DEPLOY_MODE]

set -euo pipefail

# Configuration
PC2_HOST=${1:-"pc2.local"}
DEPLOY_MODE=${2:-"full"}  # full, infrastructure, apps
MAIN_PC_HOST=${MAIN_PC_HOST:-"mainpc.local"}

echo "🚀 CROSS-MACHINE DEPLOYMENT TO PC2"
echo "========================================"
echo "PC2 Host: $PC2_HOST"
echo "Deploy Mode: $DEPLOY_MODE"
echo "Main PC Host: $MAIN_PC_HOST"

# STEP 1: Network Connectivity Validation
echo ""
echo "🔍 STEP 1: NETWORK CONNECTIVITY VALIDATION"
echo "=============================================="

# Test PC2 reachability
if ! ping -c 2 "$PC2_HOST" > /dev/null 2>&1; then
    echo "❌ PC2 host $PC2_HOST not reachable"
    exit 1
fi
echo "✅ PC2 host $PC2_HOST reachable"

# Test SSH connectivity
if ! ssh -o ConnectTimeout=5 "$PC2_HOST" "echo 'SSH connected'" > /dev/null 2>&1; then
    echo "❌ SSH connection to $PC2_HOST failed"
    echo "💡 Setup: ssh-copy-id $PC2_HOST"
    exit 1
fi
echo "✅ SSH connection to $PC2_HOST working"

# STEP 2: Environment Preparation
echo ""
echo "📦 STEP 2: ENVIRONMENT PREPARATION"
echo "=================================="

# Create deployment directory on PC2
ssh "$PC2_HOST" "mkdir -p ~/AI_System_Monorepo"
echo "✅ Deployment directory created on PC2"

# Transfer deployment package
echo "📤 Transferring deployment package..."
scp ai_system_deployment.tar.gz "$PC2_HOST:~/AI_System_Monorepo/"
ssh "$PC2_HOST" "cd ~/AI_System_Monorepo && tar -xzf ai_system_deployment.tar.gz"
echo "✅ Deployment package transferred and extracted"

# STEP 3: Docker Environment Setup
echo ""
echo "🐳 STEP 3: DOCKER ENVIRONMENT SETUP"
echo "===================================="

# Verify Docker on PC2
if ! ssh "$PC2_HOST" "docker --version" > /dev/null 2>&1; then
    echo "❌ Docker not available on PC2"
    exit 1
fi
echo "✅ Docker available on PC2"

# Verify Docker Compose
if ! ssh "$PC2_HOST" "docker compose version" > /dev/null 2>&1; then
    echo "❌ Docker Compose not available on PC2"
    exit 1
fi
echo "✅ Docker Compose available on PC2"

# Check GPU availability (for vision services)
if ssh "$PC2_HOST" "nvidia-smi" > /dev/null 2>&1; then
    echo "✅ NVIDIA GPU available on PC2"
else
    echo "⚠️  NVIDIA GPU not detected on PC2 (vision services may fail)"
fi

# STEP 4: Port Availability Check
echo ""
echo "🔌 STEP 4: PORT AVAILABILITY CHECK"
echo "=================================="

PC2_PORTS=(6390 6391 6392 6393 6394 6395 6396 4300 4301 4302 4303 4304 4305 4306 9200 9210)

for port in "${PC2_PORTS[@]}"; do
    if ssh "$PC2_HOST" "netstat -tuln | grep :$port" > /dev/null 2>&1; then
        echo "⚠️  Port $port already in use on PC2"
    else
        echo "✅ Port $port available on PC2"
    fi
done

# STEP 5: Environment Variable Setup
echo ""
echo "🔧 STEP 5: ENVIRONMENT VARIABLE SETUP"
echo "====================================="

# Copy environment files
scp .env.production "$PC2_HOST:~/AI_System_Monorepo/.env"
scp .env.secrets.production "$PC2_HOST:~/AI_System_Monorepo/.env.secrets"

# Update Main PC host references
ssh "$PC2_HOST" "cd ~/AI_System_Monorepo && sed -i 's/localhost/$MAIN_PC_HOST/g' .env"
echo "✅ Environment variables configured for cross-machine setup"

# STEP 6: Deploy PC2 Services
echo ""
echo "🚀 STEP 6: DEPLOY PC2 SERVICES"
echo "=============================="

case "$DEPLOY_MODE" in
    "infrastructure")
        echo "📡 Deploying PC2 infrastructure only..."
        ssh "$PC2_HOST" "cd ~/AI_System_Monorepo && docker compose -f docker-compose.pc2-local.yml up -d redis_pc2_infra redis_pc2_memory redis_pc2_async redis_pc2_tutoring redis_pc2_vision redis_pc2_utility redis_pc2_web nats_pc2_infra nats_pc2_memory nats_pc2_async nats_pc2_tutoring nats_pc2_vision nats_pc2_utility nats_pc2_web"
        ;;
    "apps")
        echo "🤖 Deploying PC2 applications..."
        ssh "$PC2_HOST" "cd ~/AI_System_Monorepo && docker compose -f docker-compose.pc2-local.yml up -d"
        ;;
    "full")
        echo "🎯 Full PC2 deployment..."
        ssh "$PC2_HOST" "cd ~/AI_System_Monorepo && docker compose -f docker-compose.pc2-local.yml up -d"
        ;;
    *)
        echo "❌ Unknown deploy mode: $DEPLOY_MODE"
        exit 1
        ;;
esac

# STEP 7: Validation
echo ""
echo "✅ STEP 7: DEPLOYMENT VALIDATION"
echo "==============================="

# Wait for services to start
echo "⏰ Waiting 30 seconds for services to initialize..."
sleep 30

# Test PC2 services
echo "🔍 Testing PC2 service accessibility..."
for port in 6390 6391 6392 6393 6394 6395 6396; do
    if nc -z -w2 "$PC2_HOST" "$port" 2>/dev/null; then
        echo "✅ PC2 Redis $port accessible"
    else
        echo "❌ PC2 Redis $port not accessible"
    fi
done

# Test ObservabilityHub
if nc -z -w2 "$PC2_HOST" 9200 2>/dev/null; then
    echo "✅ PC2 ObservabilityHub accessible"
else
    echo "❌ PC2 ObservabilityHub not accessible"
fi

echo ""
echo "🎉 CROSS-MACHINE DEPLOYMENT COMPLETED!"
echo "======================================"
echo "PC2 Host: $PC2_HOST"
echo "Main PC Host: $MAIN_PC_HOST"
echo "Next Step: Run integration validation from Main PC"
echo ""
echo "💡 Commands to run from Main PC:"
echo "python3 validate_mainpc_phase2_integration.py"
echo "python3 todo_manager.py done 20240521_mainpc_testing_blueprint 2"
