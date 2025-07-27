#!/usr/bin/env python3
"""
Deep Scan Validator - Comprehensive check for missing components
"""

import os
import sys
import yaml
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple

class DeepScanValidator:
    def __init__(self):
        self.issues = {
            'critical': [],
            'warning': [],
            'info': []
        }
        self.workspace = Path('/workspace')
        self.new_repo = Path('/workspace/unified-system-v1')
        
    def run_deep_scan(self):
        """Run comprehensive deep scan"""
        print("🔍 DEEP SCAN VALIDATION - Checking for missing components...")
        print("=" * 80)
        
        # Run all checks
        self.check_agent_files_exist()
        self.check_config_completeness()
        self.check_import_dependencies()
        self.check_missing_utilities()
        self.check_port_allocations()
        self.check_environment_variables()
        self.check_docker_compatibility()
        self.check_test_coverage()
        self.check_documentation_references()
        self.check_security_issues()
        
        # Print results
        self.print_scan_results()
        
    def check_agent_files_exist(self):
        """Check if all agent files referenced in config actually exist"""
        print("\n📂 Checking agent file existence...")
        
        # Load all configs
        configs_to_check = [
            'config/unified_startup.yaml',
            'config/unified_startup_phase2.yaml'
        ]
        
        all_agents = {}
        
        for config_file in configs_to_check:
            config_path = self.workspace / config_file
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    
                # Extract all agent paths
                for group_name, agents in config.get('agent_groups', {}).items():
                    for agent_name, agent_config in agents.items():
                        script_path = agent_config.get('script_path', '')
                        if script_path:
                            all_agents[agent_name] = script_path
                            
        # Check each agent file
        missing_agents = []
        for agent_name, script_path in all_agents.items():
            full_path = self.workspace / script_path
            if not full_path.exists():
                missing_agents.append(f"{agent_name}: {script_path}")
                
        if missing_agents:
            self.issues['critical'].append(
                f"Missing {len(missing_agents)} agent files that need to be copied:\n" + 
                "\n".join(f"  - {a}" for a in missing_agents[:10]) +
                (f"\n  ... and {len(missing_agents) - 10} more" if len(missing_agents) > 10 else "")
            )
        else:
            self.issues['info'].append(f"All {len(all_agents)} agent files found in workspace")
            
    def check_config_completeness(self):
        """Check if all configurations are complete"""
        print("\n⚙️  Checking configuration completeness...")
        
        # Check main config
        config_path = self.new_repo / 'config/startup_config.yaml'
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                
            # Check for required sections
            required_sections = ['global_settings', 'agent_groups', 'lazy_loader', 'hybrid_llm_routing']
            missing_sections = [s for s in required_sections if s not in config]
            
            if missing_sections:
                self.issues['warning'].append(f"Config missing sections: {', '.join(missing_sections)}")
                
            # Count agents
            total_agents = sum(len(agents) for agents in config.get('agent_groups', {}).values())
            if total_agents != 77:
                self.issues['warning'].append(f"Expected 77 agents, found {total_agents}")
                
    def check_import_dependencies(self):
        """Check for missing Python imports"""
        print("\n📦 Checking import dependencies...")
        
        # Common imports that should be in requirements.txt
        required_imports = {
            'yaml': 'pyyaml',
            'flask': 'flask',
            'zmq': 'pyzmq',
            'prometheus_client': 'prometheus-client',
            'psutil': 'psutil',
            'aiohttp': 'aiohttp',
            'numpy': 'numpy',
            'pandas': 'pandas'
        }
        
        # Check requirements.txt
        req_path = self.new_repo / 'requirements.txt'
        if req_path.exists():
            with open(req_path) as f:
                requirements = f.read().lower()
                
            missing_deps = []
            for imp, pkg in required_imports.items():
                if pkg.lower() not in requirements:
                    missing_deps.append(pkg)
                    
            if missing_deps:
                self.issues['warning'].append(f"Possibly missing dependencies: {', '.join(missing_deps)}")
                
    def check_missing_utilities(self):
        """Check for missing utility files"""
        print("\n🔧 Checking utility files...")
        
        # Check if BaseAgent exists
        base_agent_locations = [
            'main_pc_code/agents/base_agent.py',
            'pc2_code/agents/base_agent.py',
            'src/utils/base_agent.py'
        ]
        
        base_agent_found = False
        for location in base_agent_locations:
            if (self.workspace / location).exists() or (self.new_repo / location).exists():
                base_agent_found = True
                break
                
        if not base_agent_found:
            self.issues['critical'].append("BaseAgent not found - this is required for all agents!")
            
    def check_port_allocations(self):
        """Check for port conflicts"""
        print("\n🔌 Checking port allocations...")
        
        # Load config and check ports
        config_path = self.new_repo / 'config/startup_config.yaml'
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                
            used_ports = set()
            duplicates = []
            
            for group_name, agents in config.get('agent_groups', {}).items():
                for agent_name, agent_config in agents.items():
                    port = agent_config.get('port')
                    if port:
                        if port in used_ports:
                            duplicates.append(f"{agent_name}: {port}")
                        used_ports.add(port)
                        
            if duplicates:
                self.issues['critical'].append(f"Port conflicts found: {', '.join(duplicates)}")
                
    def check_environment_variables(self):
        """Check for required environment variables"""
        print("\n🔐 Checking environment variables...")
        
        env_example = self.new_repo / '.env.example'
        if env_example.exists():
            with open(env_example) as f:
                env_content = f.read()
                
            # Check for critical variables
            critical_vars = ['PROFILE', 'UNIFIED_HOST', 'OBS_HUB_ENDPOINT']
            missing_vars = [v for v in critical_vars if v not in env_content]
            
            if missing_vars:
                self.issues['warning'].append(f"Missing critical env vars: {', '.join(missing_vars)}")
                
    def check_docker_compatibility(self):
        """Check Docker setup"""
        print("\n🐳 Checking Docker compatibility...")
        
        dockerfile = self.new_repo / 'Dockerfile'
        if dockerfile.exists():
            with open(dockerfile) as f:
                content = f.read()
                
            # Check for required elements
            checks = {
                'python:3': 'Python base image',
                'requirements.txt': 'Requirements installation',
                'EXPOSE': 'Port exposure',
                'HEALTHCHECK': 'Health check'
            }
            
            for pattern, desc in checks.items():
                if pattern not in content:
                    self.issues['warning'].append(f"Dockerfile missing: {desc}")
                    
    def check_test_coverage(self):
        """Check test coverage"""
        print("\n🧪 Checking test coverage...")
        
        test_dirs = ['tests/unit', 'tests/integration', 'tests/e2e']
        empty_dirs = []
        
        for test_dir in test_dirs:
            dir_path = self.new_repo / test_dir
            if dir_path.exists():
                # Check if directory has Python files
                py_files = list(dir_path.glob('*.py'))
                if not py_files:
                    empty_dirs.append(test_dir)
                    
        if empty_dirs:
            self.issues['info'].append(f"Empty test directories: {', '.join(empty_dirs)}")
            
    def check_documentation_references(self):
        """Check documentation references"""
        print("\n📚 Checking documentation references...")
        
        # Check if README has correct links
        readme = self.new_repo / 'README.md'
        if readme.exists():
            with open(readme) as f:
                content = f.read()
                
            # Check for broken internal links
            internal_links = re.findall(r'\[.*?\]\(((?!http).*?)\)', content)
            broken_links = []
            
            for link in internal_links:
                link_path = self.new_repo / link.strip('/')
                if not link_path.exists() and not link.startswith('#'):
                    broken_links.append(link)
                    
            if broken_links:
                self.issues['warning'].append(f"Broken documentation links: {', '.join(broken_links[:5])}")
                
    def check_security_issues(self):
        """Check for security issues"""
        print("\n🔒 Checking security issues...")
        
        # Check for hardcoded secrets
        patterns = [
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'Hardcoded API key'),
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret')
        ]
        
        files_to_check = list(self.new_repo.glob('**/*.py')) + list(self.new_repo.glob('**/*.yaml'))
        
        for file_path in files_to_check[:20]:  # Check first 20 files
            if '.env' not in str(file_path) and 'example' not in str(file_path):
                try:
                    with open(file_path) as f:
                        content = f.read().lower()
                        
                    for pattern, desc in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            self.issues['critical'].append(f"Security issue in {file_path.name}: {desc}")
                except:
                    pass
                    
    def print_scan_results(self):
        """Print scan results"""
        print("\n" + "=" * 80)
        print("DEEP SCAN RESULTS")
        print("=" * 80)
        
        # Critical issues
        if self.issues['critical']:
            print("\n❌ CRITICAL ISSUES:")
            for issue in self.issues['critical']:
                print(f"\n  • {issue}")
                
        # Warnings
        if self.issues['warning']:
            print("\n⚠️  WARNINGS:")
            for issue in self.issues['warning']:
                print(f"\n  • {issue}")
                
        # Info
        if self.issues['info']:
            print("\n📋 INFO:")
            for issue in self.issues['info']:
                print(f"\n  • {issue}")
                
        # Summary
        print("\n" + "=" * 80)
        total_issues = len(self.issues['critical']) + len(self.issues['warning'])
        
        if self.issues['critical']:
            print("❌ CRITICAL ISSUES FOUND - Must fix before deployment!")
        elif self.issues['warning']:
            print("⚠️  Some warnings found - Review recommended")
        else:
            print("✅ Deep scan passed - No critical issues found!")
            
        print(f"\nTotal: {len(self.issues['critical'])} critical, {len(self.issues['warning'])} warnings")
        print("=" * 80)

if __name__ == "__main__":
    scanner = DeepScanValidator()
    scanner.run_deep_scan()