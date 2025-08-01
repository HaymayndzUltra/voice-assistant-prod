# AI System Deployment Scripts

This directory contains deployment scripts generated from the `ai_docker_remediation_plan.md`. These scripts must be executed on a system with Docker installed, not from within a container.

## Prerequisites

- Docker Engine installed and running
- Docker Compose v2 installed
- GitHub Personal Access Token (PAT) with `write:packages` scope for GHCR
- sudo access for security updates and backup configuration
- Git (for version tagging)

## Scripts Overview

### 1. `master_deploy.sh`
**Main orchestrator script** - Runs all phases in sequence
```bash
export GHCR_PAT="your-github-token"
./master_deploy.sh
```

### 2. Individual Phase Scripts

#### `monolithic_build.sh` (Phase 2-B)
Builds monolithic Docker images for MainPC and PC2 stacks
```bash
./monolithic_build.sh
```

#### `registry_push.sh` (Phase 3)
Tags and pushes images to GitHub Container Registry
```bash
export GHCR_PAT="your-github-token"
./registry_push.sh
```

#### `deploy_and_test.sh` (Phases 4-6)
- Validates docker-compose files
- Deploys services
- Runs health checks
- Executes load and smoke tests
```bash
./deploy_and_test.sh
```

#### `security_and_maintenance.sh` (Phases 7-10)
- Enables security features
- Sets up backup procedures
- Creates maintenance scripts
- Documents deployment
```bash
./security_and_maintenance.sh
```

## Additional Scripts Created

These scripts are created by `security_and_maintenance.sh`:

- `/workspace/scripts/volume_backup.sh` - Daily backup of Docker volumes
- `/workspace/scripts/rolling_update.sh` - Rolling update for services
- `/workspace/scripts/monthly_cleanup.sh` - Monthly cleanup of old data

## Usage Instructions

### Option 1: Full Deployment (Recommended)
```bash
cd /workspace
export GHCR_PAT="your-github-token"
./deploy_scripts/master_deploy.sh
```

### Option 2: Individual Phases
Run scripts individually if you need to:
- Debug specific phases
- Resume after fixing errors
- Skip certain phases

```bash
cd /workspace
export GHCR_PAT="your-github-token"

# Build images
./deploy_scripts/monolithic_build.sh

# Push to registry
./deploy_scripts/registry_push.sh

# Deploy and test
./deploy_scripts/deploy_and_test.sh

# Security and maintenance
./deploy_scripts/security_and_maintenance.sh
```

## Post-Deployment

After successful deployment:

1. Verify services: `docker ps`
2. Check metrics: 
   - MainPC: http://localhost:9000/metrics
   - PC2: http://localhost:9100/metrics
3. Review logs: Check deployment logs in `deploy_scripts/`
4. Verify backups: `crontab -l`
5. Test updates: Use `rolling_update.sh` for future updates

## Troubleshooting

### Docker not found
These scripts require Docker. Install Docker Engine on your host system.

### Permission denied
Make scripts executable: `chmod +x deploy_scripts/*.sh`

### GHCR authentication failed
1. Create a GitHub PAT with `write:packages` scope
2. Export it: `export GHCR_PAT="your-token"`

### Build failures
Check Dockerfile paths match your repository structure. The scripts assume:
- MainPC Dockerfile: `docker/mainpc/Dockerfile`
- PC2 Dockerfile: `docker/pc2/Dockerfile`

## Files Generated

- `docs/deployment_strategy.md` - Strategy decision documentation
- `docs/production_deployment_overview.md` - Deployment summary
- `deployment_logs/` - Container logs from deployments
- Various scripts in `/workspace/scripts/` for maintenance

## Important Notes

⚠️ **These scripts cannot run inside a Docker container** - They require access to the Docker daemon, which is not available in containerized environments.

📝 **Adjust paths if needed** - Scripts assume `/workspace` as the repository root. Modify if your setup differs.

🔐 **Security** - Keep your GHCR_PAT secure and never commit it to version control.