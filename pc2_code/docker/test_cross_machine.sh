#!/bin/bash
# Test script for PC2 ↔ MainPC communication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAINPC_HOST="192.168.100.16"
PC2_HOST="192.168.100.17"

echo -e "${BLUE}=== PC2 ↔ MainPC Communication Test ===${NC}\n"

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (HTTP $response)${NC}"
        return 0
    elif [ "$response" = "000" ]; then
        echo -e "${RED}✗ FAIL (Connection refused)${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠ WARNING (HTTP $response)${NC}"
        return 1
    fi
}

# Function to test ZMQ connection
test_zmq() {
    local name=$1
    local host=$2
    local port=$3
    
    echo -n "Testing ZMQ $name... "
    
    # Use Python to test ZMQ connection
    python3 -c "
import zmq
import sys
try:
    ctx = zmq.Context()
    socket = ctx.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)
    socket.connect('tcp://$host:$port')
    socket.send_string('ping')
    response = socket.recv_string()
    print('OK')
    sys.exit(0)
except:
    print('FAIL')
    sys.exit(1)
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Test PC2 local services
echo -e "${YELLOW}Testing PC2 Local Services:${NC}"
test_endpoint "MemoryOrchestratorService Health" "http://localhost:8140/health"
test_endpoint "TieredResponder Health" "http://localhost:8100/health"
test_endpoint "RemoteConnectorAgent Health" "http://localhost:8124/health"
test_endpoint "ObservabilityHub Health" "http://localhost:9100/health"
test_endpoint "ObservabilityHub Metrics" "http://localhost:9000/metrics"

echo

# Test PC2 → MainPC connectivity
echo -e "${YELLOW}Testing PC2 → MainPC Connectivity:${NC}"

# Test network connectivity
echo -n "Testing network connectivity to MainPC... "
if ping -c 1 -W 2 $MAINPC_HOST > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

# Test MainPC services from PC2
test_endpoint "MainPC ServiceRegistry" "http://$MAINPC_HOST:7100/health"
test_endpoint "MainPC ObservabilityHub" "http://$MAINPC_HOST:9000/health"

echo

# Test cross-machine sync
echo -e "${YELLOW}Testing Cross-Machine Sync:${NC}"

# Check if ObservabilityHub can reach MainPC hub
echo -n "Testing ObservabilityHub sync... "
docker exec pc2-observability-hub curl -s -o /dev/null -w "%{http_code}" "http://$MAINPC_HOST:9000/health" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo

# Test service discovery
echo -e "${YELLOW}Testing Service Discovery:${NC}"

# Register PC2 service with MainPC registry
echo -n "Registering PC2 service with MainPC... "
response=$(curl -s -X POST "http://$MAINPC_HOST:7100/register" \
    -H "Content-Type: application/json" \
    -d '{
        "name": "PC2_RemoteConnector",
        "host": "'$PC2_HOST'",
        "port": 7124,
        "health_endpoint": "/health",
        "metadata": {
            "machine": "PC2",
            "type": "gateway"
        }
    }' 2>/dev/null || echo "FAIL")

if [[ "$response" == *"success"* ]] || [[ "$response" == *"already registered"* ]]; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
fi

echo

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo "PC2 Local Services: Check individual results above"
echo "Network Connectivity: Check individual results above"
echo "Cross-Machine Sync: Check individual results above"

echo -e "\n${YELLOW}Note: Some tests may fail if MainPC services are not running.${NC}"
echo -e "${YELLOW}Ensure both PC2 and MainPC Docker environments are running.${NC}"