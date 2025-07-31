# 🐳 **COMPLETE DOCKER DEPLOYMENT GUIDE - STEP BY STEP**

## 📖 **PARA SA AI ASSISTANT: ANO ANG DOCKER DEPLOYMENT?**

### 🎯 **BASIC CONCEPT:**
```
BEFORE (Traditional):
- Install Python sa server
- Install dependencies manually  
- Run python app.py
- Pag may error, mahirap i-debug
- Different environments = different results

AFTER (Docker):
- Create "container" = mini-computer with everything included
- Same environment everywhere (dev, test, prod)
- Easy to start/stop/restart services
- Isolated - hindi nagiinterfere ang services
```

### 🏗️ **ARCHITECTURE OVERVIEW:**
```
AI SYSTEM
├── MainPC (High-end: RTX 4090, 64GB RAM)
│   ├── 11 Docker Groups
│   └── Heavy AI processing
├── PC2 (Mid-range: RTX 3060, 16GB RAM)  
│   ├── 7 Docker Groups
│   └── Support services
└── Network Communication between PCs
```

---

## 🎯 **STEP 1: PREREQUISITES & ENVIRONMENT SETUP**

### 📋 **1.1 System Requirements Check:**
```bash
# Check available resources
echo "=== SYSTEM INFO ==="
free -h                    # Memory
df -h                     # Disk space
nvidia-smi               # GPU info
docker --version         # Docker installed?
docker-compose --version # Docker Compose installed?
```

**MainPC Requirements:**
- RAM: 64GB total (32GB for AI, 16GB for services, 16GB for OS)
- GPU: RTX 4090 (24GB VRAM)
- Storage: 2TB NVMe SSD
- Network: Gigabit ethernet

**PC2 Requirements:**
- RAM: 16GB total (8GB for services, 8GB for OS)
- GPU: RTX 3060 (12GB VRAM) 
- Storage: 500GB SSD
- Network: Gigabit ethernet

### 📋 **1.2 Install Dependencies:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install NVIDIA Container Toolkit (for GPU support)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify GPU works in Docker
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

### 📋 **1.3 Network Configuration:**
```bash
# Create Docker networks
docker network create ai-network --subnet=172.20.0.0/16
docker network create monitoring-network --subnet=172.21.0.0/16

# Configure firewall (Ubuntu UFW)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8080:8090/tcp # AI services
sudo ufw allow 3000/tcp    # Grafana
sudo ufw allow 9090/tcp    # Prometheus
sudo ufw enable
```

---

## 🐳 **STEP 2: DOCKER GROUPS EXPLANATION**

### 🏗️ **MAINPC GROUPS (11 Groups):**

**Group 1: Core Coordination**
```yaml
services:
  - coordination_hub
  - system_orchestrator
dependencies: []
purpose: "Central control and task distribution"
resources: 
  cpu: "2"
  memory: "4G"
```

**Group 2: AI Processing Pipeline**
```yaml
services:
  - ai_processor_gpu1
  - ai_processor_gpu2
dependencies: ["coordination"]
purpose: "Heavy AI computation using RTX 4090"
resources:
  cpu: "8"
  memory: "16G" 
  gpu: "MIG 1/4"
```

**Group 3: Memory & Context Management**
```yaml
services:
  - memory_manager
  - context_processor
dependencies: ["coordination"]
purpose: "Manage AI memory and conversation context"
resources:
  cpu: "4"
  memory: "8G"
```

**Group 4: NLP & Language Processing**
```yaml
services:
  - nlp_processor
  - language_analyzer
dependencies: ["memory_management"]
purpose: "Natural language understanding"
resources:
  cpu: "6"
  memory: "12G"
  gpu: "MIG 1/4"
```

**Group 5: Task Management**
```yaml
services:
  - task_coordinator
  - queue_manager
dependencies: ["coordination"]
purpose: "Manage task queues and execution"
resources:
  cpu: "2"
  memory: "4G"
```

