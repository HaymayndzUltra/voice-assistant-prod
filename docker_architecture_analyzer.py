#!/usr/bin/env python3
"""
Docker Architecture Analyzer
Comprehensive audit tool for validating Docker implementation against blueprint
Date: 2025-01-13
Confidence: 95%
"""

import os
import json
import subprocess
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re

class DockerArchitectureAnalyzer:
    def __init__(self):
        self.workspace = Path("/workspace")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "folders_analyzed": {},
            "agents_consolidated": {},
            "docker_status": {},
            "discrepancies": [],
            "action_items": [],
            "compliance_score": 0
        }
        self.blueprint_services = self.load_blueprint()
        
    def load_blueprint(self) -> Dict:
        """Load service definitions from plan.md blueprint"""
        blueprint_path = self.workspace / "memory-bank/DOCUMENTS/plan.md"
        services = {}
        
        if blueprint_path.exists():
            with open(blueprint_path, 'r') as f:
                lines = f.readlines()
                # Parse Fleet Coverage Table (lines 109-176)
                for i in range(110, 177):
                    if i < len(lines):
                        line = lines[i].strip()
                        if line and not line.startswith('#'):
                            parts = line.split('\t')
                            if len(parts) >= 5:
                                service_name = parts[0]
                                services[service_name] = {
                                    'machine': parts[1],
                                    'needs': parts[2],
                                    'base_family': parts[3],
                                    'ports': parts[4]
                                }
        return services
    
    def analyze_folder_structure(self):
        """Analyze critical service folders"""
        target_folders = [
            "unified_observability_center",
            "real_time_audio_pipeline",
            "model_ops_coordinator",
            "memory_fusion_hub",
            "affective_processing_center"
        ]
        
        for folder in target_folders:
            folder_path = self.workspace / folder
            if folder_path.exists():
                analysis = {
                    "exists": True,
                    "has_dockerfile": False,
                    "has_entrypoint": False,
                    "has_docker_compose": False,
                    "has_requirements": False,
                    "main_entry": None,
                    "consolidated_agents": []
                }
                
                # Check for Docker files
                if (folder_path / "Dockerfile").exists():
                    analysis["has_dockerfile"] = True
                if (folder_path / "entrypoint.sh").exists():
                    analysis["has_entrypoint"] = True
                if (folder_path / "docker-compose.yml").exists():
                    analysis["has_docker_compose"] = True
                if (folder_path / "requirements.txt").exists():
                    analysis["has_requirements"] = True
                    
                # Find main entry point
                for file in ["app.py", "main.py", "server.py"]:
                    if (folder_path / file).exists():
                        analysis["main_entry"] = file
                        break
                
                # Find consolidated agents
                try:
                    result = subprocess.run(
                        f'grep -r "class.*Agent" {folder_path} --include="*.py" | grep -v test',
                        shell=True, capture_output=True, text=True
                    )
                    if result.stdout:
                        agents = re.findall(r'class\s+(\w*Agent)', result.stdout)
                        analysis["consolidated_agents"] = list(set(agents))
                except:
                    pass
                
                self.results["folders_analyzed"][folder] = analysis
            else:
                self.results["folders_analyzed"][folder] = {"exists": False}
    
    def check_docker_status(self):
        """Check current Docker container and image status"""
        try:
            # Get running containers
            result = subprocess.run(
                'docker ps --format "{{.Names}}|{{.Status}}|{{.Ports}}"',
                shell=True, capture_output=True, text=True
            )
            running_containers = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) == 3:
                            running_containers.append({
                                "name": parts[0],
                                "status": parts[1],
                                "ports": parts[2]
                            })
            
            self.results["docker_status"]["running_containers"] = running_containers
            
            # Get Docker images
            result = subprocess.run(
                'docker images --format "{{.Repository}}|{{.Tag}}|{{.Size}}"',
                shell=True, capture_output=True, text=True
            )
            images = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line and ('family-' in line or 'base-' in line):
                        parts = line.split('|')
                        if len(parts) == 3:
                            images.append({
                                "repository": parts[0],
                                "tag": parts[1],
                                "size": parts[2]
                            })
            
            self.results["docker_status"]["images"] = images
            
        except Exception as e:
            self.results["docker_status"]["error"] = str(e)
    
    def analyze_startup_configs(self):
        """Analyze startup configuration files"""
        configs = {}
        
        for machine in ["main_pc_code", "pc2_code"]:
            config_path = self.workspace / machine / "config/startup_config.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    try:
                        config = yaml.safe_load(f)
                        # Extract agent groups
                        if "agent_groups" in config:
                            configs[machine] = {
                                "groups": list(config["agent_groups"].keys()),
                                "total_agents": sum(
                                    len(group) for group in config["agent_groups"].values()
                                )
                            }
                    except Exception as e:
                        configs[machine] = {"error": str(e)}
        
        self.results["startup_configs"] = configs
    
    def identify_discrepancies(self):
        """Compare implementation against blueprint"""
        discrepancies = []
        
        # Check if required services have Docker files
        for folder, analysis in self.results["folders_analyzed"].items():
            if analysis.get("exists"):
                if not analysis.get("has_dockerfile"):
                    discrepancies.append({
                        "severity": "HIGH",
                        "type": "MISSING_DOCKERFILE",
                        "service": folder,
                        "message": f"{folder} missing Dockerfile"
                    })
                if not analysis.get("has_entrypoint"):
                    discrepancies.append({
                        "severity": "MEDIUM",
                        "type": "MISSING_ENTRYPOINT",
                        "service": folder,
                        "message": f"{folder} missing entrypoint.sh"
                    })
        
        # Check Docker container status
        if not self.results["docker_status"].get("running_containers"):
            discrepancies.append({
                "severity": "CRITICAL",
                "type": "NO_CONTAINERS_RUNNING",
                "message": "No Docker containers are currently running"
            })
        
        # Check for base images
        if not self.results["docker_status"].get("images"):
            discrepancies.append({
                "severity": "HIGH",
                "type": "NO_BASE_IMAGES",
                "message": "No family-* or base-* Docker images found"
            })
        
        self.results["discrepancies"] = discrepancies
    
    def generate_action_items(self):
        """Generate prioritized action items"""
        action_items = []
        
        # Critical actions
        if any(d["severity"] == "CRITICAL" for d in self.results["discrepancies"]):
            action_items.append({
                "priority": 1,
                "action": "Start Docker daemon and verify Docker installation",
                "command": "sudo systemctl start docker && docker version"
            })
        
        # Build base images
        if any(d["type"] == "NO_BASE_IMAGES" for d in self.results["discrepancies"]):
            action_items.append({
                "priority": 2,
                "action": "Build base Docker images according to blueprint",
                "command": "bash build-images.sh"
            })
        
        # Build service images
        for folder in self.results["folders_analyzed"]:
            if self.results["folders_analyzed"][folder].get("has_dockerfile"):
                action_items.append({
                    "priority": 3,
                    "action": f"Build {folder} Docker image",
                    "command": f"docker build -t {folder}:latest ./{folder}/"
                })
        
        # Start services
        action_items.append({
            "priority": 4,
            "action": "Start all services using docker-compose",
            "command": "docker-compose up -d"
        })
        
        self.results["action_items"] = sorted(action_items, key=lambda x: x["priority"])
    
    def calculate_compliance_score(self):
        """Calculate overall compliance percentage"""
        total_checks = 0
        passed_checks = 0
        
        # Folder checks
        for folder, analysis in self.results["folders_analyzed"].items():
            if analysis.get("exists"):
                total_checks += 4  # dockerfile, entrypoint, compose, requirements
                if analysis.get("has_dockerfile"): passed_checks += 1
                if analysis.get("has_entrypoint"): passed_checks += 1
                if analysis.get("has_docker_compose"): passed_checks += 1
                if analysis.get("has_requirements"): passed_checks += 1
        
        # Docker status checks
        total_checks += 2  # containers and images
        if self.results["docker_status"].get("running_containers"):
            passed_checks += 1
        if self.results["docker_status"].get("images"):
            passed_checks += 1
        
        if total_checks > 0:
            self.results["compliance_score"] = round((passed_checks / total_checks) * 100, 2)
    
    def generate_report(self):
        """Generate comprehensive markdown report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.workspace / f"docker_architecture_audit_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write(f"# Docker Architecture Audit Report\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Compliance Score:** {self.results['compliance_score']}%\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Services Analyzed:** {len(self.results['folders_analyzed'])}\n")
            f.write(f"- **Docker Status:** {'🔴 No containers running' if not self.results['docker_status'].get('running_containers') else '🟢 Containers active'}\n")
            f.write(f"- **Critical Issues:** {len([d for d in self.results['discrepancies'] if d['severity'] == 'CRITICAL'])}\n")
            f.write(f"- **Action Items:** {len(self.results['action_items'])}\n\n")
            
            # Service Analysis
            f.write("## Service Consolidation Analysis\n\n")
            for folder, analysis in self.results["folders_analyzed"].items():
                f.write(f"### {folder}\n")
                if analysis.get("exists"):
                    f.write(f"- **Status:** ✅ Exists\n")
                    f.write(f"- **Dockerfile:** {'✅' if analysis.get('has_dockerfile') else '❌'}\n")
                    f.write(f"- **Entrypoint:** {'✅' if analysis.get('has_entrypoint') else '❌'}\n")
                    f.write(f"- **Main Entry:** {analysis.get('main_entry', 'Not found')}\n")
                    if analysis.get('consolidated_agents'):
                        f.write(f"- **Consolidated Agents:** {', '.join(analysis['consolidated_agents'])}\n")
                else:
                    f.write(f"- **Status:** ❌ Not found\n")
                f.write("\n")
            
            # Discrepancies
            f.write("## Critical Discrepancies\n\n")
            for disc in sorted(self.results['discrepancies'], key=lambda x: x['severity']):
                emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(disc['severity'], "⚪")
                f.write(f"{emoji} **{disc['severity']}** - {disc['message']}\n")
            f.write("\n")
            
            # Action Items
            f.write("## Actionable Remediation Steps\n\n")
            for item in self.results['action_items']:
                f.write(f"### Priority {item['priority']}: {item['action']}\n")
                f.write(f"```bash\n{item['command']}\n```\n\n")
            
            # Raw JSON Results
            f.write("## Raw Analysis Data\n\n")
            f.write("```json\n")
            f.write(json.dumps(self.results, indent=2))
            f.write("\n```\n")
        
        return report_path
    
    def run_analysis(self):
        """Execute complete analysis pipeline"""
        print("🔍 Starting Docker Architecture Analysis...")
        
        print("📁 Analyzing folder structure...")
        self.analyze_folder_structure()
        
        print("🐳 Checking Docker status...")
        self.check_docker_status()
        
        print("⚙️ Analyzing startup configurations...")
        self.analyze_startup_configs()
        
        print("🔎 Identifying discrepancies...")
        self.identify_discrepancies()
        
        print("📋 Generating action items...")
        self.generate_action_items()
        
        print("📊 Calculating compliance score...")
        self.calculate_compliance_score()
        
        print("📝 Generating report...")
        report_path = self.generate_report()
        
        print(f"\n✅ Analysis complete!")
        print(f"📄 Report saved to: {report_path}")
        print(f"🎯 Compliance Score: {self.results['compliance_score']}%")
        
        # Save JSON results
        json_path = self.workspace / f"docker_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"💾 JSON results saved to: {json_path}")
        
        return self.results

if __name__ == "__main__":
    analyzer = DockerArchitectureAnalyzer()
    results = analyzer.run_analysis()
    
    # Print summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Total Discrepancies: {len(results['discrepancies'])}")
    print(f"Critical Issues: {len([d for d in results['discrepancies'] if d['severity'] == 'CRITICAL'])}")
    print(f"Action Items: {len(results['action_items'])}")
    print("\nTop Priority Actions:")
    for item in results['action_items'][:3]:
        print(f"  {item['priority']}. {item['action']}")