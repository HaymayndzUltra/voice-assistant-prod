#!/bin/bash
# Production secrets management script for AI System
# Usage: ./scripts/manage-secrets.sh [create|update|delete|list] [secret_name]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_PREFIX="ai_system"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if Docker is running and supports secrets
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        error "Docker is not running or not accessible"
    fi
    
    if ! docker swarm info >/dev/null 2>&1; then
        warn "Docker swarm not initialized. Initializing..."
        docker swarm init --advertise-addr 127.0.0.1
    fi
}

create_secret() {
    local secret_name="$1"
    local full_name="${SECRETS_PREFIX}_${secret_name}"
    
    if docker secret ls --format "{{.Name}}" | grep -q "^${full_name}$"; then
        warn "Secret ${full_name} already exists. Use 'update' to modify."
        return 1
    fi
    
    echo "Enter the secret value for ${secret_name}:"
    read -rs secret_value
    
    if [[ -z "$secret_value" ]]; then
        error "Secret value cannot be empty"
    fi
    
    echo "$secret_value" | docker secret create "$full_name" -
    log "Created secret: ${full_name}"
}

update_secret() {
    local secret_name="$1"
    local full_name="${SECRETS_PREFIX}_${secret_name}"
    local temp_name="${full_name}_temp"
    
    if ! docker secret ls --format "{{.Name}}" | grep -q "^${full_name}$"; then
        error "Secret ${full_name} does not exist. Use 'create' first."
    fi
    
    echo "Enter the new secret value for ${secret_name}:"
    read -rs secret_value
    
    if [[ -z "$secret_value" ]]; then
        error "Secret value cannot be empty"
    fi
    
    # Create temporary secret
    echo "$secret_value" | docker secret create "$temp_name" -
    
    # Remove old secret
    docker secret rm "$full_name"
    
    # Rename temporary secret
    # Note: Docker doesn't support renaming, so we recreate
    docker secret rm "$temp_name"
    echo "$secret_value" | docker secret create "$full_name" -
    
    log "Updated secret: ${full_name}"
    warn "Services using this secret need to be restarted to pick up changes"
}

delete_secret() {
    local secret_name="$1"
    local full_name="${SECRETS_PREFIX}_${secret_name}"
    
    if ! docker secret ls --format "{{.Name}}" | grep -q "^${full_name}$"; then
        warn "Secret ${full_name} does not exist"
        return 1
    fi
    
    echo "Are you sure you want to delete secret ${full_name}? (y/N)"
    read -r confirmation
    
    if [[ "$confirmation" =~ ^[Yy]$ ]]; then
        docker secret rm "$full_name"
        log "Deleted secret: ${full_name}"
    else
        log "Operation cancelled"
    fi
}

list_secrets() {
    log "AI System secrets:"
    docker secret ls --filter "name=${SECRETS_PREFIX}_" --format "table {{.Name}}\t{{.CreatedAt}}"
}

init_default_secrets() {
    log "Initializing default secrets..."
    
    local default_secrets=(
        "openai_key"
        "anthropic_key"
        "db_password"
        "redis_password"
    )
    
    for secret in "${default_secrets[@]}"; do
        if ! docker secret ls --format "{{.Name}}" | grep -q "^${SECRETS_PREFIX}_${secret}$"; then
            log "Creating secret: ${secret}"
            create_secret "$secret"
        else
            log "Secret ${secret} already exists, skipping"
        fi
    done
    
    log "Default secrets initialization complete"
}

show_usage() {
    cat << EOF
Usage: $0 [COMMAND] [SECRET_NAME]

Commands:
    create <name>    Create a new secret
    update <name>    Update an existing secret
    delete <name>    Delete a secret
    list             List all AI system secrets
    init             Initialize default secrets
    help             Show this help message

Examples:
    $0 create openai_key
    $0 update db_password
    $0 delete redis_password
    $0 list
    $0 init

Note: Secret names will be prefixed with '${SECRETS_PREFIX}_'
EOF
}

main() {
    check_docker
    
    case "${1:-help}" in
        "create")
            [[ $# -eq 2 ]] || error "Usage: $0 create <secret_name>"
            create_secret "$2"
            ;;
        "update")
            [[ $# -eq 2 ]] || error "Usage: $0 update <secret_name>"
            update_secret "$2"
            ;;
        "delete")
            [[ $# -eq 2 ]] || error "Usage: $0 delete <secret_name>"
            delete_secret "$2"
            ;;
        "list")
            list_secrets
            ;;
        "init")
            init_default_secrets
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            error "Unknown command: $1. Use 'help' for usage information."
            ;;
    esac
}

main "$@"