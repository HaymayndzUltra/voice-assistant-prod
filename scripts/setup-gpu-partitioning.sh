#!/bin/bash
# GPU Partitioning Setup Script for AI System
# Supports both RTX 4090 (MPS) and RTX 3060 (shared access) configurations

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Check if NVIDIA drivers and tools are available
check_nvidia_requirements() {
    if ! command -v nvidia-smi &> /dev/null; then
        error "nvidia-smi not found. Please install NVIDIA drivers."
    fi
    
    if ! command -v nvidia-ml-py &> /dev/null 2>&1 && ! python3 -c "import pynvml" &> /dev/null; then
        warn "nvidia-ml-py not available. Installing..."
        pip3 install nvidia-ml-py3
    fi
    
    log "NVIDIA requirements satisfied"
}

# Detect GPU models and capabilities
detect_gpu_info() {
    log "Detecting GPU configuration..."
    
    # Get GPU information
    GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits | head -1)
    GPU_MODELS=$(nvidia-smi --query-gpu=name --format=csv,noheader)
    GPU_MEMORY=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
    
    info "Found ${GPU_COUNT} GPU(s):"
    
    local gpu_index=0
    while IFS= read -r model; do
        local memory=$(echo "$GPU_MEMORY" | sed -n "$((gpu_index + 1))p")
        info "  GPU ${gpu_index}: ${model} (${memory} MB)"
        
        # Check MIG capability (RTX 4090 and newer enterprise cards)
        if nvidia-smi -i $gpu_index --query-gpu=mig.mode.current --format=csv,noheader 2>/dev/null | grep -q "Enabled\|Disabled"; then
            MIG_CAPABLE_GPUS+=($gpu_index)
            info "    └─ MIG capable"
        else
            MPS_GPUS+=($gpu_index)
            info "    └─ MPS suitable"
        fi
        
        ((gpu_index++))
    done <<< "$GPU_MODELS"
}

# Setup MIG partitioning for capable GPUs (RTX 4090, A100, etc.)
setup_mig_partitioning() {
    local gpu_id=$1
    
    log "Setting up MIG partitioning for GPU ${gpu_id}..."
    
    # Enable MIG mode
    if ! nvidia-smi -i $gpu_id --mig-mode=1; then
        warn "Failed to enable MIG mode on GPU ${gpu_id}. Falling back to MPS."
        setup_mps_partitioning $gpu_id
        return
    fi
    
    # Reset GPU to clear existing MIG instances
    nvidia-smi mig -i $gpu_id -dci
    nvidia-smi mig -i $gpu_id -dgi
    
    # Create MIG instances based on workload requirements
    # For AI workloads, we'll create multiple 1g.5gb instances
    
    log "Creating MIG instances..."
    
    # Create GPU instances (adjust based on your RTX 4090 capabilities)
    # RTX 4090: typically supports 2x 1g.10gb or 4x 1g.5gb instances
    
    nvidia-smi mig -i $gpu_id -cgi 1g.10gb,1g.10gb || {
        warn "Failed to create 1g.10gb instances, trying 1g.5gb..."
        nvidia-smi mig -i $gpu_id -cgi 1g.5gb,1g.5gb,1g.5gb,1g.5gb
    }
    
    # Create compute instances
    nvidia-smi mig -i $gpu_id -cci
    
    # List created instances
    nvidia-smi mig -i $gpu_id -lgip
    nvidia-smi mig -i $gpu_id -lcip
    
    log "MIG partitioning completed for GPU ${gpu_id}"
}

