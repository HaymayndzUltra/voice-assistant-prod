# Local AI System Deployment Guide

## 🚀 Quick Start Guide

This guide will help you deploy the production-ready AI System on your local machine with enterprise-grade capabilities.

## 📋 Prerequisites

### System Requirements

**Minimum Hardware**:
- CPU: 8+ cores (Intel i7/AMD Ryzen 7 or better)
- RAM: 32GB+ (64GB recommended)
- Storage: 500GB+ SSD
- GPU: NVIDIA RTX 3060 or better (RTX 4090 recommended)

**Operating System**:
- Ubuntu 20.04+ / Debian 11+
- CentOS 8+ / RHEL 8+
- macOS 12+ (with Docker Desktop)
- Windows 11 with WSL2

### Required Software

1. **Docker & Docker Compose**
2. **NVIDIA Drivers & Container Toolkit**
3. **Git**
4. **Python 3.9+**
5. **jq, curl, bc** (for scripts)

## 🛠️ Step-by-Step Installation

### Step 1: Setup Local Environment Prerequisites

#### Install Docker & Docker Compose

**Ubuntu/Debian**:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes
```

**macOS**:
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or using Homebrew:
brew install --cask docker
```

#### Install NVIDIA Drivers & Container Toolkit

**Ubuntu/Debian**:
```bash
# Install NVIDIA drivers
sudo apt update
sudo apt install nvidia-driver-535 nvidia-utils-535

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install nvidia-container-toolkit
sudo systemctl restart docker

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

#### Install Required Tools

```bash
# Ubuntu/Debian
sudo apt install git python3 python3-pip jq curl bc

# macOS
brew install git python3 jq curl bc

# Verify installations
docker --version
docker-compose --version
nvidia-smi
git --version
python3 --version
```

### Step 2: Clone and Configure Repository

```bash
# Clone the repository
git clone https://github.com/your-org/AI_System_Monorepo.git
cd AI_System_Monorepo

