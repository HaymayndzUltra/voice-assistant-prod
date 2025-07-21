#!/bin/bash

# AI System Master Docker Startup Script
# Manages both MainPC and PC2 systems based on actual configuration files

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAINPC_SCRIPT="${SCRIPT_DIR}/start_mainpc_docker.sh"
PC2_SCRIPT="${SCRIPT_DIR}/start_pc2_docker.sh"

# Banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    AI System Docker Manager                 ║"
echo "║                                                              ║"
echo "║  MainPC: 52 agents in 11 groups (main_pc_code/config)      ║"
echo "║  PC2:    23 agents with cross-machine deps (pc2_code/config)║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Usage function
usage() {
    echo -e "${BLUE}Usage: $0 [COMMAND] [OPTIONS]${NC}"
    echo ""
    echo -e "${YELLOW}COMMANDS:${NC}"
    echo -e "  ${GREEN}mainpc${NC}     Start MainPC system only"
    echo -e "  ${GREEN}pc2${NC}        Start PC2 system only"
    echo -e "  ${GREEN}both${NC}       Start both systems (MainPC first, then PC2)"
    echo -e "  ${GREEN}status${NC}     Check status of all services"
    echo -e "  ${GREEN}stop${NC}       Stop all services"
    echo -e "  ${GREEN}restart${NC}    Restart all services"
    echo -e "  ${GREEN}logs${NC}       Show logs for all services"
    echo -e "  ${GREEN}health${NC}     Run comprehensive health check"
    echo ""
    echo -e "${YELLOW}OPTIONS:${NC}"
    echo -e "  ${GREEN}--force${NC}    Force restart even if services are running"
    echo -e "  ${GREEN}--verbose${NC}  Enable verbose output"
    echo -e "  ${GREEN}--no-wait${NC}  Don't wait for health checks"
    echo ""
    echo -e "${YELLOW}EXAMPLES:${NC}"
    echo -e "  $0 mainpc           # Start only MainPC system"
    echo -e "  $0 pc2              # Start only PC2 system"
    echo -e "  $0 both             # Start both systems in proper order"
    echo -e "  $0 status           # Check all service status"
    echo -e "  $0 stop             # Stop all services"
    echo ""
    echo -e "${YELLOW}CONFIGURATION:${NC}"
    echo -e "  MainPC Config: ${BLUE}main_pc_code/config/startup_config.yaml${NC}"
    echo -e "  PC2 Config:    ${BLUE}pc2_code/config/startup_config.yaml${NC}"
    echo -e "  MainPC Network: ${BLUE}172.20.0.0/16${NC}"
    echo -e "  PC2 Network:    ${BLUE}172.21.0.0/16${NC}"
}

# Function to check if script exists and is executable
check_script() {
    local script_path=$1
    local system_name=$2
    
    if [ ! -f "$script_path" ]; then
        echo -e "${RED}Error: ${system_name} startup script not found: ${script_path}${NC}"
        return 1
    fi
    
    if [ ! -x "$script_path" ]; then
        echo -e "${RED}Error: ${system_name} startup script not executable: ${script_path}${NC}"
        echo -e "${YELLOW}Run: chmod +x ${script_path}${NC}"
        return 1
    fi
    
    return 0
}

# Function to get service status
get_service_status() {
    local compose_file=$1
    local service_name=$2
    
    if [ -f "$compose_file" ]; then
        local status=$(docker compose -f "$compose_file" ps --services --filter "status=running" 2>/dev/null | grep -c "^${service_name}$" || echo "0")
        if [ "$status" -gt "0" ]; then
            echo "running"
        else
            echo "stopped"
        fi
    else
        echo "unknown"
    fi
}

