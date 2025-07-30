# Deployment and Operations Guide

**Last Updated**: 2025-07-31  
**Version**: 3.4.0  
**Phase**: Phase 3.4 - Documentation & Developer Onboarding

## Table of Contents

1. [Overview](#overview)
2. [Environment Setup](#environment-setup)
3. [Deployment Strategies](#deployment-strategies)
4. [Configuration Management](#configuration-management)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security Considerations](#security-considerations)
7. [Scaling and Performance](#scaling-and-performance)
8. [Troubleshooting](#troubleshooting)

## Overview

The AI System Monorepo supports multiple deployment configurations across development, staging, and production environments. This guide covers deployment strategies, operational procedures, and best practices for maintaining a robust AI system infrastructure.

### Deployment Architecture

```
Production Deployment Architecture
├── Main PC Infrastructure
│   ├── Agent Orchestrator (52 agents)
│   ├── Central Configuration Service
│   ├── Error Bus Aggregator
│   ├── Monitoring Dashboard
│   └── Health Check Service
├── PC2 Infrastructure  
│   ├── Specialized Agents (22 agents)
│   ├── Memory Processing Services
│   ├── Vision Processing Pipeline
│   ├── Cross-Machine Bridge
│   └── Local Error Bus
├── Shared Infrastructure
│   ├── Redis Cluster (backend storage)
│   ├── Prometheus (metrics collection)
│   ├── Grafana (visualization)
│   ├── Log Aggregation (ELK/Loki)
│   └── Load Balancer (if applicable)
└── External Dependencies
    ├── External APIs
    ├── Database Systems
    ├── Message Queues
    └── File Storage
```

## Environment Setup

### Development Environment

#### Prerequisites

```bash
# Python 3.8+ with virtual environment
python3 -m venv ai_system_env
source ai_system_env/bin/activate

# Core dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Redis for local development
sudo apt-get install redis-server
# or
docker run -d --name redis -p 6379:6379 redis:alpine
```

#### Environment Configuration

```bash
# Set development environment
export AI_SYSTEM_ENV=dev
export AI_SYSTEM_DEBUG=true

# Local Redis configuration
export AI_REDIS_HOST=localhost
export AI_REDIS_PORT=6379

# Disable authentication in development
export AI_SECURITY_ENABLE_AUTH=false
export AI_SECURITY_SSL_ENABLED=false

# Enable detailed logging
export AI_LOGGING_LEVEL=DEBUG
export AI_LOGGING_CONSOLE_OUTPUT=true
```

#### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd AI_System_Monorepo

# Setup environment
./scripts/setup_dev_environment.sh

# Start development services
./scripts/start_dev_services.sh

# Run agents
python main_pc_code/agents/service_registry_agent.py
python pc2_code/agents/memory_orchestrator_service.py
```

### Staging Environment

#### Infrastructure Requirements

```yaml
# Staging infrastructure specification
staging_infrastructure:
  main_pc:
    cpu: 8 cores
    memory: 32GB
    storage: 500GB SSD
    network: 1Gbps
  
  pc2:
    cpu: 8 cores
    memory: 32GB
    storage: 500GB SSD
    network: 1Gbps
  
  redis:
    cpu: 4 cores
    memory: 16GB
    storage: 100GB SSD
    
  monitoring:
    cpu: 2 cores
    memory: 8GB
    storage: 200GB
```

### Production Environment

#### Infrastructure Requirements

```yaml
# Production infrastructure specification
production_infrastructure:
  main_pc:
    cpu: 16 cores
    memory: 64GB
    storage: 1TB NVMe SSD
    network: 10Gbps
    
  pc2:
    cpu: 16 cores
    memory: 64GB
    storage: 1TB NVMe SSD
    network: 10Gbps
    
  redis_cluster:
    nodes: 6 (3 masters, 3 replicas)
    cpu_per_node: 8 cores
    memory_per_node: 32GB
    storage_per_node: 500GB SSD
    
  monitoring_stack:
    prometheus: 4 cores, 16GB memory, 500GB storage
    grafana: 2 cores, 8GB memory, 100GB storage
    alertmanager: 2 cores, 4GB memory, 50GB storage
```

## Deployment Strategies

### 1. Single Machine Deployment

```bash
#!/bin/bash
# deploy_single_machine.sh

set -e

echo "Deploying AI System Monorepo - Single Machine"

# Setup environment
source ./scripts/setup_environment.sh

# Install dependencies
pip install -r requirements.txt

# Configure services
cp config/single_machine/redis.conf /etc/redis/
cp config/single_machine/prometheus.yml /etc/prometheus/

# Start supporting services
sudo systemctl start redis-server
sudo systemctl start prometheus

# Deploy agents
python scripts/deploy_agents.py --mode single_machine

# Verify deployment
python scripts/health_check.py

echo "Single machine deployment completed successfully"
```

### 2. Multi-Machine Deployment

```bash
#!/bin/bash
# deploy_multi_machine.sh

set -e

MAIN_PC_HOST=${1:-main-pc.internal}
PC2_HOST=${2:-pc2.internal}

echo "Deploying AI System Monorepo - Multi Machine"
echo "Main PC: $MAIN_PC_HOST"
echo "PC2: $PC2_HOST"

# Deploy to Main PC
echo "Deploying to Main PC..."
ssh $MAIN_PC_HOST << 'EOF'
  cd /opt/ai_system
  git pull origin main
  source ai_system_env/bin/activate
  pip install -r requirements.txt
  python scripts/deploy_main_pc_agents.py
  sudo systemctl restart ai-system-main
EOF

# Deploy to PC2
echo "Deploying to PC2..."
ssh $PC2_HOST << 'EOF'
  cd /opt/ai_system
  git pull origin main
  source ai_system_env/bin/activate
  pip install -r requirements.txt
  python scripts/deploy_pc2_agents.py
  sudo systemctl restart ai-system-pc2
EOF

# Verify cross-machine communication
python scripts/verify_cross_machine_communication.py \
  --main-pc $MAIN_PC_HOST --pc2 $PC2_HOST

echo "Multi-machine deployment completed successfully"
```

### 3. Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 aiuser && chown -R aiuser:aiuser /app
USER aiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python scripts/health_check.py || exit 1

# Default command
CMD ["python", "scripts/start_agents.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  ai-system-main:
    build: .
    environment:
      - AI_SYSTEM_ENV=prod
      - AI_SYSTEM_MACHINE=main_pc
      - AI_REDIS_HOST=redis
    depends_on:
      - redis
      - prometheus
    networks:
      - ai-system-network

  ai-system-pc2:
    build: .
    environment:
      - AI_SYSTEM_ENV=prod
      - AI_SYSTEM_MACHINE=pc2
      - AI_REDIS_HOST=redis
      - AI_MAIN_PC_HOST=ai-system-main
    depends_on:
      - redis
      - ai-system-main
    networks:
      - ai-system-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    networks:
      - ai-system-network

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - ai-system-network

volumes:
  redis-data:
  prometheus-data:

networks:
  ai-system-network:
    driver: bridge
```

## Configuration Management

### Environment-Specific Configurations

#### Configuration Validation

```bash
#!/bin/bash
# validate_config.sh

set -e

ENVIRONMENT=${1:-dev}

echo "Validating configuration for environment: $ENVIRONMENT"

# Validate base configuration
python -c "
from common.config.validation import validate_environment_config
result = validate_environment_config('$ENVIRONMENT')
if not result.valid:
    print('Configuration validation failed:')
    for error in result.errors:
        print(f'  - {error}')
    exit(1)
print('Configuration validation passed')
"

echo "Configuration validation completed successfully"
```

#### Configuration Deployment

```bash
#!/bin/bash
# deploy_config.sh

set -e

ENVIRONMENT=${1:-staging}
TARGET_HOST=${2:-localhost}

echo "Deploying configuration for environment: $ENVIRONMENT to $TARGET_HOST"

# Backup existing configuration
ssh $TARGET_HOST "
  if [ -d /opt/ai_system/config ]; then
    sudo cp -r /opt/ai_system/config /opt/ai_system/config.backup.$(date +%Y%m%d_%H%M%S)
  fi
"

# Deploy new configuration
scp -r config/defaults/ $TARGET_HOST:/tmp/ai_system_config/
ssh $TARGET_HOST "
  sudo mv /tmp/ai_system_config /opt/ai_system/config
  sudo chown -R aiuser:aiuser /opt/ai_system/config
  sudo chmod 644 /opt/ai_system/config/*.yaml
"

echo "Configuration deployment completed successfully"
```

## Monitoring and Observability

### Health Checks

```python
#!/usr/bin/env python3
# scripts/health_check.py

import sys
import requests
from typing import Tuple

class HealthChecker:
    def __init__(self):
        self.checks = [
            ("Redis Connection", self.check_redis),
            ("Main PC Agents", self.check_main_pc_agents),
            ("PC2 Agents", self.check_pc2_agents),
            ("Cross-Machine Communication", self.check_cross_machine),
            ("Error Bus", self.check_error_bus),
            ("Monitoring Stack", self.check_monitoring)
        ]
    
    def check_redis(self) -> Tuple[bool, str]:
        try:
            import redis
            from common.config import Config
            
            config = Config.for_agent(__file__)
            r = redis.Redis(
                host=config.str("redis.host", "localhost"),
                port=config.int("redis.port", 6379)
            )
            r.ping()
            return True, "Redis is healthy"
        except Exception as e:
            return False, f"Redis check failed: {str(e)}"
    
    def check_main_pc_agents(self) -> Tuple[bool, str]:
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                return True, "Main PC agents are healthy"
            else:
                return False, f"Main PC agents check failed: {response.status_code}"
        except Exception as e:
            return False, f"Main PC agents check failed: {str(e)}"
    
    def check_pc2_agents(self) -> Tuple[bool, str]:
        try:
            response = requests.get("http://pc2:8080/health", timeout=5)
            if response.status_code == 200:
                return True, "PC2 agents are healthy"
            else:
                return False, f"PC2 agents check failed: {response.status_code}"
        except Exception as e:
            return False, f"PC2 agents check failed: {str(e)}"
    
    def check_cross_machine(self) -> Tuple[bool, str]:
        try:
            import zmq
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect("tcp://pc2:5555")
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            
            socket.send_string("health_check")
            response = socket.recv_string()
            
            if response == "healthy":
                return True, "Cross-machine communication is healthy"
            else:
                return False, f"Cross-machine communication failed: {response}"
        except Exception as e:
            return False, f"Cross-machine communication check failed: {str(e)}"
    
    def check_error_bus(self) -> Tuple[bool, str]:
        try:
            from common.error_handling import ErrorPublisher
            
            publisher = ErrorPublisher()
            publisher.report_error(
                error_type="health_check",
                severity="info",
                message="Health check test message",
                context={"source": "health_checker"}
            )
            return True, "Error bus is healthy"
        except Exception as e:
            return False, f"Error bus check failed: {str(e)}"
    
    def check_monitoring(self) -> Tuple[bool, str]:
        try:
            response = requests.get("http://localhost:9090/-/healthy", timeout=5)
            if response.status_code == 200:
                return True, "Monitoring stack is healthy"
            else:
                return False, f"Monitoring check failed: {response.status_code}"
        except Exception as e:
            return False, f"Monitoring check failed: {str(e)}"
    
    def run_checks(self) -> bool:
        print("Running AI System Health Checks...")
        print("=" * 50)
        
        all_healthy = True
        
        for check_name, check_func in self.checks:
            print(f"Checking {check_name}...", end=" ")
            
            try:
                healthy, message = check_func()
                if healthy:
                    print(f"✓ {message}")
                else:
                    print(f"✗ {message}")
                    all_healthy = False
            except Exception as e:
                print(f"✗ Check failed with exception: {str(e)}")
                all_healthy = False
        
        print("=" * 50)
        if all_healthy:
            print("✓ All health checks passed")
            return True
        else:
            print("✗ Some health checks failed")
            return False

if __name__ == "__main__":
    checker = HealthChecker()
    healthy = checker.run_checks()
    sys.exit(0 if healthy else 1)
```

### Prometheus Configuration

```yaml
# config/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'ai-system-main'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    metrics_path: /metrics

  - job_name: 'ai-system-pc2'
    static_configs:
      - targets: ['pc2:8000']
    scrape_interval: 15s
    metrics_path: /metrics

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100', 'pc2:9100']
    scrape_interval: 30s
```

## Security Considerations

### SSL/TLS Configuration

```bash
#!/bin/bash
# scripts/generate_certificates.sh

set -e

CERT_DIR="/etc/ssl/ai-system"
DAYS=365

echo "Generating SSL certificates for AI System..."

# Create certificate directory
sudo mkdir -p $CERT_DIR
cd $CERT_DIR

# Generate CA private key
sudo openssl genrsa -out ca-key.pem 4096

# Generate CA certificate
sudo openssl req -new -x509 -days $DAYS -key ca-key.pem -sha256 -out ca.pem -subj "/C=US/ST=CA/L=SF/O=AI System/CN=AI System CA"

# Generate server private key
sudo openssl genrsa -out server-key.pem 4096

# Generate server certificate signing request
sudo openssl req -subj "/C=US/ST=CA/L=SF/O=AI System/CN=ai-system" -sha256 -new -key server-key.pem -out server.csr

# Generate server certificate
sudo openssl x509 -req -days $DAYS -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem -out server-cert.pem

# Set permissions
sudo chmod 400 *-key.pem
sudo chmod 444 *.pem
sudo rm server.csr

echo "SSL certificates generated successfully in $CERT_DIR"
```

### Network Security

```bash
#!/bin/bash
# scripts/setup_firewall.sh

set -e

echo "Configuring firewall for AI System..."

# Allow SSH
sudo ufw allow ssh

# Allow AI System ports
sudo ufw allow 8000:8100/tcp  # Agent ports
sudo ufw allow 9090/tcp       # Prometheus
sudo ufw allow 3000/tcp       # Grafana
sudo ufw allow 6379/tcp       # Redis

# Allow ZMQ communication between machines
sudo ufw allow 5555/tcp

# Enable firewall
sudo ufw --force enable

echo "Firewall configuration completed"
```

## Scaling and Performance

### Performance Monitoring

```python
# scripts/performance_monitor.py
import psutil
import time
from prometheus_client import Gauge

# Performance metrics
cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('system_memory_usage_percent', 'Memory usage percentage')
disk_usage = Gauge('system_disk_usage_percent', 'Disk usage percentage')

def monitor_system_performance():
    while True:
        # Update CPU usage
        cpu_usage.set(psutil.cpu_percent(interval=1))
        
        # Update memory usage
        memory = psutil.virtual_memory()
        memory_usage.set(memory.percent)
        
        # Update disk usage
        disk = psutil.disk_usage('/')
        disk_usage.set(disk.used / disk.total * 100)
        
        time.sleep(30)

if __name__ == "__main__":
    monitor_system_performance()
```

## Troubleshooting

### Common Issues

#### 1. Agent Communication Issues

**Symptoms**: Agents cannot communicate with each other

**Solutions**:
- Check network connectivity between machines
- Verify firewall rules allow required ports
- Validate ZMQ socket configurations
- Check DNS resolution for machine hostnames

#### 2. Redis Connection Issues

**Symptoms**: Backend operations fail, cache misses

**Solutions**:
- Verify Redis service is running
- Check Redis configuration and authentication
- Test Redis connectivity with redis-cli
- Monitor Redis memory usage and performance

#### 3. High Memory Usage

**Symptoms**: System becomes slow, out of memory errors

**Solutions**:
- Monitor memory usage per agent
- Implement memory limits for agents
- Optimize data structures and caching
- Add garbage collection strategies

#### 4. Performance Degradation

**Symptoms**: Slow response times, high CPU usage

**Solutions**:
- Profile agent performance
- Optimize database queries and operations
- Implement caching strategies
- Scale horizontally by adding more instances

### Diagnostic Commands

```bash
# Check system resources
htop
free -h
df -h

# Check service status
systemctl status ai-system-main
systemctl status ai-system-pc2
systemctl status redis-server

# Check logs
journalctl -u ai-system-main -f
tail -f /var/log/ai-system/agents.log

# Test connectivity
telnet pc2 5555
redis-cli ping
curl http://localhost:9090/-/healthy

# Monitor network
netstat -tulpn | grep python
ss -tulpn | grep 8080
```

---

**Next**: See [testing.md](testing.md) for testing strategies and [development.md](development.md) for development workflow.
