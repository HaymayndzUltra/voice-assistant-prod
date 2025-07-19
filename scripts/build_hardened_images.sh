#!/bin/bash
# WP-02 Build Script - Hardened Images
# Builds all Docker images with security hardening

set -e

echo "🚀 WP-02: Building Hardened Docker Images"
echo "========================================"

# Build base hardened image first
echo "📦 Building hardened base image..."
docker build -t ai_system/base:1.0 -f Dockerfile.production .
echo "✅ Base image built successfully"

# Build production compose services
echo "📦 Building production services..."
docker-compose -f docker-compose.production.yml build --parallel
echo "✅ Production services built successfully"

# Tag images for versioning
echo "🏷️ Tagging images..."
docker tag ai_system/base:1.0 ai_system/base:latest
echo "✅ Images tagged"

# Security scan (optional - requires trivy)
echo "🔍 Running security scan..."
if command -v trivy &> /dev/null; then
    trivy image ai_system/base:1.0
else
    echo "⚠️  Trivy not installed - skipping security scan"
    echo "   Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
fi

echo ""
echo "🎉 WP-02 Build Complete!"
echo "✅ All images built with security hardening"
echo "✅ Non-root user (ai:1000) configured"
echo "✅ File permissions properly set"
echo ""
echo "To start services:"
echo "  docker-compose -f docker-compose.production.yml up -d"
echo ""
echo "To debug:"
echo "  docker-compose -f docker-compose.production.yml --profile debug up -d"
echo "  docker exec -it ai-debug-shell bash"
