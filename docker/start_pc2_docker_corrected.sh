#!/bin/bash

# CORRECTED PC2 Docker Startup Script  
# Based on VALIDATED dependencies and RTX 3060 configuration
# Fixes: ResourceManager before TieredResponder/AsyncProcessor, ObservabilityHub in Phase 1

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.pc2.yml"
CONFIG_FILE="../pc2_code/config/startup_config.yaml"
NETWORK_NAME="ai_system_net"
SUBNET="172.21.0.0/16"
MAINPC_HOST="192.168.100.16"

echo -e "${CYAN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            PC2 Docker Startup (CORRECTED)         ║${NC}"
echo -e "${CYAN}║            RTX 3060 - 12GB VRAM (10GB Limit)      ║${NC}"
echo -e "${CYAN}║            Cross-Machine Dependencies Fixed        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════╝${NC}"
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

# Function to check RTX 3060 GPU status
check_gpu_status() {
    echo -e "${BLUE}=== RTX 3060 GPU Status Check ===${NC}"
    
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}NVIDIA GPU Information:${NC}"
        nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
        echo ""
        
        # Check if RTX 3060 is detected  
        if nvidia-smi --query-gpu=name --format=csv,noheader | grep -q "3060"; then
            echo -e "${GREEN}✓ RTX 3060 detected${NC}"
        else
            echo -e "${YELLOW}⚠ RTX 3060 not detected - checking available GPU${NC}"
        fi
        
        # Check VRAM with 10GB limit for PC2
        local total_vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        local used_vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
        local vram_limit=10000  # 10GB limit for RTX 3060
        local safety_margin=2000  # 2GB safety margin
        
        echo -e "${BLUE}VRAM Status (RTX 3060):${NC}"
        echo -e "  Total: ${total_vram}MB"
        echo -e "  Used: ${used_vram}MB"
        echo -e "  PC2 Limit: ${vram_limit}MB (10GB)"
        echo -e "  Safety Margin: ${safety_margin}MB"
        echo -e "  Available for PC2: $((vram_limit - used_vram))MB"
        
        if [ $used_vram -gt $vram_limit ]; then
            echo -e "${RED}⚠ VRAM usage exceeds PC2 limit!${NC}"
        else
            echo -e "${GREEN}✓ VRAM within PC2 limits${NC}"
        fi
    else
        echo -e "${RED}✗ nvidia-smi not found - GPU status unknown${NC}"
    fi
    echo ""
}