# Function to show system status
show_status() {
    echo -e "${BLUE}=== AI System Status ===${NC}"
    echo ""
    
    # MainPC Status
    echo -e "${YELLOW}MainPC System:${NC}"
    if [ -f "docker/docker-compose.mainpc.yml" ]; then
        local mainpc_running=$(docker compose -f "docker/docker-compose.mainpc.yml" ps --services --filter "status=running" 2>/dev/null | wc -l)
        local mainpc_total=$(docker compose -f "docker/docker-compose.mainpc.yml" config --services 2>/dev/null | wc -l)
        echo -e "  Status: ${GREEN}${mainpc_running}/${mainpc_total} services running${NC}"
        
        if [ "$mainpc_running" -gt "0" ]; then
            echo -e "  Key Services:"
            for service in "service-registry" "system-digital-twin" "request-coordinator" "observability-hub"; do
                local status=$(get_service_status "docker/docker-compose.mainpc.yml" "$service")
                if [ "$status" = "running" ]; then
                    echo -e "    ✓ ${service}"
                else
                    echo -e "    ✗ ${service}"
                fi
            done
        fi
    else
        echo -e "  Status: ${RED}docker-compose.mainpc.yml not found${NC}"
    fi
    echo ""
    
    # PC2 Status
    echo -e "${YELLOW}PC2 System:${NC}"
    if [ -f "docker/docker-compose.pc2.yml" ]; then
        local pc2_running=$(docker compose -f "docker/docker-compose.pc2.yml" ps --services --filter "status=running" 2>/dev/null | wc -l)
        local pc2_total=$(docker compose -f "docker/docker-compose.pc2.yml" config --services 2>/dev/null | wc -l)
        echo -e "  Status: ${GREEN}${pc2_running}/${pc2_total} services running${NC}"
        
        if [ "$pc2_running" -gt "0" ]; then
            echo -e "  Key Services:"
            for service in "observability-hub" "memory-orchestrator" "tiered-responder" "unified-web-agent"; do
                local status=$(get_service_status "docker/docker-compose.pc2.yml" "$service")
                if [ "$status" = "running" ]; then
                    echo -e "    ✓ ${service}"
                else
                    echo -e "    ✗ ${service}"
                fi
            done
        fi
    else
        echo -e "  Status: ${RED}docker-compose.pc2.yml not found${NC}"
    fi
    echo ""
    
    # Network Status
    echo -e "${YELLOW}Networks:${NC}"
    for network in "ai_system_network" "ai_system_net"; do
        if docker network ls | grep -q "$network"; then
            echo -e "  ✓ ${network}"
        else
            echo -e "  ✗ ${network}"
        fi
    done
    echo ""
}

# Function to stop all services
stop_services() {
    echo -e "${BLUE}=== Stopping AI System Services ===${NC}"
    
    # Stop PC2 first (dependent system)
    if [ -f "docker/docker-compose.pc2.yml" ]; then
        echo -e "${YELLOW}Stopping PC2 services...${NC}"
        docker compose -f "docker/docker-compose.pc2.yml" down || true
    fi
    
    # Stop MainPC
    if [ -f "docker/docker-compose.mainpc.yml" ]; then
        echo -e "${YELLOW}Stopping MainPC services...${NC}"
        docker compose -f "docker/docker-compose.mainpc.yml" down || true
    fi
    
    echo -e "${GREEN}✓ All services stopped${NC}"
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}=== AI System Logs ===${NC}"
    echo -e "${YELLOW}Choose system to view logs:${NC}"
    echo "1) MainPC logs"
    echo "2) PC2 logs"
    echo "3) Both systems"
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            if [ -f "docker/docker-compose.mainpc.yml" ]; then
                docker compose -f "docker/docker-compose.mainpc.yml" logs -f
            else
                echo -e "${RED}MainPC compose file not found${NC}"
            fi
            ;;
        2)
            if [ -f "docker/docker-compose.pc2.yml" ]; then
                docker compose -f "docker/docker-compose.pc2.yml" logs -f
            else
                echo -e "${RED}PC2 compose file not found${NC}"
            fi
            ;;
        3)
            echo -e "${YELLOW}Opening logs in separate terminals...${NC}"
            if command -v gnome-terminal >/dev/null 2>&1; then
                gnome-terminal -- bash -c "docker compose -f docker/docker-compose.mainpc.yml logs -f; read"
                gnome-terminal -- bash -c "docker compose -f docker/docker-compose.pc2.yml logs -f; read"
            else
                echo -e "${RED}Multiple terminal logs requires gnome-terminal${NC}"
                echo -e "${YELLOW}Showing MainPC logs (Ctrl+C to switch to PC2):${NC}"
                docker compose -f "docker/docker-compose.mainpc.yml" logs -f
            fi
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            ;;
    esac
}

