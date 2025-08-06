#!/usr/bin/env python3
"""
Missing Docker Files Remediation Script
Creates missing Dockerfile and docker-compose.yml for services that need them.
"""

import os
import pathlib
from typing import Dict

MISSING_FILES_SERVICES = ["scripts", "shared", "translation_services"]

def create_dockerfile(service_dir: pathlib.Path, service_name: str) -> bool:
    """Create a basic Dockerfile for a service"""
    dockerfile_path = service_dir / "Dockerfile"
    
    if dockerfile_path.exists():
        print(f"✅ {service_name}: Dockerfile already exists")
        return True
        
    # Determine if this is a Python service by looking for .py files
    has_python = any(service_dir.glob("*.py"))
    
    if service_name == "scripts":
        # Scripts directory - create a utility image
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install basic utilities
RUN apt-get update && apt-get install -y \\
    curl \\
    git \\
    jq \\
    bash \\
    && rm -rf /var/lib/apt/lists/*

# Copy scripts
COPY . .

# Make scripts executable
RUN find . -name "*.sh" -exec chmod +x {} \\;

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
  CMD echo "Scripts container healthy" || exit 1

CMD ["bash"]
"""
    
    elif service_name == "shared":
        # Shared libraries directory
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries
COPY . .

# Install any Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
  CMD echo "Shared libraries container healthy" || exit 1

# Default command for shared library container
CMD ["python", "-c", "print('Shared libraries container running')"]
"""
    
    elif service_name == "translation_services":
        # Translation services - web service
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]
"""
    
    else:
        # Generic Python service
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Expose default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]
"""
    
    try:
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        print(f"✅ {service_name}: Created Dockerfile")
        return True
    except Exception as e:
        print(f"❌ {service_name}: Error creating Dockerfile: {e}")
        return False

def create_compose_file(service_dir: pathlib.Path, service_name: str) -> bool:
    """Create a basic docker-compose.yml for a service"""
    compose_path = service_dir / "docker-compose.yml"
    
    if compose_path.exists():
        print(f"✅ {service_name}: docker-compose.yml already exists")
        return True
        
    # Service-specific configurations
    if service_name == "scripts":
        compose_content = f"""version: '3.8'

services:
  {service_name}:
    build: .
    container_name: {service_name}
    volumes:
      - .:/app
      - /var/run/docker.sock:/var/run/docker.sock
    working_dir: /app
    command: ["tail", "-f", "/dev/null"]  # Keep container running
    networks:
      - mainpc_network

networks:
  mainpc_network:
    external: true
"""
    
    elif service_name == "shared":
        compose_content = f"""version: '3.8'

services:
  {service_name}:
    build: .
    container_name: {service_name}
    volumes:
      - .:/app
    working_dir: /app
    command: ["python", "-c", "import time; time.sleep(3600)"]  # Keep running for 1 hour
    networks:
      - mainpc_network

networks:
  mainpc_network:
    external: true
"""
    
    elif service_name == "translation_services":
        compose_content = f"""version: '3.8'

services:
  {service_name}:
    build: .
    container_name: {service_name}
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
    volumes:
      - .:/app
    working_dir: /app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mainpc_network

networks:
  mainpc_network:
    external: true
"""
    
    else:
        # Generic service
        compose_content = f"""version: '3.8'

services:
  {service_name}:
    build: .
    container_name: {service_name}
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
    volumes:
      - .:/app
    working_dir: /app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - mainpc_network

networks:
  mainpc_network:
    external: true
"""
    
    try:
        with open(compose_path, 'w') as f:
            f.write(compose_content)
        print(f"✅ {service_name}: Created docker-compose.yml")
        return True
    except Exception as e:
        print(f"❌ {service_name}: Error creating docker-compose.yml: {e}")
        return False

def create_basic_requirements(service_dir: pathlib.Path, service_name: str) -> bool:
    """Create basic requirements.txt if it doesn't exist"""
    req_path = service_dir / "requirements.txt"
    
    if req_path.exists():
        return True
        
    # Basic requirements based on service type
    if service_name == "translation_services":
        requirements = """fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
pydantic==2.5.0
"""
    elif service_name == "scripts":
        requirements = """requests==2.31.0
pyyaml==6.0.1
"""
    else:
        requirements = """requests==2.31.0
"""
    
    try:
        with open(req_path, 'w') as f:
            f.write(requirements)
        print(f"✅ {service_name}: Created basic requirements.txt")
        return True
    except Exception as e:
        print(f"❌ {service_name}: Error creating requirements.txt: {e}")
        return False

def remediate_missing_files():
    """Main function to create missing Docker files"""
    print("🔧 Docker Missing Files Remediation")
    print("=" * 50)
    
    docker_dir = pathlib.Path("docker")
    fixed_count = 0
    
    for service_name in MISSING_FILES_SERVICES:
        service_dir = docker_dir / service_name
        
        if not service_dir.exists():
            print(f"❌ {service_name}: Service directory not found, creating...")
            service_dir.mkdir(parents=True, exist_ok=True)
            
        print(f"\n🔍 Processing {service_name}...")
        
        success = True
        
        # Create Dockerfile
        if create_dockerfile(service_dir, service_name):
            success = True
        else:
            success = False
            
        # Create docker-compose.yml
        if create_compose_file(service_dir, service_name):
            success = success and True
        else:
            success = False
            
        # Create basic requirements.txt
        create_basic_requirements(service_dir, service_name)
        
        if success:
            fixed_count += 1
    
    print(f"\n✅ Missing Files Remediation Complete")
    print(f"📊 Fixed: {fixed_count}/{len(MISSING_FILES_SERVICES)} services")
    
if __name__ == "__main__":
    remediate_missing_files()
