#!/bin/bash

# Script to build all PC2 container images
# This script should be run from the project root directory

set -e  # Exit on error

echo "Building PC2 container images..."

# Create the network if it doesn't exist
podman network exists pc2-network || podman network create pc2-network

# Build the base image first
echo "Building base image..."
podman build -t pc2-base:latest -f pc2_code/docker/Dockerfile.base .

# Build container images for each group
echo "Building Core Infrastructure image..."
podman build -t pc2-core-infrastructure:latest -f pc2_code/docker/Dockerfile.core_infrastructure .

echo "Building Memory & Storage image..."
podman build -t pc2-memory-storage:latest -f pc2_code/docker/Dockerfile.memory_storage .

echo "Building Security & Authentication image..."
podman build -t pc2-security-authentication:latest -f pc2_code/docker/Dockerfile.security_authentication .

echo "Building Integration & Communication image..."
podman build -t pc2-integration-communication:latest -f pc2_code/docker/Dockerfile.integration_communication .

echo "Building Monitoring & Support image..."
podman build -t pc2-monitoring-support:latest -f pc2_code/docker/Dockerfile.monitoring_support .

echo "Building Dream & Tutoring image..."
podman build -t pc2-dream-tutoring:latest -f pc2_code/docker/Dockerfile.dream_tutoring .

echo "Building Web & External Services image..."
podman build -t pc2-web-external:latest -f pc2_code/docker/Dockerfile.web_external .

echo "All images built successfully!"
echo "To start the containers, run: podman-compose -f pc2_code/docker/podman-compose.yaml up -d" 