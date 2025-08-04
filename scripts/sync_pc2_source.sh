#!/bin/bash

# PC2 Source Code Sync to PC2 Machine
# Purpose: Sync PC2 source directories to PC2 machine for native building
# Usage: ./sync_pc2_source.sh [pc2_host]

set -euo pipefail

PC2_HOST=${1:-"pc2.local"}
PC2_USER=${PC2_USER:-"haymayndz"}
SYNC_BASE="/home/haymayndz/AI_System_Monorepo"

echo "🚀 PC2 SOURCE CODE SYNC TO PC2 MACHINE"
echo "======================================="
echo "📍 Target: ${PC2_USER}@${PC2_HOST}"
echo "⏰ Started: $(date '+%Y-%m-%d %H:%M:%S')"

# Create remote base directory
echo "📁 Creating remote directory structure..."
ssh "${PC2_USER}@${PC2_HOST}" "mkdir -p /home/haymayndz/AI_System_Monorepo/{docker,common,scripts,memory-bank}"

# Sync PC2 service directories
echo "🔄 Syncing PC2 service groups..."
PC2_SERVICES=(
    "docker/pc2_infra_core"
    "docker/pc2_memory_stack"
    "docker/pc2_async_pipeline" 
    "docker/pc2_tutoring_cpu"
    "docker/pc2_vision_dream_gpu"
    "docker/pc2_utility_suite"
    "docker/pc2_web_interface"
)

for service in "${PC2_SERVICES[@]}"; do
    echo "   📦 Syncing ${service}..."
    rsync -avz --progress "${SYNC_BASE}/${service}/" "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/${service}/"
done

# Sync common dependencies
echo "🔄 Syncing common modules..."
rsync -avz --progress "${SYNC_BASE}/common/" "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/common/"

# Sync PC2-specific code
echo "🔄 Syncing PC2 agent code..."
rsync -avz --progress "${SYNC_BASE}/pc2_code/" "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/pc2_code/"

# Sync configuration files
echo "🔄 Syncing configuration..."
rsync -avz --progress "${SYNC_BASE}/.env" "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/"
rsync -avz --progress "${SYNC_BASE}/.env.secrets" "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/"

# Sync deployment scripts
echo "🔄 Syncing deployment scripts..."
rsync -avz --progress "${SYNC_BASE}/scripts/validate_pc2_*.py" "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/scripts/"

# Create PC2-specific docker-compose
echo "🔄 Creating PC2 deployment compose..."
cat > /tmp/docker-compose.pc2-remote.yml << 'EOF'
version: "3.9"

networks:
  pc2_net:
    driver: bridge

services:
  # PC2 services will build and run natively on PC2 machine
  # This compose file is designed for remote PC2 machine deployment
  
  # Infrastructure services (Redis, NATS) per service group
  # Application services will be built locally on PC2 machine
  
  # Use: docker compose -f docker-compose.pc2-remote.yml up -d --build
  # This enables native PC2 machine building and true cross-machine integration
  
EOF

rsync -avz --progress /tmp/docker-compose.pc2-remote.yml "${PC2_USER}@${PC2_HOST}:/home/haymayndz/AI_System_Monorepo/"

echo "✅ PC2 source sync completed successfully!"
echo "🎯 Next steps:"
echo "   1. SSH to PC2 machine: ssh ${PC2_USER}@${PC2_HOST}"
echo "   2. Navigate to: cd /home/haymayndz/AI_System_Monorepo"
echo "   3. Build PC2 services: cd docker/pc2_infra_core && docker compose up -d --build"
echo "   4. Test cross-machine integration from Main PC"
echo ""
echo "📊 Sync completed: $(date '+%Y-%m-%d %H:%M:%S')"
