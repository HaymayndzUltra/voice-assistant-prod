#!/bin/bash
# PC2 Docker Environment Stop Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="pc2_code/docker/docker-compose.yml"
PROJECT_NAME="pc2-agents"

echo -e "${YELLOW}Stopping PC2 Docker Environment...${NC}"

# Function to stop services gracefully
stop_services() {
    echo -e "${YELLOW}Stopping all PC2 services...${NC}"
    
    # Stop services in reverse dependency order
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME stop
    
    echo -e "${GREEN}All services stopped${NC}"
}

# Function to remove containers
remove_containers() {
    read -p "Remove all PC2 containers? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing containers...${NC}"
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME rm -f
        echo -e "${GREEN}Containers removed${NC}"
    fi
}

# Function to remove volumes
remove_volumes() {
    read -p "Remove all PC2 volumes? This will delete all data! (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Removing volumes...${NC}"
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down -v
        echo -e "${GREEN}Volumes removed${NC}"
    fi
}

# Function to show final status
show_status() {
    echo -e "\n${GREEN}PC2 Docker Environment Status:${NC}"
    
    # Check if any containers are still running
    running=$(docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps -q | wc -l)
    if [ "$running" -eq 0 ]; then
        echo -e "${GREEN}✓ All PC2 services stopped${NC}"
    else
        echo -e "${RED}✗ $running services still running${NC}"
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
    fi
}

# Main execution
main() {
    echo -e "${GREEN}=== PC2 Docker Environment Shutdown ===${NC}\n"
    
    # Stop services
    stop_services
    
    # Optional cleanup
    remove_containers
    remove_volumes
    
    # Show final status
    show_status
    
    echo -e "\n${GREEN}PC2 Docker environment shutdown complete${NC}"
}

# Run main function
main