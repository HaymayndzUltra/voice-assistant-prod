#!/bin/bash
# AI System Backup and Disaster Recovery Script
# Handles nightly backups, incremental snapshots, and full system restore

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BASE_DIR="${BACKUP_BASE_DIR:-/backup/ai-system}"
REMOTE_BACKUP_HOST="${REMOTE_BACKUP_HOST:-backup.local}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
COMPRESSION_LEVEL="${COMPRESSION_LEVEL:-6}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Critical paths to backup
CRITICAL_PATHS=(
    "data/unified_memory.db"
    "models/"
    "logs/"
    "config/"
    "memory-bank/"
    ".env"
    "docker-compose*.yml"
    "k8s/"
    "scripts/"
)

# Docker volumes to backup
DOCKER_VOLUMES=(
    "ai_system_models"
    "ai_system_data"
    "ai_system_logs"
    "ai_system_config"
    "prometheus_data"
    "grafana_data"
)

# Kubernetes volumes (if running on k8s)
K8S_NAMESPACES=(
    "ai-system-infra"
    "ai-system-core"
    "ai-system-gpu"
    "monitoring"
)

# Create backup directory structure
create_backup_dirs() {
    local timestamp=$1
    local backup_dir="${BACKUP_BASE_DIR}/${timestamp}"
    
    mkdir -p "${backup_dir}"/{files,volumes,databases,kubernetes,logs}
    echo "${backup_dir}"
}

# Backup file system paths
backup_filesystem() {
    local backup_dir=$1
    log "Starting filesystem backup..."
    
    for path in "${CRITICAL_PATHS[@]}"; do
        if [[ -e "$path" ]]; then
            local dest_path="${backup_dir}/files/$(basename "$path")"
            
            if [[ -d "$path" ]]; then
                log "Backing up directory: $path"
                tar -czf "${dest_path}.tar.gz" -C "$(dirname "$path")" "$(basename "$path")"
            else
                log "Backing up file: $path"
                cp "$path" "$dest_path"
            fi
            
            # Generate checksum
            if [[ -d "$path" ]]; then
                sha256sum "${dest_path}.tar.gz" > "${dest_path}.tar.gz.sha256"
            else
                sha256sum "$dest_path" > "${dest_path}.sha256"
            fi
        else
            warn "Path not found: $path"
        fi
    done
    
    log "Filesystem backup completed"
}

# Backup Docker volumes
backup_docker_volumes() {
    local backup_dir=$1
    log "Starting Docker volumes backup..."
    
    if ! command -v docker &> /dev/null; then
        warn "Docker not found, skipping volume backup"
        return
    fi
    
    for volume in "${DOCKER_VOLUMES[@]}"; do
        if docker volume inspect "$volume" &>/dev/null; then
            log "Backing up Docker volume: $volume"
            
            # Create temporary container to access volume
            docker run --rm \
                -v "$volume":/volume \
                -v "${backup_dir}/volumes":/backup \
                alpine:latest \
                tar -czf "/backup/${volume}.tar.gz" -C /volume .
            
            # Generate checksum
            sha256sum "${backup_dir}/volumes/${volume}.tar.gz" > "${backup_dir}/volumes/${volume}.tar.gz.sha256"
        else
            warn "Docker volume not found: $volume"
        fi
    done
    
    log "Docker volumes backup completed"
}

