#!/bin/bash

# MainPC Docker Startup Script
# Based on main_pc_code/config/startup_config.yaml validation

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.mainpc.yml"
CONFIG_FILE="../main_pc_code/config/startup_config.yaml"
NETWORK_NAME="ai_system_network"
SUBNET="172.20.0.0/16"

echo -e "${BLUE}=== MainPC Docker Startup Script ===${NC}"
echo -e "${BLUE}Based on: ${CONFIG_FILE}${NC}"
echo -e "${BLUE}Network: ${NETWORK_NAME} (${SUBNET})${NC}"
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
echo -e "${BLUE}=== Starting Infrastructure Services ===${NC}"
docker compose -f "$COMPOSE_FILE" up -d redis
if ! check_service_health "redis" "6379" 30; then
    echo -e "${RED}Failed to start Redis${NC}"
    exit 1
fi
echo ""

# Startup sequence based on validated dependencies from startup_config.yaml

# Phase 1: Core Services (Priority 1)
echo -e "${BLUE}=== Phase 1: Core Services ===${NC}"
core_services=(
    "service-registry:7200"
    "system-digital-twin:7220"
)

docker compose -f "$COMPOSE_FILE" up -d \
    service-registry \
    system-digital-twin

wait_for_group "Core Services" "${core_services[@]}"

# Phase 2: Core Infrastructure (Priority 2)
echo -e "${BLUE}=== Phase 2: Core Infrastructure ===${NC}"
infrastructure_services=(
    "request-coordinator:26002"
    "unified-system-agent:7225"
    "observability-hub:9000"
    "model-manager-suite:7211"
)

docker compose -f "$COMPOSE_FILE" up -d \
    request-coordinator \
    unified-system-agent \
    observability-hub \
    model-manager-suite

wait_for_group "Core Infrastructure" "${infrastructure_services[@]}"

# Phase 3: Memory System (Priority 3)
echo -e "${BLUE}=== Phase 3: Memory System ===${NC}"
memory_services=(
    "memory-client:5713"
    "session-memory-agent:5574"
    "knowledge-base:5715"
)

docker compose -f "$COMPOSE_FILE" up -d \
    memory-client \
    session-memory-agent \
    knowledge-base

wait_for_group "Memory System" "${memory_services[@]}"

# Phase 4: GPU Infrastructure (Priority 4)
echo -e "${BLUE}=== Phase 4: GPU Infrastructure ===${NC}"
gpu_services=(
    "vram-optimizer-agent:5572"
)

docker compose -f "$COMPOSE_FILE" up -d \
    vram-optimizer-agent

wait_for_group "GPU Infrastructure" "${gpu_services[@]}"

# Phase 5: Utility Services (Priority 5)
echo -e "${BLUE}=== Phase 5: Utility Services ===${NC}"
utility_services=(
    "code-generator:5650"
    "self-training-orchestrator:5660"
    "predictive-health-monitor:5613"
    "fixed-streaming-translation:5584"
    "executor:5606"
    "local-fine-tuner-agent:5642"
    "nllb-adapter:5581"
)

docker compose -f "$COMPOSE_FILE" up -d \
    code-generator \
    self-training-orchestrator \
    predictive-health-monitor \
    fixed-streaming-translation \
    executor \
    local-fine-tuner-agent \
    nllb-adapter

wait_for_group "Utility Services" "${utility_services[@]}"

# Phase 6: Speech Services (Priority 6)
echo -e "${BLUE}=== Phase 6: Speech Services ===${NC}"
speech_services=(
    "stt-service:5800"
    "tts-service:5801"
)

docker compose -f "$COMPOSE_FILE" up -d \
    stt-service \
    tts-service

wait_for_group "Speech Services" "${speech_services[@]}"

# Phase 7: Language Processing (Priority 7)
echo -e "${BLUE}=== Phase 7: Language Processing ===${NC}"
language_services=(
    "model-orchestrator:7213"
    "goal-manager:7205"
    "intention-validator-agent:5701"
    "nlu-agent:5709"
    "advanced-command-handler:5710"
    "chitchat-agent:5711"
    "feedback-handler:5636"
    "translation-service:5595"
    "dynamic-identity-agent:5802"
    "emotion-synthesis-agent:5706"
)

docker compose -f "$COMPOSE_FILE" up -d \
    model-orchestrator \
    goal-manager \
    intention-validator-agent \
    nlu-agent \
    advanced-command-handler \
    chitchat-agent \
    feedback-handler \
    translation-service \
    dynamic-identity-agent \
    emotion-synthesis-agent

