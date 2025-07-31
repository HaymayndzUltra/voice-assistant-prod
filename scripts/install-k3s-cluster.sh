#!/bin/bash
# k3s Cluster Installation Script for AI System
# Supports MainPC (master + worker) and PC2 (worker) configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K3S_VERSION="v1.28.5+k3s1"
NVIDIA_PLUGIN_VERSION="v0.14.3"

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

# Detect if this is MainPC or PC2 based on GPU
detect_node_type() {
    if nvidia-smi --query-gpu=name --format=csv,noheader | grep -q "RTX 4090"; then
        NODE_TYPE="master"
        GPU_TYPE="RTX-4090"
        log "Detected MainPC with RTX 4090 - configuring as k3s master"
    elif nvidia-smi --query-gpu=name --format=csv,noheader | grep -q "RTX 3060"; then
        NODE_TYPE="worker"
        GPU_TYPE="RTX-3060"
        log "Detected PC2 with RTX 3060 - configuring as k3s worker"
    else
        error "No supported GPU detected. Please ensure RTX 4090 or RTX 3060 is available."
    fi
}

# Install k3s prerequisites
install_prerequisites() {
    log "Installing k3s prerequisites..."
    
    # Update system packages
    if [[ -f /etc/debian_version ]]; then
        apt-get update
        apt-get install -y curl wget jq htop
    elif [[ -f /etc/redhat-release ]]; then
        yum update -y
        yum install -y curl wget jq htop
    else
        warn "Unsupported distribution. Please install curl, wget, jq manually."
    fi
    
    # Install Docker if not present (k3s can use containerd, but Docker is useful for development)
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        usermod -aG docker $USER
    fi
    
    log "Prerequisites installed"
}

# Install k3s master node (MainPC)
install_k3s_master() {
    log "Installing k3s master node..."
    
    # Set k3s configuration
    mkdir -p /etc/rancher/k3s
    
    cat > /etc/rancher/k3s/config.yaml << EOF
cluster-init: true
disable:
  - traefik  # We'll use our own ingress
  - servicelb  # Use MetalLB instead
node-name: mainpc-master
node-label:
  - node.kubernetes.io/instance-type=gpu-node
  - nvidia.com/gpu.product=${GPU_TYPE}
  - ai-system.io/node-role=master
kubelet-arg:
  - feature-gates=DevicePlugins=true
  - device-plugin-path=/var/lib/kubelet/device-plugins
kube-apiserver-arg:
  - feature-gates=DevicePlugins=true
EOF
    
    # Install k3s
    curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=${K3S_VERSION} sh -s - server
    
    # Wait for k3s to start
    until kubectl get nodes; do
        sleep 5
    done
    
    # Get node token for worker nodes
    NODE_TOKEN=$(cat /var/lib/rancher/k3s/server/node-token)
    MASTER_IP=$(hostname -I | awk '{print $1}')
    
    log "k3s master installed successfully"
    info "Master IP: ${MASTER_IP}"
    info "Node token: ${NODE_TOKEN}"
    info "Save these values for worker node setup"
    
    # Create worker join command file
    cat > /tmp/k3s-worker-join.txt << EOF
# Run this command on worker nodes:
curl -sfL https://get.k3s.io | K3S_URL=https://${MASTER_IP}:6443 K3S_TOKEN=${NODE_TOKEN} INSTALL_K3S_VERSION=${K3S_VERSION} sh -s - agent
EOF
    
    info "Worker join command saved to /tmp/k3s-worker-join.txt"
}

# Install k3s worker node (PC2)
install_k3s_worker() {
    log "Installing k3s worker node..."
    
    # Prompt for master details if not provided
    if [[ -z "${K3S_URL:-}" ]]; then
        echo "Enter the master node IP address:"
        read -r MASTER_IP
        K3S_URL="https://${MASTER_IP}:6443"
    fi
    
    if [[ -z "${K3S_TOKEN:-}" ]]; then
        echo "Enter the node token from master:"
        read -r K3S_TOKEN
    fi
    
    # Set k3s configuration
    mkdir -p /etc/rancher/k3s
    
    cat > /etc/rancher/k3s/config.yaml << EOF
server: ${K3S_URL}
token: ${K3S_TOKEN}
node-name: pc2-worker
node-label:
  - node.kubernetes.io/instance-type=gpu-node
  - nvidia.com/gpu.product=${GPU_TYPE}
  - ai-system.io/node-role=worker
kubelet-arg:
  - feature-gates=DevicePlugins=true
  - device-plugin-path=/var/lib/kubelet/device-plugins
EOF
    
    # Install k3s agent
    curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION=${K3S_VERSION} K3S_URL=${K3S_URL} K3S_TOKEN=${K3S_TOKEN} sh -s - agent
    
    log "k3s worker node installed successfully"
}

# Install NVIDIA device plugin
install_nvidia_device_plugin() {
    log "Installing NVIDIA device plugin for Kubernetes..."
    
    # Only run on master node
    if [[ "${NODE_TYPE}" != "master" ]]; then
        log "Skipping device plugin installation (worker node)"
        return
    fi
    
    # Create NVIDIA device plugin manifest
    cat > /tmp/nvidia-device-plugin.yaml << EOF
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nvidia-device-plugin-daemonset
  namespace: kube-system
spec:
  selector:
    matchLabels:
      name: nvidia-device-plugin-ds
  updateStrategy:
    type: RollingUpdate
  template:
    metadata:
      labels:
        name: nvidia-device-plugin-ds
    spec:
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
      nodeSelector:
        node.kubernetes.io/instance-type: gpu-node
      priorityClassName: "system-node-critical"
      containers:
      - image: nvcr.io/nvidia/k8s-device-plugin:${NVIDIA_PLUGIN_VERSION}
        name: nvidia-device-plugin-ctr
        args:
          - "--mig-strategy=single"
          - "--pass-device-specs=true"
          - "--device-list-strategy=envvar"
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        volumeMounts:
          - name: device-plugin
            mountPath: /var/lib/kubelet/device-plugins
      volumes:
        - name: device-plugin
          hostPath:
            path: /var/lib/kubelet/device-plugins
      restartPolicy: Always
EOF
    
    # Apply the device plugin
    kubectl apply -f /tmp/nvidia-device-plugin.yaml
    
    # Wait for device plugin to be ready
    kubectl rollout status daemonset/nvidia-device-plugin-daemonset -n kube-system --timeout=300s
    
    log "NVIDIA device plugin installed successfully"
}