# Backup databases
backup_databases() {
    local backup_dir=$1
    log "Starting database backup..."
    
    # SQLite databases
    for db_file in data/*.db; do
        if [[ -f "$db_file" ]]; then
            local db_name=$(basename "$db_file" .db)
            log "Backing up SQLite database: $db_name"
            
            # Use VACUUM INTO for consistent backup
            sqlite3 "$db_file" "VACUUM INTO '${backup_dir}/databases/${db_name}_$(date +%Y%m%d_%H%M%S).db'"
            
            # Generate checksum
            sha256sum "${backup_dir}/databases/${db_name}_$(date +%Y%m%d_%H%M%S).db" > \
                      "${backup_dir}/databases/${db_name}_$(date +%Y%m%d_%H%M%S).db.sha256"
        fi
    done
    
    # PostgreSQL (if running)
    if command -v pg_dump &> /dev/null && systemctl is-active postgresql &>/dev/null; then
        log "Backing up PostgreSQL databases..."
        pg_dumpall -U postgres | gzip > "${backup_dir}/databases/postgresql_$(date +%Y%m%d_%H%M%S).sql.gz"
        sha256sum "${backup_dir}/databases/postgresql_$(date +%Y%m%d_%H%M%S).sql.gz" > \
                  "${backup_dir}/databases/postgresql_$(date +%Y%m%d_%H%M%S).sql.gz.sha256"
    fi
    
    # Redis (if running)
    if command -v redis-cli &> /dev/null && systemctl is-active redis &>/dev/null; then
        log "Backing up Redis..."
        redis-cli BGSAVE
        sleep 5  # Wait for background save
        cp /var/lib/redis/dump.rdb "${backup_dir}/databases/redis_$(date +%Y%m%d_%H%M%S).rdb"
        sha256sum "${backup_dir}/databases/redis_$(date +%Y%m%d_%H%M%S).rdb" > \
                  "${backup_dir}/databases/redis_$(date +%Y%m%d_%H%M%S).rdb.sha256"
    fi
    
    log "Database backup completed"
}

# Backup Kubernetes resources
backup_kubernetes() {
    local backup_dir=$1
    log "Starting Kubernetes backup..."
    
    if ! command -v kubectl &> /dev/null; then
        warn "kubectl not found, skipping Kubernetes backup"
        return
    fi
    
    # Test cluster connectivity
    if ! kubectl cluster-info &>/dev/null; then
        warn "Kubernetes cluster not accessible, skipping backup"
        return
    fi
    
    for namespace in "${K8S_NAMESPACES[@]}"; do
        if kubectl get namespace "$namespace" &>/dev/null; then
            log "Backing up Kubernetes namespace: $namespace"
            
            local ns_backup_dir="${backup_dir}/kubernetes/${namespace}"
            mkdir -p "$ns_backup_dir"
            
            # Export all resources
            kubectl get all,configmaps,secrets,pvc,ingress -n "$namespace" -o yaml > \
                "${ns_backup_dir}/resources.yaml"
            
            # Export persistent volume claims data
            local pvcs=$(kubectl get pvc -n "$namespace" -o jsonpath='{.items[*].metadata.name}')
            for pvc in $pvcs; do
                log "Backing up PVC data: $pvc"
                kubectl run backup-pod-$pvc --rm -i --restart=Never \
                    --image=alpine:latest \
                    --overrides="{
                        \"spec\": {
                            \"containers\": [{
                                \"name\": \"backup\",
                                \"image\": \"alpine:latest\",
                                \"command\": [\"tar\", \"-czf\", \"/tmp/${pvc}.tar.gz\", \"-C\", \"/data\", \".\"],
                                \"volumeMounts\": [{
                                    \"name\": \"data\",
                                    \"mountPath\": \"/data\"
                                }]
                            }],
                            \"volumes\": [{
                                \"name\": \"data\",
                                \"persistentVolumeClaim\": {
                                    \"claimName\": \"$pvc\"
                                }
                            }]
                        }
                    }" || warn "Failed to backup PVC: $pvc"
            done
        else
            warn "Kubernetes namespace not found: $namespace"
        fi
    done
    
    # Backup cluster-wide resources
    log "Backing up cluster-wide resources..."
    kubectl get nodes,clusterroles,clusterrolebindings,storageclasses -o yaml > \
        "${backup_dir}/kubernetes/cluster-resources.yaml"
    
    log "Kubernetes backup completed"
}

# Create backup manifest
create_backup_manifest() {
    local backup_dir=$1
    local timestamp=$2
    
    cat > "${backup_dir}/backup-manifest.json" << EOF
{
    "timestamp": "$timestamp",
    "hostname": "$(hostname)",
    "backup_type": "full",
    "ai_system_version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "backup_size_bytes": $(du -sb "$backup_dir" | cut -f1),
    "paths_backed_up": $(printf '%s\n' "${CRITICAL_PATHS[@]}" | jq -R . | jq -s .),
    "docker_volumes": $(printf '%s\n' "${DOCKER_VOLUMES[@]}" | jq -R . | jq -s .),
    "k8s_namespaces": $(printf '%s\n' "${K8S_NAMESPACES[@]}" | jq -R . | jq -s .),
    "checksum_algorithm": "sha256",
    "compression": "gzip",
    "retention_days": $RETENTION_DAYS
}
EOF
    
    # Generate manifest checksum
    sha256sum "${backup_dir}/backup-manifest.json" > "${backup_dir}/backup-manifest.json.sha256"
}

# Compress backup directory
compress_backup() {
    local backup_dir=$1
    local timestamp=$2
    
    log "Compressing backup..."
    
    cd "$(dirname "$backup_dir")"
    tar -czf "${backup_dir}.tar.gz" "$(basename "$backup_dir")"
    
    # Generate final checksum
    sha256sum "${backup_dir}.tar.gz" > "${backup_dir}.tar.gz.sha256"
    
    # Remove uncompressed directory
    rm -rf "$backup_dir"
    
    log "Backup compressed: ${backup_dir}.tar.gz"
}

# Upload to remote backup
upload_to_remote() {
    local backup_file=$1
    
    if [[ -n "${REMOTE_BACKUP_HOST}" && "${REMOTE_BACKUP_HOST}" != "backup.local" ]]; then
        log "Uploading to remote backup host..."
        
        # Create remote directory
        ssh "${REMOTE_BACKUP_HOST}" "mkdir -p /backup/ai-system/"
        
        # Upload backup file and checksum
        rsync -avz --progress "$backup_file" "${REMOTE_BACKUP_HOST}:/backup/ai-system/"
        rsync -avz --progress "${backup_file}.sha256" "${REMOTE_BACKUP_HOST}:/backup/ai-system/"
        
        log "Remote upload completed"
    else
        info "No remote backup host configured, skipping upload"
    fi
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Local cleanup
    find "$BACKUP_BASE_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_BASE_DIR" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
    
    # Remote cleanup (if configured)
    if [[ -n "${REMOTE_BACKUP_HOST}" && "${REMOTE_BACKUP_HOST}" != "backup.local" ]]; then
        ssh "${REMOTE_BACKUP_HOST}" \
            "find /backup/ai-system/ -name '*.tar.gz' -mtime +$RETENTION_DAYS -delete"
    fi
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    local backup_file=$1
    
    log "Verifying backup integrity..."
    
    # Check if backup file exists
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
    fi
    
    # Verify checksum
    if [[ -f "${backup_file}.sha256" ]]; then
        if sha256sum -c "${backup_file}.sha256"; then
            log "Backup integrity verified"
        else
            error "Backup integrity check failed"
        fi
    else
        warn "Checksum file not found, skipping integrity check"
    fi
    
    # Test archive extraction (first few files only)
    log "Testing archive extraction..."
    if tar -tzf "$backup_file" | head -10 &>/dev/null; then
        log "Archive extraction test passed"
    else
        error "Archive is corrupted or unreadable"
    fi
}

# Restore from backup
restore_from_backup() {
    local backup_file=$1
    local restore_type=${2:-full}
    
    log "Starting restore from: $backup_file"
    
    # Verify backup before restore
    verify_backup "$backup_file"
    
    # Create restore directory
    local restore_dir="/tmp/ai-system-restore-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$restore_dir"
    
    # Extract backup
    log "Extracting backup..."
    tar -xzf "$backup_file" -C "$restore_dir"
    
    local backup_content_dir=$(find "$restore_dir" -maxdepth 1 -type d | tail -1)
    
    case "$restore_type" in
        "full")
            restore_full "$backup_content_dir"
            ;;
        "config")
            restore_config_only "$backup_content_dir"
            ;;
        "data")
            restore_data_only "$backup_content_dir"
            ;;
        *)
            error "Unknown restore type: $restore_type"
            ;;
    esac
    
    # Cleanup restore directory
    rm -rf "$restore_dir"
    
    log "Restore completed successfully"
}

# Full system restore
restore_full() {
    local backup_content_dir=$1
    
    warn "FULL RESTORE WILL OVERWRITE EXISTING DATA!"
    echo "Are you sure you want to proceed? (yes/no)"
    read -r confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log "Restore cancelled"
        return
    fi
    
    log "Performing full system restore..."
    
    # Stop services
    log "Stopping AI system services..."
    docker-compose down 2>/dev/null || true
    kubectl delete namespace ai-system-infra ai-system-core ai-system-gpu 2>/dev/null || true
    
    # Restore files
    restore_filesystem "$backup_content_dir"
    
    # Restore databases
    restore_databases "$backup_content_dir"
    
    # Restore Docker volumes
    restore_docker_volumes "$backup_content_dir"
    
    # Restore Kubernetes resources
    restore_kubernetes "$backup_content_dir"
    
    log "Full restore completed. Please restart services manually."
}

# Restore filesystem
restore_filesystem() {
    local backup_content_dir=$1
    
    log "Restoring filesystem..."
    
    local files_dir="${backup_content_dir}/files"
    if [[ -d "$files_dir" ]]; then
        for backup_file in "$files_dir"/*; do
            local filename=$(basename "$backup_file")
            
            if [[ "$backup_file" == *.tar.gz ]]; then
                local target_name=${filename%.tar.gz}
                log "Restoring directory: $target_name"
                tar -xzf "$backup_file" -C .
            else
                log "Restoring file: $filename"
                cp "$backup_file" .
            fi
        done
    fi
}

# Restore databases
restore_databases() {
    local backup_content_dir=$1
    
    log "Restoring databases..."
    
    local db_dir="${backup_content_dir}/databases"
    if [[ -d "$db_dir" ]]; then
        for db_backup in "$db_dir"/*.db; do
            if [[ -f "$db_backup" ]]; then
                local db_name=$(basename "$db_backup" | cut -d'_' -f1)
                log "Restoring SQLite database: $db_name"
                cp "$db_backup" "data/${db_name}.db"
            fi
        done
    fi
}

# Restore Docker volumes
restore_docker_volumes() {
    local backup_content_dir=$1
    
    log "Restoring Docker volumes..."
    
    local volumes_dir="${backup_content_dir}/volumes"
    if [[ -d "$volumes_dir" ]]; then
        for volume_backup in "$volumes_dir"/*.tar.gz; do
            if [[ -f "$volume_backup" ]]; then
                local volume_name=$(basename "$volume_backup" .tar.gz)
                log "Restoring Docker volume: $volume_name"
                
                # Recreate volume
                docker volume rm "$volume_name" 2>/dev/null || true
                docker volume create "$volume_name"
                
                # Restore data
                docker run --rm \
                    -v "$volume_name":/volume \
                    -v "$volumes_dir":/backup \
                    alpine:latest \
                    tar -xzf "/backup/$(basename "$volume_backup")" -C /volume
            fi
        done
    fi
}

# Restore Kubernetes resources
restore_kubernetes() {
    local backup_content_dir=$1
    
    log "Restoring Kubernetes resources..."
    
    local k8s_dir="${backup_content_dir}/kubernetes"
    if [[ -d "$k8s_dir" ]]; then
        # Restore namespaces and resources
        for ns_dir in "$k8s_dir"/*/; do
            if [[ -d "$ns_dir" ]]; then
                local namespace=$(basename "$ns_dir")
                log "Restoring Kubernetes namespace: $namespace"
                
                kubectl create namespace "$namespace" 2>/dev/null || true
                kubectl apply -f "${ns_dir}/resources.yaml" || warn "Failed to restore some resources in $namespace"
            fi
        done
        
        # Restore cluster resources
        if [[ -f "${k8s_dir}/cluster-resources.yaml" ]]; then
            kubectl apply -f "${k8s_dir}/cluster-resources.yaml" || warn "Failed to restore some cluster resources"
        fi
    fi
}