**Group 6: Knowledge & Retrieval**
```yaml
services:
  - knowledge_base
  - retrieval_engine
dependencies: ["memory_management"]
purpose: "Knowledge search and retrieval"
resources:
  cpu: "4"
  memory: "8G"
```

**Group 7: Code Analysis**
```yaml
services:
  - code_analyzer
  - syntax_processor
dependencies: ["nlp_processing"]
purpose: "Code understanding and analysis"
resources:
  cpu: "4"
  memory: "6G"
```

**Group 8: Response Generation**
```yaml
services:
  - response_generator
  - output_formatter
dependencies: ["ai_processing", "nlp_processing"]
purpose: "Generate and format AI responses"
resources:
  cpu: "6"
  memory: "10G"
  gpu: "MIG 1/4"
```

**Group 9: Audio Processing**
```yaml
services:
  - audio_processor
  - speech_synthesizer
dependencies: ["response_generation"]
purpose: "Audio input/output processing"
resources:
  cpu: "4"
  memory: "6G"
  gpu: "MIG 1/4"
```

**Group 10: Session Management**
```yaml
services:
  - session_manager
  - state_coordinator
dependencies: ["task_management"]
purpose: "Manage user sessions and state"
resources:
  cpu: "2"
  memory: "3G"
```

**Group 11: External Integrations**
```yaml
services:
  - api_gateway
  - integration_hub
dependencies: ["session_management"]
purpose: "External API and service integrations"
resources:
  cpu: "2"
  memory: "2G"
```

### 🏗️ **PC2 GROUPS (7 Groups):**

**Group 1: Database Services**
```yaml
services:
  - postgresql
  - redis
  - mongodb
dependencies: []
purpose: "Data storage and caching"
resources:
  cpu: "4"
  memory: "6G"
```

**Group 2: Monitoring & Observability**
```yaml
services:
  - prometheus
  - grafana
  - jaeger
dependencies: []
purpose: "System monitoring and metrics"
resources:
  cpu: "2"
  memory: "4G"
```

**Group 3: Security & Authentication**
```yaml
services:
  - auth_service
  - security_scanner
dependencies: ["database_services"]
purpose: "Authentication and security"
resources:
  cpu: "2"
  memory: "2G"
```

**Group 4: File & Media Processing**
```yaml
services:
  - file_processor
  - media_converter
dependencies: ["database_services"]
purpose: "Handle file uploads and media"
resources:
  cpu: "3"
  memory: "4G"
  gpu: "shared"
```

**Group 5: Backup & Storage**
```yaml
services:
  - backup_service
  - storage_manager
dependencies: ["database_services"]
purpose: "Data backup and storage management"
resources:
  cpu: "2"
  memory: "2G"
```

**Group 6: Network & Communication**
```yaml
services:
  - network_router
  - message_broker
dependencies: []
purpose: "Inter-service communication"
resources:
  cpu: "2"
  memory: "2G"
```

**Group 7: Utility Services**
```yaml
services:
  - log_aggregator
  - health_checker
dependencies: ["monitoring"]
purpose: "System utilities and health monitoring"
resources:
  cpu: "1"
  memory: "1G"
```

---

## 🔧 **STEP 3: DOCKER COMPOSE CONFIGURATION**

### 📋 **3.1 MainPC Docker Compose:**
```yaml
# main_pc_code/config/docker-compose.yml
version: '3.9'

networks:
  ai-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  # Group 1: Core Coordination
  coordination:
    build:
      context: ../services/coordination
      dockerfile: Dockerfile
    networks:
      - ai-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=info
    
  # Group 2: AI Processing Pipeline  
  ai_processing:
    build:
      context: ../services/ai_processing
      dockerfile: Dockerfile
    networks:
      - ai-network
    depends_on:
      - coordination
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]
    environment:
      - CUDA_VISIBLE_DEVICES=0
      - GPU_MEMORY_FRACTION=0.25
    
  # ... (continue for all 11 groups)
```

