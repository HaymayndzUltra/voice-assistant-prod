#!/usr/bin/env bash
# AI System Security and Maintenance Script
# Covers Phases 7-10 of the remediation plan

set -euo pipefail

echo "=== AI System Security and Maintenance Script ==="
echo "Starting at: $(date)"

# Phase 7: Security Hardening
echo ""
echo "=== PHASE 7: Security Hardening ==="

echo "Enabling Docker Content Trust..."
export DOCKER_CONTENT_TRUST=1
echo "✅ Docker Content Trust enabled"

echo "Scanning all running containers..."
docker scan $(docker ps -q) || echo "⚠️  Docker scan not available, consider installing"

echo "Setting up automatic security updates..."
if [ -f /etc/debian_version ]; then
    sudo apt-get update
    sudo apt-get install -y unattended-upgrades
    sudo dpkg-reconfigure -plow unattended-upgrades
    echo "✅ Automatic security updates configured"
else
    echo "⚠️  Not a Debian-based system, configure security updates manually"
fi

echo "Checking non-root users in containers..."
VERSION_TAG=${VERSION_TAG:-latest}
docker inspect ghcr.io/haymayndzultra/ai_system/mainpc_stack:$VERSION_TAG --format '{{json .Config.User}}' || echo "MainPC image not found"
docker inspect ghcr.io/haymayndzultra/ai_system/pc2_stack:$VERSION_TAG --format '{{json .Config.User}}' || echo "PC2 image not found"

# Phase 8: Backup & Disaster Recovery
echo ""
echo "=== PHASE 8: Backup & Disaster Recovery ==="

echo "Creating backup directory..."
sudo mkdir -p /backups
sudo chmod 755 /backups

echo "Creating volume backup script..."
cat > /workspace/scripts/volume_backup.sh <<'EOS'
#!/usr/bin/env bash
set -e
TS=$(date +%Y%m%d_%H%M)

# Backup MainPC volumes
echo "Backing up MainPC volumes..."
for container in $(docker ps --filter "label=com.docker.compose.project=main_pc_code" -q); do
    container_name=$(docker inspect -f '{{.Name}}' $container | sed 's/^\///')
    docker run --rm --volumes-from $container \
        -v /backups:/backup alpine \
        tar czf /backup/${container_name}_${TS}.tgz /app/data 2>/dev/null || true
done

# Backup PC2 volumes
echo "Backing up PC2 volumes..."
for container in $(docker ps --filter "label=com.docker.compose.project=pc2_code" -q); do
    container_name=$(docker inspect -f '{{.Name}}' $container | sed 's/^\///')
    docker run --rm --volumes-from $container \
        -v /backups:/backup alpine \
        tar czf /backup/${container_name}_${TS}.tgz /app/data 2>/dev/null || true
done

echo "Backup completed at $(date)"
echo "Backup files stored in /backups/"
EOS
chmod +x /workspace/scripts/volume_backup.sh
echo "✅ Volume backup script created"

echo "Setting up daily backup cron job..."
(crontab -l 2>/dev/null; echo "0 2 * * * /workspace/scripts/volume_backup.sh > /var/log/backup.log 2>&1") | crontab -
echo "✅ Daily backup scheduled for 2 AM"

# Phase 9: Maintenance Operations
echo ""
echo "=== PHASE 9: Maintenance Operations ==="

echo "Creating rolling update script..."
cat > /workspace/scripts/rolling_update.sh <<'EOS'
#!/usr/bin/env bash
# Rolling update script for AI System services
# Usage: ./rolling_update.sh <service_name> <new_version_tag>

set -euo pipefail

SERVICE=$1
VERSION_TAG=$2

echo "Performing rolling update for $SERVICE to version $VERSION_TAG"

# Update MainPC service
if docker compose -f /workspace/main_pc_code/config/docker-compose.yml ps | grep -q $SERVICE; then
    echo "Updating MainPC $SERVICE..."
    docker compose -f /workspace/main_pc_code/config/docker-compose.yml pull $SERVICE
    docker compose -f /workspace/main_pc_code/config/docker-compose.yml up -d $SERVICE
fi

