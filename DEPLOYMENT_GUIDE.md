# 🚀 Docker Deployment Guide

## 📋 **Prerequisites**

1. **Docker & Docker Compose** installed
2. **Git** repository cloned
3. **GitHub Personal Access Token** with `write:packages` scope
4. **OpenAI API Key** (or other LLM provider key)

## 🔐 **Environment Setup**

### **Option 1: Environment Variables**
```bash
export GHCR_USER="haymayndzultra"
export GHCR_TOKEN="ghp_your_github_token_here"
export OPENAI_KEY="sk-your_openai_key_here"
```

### **Option 2: .env File**
Create a `.env` file in the project root:
```bash
# GitHub Container Registry
GHCR_USER=haymayndzultra
GHCR_TOKEN=ghp_your_github_token_here

# OpenAI API
OPENAI_KEY=sk-your_openai_key_here

# Optional: AWS Bedrock
# BEDROCK_KEY=your_bedrock_key_here
```

Then source it:
```bash
source .env
```

## 🏗️ **Deployment Steps**

### **1. Make Script Executable**
```bash
chmod +x deploy_improved.sh
```

### **2. Run Deployment**
```bash
./deploy_improved.sh
```

## 📊 **What the Script Does**

1. **Validates Configuration** - Checks for required environment variables
2. **Docker Login** - Authenticates with GitHub Container Registry
3. **Builds Images** - Creates Docker images for:
   - `remote-api-adapter` - OpenAI/Bedrock API wrapper
   - `tiny-llama` - Local GPU model
   - `observability-hub` - Monitoring infrastructure
4. **Pushes Images** - Uploads to GHCR with Git SHA tags
5. **Creates Secrets** - Sets up API keys as Docker secrets
6. **Updates Compose Files** - Patches image tags in docker-compose files
7. **Starts Stack** - Brings up the complete system
8. **Health Checks** - Verifies all services are running

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. "GHCR_TOKEN not set"**
```bash
# Solution: Set the environment variable
export GHCR_TOKEN="ghp_your_token_here"
```

#### **2. "Docker login failed"**
```bash
# Check your token has the right permissions
# Token needs: write:packages, read:packages
```

#### **3. "tiny_llama_context directory not found"**
```bash
# The directory doesn't exist - you need to create it or modify the script
# to point to the correct TinyLlama build context
```

#### **4. "Failed to build remote-api-adapter"**
```bash
# Check that remote_api_adapter/Dockerfile exists
# Verify Python dependencies are correct
```

### **Manual Health Checks**

```bash
# Check container status
docker ps

# Check logs
docker compose logs remote-api-adapter
docker compose logs tiny-llama
docker compose logs observability-hub-standby

# Test health endpoints
curl http://localhost:7101/metrics  # metrics-forwarder
curl http://localhost:7102/-/healthy  # observability-hub (if running)
```

## 🏥 **Monitoring**

### **Available Endpoints**
- **Metrics Forwarder**: `http://localhost:7101/metrics`
- **Observability Hub**: `http://localhost:7102` (if standby is enabled)
- **MainPC Observability**: `http://localhost:9000` (from mainpc compose)

### **Container Groups**
Based on the memory-bank analysis, your system uses these container groups:

#### **MainPC (RTX 4090)**
- `mainpc_core_services` - Service registry, digital twin
- `mainpc_gpu_intensive` - Model management, VRAM optimization
- `mainpc_language_pipeline` - NLU, translation, response
- `mainpc_audio_speech` - STT, TTS, audio processing
- `mainpc_memory_system` - Memory management
- `mainpc_emotion_system` - Emotion detection, empathy
- `mainpc_learning_services` - Learning orchestration
- `mainpc_utility_services` - Code generation, execution
- `mainpc_perception_services` - Face recognition, identity
- `mainpc_reasoning_extras` - Reasoning, goal management

#### **PC2 (RTX 3060)** - Not in this deployment
- Memory processing, interaction core, specialized agents

## 🔧 **Customization**

### **Adding New Services**
1. Add Dockerfile for the service
2. Add build step in the script
3. Add service definition in docker-compose.hybrid.yml
4. Update image tag patching

### **Resource Limits**
Add to docker-compose.hybrid.yml:
```yaml
services:
  your-service:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          cpus: "1.0"
          memory: 2G
```

### **GPU Access**
```yaml
services:
  gpu-service:
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
```

## 🚨 **Security Notes**

1. **Never commit secrets** to version control
2. **Use Docker secrets** for sensitive data
3. **Rotate tokens regularly**
4. **Monitor container logs** for security issues
5. **Use non-root users** in containers (already implemented)

## 📈 **Performance Optimization**

### **Resource Allocation**
- **GPU-intensive**: 8-16GB VRAM, 8 CPU cores
- **CPU-intensive**: 4-8GB RAM, 4-6 CPU cores
- **Light services**: 1-2GB RAM, 1-2 CPU cores

### **Network Optimization**
- Use host networking for high-throughput services
- Implement connection pooling
- Monitor network latency between containers

## 🔄 **Rollback Strategy**

```bash
# Rollback to previous version
export GIT_SHA="previous_commit_sha"
./deploy_improved.sh

# Or use docker compose rollback
docker compose -f docker/mainpc/docker-compose.mainpc.yml \
               -f docker-compose.hybrid.yml \
               up -d --force-recreate
``` 