### 📋 **3.2 PC2 Docker Compose:**
```yaml
# pc2_code/config/docker-compose.yml
version: '3.9'

networks:
  support-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16

services:
  # Group 1: Database Services
  database_services:
    build:
      context: ../services/database
      dockerfile: Dockerfile
    networks:
      - support-network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 6G
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - redis_data:/data
    environment:
      - POSTGRES_DB=aidb
      - POSTGRES_USER=aiuser
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    
  # ... (continue for all 7 groups)

volumes:
  postgres_data:
  redis_data:
  
secrets:
  db_password:
    external: true
```

---

## 🧪 **STEP 4: TESTING STRATEGY**

### 📋 **4.1 Unit Testing (Per Service):**
```bash
# Test individual services before building
cd services/coordination
python -m pytest tests/ -v
docker build -t coordination:test .
docker run --rm coordination:test python -m pytest
```

### 📋 **4.2 Integration Testing:**
```bash
# Test service-to-service communication
docker-compose -f docker-compose.test.yml up -d
python tests/integration/test_service_communication.py
docker-compose -f docker-compose.test.yml down
```

### 📋 **4.3 End-to-End Testing:**
```bash
# Full system test
docker-compose up -d
sleep 60  # Wait for all services to start

# Run E2E tests
python tests/e2e/test_full_workflow.py
python tests/e2e/test_ai_processing.py
python tests/e2e/test_cross_pc_communication.py

# Performance tests
python tests/performance/test_load.py
python tests/performance/test_gpu_utilization.py
```

### 📋 **4.4 Health Check Testing:**
```bash
# Verify all services are healthy
for service in $(docker-compose ps --services); do
  echo "Checking $service..."
  docker-compose exec $service curl -f http://localhost:8080/health || echo "$service FAILED"
done
```

---

## 🚀 **STEP 5: DEPLOYMENT WORKFLOW**

### 📋 **5.1 Pre-Deployment Checklist:**
```bash
#!/bin/bash
# scripts/pre-deployment-check.sh

echo "=== PRE-DEPLOYMENT CHECKLIST ==="

# Check system resources
echo "1. Checking system resources..."
free -h | grep Mem
df -h | grep -E "(sda|nvme)"

# Check Docker
echo "2. Checking Docker..."
docker version || exit 1
docker-compose version || exit 1

# Check GPU
echo "3. Checking GPU..."
nvidia-smi || exit 1

# Check networks
echo "4. Checking networks..."
docker network ls | grep ai-network || docker network create ai-network

# Check secrets
echo "5. Checking secrets..."
docker secret ls | grep db_password || echo "WARN: db_password secret missing"

# Check configuration files
echo "6. Checking config files..."
test -f docker-compose.yml || exit 1
test -f .env || exit 1

echo "✅ Pre-deployment check complete!"
```

### 📋 **5.2 MainPC Deployment:**
```bash
#!/bin/bash
# Deploy MainPC services

echo "=== MAINPC DEPLOYMENT ==="
cd main_pc_code/config

# Step 1: Pull/build images
echo "Building images..."
docker-compose build --parallel

# Step 2: Start coordination first
echo "Starting coordination services..."
docker-compose up -d coordination
sleep 30

# Step 3: Start AI processing
echo "Starting AI processing..."
docker-compose up -d ai_processing memory_management
sleep 60

# Step 4: Start dependent services
echo "Starting dependent services..."
docker-compose up -d nlp_processing task_management
sleep 30

# Step 5: Start remaining services
echo "Starting remaining services..."
docker-compose up -d

# Step 6: Verify deployment
echo "Verifying deployment..."
./scripts/verify-deployment.sh
```

