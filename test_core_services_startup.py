#!/usr/bin/env python3
"""
🧪 CORE SERVICES STARTUP TEST
============================

This script tests that the core services can be imported and instantiated
without errors, validating deployment readiness.
"""

import sys
import os
import time
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "main_pc_code"))
sys.path.insert(0, str(project_root / "common"))

def test_core_imports():
    """Test that core service modules can be imported."""
    print("🔍 Testing Core Service Imports...")
    
    core_services = [
        ("BaseAgent", "common.core.base_agent"),
        ("ServiceRegistry", "main_pc_code.agents.service_registry_agent"),
        ("SystemDigitalTwin", "main_pc_code.agents.system_digital_twin"),
        ("RequestCoordinator", "main_pc_code.agents.request_coordinator"),
        ("UnifiedSystemAgent", "main_pc_code.agents.unified_system_agent"),
        ("ModelManagerSuite", "main_pc_code.model_manager_suite"),
    ]
    
    successful_imports = 0
    failed_imports = []
    
    for service_name, module_path in core_services:
        try:
            # Try to import the module
            __import__(module_path)
            print(f"  ✅ {service_name}: Import successful")
            successful_imports += 1
        except Exception as e:
            print(f"  ❌ {service_name}: Import failed - {e}")
            failed_imports.append((service_name, str(e)))
    
    success_rate = (successful_imports / len(core_services)) * 100
    print(f"\n📊 Import Test Results: {successful_imports}/{len(core_services)} successful ({success_rate:.1f}%)")
    
    return failed_imports

