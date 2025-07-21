#!/bin/bash

# PC2 Docker Startup Script
# Based on pc2_code/config/startup_config.yaml validation

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.pc2.yml"
CONFIG_FILE="../pc2_code/config/startup_config.yaml"
NETWORK_NAME="ai_system_net"
SUBNET="172.21.0.0/16"
MAINPC_HOST="192.168.100.16"

echo -e "${BLUE}=== PC2 Docker Startup Script ===${NC}"
echo -e "${BLUE}Based on: ${CONFIG_FILE}${NC}"
echo -e "${BLUE}Network: ${NETWORK_NAME} (${SUBNET})${NC}"
echo -e "${BLUE}MainPC Host: ${MAINPC_HOST}${NC}"
echo ""

# Function to check if service is healthy
check_service_health() {
    local service_name=$1
    local port=$2
    local timeout=${3:-30}
    
    echo -e "${YELLOW}Checking health of ${service_name} on port ${port}...${NC}"
    
    for i in $(seq 1 $timeout); do
        if docker exec ${service_name} python -c "
import zmq
import json
import sys
try:
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect('tcp://localhost:${port}')
    socket.setsockopt(zmq.RCVTIMEO, 5000)
    socket.send_json({'action': 'health_check'})
    response = socket.recv_json()
    print('Health check response:', response)
    sys.exit(0 if response.get('status') in ['ok', 'healthy'] else 1)
except Exception as e:
    print('Health check failed:', e)
    sys.exit(1)
" 2>/dev/null; then
            echo -e "${GREEN}✓ ${service_name} is healthy${NC}"
            return 0
        fi
        echo -e "${YELLOW}  Attempt ${i}/${timeout} - waiting...${NC}"
        sleep 2
    done
    
    echo -e "${RED}✗ ${service_name} health check failed after ${timeout} attempts${NC}"
    return 1
}

# Function to wait for service group
wait_for_group() {
    local group_name=$1
    shift
    local services=("$@")
    
    echo -e "${BLUE}=== Waiting for ${group_name} group ===${NC}"
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if ! check_service_health "$name" "$port" 60; then
            echo -e "${RED}Failed to start ${group_name} group - ${name} not healthy${NC}"
            exit 1
        fi
    done
    
    echo -e "${GREEN}✓ ${group_name} group is healthy${NC}"
    echo ""
}

# Function to check MainPC connectivity
check_mainpc_connectivity() {
    echo -e "${BLUE}=== Checking MainPC Connectivity ===${NC}"
    
    echo -e "${YELLOW}Testing connection to MainPC (${MAINPC_HOST})...${NC}"
    
    # Check if MainPC Service Registry is accessible
    if timeout 10 bash -c "</dev/tcp/${MAINPC_HOST}/7200" 2>/dev/null; then
        echo -e "${GREEN}✓ MainPC Service Registry is accessible${NC}"
    else
        echo -e "${RED}✗ Cannot connect to MainPC Service Registry at ${MAINPC_HOST}:7200${NC}"
        echo -e "${YELLOW}Warning: PC2 will start but may have limited functionality${NC}"
    fi
    
    # Check if MainPC ObservabilityHub is accessible
    if timeout 10 bash -c "</dev/tcp/${MAINPC_HOST}/9000" 2>/dev/null; then
        echo -e "${GREEN}✓ MainPC ObservabilityHub is accessible${NC}"
    else
        echo -e "${RED}✗ Cannot connect to MainPC ObservabilityHub at ${MAINPC_HOST}:9000${NC}"
        echo -e "${YELLOW}Warning: Cross-machine monitoring may be limited${NC}"
    fi
    echo ""
}

# Check prerequisites
echo -e "${BLUE}=== Checking Prerequisites ===${NC}"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: ${COMPOSE_FILE} not found${NC}"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: ${CONFIG_FILE} not found${NC}"
    exit 1
fi

# Check Docker
if ! docker --version > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker not found${NC}"
    exit 1
fi

# Check Docker Compose
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker Compose not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Check MainPC connectivity
check_mainpc_connectivity

