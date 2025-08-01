#!/usr/bin/env bash
# AI System Master Deployment Script
# Executes all phases of the Docker remediation plan

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/deployment_$(date +%Y%m%d_%H%M%S).log"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    log "❌ ERROR: Deployment failed at line $1"
    log "Check $LOG_FILE for details"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Banner
cat << 'EOF'
    _    ___   ____            _                 
   / \  |_ _| / ___| _   _ ___| |_ ___ _ __ ___  
  / _ \  | |  \___ \| | | / __| __/ _ \ '_ ` _ \ 
 / ___ \ | |   ___) | |_| \__ \ ||  __/ | | | | |
/_/   \_\___| |____/ \__, |___/\__\___|_| |_| |_|
                     |___/                        
         Docker Deployment Orchestrator
EOF

log "=== Starting AI System Master Deployment ==="
log "Working directory: $(pwd)"
log "Script directory: $SCRIPT_DIR"

# Check prerequisites
log ""
log "=== Checking Prerequisites ==="

if ! command -v docker &> /dev/null; then
    log "❌ Docker is not installed or not in PATH"
    exit 1
fi
log "✅ Docker is available"

if ! command -v docker compose &> /dev/null; then
    log "❌ Docker Compose is not installed"
    exit 1
fi
log "✅ Docker Compose is available"

if [ -z "${GHCR_PAT:-}" ]; then
    log "⚠️  WARNING: GHCR_PAT environment variable not set"
    log "   You will need it for Phase 3 (Registry Push)"
    log "   Set it with: export GHCR_PAT=<your-github-personal-access-token>"
fi

# Phase execution function
execute_phase() {
    local phase_name=$1
    local script_name=$2
    
    log ""
    log "=== Executing $phase_name ==="
    
    if [ -f "$SCRIPT_DIR/$script_name" ]; then
        log "Running $script_name..."
        bash "$SCRIPT_DIR/$script_name" 2>&1 | tee -a "$LOG_FILE"
        log "✅ $phase_name completed"
    else
        log "❌ Script not found: $SCRIPT_DIR/$script_name"
        return 1
    fi
}

# Main deployment sequence
log ""
log "=== DEPLOYMENT SEQUENCE ==="
log "1. Build monolithic images"
log "2. Push to registry"
log "3. Deploy and test"
log "4. Security and maintenance setup"

# Confirm before proceeding
read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Deployment cancelled by user"
    exit 0
fi

# Execute phases
execute_phase "Phase 2-B: Monolithic Build" "monolithic_build.sh"
execute_phase "Phase 3: Registry Push" "registry_push.sh"
execute_phase "Phases 4-6: Deploy and Test" "deploy_and_test.sh"
execute_phase "Phases 7-10: Security and Maintenance" "security_and_maintenance.sh"

# Final summary
log ""
log "=== DEPLOYMENT SUMMARY ==="
log "✅ All phases executed successfully"
log "📋 Deployment log: $LOG_FILE"
log "📁 Scripts location: $SCRIPT_DIR"
log ""
log "=== POST-DEPLOYMENT CHECKLIST ==="
log "1. Verify services are running: docker ps"
log "2. Check metrics endpoints: http://localhost:9000/metrics (MainPC), http://localhost:9100/metrics (PC2)"
log "3. Review security scan results in the log"
log "4. Confirm backup cron jobs: crontab -l"
log "5. Test rolling update procedure with a sample service"
log ""
log "Deployment completed at $(date)"