wait_for_group "Language Processing" "${language_services[@]}"

# Phase 8: Emotion System (Priority 8)
echo -e "${BLUE}=== Phase 8: Emotion System ===${NC}"
emotion_services=(
    "emotion-engine:5590"
    "mood-tracker-agent:5704"
    "human-awareness-agent:5705"
    "tone-detector:5625"
    "voice-profiling-agent:5708"
    "empathy-agent:5703"
)

docker compose -f "$COMPOSE_FILE" up -d \
    emotion-engine \
    mood-tracker-agent \
    human-awareness-agent \
    tone-detector \
    voice-profiling-agent \
    empathy-agent

wait_for_group "Emotion System" "${emotion_services[@]}"

# Phase 9: Audio Interface (Priority 9)
echo -e "${BLUE}=== Phase 9: Audio Interface ===${NC}"
audio_services=(
    "audio-capture:6550"
    "fused-audio-preprocessor:6551"
    "streaming-interrupt-handler:5576"
    "streaming-speech-recognition:6553"
    "streaming-tts-agent:5562"
    "wake-word-detector:6552"
    "streaming-language-analyzer:5579"
    "proactive-agent:5624"
)

docker compose -f "$COMPOSE_FILE" up -d \
    audio-capture \
    fused-audio-preprocessor \
    streaming-interrupt-handler \
    streaming-speech-recognition \
    streaming-tts-agent \
    wake-word-detector \
    streaming-language-analyzer \
    proactive-agent

wait_for_group "Audio Interface" "${audio_services[@]}"

# Phase 10: Learning & Knowledge (Priority 10)
echo -e "${BLUE}=== Phase 10: Learning & Knowledge ===${NC}"
learning_services=(
    "learning-orchestration-service:7210"
    "learning-opportunity-detector:7202"
    "learning-manager:5580"
    "active-learning-monitor:5638"
    "learning-adjuster-agent:5643"
)

docker compose -f "$COMPOSE_FILE" up -d \
    learning-orchestration-service \
    learning-opportunity-detector \
    learning-manager \
    active-learning-monitor \
    learning-adjuster-agent

wait_for_group "Learning & Knowledge" "${learning_services[@]}"

# Phase 11: Vision Processing & Reasoning (Priority 11)
echo -e "${BLUE}=== Phase 11: Vision & Reasoning ===${NC}"
vision_reasoning_services=(
    "face-recognition-agent:5610"
    "chain-of-thought-agent:5612"
    "responder:5637"
)

docker compose -f "$COMPOSE_FILE" up -d \
    face-recognition-agent \
    chain-of-thought-agent \
    responder

wait_for_group "Vision & Reasoning" "${vision_reasoning_services[@]}"

# Final health check
echo -e "${BLUE}=== Final System Health Check ===${NC}"
echo -e "${YELLOW}Running comprehensive health check...${NC}"

# Get all running containers
running_containers=$(docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running")

healthy_count=0
total_count=0

for container in $running_containers; do
    total_count=$((total_count + 1))
    if docker compose -f "$COMPOSE_FILE" exec -T "$container" python -c "
import requests
import sys
try:
    response = requests.get('http://localhost:8000/health', timeout=5)
    sys.exit(0 if response.status_code == 200 else 1)
except:
    sys.exit(1)
" 2>/dev/null; then
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
    echo -e "${GREEN}🎉 All MainPC services started successfully!${NC}"
    echo ""
    echo -e "${BLUE}Service URLs:${NC}"
    echo -e "${YELLOW}  - Service Registry: http://localhost:7200${NC}"
    echo -e "${YELLOW}  - System Digital Twin: http://localhost:7220${NC}"
    echo -e "${YELLOW}  - Request Coordinator: http://localhost:26002${NC}"
    echo -e "${YELLOW}  - Observability Hub: http://localhost:9000${NC}"
    echo ""
    echo -e "${BLUE}Useful commands:${NC}"
    echo -e "${YELLOW}  - View logs: docker compose -f ${COMPOSE_FILE} logs -f [service-name]${NC}"
    echo -e "${YELLOW}  - Stop all: docker compose -f ${COMPOSE_FILE} down${NC}"
    echo -e "${YELLOW}  - Restart service: docker compose -f ${COMPOSE_FILE} restart [service-name]${NC}"
else
    echo -e "${RED}⚠️  Some services failed to start properly${NC}"
    echo -e "${YELLOW}Check logs: docker compose -f ${COMPOSE_FILE} logs${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}MainPC Docker startup completed successfully!${NC}"