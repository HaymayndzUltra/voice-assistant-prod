# Docker Setup for Background Agent Testing

## Prerequisites for Background Agent

### 1. Docker Engine Access
```bash
# Check Docker daemon status
sudo systemctl status docker

# Start Docker if not running
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Add current user to docker group (to avoid sudo)
sudo usermod -aG docker $USER
newgrp docker  # Apply group changes immediately
```

### 2. Docker Compose Installation
```bash
# Install Docker Compose V2
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify installation
docker compose version
```

### 3. System Resources Check
```bash
# Check available disk space (Docker images can be large)
df -h

# Check memory (for building 77 containers)
free -h

# Check Docker system info
docker system df
docker system info
```

## Docker Testing Strategy for Background Agent

### 1. Container Build Testing
```python
import subprocess
import json
from pathlib import Path

def test_container_build(container_path: Path) -> dict:
    """Test if a container builds successfully"""
    result = {
        'container': container_path.name,
        'build_success': False,
        'build_time': 0,
        'image_size': 0,
        'error_message': None
    }
    
    try:
        # Build the container
        cmd = ['docker', 'build', '-t', f'test-{container_path.name}', str(container_path)]
        start_time = time.time()
        
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        
        result['build_time'] = time.time() - start_time
        
        if process.returncode == 0:
            result['build_success'] = True
            
            # Get image size
            size_cmd = ['docker', 'images', f'test-{container_path.name}', '--format', '{{.Size}}']
            size_result = subprocess.run(size_cmd, capture_output=True, text=True)
            result['image_size'] = size_result.stdout.strip()
        else:
            result['error_message'] = process.stderr
            
    except subprocess.TimeoutExpired:
        result['error_message'] = "Build timeout (5 minutes)"
    except Exception as e:
        result['error_message'] = str(e)
    
    return result
```

### 2. Docker Compose Testing
```python
def test_docker_compose(compose_file: Path) -> dict:
    """Test docker-compose file validity"""
    result = {
        'compose_file': str(compose_file),
        'valid': False,
        'services': [],
        'error_message': None
    }
    
    try:
        # Validate compose file
        cmd = ['docker', 'compose', '-f', str(compose_file), 'config']
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            result['valid'] = True
            # Parse services from output
            import yaml
            config = yaml.safe_load(process.stdout)
            result['services'] = list(config.get('services', {}).keys())
        else:
            result['error_message'] = process.stderr
            
    except Exception as e:
        result['error_message'] = str(e)
    
    return result
```

### 3. Container Runtime Testing
```python
def test_container_runtime(image_name: str) -> dict:
    """Test if container runs and responds to health checks"""
    result = {
        'image': image_name,
        'starts_successfully': False,
        'health_check_passes': False,
        'startup_time': 0,
        'error_message': None
    }
    
    try:
        # Start container
        start_time = time.time()
        cmd = ['docker', 'run', '-d', '--name', f'test-run-{image_name}', image_name]
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            container_id = process.stdout.strip()
            result['starts_successfully'] = True
            result['startup_time'] = time.time() - start_time
            
            # Wait for container to be ready
            time.sleep(5)
            
            # Check if container is still running
            status_cmd = ['docker', 'inspect', container_id, '--format', '{{.State.Status}}']
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            
            if status_result.stdout.strip() == 'running':
                result['health_check_passes'] = True
            
            # Cleanup
            subprocess.run(['docker', 'stop', container_id], capture_output=True)
            subprocess.run(['docker', 'rm', container_id], capture_output=True)
        else:
            result['error_message'] = process.stderr
            
    except Exception as e:
        result['error_message'] = str(e)
    
    return result
```

## Resource Management for 77 Containers

### 1. Disk Space Management
```bash
# Before testing - check space
docker system df

# Clean up unused resources
docker system prune -f

# Remove unused images
docker image prune -a -f

# Clean up build cache
docker builder prune -f
```

### 2. Memory Management for Builds
```python
def build_containers_in_batches(container_paths, batch_size=5):
    """Build containers in batches to manage memory"""
    results = []
    
    for i in range(0, len(container_paths), batch_size):
        batch = container_paths[i:i+batch_size]
        
        print(f"Building batch {i//batch_size + 1}: {[p.name for p in batch]}")
        
        # Build batch
        batch_results = []
        for container_path in batch:
            result = test_container_build(container_path)
            batch_results.append(result)
        
        results.extend(batch_results)
        
        # Clean up after batch
        subprocess.run(['docker', 'system', 'prune', '-f'], capture_output=True)
        
        # Brief pause between batches
        time.sleep(10)
    
    return results
```

### 3. Parallel Testing Strategy
```python
import concurrent.futures
import threading

def test_all_containers_parallel(container_paths, max_workers=3):
    """Test containers in parallel with resource limits"""
    
    # Use ThreadPoolExecutor with limited workers to prevent resource exhaustion
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all build tasks
        future_to_container = {
            executor.submit(test_container_build, path): path 
            for path in container_paths
        }
        
        results = []
        for future in concurrent.futures.as_completed(future_to_container):
            container_path = future_to_container[future]
            try:
                result = future.result()
                results.append(result)
                print(f"✅ {container_path.name}: {result['build_success']}")
            except Exception as e:
                print(f"❌ {container_path.name}: {e}")
                results.append({
                    'container': container_path.name,
                    'build_success': False,
                    'error_message': str(e)
                })
        
        return results
```

## Environment Setup Script for Background Agent

```bash
#!/bin/bash
# setup_docker_for_background_agent.sh

echo "🐳 Setting up Docker for Background Agent Testing"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Create testing workspace
mkdir -p /tmp/docker-testing
cd /tmp/docker-testing

# Pre-pull common base images to speed up builds
echo "📥 Pre-pulling common base images..."
docker pull python:3.9-slim
docker pull python:3.10-slim
docker pull nvidia/cuda:11.8-devel-ubuntu20.04

# Clean up any existing test containers/images
echo "🧹 Cleaning up existing test resources..."
docker container prune -f
docker image prune -f
docker system prune -f

echo "✅ Docker setup complete for background agent testing"
echo "📊 System status:"
docker system df
echo "💾 Available disk space:"
df -h /var/lib/docker
```

## Testing Commands for Background Agent

```python
# Key Docker commands the background agent will use:

# 1. Build testing
subprocess.run(['docker', 'build', '-t', 'test-agent', '/path/to/agent'])

# 2. Compose validation  
subprocess.run(['docker', 'compose', '-f', 'docker-compose.yml', 'config'])

# 3. Runtime testing
subprocess.run(['docker', 'run', '--rm', 'test-agent', 'python', '--version'])

# 4. Resource monitoring
subprocess.run(['docker', 'stats', '--no-stream'])

# 5. Cleanup
subprocess.run(['docker', 'system', 'prune', '-f'])
```