#!/bin/bash

# AI System Docker Management Script
# This script manages Docker deployments for both MainPC and PC2 components

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Define paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
MAINPC_DIR="$DOCKER_DIR/mainpc"
PC2_DIR="$DOCKER_DIR/pc2"
SHARED_DIR="$DOCKER_DIR/shared"
CERT_DIR="$PROJECT_ROOT/certificates"
LOG_DIR="$PROJECT_ROOT/logs"

# Function to display menu
show_menu() {
    clear
    echo -e "${BLUE}=== AI System Docker Management ===${NC}"
    echo -e "${BLUE}====================================${NC}"
    echo ""
    echo -e "1) ${GREEN}Deploy MainPC components${NC}"
    echo -e "2) ${GREEN}Deploy PC2 components${NC}"
    echo -e "3) ${GREEN}Deploy both systems${NC}"
    echo -e "4) ${YELLOW}View MainPC logs${NC}"
    echo -e "5) ${YELLOW}View PC2 logs${NC}"
    echo -e "6) ${RED}Stop MainPC containers${NC}"
    echo -e "7) ${RED}Stop PC2 containers${NC}"
    echo -e "8) ${RED}Stop all containers${NC}"
    echo -e "9) ${BLUE}Create shared network${NC}"
    echo -e "10) ${BLUE}Show container status${NC}"
    echo -e "0) ${RED}Exit${NC}"
    echo ""
    echo -n "Enter your choice [0-10]: "
}

# Function to create shared network
create_shared_network() {
    echo -e "${YELLOW}Creating shared network...${NC}"
    cd "$SHARED_DIR"
    docker-compose -f docker-compose.network.yml up -d
    echo -e "${GREEN}Shared network created.${NC}"
}

# Function to deploy MainPC components
deploy_mainpc() {
    echo -e "${YELLOW}Deploying MainPC components...${NC}"
    cd "$MAINPC_DIR"
    docker-compose up -d
    echo -e "${GREEN}MainPC components deployed.${NC}"
}

# Function to deploy PC2 components
deploy_pc2() {
    echo -e "${YELLOW}Deploying PC2 components...${NC}"
    cd "$PC2_DIR"
    docker-compose up -d
    echo -e "${GREEN}PC2 components deployed.${NC}"
}

# Function to deploy both systems
deploy_both() {
    create_shared_network
    deploy_mainpc
    deploy_pc2
}

# Function to view MainPC logs
view_mainpc_logs() {
    echo -e "${YELLOW}Viewing MainPC logs...${NC}"
    cd "$MAINPC_DIR"
    docker-compose logs -f
}

# Function to view PC2 logs
view_pc2_logs() {
    echo -e "${YELLOW}Viewing PC2 logs...${NC}"
    cd "$PC2_DIR"
    docker-compose logs -f
}

# Function to stop MainPC containers
stop_mainpc() {
    echo -e "${RED}Stopping MainPC containers...${NC}"
    cd "$MAINPC_DIR"
    docker-compose down
    echo -e "${GREEN}MainPC containers stopped.${NC}"
}

# Function to stop PC2 containers
stop_pc2() {
    echo -e "${RED}Stopping PC2 containers...${NC}"
    cd "$PC2_DIR"
    docker-compose down
    echo -e "${GREEN}PC2 containers stopped.${NC}"
}

# Function to stop all containers
stop_all() {
    stop_mainpc
    stop_pc2
    echo -e "${RED}Stopping shared network...${NC}"
    cd "$SHARED_DIR"
    docker-compose -f docker-compose.network.yml down
    echo -e "${GREEN}All containers stopped.${NC}"
}

# Function to show container status
show_status() {
    echo -e "${BLUE}=== MainPC Container Status ===${NC}"
    cd "$MAINPC_DIR"
    docker-compose ps
    
    echo -e "${BLUE}=== PC2 Container Status ===${NC}"
    cd "$PC2_DIR"
    docker-compose ps
    
    echo -e "${BLUE}=== Docker Networks ===${NC}"
    docker network ls | grep ai
}

# Create necessary directories
mkdir -p "$CERT_DIR" "$LOG_DIR"

# Generate ZMQ certificates if they don't exist
if [ ! -f "$CERT_DIR/client.key_secret" ] || [ ! -f "$CERT_DIR/server.key_secret" ]; then
    echo -e "${YELLOW}Generating ZMQ certificates...${NC}"
    python "$PROJECT_ROOT/scripts/generate_zmq_certificates.py"
fi

# Main loop
while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            create_shared_network
            deploy_mainpc
            read -p "Press Enter to continue..."
            ;;
        2)
            create_shared_network
            deploy_pc2
            read -p "Press Enter to continue..."
            ;;
        3)
            deploy_both
            read -p "Press Enter to continue..."
            ;;
        4)
            view_mainpc_logs
            ;;
        5)
            view_pc2_logs
            ;;
        6)
            stop_mainpc
            read -p "Press Enter to continue..."
            ;;
        7)
            stop_pc2
            read -p "Press Enter to continue..."
            ;;
        8)
            stop_all
            read -p "Press Enter to continue..."
            ;;
        9)
            create_shared_network
            read -p "Press Enter to continue..."
            ;;
        10)
            show_status
            read -p "Press Enter to continue..."
            ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Press Enter to continue...${NC}"
            read
            ;;
    esac
done 