# Setup MPS for non-MIG capable GPUs (RTX 3060, etc.)
setup_mps_partitioning() {
    local gpu_id=$1
    
    log "Setting up CUDA MPS for GPU ${gpu_id}..."
    
    # Set environment variables for MPS
    export CUDA_VISIBLE_DEVICES=$gpu_id
    export CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps-$gpu_id
    export CUDA_MPS_LOG_DIRECTORY=/var/log/nvidia-mps-$gpu_id
    
    # Create directories
    mkdir -p $CUDA_MPS_PIPE_DIRECTORY
    mkdir -p $CUDA_MPS_LOG_DIRECTORY
    
    # Set memory limits per client (adjust based on your workload)
    # For RTX 3060 (12GB), we'll allow up to 4 clients with 2.5GB each
    local memory_limit=$((2560)) # MB per client
    
    # Start MPS daemon
    nvidia-cuda-mps-control -d
    
    # Configure memory limits
    echo "set_default_device_pinned_mem_limit 0 ${memory_limit}M" | nvidia-cuda-mps-control
    echo "set_default_active_thread_percentage 25" | nvidia-cuda-mps-control
    
    log "MPS setup completed for GPU ${gpu_id}"
    
    # Create systemd service for MPS persistence
    create_mps_service $gpu_id
}

# Create systemd service for MPS daemon persistence
create_mps_service() {
    local gpu_id=$1
    
    cat > /etc/systemd/system/nvidia-mps-gpu${gpu_id}.service << EOF
[Unit]
Description=NVIDIA MPS Daemon for GPU ${gpu_id}
After=graphical.target

[Service]
Type=forking
Environment=CUDA_VISIBLE_DEVICES=${gpu_id}
Environment=CUDA_MPS_PIPE_DIRECTORY=/tmp/nvidia-mps-${gpu_id}
Environment=CUDA_MPS_LOG_DIRECTORY=/var/log/nvidia-mps-${gpu_id}
ExecStart=/usr/bin/nvidia-cuda-mps-control -d
ExecStop=/usr/bin/nvidia-cuda-mps-control quit
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable nvidia-mps-gpu${gpu_id}.service
    
    log "Created systemd service for MPS GPU ${gpu_id}"
}

# Setup DCGM exporter for monitoring
setup_dcgm_exporter() {
    log "Setting up DCGM exporter for GPU monitoring..."
    
    # Check if DCGM is available
    if ! command -v dcgmi &> /dev/null; then
        log "Installing DCGM..."
        # Install DCGM (adjust for your distribution)
        if [[ -f /etc/debian_version ]]; then
            curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb -o cuda-keyring.deb
            dpkg -i cuda-keyring.deb
            apt-get update
            apt-get install -y datacenter-gpu-manager
        else
            warn "Please install DCGM manually for your distribution"
            return
        fi
    fi
    
    # Start DCGM daemon
    systemctl start nvidia-dcgm
    systemctl enable nvidia-dcgm
    
    # Create DCGM exporter configuration
    cat > /etc/dcgm-exporter/default-counters.csv << 'EOF'
# DCGM_FI_DEV_GPU_UTIL, gauge, GPU utilization (in %).
DCGM_FI_DEV_GPU_UTIL, gauge, GPU utilization.
# DCGM_FI_DEV_MEM_COPY_UTIL, gauge, Memory utilization (in %).
DCGM_FI_DEV_MEM_COPY_UTIL, gauge, Memory utilization.
# DCGM_FI_DEV_POWER_USAGE, gauge, Power draw (in W).
DCGM_FI_DEV_POWER_USAGE, gauge, Power usage in watts.
# DCGM_FI_DEV_GPU_TEMP, gauge, GPU temperature (in C).
DCGM_FI_DEV_GPU_TEMP, gauge, GPU temperature in Celsius.
# DCGM_FI_DEV_FB_USED, gauge, Framebuffer memory used (in MiB).
DCGM_FI_DEV_FB_USED, gauge, Framebuffer memory used in MiB.
# DCGM_FI_DEV_FB_FREE, gauge, Framebuffer memory free (in MiB).
DCGM_FI_DEV_FB_FREE, gauge, Framebuffer memory free in MiB.
EOF
    
    # Create Docker Compose service for DCGM exporter
    cat > docker-compose.dcgm.yml << 'EOF'
version: "3.9"

services:
  dcgm-exporter:
    image: nvcr.io/nvidia/k8s/dcgm-exporter:3.1.8-3.1.5-ubuntu20.04
    runtime: nvidia
    environment:
      - DCGM_EXPORTER_LISTEN=:9400
      - DCGM_EXPORTER_KUBERNETES=false
    ports:
      - "9400:9400"
    volumes:
      - /etc/dcgm-exporter:/etc/dcgm-exporter:ro
    cap_add:
      - SYS_ADMIN
    devices:
      - /dev/nvidiactl
      - /dev/nvidia-uvm
      - /dev/nvidia-uvm-tools
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: ["gpu", "utility"]
    restart: unless-stopped

networks:
  default:
    name: monitoring_net
    external: true
EOF
    
    log "DCGM exporter configuration created"
}

