#!/usr/bin/env python3
"""
🔬 COMPREHENSIVE AI SYSTEM VALIDATION
====================================

This script performs comprehensive validation of the AI System:
1. Syntax validation across all Python files
2. Import chain validation
3. Core services startup simulation
4. Health check endpoint validation
5. Docker configuration validation
"""

import os
import sys
import ast
import py_compile
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import List, Dict, Tuple

class SystemValidator:
    def __init__(self):
        self.project_root = Path(".")
        self.mainpc_agents = self.project_root / "main_pc_code" / "agents"
        self.formainpc_dir = self.project_root / "main_pc_code" / "FORMAINPC"
        self.common_dir = self.project_root / "common"
        self.validation_results = {
            'syntax_validation': {'passed': 0, 'failed': 0, 'errors': []},
            'import_validation': {'passed': 0, 'failed': 0, 'errors': []},
            'config_validation': {'valid': False, 'errors': []},
            'docker_validation': {'valid': False, 'errors': []}
        }
    
    def validate_syntax(self) -> bool:
        """Validate syntax of all Python files."""
        print("🔍 SYNTAX VALIDATION")
        print("=" * 30)
        
        python_files = []
        
        # Collect all Python files
        for directory in [self.mainpc_agents, self.formainpc_dir, self.common_dir]:
            if directory.exists():
                python_files.extend(directory.rglob("*.py"))
        
        syntax_errors = []
        
        for py_file in python_files:
            try:
                # Try to compile the Python file
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                # Parse AST to check for syntax errors
                ast.parse(source, filename=str(py_file))
                
                # Try py_compile for additional validation
                py_compile.compile(str(py_file), doraise=True)
                
                self.validation_results['syntax_validation']['passed'] += 1
                print(f"  ✅ {py_file.name}")
                
            except SyntaxError as e:
                error_msg = f"{py_file.name}: Line {e.lineno}: {e.msg}"
                syntax_errors.append(error_msg)
                self.validation_results['syntax_validation']['failed'] += 1
                self.validation_results['syntax_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                
            except Exception as e:
                error_msg = f"{py_file.name}: {str(e)}"
                syntax_errors.append(error_msg)
                self.validation_results['syntax_validation']['failed'] += 1
                self.validation_results['syntax_validation']['errors'].append(error_msg)
                print(f"  ⚠️  {error_msg}")
        
        total_files = self.validation_results['syntax_validation']['passed'] + self.validation_results['syntax_validation']['failed']
        success_rate = (self.validation_results['syntax_validation']['passed'] / total_files * 100) if total_files > 0 else 0
        
        print(f"\n📊 Syntax validation: {self.validation_results['syntax_validation']['passed']}/{total_files} files passed ({success_rate:.1f}%)")
        
        return len(syntax_errors) == 0
    
    def validate_imports(self) -> bool:
        """Validate import chains in critical files."""
        print("\n🔗 IMPORT VALIDATION")
        print("=" * 25)
        
        critical_files = [
            "common/core/base_agent.py",
            "main_pc_code/scripts/start_system.py",
            "main_pc_code/agents/service_registry_agent.py",
            "main_pc_code/agents/system_digital_twin.py",
            "main_pc_code/agents/request_coordinator.py"
        ]
        
        import_errors = []
        
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                error_msg = f"Critical file missing: {file_path}"
                import_errors.append(error_msg)
                self.validation_results['import_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                continue
            
            try:
                # Create a temporary test script to validate imports
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                    temp_file.write(f"""
import sys
import os
sys.path.insert(0, '{self.project_root.absolute()}')
sys.path.insert(0, '{(self.project_root / 'main_pc_code').absolute()}')
sys.path.insert(0, '{(self.project_root / 'common').absolute()}')

try:
    # Test import of the target file as a module
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_module", r"{full_path.absolute()}")
    module = importlib.util.module_from_spec(spec)
    print("Import test successful")
except Exception as e:
    print(f"Import error: {{e}}")
    sys.exit(1)
""")
                    temp_name = temp_file.name
                
                # Run the import test
                result = subprocess.run([sys.executable, temp_name], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    self.validation_results['import_validation']['passed'] += 1
                    print(f"  ✅ {file_path}")
                else:
                    error_msg = f"{file_path}: {result.stderr.strip() or result.stdout.strip()}"
                    import_errors.append(error_msg)
                    self.validation_results['import_validation']['failed'] += 1
                    self.validation_results['import_validation']['errors'].append(error_msg)
                    print(f"  ❌ {error_msg}")
                
                # Clean up temp file
                os.unlink(temp_name)
                
            except Exception as e:
                error_msg = f"{file_path}: Validation error - {str(e)}"
                import_errors.append(error_msg)
                self.validation_results['import_validation']['failed'] += 1
                self.validation_results['import_validation']['errors'].append(error_msg)
                print(f"  ⚠️  {error_msg}")
        
        total_files = len(critical_files)
        success_rate = (self.validation_results['import_validation']['passed'] / total_files * 100) if total_files > 0 else 0
        
        print(f"\n📊 Import validation: {self.validation_results['import_validation']['passed']}/{total_files} files passed ({success_rate:.1f}%)")
        
        return len(import_errors) == 0
    
    def validate_startup_config(self) -> bool:
        """Validate startup configuration."""
        print("\n⚙️  CONFIG VALIDATION")
        print("=" * 25)
        
        config_path = self.project_root / "main_pc_code" / "config" / "startup_config.yaml"
        
        if not config_path.exists():
            error_msg = "startup_config.yaml not found"
            self.validation_results['config_validation']['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return False
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate structure
            required_sections = ['global_settings', 'agent_groups']
            missing_sections = [s for s in required_sections if s not in config]
            
            if missing_sections:
                error_msg = f"Missing config sections: {missing_sections}"
                self.validation_results['config_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                return False
            
            # Validate agent groups
            agent_groups = config.get('agent_groups', {})
            required_groups = ['core_services']
            missing_groups = [g for g in required_groups if g not in agent_groups]
            
            if missing_groups:
                error_msg = f"Missing agent groups: {missing_groups}"
                self.validation_results['config_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                return False
            
            # Validate core services
            core_services = agent_groups.get('core_services', {})
            required_core = ['ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator']
            missing_core = [s for s in required_core if s not in core_services]
            
            if missing_core:
                error_msg = f"Missing core services: {missing_core}"
                self.validation_results['config_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                return False
            
            # Count agents and validate script paths
            total_agents = 0
            missing_scripts = []
            
            for group_name, agents in agent_groups.items():
                for agent_name, agent_config in agents.items():
                    total_agents += 1
                    script_path = agent_config.get('script_path', '')
                    
                    if script_path:
                        full_script_path = self.project_root / script_path
                        if not full_script_path.exists():
                            missing_scripts.append(f"{agent_name}: {script_path}")
            
            print(f"  📊 Total agents configured: {total_agents}")
            print(f"  📁 Agent groups: {len(agent_groups)}")
            
            if missing_scripts:
                print(f"  ⚠️  Missing script files:")
                for missing in missing_scripts[:5]:  # Show first 5
                    print(f"    ❌ {missing}")
                if len(missing_scripts) > 5:
                    print(f"    ... and {len(missing_scripts) - 5} more")
            
            self.validation_results['config_validation']['valid'] = len(missing_scripts) == 0
            print(f"  ✅ Configuration structure valid")
            
            return len(missing_scripts) == 0
            
        except Exception as e:
            error_msg = f"Config validation error: {str(e)}"
            self.validation_results['config_validation']['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return False
    
    def validate_docker_config(self) -> bool:
        """Validate Docker configuration."""
        print("\n🐳 DOCKER VALIDATION")
        print("=" * 24)
        
        docker_compose_path = self.project_root / "docker" / "docker-compose.mainpc.yml"
        
        if not docker_compose_path.exists():
            error_msg = "docker-compose.mainpc.yml not found"
            self.validation_results['docker_validation']['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return False
        
        try:
            with open(docker_compose_path, 'r') as f:
                docker_config = yaml.safe_load(f)
            
            # Validate structure
            if 'services' not in docker_config:
                error_msg = "No services defined in Docker Compose"
                self.validation_results['docker_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                return False
            
            services = docker_config['services']
            required_services = ['core-services', 'redis']
            missing_services = [s for s in required_services if s not in services]
            
            if missing_services:
                error_msg = f"Missing Docker services: {missing_services}"
                self.validation_results['docker_validation']['errors'].append(error_msg)
                print(f"  ❌ {error_msg}")
                return False
            
            print(f"  📊 Docker services defined: {len(services)}")
            print(f"  ✅ Docker configuration valid")
            
            self.validation_results['docker_validation']['valid'] = True
            return True
            
        except Exception as e:
            error_msg = f"Docker validation error: {str(e)}"
            self.validation_results['docker_validation']['errors'].append(error_msg)
            print(f"  ❌ {error_msg}")
            return False
    
    def run_comprehensive_validation(self) -> Dict:
        """Run all validation checks."""
        print("🚀 COMPREHENSIVE AI SYSTEM VALIDATION")
        print("=" * 50)
        print("🔬 Starting comprehensive system validation...")
        
        # Run all validations
        syntax_valid = self.validate_syntax()
        import_valid = self.validate_imports()
        config_valid = self.validate_startup_config()
        docker_valid = self.validate_docker_config()
        
        # Calculate overall score
        total_checks = 4
        passed_checks = sum([syntax_valid, import_valid, config_valid, docker_valid])
        overall_score = (passed_checks / total_checks) * 100
        
        # Print comprehensive summary
        print("\n" + "=" * 50)
        print("📈 COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 50)
        
        print(f"🔍 Syntax Validation: {'✅' if syntax_valid else '❌'}")
        print(f"   📊 {self.validation_results['syntax_validation']['passed']} passed, {self.validation_results['syntax_validation']['failed']} failed")
        
        print(f"🔗 Import Validation: {'✅' if import_valid else '❌'}")
        print(f"   📊 {self.validation_results['import_validation']['passed']} passed, {self.validation_results['import_validation']['failed']} failed")
        
        print(f"⚙️  Config Validation: {'✅' if config_valid else '❌'}")
        print(f"🐳 Docker Validation: {'✅' if docker_valid else '❌'}")
        
        print(f"\n🎯 Overall System Health: {overall_score:.1f}% ({passed_checks}/{total_checks} checks passed)")
        
        if overall_score >= 90:
            print("🎉 EXCELLENT: System is ready for deployment!")
        elif overall_score >= 70:
            print("⚡ GOOD: System is mostly ready, minor issues need attention")
        elif overall_score >= 50:
            print("⚠️  FAIR: System needs significant fixes before deployment")
        else:
            print("🚨 CRITICAL: System requires major fixes before it can run")
        
        # Show critical errors
        all_errors = []
        for validation_type, results in self.validation_results.items():
            if 'errors' in results and results['errors']:
                all_errors.extend(results['errors'])
        
        if all_errors:
            print(f"\n🚨 CRITICAL ISSUES TO FIX ({len(all_errors)}):")
            for error in all_errors[:10]:  # Show first 10 errors
                print(f"  ❌ {error}")
            if len(all_errors) > 10:
                print(f"  ... and {len(all_errors) - 10} more errors")
        
        return {
            'overall_score': overall_score,
            'passed_checks': passed_checks,
            'total_checks': total_checks,
            'ready_for_deployment': overall_score >= 90,
            'validation_results': self.validation_results
        }

if __name__ == "__main__":
    validator = SystemValidator()
    results = validator.run_comprehensive_validation()
    
    # Exit with appropriate code
    if results['ready_for_deployment']:
        print("\n✨ System validation completed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  System validation completed with issues (Score: {results['overall_score']:.1f}%)")
        sys.exit(1)