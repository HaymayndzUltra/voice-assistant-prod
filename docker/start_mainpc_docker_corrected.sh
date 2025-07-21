#!/bin/bash

# CORRECTED MainPC Docker Startup Script
# Based on VALIDATED dependencies and RTX 4090 configuration
# Fixes: ServiceRegistry first, proper GPU memory management

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.mainpc.yml"
CONFIG_FILE="../main_pc_code/config/startup_config.yaml"
NETWORK_NAME="ai_system_network"
SUBNET="172.20.0.0/16"

echo -e "${PURPLE}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║           MainPC Docker Startup (CORRECTED)       ║${NC}"
echo -e "${PURPLE}║           RTX 4090 - 24GB VRAM (19.2GB Budget)    ║${NC}"
echo -e "${PURPLE}║           Based on Validated Dependencies          ║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if service is healthy
check_service_health() {
    local service_name=$1
    local port=$2
    local timeout=${3:-30}
    
    echo -e "${YELLOW}Checking health of ${service_name} on port ${port}...${NC}"
    
    for i in $(seq 1 $timeout); do
        if docker exec "${service_name}" python -c "
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

# Function to check GPU status
check_gpu_status() {
    echo -e "${BLUE}=== RTX 4090 GPU Status Check ===${NC}"
    
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo -e "${YELLOW}NVIDIA GPU Information:${NC}"
        nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader,nounits
        echo ""
        
        # Check if RTX 4090 is detected
        if nvidia-smi --query-gpu=name --format=csv,noheader | grep -q "4090"; then
            echo -e "${GREEN}✓ RTX 4090 detected${NC}"
        else
            echo -e "${YELLOW}⚠ RTX 4090 not detected - checking available GPU${NC}"
        fi
        
        # Check VRAM
        local total_vram=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        local used_vram=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
        local budget_vram=$((total_vram * 80 / 100))
        
        echo -e "${BLUE}VRAM Status:${NC}"
        echo -e "  Total: ${total_vram}MB"
        echo -e "  Used: ${used_vram}MB"
        echo -e "  Budget (80%): ${budget_vram}MB"
        echo -e "  Available: $((total_vram - used_vram))MB"
        
        if [ $used_vram -gt $budget_vram ]; then
            echo -e "${RED}⚠ VRAM usage exceeds budget!${NC}"
        else
            echo -e "${GREEN}✓ VRAM within budget${NC}"
        fi
    else
        echo -e "${RED}✗ nvidia-smi not found - GPU status unknown${NC}"
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
volumes=("logs" "models" "data" "config")
for volume in "${volumes[@]}"; do
    if ! docker volume ls | grep -q "ai_system_${volume}"; then
        echo -e "${YELLOW}Creating volume: ai_system_${volume}${NC}"
        docker volume create "ai_system_${volume}"
    else
        echo -e "${GREEN}✓ Volume ai_system_${volume} exists${NC}"
    fi
done
echo ""

# Start infrastructure services first
echo -e "${BLUE}=== Starting Infrastructure ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d redis
sleep 5
echo -e "${GREEN}✓ Redis started${NC}"
echo ""

# CORRECTED STARTUP SEQUENCE BASED ON VALIDATED DEPENDENCIES

# Phase 1: Foundation (ServiceRegistry FIRST - NO DEPENDENCIES)
echo -e "${PURPLE}=== Phase 1: Foundation Services ===${NC}"
echo -e "${YELLOW}Starting ServiceRegistry (NO DEPENDENCIES)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d service-registry

if ! check_service_health "service-registry" "7200" 60; then
    echo -e "${RED}CRITICAL: ServiceRegistry failed to start!${NC}"
    exit 1
fi
echo ""

# Phase 2: Core Infrastructure (Depends on ServiceRegistry)
echo -e "${PURPLE}=== Phase 2: Core Infrastructure ===${NC}"
echo -e "${YELLOW}Starting SystemDigitalTwin (depends on ServiceRegistry)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d system-digital-twin

if ! check_service_health "system-digital-twin" "7220" 60; then
    echo -e "${RED}CRITICAL: SystemDigitalTwin failed to start!${NC}"
    exit 1
fi
echo ""

# Phase 3: Core Services (Depend on SystemDigitalTwin)
echo -e "${PURPLE}=== Phase 3: Core Services ===${NC}"
echo -e "${YELLOW}Starting RequestCoordinator, UnifiedSystemAgent, ObservabilityHub...${NC}"

docker compose -f "$COMPOSE_FILE" up -d \
    request-coordinator \
    unified-system-agent \
    observability-hub

# Validate each service
core_services=(
    "request-coordinator:26002"
    "unified-system-agent:7225"
    "observability-hub:9000"
)

for service in "${core_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health "$name" "$port" 60; then
        echo -e "${RED}CRITICAL: ${name} failed to start!${NC}"
        exit 1
    fi
done
echo ""

# Phase 4: GPU Services (RTX 4090 - ModelManagerSuite)
echo -e "${PURPLE}=== Phase 4: GPU Services (RTX 4090) ===${NC}"
echo -e "${YELLOW}Starting ModelManagerSuite (19.2GB VRAM budget)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d model-manager-suite

if ! check_service_health "model-manager-suite" "7211" 90; then
    echo -e "${RED}CRITICAL: ModelManagerSuite failed to start!${NC}"
    echo -e "${YELLOW}Checking GPU status...${NC}"
    check_gpu_status
    exit 1
fi

# Check VRAM usage after ModelManagerSuite
echo -e "${BLUE}Post-ModelManagerSuite GPU Check:${NC}"
check_gpu_status
echo ""

# Phase 5: Memory System (Depends on SystemDigitalTwin & MemoryClient)
echo -e "${PURPLE}=== Phase 5: Memory System ===${NC}"
echo -e "${YELLOW}Starting Memory services...${NC}"

docker compose -f "$COMPOSE_FILE" up -d memory-client

if ! check_service_health "memory-client" "5713" 60; then
    echo -e "${RED}CRITICAL: MemoryClient failed to start!${NC}"
    exit 1
fi

docker compose -f "$COMPOSE_FILE" up -d \
    session-memory-agent \
    knowledge-base

memory_services=(
    "session-memory-agent:5574"
    "knowledge-base:5715"
)

for service in "${memory_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if ! check_service_health "$name" "$port" 60; then
        echo -e "${RED}CRITICAL: ${name} failed to start!${NC}"
        exit 1
    fi
done
echo ""

# Phase 6: GPU Infrastructure (Depends on ModelManagerSuite)
echo -e "${PURPLE}=== Phase 6: GPU Infrastructure ===${NC}"
echo -e "${YELLOW}Starting VRAMOptimizerAgent (coordinates with ModelManagerSuite)...${NC}"

docker compose -f "$COMPOSE_FILE" up -d vram-optimizer-agent

if ! check_service_health "vram-optimizer-agent" "5572" 60; then
    echo -e "${RED}WARNING: VRAMOptimizerAgent failed to start (non-critical)${NC}"
fi
echo ""

# Phase 7: Utility Services (Various dependencies)
echo -e "${PURPLE}=== Phase 7: Utility Services ===${NC}"
echo -e "${YELLOW}Starting utility services...${NC}"

docker compose -f "$COMPOSE_FILE" up -d \
    code-generator \
    self-training-orchestrator \
    predictive-health-monitor \
    fixed-streaming-translation \
    executor \
    local-fine-tuner-agent \
    nllb-adapter

utility_services=(
    "code-generator:5650"
    "self-training-orchestrator:5660"
    "predictive-health-monitor:5613"
    "fixed-streaming-translation:5584"
    "executor:5606"
    "local-fine-tuner-agent:5642"
    "nllb-adapter:5581"
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

# Phase 8: Speech Services
echo -e "${PURPLE}=== Phase 8: Speech Services ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d stt-service tts-service

speech_services=(
    "stt-service:5800"
    "tts-service:5801"
)

for service in "${speech_services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    check_service_health "$name" "$port" 45
done
echo ""

# Phase 9: Language Processing
echo -e "${PURPLE}=== Phase 9: Language Processing ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    model-orchestrator \
    goal-manager \
    intention-validator-agent \
    nlu-agent \
    advanced-command-handler

# Continue with remaining phases...
echo -e "${YELLOW}Starting remaining language processing services...${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    chitchat-agent \
    feedback-handler \
    translation-service \
    dynamic-identity-agent \
    emotion-synthesis-agent

echo ""

# Phase 10: Emotion System
echo -e "${PURPLE}=== Phase 10: Emotion System ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    emotion-engine \
    mood-tracker-agent \
    human-awareness-agent \
    tone-detector \
    voice-profiling-agent \
    empathy-agent

echo ""

# Phase 11: Audio Interface & Learning Systems
echo -e "${PURPLE}=== Phase 11: Audio & Learning Systems ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    audio-capture \
    fused-audio-preprocessor \
    streaming-interrupt-handler \
    streaming-speech-recognition \
    streaming-tts-agent \
    wake-word-detector \
    streaming-language-analyzer \
    proactive-agent

docker compose -f "$COMPOSE_FILE" up -d \
    learning-orchestration-service \
    learning-opportunity-detector \
    learning-manager \
    active-learning-monitor \
    learning-adjuster-agent

echo ""

# Phase 12: Vision & Reasoning
echo -e "${PURPLE}=== Phase 12: Vision & Reasoning ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d \
    face-recognition-agent \
    chain-of-thought-agent \
    responder

echo ""

# Final system health check
echo -e "${BLUE}=== Final System Validation ===${NC}"

# Check critical services
critical_services=(
    "service-registry:7200"
    "system-digital-twin:7220"
    "request-coordinator:26002"
    "model-manager-suite:7211"
    "observability-hub:9000"
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
echo -e "${BLUE}=== Final GPU Status ===${NC}"
check_gpu_status

# Final report
echo -e "${BLUE}=== MainPC Startup Summary ===${NC}"
if [ $failed_critical -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical services started successfully!${NC}"
    echo ""
    echo -e "${BLUE}Key Service URLs:${NC}"
    echo -e "${YELLOW}  - Service Registry: http://localhost:7200${NC}"
    echo -e "${YELLOW}  - System Digital Twin: http://localhost:7220${NC}"
    echo -e "${YELLOW}  - Request Coordinator: http://localhost:26002${NC}"
    echo -e "${YELLOW}  - Model Manager Suite: http://localhost:7211${NC}"
    echo -e "${YELLOW}  - Observability Hub: http://localhost:9000${NC}"
    echo ""
    echo -e "${BLUE}GPU Configuration:${NC}"
    echo -e "${YELLOW}  - RTX 4090: 24GB VRAM total${NC}"
    echo -e "${YELLOW}  - Budget: 19.2GB (80% allocation)${NC}"
    echo -e "${YELLOW}  - Model Manager Suite: Primary GPU user${NC}"
    echo ""
else
    echo -e "${RED}⚠️ ${failed_critical} critical services failed to start${NC}"
    echo -e "${YELLOW}System may not function properly${NC}"
    exit 1
fi

echo -e "${GREEN}MainPC (RTX 4090) startup completed!${NC}"