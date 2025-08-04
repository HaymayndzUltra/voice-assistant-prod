#!/usr/bin/env bash
# 🚀 PC2 DOCKER IMAGES TRANSFER SCRIPT
# Build locally, transfer to PC2 machine

set -euo pipefail

PC2_HOST=${1:-"pc2.local"}
TRANSFER_MODE=${2:-"compressed"}  # compressed, registry, direct

echo "🚀 PC2 IMAGES TRANSFER TO $PC2_HOST"
echo "======================================="
echo "Transfer Mode: $TRANSFER_MODE"

# PC2 Services to transfer
PC2_SERVICES=(
    "ai_system_monorepo-pc2-infra-core"
    "ai_system_monorepo-pc2-memory-stack" 
    "ai_system_monorepo-pc2-async-pipeline"
    "ai_system_monorepo-pc2-tutoring-cpu"
    "ai_system_monorepo-pc2-vision-dream-gpu"
    "ai_system_monorepo-pc2-utility-suite"
    "ai_system_monorepo-pc2-web-interface"
)

case "$TRANSFER_MODE" in
    "compressed")
        echo "📦 COMPRESSED TRANSFER MODE"
        echo "=========================="
        
        # Create transfer directory
        mkdir -p pc2_images_transfer
        cd pc2_images_transfer
        
        # Save and compress each image
        for service in "${PC2_SERVICES[@]}"; do
            echo "💾 Saving $service..."
            if docker image inspect "$service:latest" >/dev/null 2>&1; then
                docker save "$service:latest" | gzip > "${service##*-}.tar.gz"
                echo "✅ Compressed: ${service##*-}.tar.gz"
            else
                echo "⚠️  Image not found: $service"
            fi
        done
        
        # Transfer all compressed images
        echo "📤 Transferring to $PC2_HOST..."
        scp *.tar.gz "$PC2_HOST:~/"
        
        # Load images on PC2
        echo "📥 Loading images on $PC2_HOST..."
        for service in "${PC2_SERVICES[@]}"; do
            image_file="${service##*-}.tar.gz"
            if [ -f "$image_file" ]; then
                echo "Loading $image_file on PC2..."
                ssh "$PC2_HOST" "docker load < ~/$image_file"
                ssh "$PC2_HOST" "rm ~/$image_file"  # Cleanup
            fi
        done
        
        cd ..
        rm -rf pc2_images_transfer
        ;;
        
    "registry")
        echo "🏪 REGISTRY TRANSFER MODE"
        echo "======================="
        
        # Setup local registry if not exists
        if ! docker container inspect registry >/dev/null 2>&1; then
            echo "🏪 Starting local Docker registry..."
            docker run -d -p 5000:5000 --name registry registry:2
            sleep 5
        fi
        
        REGISTRY="$(hostname -I | awk '{print $1}'):5000"
        
        # Tag and push to local registry
        for service in "${PC2_SERVICES[@]}"; do
            if docker image inspect "$service:latest" >/dev/null 2>&1; then
                echo "📤 Pushing $service to registry..."
                docker tag "$service:latest" "$REGISTRY/${service##*-}:latest"
                docker push "$REGISTRY/${service##*-}:latest"
            fi
        done
        
        # Pull from PC2
        for service in "${PC2_SERVICES[@]}"; do
            echo "📥 Pulling ${service##*-} on PC2..."
            ssh "$PC2_HOST" "docker pull $REGISTRY/${service##*-}:latest"
            ssh "$PC2_HOST" "docker tag $REGISTRY/${service##*-}:latest $service:latest"
        done
        ;;
        
    "direct")
        echo "🔄 DIRECT TRANSFER MODE (via SSH)"
        echo "==============================="
        
        for service in "${PC2_SERVICES[@]}"; do
            if docker image inspect "$service:latest" >/dev/null 2>&1; then
                echo "📤 Direct transfer: $service"
                docker save "$service:latest" | ssh "$PC2_HOST" "docker load"
                echo "✅ Transferred: $service"
            fi
        done
        ;;
        
    *)
        echo "❌ Unknown transfer mode: $TRANSFER_MODE"
        echo "Valid modes: compressed, registry, direct"
        exit 1
        ;;
esac

# Verify images on PC2
echo ""
echo "✅ VERIFICATION"
echo "==============="
echo "PC2 Images:"
ssh "$PC2_HOST" "docker images | grep pc2"

echo ""
echo "🎉 PC2 IMAGES TRANSFER COMPLETED!"
echo "================================="
echo "Next steps:"
echo "1. ssh $PC2_HOST"
echo "2. cd AI_System_Monorepo"  
echo "3. docker-compose -f docker-compose.pc2-local.yml up -d"
