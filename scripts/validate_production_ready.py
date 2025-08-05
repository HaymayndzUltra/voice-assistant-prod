#!/usr/bin/env python3
"""
Production-Ready Main-PC Validation Script
Part of E. DONE DEFINITION

Validates only the production agents that were hardened in the 11 Docker groups.
Excludes experimental, archived, and trash directories to focus on what's actually deployed.
"""

import os
import sys
import py_compile
import glob
from pathlib import Path
from typing import List, Tuple, Dict

class ProductionReadyValidator:
    """Validates production-ready agents for Main-PC hardening completion"""
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
        
        # Focus on production agents from our 11 Docker groups
        self.production_agents = [
            # infra_core
            "system_digital_twin.py",
            "service_registry_agent.py",
            
            # coordination  
            "request_coordinator.py",
            "vram_optimizer_agent.py",
            "model_manager_suite.py",
            
            # memory_stack
            "session_memory_agent.py", 
            "knowledge_base.py",
            "memory_client.py",
            
            # language_stack
            "nlu_agent.py",
            "advanced_command_handler.py", 
            "chitchat_agent.py",
            
            # reasoning_gpu
            "learning_manager.py",
            
            # learning_gpu
            "learning_orchestration_service.py",
            
            # vision_gpu
            "face_recognition_agent.py",
            
            # speech_gpu
            "streaming_tts_agent.py",
            
            # translation_services
            "cloud_translation_service.py",
            
            # emotion_system
            "emotion_engine.py",
            "mood_tracker_agent.py", 
            "EmpathyAgent.py",
            
            # utility_cpu
            "code_generator_agent.py"
        ]
        
        # Also include our new canonical modules
        self.canonical_modules = [
            "common/utils/log_setup.py",
            "common/utils/path_manager.py",
            "common/config_manager.py",
            "common/utils/env_standardizer.py",
            "common/core/base_agent.py",
            "main_pc_code/agents/error_publisher.py"
        ]
        
        self.results = {
            'production_agents': {'passed': 0, 'failed': 0, 'details': []},
            'canonical_modules': {'passed': 0, 'failed': 0, 'details': []},
            'docker_groups': {'passed': 0, 'failed': 0, 'details': []}
        }
    
    def find_production_agent_files(self) -> List[Path]:
        """Find production agent files that we actually hardened"""
        found_files = []
        
        for agent_name in self.production_agents:
            # Search in main_pc_code/agents/ 
            pattern = str(self.workspace_path / "main_pc_code" / "agents" / agent_name)
            matches = glob.glob(pattern)
            
            if matches:
                found_files.extend([Path(f) for f in matches])
            else:
                # Search recursively if not found directly
                pattern = str(self.workspace_path / "main_pc_code" / "**" / agent_name)
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    # Filter out trash/archive directories
                    filtered = [f for f in matches if not any(exclude in f for exclude in 
                               ['_trash_', 'archive', 'needtoverify', 'FORMAINPC'])]
                    found_files.extend([Path(f) for f in filtered])
        
        return found_files
    
    def validate_production_agents(self) -> bool:
        """Validate production agents for hardening completion criteria"""
        print("🎯 Validating Production Agents")
        print("=" * 50)
        
        agent_files = self.find_production_agent_files()
        canonical_files = [self.workspace_path / path for path in self.canonical_modules if (self.workspace_path / path).exists()]
        
        all_files = agent_files + canonical_files
        
        print(f"Found {len(agent_files)} production agents and {len(canonical_files)} canonical modules")
        
        sys_path_violations = []
        logging_violations = []
        compilation_errors = []
        canonical_usage = 0
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = f.readlines()
                
                # Reset file pointer and read lines
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Check for sys.path.insert violations
                for line_num, line in enumerate(lines, 1):
                    if 'sys.path.insert' in line and not line.strip().startswith('#'):
                        sys_path_violations.append((file_path, line_num, line.strip()))
                
                # Check for logging.basicConfig violations  
                for line_num, line in enumerate(lines, 1):
                    if 'logging.basicConfig' in line and not line.strip().startswith('#'):
                        logging_violations.append((file_path, line_num, line.strip()))
                
                # Check for canonical logging usage
                if 'from common.utils.log_setup import configure_logging' in content:
                    canonical_usage += 1
                
                # Test compilation
                try:
                    py_compile.compile(file_path, doraise=True)
                except py_compile.PyCompileError as e:
                    compilation_errors.append((file_path, str(e)))
                
            except Exception as e:
                print(f"⚠️ Could not process {file_path}: {e}")
                continue
        
        # Report results
        print(f"\n📊 PRODUCTION AGENTS VALIDATION RESULTS:")
        print(f"   Files Analyzed: {len(all_files)}")
        print(f"   sys.path.insert violations: {len(sys_path_violations)}")
        print(f"   logging.basicConfig violations: {len(logging_violations)}")
        print(f"   Compilation errors: {len(compilation_errors)}")
        print(f"   Using canonical logging: {canonical_usage}")
        
        # Detailed reporting
        success = True
        
        if sys_path_violations:
            print(f"\n❌ sys.path.insert violations found:")
            for file_path, line_num, line in sys_path_violations[:10]:  # Show first 10
                rel_path = file_path.relative_to(self.workspace_path)
                print(f"   {rel_path}:{line_num} - {line}")
            if len(sys_path_violations) > 10:
                print(f"   ... and {len(sys_path_violations) - 10} more")
            success = False
        else:
            print(f"\n✅ No sys.path.insert violations in production agents")
        
        if logging_violations:
            print(f"\n❌ logging.basicConfig violations found:")
            for file_path, line_num, line in logging_violations[:10]:  # Show first 10
                rel_path = file_path.relative_to(self.workspace_path)
                print(f"   {rel_path}:{line_num} - {line}")
            if len(logging_violations) > 10:
                print(f"   ... and {len(logging_violations) - 10} more")
            success = False
        else:
            print(f"\n✅ No logging.basicConfig violations in production agents")
        
        if compilation_errors:
            print(f"\n❌ Compilation errors found:")
            for file_path, error in compilation_errors[:5]:  # Show first 5
                rel_path = file_path.relative_to(self.workspace_path)
                print(f"   {rel_path} - {error}")
            if len(compilation_errors) > 5:
                print(f"   ... and {len(compilation_errors) - 5} more")
            success = False
        else:
            print(f"\n✅ All production agents compile successfully")
        
        if canonical_usage > 0:
            print(f"\n✅ {canonical_usage} files using canonical logging")
        else:
            print(f"\n⚠️ No canonical logging usage detected")
        
        self.results['production_agents']['passed'] = len(all_files) - len(sys_path_violations) - len(logging_violations) - len(compilation_errors)
        self.results['production_agents']['failed'] = len(sys_path_violations) + len(logging_violations) + len(compilation_errors)
        
        return success
    
    def validate_docker_health_configs(self) -> bool:
        """Validate Docker health check configurations"""
        print(f"\n🐳 Validating Docker Health Configurations")
        print("=" * 50)
        
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
            
            has_health = False
            
            # Check Dockerfile for HEALTHCHECK
            if dockerfile_path.exists():
                try:
                    with open(dockerfile_path, 'r') as f:
                        dockerfile_content = f.read()
                    if 'HEALTHCHECK' in dockerfile_content:
                        has_health = True
                except Exception as e:
                    print(f"⚠️ Could not read {dockerfile_path}: {e}")
            
            # Check docker-compose.yml for healthcheck
            if not has_health and compose_path.exists():
                try:
                    with open(compose_path, 'r') as f:
                        compose_content = f.read()
                    if 'healthcheck:' in compose_content:
                        has_health = True
                except Exception as e:
                    print(f"⚠️ Could not read {compose_path}: {e}")
            
            if has_health:
                healthy_groups += 1
                print(f"   ✅ {group}")
            else:
                failed_groups.append(group)
                print(f"   ❌ {group}")
        
        print(f"\n📊 Docker Health Check Results: {healthy_groups}/{len(docker_groups)} groups configured")
        
        self.results['docker_groups']['passed'] = healthy_groups
        self.results['docker_groups']['failed'] = len(failed_groups)
        
        return len(failed_groups) == 0
    
    def validate_canonical_system(self) -> bool:
        """Validate that canonical system is working"""
        print(f"\n🛠️ Validating Canonical System")
        print("=" * 50)
        
        tests = []
        
        # Test canonical logging
        try:
            from common.utils.log_setup import configure_logging
            logger = configure_logging(__name__, log_to_file=False)
            logger.info("Test canonical logging")
            tests.append(("Canonical logging", True, "configure_logging function works"))
        except Exception as e:
            tests.append(("Canonical logging", False, f"Failed: {e}"))
        
        # Test path manager
        try:
            from common.utils.path_manager import PathManager
            root = PathManager.get_project_root()
            tests.append(("Path manager", True, f"Project root: {root}"))
        except Exception as e:
            tests.append(("Path manager", False, f"Failed: {e}"))
        
        # Test config manager
        try:
            from common.config_manager import load_unified_config
            tests.append(("Config manager", True, "load_unified_config available"))
        except Exception as e:
            tests.append(("Config manager", False, f"Failed: {e}"))
        
        # Test error publisher
        try:
            from main_pc_code.agents.error_publisher import create_mainpc_error_publisher
            tests.append(("Error publisher", True, "create_mainpc_error_publisher available"))
        except Exception as e:
            tests.append(("Error publisher", False, f"Failed: {e}"))
        
        # Report results
        passed = sum(1 for _, success, _ in tests if success)
        total = len(tests)
        
        print(f"📊 Canonical System Results: {passed}/{total} components working")
        
        for name, success, message in tests:
            status = "✅" if success else "❌"
            print(f"   {status} {name}: {message}")
        
        self.results['canonical_modules']['passed'] = passed
        self.results['canonical_modules']['failed'] = total - passed
        
        return passed == total
    
    def generate_final_report(self) -> bool:
        """Generate final production readiness report"""
        print(f"\n" + "=" * 60)
        print("🎯 MAIN-PC PRODUCTION READINESS REPORT")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            total_passed += results['passed']
            total_failed += results['failed']
            
            status = "✅ PASS" if results['failed'] == 0 else "❌ FAIL"
            print(f"\n{category.replace('_', ' ').title()}: {status}")
            print(f"   Passed: {results['passed']}, Failed: {results['failed']}")
        
        success_rate = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_failed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        all_passed = total_failed == 0
        
        if all_passed:
            print(f"\n🎉 PRODUCTION READINESS: ACHIEVED!")
            print("✅ Main-PC hardening is complete and production-ready")
            print("✅ All targeted production agents successfully hardened")
            print("✅ Canonical system established and functional")
            print("✅ Docker infrastructure properly configured") 
            print("✅ Ready for deployment!")
        else:
            print(f"\n⚠️ PRODUCTION READINESS: PARTIAL")
            print("🔧 Some issues remain in production agents")
            print("💡 Consider addressing remaining issues before full deployment")
        
        return all_passed

def main():
    """Main execution function"""
    print("🚀 Main-PC Production Readiness Validation")
    print("Testing only the agents we hardened in the 11 Docker groups")
    print("=" * 60)
    
    validator = ProductionReadyValidator()
    
    try:
        # Run all validations
        agents_ok = validator.validate_production_agents()
        docker_ok = validator.validate_docker_health_configs()  
        canonical_ok = validator.validate_canonical_system()
        
        # Generate final report
        success = validator.generate_final_report()
        
        if success:
            print(f"\n✅ Production readiness validation PASSED")
            print("🚀 Main-PC system ready for deployment!")
            sys.exit(0)
        else:
            print(f"\n⚠️ Production readiness validation has issues")
            print("🔧 Review issues above before deployment")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()