#!/usr/bin/env bash

# Script to launch a WSL2 container with GPU support for the AI System
set -e

# Function to display usage information
function show_usage {
    echo "Usage: $0 <container-group> [--dev]"
    echo "  container-group: The group of agents to run (core-services, memory-system, etc.)"
    echo "  --dev: Mount the current directory for development (optional)"
    echo ""
    echo "Available container groups:"
    echo "  core-services: Essential system services (SystemDigitalTwin)"
    echo "  memory-system: Memory related services"
    echo "  utility-services: Utility services"
    echo "  ai-models-gpu-services: GPU accelerated AI models"
    echo "  language-processing: NLP and translation services"
    exit 1
}

# Check arguments
if [ "$#" -lt 1 ]; then
    show_usage
fi

CONTAINER_GROUP="$1"
shift

# Check for valid container group
VALID_GROUPS=("core-services" "memory-system" "utility-services" "ai-models-gpu-services" "language-processing" "vision-system" "learning-knowledge" "audio-processing" "emotion-system" "utilities-support" "security-auth")
VALID_GROUP=0

for group in "${VALID_GROUPS[@]}"; do
    if [ "$CONTAINER_GROUP" = "$group" ]; then
        VALID_GROUP=1
        break
    fi
done

if [ "$VALID_GROUP" -eq 0 ]; then
    echo "Error: Invalid container group '$CONTAINER_GROUP'"
    show_usage
fi

# Check if we need development mode
DEV_MODE=0
if [[ "$*" == *"--dev"* ]]; then
    DEV_MODE=1
fi

# Set script directory path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PODMAN_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROJECT_ROOT="$( cd "$PODMAN_DIR/../.." && pwd )"

# First, make sure GPU support is working
echo "Checking GPU device paths in WSL2..."
"$SCRIPT_DIR/fix_wsl2_gpu.sh"

# Default command to run in container
CONTAINER_CMD="/app/docker/podman/scripts/container_startup.py"
IMAGE_NAME="ai-system:cuda-wsl2"

# Set container name
CONTAINER_NAME="ai-system-${CONTAINER_GROUP}"

# Remove any existing container with the same name
echo "Removing any existing container with name $CONTAINER_NAME..."
podman rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Set volume mounts
VOLUME_MOUNTS="-v $PROJECT_ROOT/logs:/app/logs -v $PROJECT_ROOT/data:/app/data"

# Add development volume mount if in dev mode
if [ "$DEV_MODE" -eq 1 ]; then
    echo "Starting in development mode - mounting current code directory"
    VOLUME_MOUNTS="$VOLUME_MOUNTS -v $PROJECT_ROOT:/app"
fi

# Set environment variables
ENV_VARS="-e CONTAINER_GROUP=$CONTAINER_GROUP -e PYTHONPATH=/app -e PYTHONUNBUFFERED=1"

# Add GPU support flags
GPU_FLAGS="--device nvidia.com/gpu=all"

echo "Launching container $CONTAINER_NAME from image $IMAGE_NAME..."
# Use host network mode to avoid CNI network issues in WSL2
podman run --name "$CONTAINER_NAME" --network host $GPU_FLAGS $ENV_VARS $VOLUME_MOUNTS -it --rm "$IMAGE_NAME" "$CONTAINER_CMD" 