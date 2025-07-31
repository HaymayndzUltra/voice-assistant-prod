# Foundation Services Test Suite

This directory contains the test setup for the `foundation_services` agent group from your AI system monorepo.

## 🏗️ Foundation Services

The foundation services are the core agents that provide essential system functionality:

1. **ServiceRegistry** (Port 7200) - Service discovery and registration
2. **SystemDigitalTwin** (Port 7220) - System state monitoring
3. **RequestCoordinator** (Port 26002) - Request routing and coordination
4. **ModelManagerSuite** (Port 7211) - Model management and hybrid LLM routing
5. **VRAMOptimizerAgent** (Port 5572) - GPU memory optimization
6. **ObservabilityHub** (Port 9000) - System monitoring and metrics
7. **UnifiedSystemAgent** (Port 7201) - Unified system interface

## 🚀 Quick Start

### Local Testing

```bash
# Build the test Docker image
docker build -f docker/Dockerfile.foundation-test -t foundation-services-test .

# Start foundation services
docker-compose -f docker-compose.foundation-test.yml up -d

# Check health
docker exec foundation-services-test python3 /app/test/health_check_foundation.py

# View logs
docker logs foundation-services-test

# Stop services
docker-compose -f docker-compose.foundation-test.yml down
```

### Manual Testing

```bash
# Start services manually
python3 test/start_foundation_services.py

# Check health
python3 test/health_check_foundation.py
```

## 📋 Test Files

- **`start_foundation_services.py`** - Startup script that launches services in dependency order
- **`health_check_foundation.py`** - Health check script for Docker healthcheck
- **`docker-compose.foundation-test.yml`** - Docker Compose configuration
- **`docker/Dockerfile.foundation-test`** - Docker image for testing

## 🔧 Configuration

### Environment Variables

```bash
# Test mode settings
TEST_MODE=true
SKIP_GPU_CHECKS=true
MOCK_MODELS=true
HEALTH_CHECK_TIMEOUT=30

# Foundation service settings
PORT_OFFSET=0
LOG_LEVEL=INFO
ENABLE_HYBRID_INFERENCE=true
HYBRID_QUALITY_THRESHOLD=0.85
```

### Port Mapping

| Service | Main Port | Health Port |
|---------|-----------|-------------|
| ServiceRegistry | 7200 | 8200 |
| SystemDigitalTwin | 7220 | 8220 |
| RequestCoordinator | 26002 | 27002 |
| ModelManagerSuite | 7211 | 8211 |
| VRAMOptimizerAgent | 5572 | 6572 |
| ObservabilityHub | 9000 | 9001 |
| UnifiedSystemAgent | 7201 | 8201 |

## 🧪 GitHub Workflow

The `.github/workflows/test-foundation-services.yml` workflow automatically tests:

1. **Service Startup** - Verifies all services start in correct order
2. **Health Checks** - Validates health endpoints respond correctly
3. **Connectivity** - Tests port accessibility and service communication
4. **Integration** - Tests service interactions and API endpoints
5. **Performance** - Measures response times and resource usage
6. **Error Detection** - Monitors logs for errors and exceptions

### Trigger Conditions

The workflow runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Changes to foundation service files

## 🔍 Health Check Details

### Service Health Endpoints

Each service exposes a health endpoint at `http://localhost:{health_port}/health`:

```bash
# Example health check
curl http://localhost:8200/health  # ServiceRegistry
curl http://localhost:8220/health  # SystemDigitalTwin
curl http://localhost:8211/health  # ModelManagerSuite
```

### Health Check Response

```json
{
  "status": "healthy",
  "service": "ServiceRegistry",
  "timestamp": "2025-01-30T10:30:00Z",
  "uptime": 3600,
  "version": "1.0.0"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check for port conflicts
   netstat -tulpn | grep :7200
   ```

2. **Service Dependencies**
   ```bash
   # Check service startup order
   docker logs foundation-services-test | grep "Starting"
   ```

3. **Health Check Failures**
   ```bash
   # Manual health check
   python3 test/health_check_foundation.py
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG_MODE=true

# Start with debug output
python3 test/start_foundation_services.py
```

## 📊 Performance Metrics

The test suite monitors:

- **Startup Time** - Time to start all services
- **Response Time** - Health endpoint response times
- **Resource Usage** - CPU and memory consumption
- **Error Rate** - Failed health checks and exceptions

### Performance Thresholds

- **Startup Time**: < 60 seconds
- **Health Response**: < 5 seconds
- **Memory Usage**: < 2GB total
- **Error Rate**: 0% for healthy services

## 🔄 Continuous Integration

The foundation services test is integrated into your CI/CD pipeline:

1. **Pre-commit** - Basic health checks
2. **Pull Request** - Full integration testing
3. **Deployment** - Production readiness validation

## 📝 Test Results

Successful test execution shows:

```
🎉 Foundation Services Test Completed Successfully!
✅ All 7 foundation services are running and healthy
✅ Service connectivity verified
✅ Health endpoints responding
✅ Performance within acceptable limits
```

## 🤝 Contributing

To add new foundation services:

1. Update `start_foundation_services.py` with new service config
2. Add health check in `health_check_foundation.py`
3. Update port mapping in documentation
4. Add integration tests to GitHub workflow

## 📚 Related Documentation

- [Main Startup Configuration](../main_pc_code/config/startup_config.yaml)
- [Docker Setup](../docker/)
- [Agent Documentation](../main_pc_code/agents/)
- [Model Manager Suite](../main_pc_code/model_manager_suite.py) 