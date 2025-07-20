#!/bin/bash
# PC2 Docker Environment Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="pc2_code/docker/docker-compose.yml"
PROJECT_NAME="pc2-agents"
MAINPC_BRIDGE="mainpc_bridge"

echo -e "${GREEN}Starting PC2 Docker Environment...${NC}"

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
}

# Function to create external network if it doesn't exist
create_external_network() {
    if ! docker network inspect $MAINPC_BRIDGE > /dev/null 2>&1; then
        echo -e "${YELLOW}Creating external network: $MAINPC_BRIDGE${NC}"
        docker network create --driver bridge \
            --subnet=172.20.0.0/16 \
            --gateway=172.20.0.1 \
            $MAINPC_BRIDGE
    else
        echo -e "${GREEN}External network $MAINPC_BRIDGE already exists${NC}"
    fi
}

# Function to build base image
build_base_image() {
    echo -e "${YELLOW}Building PC2 base Docker image...${NC}"
    docker build -t pc2_code/docker:latest -f pc2_code/docker/Dockerfile .
}

# Function to check and create required directories
create_directories() {
    echo -e "${YELLOW}Creating required directories...${NC}"
    mkdir -p pc2_code/logs
    mkdir -p pc2_code/data
    mkdir -p pc2_code/models
    mkdir -p pc2_code/cache
}

# Function to start services in dependency order
start_services() {
    echo -e "${GREEN}Starting PC2 services...${NC}"
    
    # Start infrastructure services first
    echo -e "${YELLOW}Starting infrastructure services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d redis observability-hub
    
    # Wait for Redis to be ready
    echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
    until docker exec pc2-redis redis-cli ping > /dev/null 2>&1; do
        sleep 1
    done
    echo -e "${GREEN}Redis is ready${NC}"
    
    # Start core services
    echo -e "${YELLOW}Starting core services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d \
        memory-orchestrator \
        resource-manager
    
    # Wait for core services to be healthy
    sleep 10
    
    # Start dependent services
    echo -e "${YELLOW}Starting dependent services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d \
        cache-manager \
        context-manager \
        unified-utils \
        task-scheduler \
        async-processor
    
    # Wait for dependent services
    sleep 10
    
    # Start remaining services
    echo -e "${YELLOW}Starting remaining services...${NC}"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d
}

# Function to check service health
check_health() {
    echo -e "${YELLOW}Checking service health...${NC}"
    
    # Get list of running containers
    containers=$(docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps -q)
    
    all_healthy=true
    for container in $containers; do
        container_name=$(docker inspect -f '{{.Name}}' $container | sed 's/\///')
        health_status=$(docker inspect -f '{{.State.Health.Status}}' $container 2>/dev/null || echo "none")
        
        if [ "$health_status" = "healthy" ]; then
            echo -e "${GREEN}✓ $container_name: healthy${NC}"
        elif [ "$health_status" = "none" ]; then
            echo -e "${YELLOW}○ $container_name: no health check${NC}"
        else
            echo -e "${RED}✗ $container_name: $health_status${NC}"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        echo -e "${GREEN}All services are healthy!${NC}"
    else
        echo -e "${YELLOW}Some services are not healthy yet. They may still be starting up.${NC}"
    fi
}

# Function to show service URLs
show_urls() {
    echo -e "\n${GREEN}PC2 Service URLs:${NC}"
    echo "Memory Orchestrator:     http://localhost:7140 (health: http://localhost:8140/health)"
    echo "Tiered Responder:        http://localhost:7100 (health: http://localhost:8100/health)"
    echo "Remote Connector:        http://localhost:7124 (health: http://localhost:8124/health)"
    echo "Observability Hub:       http://localhost:9000 (health: http://localhost:9100/health)"
    echo "Advanced Router:         http://localhost:7129 (health: http://localhost:8129/health)"
}

# Main execution
main() {
    echo -e "${GREEN}=== PC2 Docker Environment Startup ===${NC}\n"
    
    # Check prerequisites
    check_docker
    
    # Create required infrastructure
    create_external_network
    create_directories
    
    # Build and start services
    build_base_image
    start_services
    
    # Wait for services to stabilize
    echo -e "${YELLOW}Waiting for services to stabilize...${NC}"
    sleep 20
    
    # Check health and show status
    check_health
    show_urls
    
    echo -e "\n${GREEN}PC2 Docker environment is ready!${NC}"
    echo -e "${YELLOW}Use 'docker-compose -f $COMPOSE_FILE logs -f' to view logs${NC}"
    echo -e "${YELLOW}Use './stop_pc2_docker.sh' to stop all services${NC}"
}

# Run main function
main