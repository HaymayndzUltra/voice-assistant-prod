# 🚀 MemoryHub Deployment Guide

**Production deployment guide for MemoryHub Unified v2.0.0**

## 🎯 Overview

This guide covers deploying MemoryHub Unified in production environments, including infrastructure setup, containerization, orchestration, and monitoring.

---

## 📋 Pre-Deployment Checklist

### Infrastructure Requirements

- **CPU**: 2+ cores (4+ recommended for production)
- **Memory**: 1GB minimum (2GB+ recommended)
- **Storage**: 10GB+ for data, logs, and models
- **Network**: HTTP/HTTPS access on port 7010
- **Redis**: Version 6+ with persistence enabled
- **Python**: Version 3.8+ with pip

### Security Requirements

- **JWT Secret**: 256-bit secure random key
- **Redis Password**: Strong authentication if exposed
- **TLS/SSL**: HTTPS in production
- **Firewall**: Restrict access to necessary ports
- **Backups**: Regular data backups configured

### Dependencies

```bash
# System dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip redis-server curl

# Python dependencies (handled by requirements.txt)
pip install -r requirements.txt
```

---

## 🐳 Docker Deployment

### Single Container

**Dockerfile**:
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model to reduce startup time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data logs

# Set permissions
RUN useradd -m -u 1000 memoryhub && chown -R memoryhub:memoryhub /app
USER memoryhub

# Expose port
EXPOSE 7010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7010/health || exit 1

# Run application
CMD ["uvicorn", "memory_hub.memory_hub:app", "--host", "0.0.0.0", "--port", "7010"]
```

**Build and Run**:
```bash
# Build image
docker build -t memoryhub:v2.0.0 .

# Run container
docker run -d \
  --name memoryhub \
  -p 7010:7010 \
  -e REDIS_HOST=host.docker.internal \
  -e JWT_SECRET=your-production-secret \
  -v memoryhub_data:/app/data \
  -v memoryhub_logs:/app/logs \
  memoryhub:v2.0.0
```

### Docker Compose (Recommended)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  memoryhub:
    build: .
    container_name: memoryhub
    restart: unless-stopped
    ports:
      - "7010:7010"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - JWT_SECRET=${JWT_SECRET}
      - SQLITE_PATH=/app/data/memory_hub.db
      - EMBEDDING_INDEX_PATH=/app/data/embeddings.index
      - LOG_LEVEL=INFO
      - REQUIRE_AUTH=true
    volumes:
      - memoryhub_data:/app/data
      - memoryhub_logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7010/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  redis:
    image: redis:7-alpine
    container_name: memoryhub_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --appendfsync everysec
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: memoryhub_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - memoryhub

volumes:
  memoryhub_data:
    driver: local
  memoryhub_logs:
    driver: local
  redis_data:
    driver: local
```

**Environment File (.env)**:
```bash
# Create .env file for docker-compose
REDIS_PASSWORD=your-secure-redis-password
JWT_SECRET=your-256-bit-jwt-secret-key
```

**Deploy with Docker Compose**:
```bash
# Create environment file
echo "REDIS_PASSWORD=$(openssl rand -hex 32)" > .env
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env

# Deploy stack
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs memoryhub

# Verify deployment
curl http://localhost:7010/health
```

---

## ☸️ Kubernetes Deployment

### Namespace and ConfigMap

**namespace.yaml**:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: memoryhub
```

**configmap.yaml**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: memoryhub-config
  namespace: memoryhub
data:
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  SQLITE_PATH: "/app/data/memory_hub.db"
  EMBEDDING_MODEL: "all-MiniLM-L6-v2"
  LOG_LEVEL: "INFO"
  REQUIRE_AUTH: "true"
  MONITOR_ENABLED: "true"
```

### Secrets

**secrets.yaml**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: memoryhub-secrets
  namespace: memoryhub
type: Opaque
data:
  jwt-secret: <base64-encoded-jwt-secret>
  redis-password: <base64-encoded-redis-password>
```

```bash
# Create secrets
kubectl create secret generic memoryhub-secrets \
  --from-literal=jwt-secret=$(openssl rand -hex 32) \
  --from-literal=redis-password=$(openssl rand -hex 32) \
  -n memoryhub
