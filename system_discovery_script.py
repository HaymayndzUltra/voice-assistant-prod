#!/usr/bin/env python3
"""
System Discovery Script for Background Agent
Maps the complete file structure of the dual-machine AI system
"""

import os
from pathlib import Path
from typing import Dict, List, Set
import json

def discover_system_structure() -> Dict[str, any]:
    """Complete system discovery and mapping"""
    
    project_root = Path.cwd()
    discovery_report = {
        'project_root': str(project_root),
        'docker_containers': {},
        'agent_locations': {},
        'configuration_files': {},
        'requirements_files': {},
        'shared_modules': {},
        'startup_configs': {},
        'missing_files': [],
        'summary': {}
    }
    
    print("🔍 SYSTEM DISCOVERY STARTING...")
    print("=" * 60)
    
    # 1. Docker Container Discovery
    print("\n📦 DISCOVERING DOCKER CONTAINERS...")
    docker_dir = project_root / "docker"
    
    if docker_dir.exists():
        container_count = 0
        for container_path in docker_dir.iterdir():
            if container_path.is_dir():
                container_count += 1
                container_name = container_path.name
                
                container_info = {
                    'path': str(container_path),
                    'has_dockerfile': (container_path / "Dockerfile").exists(),
                    'has_docker_compose': (container_path / "docker-compose.yml").exists(),
                    'has_requirements': (container_path / "requirements.txt").exists(),
                    'python_files': [],
                    'other_requirements': []
                }
                
                # Find Python files
                for py_file in container_path.rglob("*.py"):
                    container_info['python_files'].append(str(py_file.relative_to(project_root)))
                
                # Find other requirement files
                for req_file in container_path.glob("requirements*.txt"):
                    container_info['other_requirements'].append(str(req_file.relative_to(project_root)))
                
                discovery_report['docker_containers'][container_name] = container_info
        
        print(f"   Found {container_count} Docker containers")
    else:
        print("   ❌ Docker directory not found!")
    
    # 2. Agent Code Discovery
    print("\n🤖 DISCOVERING AGENT LOCATIONS...")
    
    # MainPC Agents
    mainpc_agents_dir = project_root / "main_pc_code" / "agents"
    if mainpc_agents_dir.exists():
        mainpc_agents = []
        for agent_file in mainpc_agents_dir.rglob("*.py"):
            mainpc_agents.append(str(agent_file.relative_to(project_root)))
        discovery_report['agent_locations']['mainpc_agents'] = mainpc_agents
        print(f"   MainPC agents: {len(mainpc_agents)} Python files")
    
    # PC2 Agents
    pc2_agents_dir = project_root / "pc2_code" / "agents"
    if pc2_agents_dir.exists():
        pc2_agents = []
        for agent_file in pc2_agents_dir.rglob("*.py"):
            pc2_agents.append(str(agent_file.relative_to(project_root)))
        discovery_report['agent_locations']['pc2_agents'] = pc2_agents
        print(f"   PC2 agents: {len(pc2_agents)} Python files")
    
    # 3. Shared Module Discovery
    print("\n🔗 DISCOVERING SHARED MODULES...")
    
    common_dir = project_root / "common"
    if common_dir.exists():
        shared_modules = []
        for common_file in common_dir.rglob("*.py"):
            shared_modules.append(str(common_file.relative_to(project_root)))
        discovery_report['shared_modules']['common'] = shared_modules
        print(f"   Common modules: {len(shared_modules)} Python files")
    
    # Phase implementations
    phase_dir = project_root / "phase1_implementation"
    if phase_dir.exists():
        phase_modules = []
        for phase_file in phase_dir.rglob("*.py"):
            phase_modules.append(str(phase_file.relative_to(project_root)))
        discovery_report['shared_modules']['phase1_implementation'] = phase_modules
        print(f"   Phase1 modules: {len(phase_modules)} Python files")
    
    # 4. Configuration File Discovery
    print("\n⚙️ DISCOVERING CONFIGURATION FILES...")
    
    config_patterns = [
        "startup_config*.yaml",
        "docker-compose*.yml",
        "*.yaml",
        "*.yml",
        "*.json",
        "env_config*.sh"
    ]
    
    config_files = {}
    for pattern in config_patterns:
        files = list(project_root.rglob(pattern))
        if files:
            config_files[pattern] = [str(f.relative_to(project_root)) for f in files]
            print(f"   {pattern}: {len(files)} files")
    
    discovery_report['configuration_files'] = config_files
    
    # 5. Requirements File Discovery
    print("\n📋 DISCOVERING REQUIREMENTS FILES...")
    
    req_files = {}
    req_patterns = ["requirements*.txt", "*.requirements"]
    
    for pattern in req_patterns:
        files = list(project_root.rglob(pattern))
        if files:
            req_files[pattern] = [str(f.relative_to(project_root)) for f in files]
            print(f"   {pattern}: {len(files)} files")
    
    discovery_report['requirements_files'] = req_files
    
    # 6. Startup Configuration Analysis
    print("\n🚀 ANALYZING STARTUP CONFIGURATIONS...")
    
    startup_configs = {}
    
    # MainPC startup config
    mainpc_config = project_root / "main_pc_code" / "config" / "startup_config.yaml"
    if mainpc_config.exists():
        startup_configs['mainpc'] = str(mainpc_config.relative_to(project_root))
        print(f"   MainPC config: {mainpc_config.relative_to(project_root)}")
    
    # PC2 startup config
    pc2_config = project_root / "pc2_code" / "config" / "startup_config.yaml"
    if pc2_config.exists():
        startup_configs['pc2'] = str(pc2_config.relative_to(project_root))
        print(f"   PC2 config: {pc2_config.relative_to(project_root)}")
    
    # Root configs
    for config_file in project_root.glob("*startup_config*.yaml"):
        startup_configs[f'root_{config_file.stem}'] = str(config_file.relative_to(project_root))
        print(f"   Root config: {config_file.relative_to(project_root)}")
    
    discovery_report['startup_configs'] = startup_configs
    
    # 7. Missing File Detection
    print("\n⚠️ DETECTING MISSING CRITICAL FILES...")
    
    missing_files = []
    
    # Check each Docker container for required files
    for container_name, container_info in discovery_report['docker_containers'].items():
        container_path = Path(container_info['path'])
        
        if not container_info['has_dockerfile']:
            missing_files.append(f"{container_path}/Dockerfile")
        
        if not container_info['has_docker_compose']:
            missing_files.append(f"{container_path}/docker-compose.yml")
        
        if not container_info['has_requirements']:
            missing_files.append(f"{container_path}/requirements.txt")
    
    discovery_report['missing_files'] = missing_files
    print(f"   Missing critical files: {len(missing_files)}")
    
    # 8. Generate Summary
    discovery_report['summary'] = {
        'total_docker_containers': len(discovery_report['docker_containers']),
        'containers_with_dockerfile': sum(1 for c in discovery_report['docker_containers'].values() if c['has_dockerfile']),
        'containers_with_requirements': sum(1 for c in discovery_report['docker_containers'].values() if c['has_requirements']),
        'total_python_files': (
            len(discovery_report['agent_locations'].get('mainpc_agents', [])) +
            len(discovery_report['agent_locations'].get('pc2_agents', [])) +
            len(discovery_report['shared_modules'].get('common', []))
        ),
        'total_requirements_files': sum(len(files) for files in discovery_report['requirements_files'].values()),
        'missing_critical_files': len(missing_files)
    }
    
    return discovery_report

