#!/usr/bin/env python3
"""
Main-PC Done Definition Validator
Part of D. EXECUTION SCRIPT SKELETON

Validates the "E. DONE DEFINITION" criteria:
☑ Zero sys.path.insert left in main_pc_code/agents
☑ logging.basicConfig removed/replaced  
☑ python -m py_compile passes for all Python files
☑ Docker compose health checks (simulated)
"""

import os
import sys
import subprocess
import py_compile
import glob
from pathlib import Path
from typing import List, Tuple, Dict

class DoneDefinitionValidator:
    """Validates the completion criteria for Main-PC hardening"""
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
        self.results = {
            'sys_path_check': {'passed': 0, 'failed': 0, 'files': []},
            'logging_check': {'passed': 0, 'failed': 0, 'files': []},
            'compile_check': {'passed': 0, 'failed': 0, 'files': []},
            'health_check': {'passed': 0, 'failed': 0, 'groups': []}
        }
        self.errors = []
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in main_pc_code/agents"""
        pattern = str(self.workspace_path / "main_pc_code" / "**" / "*.py")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        
        # Also include common module files
        common_pattern = str(self.workspace_path / "common" / "**" / "*.py")
        files.extend([Path(f) for f in glob.glob(common_pattern, recursive=True)])
        
        return files
    
    def check_sys_path_insert(self) -> bool:
        """Check for remaining sys.path.insert statements"""
        print("🔍 Checking for sys.path.insert statements...")
        
        python_files = self.find_python_files()
        found_violations = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    if 'sys.path.insert' in line and not line.strip().startswith('#'):
                        found_violations.append((file_path, line_num, line.strip()))
                        
            except Exception as e:
                print(f"⚠️ Could not read {file_path}: {e}")
                continue
        
        if found_violations:
            self.results['sys_path_check']['failed'] = len(found_violations)
            self.results['sys_path_check']['files'] = found_violations
            print(f"❌ Found {len(found_violations)} sys.path.insert violations:")
            for file_path, line_num, line in found_violations:
                rel_path = file_path.relative_to(self.workspace_path)
                print(f"   {rel_path}:{line_num} - {line}")
            return False
        else:
            self.results['sys_path_check']['passed'] = len(python_files)
            print(f"✅ No sys.path.insert found in {len(python_files)} Python files")
            return True
    
    def check_logging_basicconfig(self) -> bool:
        """Check for remaining logging.basicConfig statements"""
        print("\n🔍 Checking for logging.basicConfig statements...")
        
        python_files = self.find_python_files()
        found_violations = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    if 'logging.basicConfig' in line and not line.strip().startswith('#'):
                        found_violations.append((file_path, line_num, line.strip()))
                        
            except Exception as e:
                print(f"⚠️ Could not read {file_path}: {e}")
                continue
        
        if found_violations:
            self.results['logging_check']['failed'] = len(found_violations)
            self.results['logging_check']['files'] = found_violations
            print(f"❌ Found {len(found_violations)} logging.basicConfig violations:")
            for file_path, line_num, line in found_violations:
                rel_path = file_path.relative_to(self.workspace_path)
                print(f"   {rel_path}:{line_num} - {line}")
            return False
        else:
            self.results['logging_check']['passed'] = len(python_files)
            print(f"✅ No logging.basicConfig found in {len(python_files)} Python files")
            return True
    
    def check_python_compilation(self) -> bool:
        """Check that all Python files compile successfully"""
        print("\n🔍 Checking Python file compilation...")
        
        python_files = self.find_python_files()
        compilation_errors = []
        compiled_count = 0
        
        for file_path in python_files:
            try:
                py_compile.compile(file_path, doraise=True)
                compiled_count += 1
            except py_compile.PyCompileError as e:
                compilation_errors.append((file_path, str(e)))
            except Exception as e:
                compilation_errors.append((file_path, f"Unexpected error: {str(e)}"))
        
        if compilation_errors:
            self.results['compile_check']['failed'] = len(compilation_errors)
            self.results['compile_check']['files'] = compilation_errors
            print(f"❌ Compilation failed for {len(compilation_errors)} files:")
            for file_path, error in compilation_errors:
                rel_path = file_path.relative_to(self.workspace_path)
                print(f"   {rel_path} - {error}")
            return False
        else:
            self.results['compile_check']['passed'] = compiled_count
            print(f"✅ All {compiled_count} Python files compiled successfully")
            return True
    
    def check_docker_health_configs(self) -> bool:
        """Check Docker health check configurations"""
        print("\n🔍 Checking Docker health check configurations...")
        
        docker_groups = [
            "infra_core", "coordination", "memory_stack", "language_stack",
            "reasoning_gpu", "learning_gpu", "vision_gpu", "speech_gpu",
            "translation_services", "emotion_system", "utility_cpu"
        ]
        
        healthy_groups = 0
        failed_groups = []
        
        for group in docker_groups:
            group_path = self.workspace_path / "docker" / group
            dockerfile_path = group_path / "Dockerfile"
            compose_path = group_path / "docker-compose.yml"
            
            has_dockerfile_health = False
            has_compose_health = False
            
            # Check Dockerfile for HEALTHCHECK
            if dockerfile_path.exists():
                try:
                    with open(dockerfile_path, 'r') as f:
                        dockerfile_content = f.read()
                    if 'HEALTHCHECK' in dockerfile_content:
                        has_dockerfile_health = True
                except Exception as e:
                    print(f"⚠️ Could not read {dockerfile_path}: {e}")
            
            # Check docker-compose.yml for healthcheck
            if compose_path.exists():
                try:
                    with open(compose_path, 'r') as f:
                        compose_content = f.read()
                    if 'healthcheck:' in compose_content:
                        has_compose_health = True
                except Exception as e:
                    print(f"⚠️ Could not read {compose_path}: {e}")
            
            if has_dockerfile_health or has_compose_health:
                healthy_groups += 1
                print(f"   ✅ {group} - Health checks configured")
            else:
                failed_groups.append(group)
                print(f"   ❌ {group} - No health checks found")
        
        if failed_groups:
            self.results['health_check']['failed'] = len(failed_groups)
            self.results['health_check']['groups'] = failed_groups
            return False
        else:
            self.results['health_check']['passed'] = healthy_groups
            print(f"✅ Health checks configured for all {healthy_groups} Docker groups")
            return True
    
    def check_canonical_imports(self) -> bool:
        """Check that canonical imports are being used"""
        print("\n🔍 Checking canonical import usage...")
        
        python_files = [f for f in self.find_python_files() if 'agents' in str(f)]
        canonical_usage = 0
        files_with_canonical = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for canonical logging import
                if 'from common.utils.log_setup import configure_logging' in content:
                    canonical_usage += 1
                    files_with_canonical.append(file_path)
                    
            except Exception as e:
                print(f"⚠️ Could not read {file_path}: {e}")
                continue
        
        agent_files = len(python_files)
        print(f"✅ Found canonical logging in {canonical_usage}/{agent_files} agent files")
        
        if canonical_usage > 0:
            return True
        else:
            print("⚠️ No canonical logging usage found")
            return False
    
    def run_all_checks(self) -> bool:
        """Run all done definition checks"""
        print("🎯 Main-PC Done Definition Validation")
        print("=" * 50)
        
        checks = [
            ("Zero sys.path.insert", self.check_sys_path_insert),
            ("No logging.basicConfig", self.check_logging_basicconfig), 
            ("Python compilation", self.check_python_compilation),
            ("Docker health checks", self.check_docker_health_configs),
            ("Canonical imports", self.check_canonical_imports)
        ]
        
        passed_checks = 0
        total_checks = len(checks)
        
        for check_name, check_func in checks:
            print(f"\n{'='*20} {check_name} {'='*20}")
            try:
                if check_func():
                    passed_checks += 1
                    print(f"✅ {check_name} - PASSED")
                else:
                    print(f"❌ {check_name} - FAILED")
            except Exception as e:
                print(f"💥 {check_name} - ERROR: {e}")
                self.errors.append((check_name, str(e)))
        
        return self.generate_final_report(passed_checks, total_checks)
    
    def generate_final_report(self, passed_checks: int, total_checks: int) -> bool:
        """Generate the final validation report"""
        print("\n" + "=" * 50)
        print("📊 DONE DEFINITION VALIDATION REPORT")
        print("=" * 50)
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Checks Passed: {passed_checks}/{total_checks}")
        print(f"   Success Rate: {(passed_checks/total_checks*100):.1f}%")
        
        # Detailed results
        print(f"\n📋 DETAILED RESULTS:")
        
        for check_name, results in self.results.items():
            if results['passed'] > 0 or results['failed'] > 0:
                status = "✅ PASS" if results['failed'] == 0 else "❌ FAIL"
                print(f"   {check_name}: {status} (Passed: {results['passed']}, Failed: {results['failed']})")
        
        if self.errors:
            print(f"\n💥 ERRORS ENCOUNTERED:")
            for check_name, error in self.errors:
                print(f"   - {check_name}: {error}")
        
        # Final determination
        all_passed = passed_checks == total_checks and len(self.errors) == 0
        
        if all_passed:
            print(f"\n🎉 ALL DONE DEFINITION CRITERIA MET!")
            print("✅ Main-PC hardening is complete and ready for deployment")
            return True
        else:
            print(f"\n❌ DONE DEFINITION CRITERIA NOT FULLY MET")
            print("🔧 Please address the issues above before considering hardening complete")
            return False

def main():
    """Main execution function"""
    workspace = os.environ.get('WORKSPACE_PATH', '/workspace')
    validator = DoneDefinitionValidator(workspace)
    
    try:
        success = validator.run_all_checks()
        
        if success:
            print("\n✅ Done Definition validation completed successfully")
            sys.exit(0)
        else:
            print("\n❌ Done Definition validation failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()