# Make scripts executable
chmod +x scripts/*.sh

# Install Python dependencies
pip3 install -r requirements.txt
```

### Step 3: Configure Secrets and Environment Variables

```bash
# Initialize Docker secrets
./scripts/manage-secrets.sh init

# Set required environment variables
export OPENAI_API_KEY="your-openai-api-key"
export DATABASE_PASSWORD="secure-password"
export JWT_SECRET="your-jwt-secret"
export GRAFANA_PASSWORD="ai-system-2024"

# Save to .env file
cat > .env << EOF
OPENAI_API_KEY=${OPENAI_API_KEY}
DATABASE_PASSWORD=${DATABASE_PASSWORD}
JWT_SECRET=${JWT_SECRET}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
EOF

# Create secrets
echo "${OPENAI_API_KEY}" | ./scripts/manage-secrets.sh create openai_api_key -
echo "${DATABASE_PASSWORD}" | ./scripts/manage-secrets.sh create database_password -
echo "${JWT_SECRET}" | ./scripts/manage-secrets.sh create jwt_secret -
```

### Step 4: Run Security Hardening

```bash
# Run security hardening (requires sudo)
sudo ./scripts/security-hardening.sh

# This will:
# - Create mTLS certificates
# - Configure Docker Content Trust
# - Setup network policies
# - Harden system configuration
```

### Step 5: Setup GPU Partitioning and Monitoring

```bash
# Setup GPU optimization (requires sudo)
sudo ./scripts/setup-gpu-partitioning.sh

# This will:
# - Configure NVIDIA MIG (RTX 4090) or MPS (RTX 3060)
# - Setup DCGM Exporter for GPU metrics
# - Create systemd services for GPU management
```

### Step 6: Deploy Core AI Services

```bash
# Start core infrastructure services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check service health
docker-compose exec coordination curl -f http://localhost:8200/health
```

### Step 7: Deploy Observability Stack

```bash
# Deploy monitoring and observability
docker-compose -f docker-compose.observability.yml up -d

# Wait for services to be ready
sleep 60

# Verify Grafana access
curl -f http://localhost:3000/api/health

# Verify Prometheus access
curl -f http://localhost:9090/api/v1/status/config

# Verify Jaeger access
curl -f http://localhost:16686/api/services
```

### Step 8: Run End-to-End Tests

```bash
# Deploy test environment
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Check test results
echo "Test Results:"
docker-compose -f docker-compose.test.yml logs e2e_test_runner
```

### Step 9: Execute Resilience Validation

```bash
# Run comprehensive resilience testing
./scripts/resilience-validation-pipeline.sh

# This will:
# - Execute chaos engineering experiments
# - Run load testing with various patterns
# - Generate resilience validation report
# - Verify system recovery capabilities
```

### Step 10: Configure Monitoring and Alerts

#### Access Dashboards

1. **Grafana**: http://localhost:3000
   - Username: `admin`
   - Password: `ai-system-2024`

2. **Prometheus**: http://localhost:9090

3. **Jaeger**: http://localhost:16686

#### Import Dashboards

```bash
# Import pre-configured dashboards
curl -X POST \
  http://admin:ai-system-2024@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @config/observability/grafana/dashboards/ai-system-overview.json

# Configure alerting rules
curl -X POST \
  http://admin:ai-system-2024@localhost:3000/api/ruler/grafana/api/v1/rules/ai-system \
  -H 'Content-Type: application/yaml' \
  -d @config/observability/grafana/alerting/slo-alerts.yaml
```

### Step 11: Setup Automated Backup and Health Monitoring

```bash
# Test backup system
./scripts/backup-restore.sh backup

# Setup automated backups (add to crontab)
echo "0 2 * * * /path/to/AI_System_Monorepo/scripts/backup-restore.sh backup" | crontab -

# Setup health monitoring
echo "*/5 * * * * /path/to/AI_System_Monorepo/scripts/health_probe.py --url http://localhost:7200/health --push-metrics" | crontab -
```

## 🔧 Configuration Options

### System Configuration

Edit `main_pc_code/config/startup_config.yaml` or `pc2_code/config/startup_config.yaml` based on your hardware:

```yaml
# For RTX 4090 (MainPC configuration)
docker_groups:
  vision_gpu:
    agents: ["vision_agent", "image_processor"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["GPU-0"]  # MIG instance
              capabilities: [gpu]

# For RTX 3060 (PC2 configuration)  
docker_groups:
  vision_dream_gpu:
    agents: ["vision_dream_agent"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["0"]  # Full GPU with MPS
              capabilities: [gpu]
```

### Performance Tuning

Edit `config/observability/slo-config.yaml` to adjust SLO targets:

```yaml
slos:
  coordination_latency:
    threshold: 0.5  # 500ms for P99 latency
    window: "5m"
  
  gpu_utilization:
    threshold: 85.0  # Max 85% GPU utilization
    lower_threshold: 60.0  # Min 60% for efficiency
```

## 📊 Monitoring Your Deployment

### Key Metrics to Watch

1. **System Health**:
   ```bash
   # Check SLO compliance
   curl -s "http://localhost:9090/api/v1/query?query=ai_system_slo_compliance" | jq .
   
   # Check service availability
   curl -s "http://localhost:9090/api/v1/query?query=ai_system_availability_percentage" | jq .
   ```

2. **Resource Utilization**:
   ```bash
   # GPU utilization
   curl -s "http://localhost:9090/api/v1/query?query=nvidia_smi_utilization_gpu_ratio" | jq .
   
   # Memory usage
   curl -s "http://localhost:9090/api/v1/query?query=node_memory_MemAvailable_bytes" | jq .
   ```

3. **Performance Metrics**:
   ```bash
   # Response times
   curl -s "http://localhost:9090/api/v1/query?query=ai_system_response_time_p99_seconds" | jq .
   
   # Request rates
   curl -s "http://localhost:9090/api/v1/query?query=rate(ai_request_count[5m])" | jq .
   ```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| SLO Compliance | < 95% | < 90% |
| GPU Utilization | > 90% | > 95% |
| Memory Usage | > 80% | > 90% |
| Response Time P99 | > 2s | > 5s |
| Error Rate | > 1% | > 5% |

## 🚨 Troubleshooting

### Common Issues

1. **Docker Permission Denied**:
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

2. **GPU Not Detected**:
   ```bash
   # Check NVIDIA drivers
   nvidia-smi
   
   # Restart Docker with GPU support
   sudo systemctl restart docker
   
   # Test GPU access
   docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
   ```

3. **Port Conflicts**:
   ```bash
   # Check port usage
   sudo netstat -tulpn | grep :3000
   
   # Modify docker-compose.yml if needed
   ```

4. **Service Startup Failures**:
   ```bash
   # Check service logs
   docker-compose logs [service_name]
   
   # Restart specific service
   docker-compose restart [service_name]
   ```

5. **Memory Issues**:
   ```bash
   # Free up memory
   docker system prune -f
   
   # Adjust service memory limits in docker-compose.yml
   ```

### Emergency Procedures

1. **Full System Reset**:
   ```bash
   # Stop all services
   docker-compose down
   docker-compose -f docker-compose.observability.yml down
   
   # Clean up
   docker system prune -a -f
   
   # Restart
   docker-compose up -d
   ```

2. **Backup Recovery**:
   ```bash
   # List available backups
   ./scripts/backup-restore.sh list
   
   # Restore from backup
   ./scripts/backup-restore.sh restore [backup_date]
   ```

3. **Stop Chaos Testing**:
   ```bash
   # Emergency stop all chaos experiments
   python3 scripts/chaos-monkey.py --emergency-stop
   ```

## 🔄 Updates and Maintenance

### Regular Maintenance

**Daily**:
- Check dashboard health indicators
- Review error rates and performance metrics
- Verify backup completion

**Weekly**:
- Run resilience validation pipeline
- Update Docker images: `docker-compose pull`
- Review security alerts and patches

**Monthly**:
- Update system packages
- Rotate TLS certificates if needed
- Full disaster recovery test

### Updating the System

```bash
# Pull latest changes
git pull origin main

# Update Docker images
docker-compose pull

# Restart services with new images
docker-compose up -d

# Verify health after update
./scripts/resilience-validation-pipeline.sh
```

## 📞 Support

### Getting Help

1. **Documentation**: Check `docs/` directory for detailed guides
2. **Logs**: Review service logs with `docker-compose logs [service]`
3. **Metrics**: Use Grafana dashboards for system insights
4. **Issues**: Create GitHub issues for bugs or feature requests

### Performance Optimization

1. **GPU Optimization**:
   - Monitor GPU utilization in Grafana
   - Adjust MIG/MPS configuration as needed
   - Balance workload across GPU partitions

2. **Memory Optimization**:
   - Monitor memory usage trends
   - Adjust service memory limits
   - Enable swap if needed (not recommended for production)

3. **Network Optimization**:
   - Monitor network latency between services
   - Adjust Docker network configuration
   - Consider using host networking for high-performance workloads

---

**Deployment Status**: Follow the todo list to track your deployment progress!

**Need Help?**: Check the comprehensive documentation in `docs/AI_SYSTEM_PRODUCTION_DEPLOYMENT_SUMMARY.md` for complete system details.