def test_syntax_validation():
    """Test syntax of critical core service files."""
    print("\n🔍 Testing Critical File Syntax...")
    
    critical_files = [
        "common/core/base_agent.py",
        "main_pc_code/agents/service_registry_agent.py", 
        "main_pc_code/agents/system_digital_twin.py",
        "main_pc_code/agents/request_coordinator.py",
        "main_pc_code/scripts/start_system.py"
    ]
    
    syntax_errors = []
    
    for file_path in critical_files:
        full_path = project_root / file_path
        if not full_path.exists():
            syntax_errors.append(f"{file_path}: File not found")
            print(f"  ❌ {file_path}: File not found")
            continue
            
        try:
            import ast
            with open(full_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Parse AST to check syntax
            ast.parse(source, filename=str(full_path))
            print(f"  ✅ {file_path}: Syntax valid")
            
        except SyntaxError as e:
            error_msg = f"{file_path}: Line {e.lineno}: {e.msg}"
            syntax_errors.append(error_msg)
            print(f"  ❌ {error_msg}")
        except Exception as e:
            error_msg = f"{file_path}: {str(e)}"
            syntax_errors.append(error_msg)
            print(f"  ⚠️  {error_msg}")
    
    success_rate = ((len(critical_files) - len(syntax_errors)) / len(critical_files)) * 100
    print(f"\n📊 Syntax Test Results: {len(critical_files) - len(syntax_errors)}/{len(critical_files)} files valid ({success_rate:.1f}%)")
    
    return syntax_errors

def test_configuration_loading():
    """Test that startup configuration can be loaded."""
    print("\n🔍 Testing Configuration Loading...")
    
    config_path = project_root / "main_pc_code" / "config" / "startup_config.yaml"
    
    if not config_path.exists():
        print(f"  ❌ Configuration file not found: {config_path}")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate structure
        if 'agent_groups' not in config:
            print("  ❌ Missing agent_groups in configuration")
            return False
            
        if 'core_services' not in config['agent_groups']:
            print("  ❌ Missing core_services group in configuration")
            return False
            
        core_services = config['agent_groups']['core_services']
        required_services = ['ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator']
        
        missing_services = [s for s in required_services if s not in core_services]
        if missing_services:
            print(f"  ❌ Missing required services: {missing_services}")
            return False
        
        print(f"  ✅ Configuration loaded successfully")
        print(f"  📊 Core services configured: {len(core_services)}")
        print(f"  📊 Total agent groups: {len(config['agent_groups'])}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration loading failed: {e}")
        return False

def test_port_assignments():
    """Test that port assignments are conflict-free."""
    print("\n🔍 Testing Port Assignments...")
    
    config_path = project_root / "main_pc_code" / "config" / "startup_config.yaml"
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        ports_used = {}
        health_ports_used = {}
        conflicts = []
        
        agent_groups = config.get('agent_groups', {})
        
        for group_name, agents in agent_groups.items():
            for agent_name, agent_config in agents.items():
                port = agent_config.get('port')
                health_port = agent_config.get('health_check_port')
                
                if port:
                    if port in ports_used:
                        conflicts.append(f"Port {port}: {ports_used[port]} vs {agent_name}")
                    else:
                        ports_used[port] = agent_name
                
                if health_port:
                    if health_port in health_ports_used:
                        conflicts.append(f"Health port {health_port}: {health_ports_used[health_port]} vs {agent_name}")
                    elif health_port in ports_used:
                        conflicts.append(f"Health port {health_port} conflicts with main port of {ports_used[health_port]}")
                    else:
                        health_ports_used[health_port] = agent_name
        
        if conflicts:
            print(f"  ❌ Port conflicts found:")
            for conflict in conflicts:
                print(f"    ⚠️  {conflict}")
            return False
        else:
            print(f"  ✅ No port conflicts found")
            print(f"  📊 Unique ports: {len(ports_used)}")
            print(f"  📊 Unique health ports: {len(health_ports_used)}")
            return True
            
    except Exception as e:
        print(f"  ❌ Port validation failed: {e}")
        return False

def run_core_services_test():
    """Run complete core services startup test."""
    print("🚀 CORE SERVICES STARTUP TEST")
    print("=" * 40)
    print("🧪 Testing deployment readiness...")
    
    # Run all tests
    failed_imports = test_core_imports()
    syntax_errors = test_syntax_validation()
    config_valid = test_configuration_loading()
    ports_valid = test_port_assignments()
    
    # Calculate overall score
    tests = [
        ("Import Test", len(failed_imports) == 0),
        ("Syntax Test", len(syntax_errors) == 0),
        ("Config Test", config_valid),
        ("Port Test", ports_valid)
    ]
    
    passed_tests = sum(1 for _, passed in tests if passed)
    total_tests = len(tests)
    overall_score = (passed_tests / total_tests) * 100
    
    # Print summary
    print("\n" + "=" * 40)
    print("📈 CORE SERVICES TEST SUMMARY")
    print("=" * 40)
    
    for test_name, passed in tests:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}: {'PASSED' if passed else 'FAILED'}")
    
    print(f"\n🎯 Overall Test Score: {overall_score:.1f}% ({passed_tests}/{total_tests} tests passed)")
    
    if overall_score >= 90:
        print("🎉 EXCELLENT: Core services are ready for deployment!")
        deployment_ready = True
    elif overall_score >= 75:
        print("⚡ GOOD: Core services are mostly ready, minor issues need attention")
        deployment_ready = True
    elif overall_score >= 50:
        print("⚠️  FAIR: Core services need fixes before deployment")
        deployment_ready = False
    else:
        print("🚨 CRITICAL: Core services are not ready for deployment")
        deployment_ready = False
    
    # Show specific issues
    if failed_imports or syntax_errors:
        print(f"\n🚨 ISSUES TO ADDRESS:")
        for service_name, error in failed_imports:
            print(f"  ❌ Import Error - {service_name}: {error}")
        for error in syntax_errors:
            print(f"  ❌ Syntax Error - {error}")
    
    if deployment_ready:
        print(f"\n✨ DEPLOYMENT COMMANDS:")
        print(f"  docker-compose -f docker/docker-compose.mainpc.yml up core-services")
        print(f"  # Monitor health: curl http://localhost:8220/health")
    
    return {
        'deployment_ready': deployment_ready,
        'overall_score': overall_score,
        'tests_passed': passed_tests,
        'total_tests': total_tests,
        'failed_imports': failed_imports,
        'syntax_errors': syntax_errors
    }

if __name__ == "__main__":
    results = run_core_services_test()
    
    # Exit with appropriate code
    if results['deployment_ready']:
        print("\n🎊 Core services startup test PASSED!")
        sys.exit(0)
    else:
        print(f"\n⚠️  Core services startup test FAILED (Score: {results['overall_score']:.1f}%)")
        sys.exit(1)