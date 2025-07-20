#!/bin/bash

# PC2 Docker Images Build Script
# Builds all PC2 agent Docker images in dependency order

set -e

echo "🚀 Building PC2 Docker Images..."

# Change to the project root directory
cd "$(dirname "$0")/../.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

build_image() {
    local dockerfile=$1
    local tag=$2
    local name=$3
    
    echo -e "${BLUE}📦 Building $name ($tag)...${NC}"
    
    if docker build -f "$dockerfile" -t "$tag" .; then
        echo -e "${GREEN}✅ Successfully built $name${NC}"
    else
        echo -e "${RED}❌ Failed to build $name${NC}"
        exit 1
    fi
}

# Build base image first (all others depend on it)
build_image "pc2_code/docker/Dockerfile.pc2-base" "pc2-base:latest" "PC2 Base Image"

# Build specialized images
build_image "pc2_code/docker/Dockerfile.pc2-vision" "pc2-vision:latest" "PC2 Vision Processing Image"
build_image "pc2_code/docker/Dockerfile.pc2-web" "pc2-web:latest" "PC2 Web Agent Image"
build_image "pc2_code/docker/Dockerfile.pc2-monitoring" "pc2-monitoring:latest" "PC2 Monitoring Image"

echo -e "${GREEN}🎉 All PC2 Docker images built successfully!${NC}"

# List built images
echo -e "${YELLOW}📋 Built images:${NC}"
docker images | grep "pc2-" | head -10

# Show total size
echo -e "${YELLOW}📊 Total size of PC2 images:${NC}"
docker images | grep "pc2-" | awk '{sum += $NF} END {print sum " MB (approximate)"}'

echo -e "${BLUE}💡 To start all services: docker-compose -f pc2_code/docker-compose.pc2.yml up -d${NC}"
echo -e "${BLUE}💡 To view logs: docker-compose -f pc2_code/docker-compose.pc2.yml logs -f${NC}"
echo -e "${BLUE}💡 To stop all services: docker-compose -f pc2_code/docker-compose.pc2.yml down${NC}" 