# Main backup function
perform_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    log "Starting AI System backup: $timestamp"
    
    # Check disk space
    local available_space=$(df "$BACKUP_BASE_DIR" | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 10485760 ]]; then  # Less than 10GB
        warn "Low disk space available for backup: ${available_space}KB"
    fi
    
    # Create backup directory
    local backup_dir=$(create_backup_dirs "$timestamp")
    
    # Perform backups
    backup_filesystem "$backup_dir"
    backup_docker_volumes "$backup_dir"
    backup_databases "$backup_dir"
    backup_kubernetes "$backup_dir"
    
    # Create manifest
    create_backup_manifest "$backup_dir" "$timestamp"
    
    # Compress backup
    compress_backup "$backup_dir" "$timestamp"
    
    # Upload to remote
    upload_to_remote "${backup_dir}.tar.gz"
    
    # Verify backup
    verify_backup "${backup_dir}.tar.gz"
    
    # Cleanup old backups
    cleanup_old_backups
    
    log "Backup completed successfully: ${backup_dir}.tar.gz"
    
    # Log backup size
    local backup_size=$(du -h "${backup_dir}.tar.gz" | cut -f1)
    info "Backup size: $backup_size"
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    backup              Perform full system backup
    restore <file>      Restore from backup file
    verify <file>       Verify backup integrity
    list               List available backups
    cleanup            Remove old backups
    help               Show this help message

