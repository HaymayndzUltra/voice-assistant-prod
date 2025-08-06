#!/usr/bin/env python3
"""
Health Check Remediation Script
Adds missing healthcheck configurations to Docker services based on audit findings.
"""

import os
import pathlib
import json
import yaml
import re
from typing import Dict, List

# Services missing health checks from audit
MISSING_HEALTHCHECK_SERVICES = [
    "code_generator", "empathy_agent", "executor",
    "human_awareness", "knowledge_base", "memory_client", 
    "mood_tracker", "predictive_health_monitor", "scripts",
    "session_memory_agent", "shared", "tone_detector",
    "translation_services", "voice_profiling", "vram_optimizer"
]

def add_healthcheck_to_compose(compose_file: pathlib.Path, service_name: str) -> bool:
    """Add healthcheck to docker-compose.yml file"""
    if not compose_file.exists():
        print(f"❌ {compose_file} does not exist")
        return False
    
    try:
        with open(compose_file, 'r') as f:
            content = f.read()
            
        # Parse YAML
        compose_data = yaml.safe_load(content)
        
        if 'services' not in compose_data:
            print(f"❌ No services found in {compose_file}")
            return False
            
        # Find the main service (usually matches directory name or is first)
        main_service = None
        for svc_name in compose_data['services']:
            if service_name in svc_name or len(compose_data['services']) == 1:
                main_service = svc_name
                break
        
        if not main_service:
            main_service = list(compose_data['services'].keys())[0]
            
        # Check if healthcheck already exists
        if 'healthcheck' in compose_data['services'][main_service]:
            print(f"✅ {service_name}: healthcheck already exists")
            return True
            
        # Determine port from compose file or use default
        port = "8000"  # default
        service_config = compose_data['services'][main_service]
        
        if 'ports' in service_config:
            # Extract port from ports mapping like "8001:8000"
            port_mapping = service_config['ports'][0]
            if isinstance(port_mapping, str) and ':' in port_mapping:
                port = port_mapping.split(':')[1]
            elif isinstance(port_mapping, int):
                port = str(port_mapping)
                
        # Add healthcheck configuration
        healthcheck_config = {
            'test': f'curl -f http://localhost:{port}/health || exit 1',
            'interval': '30s',
            'timeout': '10s',
            'retries': 3,
            'start_period': '40s'
        }
        
        compose_data['services'][main_service]['healthcheck'] = healthcheck_config
        
        # Write back to file
        with open(compose_file, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False, indent=2)
            
        print(f"✅ {service_name}: Added healthcheck on port {port}")
        return True
        
    except Exception as e:
        print(f"❌ {service_name}: Error adding healthcheck: {e}")
        return False

def add_healthcheck_to_dockerfile(dockerfile: pathlib.Path, port: str = "8000") -> bool:
    """Add HEALTHCHECK instruction to Dockerfile"""
    if not dockerfile.exists():
        print(f"❌ {dockerfile} does not exist")
        return False
        
    try:
        with open(dockerfile, 'r') as f:
            lines = f.readlines()
            
        # Check if HEALTHCHECK already exists
        for line in lines:
            if line.strip().startswith('HEALTHCHECK'):
                print(f"✅ {dockerfile.parent.name}: HEALTHCHECK already exists in Dockerfile")
                return True
                
        # Find the best place to insert HEALTHCHECK (after EXPOSE, before CMD)
        insert_index = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith('CMD') or line.strip().startswith('ENTRYPOINT'):
                insert_index = i
                break
                
        # Add HEALTHCHECK instruction
        healthcheck_line = f"HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\\n"
        healthcheck_line += f"  CMD curl -f http://localhost:{port}/health || exit 1\n\n"
        
        lines.insert(insert_index, healthcheck_line)
        
        # Write back to file
        with open(dockerfile, 'w') as f:
            f.writelines(lines)
            
        print(f"✅ {dockerfile.parent.name}: Added HEALTHCHECK to Dockerfile")
        return True
        
    except Exception as e:
        print(f"❌ {dockerfile.parent.name}: Error adding HEALTHCHECK: {e}")
        return False

def remediate_healthchecks():
    """Main function to add missing healthchecks"""
    print("🔧 Docker Health Check Remediation")
    print("=" * 50)
    
    docker_dir = pathlib.Path("docker")
    fixed_count = 0
    
    for service_name in MISSING_HEALTHCHECK_SERVICES:
        service_dir = docker_dir / service_name
        
        if not service_dir.exists():
            print(f"❌ {service_name}: Service directory not found")
            continue
            
        print(f"\n🔍 Processing {service_name}...")
        
        # Try to fix docker-compose.yml first
        compose_file = service_dir / "docker-compose.yml"
        if compose_file.exists():
            if add_healthcheck_to_compose(compose_file, service_name):
                fixed_count += 1
        else:
            print(f"⚠️  {service_name}: No docker-compose.yml found")
            
        # Also add to Dockerfile if it exists
        dockerfile = service_dir / "Dockerfile"
        if dockerfile.exists():
            add_healthcheck_to_dockerfile(dockerfile)
        else:
            print(f"⚠️  {service_name}: No Dockerfile found")
    
    print(f"\n✅ Health Check Remediation Complete")
    print(f"📊 Fixed: {fixed_count}/{len(MISSING_HEALTHCHECK_SERVICES)} services")
    
if __name__ == "__main__":
    remediate_healthchecks()
