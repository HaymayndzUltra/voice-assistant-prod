#!/bin/bash
# =============================================================================
# AI SYSTEM DOCKER DEPLOYMENT SCRIPT
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
PC2_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.pc2.yml"

echo -e "${BLUE}🚀 AI System Docker Deployment Script${NC}"
echo -e "${BLUE}======================================${NC}"

# Function to print colored output
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check NVIDIA Docker runtime (for GPU containers)
    if ! docker info | grep -q nvidia; then
        log_warning "NVIDIA Docker runtime not detected. GPU containers may not work."
    fi
    
    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to create environment file
setup_environment() {
    log_info "Setting up environment configuration..."
    
    ENV_FILE="${PROJECT_ROOT}/.env"
    ENV_TEMPLATE="${PROJECT_ROOT}/env.template"
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_TEMPLATE" ]; then
            log_info "Creating .env file from template..."
            cp "$ENV_TEMPLATE" "$ENV_FILE"
            log_success "Environment file created: $ENV_FILE"
            log_warning "Please review and modify .env file as needed"
        else
            log_error "Environment template not found: $ENV_TEMPLATE"
            exit 1
        fi
    else
        log_info "Environment file already exists: $ENV_FILE"
    fi
}

# Function to create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    cd "$PROJECT_ROOT"
    
    # Create log directories
    mkdir -p logs/{mainpc,pc2}/{core-platform,model-manager-gpu,memory-stack,utility-gpu,reasoning-gpu,vision-gpu,language-stack-gpu,audio-emotion}
    mkdir -p logs/pc2/{vision-dream-gpu,memory-reasoning-gpu,tutor-suite-cpu,infra-core-cpu}
    
    # Create data directories
    mkdir -p data/{mainpc,pc2}
    mkdir -p config/{mainpc,pc2}
    
    # Create cache directories
    mkdir -p cache/{models,embeddings}
    
    # Ensure models directory exists and is accessible
    if [ ! -d "models" ]; then
        log_warning "Models directory not found. Creating empty models directory."
        mkdir -p models/{gguf,nllb-200-distilled-600M}
    fi
    
    # Set proper permissions
    chmod -R 755 logs data config cache 2>/dev/null || true
    
    log_success "Directories created successfully"
}

# Function to create cross-machine network
setup_networks() {
    log_info "Setting up Docker networks..."
    
    # Create cross-machine network if it doesn't exist
    if ! docker network ls | grep -q "cross_machine"; then
        log_info "Creating cross-machine network..."
        docker network create cross_machine \
            --driver bridge \
            --subnet 172.22.0.0/16 \
            --attachable || true
        log_success "Cross-machine network created"
    else
        log_info "Cross-machine network already exists"
    fi
}

# Function to build images
build_images() {
    local mode=$1
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    case $mode in
        "mainpc")
            log_info "Building MainPC images..."
            docker-compose -f "$COMPOSE_FILE" build
            ;;
        "pc2")
            log_info "Building PC2 images..."
            docker-compose -f "$PC2_COMPOSE_FILE" build
            ;;
        "all")
            log_info "Building all images..."
            docker-compose -f "$COMPOSE_FILE" build
            if [ -f "$PC2_COMPOSE_FILE" ]; then
                docker-compose -f "$PC2_COMPOSE_FILE" build
            fi
            ;;
        *)
            log_error "Invalid build mode: $mode"
            exit 1
            ;;
    esac
    
    log_success "Docker images built successfully"
}

# Function to deploy containers
deploy_containers() {
    local mode=$1
    log_info "Deploying containers..."
    
    cd "$PROJECT_ROOT"
    
    case $mode in
        "mainpc")
            log_info "Deploying MainPC containers..."
            docker-compose -f "$COMPOSE_FILE" up -d
            ;;
        "pc2")
            log_info "Deploying PC2 containers..."
            docker-compose -f "$PC2_COMPOSE_FILE" up -d
            ;;
        "all")
            log_info "Deploying all containers..."
            docker-compose -f "$COMPOSE_FILE" up -d
            if [ -f "$PC2_COMPOSE_FILE" ]; then
                docker-compose -f "$PC2_COMPOSE_FILE" up -d
            fi
            ;;
        *)
            log_error "Invalid deployment mode: $mode"
            exit 1
            ;;
    esac
    
    log_success "Containers deployed successfully"
}