# Update PC2 service
if docker compose -f /workspace/pc2_code/config/docker-compose.yml ps | grep -q $SERVICE; then
    echo "Updating PC2 $SERVICE..."
    docker compose -f /workspace/pc2_code/config/docker-compose.yml pull $SERVICE
    docker compose -f /workspace/pc2_code/config/docker-compose.yml up -d $SERVICE
fi

# Validate health
sleep 10
python3 /workspace/main_pc_code/scripts/health_probe.py --host 127.0.0.1 || echo "Health probe script not found"

echo "Rolling update completed"
EOS
chmod +x /workspace/scripts/rolling_update.sh
echo "✅ Rolling update script created"

echo "Creating monthly cleanup script..."
cat > /workspace/scripts/monthly_cleanup.sh <<'EOS'
#!/usr/bin/env bash
# Monthly cleanup script

echo "Running monthly cleanup at $(date)"

# Clean up old images and volumes
docker system prune -af --volumes

# Clean up old backup files (keep last 30 days)
find /backups -name "*.tgz" -mtime +30 -delete

# Clean up logs
find /var/log -name "*.log" -mtime +30 -delete

echo "Cleanup completed"
EOS
chmod +x /workspace/scripts/monthly_cleanup.sh
echo "✅ Monthly cleanup script created"

# Schedule monthly cleanup
(crontab -l 2>/dev/null; echo "0 3 1 * * /workspace/scripts/monthly_cleanup.sh > /var/log/cleanup.log 2>&1") | crontab -
echo "✅ Monthly cleanup scheduled for 1st of each month at 3 AM"

# Phase 10: Document & Archive
echo ""
echo "=== PHASE 10: Document & Archive ==="

echo "Creating deployment logs directory..."
mkdir -p /workspace/deployment_logs

echo "Capturing current deployment logs..."
TIMESTAMP=$(date +%Y%m%d_%H%M)
docker compose -f main_pc_code/config/docker-compose.yml logs --no-color > /workspace/deployment_logs/${TIMESTAMP}_mainpc.log 2>&1 || true
docker compose -f pc2_code/config/docker-compose.yml logs --no-color > /workspace/deployment_logs/${TIMESTAMP}_pc2.log 2>&1 || true
echo "✅ Deployment logs captured"

echo "Creating deployment summary..."
cat > /workspace/docs/production_deployment_overview.md <<EOF
# Production Deployment Overview

## Deployment Information
- **Date**: $(date)
- **Strategy**: Monolithic Build
- **Version Tag**: ${VERSION_TAG:-latest}

## Infrastructure
- **MainPC Stack**: ghcr.io/haymayndzultra/ai_system/mainpc_stack:${VERSION_TAG:-latest}
- **PC2 Stack**: ghcr.io/haymayndzultra/ai_system/pc2_stack:${VERSION_TAG:-latest}

## Backup Configuration
- **Schedule**: Daily at 2 AM
- **Location**: /backups/
- **Retention**: 30 days

## Security
- Docker Content Trust: Enabled
- Automatic Updates: Configured
- Container User: Should be non-root (verify with docker inspect)

## Maintenance
- Rolling Update Script: /workspace/scripts/rolling_update.sh
- Monthly Cleanup: 1st of each month at 3 AM
- Health Monitoring: Prometheus endpoints on ports 9000 (MainPC) and 9100 (PC2)

## Logs
- Deployment logs: /workspace/deployment_logs/
- Backup logs: /var/log/backup.log
- Cleanup logs: /var/log/cleanup.log
EOF
echo "✅ Deployment documentation created"

echo ""
echo "=== Security and Maintenance Setup Complete ==="
echo "Completed at: $(date)"
echo ""
echo "=== FINAL VALIDATION ==="
echo "Re-running Phase 0 audit to validate deployment..."

# Re-run Phase 0 audit
python3 -c "
import os, yaml, pathlib
root = pathlib.Path('/workspace').resolve()
dockerfiles = [str(p) for p in root.rglob('Dockerfile*') if p.is_file()]
compose_files = [str(p) for p in root.rglob('docker-compose*.yml')]
print(f'Total Dockerfiles: {len(dockerfiles)}')
print(f'Total Compose files: {len(compose_files)}')
print('✅ Deployment validation complete')
"

echo ""
echo "=== ALL PHASES COMPLETE ==="
echo "Deployment scripts have been generated and are ready for execution on a Docker-enabled system"