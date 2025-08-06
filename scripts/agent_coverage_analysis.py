#!/usr/bin/env python3
"""
Agent Coverage Analysis
Fixed to analyze actual Docker services and agents
"""

import os
import re
from pathlib import Path

def extract_agents_from_docker_compose():
    """Extract agents from actual docker-compose.yml files"""
    agents_by_group = {}
    docker_dir = Path("docker")
    
    if not docker_dir.exists():
        print("❌ Docker directory not found!")
        return agents_by_group
    
    for service_dir in docker_dir.iterdir():
        if not service_dir.is_dir():
            continue
            
        compose_file = service_dir / "docker-compose.yml"
        if not compose_file.exists():
            continue
            
        group = service_dir.name
        
        with open(compose_file, 'r') as f:
            content = f.read()
        
        # Find all agent commands in YAML format
        # Pattern: - main_pc_code.agents.X
        pattern = r'^\s*-\s+main_pc_code\.agents\.([^\s]+)\s*$'
        matches = re.findall(pattern, content, re.MULTILINE)
        
        if matches:
            agents_by_group[group] = matches
    
    return agents_by_group

def analyze_coverage():
    """Analyze what agents are actually defined in Docker"""
    print("🔍 AGENT COVERAGE ANALYSIS")
    print("=" * 50)
    
    agents_by_group = extract_agents_from_docker_compose()
    
    if not agents_by_group:
        print("❌ No agents found in any Docker compose files")
        return
        
    total_agents = 0
    print("\n📊 AGENTS BY GROUP:")
    
    for group, agents in agents_by_group.items():
        print(f"\n🔧 {group.upper()}:")
        for agent in agents:
            print(f"   ✅ {agent}")
            total_agents += 1
    
    # Count total docker services
    docker_services = len([d for d in Path('docker').iterdir() if d.is_dir()])
    
    print(f"\n🎯 SUMMARY:")
    print(f"   Total Docker services: {docker_services}")
    print(f"   Services with agents: {len(agents_by_group)}")
    print(f"   Total agents found: {total_agents}")
    
    if total_agents > 0:
        coverage_rate = (len(agents_by_group) / docker_services * 100)
        print(f"   Agent coverage: {coverage_rate:.1f}% of Docker services")
        print(f"   ✅ SUCCESS: Found {total_agents} agents across {len(agents_by_group)} services")
    else:
        print(f"   ⚠️  WARNING: No agents detected - check compose file patterns")

if __name__ == "__main__":
    analyze_coverage()