### 📋 **5.3 PC2 Deployment:**
```bash
#!/bin/bash
# Deploy PC2 services

echo "=== PC2 DEPLOYMENT ==="
cd pc2_code/config

# Step 1: Start databases first
echo "Starting database services..."
docker-compose up -d database_services
sleep 60

# Step 2: Start monitoring
echo "Starting monitoring..."
docker-compose up -d monitoring
sleep 30

# Step 3: Start remaining services
echo "Starting support services..."
docker-compose up -d

# Step 4: Verify deployment
echo "Verifying deployment..."
./scripts/verify-deployment.sh
```

---

## 🔍 **STEP 6: VERIFICATION & VALIDATION**

### 📋 **6.1 Service Health Verification:**
```bash
#!/bin/bash
# scripts/verify-deployment.sh

echo "=== DEPLOYMENT VERIFICATION ==="

# Check all containers are running
echo "1. Container status:"
docker-compose ps

# Check health endpoints
echo "2. Health endpoints:"
services=(
  "coordination:8080"
  "ai_processing:8081"
  "memory_management:8082"
  "nlp_processing:8083"
  "task_management:8084"
)

for service in "${services[@]}"; do
  IFS=':' read -r name port <<< "$service"
  echo -n "Checking $name... "
  if curl -f -s "http://localhost:$port/health" > /dev/null; then
    echo "✅ HEALTHY"
  else
    echo "❌ UNHEALTHY"
  fi
done

# Check GPU utilization
echo "3. GPU utilization:"
nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits

# Check memory usage
echo "4. Memory usage:"
free -h

# Check logs for errors
echo "5. Recent errors:"
docker-compose logs --tail=100 | grep -i error | tail -10
```

### 📋 **6.2 Cross-PC Communication Test:**
```bash
#!/bin/bash
# Test communication between MainPC and PC2

echo "=== CROSS-PC COMMUNICATION TEST ==="

# Test MainPC -> PC2
echo "Testing MainPC -> PC2..."
curl -f "http://pc2-ip:8080/api/status" || echo "❌ MainPC->PC2 failed"

# Test PC2 -> MainPC  
echo "Testing PC2 -> MainPC..."
curl -f "http://mainpc-ip:8080/api/status" || echo "❌ PC2->MainPC failed"

# Test database connectivity
echo "Testing database connectivity..."
docker-compose exec ai_processing python -c "
import psycopg2
conn = psycopg2.connect(host='pc2-ip', port=5432, database='aidb')
print('✅ Database connection successful')
"
```

### 📋 **6.3 Performance Validation:**
```bash
#!/bin/bash
# Performance benchmarks

echo "=== PERFORMANCE VALIDATION ==="

# AI processing latency
echo "1. AI processing latency:"
time curl -X POST "http://localhost:8081/api/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world test"}'

# GPU memory usage
echo "2. GPU memory usage:"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# Container resource usage
echo "3. Container resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Network latency between services
echo "4. Inter-service latency:"
docker-compose exec coordination ping -c 3 ai_processing
```

---

## 🛠️ **STEP 7: TROUBLESHOOTING & MAINTENANCE**

### 📋 **7.1 Common Issues & Solutions:**

**Issue: Service fails to start**
```bash
# Check logs
docker-compose logs service_name

# Check resource usage
docker stats
free -h

# Restart service
docker-compose restart service_name
```

**Issue: GPU not detected**
```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi

# Restart Docker daemon
sudo systemctl restart docker
```

**Issue: Network connectivity problems**
```bash
# Check networks
docker network ls
docker network inspect ai-network

# Test connectivity
docker-compose exec service1 ping service2

# Recreate networks
docker-compose down
docker network prune
docker-compose up -d
```

### 📋 **7.2 Monitoring & Logs:**
```bash
# Real-time logs
docker-compose logs -f service_name

# Export logs for analysis
docker-compose logs > deployment_logs.txt

# Monitor resource usage
watch docker stats

# Monitor GPU usage
watch nvidia-smi
```

