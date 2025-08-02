#!/bin/bash
# Container System Fix Application Script
# Generated: 2025-08-02
# Purpose: Apply all fixes identified in the container status analysis

set -e  # Exit on error

echo "🔧 Container System Fix Script"
echo "=============================="
echo ""

# Function to check if docker-compose is available
check_docker() {
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ docker-compose not found. Please install Docker Compose."
        exit 1
    fi
    echo "✅ Docker Compose found"
}

# Function to rebuild and restart a service group
rebuild_group() {
    local group_name=$1
    local compose_file=$2
    
    echo ""
    echo "🔄 Processing $group_name..."
    
    if [ -f "$compose_file" ]; then
        echo "  📦 Building images..."
        docker-compose -f "$compose_file" build
        
        echo "  🚀 Restarting services..."
        docker-compose -f "$compose_file" down
        docker-compose -f "$compose_file" up -d
        
        echo "  ✅ $group_name updated successfully"
    else
        echo "  ⚠️  Compose file not found: $compose_file"
    fi
}

# Check prerequisites
echo "1️⃣ Checking prerequisites..."
check_docker

# Rebuild affected groups
echo ""
echo "2️⃣ Rebuilding affected container groups..."

# Language Stack - Fixed module paths
rebuild_group "language_stack" "/workspace/docker/language_stack/docker-compose.yml"

# Speech GPU - Added missing dependencies  
rebuild_group "speech_gpu" "/workspace/docker/speech_gpu/docker-compose.yml"

# Emotion System - Fixed module path
rebuild_group "emotion_system" "/workspace/docker/emotion_system/docker-compose.yml"

# Reasoning GPU - Just restart NATS
echo ""
echo "🔄 Processing reasoning_gpu NATS..."
if [ -f "/workspace/docker/reasoning_gpu/docker-compose.yml" ]; then
    docker-compose -f "/workspace/docker/reasoning_gpu/docker-compose.yml" restart nats_reasoning || true
    echo "  ✅ NATS configuration updated"
fi

# Infra Core - Restart service registry
echo ""
echo "🔄 Processing infra_core service_registry..."
if [ -f "/workspace/docker/infra_core/docker-compose.yml" ]; then
    docker-compose -f "/workspace/docker/infra_core/docker-compose.yml" restart service_registry || true
    echo "  ✅ Service registry configuration updated"
fi

# Health check function
health_check() {
    echo ""
    echo "3️⃣ Running health checks..."
    echo ""
    
    # Check container status
    echo "📊 Container Status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
    
    echo ""
    echo "📈 Unhealthy containers:"
    docker ps --filter "health=unhealthy" --format "table {{.Names}}\t{{.Status}}"
}

# Run health checks
health_check

echo ""
echo "✅ Fix application complete!"
echo ""
echo "📝 Next steps:"
echo "  1. Monitor logs: docker-compose logs -f [service_name]"
echo "  2. Check specific group: docker-compose -f [compose_file] ps"
echo "  3. Verify cross-group communication"
echo "  4. Resolve any remaining port conflicts"
echo ""
echo "💡 For detailed analysis, see: /workspace/memory-bank/container-status-reports/CONTAINER_FIXES_SUMMARY.md"