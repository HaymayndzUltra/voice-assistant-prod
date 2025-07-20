#!/bin/bash

# PC2 System Startup and Management Script
# Comprehensive script to build, start, monitor and manage PC2 containerized agents

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.pc2.yml"

# Configuration
PC2_IP="${PC2_IP:-$(hostname -I | awk '{print $1}')}"
MAINPC_IP="${MAINPC_IP:-192.168.100.16}"

print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                              PC2 System Manager                             ║"
    echo "║                        Containerized AI Agent System                        ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo -e "${YELLOW}Usage: $0 [COMMAND]${NC}"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo "  build      Build all PC2 Docker images"
    echo "  start      Start all PC2 services"
    echo "  stop       Stop all PC2 services"
    echo "  restart    Restart all PC2 services"
    echo "  status     Show status of all services"
    echo "  logs       Show logs for all services"
    echo "  health     Run comprehensive health check"
    echo "  clean      Clean up containers and images"
    echo "  test       Test cross-machine connectivity"
    echo "  monitor    Start monitoring dashboard"
    echo "  help       Show this help message"
    echo ""
    echo -e "${BLUE}Environment Variables:${NC}"
    echo "  PC2_IP      IP address of PC2 machine (auto-detected: $PC2_IP)"
    echo "  MAINPC_IP   IP address of MainPC machine (default: $MAINPC_IP)"
}

check_requirements() {
    echo -e "${BLUE}📋 Checking requirements...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Check if in project root
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        echo -e "${RED}❌ Not in project root directory${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All requirements met${NC}"
}

build_images() {
    echo -e "${BLUE}🔨 Building PC2 Docker images...${NC}"
    cd "$PROJECT_ROOT"
    
    # Make build script executable
    chmod +x "$SCRIPT_DIR/build_images.sh"
    
    # Run build script
    "$SCRIPT_DIR/build_images.sh"
    
    echo -e "${GREEN}✅ Build completed${NC}"
}

start_services() {
    echo -e "${BLUE}🚀 Starting PC2 services...${NC}"
    cd "$PROJECT_ROOT"
    
    # Create external network if it doesn't exist
    docker network create external_network 2>/dev/null || true
    
    # Start services in dependency order
    echo -e "${YELLOW}📦 Starting core infrastructure...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d observability-hub
    sleep 10
    
    echo -e "${YELLOW}📦 Starting memory and resource services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d memory-orchestrator-service resource-manager
    sleep 15
    
    echo -e "${YELLOW}📦 Starting integration layer...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d tiered-responder async-processor cache-manager
    sleep 10
    
    echo -e "${YELLOW}📦 Starting core agents...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d \
        dreamworld-agent unified-memory-reasoning-agent context-manager \
        experience-tracker task-scheduler
    sleep 10
    
    echo -e "${YELLOW}📦 Starting utility and specialized agents...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d \
        unified-utils-agent authentication-agent filesystem-assistant-agent \
        agent-trust-scorer proactive-context-monitor
    sleep 10
    
    echo -e "${YELLOW}📦 Starting advanced services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d \
        advanced-router remote-connector-agent vision-processing-agent \
        unified-web-agent
    sleep 10
    
    echo -e "${YELLOW}📦 Starting tutoring and dreaming services...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d \
        tutor-agent tutoring-agent dreaming-mode-agent
    
    echo -e "${GREEN}✅ All services started${NC}"
    
    # Wait for services to be ready
    echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
    sleep 30
    
    show_status
}

stop_services() {
    echo -e "${BLUE}🛑 Stopping PC2 services...${NC}"
    cd "$PROJECT_ROOT"
    
    docker-compose -f "$COMPOSE_FILE" down
    
    echo -e "${GREEN}✅ All services stopped${NC}"
}

restart_services() {
    echo -e "${BLUE}🔄 Restarting PC2 services...${NC}"
    stop_services
    sleep 5
    start_services
}

show_status() {
    echo -e "${BLUE}📊 PC2 Services Status:${NC}"
    cd "$PROJECT_ROOT"
    
    # Show container status
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo -e "${BLUE}🔍 Health Summary:${NC}"
    
    # Quick health check for key services
    local healthy=0
    local total=0
    
    for service in observability-hub memory-orchestrator-service tiered-responder; do
        total=$((total + 1))
        container_name="pc2-${service//-/-}"
        if docker exec "$container_name" python /app/health_check.py &>/dev/null; then
            echo -e "${GREEN}✅ $service${NC}"
            healthy=$((healthy + 1))
        else
            echo -e "${RED}❌ $service${NC}"
        fi
    done
    
    echo ""
    echo -e "${BLUE}Health Score: ${healthy}/${total} services healthy${NC}"
}