### 📋 **7.3 Backup & Recovery:**
```bash
# Backup volumes
docker run --rm -v ai_data:/data -v $(pwd):/backup alpine tar czf /backup/ai_data_backup.tar.gz /data

# Backup configuration
tar czf config_backup.tar.gz main_pc_code/ pc2_code/ scripts/

# Recovery
docker volume create ai_data_restored
docker run --rm -v ai_data_restored:/data -v $(pwd):/backup alpine tar xzf /backup/ai_data_backup.tar.gz -C /
```

---

## 📊 **STEP 8: MONITORING & OBSERVABILITY**

### 📋 **8.1 Metrics Collection:**
```yaml
# Prometheus configuration
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'ai-services'
    static_configs:
      - targets: 
        - 'coordination:8080'
        - 'ai_processing:8081'
        - 'memory_management:8082'
    metrics_path: /metrics
    
  - job_name: 'gpu-metrics'
    static_configs:
      - targets: ['dcgm-exporter:9400']
```

### 📋 **8.2 Grafana Dashboards:**
```json
{
  "dashboard": {
    "title": "AI System Overview",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job='ai-services'}"
          }
        ]
      },
      {
        "title": "GPU Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "DCGM_FI_DEV_GPU_UTIL"
          }
        ]
      }
    ]
  }
}
```

### 📋 **8.3 Alerting Rules:**
```yaml
# Alert rules
groups:
  - name: ai-system
    rules:
      - alert: ServiceDown
        expr: up{job="ai-services"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "AI service {{ $labels.instance }} is down"
          
      - alert: HighGPUUsage
        expr: DCGM_FI_DEV_GPU_UTIL > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU utilization is above 90%"
```

---

## 🎯 **STEP 9: PRODUCTION CHECKLIST**

### ✅ **Pre-Production:**
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] End-to-end tests pass
- [ ] Performance benchmarks meet requirements
- [ ] Security scan completed
- [ ] Backup procedures tested
- [ ] Monitoring configured
- [ ] Alerting rules configured
- [ ] Documentation updated

### ✅ **Production Deployment:**
- [ ] Blue-green deployment strategy
- [ ] Database migration scripts ready
- [ ] Rollback plan prepared
- [ ] Health checks configured
- [ ] Load balancer configured
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] DNS records updated

### ✅ **Post-Production:**
- [ ] All services healthy
- [ ] Metrics flowing to monitoring
- [ ] Alerts configured and tested
- [ ] Performance within SLA
- [ ] Security monitoring active
- [ ] Backup jobs running
- [ ] Documentation updated
- [ ] Team trained on operations

---

## 📚 **QUICK REFERENCE COMMANDS**

### 🚀 **Deployment:**
```bash
# Full deployment
./scripts/deploy-all.sh

# Deploy MainPC only
cd main_pc_code/config && docker-compose up -d

# Deploy PC2 only  
cd pc2_code/config && docker-compose up -d
```

### 🔍 **Monitoring:**
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f

# Check resource usage
docker stats

# Check GPU
nvidia-smi
```

### 🛠️ **Maintenance:**
```bash
# Update images
docker-compose pull && docker-compose up -d

# Restart all services
docker-compose restart

# Clean up
docker system prune -f
```

### 🆘 **Emergency:**
```bash
# Stop all services
docker-compose down

# Emergency restart
docker-compose down && docker-compose up -d

# Check for issues
./scripts/health-check.sh
```

---

## 🎯 **SUCCESS CRITERIA**

**Deployment is successful when:**
1. ✅ All containers running and healthy
2. ✅ GPU utilization visible in monitoring
3. ✅ Cross-PC communication working
4. ✅ AI processing responds within 2 seconds
5. ✅ No critical errors in logs
6. ✅ Monitoring dashboards showing data
7. ✅ Backup procedures working
8. ✅ Load tests pass performance requirements

**Your AI System is now PRODUCTION READY! 🚀**