#!/bin/bash

# CASCADE Docker Deployment Script
# Manages deployment of MainPC and PC2 systems

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MAINPC_COMPOSE="${SCRIPT_DIR}/mainpc/docker-compose.yml"
PC2_COMPOSE="${SCRIPT_DIR}/pc2/docker-compose.yml"
ENV_FILE="${SCRIPT_DIR}/.env"

# Default values
CASCADE_VERSION=${CASCADE_VERSION:-"latest"}
DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-"production"}
PORT_OFFSET=${PORT_OFFSET:-0}

# Functions
print_header() {
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}CASCADE Docker Deployment Manager${NC}"
    echo -e "${GREEN}============================================${NC}"
}

print_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  deploy-mainpc    Deploy MainPC system"
    echo "  deploy-pc2       Deploy PC2 system"
    echo "  deploy-all       Deploy both systems"
    echo "  stop-mainpc      Stop MainPC system"
    echo "  stop-pc2         Stop PC2 system"
    echo "  stop-all         Stop both systems"
    echo "  status           Show system status"
    echo "  logs [service]   Show logs for service"
    echo "  health           Check health of all services"
    echo ""
    echo "Options:"
    echo "  --version        CASCADE version to deploy (default: latest)"
    echo "  --port-offset    Port offset for multiple deployments"
    echo "  --mode           Deployment mode (production/development)"
}

check_requirements() {
    echo -e "${YELLOW}Checking requirements...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed!${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed!${NC}"
        exit 1
    fi
    
    # Check NVIDIA Docker (for GPU support)
    if ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}Warning: NVIDIA Docker runtime not available. GPU features will be disabled.${NC}"
    fi
    
    echo -e "${GREEN}All requirements satisfied!${NC}"
}

create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}Creating environment file...${NC}"
        cat > "$ENV_FILE" << EOF
# CASCADE Docker Environment Configuration
CASCADE_VERSION=${CASCADE_VERSION}
PORT_OFFSET=${PORT_OFFSET}
LOG_LEVEL=INFO
DEPLOYMENT_MODE=${DEPLOYMENT_MODE}

# MainPC Configuration
MAINPC_HOST=mainpc
MAINPC_OBS_HUB=http://mainpc:9000

# PC2 Configuration
PC2_HOST=pc2

# Monitoring
GRAFANA_PASSWORD=cascade_admin

# Resource Limits
MAINPC_MEMORY_LIMIT=64G
PC2_MEMORY_LIMIT=32G
EOF
        echo -e "${GREEN}Environment file created!${NC}"
    else
        echo -e "${YELLOW}Using existing environment file${NC}"
    fi
}

deploy_mainpc() {
    echo -e "${GREEN}Deploying MainPC system...${NC}"
    
    # Build images
    echo "Building MainPC images..."
    docker-compose -f "$MAINPC_COMPOSE" build
    
    # Start services in order
    echo "Starting core platform services..."
    docker-compose -f "$MAINPC_COMPOSE" up -d service-registry
    sleep 10
    
    docker-compose -f "$MAINPC_COMPOSE" up -d system-digital-twin
    sleep 10
    
    docker-compose -f "$MAINPC_COMPOSE" up -d observability-hub unified-system-agent
    sleep 10
    
    echo "Starting AI engine services..."
    docker-compose -f "$MAINPC_COMPOSE" up -d model-manager-suite
    sleep 30  # Allow time for model loading
    
    docker-compose -f "$MAINPC_COMPOSE" up -d vram-optimizer model-orchestrator
    
    echo "Starting remaining services..."
    docker-compose -f "$MAINPC_COMPOSE" up -d
    
    echo -e "${GREEN}MainPC deployment complete!${NC}"
}

deploy_pc2() {
    echo -e "${GREEN}Deploying PC2 system...${NC}"
    
    # Build images
    echo "Building PC2 images..."
    docker-compose -f "$PC2_COMPOSE" build
    
    # Start core services
    echo "Starting PC2 core services..."
    docker-compose -f "$PC2_COMPOSE" up -d observability-hub-pc2 memory-orchestrator
    sleep 10
    
    docker-compose -f "$PC2_COMPOSE" up -d resource-manager
    sleep 5
    
    docker-compose -f "$PC2_COMPOSE" up -d async-processor cache-manager
    sleep 5
    
    echo "Starting PC2 application services..."
    docker-compose -f "$PC2_COMPOSE" up -d
    
    echo -e "${GREEN}PC2 deployment complete!${NC}"
}

stop_mainpc() {
    echo -e "${YELLOW}Stopping MainPC system...${NC}"
    docker-compose -f "$MAINPC_COMPOSE" down
    echo -e "${GREEN}MainPC stopped!${NC}"
}

stop_pc2() {
    echo -e "${YELLOW}Stopping PC2 system...${NC}"
    docker-compose -f "$PC2_COMPOSE" down
    echo -e "${GREEN}PC2 stopped!${NC}"
}

show_status() {
    echo -e "${GREEN}CASCADE System Status${NC}"
    echo ""
    
    echo "MainPC Services:"
    docker-compose -f "$MAINPC_COMPOSE" ps
    echo ""
    
    echo "PC2 Services:"
    docker-compose -f "$PC2_COMPOSE" ps
}

check_health() {
    echo -e "${GREEN}Checking service health...${NC}"
    
    # Function to check individual service health
    check_service_health() {
        local service=$1
        local health_port=$2
        local host=${3:-localhost}
        
        if curl -sf "http://${host}:${health_port}/health" > /dev/null; then
            echo -e "  ${service}: ${GREEN}HEALTHY${NC}"
        else
            echo -e "  ${service}: ${RED}UNHEALTHY${NC}"
        fi
    }
    
    echo "MainPC Health:"
    check_service_health "ServiceRegistry" 8200
    check_service_health "SystemDigitalTwin" 8220
    check_service_health "ObservabilityHub" 9001
    check_service_health "ModelManagerSuite" 8211
    
    echo ""
    echo "PC2 Health:"
    check_service_health "ObservabilityHub-PC2" 9110
    check_service_health "MemoryOrchestrator" 8140
    check_service_health "ResourceManager" 8113
}

show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        echo "Please specify a service name"
        exit 1
    fi
    
    # Try MainPC first
    if docker-compose -f "$MAINPC_COMPOSE" ps | grep -q "$service"; then
        docker-compose -f "$MAINPC_COMPOSE" logs -f "$service"
    # Then try PC2
    elif docker-compose -f "$PC2_COMPOSE" ps | grep -q "$service"; then
        docker-compose -f "$PC2_COMPOSE" logs -f "$service"
    else
        echo -e "${RED}Service '$service' not found${NC}"
        exit 1
    fi
}

# Main script
print_header

case "$1" in
    deploy-mainpc)
        check_requirements
        create_env_file
        deploy_mainpc
        ;;
    deploy-pc2)
        check_requirements
        create_env_file
        deploy_pc2
        ;;
    deploy-all)
        check_requirements
        create_env_file
        deploy_mainpc
        echo ""
        deploy_pc2
        ;;
    stop-mainpc)
        stop_mainpc
        ;;
    stop-pc2)
        stop_pc2
        ;;
    stop-all)
        stop_mainpc
        stop_pc2
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        print_usage
        exit 1
        ;;
esac