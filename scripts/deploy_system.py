#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Complete AI System Deployment Script
Deploys the entire system with correct IP addresses:
MainPC: 192.168.100.16 (RTX 4090)  
PC2: 192.168.100.17 (RTX 3060)
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

class SystemDeployer:
    def __init__(self):
        self.mainpc_ip = get_service_ip("mainpc")
        self.pc2_ip = get_service_ip("pc2")
        self.project_root = Path(__file__).parent.parent
        
    def setup_environment(self, machine_type: str):
        """Setup environment variables for deployment"""
        env_file = self.project_root / "docker" / ".env"
        
        env_content = f"""# AI System Deployment Environment
# Generated automatically by deploy_system.py

# Machine Configuration
MACHINE_TYPE={machine_type}
MAINPC_HOST={self.mainpc_ip}
PC2_HOST={self.pc2_ip}

# Core Settings
PYTHONPATH=/app
LOG_LEVEL=INFO
DEBUG_MODE=false

# Network Configuration
REDIS_HOST={self.mainpc_ip}
NATS_HOST={self.mainpc_ip}
SERVICE_REGISTRY_HOST={self.mainpc_ip}

# Security (Non-root containers)
CONTAINER_USER=ai
CONTAINER_UID=1000

# GPU Configuration
CUDA_VISIBLE_DEVICES=0
NVIDIA_VISIBLE_DEVICES=all

# Observability
ENABLE_METRICS=true
ENABLE_TRACING=true
MESH_DISABLED=true

# Cross-machine sync
SYNC_ENABLED=true
SYNC_INTERVAL=300
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Created environment file: {env_file}")
    
    def deploy_mainpc(self):
        """Deploy MainPC (RTX 4090) services"""
        print(f"🚀 Deploying MainPC services on {self.mainpc_ip}...")
        
        self.setup_environment("mainpc")
        
        os.chdir(self.project_root)
        
        # Build and deploy MainPC containers
        cmd = [
            "docker", "compose", 
            "-f", "docker/docker-compose.mainpc.yml",
            "up", "-d", "--build"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("✅ MainPC deployment successful!")
            return True
        else:
            print("❌ MainPC deployment failed!")
            return False
    
    def deploy_pc2(self):
        """Deploy PC2 (RTX 3060) services"""
        print(f"🚀 Deploying PC2 services on {self.pc2_ip}...")
        
        self.setup_environment("pc2")
        
        os.chdir(self.project_root)
        
        # Build and deploy PC2 containers
        cmd = [
            "docker", "compose",
            "-f", "docker/docker-compose.pc2.yml", 
            "up", "-d", "--build"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("✅ PC2 deployment successful!")
            return True
        else:
            print("❌ PC2 deployment failed!")
            return False
    
    def validate_deployment(self):
        """Validate the deployment"""
        print("🔍 Validating deployment...")
        
        validation_script = self.project_root / "scripts" / "validate_deployment.py"
        
        cmd = [
            "python", str(validation_script),
            "--mainpc-host", self.mainpc_ip,
            "--pc2-host", self.pc2_ip,
            "--machine", "all"
        ]
        
        result = subprocess.run(cmd)
        return result.returncode == 0
    
    def show_status(self):
        """Show deployment status"""
        print(f"""
🎯 AI SYSTEM DEPLOYMENT STATUS
{'='*50}

MainPC (RTX 4090): {self.mainpc_ip}
PC2 (RTX 3060): {self.pc2_ip}

🔧 QUICK COMMANDS:

# Check container status:
docker ps

# View logs:
docker compose -f docker/docker-compose.mainpc.yml logs -f
docker compose -f docker/docker-compose.pc2.yml logs -f

# Stop services:
docker compose -f docker/docker-compose.mainpc.yml down
docker compose -f docker/docker-compose.pc2.yml down

# Validate deployment:
python scripts/validate_deployment.py --all

# Monitor cross-machine sync:
docker logs -f ai_system_sync-service_1

🎉 DEPLOYMENT COMPLETE!
""")

def main():
    parser = argparse.ArgumentParser(description="Deploy AI System")
    parser.add_argument("--machine", choices=["mainpc", "pc2", "all"], 
                       default="all", help="Which machine to deploy")
    parser.add_argument("--validate", action="store_true", 
                       help="Run validation after deployment")
    parser.add_argument("--status-only", action="store_true",
                       help="Show status information only")
    
    args = parser.parse_args()
    
    deployer = SystemDeployer()
    
    if args.status_only:
        deployer.show_status()
        return
    
    success = True
    
    if args.machine in ["all", "mainpc"]:
        success &= deployer.deploy_mainpc()
    
    if args.machine in ["all", "pc2"]:
        success &= deployer.deploy_pc2()
    
    if success and args.validate:
        success &= deployer.validate_deployment()
    
    if success:
        deployer.show_status()
        print("🎉 DEPLOYMENT SUCCESSFUL!")
    else:
        print("❌ DEPLOYMENT FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main() 