show_logs() {
    echo -e "${BLUE}📋 PC2 Services Logs:${NC}"
    cd "$PROJECT_ROOT"
    
    if [[ $# -gt 1 ]]; then
        # Show logs for specific service
        docker-compose -f "$COMPOSE_FILE" logs -f "$2"
    else
        # Show logs for all services
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

run_health_check() {
    echo -e "${BLUE}🏥 Running comprehensive health check...${NC}"
    cd "$PROJECT_ROOT"
    
    # Check if services are running
    echo -e "${YELLOW}📊 Container Status:${NC}"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo -e "${YELLOW}🔍 Individual Health Checks:${NC}"
    
    # Health check for each service
    local services=(
        "observability-hub:9100"
        "memory-orchestrator-service:8140"
        "tiered-responder:8100"
        "resource-manager:8113"
        "advanced-router:8129"
        "remote-connector-agent:8124"
    )
    
    for service_port in "${services[@]}"; do
        IFS=':' read -r service port <<< "$service_port"
        container_name="pc2-${service//-/-}"
        
        if docker exec "$container_name" curl -f "http://localhost:$port/health" &>/dev/null; then
            echo -e "${GREEN}✅ $service ($port)${NC}"
        else
            echo -e "${RED}❌ $service ($port)${NC}"
        fi
    done
    
    echo ""
    echo -e "${YELLOW}🌐 Cross-Machine Connectivity:${NC}"
    
    # Test MainPC connectivity
    if curl -f "http://$MAINPC_IP:26002/health" &>/dev/null; then
        echo -e "${GREEN}✅ MainPC connectivity ($MAINPC_IP:26002)${NC}"
    else
        echo -e "${RED}❌ MainPC connectivity ($MAINPC_IP:26002)${NC}"
    fi
    
    # Test PC2 external access
    if curl -f "http://$PC2_IP:7100/health" &>/dev/null; then
        echo -e "${GREEN}✅ PC2 external access ($PC2_IP:7100)${NC}"
    else
        echo -e "${RED}❌ PC2 external access ($PC2_IP:7100)${NC}"
    fi
}

test_connectivity() {
    echo -e "${BLUE}🔗 Testing cross-machine connectivity...${NC}"
    
    echo -e "${YELLOW}Testing PC2 → MainPC:${NC}"
    echo "  MainPC RequestCoordinator: http://$MAINPC_IP:26002"
    echo "  MainPC ObservabilityHub: http://$MAINPC_IP:9000"
    
    echo -e "${YELLOW}Testing MainPC → PC2:${NC}"
    echo "  PC2 TieredResponder: http://$PC2_IP:7100"
    echo "  PC2 AdvancedRouter: http://$PC2_IP:7129"
    echo "  PC2 ObservabilityHub: http://$PC2_IP:9000"
    
    echo ""
    echo -e "${YELLOW}Running connectivity tests...${NC}"
    
    # Test each endpoint
    for endpoint in \
        "MainPC RequestCoordinator:http://$MAINPC_IP:26002/health" \
        "PC2 TieredResponder:http://$PC2_IP:7100/health" \
        "PC2 ObservabilityHub:http://$PC2_IP:9000/health"; do
        
        IFS=':' read -r name url <<< "$endpoint"
        if curl -f "$url" &>/dev/null; then
            echo -e "${GREEN}✅ $name${NC}"
        else
            echo -e "${RED}❌ $name${NC}"
        fi
    done
}

clean_system() {
    echo -e "${BLUE}🧹 Cleaning PC2 system...${NC}"
    cd "$PROJECT_ROOT"
    
    # Stop services
    docker-compose -f "$COMPOSE_FILE" down
    
    # Remove containers
    docker-compose -f "$COMPOSE_FILE" rm -f
    
    # Remove images (optional)
    read -p "Remove PC2 Docker images? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker images | grep "pc2-" | awk '{print $3}' | xargs -r docker rmi
    fi
    
    # Clean volumes (optional)
    read -p "Remove PC2 volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume ls | grep "pc2_" | awk '{print $2}' | xargs -r docker volume rm
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

start_monitoring() {
    echo -e "${BLUE}📊 Starting monitoring dashboard...${NC}"
    echo "Opening PC2 ObservabilityHub dashboard..."
    echo "URL: http://$PC2_IP:9000"
    
    # Try to open in browser (Linux)
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://$PC2_IP:9000" &
    fi
}

# Main script logic
case "${1:-help}" in
    "build")
        print_header
        check_requirements
        build_images
        ;;
    "start")
        print_header
        check_requirements
        start_services
        ;;
    "stop")
        print_header
        stop_services
        ;;
    "restart")
        print_header
        check_requirements
        restart_services
        ;;
    "status")
        print_header
        show_status
        ;;
    "logs")
        show_logs "$@"
        ;;
    "health")
        print_header
        run_health_check
        ;;
    "test")
        print_header
        test_connectivity
        ;;
    "clean")
        print_header
        clean_system
        ;;
    "monitor")
        print_header
        start_monitoring
        ;;
    "help"|*)
        print_header
        print_usage
        ;;
esac