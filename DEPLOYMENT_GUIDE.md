# Deployment Guide for New Services (Phases 1-7)

This guide covers the deployment and configuration of all services implemented in phases 1-7.

## Prerequisites

### System Requirements
- Python 3.10+
- Docker Engine with appropriate permissions
- Node.js 16+ (for Dashboard frontend)
- 8GB+ RAM recommended for full deployment
- GPU support (NVIDIA drivers) for optimal performance

### Python Dependencies
```bash
# Core dependencies for all services
pip install grpcio grpcio-tools fastapi uvicorn aiohttp prometheus-client
pip install psutil pyyaml docker requests python-dotenv uvloop
```

### Docker Setup
```bash
# Ensure Docker daemon is running
sudo systemctl start docker

# Add user to docker group (requires logout/login)
sudo usermod -aG docker $USER

# Verify Docker access
docker ps
```

## Service-Specific Deployment

### Phase 1: Cross-Machine GPU Scheduler

**Location:** `services/cross_gpu_scheduler/`

**Build & Deploy:**
```bash
# Build Docker image
cd services/cross_gpu_scheduler
docker build -t cross-gpu-scheduler:latest .

# Run standalone
docker run -d \
  --name cross-gpu-scheduler \
  -p 7050:7050 \
  -p 9005:9005 \
  -e PORT_OFFSET=0 \
  -e METRICS_PORT=9005 \
  cross-gpu-scheduler:latest

# Health check
curl http://localhost:9005/health
```

**Configuration:**
- Edit `main_pc_code/config/startup_config.yaml`
- Service runs on `${PORT_OFFSET}+7050`
- Metrics on `${PORT_OFFSET}+9005`

### Phase 2: Central Error Bus

**Location:** `services/central_error_bus/`

**Build & Deploy:**
```bash
# Build Docker image
cd services/central_error_bus
docker build -t central-error-bus:latest .

# Run standalone
docker run -d \
  --name central-error-bus \
  -p 7150:7150 \
  -p 8150:8150 \
  -e PORT_OFFSET=0 \
  -e METRICS_PORT=8150 \
  central-error-bus:latest

# Health check
curl http://localhost:8150/health
```

### Phase 3: Streaming Translation Proxy

**Location:** `services/streaming_translation_proxy/`

**Build & Deploy:**
```bash
# Build Docker image
cd services/streaming_translation_proxy
docker build -t translation-proxy:latest .

# Run with API keys
docker run -d \
  --name translation-proxy \
  -p 7080:7080 \
  -p 9006:9006 \
  -e PORT_OFFSET=0 \
  -e METRICS_PORT=9006 \
  -e GOOGLE_TRANSLATE_API_KEY=your_api_key \
  translation-proxy:latest
```

### Phase 4: Tutoring Service Agent

**Location:** `pc2_code/agents/TutoringServiceAgent.py`

**Deploy:**
```bash
# This is an agent, not a standalone service
# It's loaded by the PC2 system startup
# Ensure configuration is in pc2_code/config/startup_config.yaml

# Test import
python3 -c "from pc2_code.agents.TutoringServiceAgent import TutoringServiceAgent; print('Import successful')"
```

**Configuration Fix Applied:**
- The agent now correctly reads from `pc2_services` list in YAML
- Removed unused `_agent_args` variable
- Added proper error handling for configuration loading

### Phase 5: Observability Dashboard

**Location:** `services/obs_dashboard_api/` and `dashboard/`

**Backend API Deployment:**
```bash
# Build API Docker image
cd services/obs_dashboard_api
docker build -t obs-dashboard-api:latest .

# Run API
docker run -d \
  --name obs-dashboard-api \
  -p 8001:8001 \
  -p 9007:9007 \
  -e PORT_OFFSET=0 \
  -e METRICS_PORT=9007 \
  -e OBS_HUB=http://observability-hub:9000 \
  obs-dashboard-api:latest
```

**Frontend Deployment:**
```bash
# Install dependencies
cd dashboard
npm install

# Development server
npm start
# Access at http://localhost:3000

# Production build
npm run build
# Serve build/ directory with your web server
```