# Generate GPU allocation configuration for Docker Compose
generate_gpu_allocation_config() {
    log "Generating GPU allocation configuration..."
    
    cat > gpu-allocation.yml << EOF
# GPU Allocation Configuration for AI System
# Generated on $(date)

gpu_allocation:
  mainpc_rtx4090:
    total_memory_gb: 24
    partitions:
      coordination: 40%      # Model loading, VRAM optimization
      reasoning: 20%         # Chain-of-thought, advanced reasoning
      learning: 20%          # Training, fine-tuning
      speech: 10%           # STT/TTS processing
      vision: 10%           # Face recognition, image processing
    
  pc2_rtx3060:
    total_memory_gb: 12
    partitions:
      vision_dream: 70%     # Primary GPU workload
      coordination: 30%     # Lightweight model operations

docker_gpu_config:
  # For MIG-enabled GPUs
  mig_devices:
$(for gpu in "${MIG_CAPABLE_GPUS[@]}"; do
    echo "    - gpu_id: $gpu"
    echo "      instances: ['MIG-GPU-xxx/0/0', 'MIG-GPU-xxx/1/0']"
done)
  
  # For MPS-enabled GPUs  
  mps_devices:
$(for gpu in "${MPS_GPUS[@]}"; do
    echo "    - gpu_id: $gpu"
    echo "      shared_access: true"
    echo "      memory_limit_mb: 2560"
done)
EOF
    
    log "GPU allocation configuration saved to gpu-allocation.yml"
}

# Main execution
main() {
    log "Starting GPU partitioning setup..."
    
    # Initialize arrays
    MIG_CAPABLE_GPUS=()
    MPS_GPUS=()
    
    # Check requirements and detect GPUs
    check_nvidia_requirements
    detect_gpu_info
    
    # Setup partitioning based on GPU capabilities
    for gpu in "${MIG_CAPABLE_GPUS[@]}"; do
        setup_mig_partitioning $gpu
    done
    
    for gpu in "${MPS_GPUS[@]}"; do
        setup_mps_partitioning $gpu
    done
    
    # Setup monitoring
    setup_dcgm_exporter
    
    # Generate configuration
    generate_gpu_allocation_config
    
    log "GPU partitioning setup completed!"
    info "Next steps:"
    info "1. Start DCGM exporter: docker-compose -f docker-compose.dcgm.yml up -d"
    info "2. Verify GPU partitioning: nvidia-smi"
    info "3. Check MPS status: echo 'get_server_list' | nvidia-cuda-mps-control"
    info "4. Monitor metrics: curl http://localhost:9400/metrics"
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    setup           Setup GPU partitioning and monitoring
    status          Show current GPU partitioning status
    stop-mps        Stop MPS daemons
    restart-dcgm    Restart DCGM services
    help            Show this help message

Examples:
    $0 setup
    $0 status
    $0 stop-mps
EOF
}

case "${1:-setup}" in
    "setup")
        main
        ;;
    "status")
        nvidia-smi
        echo ""
        echo "MPS Status:"
        echo 'get_server_list' | nvidia-cuda-mps-control 2>/dev/null || echo "MPS not running"
        ;;
    "stop-mps")
        echo 'quit' | nvidia-cuda-mps-control 2>/dev/null || echo "MPS not running"
        ;;
    "restart-dcgm")
        systemctl restart nvidia-dcgm
        docker-compose -f docker-compose.dcgm.yml restart
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        error "Unknown command: $1. Use 'help' for usage information."
        ;;
esac