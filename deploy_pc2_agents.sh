#!/bin/bash
# PC2 Agents Deployment Script
# This script deploys PC2 agents in the correct order with health checks

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.pc2.individual.yml"
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_INTERVAL=5

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to check if a service is healthy
check_service_health() {
    local service=$1
    local port=$2
    local timeout=$3
    local elapsed=0
    
    print_status "Checking health of $service on port $port..."
    
    while [ $elapsed -lt $timeout ]; do
        if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1; then
            print_status "$service is healthy!"
            return 0
        fi
        
        sleep $HEALTH_CHECK_INTERVAL
        elapsed=$((elapsed + HEALTH_CHECK_INTERVAL))
        echo -n "."
    done
    
    print_error "$service failed health check after ${timeout}s"
    return 1
}

# Function to deploy a service
deploy_service() {
    local service=$1
    local port=$2
    
    print_status "Deploying $service..."
    
    if docker compose -f $DOCKER_COMPOSE_FILE up -d --build $service; then
        print_status "$service started, waiting for health check..."
        
        if check_service_health $service $port $HEALTH_CHECK_TIMEOUT; then
            return 0
        else
            print_error "Health check failed for $service"
            return 1
        fi
    else
        print_error "Failed to deploy $service"
        return 1
    fi
}

# Main deployment sequence
main() {
    print_status "Starting PC2 agents deployment..."
    
    # Change to docker directory
    cd docker/
    
    # Stage A - Core infrastructure (already working)
    print_status "=== Stage A: Core Infrastructure ==="
    deploy_service "observability-hub" 9000
    deploy_service "unified-utils-agent" 7118
    deploy_service "authentication-agent" 7116
    
    # Stage B - Foundation services
    print_status "=== Stage B: Foundation Services ==="
    deploy_service "memory-orchestrator-service" 7140
    deploy_service "resource-manager" 7113
    deploy_service "cache-manager" 7102
    
    # Stage C - Processing agents
    print_status "=== Stage C: Processing Agents ==="
    deploy_service "context-manager" 7111
    deploy_service "advanced-router" 7129
    
    # Stage D - Feature agents
    print_status "=== Stage D: Feature Agents ==="
    deploy_service "agent-trust-scorer" 7122
    deploy_service "filesystem-assistant-agent" 7123
    deploy_service "unified-web-agent" 7126
    deploy_service "dreaming-mode-agent" 7127
    deploy_service "remote-connector-agent" 7124
    deploy_service "proactive-context-monitor" 7119
    
    # Summary
    print_status "=== Deployment Summary ==="
    docker compose -f $DOCKER_COMPOSE_FILE ps
    
    print_status "PC2 agents deployment completed!"
    print_status "You can check the status with: docker compose -f $DOCKER_COMPOSE_FILE ps"
    print_status "View logs with: docker compose -f $DOCKER_COMPOSE_FILE logs -f [service-name]"
}

# Run main function
main