```

### Redis Deployment

**redis-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: memoryhub
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: memoryhub-secrets
              key: redis-password
        command:
        - redis-server
        - --requirepass
        - $(REDIS_PASSWORD)
        - --appendonly
        - "yes"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
        livenessProbe:
          exec:
            command:
            - redis-cli
            - -a
            - $(REDIS_PASSWORD)
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - -a
            - $(REDIS_PASSWORD)
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: memoryhub
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: memoryhub
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

### MemoryHub Deployment

**memoryhub-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memoryhub
  namespace: memoryhub
  labels:
    app: memoryhub
spec:
  replicas: 3
  selector:
    matchLabels:
      app: memoryhub
  template:
    metadata:
      labels:
        app: memoryhub
    spec:
      containers:
      - name: memoryhub
        image: memoryhub:v2.0.0
        ports:
        - containerPort: 7010
        env:
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: memoryhub-secrets
              key: jwt-secret
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: memoryhub-secrets
              key: redis-password
        envFrom:
        - configMapRef:
            name: memoryhub-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: memoryhub-data
          mountPath: /app/data
        - name: memoryhub-logs
          mountPath: /app/logs
        livenessProbe:
          httpGet:
            path: /health
            port: 7010
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 7010
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health
            port: 7010
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 10
      volumes:
      - name: memoryhub-data
        persistentVolumeClaim:
          claimName: memoryhub-data-pvc
      - name: memoryhub-logs
        persistentVolumeClaim:
          claimName: memoryhub-logs-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: memoryhub-service
  namespace: memoryhub
spec:
  selector:
    app: memoryhub
  ports:
  - port: 7010
    targetPort: 7010
    protocol: TCP
  type: ClusterIP

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: memoryhub-data-pvc
  namespace: memoryhub
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: memoryhub-logs-pvc
  namespace: memoryhub
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
```

### Ingress (Optional)

**ingress.yaml**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: memoryhub-ingress
  namespace: memoryhub
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - memoryhub.yourdomain.com
    secretName: memoryhub-tls
  rules:
  - host: memoryhub.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: memoryhub-service
            port:
              number: 7010
```

**Deploy to Kubernetes**:
```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f memoryhub-deployment.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n memoryhub
kubectl get services -n memoryhub
kubectl logs -f deployment/memoryhub -n memoryhub

# Verify deployment
kubectl port-forward svc/memoryhub-service 7010:7010 -n memoryhub
curl http://localhost:7010/health
```

---

## 🔧 Traditional Server Deployment

### System Service Setup

**systemd Service (/etc/systemd/system/memoryhub.service)**:
```ini
[Unit]
Description=MemoryHub Unified Service
After=network.target redis.service
Requires=redis.service

[Service]
Type=exec
User=memoryhub
Group=memoryhub
WorkingDirectory=/opt/memoryhub
Environment=PATH=/opt/memoryhub/venv/bin
EnvironmentFile=/opt/memoryhub/.env
ExecStart=/opt/memoryhub/venv/bin/uvicorn memory_hub.memory_hub:app --host 0.0.0.0 --port 7010 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=memoryhub

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/memoryhub/data /opt/memoryhub/logs

[Install]
WantedBy=multi-user.target
```

**Installation Script**:
```bash
#!/bin/bash
# install.sh - MemoryHub installation script

set -e

# Configuration
INSTALL_DIR="/opt/memoryhub"
SERVICE_USER="memoryhub"
PYTHON_VERSION="3.9"

# Create user
sudo useradd -r -s /bin/false -d $INSTALL_DIR $SERVICE_USER || true

# Create directories
sudo mkdir -p $INSTALL_DIR/{data,logs}
sudo chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Install Python and dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv redis-server

# Create virtual environment
sudo -u $SERVICE_USER python3 -m venv $INSTALL_DIR/venv
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install -r requirements.txt

# Copy application files
sudo cp -r . $INSTALL_DIR/
sudo chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Create environment file
sudo tee $INSTALL_DIR/.env > /dev/null <<EOF
REDIS_HOST=localhost
REDIS_PORT=6379
SQLITE_PATH=$INSTALL_DIR/data/memory_hub.db
EMBEDDING_INDEX_PATH=$INSTALL_DIR/data/embeddings.index
JWT_SECRET=$(openssl rand -hex 32)
LOG_LEVEL=INFO
REQUIRE_AUTH=true
EOF

sudo chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/.env
sudo chmod 600 $INSTALL_DIR/.env

# Install and start service
sudo cp deployment/memoryhub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable memoryhub
sudo systemctl start memoryhub

