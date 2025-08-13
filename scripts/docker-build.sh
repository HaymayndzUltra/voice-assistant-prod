#!/bin/bash

# 🐳 Local Docker Build and Push Script
# Uses local environment variables for development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="ghcr.io"
IMAGE_NAME="haymayndzultra"
REPO_NAME=$(basename $(git rev-parse --show-toplevel))
FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}/${REPO_NAME}"

# Load local secrets if available
if [ -f ".cursor_secrets/ghcr.env" ]; then
    echo -e "${BLUE}🔐 Loading local GHCR token...${NC}"
    source ".cursor_secrets/ghcr.env"
elif [ -f ".env" ]; then
    echo -e "${BLUE}🔐 Loading .env file...${NC}"
    source ".env"
fi

# Check if token is available
if [ -z "${GHCR_NEW:-}" ]; then
    echo -e "${RED}❌ GHCR_NEW token not found!${NC}"
    echo "Please set GHCR_NEW environment variable or create .cursor_secrets/ghcr.env"
    exit 1
fi

echo -e "${GREEN}✅ GHCR token loaded successfully${NC}"

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  build          Build Docker image only"
    echo "  push           Build and push to GHCR"
    echo "  login          Login to GHCR only"
    echo "  clean          Clean up local images"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build       # Build image locally"
    echo "  $0 push        # Build and push to GHCR"
    echo "  $0 login       # Login to GHCR"
}

# Function to login to GHCR
login_ghcr() {
    echo -e "${BLUE}🔐 Logging in to GitHub Container Registry...${NC}"
    echo "${GHCR_NEW}" | docker login "${REGISTRY}" -u "${IMAGE_NAME}" --password-stdin
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Successfully logged in to GHCR${NC}"
    else
        echo -e "${RED}❌ Failed to login to GHCR${NC}"
        exit 1
    fi
}

# Function to build image
build_image() {
    local tag=${1:-latest}
    echo -e "${BLUE}🏗️ Building Docker image: ${FULL_IMAGE_NAME}:${tag}${NC}"
    
    docker build -t "${FULL_IMAGE_NAME}:${tag}" .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Image built successfully: ${FULL_IMAGE_NAME}:${tag}${NC}"
    else
        echo -e "${RED}❌ Failed to build image${NC}"
        exit 1
    fi
}

# Function to push image
push_image() {
    local tag=${1:-latest}
    echo -e "${BLUE}📤 Pushing image to GHCR: ${FULL_IMAGE_NAME}:${tag}${NC}"
    
    docker push "${FULL_IMAGE_NAME}:${tag}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Image pushed successfully: ${FULL_IMAGE_NAME}:${tag}${NC}"
        echo -e "${BLUE}🔗 View at: https://github.com/${IMAGE_NAME}/${REPO_NAME}/pkgs/container/${REPO_NAME}${NC}"
    else
        echo -e "${RED}❌ Failed to push image${NC}"
        exit 1
    fi
}

# Function to clean up
clean_images() {
    echo -e "${YELLOW}🧹 Cleaning up local images...${NC}"
    
    # Remove local images
    docker rmi "${FULL_IMAGE_NAME}:latest" 2>/dev/null || true
    docker rmi "${FULL_IMAGE_NAME}:$(git rev-parse --short HEAD)" 2>/dev/null || true
    
    # Clean up dangling images
    docker image prune -f
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main script logic
case "${1:-help}" in
    "build")
        build_image
        ;;
    "push")
        login_ghcr
        build_image
        push_image
        ;;
    "login")
        login_ghcr
        ;;
    "clean")
        clean_images
        ;;
    "help"|*)
        show_usage
        exit 0
        ;;
esac

echo -e "${GREEN}🎉 Operation completed successfully!${NC}"