# Setup namespaces and basic resources
setup_namespaces() {
    log "Setting up AI System namespaces..."
    
    # Only run on master node
    if [[ "${NODE_TYPE}" != "master" ]]; then
        return
    fi
    
    # Create namespaces
    kubectl create namespace ai-system-infra --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace ai-system-core --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace ai-system-gpu --dry-run=client -o yaml | kubectl apply -f -
    kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
    
    # Label namespaces
    kubectl label namespace ai-system-infra name=ai-system-infra --overwrite
    kubectl label namespace ai-system-core name=ai-system-core --overwrite
    kubectl label namespace ai-system-gpu name=ai-system-gpu --overwrite
    kubectl label namespace monitoring name=monitoring --overwrite
    
    # Create resource quotas
    cat > /tmp/gpu-quota.yaml << EOF
apiVersion: v1
kind: ResourceQuota
metadata:
  name: gpu-quota
  namespace: ai-system-gpu
spec:
  hard:
    requests.nvidia.com/gpu: "2"
    limits.nvidia.com/gpu: "2"
    requests.memory: "32Gi"
    limits.memory: "48Gi"
EOF
    
    kubectl apply -f /tmp/gpu-quota.yaml
    
    log "Namespaces and quotas configured"
}

# Install MetalLB for LoadBalancer services
install_metallb() {
    log "Installing MetalLB for LoadBalancer services..."
    
    # Only run on master node
    if [[ "${NODE_TYPE}" != "master" ]]; then
        return
    fi
    
    # Install MetalLB
    kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.12/config/manifests/metallb-native.yaml
    
    # Wait for MetalLB to be ready
    kubectl wait --namespace metallb-system \
                --for=condition=ready pod \
                --selector=app=metallb \
                --timeout=90s
    
    # Configure IP address pool (adjust for your network)
    cat > /tmp/metallb-config.yaml << EOF
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: ai-system-pool
  namespace: metallb-system
spec:
  addresses:
  - 192.168.1.240-192.168.1.250  # Adjust for your network
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: ai-system-advertisement
  namespace: metallb-system
spec:
  ipAddressPools:
  - ai-system-pool
EOF
    
    kubectl apply -f /tmp/metallb-config.yaml
    
    log "MetalLB installed and configured"
}

# Verify installation
verify_installation() {
    log "Verifying k3s installation..."
    
    # Check nodes
    kubectl get nodes -o wide
    
    # Check GPU resources
    kubectl describe nodes | grep -A 5 "nvidia.com/gpu"
    
    # Check system pods
    kubectl get pods -n kube-system
    
    if [[ "${NODE_TYPE}" == "master" ]]; then
        # Check namespaces
        kubectl get namespaces
        
        # Check device plugin
        kubectl get pods -n kube-system -l name=nvidia-device-plugin-ds
    fi
    
    log "Installation verification completed"
}

# Main installation function
main() {
    log "Starting k3s cluster installation for AI System..."
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
    
    # Detect node type
    detect_node_type
    
    # Install prerequisites
    install_prerequisites
    
    # Install k3s based on node type
    if [[ "${NODE_TYPE}" == "master" ]]; then
        install_k3s_master
        install_nvidia_device_plugin
        setup_namespaces
        install_metallb
    else
        install_k3s_worker
    fi
    
    # Verify installation
    verify_installation
    
    log "k3s installation completed successfully!"
    
    if [[ "${NODE_TYPE}" == "master" ]]; then
        info "Next steps:"
        info "1. Install worker nodes using the join command in /tmp/k3s-worker-join.txt"
        info "2. Deploy AI System manifests: kubectl apply -k k8s/manifests/"
        info "3. Monitor cluster: kubectl get nodes,pods -A"
    else
        info "Worker node joined successfully. Check status on master with: kubectl get nodes"
    fi
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    install         Install k3s cluster (auto-detects master/worker)
    uninstall       Uninstall k3s
    status          Show cluster status
    help            Show this help message

Environment Variables:
    K3S_URL         Master node URL (for worker installation)
    K3S_TOKEN       Node token (for worker installation)

Examples:
    $0 install                           # Auto-install based on GPU type
    K3S_URL=https://192.168.1.100:6443 K3S_TOKEN=xxx $0 install  # Worker with env vars
    $0 status
EOF
}

case "${1:-install}" in
    "install")
        main
        ;;
    "uninstall")
        if [[ -f /usr/local/bin/k3s-uninstall.sh ]]; then
            /usr/local/bin/k3s-uninstall.sh
        elif [[ -f /usr/local/bin/k3s-agent-uninstall.sh ]]; then
            /usr/local/bin/k3s-agent-uninstall.sh
        else
            warn "k3s uninstall script not found"
        fi
        ;;
    "status")
        kubectl get nodes -o wide
        kubectl get pods -A
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        error "Unknown command: $1. Use 'help' for usage information."
        ;;
esac