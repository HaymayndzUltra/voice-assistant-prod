#!/bin/bash

# Cross-Machine Network Setup for AI System
# MainPC (192.168.100.16) ↔ PC2 (192.168.100.17)

set -e

echo "🌐 AI System Cross-Machine Network Setup"
echo "========================================="

# Network configuration
MAINPC_IP="192.168.100.16"
PC2_IP="192.168.100.17"
NETWORK_NAME="ai_system_network"
SUBNET="172.21.0.0/16"

echo ""
echo "📋 Network Configuration:"
echo "MainPC IP: $MAINPC_IP"
echo "PC2 IP:    $PC2_IP"
echo "Network:   $NETWORK_NAME"
echo "Subnet:    $SUBNET"

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "❌ Docker is not running on $(hostname). Please start Docker first."
        exit 1
    fi
    echo "✅ Docker is running on $(hostname)"
}

# Function to create/update Docker network
setup_network() {
    echo ""
    echo "🔧 Setting up Docker network..."
    
    # Remove existing network if it exists
    if docker network ls | grep -q "$NETWORK_NAME"; then
        echo "⚠️  Removing existing network: $NETWORK_NAME"
        docker network rm "$NETWORK_NAME" 2>/dev/null || true
    fi
    
    # Create new network with external connectivity
    echo "🌐 Creating network: $NETWORK_NAME"
    docker network create \
        --driver bridge \
        --subnet="$SUBNET" \
        --opt com.docker.network.bridge.enable_icc=true \
        --opt com.docker.network.bridge.enable_ip_masquerade=true \
        --opt com.docker.network.driver.mtu=1500 \
        "$NETWORK_NAME"
    
    echo "✅ Network created successfully"
}

# Function to configure cross-machine connectivity
configure_connectivity() {
    echo ""
    echo "🔗 Configuring cross-machine connectivity..."
    
    # Add routes for container communication (requires sudo)
    current_ip=$(hostname -I | awk '{print $1}')
    
    if [[ "$current_ip" == "$MAINPC_IP" ]]; then
        echo "📍 Detected MainPC - configuring routes to PC2"
        
        # Add route to PC2 container subnet
        echo "Adding route to PC2 containers..."
        sudo ip route add 172.21.0.0/16 via "$PC2_IP" 2>/dev/null || echo "Route may already exist"
        
    elif [[ "$current_ip" == "$PC2_IP" ]]; then
        echo "📍 Detected PC2 - configuring routes to MainPC"
        
        # Add route to MainPC container subnet
        echo "Adding route to MainPC containers..."
        sudo ip route add 172.20.0.0/16 via "$MAINPC_IP" 2>/dev/null || echo "Route may already exist"
        
    else
        echo "⚠️  Unknown machine IP: $current_ip"
        echo "Manual network configuration may be required"
    fi
}

# Function to test connectivity
test_connectivity() {
    echo ""
    echo "🧪 Testing cross-machine connectivity..."
    
    # Test basic IP connectivity
    if ping -c 2 "$MAINPC_IP" >/dev/null 2>&1; then
        echo "✅ MainPC ($MAINPC_IP) is reachable"
    else
        echo "❌ MainPC ($MAINPC_IP) is unreachable"
    fi
    
    if ping -c 2 "$PC2_IP" >/dev/null 2>&1; then
        echo "✅ PC2 ($PC2_IP) is reachable"
    else
        echo "❌ PC2 ($PC2_IP) is unreachable"
    fi
}

# Function to create service discovery configuration
create_service_discovery() {
    echo ""
    echo "🔍 Creating service discovery configuration..."
    
    # Create service discovery config
    mkdir -p config/network
    
    cat > config/network/service_discovery.yml << EOF
# AI System Service Discovery Configuration
# Enables cross-machine agent communication

services:
  # MainPC Services (Primary Hub)
  mainpc:
    host: "$MAINPC_IP"
    observability_hub:
      port: 9000
      health_port: 9100
    redis:
      port: 6379
    
  # PC2 Services (Lightweight Forwarder)  
  pc2:
    host: "$PC2_IP"
    observability_hub:
      port: 9000
      health_port: 9100
      mode: "forwarder"
      primary_hub: "http://$MAINPC_IP:9000"

# Cross-machine agent communication ports
cross_machine_ports:
  mainpc_to_pc2:
    # PC2 exposed services
    - { service: "MemoryOrchestratorService", port: 7140 }
    - { service: "TieredResponder", port: 7100 }
    - { service: "AdvancedRouter", port: 7129 }
    - { service: "RemoteConnectorAgent", port: 7124 }
    
  pc2_to_mainpc:
    # MainPC exposed services
    - { service: "ModelManagerSuite", port: 7211 }
    - { service: "RequestCoordinator", port: 26002 }
    - { service: "SystemDigitalTwin", port: 7220 }

# Network security
security:
  allowed_subnets:
    - "192.168.100.0/24"  # Local network
    - "172.20.0.0/16"     # MainPC containers
    - "172.21.0.0/16"     # PC2 containers
EOF

    echo "✅ Service discovery configuration created"
}

# Main execution
main() {
    echo ""
    echo "🚀 Starting network setup..."
    
    check_docker
    setup_network
    configure_connectivity
    test_connectivity
    create_service_discovery
    
    echo ""
    echo "🎉 Cross-machine network setup complete!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Run this script on both MainPC and PC2"
    echo "2. Start MainPC containers: cd docker/mainpc && ./start-mainpc.sh"
    echo "3. Start PC2 containers: cd docker/pc2 && ./start-pc2.sh"
    echo "4. Validate connectivity: cd docker/pc2 && ./validate-pc2.py"
    
    echo ""
    echo "💡 Network Commands:"
    echo "View network: docker network ls"
    echo "Inspect network: docker network inspect $NETWORK_NAME"
    echo "View routes: ip route show"
}

# Execute main function
main "$@" 