# Function to run health check
run_health_check() {
    echo -e "${BLUE}=== AI System Health Check ===${NC}"
    echo ""
    
    # Check MainPC
    echo -e "${YELLOW}MainPC Health Check:${NC}"
    if [ -f "docker/docker-compose.mainpc.yml" ]; then
        for port in 7200 7220 26002 9000; do
            if timeout 5 bash -c "</dev/tcp/localhost/${port}" 2>/dev/null; then
                echo -e "  ✓ Port ${port} (responding)"
            else
                echo -e "  ✗ Port ${port} (not responding)"
            fi
        done
    fi
    echo ""
    
    # Check PC2
    echo -e "${YELLOW}PC2 Health Check:${NC}"
    if [ -f "docker/docker-compose.pc2.yml" ]; then
        for port in 9000 7140 7100 7126; do
            if timeout 5 bash -c "</dev/tcp/localhost/${port}" 2>/dev/null; then
                echo -e "  ✓ Port ${port} (responding)"
            else
                echo -e "  ✗ Port ${port} (not responding)"
            fi
        done
    fi
    echo ""
    
    # Check cross-machine connectivity (if PC2 is running)
    echo -e "${YELLOW}Cross-Machine Connectivity:${NC}"
    MAINPC_HOST="192.168.100.16"
    for port in 7200 9000 6379; do
        if timeout 5 bash -c "</dev/tcp/${MAINPC_HOST}/${port}" 2>/dev/null; then
            echo -e "  ✓ ${MAINPC_HOST}:${port} (accessible)"
        else
            echo -e "  ✗ ${MAINPC_HOST}:${port} (not accessible)"
        fi
    done
}

# Parse command line arguments
COMMAND=""
FORCE=false
VERBOSE=false
NO_WAIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        mainpc|pc2|both|status|stop|restart|logs|health)
            COMMAND="$1"
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --no-wait)
            NO_WAIT=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Check if command was provided
if [ -z "$COMMAND" ]; then
    usage
    exit 1
fi

# Change to script directory
cd "$SCRIPT_DIR"

# Execute command
case $COMMAND in
    mainpc)
        echo -e "${BLUE}Starting MainPC system...${NC}"
        check_script "$MAINPC_SCRIPT" "MainPC" || exit 1
        "$MAINPC_SCRIPT"
        ;;
    
    pc2)
        echo -e "${BLUE}Starting PC2 system...${NC}"
        check_script "$PC2_SCRIPT" "PC2" || exit 1
        "$PC2_SCRIPT"
        ;;
    
    both)
        echo -e "${BLUE}Starting both systems (MainPC first, then PC2)...${NC}"
        check_script "$MAINPC_SCRIPT" "MainPC" || exit 1
        check_script "$PC2_SCRIPT" "PC2" || exit 1
        
        echo -e "${PURPLE}=== Starting MainPC System ===${NC}"
        "$MAINPC_SCRIPT"
        
        echo ""
        echo -e "${PURPLE}=== Starting PC2 System ===${NC}"
        echo -e "${YELLOW}Waiting 30 seconds for MainPC to stabilize...${NC}"
        sleep 30
        "$PC2_SCRIPT"
        
        echo ""
        echo -e "${GREEN}🎉 Both systems started successfully!${NC}"
        echo -e "${BLUE}Run '$0 status' to check system health${NC}"
        ;;
    
    status)
        show_status
        ;;
    
    stop)
        stop_services
        ;;
    
    restart)
        echo -e "${BLUE}Restarting AI System...${NC}"
        stop_services
        echo -e "${YELLOW}Waiting 10 seconds before restart...${NC}"
        sleep 10
        
        if [ "$FORCE" = true ] || [ -f "docker/docker-compose.mainpc.yml" ] || [ -f "docker/docker-compose.pc2.yml" ]; then
            $0 both
        else
            echo -e "${RED}No compose files found to restart${NC}"
            exit 1
        fi
        ;;
    
    logs)
        show_logs
        ;;
    
    health)
        run_health_check
        ;;
    
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        exit 1
        ;;
esac