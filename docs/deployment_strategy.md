# Deployment Strategy

## Strategy Decision
- **Date**: 2025-01-30
- **Strategy**: Monolithic Build Workflow (Phase 2-B)
- **Reason**: Modular Dockerfiles referenced in CI are missing. Only monolithic Dockerfiles exist at:
  - `/workspace/docker/mainpc/Dockerfile`
  - `/workspace/docker/pc2/Dockerfile`

## Build Approach
Using monolithic images with service-specific commands in docker-compose files.