# Create network if it doesn't exist
echo -e "${BLUE}=== Setting up Network ===${NC}"
if ! docker network ls | grep -q "$NETWORK_NAME"; then
    echo -e "${YELLOW}Creating network: ${NETWORK_NAME}${NC}"
    docker network create \
        --driver bridge \
        --subnet="$SUBNET" \
        "$NETWORK_NAME"
    echo -e "${GREEN}✓ Network created${NC}"
else
    echo -e "${GREEN}✓ Network already exists${NC}"
fi
echo ""

# Create volumes
echo -e "${BLUE}=== Setting up Volumes ===${NC}"
volumes=("logs" "data" "cache_data")
for volume in "${volumes[@]}"; do
    if ! docker volume ls | grep -q "pc2_${volume}"; then
        echo -e "${YELLOW}Creating volume: pc2_${volume}${NC}"
        docker volume create "pc2_${volume}"
    else
        echo -e "${GREEN}✓ Volume pc2_${volume} exists${NC}"
    fi
done
echo ""

# Set environment variables for cross-machine communication
export SERVICE_REGISTRY_HOST=${MAINPC_HOST}
export REDIS_HOST=${MAINPC_HOST}
export MAINPC_HOST=${MAINPC_HOST}

echo -e "${BLUE}=== Environment Variables ===${NC}"
echo -e "${YELLOW}SERVICE_REGISTRY_HOST=${SERVICE_REGISTRY_HOST}${NC}"
echo -e "${YELLOW}REDIS_HOST=${REDIS_HOST}${NC}"
echo -e "${YELLOW}MAINPC_HOST=${MAINPC_HOST}${NC}"
echo ""

# Startup sequence based on validated dependencies from startup_config.yaml

# Phase 1: Foundation Services (Priority 1)
echo -e "${BLUE}=== Phase 1: Foundation Services ===${NC}"
foundation_services=(
    "observability-hub:9000"
    "memory-orchestrator:7140"
)

docker compose -f "$COMPOSE_FILE" up -d \
    observability-hub \
    memory-orchestrator

wait_for_group "Foundation Services" "${foundation_services[@]}"

# Phase 2: Infrastructure Services (Priority 2)
echo -e "${BLUE}=== Phase 2: Infrastructure Services ===${NC}"
infrastructure_services=(
    "resource-manager:7113"
    "cache-manager:7102"
)

docker compose -f "$COMPOSE_FILE" up -d \
    resource-manager \
    cache-manager

wait_for_group "Infrastructure Services" "${infrastructure_services[@]}"

# Phase 3: Task Processing Services (Priority 3)
echo -e "${BLUE}=== Phase 3: Task Processing Services ===${NC}"
task_processing_services=(
    "async-processor:7101"
    "task-scheduler:7115"
    "advanced-router:7129"
)

docker compose -f "$COMPOSE_FILE" up -d \
    async-processor \
    task-scheduler \
    advanced-router

wait_for_group "Task Processing Services" "${task_processing_services[@]}"

# Phase 4: Memory & Reasoning Services (Priority 4)
echo -e "${BLUE}=== Phase 4: Memory & Reasoning Services ===${NC}"
memory_reasoning_services=(
    "dream-world-agent:7104"
    "unified-memory-reasoning-agent:7105"
    "context-manager:7111"
    "experience-tracker:7112"
)

docker compose -f "$COMPOSE_FILE" up -d \
    dream-world-agent \
    unified-memory-reasoning-agent \
    context-manager \
    experience-tracker

wait_for_group "Memory & Reasoning Services" "${memory_reasoning_services[@]}"

# Phase 5: Tutoring & Learning Services (Priority 5)
echo -e "${BLUE}=== Phase 5: Tutoring & Learning Services ===${NC}"
tutoring_services=(
    "tutor-agent:7108"
    "tutoring-agent:7131"
)

docker compose -f "$COMPOSE_FILE" up -d \
    tutor-agent \
    tutoring-agent

wait_for_group "Tutoring & Learning Services" "${tutoring_services[@]}"

# Phase 6: Utility Services (Priority 6)
echo -e "${BLUE}=== Phase 6: Utility Services ===${NC}"
utility_services=(
    "unified-utils-agent:7118"
    "authentication-agent:7116"
    "agent-trust-scorer:7122"
    "filesystem-assistant-agent:7123"
)

docker compose -f "$COMPOSE_FILE" up -d \
    unified-utils-agent \
    authentication-agent \
    agent-trust-scorer \
    filesystem-assistant-agent

