#!/usr/bin/env python3
"""
Migration Validator - Comprehensive validation of AI system migration checklist
Validates repository structure, agent paths, dependencies, and configuration
"""
import yaml, pathlib, pprint, sys, itertools, json, os
from collections import defaultdict

class MigrationValidator:
    def __init__(self):
        self.results = {
            "repository_structure": {},
            "agent_paths": {},
            "configuration_files": {},
            "dependencies": {},
            "docker_environment": {},
            "shared_resources": {},
            "potential_issues": []
        }
        
    def validate_repository_structure(self):
        """Validate repository skeleton structure"""
        print("🔍 Validating Repository Structure...")
        
        required_dirs = [
            "main_pc_code",
            "pc2_code", 
            "docker",
            "docs",
            "models",
            "logs",
            "data"
        ]
        
        for dir_name in required_dirs:
            path = pathlib.Path(dir_name)
            if path.exists():
                self.results["repository_structure"][dir_name] = {
                    "status": "✅ EXISTS",
                    "path": str(path.absolute())
                }
            else:
                self.results["repository_structure"][dir_name] = {
                    "status": "❌ MISSING",
                    "path": str(path.absolute())
                }
                self.results["potential_issues"].append(f"Missing directory: {dir_name}")
    
    def validate_agent_paths(self):
        """Validate all agent script paths exist"""
        print("🔍 Validating Agent Script Paths...")
        
        # Load agent paths from our previous analysis
        try:
            with open('agent_analysis_results.json', 'r') as f:
                agent_data = json.load(f)
            
            for config_file, agents in agent_data['results'].items():
                system_name = "MainPC" if "main_pc_code" in config_file else "PC2"
                self.results["agent_paths"][system_name] = {
                    "total_agents": len(agents),
                    "valid_paths": 0,
                    "missing_paths": 0,
                    "missing_agents": []
                }
                
                for agent_name, script_path in agents.items():
                    if pathlib.Path(script_path).exists():
                        self.results["agent_paths"][system_name]["valid_paths"] += 1
                    else:
                        self.results["agent_paths"][system_name]["missing_paths"] += 1
                        self.results["agent_paths"][system_name]["missing_agents"].append({
                            "name": agent_name,
                            "path": script_path
                        })
                        self.results["potential_issues"].append(f"Missing agent script: {script_path}")
        
        except FileNotFoundError:
            self.results["potential_issues"].append("agent_analysis_results.json not found - run agent_script_path_analysis.py first")
    
    def validate_configuration_files(self):
        """Validate configuration files exist and are valid YAML"""
        print("🔍 Validating Configuration Files...")
        
        config_files = [
            "main_pc_code/config/startup_config.yaml",
            "pc2_code/config/startup_config.yaml"
        ]
        
        for config_file in config_files:
            path = pathlib.Path(config_file)
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        yaml.safe_load(f)
                    self.results["configuration_files"][config_file] = {
                        "status": "✅ VALID YAML",
                        "path": str(path.absolute())
                    }
                except yaml.YAMLError as e:
                    self.results["configuration_files"][config_file] = {
                        "status": "❌ INVALID YAML",
                        "error": str(e),
                        "path": str(path.absolute())
                    }
                    self.results["potential_issues"].append(f"Invalid YAML in {config_file}: {e}")
            else:
                self.results["configuration_files"][config_file] = {
                    "status": "❌ MISSING",
                    "path": str(path.absolute())
                }
                self.results["potential_issues"].append(f"Missing configuration file: {config_file}")
    
    def validate_dependencies(self):
        """Validate Python dependency files"""
        print("🔍 Validating Dependencies...")
        
        dependency_files = [
            "main_pc_code/requirements.txt",
            "pc2_code/requirements.txt",
            "requirements.txt"
        ]
        
        for dep_file in dependency_files:
            path = pathlib.Path(dep_file)
            if path.exists():
                # Check for unpinned dependencies
                with open(path, 'r') as f:
                    content = f.read()
                    unpinned = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#') and '>=' in line:
                            unpinned.append(line)
                
                self.results["dependencies"][dep_file] = {
                    "status": "✅ EXISTS",
                    "unpinned_dependencies": unpinned,
                    "path": str(path.absolute())
                }
                
                if unpinned:
                    self.results["potential_issues"].append(f"Unpinned dependencies in {dep_file}: {unpinned}")
            else:
                self.results["dependencies"][dep_file] = {
                    "status": "❌ MISSING",
                    "path": str(path.absolute())
                }
                self.results["potential_issues"].append(f"Missing dependency file: {dep_file}")
    
    def validate_docker_environment(self):
        """Validate Docker environment files"""
        print("🔍 Validating Docker Environment...")
        
        docker_files = [
            "Dockerfile",
            "docker/mainpc/Dockerfile",
            "docker/pc2/Dockerfile",
            "docker-compose.yml"
        ]
        
        for docker_file in docker_files:
            path = pathlib.Path(docker_file)
            if path.exists():
                self.results["docker_environment"][docker_file] = {
                    "status": "✅ EXISTS",
                    "path": str(path.absolute())
                }
            else:
                self.results["docker_environment"][docker_file] = {
                    "status": "❌ MISSING",
                    "path": str(path.absolute())
                }
                self.results["potential_issues"].append(f"Missing Docker file: {docker_file}")
    
    def validate_shared_resources(self):
        """Validate shared resources and models"""
        print("🔍 Validating Shared Resources...")
        
        # Check models directory
        models_path = pathlib.Path("models")
        if models_path.exists():
            model_files = list(models_path.glob("*.gguf")) + list(models_path.glob("whisper*")) + list(models_path.glob("xtts*"))
            self.results["shared_resources"]["models"] = {
                "status": "✅ EXISTS",
                "count": len(model_files),
                "files": [str(f.name) for f in model_files]
            }
        else:
            self.results["shared_resources"]["models"] = {
                "status": "❌ MISSING",
                "count": 0
            }
            self.results["potential_issues"].append("Missing models directory")
        
        # Check data directory
        data_path = pathlib.Path("data")
        if data_path.exists():
            db_files = list(data_path.glob("*.db"))
            self.results["shared_resources"]["data"] = {
                "status": "✅ EXISTS",
                "db_files": [str(f.name) for f in db_files]
            }
        else:
            self.results["shared_resources"]["data"] = {
                "status": "❌ MISSING"
            }
            self.results["potential_issues"].append("Missing data directory")
        
        # Check logs directory
        logs_path = pathlib.Path("logs")
        if logs_path.exists():
            self.results["shared_resources"]["logs"] = {
                "status": "✅ EXISTS",
                "writable": os.access(logs_path, os.W_OK)
            }
        else:
            self.results["shared_resources"]["logs"] = {
                "status": "❌ MISSING"
            }
            self.results["potential_issues"].append("Missing logs directory")
    
    def check_port_collisions(self):
        """Check for potential port collisions"""
        print("🔍 Checking Port Configurations...")
        
        port_usage = defaultdict(list)
        
        for config_file in ["main_pc_code/config/startup_config.yaml", "pc2_code/config/startup_config.yaml"]:
            if pathlib.Path(config_file).exists():
                with open(config_file, 'r') as f:
                    cfg = yaml.safe_load(f)
                
                # Extract ports from agent configurations
                if "agent_groups" in cfg:
                    for group in cfg["agent_groups"].values():
                        if group:
                            for agent_name, agent_config in group.items():
                                if isinstance(agent_config, dict) and "port" in agent_config:
                                    port = agent_config["port"]
                                    port_usage[port].append(f"{config_file}:{agent_name}")
                
                if "pc2_services" in cfg:
                    for service in cfg["pc2_services"]:
                        if isinstance(service, dict) and "port" in service:
                            port = service["port"]
                            port_usage[port].append(f"{config_file}:{service['name']}")
        
        # Check for collisions
        collisions = {port: agents for port, agents in port_usage.items() if len(agents) > 1}
        if collisions:
            self.results["potential_issues"].append(f"Port collisions detected: {collisions}")
    
    def generate_migration_report(self):
        """Generate comprehensive migration report"""
        print("\n" + "="*80)
        print("MIGRATION VALIDATION REPORT")
        print("="*80)
        
        # Repository Structure
        print("\n📁 REPOSITORY STRUCTURE:")
        for dir_name, info in self.results["repository_structure"].items():
            print(f"   {dir_name}: {info['status']}")
        
        # Agent Paths
        print("\n🤖 AGENT SCRIPT PATHS:")
        for system, info in self.results["agent_paths"].items():
            print(f"   {system}: {info['valid_paths']}/{info['total_agents']} valid paths")
            if info['missing_paths'] > 0:
                print(f"      Missing: {info['missing_paths']} agents")
        
        # Configuration Files
        print("\n⚙️  CONFIGURATION FILES:")
        for config_file, info in self.results["configuration_files"].items():
            print(f"   {config_file}: {info['status']}")
        
        # Dependencies
        print("\n📦 DEPENDENCIES:")
        for dep_file, info in self.results["dependencies"].items():
            print(f"   {dep_file}: {info['status']}")
            if info.get('unpinned_dependencies'):
                print(f"      Unpinned: {len(info['unpinned_dependencies'])} dependencies")
        
        # Docker Environment
        print("\n🐳 DOCKER ENVIRONMENT:")
        for docker_file, info in self.results["docker_environment"].items():
            print(f"   {docker_file}: {info['status']}")
        
        # Shared Resources
        print("\n📚 SHARED RESOURCES:")
        for resource, info in self.results["shared_resources"].items():
            print(f"   {resource}: {info['status']}")
            if resource == "models" and info.get('count', 0) > 0:
                print(f"      Models found: {info['count']}")
        
        # Potential Issues
        if self.results["potential_issues"]:
            print("\n⚠️  POTENTIAL ISSUES:")
            for issue in self.results["potential_issues"]:
                print(f"   • {issue}")
        else:
            print("\n✅ No potential issues detected!")
        
        # Save detailed report
        with open('migration_validation_report.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: migration_validation_report.json")
    
    def run_full_validation(self):
        """Run complete migration validation"""
        self.validate_repository_structure()
        self.validate_agent_paths()
        self.validate_configuration_files()
        self.validate_dependencies()
        self.validate_docker_environment()
        self.validate_shared_resources()
        self.check_port_collisions()
        self.generate_migration_report()

def main():
    validator = MigrationValidator()
    validator.run_full_validation()

if __name__ == "__main__":
    main() 