**Docker Compose Example:**
```yaml
version: '3.8'
services:
  obs-api:
    build: ./services/obs_dashboard_api
    ports:
      - "8001:8001"
      - "9007:9007"
    environment:
      - OBS_HUB=http://observability-hub:9000
  
  obs-ui:
    build: ./dashboard
    ports:
      - "3000:3000"
    depends_on:
      - obs-api
```

### Phase 6: Self-Healing Supervisor

**Location:** `services/self_healing_supervisor/`

**Build & Deploy:**
```bash
# Build Docker image
cd services/self_healing_supervisor
docker build -t self-healing-supervisor:latest .

# Run with Docker socket mount (CRITICAL)
docker run -d \
  --name self-healing-supervisor \
  -p 7009:7009 \
  -p 9008:9008 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e PORT_OFFSET=0 \
  -e METRICS_PORT=9008 \
  -e HEALTH_POLL_SEC=30 \
  self-healing-supervisor:latest
```

**Important Notes:**
- **REQUIRES** `/var/run/docker.sock` mount for container management
- Monitor with `docker logs self-healing-supervisor`
- Configure health check endpoints in container labels

### Phase 7: Speech Relay Service

**Location:** `services/speech_relay/`

**Build & Deploy:**
```bash
# Generate gRPC stubs first
cd services/speech_relay
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. relay.proto

# Build Docker image
docker build -t speech-relay:latest .

# Run with MainPC endpoint
docker run -d \
  --name speech-relay \
  -p 7130:7130 \
  -p 9109:9109 \
  -e PORT_OFFSET=0 \
  -e METRICS_PORT=9109 \
  -e MAINPC_TTS_ENDPOINT=mainpc:5562 \
  -e RELAY_PORT=7130 \
  speech-relay:latest
```

## Full System Deployment

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  cross-gpu-scheduler:
    build: ./services/cross_gpu_scheduler
    ports:
      - "${PORT_OFFSET:-0}7050:7050"
      - "${PORT_OFFSET:-0}9005:9005"
    environment:
      - PORT_OFFSET=${PORT_OFFSET:-0}
      - METRICS_PORT=9005

  central-error-bus:
    build: ./services/central_error_bus
    ports:
      - "${PORT_OFFSET:-0}7150:7150"
      - "${PORT_OFFSET:-0}8150:8150"
    environment:
      - PORT_OFFSET=${PORT_OFFSET:-0}
      - METRICS_PORT=8150

  translation-proxy:
    build: ./services/streaming_translation_proxy
    ports:
      - "${PORT_OFFSET:-0}7080:7080"
      - "${PORT_OFFSET:-0}9006:9006"
    environment:
      - PORT_OFFSET=${PORT_OFFSET:-0}
      - METRICS_PORT=9006
      - GOOGLE_TRANSLATE_API_KEY=${GOOGLE_TRANSLATE_API_KEY}

  obs-dashboard-api:
    build: ./services/obs_dashboard_api
    ports:
      - "${PORT_OFFSET:-0}8001:8001"
      - "${PORT_OFFSET:-0}9007:9007"
    environment:
      - PORT_OFFSET=${PORT_OFFSET:-0}
      - METRICS_PORT=9007
      - OBS_HUB=http://observability-hub:9000

  obs-dashboard-ui:
    build: ./dashboard
    ports:
      - "3000:3000"
    depends_on:
      - obs-dashboard-api

  self-healing-supervisor:
    build: ./services/self_healing_supervisor
    ports:
      - "${PORT_OFFSET:-0}7009:7009"
      - "${PORT_OFFSET:-0}9008:9008"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - PORT_OFFSET=${PORT_OFFSET:-0}
      - METRICS_PORT=9008
      - HEALTH_POLL_SEC=30

  speech-relay:
    build: ./services/speech_relay
    ports:
      - "${PORT_OFFSET:-0}7130:7130"
      - "${PORT_OFFSET:-0}9109:9109"
    environment:
      - PORT_OFFSET=${PORT_OFFSET:-0}
      - METRICS_PORT=9109
      - MAINPC_TTS_ENDPOINT=mainpc:5562
      - RELAY_PORT=7130