echo "MemoryHub installed and started successfully!"
echo "Check status: sudo systemctl status memoryhub"
echo "View logs: sudo journalctl -u memoryhub -f"
```

### Nginx Reverse Proxy

**nginx.conf**:
```nginx
upstream memoryhub {
    server 127.0.0.1:7010;
    keepalive 32;
}

server {
    listen 80;
    server_name memoryhub.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name memoryhub.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/ssl/certs/memoryhub.crt;
    ssl_certificate_key /etc/ssl/private/memoryhub.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy settings
    location / {
        proxy_pass http://memoryhub;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Request size limits
        client_max_body_size 50M;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://memoryhub;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/memoryhub/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 📊 Monitoring and Observability

### Health Monitoring

**Health Check Script (healthcheck.sh)**:
```bash
#!/bin/bash
# Health check script for monitoring systems

MEMORYHUB_URL="http://localhost:7010"
TIMEOUT=10

# Check MemoryHub health
response=$(curl -s -w "%{http_code}" -o /tmp/health_response --connect-timeout $TIMEOUT "$MEMORYHUB_URL/health")
http_code="${response: -3}"

if [ "$http_code" = "200" ]; then
    echo "MemoryHub: HEALTHY"
    
    # Check component status
    status=$(jq -r '.status' /tmp/health_response)
    storage=$(jq -r '.unified_storage' /tmp/health_response)
    embedding=$(jq -r '.semantic_search' /tmp/health_response)
    monitor=$(jq -r '.background_monitor' /tmp/health_response)
    
    echo "Overall Status: $status"
    echo "Storage: $storage"
    echo "Embedding: $embedding"
    echo "Monitor: $monitor"
    
    exit 0
else
    echo "MemoryHub: UNHEALTHY (HTTP $http_code)"
    exit 1
fi
```

### Prometheus Metrics

**metrics.py** (add to MemoryHub):
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Metrics
REQUEST_COUNT = Counter('memoryhub_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('memoryhub_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('memoryhub_active_connections', 'Active connections')
STORAGE_OPERATIONS = Counter('memoryhub_storage_operations_total', 'Storage operations', ['operation', 'namespace'])
EMBEDDING_OPERATIONS = Counter('memoryhub_embedding_operations_total', 'Embedding operations', ['operation'])

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(generate_latest())
```

### Log Aggregation

**logging.yaml** (for structured logging):
```yaml
version: 1
disable_existing_loggers: false

formatters:
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s", "component": "memoryhub"}'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/memory_hub.log
    maxBytes: 100MB
    backupCount: 5

loggers:
  memory_hub:
    level: DEBUG
    handlers: [console, file]
    propagate: false
  
  uvicorn:
    level: INFO
    handlers: [console]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

---

## 🔐 Security Hardening

### TLS/SSL Configuration

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -keyout memoryhub.key -out memoryhub.crt -days 365 -nodes

# Let's Encrypt certificate (production)
certbot --nginx -d memoryhub.yourdomain.com
```

### Firewall Rules

```bash
# UFW firewall rules
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# Restrict Redis access (if external)
sudo ufw allow from 10.0.0.0/8 to any port 6379
```

### Environment Hardening

```bash
# Secure file permissions
chmod 600 .env
chmod 700 data/
chmod 755 logs/

# SELinux policies (if applicable)
setsebool -P httpd_can_network_connect 1
semanage port -a -t http_port_t -p tcp 7010
```

---

## 📈 Performance Tuning

### System Optimization

```bash
# Increase file descriptor limits
echo "memoryhub soft nofile 65536" >> /etc/security/limits.conf
echo "memoryhub hard nofile 65536" >> /etc/security/limits.conf

# Optimize Redis
echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
sysctl -p
```

### Application Tuning

```bash
# Environment variables for performance
export UVICORN_WORKERS=4
export UVICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker
export UVICORN_BACKLOG=2048
export UVICORN_MAX_REQUESTS=1000
export UVICORN_MAX_REQUESTS_JITTER=100
```

---

## 🔄 Backup and Recovery

### Backup Script

```bash
#!/bin/bash
# backup.sh - MemoryHub backup script

BACKUP_DIR="/backup/memoryhub"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

# Backup SQLite database
cp /opt/memoryhub/data/memory_hub.db "$BACKUP_DIR/memory_hub_$DATE.db"

# Backup Redis data
redis-cli --rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Backup FAISS index and metadata
cp /opt/memoryhub/data/embeddings.index "$BACKUP_DIR/embeddings_$DATE.index"
cp /opt/memoryhub/data/embeddings_metadata.json "$BACKUP_DIR/embeddings_metadata_$DATE.json"

# Backup configuration
cp /opt/memoryhub/.env "$BACKUP_DIR/config_$DATE.env"

# Create tarball
tar -czf "$BACKUP_DIR/memoryhub_backup_$DATE.tar.gz" -C "$BACKUP_DIR" \
    memory_hub_$DATE.db \
    redis_$DATE.rdb \
    embeddings_$DATE.index \
    embeddings_metadata_$DATE.json \
    config_$DATE.env

# Clean up individual files
rm "$BACKUP_DIR"/*.{db,rdb,index,json,env}

# Remove old backups
find "$BACKUP_DIR" -name "memoryhub_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: memoryhub_backup_$DATE.tar.gz"
```

### Recovery Script

```bash
#!/bin/bash
# restore.sh - MemoryHub restore script

BACKUP_FILE="$1"
RESTORE_DIR="/opt/memoryhub"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop service
sudo systemctl stop memoryhub

# Extract backup
tar -xzf "$BACKUP_FILE" -C /tmp/

# Restore files
cp /tmp/memory_hub_*.db "$RESTORE_DIR/data/memory_hub.db"
cp /tmp/embeddings_*.index "$RESTORE_DIR/data/embeddings.index"
cp /tmp/embeddings_metadata_*.json "$RESTORE_DIR/data/embeddings_metadata.json"

# Restore Redis (requires manual intervention)
echo "Restore Redis data manually:"
echo "redis-cli --rdb /tmp/redis_*.rdb"

# Set permissions
chown -R memoryhub:memoryhub "$RESTORE_DIR/data"

# Start service
sudo systemctl start memoryhub

echo "Restore completed. Check service status with: systemctl status memoryhub"
```

---

## 🧪 Deployment Validation

### Deployment Test Script

```bash
#!/bin/bash
# validate_deployment.sh - Validate MemoryHub deployment

BASE_URL="http://localhost:7010"
FAILED=0

echo "🧪 Validating MemoryHub deployment..."

# Test 1: Health check
echo "Testing health endpoint..."
if curl -s "$BASE_URL/health" | grep -q "healthy"; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    FAILED=$((FAILED + 1))
fi

# Test 2: Authentication
echo "Testing authentication..."
TOKEN=$(curl -s -X POST "$BASE_URL/auth/token" \
    -H "Content-Type: application/json" \
    -d '{"username": "test", "password": "test"}' | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "✅ Authentication passed"
else
    echo "❌ Authentication failed"
    FAILED=$((FAILED + 1))
fi

# Test 3: Key-value storage
echo "Testing key-value storage..."
STORE_RESULT=$(curl -s -X POST "$BASE_URL/kv" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"key": "test_key", "value": "test_value", "namespace": "test"}')

if echo "$STORE_RESULT" | grep -q "success"; then
    echo "✅ Key-value storage passed"
else
    echo "❌ Key-value storage failed"
    FAILED=$((FAILED + 1))
fi

# Test 4: Document storage
echo "Testing document storage..."
DOC_RESULT=$(curl -s -X POST "$BASE_URL/doc" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"doc_id": "test_doc", "title": "Test", "content": "Test content", "namespace": "test"}')

if echo "$DOC_RESULT" | grep -q "success"; then
    echo "✅ Document storage passed"
else
    echo "❌ Document storage failed"
    FAILED=$((FAILED + 1))
fi

# Test 5: Semantic search
echo "Testing semantic search..."
SEARCH_RESULT=$(curl -s -X POST "$BASE_URL/embedding/search" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"query": "test content", "namespace": "test", "limit": 1}')

if echo "$SEARCH_RESULT" | grep -q "results"; then
    echo "✅ Semantic search passed"
else
    echo "❌ Semantic search failed"
    FAILED=$((FAILED + 1))
fi

# Summary
echo
if [ $FAILED -eq 0 ]; then
    echo "🎉 All tests passed! MemoryHub deployment is successful."
    exit 0
else
    echo "⚠️  $FAILED test(s) failed. Please check the deployment."
    exit 1
fi
```

---

**MemoryHub Deployment Guide v2.0.0** - Complete production deployment reference ✅🚀 
 