def generate_discovery_paths() -> Dict[str, List[str]]:
    """Generate specific file paths for background agent analysis"""
    
    paths = {
        'docker_containers': [],
        'agent_source_files': [],
        'requirements_files': [],
        'config_files': [],
        'shared_modules': []
    }
    
    project_root = Path.cwd()
    
    # Docker containers
    docker_dir = project_root / "docker"
    if docker_dir.exists():
        for container in docker_dir.iterdir():
            if container.is_dir():
                paths['docker_containers'].append(str(container))
    
    # Agent source files
    for agent_dir in [
        project_root / "main_pc_code" / "agents",
        project_root / "pc2_code" / "agents"
    ]:
        if agent_dir.exists():
            for py_file in agent_dir.rglob("*.py"):
                paths['agent_source_files'].append(str(py_file))
    
    # Requirements files
    for req_file in project_root.rglob("requirements*.txt"):
        paths['requirements_files'].append(str(req_file))
    
    # Config files
    for config_file in project_root.rglob("*config*.yaml"):
        paths['config_files'].append(str(config_file))
    for config_file in project_root.rglob("*config*.yml"):
        paths['config_files'].append(str(config_file))
    
    # Shared modules
    common_dir = project_root / "common"
    if common_dir.exists():
        for py_file in common_dir.rglob("*.py"):
            paths['shared_modules'].append(str(py_file))
    
    return paths

def main():
    """Run complete system discovery"""
    
    print("🎯 AI SYSTEM STRUCTURE DISCOVERY")
    print("=" * 60)
    
    # Run discovery
    discovery_report = discover_system_structure()
    
    # Generate paths for background agent
    analysis_paths = generate_discovery_paths()
    
    # Print summary
    print("\n📊 DISCOVERY SUMMARY:")
    print("=" * 60)
    summary = discovery_report['summary']
    print(f"Docker containers found: {summary['total_docker_containers']}")
    print(f"Containers with Dockerfile: {summary['containers_with_dockerfile']}")
    print(f"Containers with requirements.txt: {summary['containers_with_requirements']}")
    print(f"Total Python files: {summary['total_python_files']}")
    print(f"Total requirements files: {summary['total_requirements_files']}")
    print(f"Missing critical files: {summary['missing_critical_files']}")
    
    # Save reports
    with open("system_discovery_report.json", "w") as f:
        json.dump(discovery_report, f, indent=2)
    
    with open("analysis_paths.json", "w") as f:
        json.dump(analysis_paths, f, indent=2)
    
    print(f"\n✅ Discovery complete!")
    print(f"📁 Reports saved:")
    print(f"   - system_discovery_report.json")
    print(f"   - analysis_paths.json")
    
    # Print critical missing files
    if discovery_report['missing_files']:
        print(f"\n⚠️ CRITICAL MISSING FILES:")
        for missing_file in discovery_report['missing_files'][:10]:  # Show first 10
            print(f"   ❌ {missing_file}")
        if len(discovery_report['missing_files']) > 10:
            print(f"   ... and {len(discovery_report['missing_files']) - 10} more")

if __name__ == "__main__":
    main()