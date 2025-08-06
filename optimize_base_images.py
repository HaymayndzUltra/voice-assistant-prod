#!/usr/bin/env python3
"""
Base Image Optimization Script
Migrates CPU services to python:3.10-slim-bullseye and optimizes Dockerfile patterns.
"""

import os
import pathlib
import re
from typing import List, Dict

def get_cpu_services() -> List[str]:
    """Get list of CPU-only services (non-GPU)"""
    # Based on optimization report - all services except GPU ones
    gpu_services = [
        "pc2_dream_world_agent",
        "pc2_dreaming_mode_agent", 
        "pc2_vision_processing_agent",
        "tiny_llama_service_enhanced"
    ]
    
    docker_dir = pathlib.Path("docker")
    all_services = []
    
    for service_dir in docker_dir.iterdir():
        if service_dir.is_dir() and service_dir.name not in gpu_services:
            all_services.append(service_dir.name)
    
    return all_services

def optimize_dockerfile(dockerfile_path: pathlib.Path, service_name: str) -> bool:
    """Optimize a Dockerfile with slim base image and best practices"""
    if not dockerfile_path.exists():
        print(f"⚠️  {service_name}: No Dockerfile found")
        return False
        
    try:
        with open(dockerfile_path, 'r') as f:
            content = f.read()
            
        original_content = content
        
        # 1. Replace base image with slim version
        content = re.sub(
            r'FROM python:[0-9.]+(?:-[a-z]+)?',
            'FROM python:3.10-slim-bullseye',
            content
        )
        
        # 2. Optimize pip install commands
        # Add --no-cache-dir to pip install
        content = re.sub(
            r'pip install(?!\s+--no-cache-dir)',
            'pip install --no-cache-dir',
            content
        )
        
        # 3. Add pip disable version check
        content = re.sub(
            r'pip install --no-cache-dir',
            'pip install --disable-pip-version-check --no-cache-dir',
            content
        )
        
        # 4. Optimize apt-get commands
        # Ensure proper cleanup
        apt_pattern = r'(RUN\s+apt-get\s+update\s+&&\s+apt-get\s+install[^&]*?)(?:\s+&&\s+rm\s+-rf\s+/var/lib/apt/lists/\*)?'
        apt_replacement = r'\1 \\\n    && rm -rf /var/lib/apt/lists/*'
        content = re.sub(apt_pattern, apt_replacement, content, flags=re.MULTILINE)
        
        # 5. Add optimization comments
        if 'FROM python:3.10-slim-bullseye' in content and '# Optimized' not in content:
            content = '# Optimized Dockerfile - slim base image with pip cache disabled\n' + content
            
        # 6. Ensure HEALTHCHECK exists (if not already added by previous script)
        if 'HEALTHCHECK' not in content:
            # Find insertion point before CMD/ENTRYPOINT
            lines = content.split('\n')
            insert_index = len(lines)
            
            for i, line in enumerate(lines):
                if line.strip().startswith('CMD') or line.strip().startswith('ENTRYPOINT'):
                    insert_index = i
                    break
                    
            healthcheck = [
                '',
                '# Health check for container monitoring',
                'HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\',
                '  CMD curl -f http://localhost:8000/health || exit 1',
                ''
            ]
            
            lines[insert_index:insert_index] = healthcheck
            content = '\n'.join(lines)
        
        # Only write if content changed
        if content != original_content:
            with open(dockerfile_path, 'w') as f:
                f.write(content)
            print(f"✅ {service_name}: Optimized Dockerfile")
            return True
        else:
            print(f"✅ {service_name}: Already optimized")
            return True
            
    except Exception as e:
        print(f"❌ {service_name}: Error optimizing Dockerfile: {e}")
        return False

def add_dockerignore(service_dir: pathlib.Path, service_name: str) -> bool:
    """Add optimized .dockerignore file if missing"""
    dockerignore_path = service_dir / ".dockerignore"
    
    if dockerignore_path.exists():
        return True
        
    dockerignore_content = """# Python cache and artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# IDE and editor files
.vscode/
.idea/
*.swp
*.swo
*~

# Git and version control
.git/
.gitignore

# Documentation and non-essential files
README.md
*.md
docs/
tests/

# Log files
*.log
logs/

# Temporary files
tmp/
temp/
.tmp/

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
"""
    
    try:
        with open(dockerignore_path, 'w') as f:
            f.write(dockerignore_content)
        print(f"✅ {service_name}: Added .dockerignore")
        return True
    except Exception as e:
        print(f"❌ {service_name}: Error creating .dockerignore: {e}")
        return False

def optimize_base_images():
    """Main function to optimize base images across CPU services"""
    print("🔧 Docker Base Image Optimization")
    print("=" * 50)
    
    cpu_services = get_cpu_services()
    print(f"📊 Found {len(cpu_services)} CPU services to optimize")
    
    docker_dir = pathlib.Path("docker")
    optimized_count = 0
    
    for service_name in cpu_services:
        service_dir = docker_dir / service_name
        
        if not service_dir.exists():
            print(f"❌ {service_name}: Service directory not found")
            continue
            
        print(f"\n🔍 Processing {service_name}...")
        
        # Optimize Dockerfile
        dockerfile_path = service_dir / "Dockerfile"
        dockerfile_success = optimize_dockerfile(dockerfile_path, service_name)
        
        # Add .dockerignore
        dockerignore_success = add_dockerignore(service_dir, service_name)
        
        if dockerfile_success:
            optimized_count += 1
    
    print(f"\n✅ Base Image Optimization Complete")
    print(f"📊 Optimized: {optimized_count}/{len(cpu_services)} services")
    
    # Summary of optimizations
    print(f"\n🎯 Optimizations Applied:")
    print(f"   • Base image: python:3.10-slim-bullseye")
    print(f"   • Pip options: --disable-pip-version-check --no-cache-dir")
    print(f"   • Apt cleanup: rm -rf /var/lib/apt/lists/*")
    print(f"   • Added .dockerignore for smaller build contexts")
    print(f"   • Health checks for container monitoring")
    
if __name__ == "__main__":
    optimize_base_images()