wait_for_group "Utility Services" "${utility_services[@]}"

# Phase 7: Advanced Processing Services (Priority 7)
echo -e "${BLUE}=== Phase 7: Advanced Processing Services ===${NC}"
advanced_services=(
    "vision-processing-agent:7150"
    "remote-connector-agent:7124"
    "unified-web-agent:7126"
    "dreaming-mode-agent:7127"
)

docker compose -f "$COMPOSE_FILE" up -d \
    vision-processing-agent \
    remote-connector-agent \
    unified-web-agent \
    dreaming-mode-agent

wait_for_group "Advanced Processing Services" "${advanced_services[@]}"

# Phase 8: Monitoring & Context Services (Priority 8)
echo -e "${BLUE}=== Phase 8: Monitoring & Context Services ===${NC}"
monitoring_services=(
    "proactive-context-monitor:7119"
)

docker compose -f "$COMPOSE_FILE" up -d \
    proactive-context-monitor

wait_for_group "Monitoring & Context Services" "${monitoring_services[@]}"

# Final health check
echo -e "${BLUE}=== Final System Health Check ===${NC}"
echo -e "${YELLOW}Running comprehensive health check...${NC}"

# Get all running containers
running_containers=$(docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running")

healthy_count=0
total_count=0

for container in $running_containers; do
    total_count=$((total_count + 1))
    
    # Extract port from container configuration
    port=$(docker compose -f "$COMPOSE_FILE" config | grep -A 10 "^  ${container}:" | grep -E "^\s*-\s*\"[0-9]+:" | head -1 | sed 's/.*"\([0-9]*\):.*/\1/')
    
    if [ -n "$port" ] && check_service_health "$container" "$port" 10; then
        healthy_count=$((healthy_count + 1))
        echo -e "${GREEN}✓ ${container}${NC}"
    else
        echo -e "${RED}✗ ${container}${NC}"
    fi
done

echo ""
echo -e "${BLUE}=== Startup Summary ===${NC}"
echo -e "${GREEN}Healthy services: ${healthy_count}/${total_count}${NC}"

if [ "$healthy_count" -eq "$total_count" ]; then
    echo -e "${GREEN}🎉 All PC2 services started successfully!${NC}"
    echo ""
    echo -e "${BLUE}Key Service URLs:${NC}"
    echo -e "${YELLOW}  - ObservabilityHub: http://localhost:9000${NC}"
    echo -e "${YELLOW}  - Memory Orchestrator: http://localhost:7140${NC}"
    echo -e "${YELLOW}  - Tiered Responder: http://localhost:7100${NC}"
    echo -e "${YELLOW}  - Unified Web Agent: http://localhost:7126${NC}"
    echo ""
    echo -e "${BLUE}Cross-Machine Dependencies:${NC}"
    echo -e "${YELLOW}  - MainPC Service Registry: ${MAINPC_HOST}:7200${NC}"
    echo -e "${YELLOW}  - MainPC ObservabilityHub: ${MAINPC_HOST}:9000${NC}"
    echo -e "${YELLOW}  - MainPC Redis: ${MAINPC_HOST}:6379${NC}"
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo -e "${YELLOW}  - View logs: docker compose -f ${COMPOSE_FILE} logs -f [service-name]${NC}"
    echo -e "${YELLOW}  - Stop all: docker compose -f ${COMPOSE_FILE} down${NC}"
    echo -e "${YELLOW}  - Restart service: docker compose -f ${COMPOSE_FILE} restart [service-name]${NC}"
    echo -e "${YELLOW}  - Check cross-machine connectivity: docker compose -f ${COMPOSE_FILE} exec [service] ping ${MAINPC_HOST}${NC}"
else
    echo -e "${RED}⚠️  Some services failed to start properly${NC}"
    echo -e "${YELLOW}Check logs: docker compose -f ${COMPOSE_FILE} logs${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo -e "${YELLOW}1. Check MainPC connectivity: ping ${MAINPC_HOST}${NC}"
    echo -e "${YELLOW}2. Verify MainPC services are running${NC}"
    echo -e "${YELLOW}3. Check network configuration and firewall rules${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}PC2 Docker startup completed successfully!${NC}"