Restore Types:
    full               Complete system restore (default)
    config             Restore configuration files only
    data               Restore data files only

Environment Variables:
    BACKUP_BASE_DIR         Base directory for backups (default: /backup/ai-system)
    REMOTE_BACKUP_HOST      Remote backup host (optional)
    RETENTION_DAYS          Backup retention in days (default: 30)
    COMPRESSION_LEVEL       Compression level 1-9 (default: 6)

Examples:
    $0 backup                                   # Full backup
    $0 restore /backup/ai-system/20240131_120000.tar.gz  # Full restore
    $0 restore backup.tar.gz config           # Config-only restore
    $0 verify backup.tar.gz                   # Verify backup
    $0 list                                   # List backups
EOF
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [[ -d "$BACKUP_BASE_DIR" ]]; then
        find "$BACKUP_BASE_DIR" -name "*.tar.gz" -printf "%T+ %s %p\n" | sort -r | while read -r date size file; do
            local size_human=$(numfmt --to=iec --suffix=B "$size")
            echo "  $date  $size_human  $(basename "$file")"
        done
    else
        warn "Backup directory not found: $BACKUP_BASE_DIR"
    fi
}

# Main execution
main() {
    # Create backup base directory if it doesn't exist
    mkdir -p "$BACKUP_BASE_DIR"
    
    case "${1:-backup}" in
        "backup")
            perform_backup
            ;;
        "restore")
            [[ $# -ge 2 ]] || error "Usage: $0 restore <backup_file> [restore_type]"
            restore_from_backup "$2" "${3:-full}"
            ;;
        "verify")
            [[ $# -eq 2 ]] || error "Usage: $0 verify <backup_file>"
            verify_backup "$2"
            ;;
        "list")
            list_backups
            ;;
        "cleanup")
            cleanup_old_backups
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