```

**Deploy All Services:**
```bash
# Set environment variables
export PORT_OFFSET=0
export GOOGLE_TRANSLATE_API_KEY=your_api_key

# Deploy all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Verification & Testing

### Health Checks
```bash
# Check all service health endpoints
curl http://localhost:9005/health  # Cross-GPU Scheduler
curl http://localhost:8150/health  # Central Error Bus
curl http://localhost:9006/health  # Translation Proxy
curl http://localhost:9007/health  # Observability API
curl http://localhost:9008/health  # Self-Healing Supervisor
curl http://localhost:9109/health  # Speech Relay
```

### Metrics Endpoints
```bash
# Prometheus metrics for monitoring
curl http://localhost:9005/metrics
curl http://localhost:8150/metrics
curl http://localhost:9006/metrics
curl http://localhost:9007/metrics
curl http://localhost:9008/metrics
curl http://localhost:9109/metrics
```

### Integration Tests
```bash
# Run import tests for all services
python3 -c "
import sys
sys.path.append('tests')
from test_obs_dashboard_api_import import test_import as test_api
from test_self_healer_import import test_import as test_healer
from test_speech_relay_import import test_import as test_relay
from test_tutoring_service_import import test_import as test_tutoring

print('Testing imports...')
test_api(); print('✓ Observability API')
test_healer(); print('✓ Self-Healing Supervisor') 
test_relay(); print('✓ Speech Relay')
test_tutoring(); print('✓ Tutoring Service')
print('All tests passed!')
"
```

## Troubleshooting

### Common Issues

1. **Docker Permission Denied**
   ```bash
   sudo usermod -aG docker $USER
   # Logout and login again
   ```

2. **Port Conflicts**
   ```bash
   # Change PORT_OFFSET environment variable
   export PORT_OFFSET=1000
   ```

3. **gRPC Import Errors**
   ```bash
   # Regenerate protobuf stubs
   cd services/speech_relay
   python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. relay.proto
   ```

4. **Self-Healing Supervisor Can't Access Docker**
   ```bash
   # Ensure Docker socket permissions
   sudo chmod 666 /var/run/docker.sock
   # Or run with --privileged flag (less secure)
   ```

5. **Dashboard Not Loading**
   ```bash
   # Check API connectivity
   curl http://localhost:8001/health
   
   # Rebuild frontend
   cd dashboard
   rm -rf node_modules package-lock.json
   npm install
   npm start
   ```

### Logs and Debugging
```bash
# Service logs
docker logs cross-gpu-scheduler
docker logs central-error-bus
docker logs translation-proxy
docker logs obs-dashboard-api
docker logs self-healing-supervisor
docker logs speech-relay

# Real-time monitoring
docker stats

# Container inspection
docker inspect <container_name>
```

## Performance Tuning

### Resource Limits
```yaml
# Add to docker-compose.yml services
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### Environment Optimization
```bash
# For production deployment
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Increase worker processes for APIs
export UVICORN_WORKERS=4
```

## Security Considerations

1. **API Keys:** Store in environment variables or secrets management
2. **Docker Socket:** Limit access to Self-Healing Supervisor container only
3. **Network Isolation:** Use Docker networks to isolate services
4. **Health Endpoints:** Consider adding authentication for production
5. **Metrics:** Secure Prometheus endpoints in production environments

## Monitoring Integration

### Prometheus Configuration
```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'new-services'
    static_configs:
      - targets: 
        - 'localhost:9005'  # Cross-GPU Scheduler
        - 'localhost:8150'  # Central Error Bus
        - 'localhost:9006'  # Translation Proxy
        - 'localhost:9007'  # Observability API
        - 'localhost:9008'  # Self-Healing Supervisor
        - 'localhost:9109'  # Speech Relay
```

### Grafana Dashboards
- Import dashboard configurations from `monitoring/grafana/`
- Key metrics: service uptime, request rates, error rates, resource usage
- Alerts: service down, high error rate, resource exhaustion 