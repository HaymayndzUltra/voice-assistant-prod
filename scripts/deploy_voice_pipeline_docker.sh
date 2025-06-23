#!/bin/bash

# Voice Pipeline Docker Deployment Script
# This script builds and deploys the voice pipeline components in Docker

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
CERT_DIR="$PROJECT_ROOT/certificates"
LOG_DIR="$PROJECT_ROOT/logs"

echo -e "${GREEN}=== Voice Pipeline Docker Deployment ===${NC}"
echo "Project root: $PROJECT_ROOT"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating necessary directories...${NC}"
mkdir -p "$CERT_DIR" "$LOG_DIR"

# Generate requirements.txt if it doesn't exist
if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo -e "${YELLOW}Generating requirements.txt...${NC}"
    pip freeze > "$PROJECT_ROOT/requirements.txt"
fi

# Generate ZMQ certificates if they don't exist
if [ ! -f "$CERT_DIR/client.key_secret" ] || [ ! -f "$CERT_DIR/server.key_secret" ]; then
    echo -e "${YELLOW}Generating ZMQ certificates...${NC}"
    python "$PROJECT_ROOT/scripts/generate_zmq_certificates.py"
fi

# Build Docker images
echo -e "${YELLOW}Building Docker images...${NC}"
cd "$DOCKER_DIR"
docker-compose -f docker-compose.voice_pipeline.yml build

# Start the services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.voice_pipeline.yml up -d

# Check if services are running
echo -e "${YELLOW}Checking service status...${NC}"
docker-compose -f docker-compose.voice_pipeline.yml ps

# Show logs for the system digital twin
echo -e "${YELLOW}Showing logs for system-digital-twin...${NC}"
docker-compose -f docker-compose.voice_pipeline.yml logs system-digital-twin

echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo "To view logs: docker-compose -f $DOCKER_DIR/docker-compose.voice_pipeline.yml logs -f"
echo "To stop services: docker-compose -f $DOCKER_DIR/docker-compose.voice_pipeline.yml down" 