# Function to check MainPC connectivity
check_mainpc_connectivity() {
    echo -e "${BLUE}=== MainPC Connectivity Check ===${NC}"
    
    echo -e "${YELLOW}Testing connection to MainPC (${MAINPC_HOST})...${NC}"
    
    # Check critical MainPC services
    mainpc_services=(
        "7200:ServiceRegistry"
        "9000:ObservabilityHub"  
        "6379:Redis"
    )
    
    connectivity_issues=0
    for service in "${mainpc_services[@]}"; do
        IFS=':' read -r port name <<< "$service"
        if timeout 10 bash -c "</dev/tcp/${MAINPC_HOST}/${port}" 2>/dev/null; then
            echo -e "${GREEN}✓ ${name} (${MAINPC_HOST}:${port})${NC}"
        else
            echo -e "${RED}✗ ${name} (${MAINPC_HOST}:${port})${NC}"
            connectivity_issues=$((connectivity_issues + 1))
        fi
    done
    
    if [ $connectivity_issues -gt 0 ]; then
        echo -e "${YELLOW}⚠ ${connectivity_issues} MainPC services unreachable${NC}"
        echo -e "${YELLOW}PC2 will start but may have limited functionality${NC}"
    else
        echo -e "${GREEN}✓ All MainPC services accessible${NC}"
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

# Check GPU status
check_gpu_status

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

echo -e "${BLUE}=== Cross-Machine Environment ===${NC}"
echo -e "${YELLOW}SERVICE_REGISTRY_HOST=${SERVICE_REGISTRY_HOST}${NC}"
echo -e "${YELLOW}REDIS_HOST=${REDIS_HOST}${NC}"
echo -e "${YELLOW}MAINPC_HOST=${MAINPC_HOST}${NC}"
echo ""

# CORRECTED STARTUP SEQUENCE BASED ON VALIDATED DEPENDENCIES

# Phase 1: Foundation Services (NO DEPENDENCIES - PARALLEL START)
echo -e "${PURPLE}=== Phase 1: Foundation Services (CORRECTED) ===${NC}"
echo -e "${YELLOW}Starting MemoryOrchestratorService & ObservabilityHub (NO DEPENDENCIES)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d \
    memory-orchestrator \
    observability-hub

# Validate foundation services
foundation_services=(
    "memory-orchestrator:7140"
    "observability-hub:9000"
)

for service in "${foundation_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health "$name" "$port" 60; then
        echo -e "${RED}CRITICAL: ${name} failed to start!${NC}"
        exit 1
    fi
done
echo ""

# Phase 2: Resource Management (RTX 3060 Management)
echo -e "${PURPLE}=== Phase 2: Resource Management (RTX 3060) ===${NC}"
echo -e "${YELLOW}Starting ResourceManager (depends on ObservabilityHub)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d resource-manager

if ! check_service_health "resource-manager" "7113" 60; then
    echo -e "${RED}CRITICAL: ResourceManager failed to start!${NC}"
    echo -e "${YELLOW}This will break TieredResponder & AsyncProcessor!${NC}"
    exit 1
fi

# Check GPU status after ResourceManager
echo -e "${BLUE}Post-ResourceManager GPU Check:${NC}"
check_gpu_status
echo ""

# Phase 3: Cache System (Depends on MemoryOrchestratorService)
echo -e "${PURPLE}=== Phase 3: Cache System ===${NC}"
echo -e "${YELLOW}Starting CacheManager (depends on MemoryOrchestratorService)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d cache-manager

if ! check_service_health "cache-manager" "7102" 60; then
    echo -e "${RED}CRITICAL: CacheManager failed to start!${NC}"
    exit 1
fi
echo ""

# Phase 4: Task Processing (CORRECTED - Now depends on ResourceManager)
echo -e "${PURPLE}=== Phase 4: Task Processing (DEPENDENCY FIXED) ===${NC}"
echo -e "${YELLOW}Starting TieredResponder & AsyncProcessor (both depend on ResourceManager)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d \
    tiered-responder \
    async-processor

# Validate task processing services
task_services=(
    "tiered-responder:7100"
    "async-processor:7101"
)

for service in "${task_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health "$name" "$port" 60; then
        echo -e "${RED}CRITICAL: ${name} failed to start!${NC}"
        exit 1
    fi
done
echo ""

# Phase 5: Advanced Task Processing
echo -e "${PURPLE}=== Phase 5: Advanced Task Processing ===${NC}"
echo -e "${YELLOW}Starting TaskScheduler & AdvancedRouter...${NC}"

docker compose -f "$COMPOSE_FILE" up -d \
    task-scheduler \
    advanced-router

advanced_task_services=(
    "task-scheduler:7115"
    "advanced-router:7129"
)

for service in "${advanced_task_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health "$name" "$port" 60; then
        echo -e "${RED}WARNING: ${name} failed to start (non-critical)${NC}"
    fi
done
echo ""

# Phase 6: Memory & Reasoning Services
echo -e "${PURPLE}=== Phase 6: Memory & Reasoning Services ===${NC}"
echo -e "${YELLOW}Starting memory and reasoning agents...${NC}"

docker compose -f "$COMPOSE_FILE" up -d \
    dream-world-agent \
    unified-memory-reasoning-agent \
    context-manager \
    experience-tracker

memory_reasoning_services=(
    "dream-world-agent:7104"
    "unified-memory-reasoning-agent:7105"
    "context-manager:7111"
    "experience-tracker:7112"
)

for service in "${memory_reasoning_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if check_service_health "$name" "$port" 45; then
        echo -e "${GREEN}✓ ${name}${NC}"
    else
        echo -e "${YELLOW}⚠ ${name} (non-critical)${NC}"
    fi
done
echo ""

# Phase 7: Tutoring & Learning Services
echo -e "${PURPLE}=== Phase 7: Tutoring & Learning Services ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    tutor-agent \
    tutoring-agent

tutoring_services=(
    "tutor-agent:7108"
    "tutoring-agent:7131"
)

for service in "${tutoring_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    check_service_health "$name" "$port" 45
done
echo ""

# Phase 8: Utility Services
echo -e "${PURPLE}=== Phase 8: Utility Services ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    unified-utils-agent \
    authentication-agent \
    agent-trust-scorer \
    filesystem-assistant-agent

utility_services=(
    "unified-utils-agent:7118"
    "authentication-agent:7116"
    "agent-trust-scorer:7122"
    "filesystem-assistant-agent:7123"
)

echo -e "${YELLOW}Checking utility services...${NC}"
for service in "${utility_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if check_service_health "$name" "$port" 30; then
        echo -e "${GREEN}✓ ${name}${NC}"
    else
        echo -e "${YELLOW}⚠ ${name} (non-critical)${NC}"
    fi
done
echo ""

# Phase 9: Vision & Web Processing (RTX 3060 Usage)
echo -e "${PURPLE}=== Phase 9: Vision & Web Processing (RTX 3060) ===${NC}"
echo -e "${YELLOW}Starting VisionProcessingAgent (depends on CacheManager)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d vision-processing-agent

if ! check_service_health "vision-processing-agent" "7150" 60; then
    echo -e "${RED}WARNING: VisionProcessingAgent failed (RTX 3060 issue?)${NC}"
    check_gpu_status
fi

docker compose -f "$COMPOSE_FILE" up -d \
    remote-connector-agent \
    unified-web-agent

web_services=(
    "remote-connector-agent:7124"
    "unified-web-agent:7126"
)

for service in "${web_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    check_service_health "$name" "$port" 45
done
echo ""

# Phase 10: Advanced Processing & Monitoring
echo -e "${PURPLE}=== Phase 10: Advanced Processing & Monitoring ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    dreaming-mode-agent \
    proactive-context-monitor

final_services=(
    "dreaming-mode-agent:7127"
    "proactive-context-monitor:7119"
)

for service in "${final_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    check_service_health "$name" "$port" 45
done
echo ""

# Final system validation
echo -e "${BLUE}=== Final PC2 System Validation ===${NC}"

# Check critical services
critical_services=(
    "memory-orchestrator:7140"
    "observability-hub:9000"
    "resource-manager:7113"
    "cache-manager:7102"
    "tiered-responder:7100"
    "async-processor:7101"
)

echo -e "${YELLOW}Validating critical services...${NC}"
failed_critical=0
for service in "${critical_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if check_service_health "$name" "$port" 15; then
        echo -e "${GREEN}✓ ${name} (CRITICAL)${NC}"
    else
        echo -e "${RED}✗ ${name} (CRITICAL - FAILED)${NC}"
        failed_critical=$((failed_critical + 1))
    fi
done

# Final GPU check
echo ""
echo -e "${BLUE}=== Final RTX 3060 Status ===${NC}"
check_gpu_status

# Cross-machine connectivity check
echo -e "${BLUE}=== Cross-Machine Connectivity Status ===${NC}"
check_mainpc_connectivity

# Final report
echo -e "${BLUE}=== PC2 Startup Summary ===${NC}"
if [ $failed_critical -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical PC2 services started successfully!${NC}"
    echo ""
    echo -e "${BLUE}Key Service URLs:${NC}"
    echo -e "${YELLOW}  - Memory Orchestrator: http://localhost:7140${NC}"
    echo -e "${YELLOW}  - ObservabilityHub: http://localhost:9000${NC}"
    echo -e "${YELLOW}  - Resource Manager: http://localhost:7113${NC}"
    echo -e "${YELLOW}  - Tiered Responder: http://localhost:7100${NC}"
    echo -e "${YELLOW}  - Unified Web Agent: http://localhost:7126${NC}"
    echo ""
    echo -e "${BLUE}GPU Configuration (RTX 3060):${NC}"
    echo -e "${YELLOW}  - Total VRAM: 12GB${NC}"
    echo -e "${YELLOW}  - PC2 Limit: 10GB (safety margin)${NC}"
    echo -e "${YELLOW}  - Vision Processing: RTX 3060 optimized${NC}"
    echo ""
    echo -e "${BLUE}Cross-Machine Dependencies:${NC}"
    echo -e "${YELLOW}  - MainPC Service Registry: ${MAINPC_HOST}:7200${NC}"
    echo -e "${YELLOW}  - MainPC ObservabilityHub: ${MAINPC_HOST}:9000${NC}"
    echo -e "${YELLOW}  - MainPC Redis: ${MAINPC_HOST}:6379${NC}"
    echo ""
else
    echo -e "${RED}⚠️ ${failed_critical} critical services failed to start${NC}"
    echo -e "${YELLOW}PC2 system may not function properly${NC}"
    echo ""
    echo -e "${BLUE}Common Issues:${NC}"
    echo -e "${YELLOW}1. Check RTX 3060 drivers and CUDA installation${NC}"
    echo -e "${YELLOW}2. Verify MainPC connectivity: ping ${MAINPC_HOST}${NC}"
    echo -e "${YELLOW}3. Check VRAM usage and limits${NC}"
    exit 1
fi

echo -e "${GREEN}PC2 (${GPU_MODEL}) startup completed!${NC}"