# Function to show container status
show_status() {
    log_info "Container Status:"
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Show MainPC containers
    echo -e "${BLUE}MainPC Containers:${NC}"
    docker-compose -f "$COMPOSE_FILE" ps
    echo ""
    
    # Show PC2 containers if file exists
    if [ -f "$PC2_COMPOSE_FILE" ]; then
        echo -e "${BLUE}PC2 Containers:${NC}"
        docker-compose -f "$PC2_COMPOSE_FILE" ps
        echo ""
    fi
    
    # Show networks
    echo -e "${BLUE}Networks:${NC}"
    docker network ls | grep -E "(cross_machine|mainpc|pc2)"
    echo ""
    
    # Show volumes
    echo -e "${BLUE}Volumes:${NC}"
    docker volume ls | grep -E "(ai-system|models|cache)"
}

# Function to show help
show_help() {
    echo "AI System Docker Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build [mainpc|pc2|all]    Build Docker images"
    echo "  deploy [mainpc|pc2|all]   Deploy containers"
    echo "  start [mainpc|pc2|all]    Build and deploy containers"
    echo "  stop [mainpc|pc2|all]     Stop containers"
    echo "  restart [mainpc|pc2|all]  Restart containers"
    echo "  status                    Show container status"
    echo "  logs [container]          Show container logs"
    echo "  cleanup                   Remove all containers and images"
    echo "  help                      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start mainpc           # Build and deploy MainPC containers only"
    echo "  $0 deploy all             # Deploy all containers"
    echo "  $0 logs model-manager-gpu # Show logs for model manager"
    echo "  $0 status                 # Show all container status"
}

# Main script logic
main() {
    local command=$1
    local target=${2:-"all"}
    
    case $command in
        "build")
            check_prerequisites
            setup_environment
            create_directories
            setup_networks
            build_images "$target"
            ;;
        "deploy")
            check_prerequisites
            setup_environment
            create_directories
            setup_networks
            deploy_containers "$target"
            ;;
        "start")
            check_prerequisites
            setup_environment
            create_directories
            setup_networks
            build_images "$target"
            deploy_containers "$target"
            show_status
            ;;
        "stop")
            cd "$PROJECT_ROOT"
            if [ "$target" = "mainpc" ] || [ "$target" = "all" ]; then
                docker-compose -f "$COMPOSE_FILE" down
            fi
            if [ "$target" = "pc2" ] || [ "$target" = "all" ]; then
                docker-compose -f "$PC2_COMPOSE_FILE" down 2>/dev/null || true
            fi
            log_success "Containers stopped"
            ;;
        "restart")
            cd "$PROJECT_ROOT"
            if [ "$target" = "mainpc" ] || [ "$target" = "all" ]; then
                docker-compose -f "$COMPOSE_FILE" restart
            fi
            if [ "$target" = "pc2" ] || [ "$target" = "all" ]; then
                docker-compose -f "$PC2_COMPOSE_FILE" restart 2>/dev/null || true
            fi
            log_success "Containers restarted"
            ;;
        "status")
            show_status
            ;;
        "logs")
            cd "$PROJECT_ROOT"
            if [ -n "$target" ]; then
                docker logs -f "$target" 2>/dev/null || \
                docker-compose -f "$COMPOSE_FILE" logs -f "$target" 2>/dev/null || \
                docker-compose -f "$PC2_COMPOSE_FILE" logs -f "$target" 2>/dev/null || \
                log_error "Container not found: $target"
            else
                log_error "Container name required for logs command"
            fi
            ;;
        "cleanup")
            cd "$PROJECT_ROOT"
            log_warning "This will remove all containers, images, and volumes. Continue? (y/N)"
            read -r confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                docker-compose -f "$COMPOSE_FILE" down -v --rmi all 2>/dev/null || true
                docker-compose -f "$PC2_COMPOSE_FILE" down -v --rmi all 2>/dev/null || true
                docker network rm cross_machine 2>/dev/null || true
                log_success "Cleanup completed"
            else
                log_info "Cleanup cancelled"
            fi
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "")
            log_error "No command specified"
            show_help
            exit 1
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 