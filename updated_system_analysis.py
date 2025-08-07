#!/usr/bin/env python3
"""
UPDATED COMPREHENSIVE SYSTEM ANALYSIS
=====================================
Deep analysis of MainPC and PC2 subsystems based on latest codebase updates
"""

import json
import yaml
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

class UpdatedSystemAnalyzer:
    def __init__(self):
        self.analysis = {
            "scan_timestamp": datetime.now().isoformat(),
            "codebase_version": "post-120-commits",
            "critical_findings": [],
            "blind_spots_identified": [],
            "new_components_analysis": [],
            "recommendations": []
        }
        
    def analyze_updated_architecture(self):
        """Analyze the updated architecture with new Docker structure"""
        print("🔍 ANALYZING UPDATED ARCHITECTURE...")
        
        # 1. Docker Structure Analysis
        self.analyze_docker_reorganization()
        
        # 2. New Services Analysis  
        self.analyze_new_services()
        
        # 3. Configuration Drift Check
        self.analyze_configuration_updates()
        
        # 4. Cross-Machine Communication Updates
        self.analyze_cross_machine_updates()
        
        # 5. Monitoring & Observability Updates
        self.analyze_observability_updates()
        
        return self.analysis
    
    def analyze_docker_reorganization(self):
        """Analyze the massive Docker reorganization"""
        print("📦 Analyzing Docker Reorganization...")
        
        findings = []
        
        # Check new docker structure
        docker_path = Path("docker")
        if docker_path.exists():
            docker_dirs = [d.name for d in docker_path.iterdir() if d.is_dir()]
            
            findings.append({
                "category": "docker_structure",
                "type": "massive_reorganization",
                "description": f"Found {len(docker_dirs)} individual Docker services - massive containerization",
                "impact": "high",
                "details": {
                    "service_count": len(docker_dirs),
                    "individual_containers": True,
                    "backup_locations": ["docker_backup_not_in_startup_config", "mainpc_docker_backup_not_in_startup_config"]
                },
                "potential_issues": [
                    "Resource overhead from many containers",
                    "Complex orchestration required", 
                    "Potential port conflicts",
                    "Backup containers not aligned with startup configs"
                ]
            })
        
        # Check shared base images
        shared_path = Path("docker/shared/base_pc2")
        if shared_path.exists():
            base_images = list(shared_path.glob("*.Dockerfile"))
            findings.append({
                "category": "docker_optimization",
                "type": "shared_base_images", 
                "description": f"New shared base images: {[f.name for f in base_images]}",
                "impact": "positive",
                "details": {
                    "base_images": [f.name for f in base_images],
                    "optimization_potential": "reduced build times and image sizes"
                }
            })
        
        self.analysis["new_components_analysis"].extend(findings)
    
    def analyze_new_services(self):
        """Analyze newly created services"""
        print("🛠️ Analyzing New Services...")
        
        new_services = []
        services_path = Path("services")
        
        if services_path.exists():
            for service_dir in services_path.iterdir():
                if service_dir.is_dir():
                    service_info = {
                        "name": service_dir.name,
                        "has_dockerfile": (service_dir / "Dockerfile").exists(),
                        "has_requirements": (service_dir / "requirements.txt").exists(),
                        "has_readme": (service_dir / "README.md").exists()
                    }
                    
                    # Special analysis for specific services
                    if service_dir.name == "cross_gpu_scheduler":
                        service_info["type"] = "gpu_coordination"
                        service_info["impact"] = "addresses GPU resource blind spot"
                    elif service_dir.name == "streaming_translation_proxy":
                        service_info["type"] = "translation_optimization"  
                        service_info["impact"] = "real-time translation capability"
                    elif service_dir.name == "central_error_bus":
                        service_info["type"] = "error_coordination"
                        service_info["impact"] = "centralized error handling"
                    
                    new_services.append(service_info)
        
        self.analysis["new_components_analysis"].append({
            "category": "new_services",
            "type": "service_expansion",
            "description": f"Found {len(new_services)} new services in /services/",
            "impact": "medium_to_high",
            "services": new_services
        })
    
    def analyze_configuration_updates(self):
        """Analyze configuration file updates and potential drift"""
        print("⚙️ Analyzing Configuration Updates...")
        
        config_findings = []
        
        # Check startup config alignment
        mainpc_config = Path("main_pc_code/config/startup_config.yaml")
        pc2_config = Path("pc2_code/config/startup_config.yaml")
        
        if mainpc_config.exists() and pc2_config.exists():
            try:
                with open(mainpc_config) as f:
                    mainpc_data = yaml.safe_load(f)
                with open(pc2_config) as f:
                    pc2_data = yaml.safe_load(f)
                
                # Count agents in each
                mainpc_agents = 0
                pc2_agents = 0
                
                if 'agent_groups' in mainpc_data:
                    for group in mainpc_data['agent_groups'].values():
                        mainpc_agents += len(group) if isinstance(group, dict) else 0
                
                if 'pc2_services' in pc2_data:
                    pc2_agents = len(pc2_data['pc2_services'])
                
                config_findings.append({
                    "category": "configuration_analysis",
                    "type": "agent_distribution",
                    "description": f"MainPC: {mainpc_agents} agents, PC2: {pc2_agents} agents",
                    "impact": "informational",
                    "details": {
                        "mainpc_agent_count": mainpc_agents,
                        "pc2_agent_count": pc2_agents,
                        "total_system_agents": mainpc_agents + pc2_agents
                    }
                })
                
            except Exception as e:
                config_findings.append({
                    "category": "configuration_analysis", 
                    "type": "config_parse_error",
                    "description": f"Failed to parse configs: {e}",
                    "impact": "high"
                })
        
        self.analysis["critical_findings"].extend(config_findings)
    
    def analyze_cross_machine_updates(self):
        """Analyze cross-machine communication updates"""
        print("🌐 Analyzing Cross-Machine Communication Updates...")
        
        # Check if new services address cross-machine communication
        findings = []
        
        # GPU Scheduler cross-machine capability
        gpu_scheduler_path = Path("services/cross_gpu_scheduler")
        if gpu_scheduler_path.exists():
            findings.append({
                "category": "cross_machine_improvements",
                "type": "gpu_coordination",
                "description": "Cross-GPU Scheduler addresses GPU resource coordination blind spot",
                "impact": "positive_high",
                "addresses_blind_spot": "GPU resource coordination between RTX 4090 and RTX 3060"
            })
        
        # Check for remaining communication gaps
        findings.append({
            "category": "remaining_blind_spots",
            "type": "network_resilience", 
            "description": "ZMQ Bridge still single point of failure - no visible failover mechanism",
            "impact": "high",
            "recommendation": "Implement redundant communication channels"
        })
        
        self.analysis["blind_spots_identified"].extend(findings)
    
    def analyze_observability_updates(self):
        """Analyze observability and monitoring updates"""
        print("📊 Analyzing Observability Updates...")
        
        obs_findings = []
        
        # Check ObservabilityHub updates
        obs_hub_paths = [
            Path("phase1_implementation/consolidated_agents/observability_hub"),
            Path("docker/observability_hub"),
            Path("docker/pc2_observability_hub")
        ]
        
        obs_components = []
        for path in obs_hub_paths:
            if path.exists():
                obs_components.append(str(path))
        
        if obs_components:
            obs_findings.append({
                "category": "observability_improvements",
                "type": "hub_consolidation",
                "description": f"ObservabilityHub components found: {obs_components}",
                "impact": "positive",
                "addresses_blind_spot": "Centralized monitoring across MainPC and PC2"
            })
        
        # Check for dashboard services
        dashboard_path = Path("services/obs_dashboard_api")
        if dashboard_path.exists():
            obs_findings.append({
                "category": "observability_improvements", 
                "type": "dashboard_api",
                "description": "Dashboard API service found - addresses unified monitoring blind spot",
                "impact": "positive_high"
            })
        
        self.analysis["critical_findings"].extend(obs_findings)
    
    def generate_blind_spot_commands(self):
        """Generate specific commands to investigate remaining blind spots"""
        
        commands = {
            "network_analysis": [
                "netstat -tlnp | grep -E '5600|7155'",  # ZMQ Bridge and GPU Scheduler
                "ps aux | grep -E 'zmq|proxy|scheduler'",
                "docker ps | grep -E 'cross_gpu|translation|error_bus'"
            ],
            "resource_coordination": [
                "nvidia-smi",
                "docker stats --no-stream",
                "free -h && df -h"
            ],
            "service_health": [
                "curl -s http://localhost:8000/health",  # GPU Scheduler health
                "curl -s http://localhost:6596/health",  # Translation Proxy health
                "docker inspect $(docker ps -q) --format '{{.Name}}: {{.State.Health.Status}}'"
            ],
            "configuration_validation": [
                "find . -name startup_config.yaml -exec wc -l {} +",
                "grep -r 'PORT_OFFSET' main_pc_code/ pc2_code/ | wc -l",
                "find docker/ -name requirements.txt | wc -l"
            ]
        }
        
        return commands
    
    def save_analysis(self, filename="updated_system_analysis.json"):
        """Save analysis to file"""
        with open(filename, 'w') as f:
            json.dump(self.analysis, f, indent=2)
        
        print(f"✅ Analysis saved to {filename}")

def main():
    analyzer = UpdatedSystemAnalyzer()
    results = analyzer.analyze_updated_architecture()
    
    print(f"\n🔍 UPDATED SYSTEM ANALYSIS COMPLETED")
    print(f"📊 Critical Findings: {len(results['critical_findings'])}")
    print(f"🎯 Blind Spots Identified: {len(results['blind_spots_identified'])}") 
    print(f"🛠️ New Components: {len(results['new_components_analysis'])}")
    
    print("\n📋 KEY FINDINGS SUMMARY:")
    for finding in results['critical_findings'][:3]:  # Show top 3
        print(f"   • {finding.get('description', 'N/A')}")
    
    analyzer.save_analysis()
    
    print("\n🎯 INVESTIGATION COMMANDS:")
    commands = analyzer.generate_blind_spot_commands()
    for category, cmd_list in commands.items():
        print(f"\n{category.upper()}:")
        for cmd in cmd_list:
            print(f"   {cmd}")

if __name__ == "__main__":
    main()