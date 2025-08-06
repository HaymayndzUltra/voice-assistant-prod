#!/bin/bash

# 🐳 Local Docker Registry Setup Script
# For AI System Monorepo - Main PC & PC2 Integration

set -e

echo "🚀 Setting up Centralized Local Docker Registry..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REGISTRY_HOST="localhost"
REGISTRY_PORT="5000"
REGISTRY_URL="${REGISTRY_HOST}:${REGISTRY_PORT}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. Create insecure registry configuration
print_info "Configuring Docker daemon for insecure registry..."

DAEMON_CONFIG="/etc/docker/daemon.json"
if [ -f "$DAEMON_CONFIG" ]; then
    print_warning "Backing up existing daemon.json..."
    sudo cp "$DAEMON_CONFIG" "${DAEMON_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create or update daemon.json
sudo tee "$DAEMON_CONFIG" > /dev/null <<EOF
{
  "insecure-registries": ["${REGISTRY_URL}"],
  "registry-mirrors": [],
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

print_status "Docker daemon configuration updated"

# 2. Restart Docker service
print_info "Restarting Docker service..."
sudo systemctl restart docker
sleep 3

print_status "Docker service restarted"

# 3. Start registry services
print_info "Starting local Docker registry..."
cd "$(dirname "$0")/../docker-registry"

docker-compose down 2>/dev/null || true
docker-compose up -d

print_status "Registry services started"

# 4. Wait for registry to be ready
print_info "Waiting for registry to be ready..."
for i in {1..30}; do
    if curl -s http://${REGISTRY_URL}/v2/ >/dev/null; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# 5. Test registry
print_info "Testing registry connectivity..."
if curl -s http://${REGISTRY_URL}/v2/ | grep -q '{}'; then
    print_status "Registry is responding correctly"
else
    print_error "Registry test failed"
    exit 1
fi

# 6. Show registry information
echo ""
echo "🎉 Local Docker Registry Setup Complete!"
echo ""
print_info "Registry URL: http://${REGISTRY_URL}"
print_info "Registry UI: http://localhost:5001"
echo ""

# 7. Show usage examples
echo "📋 Usage Examples:"
echo ""
echo "# Tag an image for local registry:"
echo "docker tag my-image:latest ${REGISTRY_URL}/my-image:latest"
echo ""
echo "# Push to local registry:"
echo "docker push ${REGISTRY_URL}/my-image:latest"
echo ""
echo "# Pull from local registry:"
echo "docker pull ${REGISTRY_URL}/my-image:latest"
echo ""

# 8. Show current running services
print_info "Running registry services:"
docker-compose ps

echo ""
print_status "Setup completed successfully! 🎉"
