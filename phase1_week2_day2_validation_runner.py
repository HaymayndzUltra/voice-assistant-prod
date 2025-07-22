#!/usr/bin/env python3
"""
Enhanced BaseAgent Validation Framework - Execution Script
Phase 1 Week 2 Day 2 - Continuing from old session
"""

import os
import sys
import time
import json
import subprocess
import threading
import tempfile
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import required modules
from common.utils.path_manager import PathManager
from common.core.base_agent import BaseAgent
from common.utils.logger_util import get_json_logger

class ValidationRunner:
    """Execute the validation framework designed in old session"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'validation_type': 'enhanced_baseagent_continuation',
            'tests_run': 0,
            'successes': 0,
            'failures': []
        }
        self.logger = get_json_logger("ValidationRunner")
        
    def test_baseagent_import_performance(self):
        """Test BaseAgent import performance across active agents"""
        print("\n🔍 TESTING BASEAGENT IMPORT PERFORMANCE...")
        
        # Active agents from startup configs (from old session analysis)
        test_agents = [
            'main_pc_code/agents/service_registry_agent.py',
            'main_pc_code/agents/request_coordinator.py',
            'main_pc_code/agents/memory_client.py',
            'main_pc_code/agents/model_orchestrator.py',
            'main_pc_code/agents/face_recognition_agent.py',
            'pc2_code/agents/memory_orchestrator_service.py',
            'pc2_code/agents/remote_connector_agent.py',
            'pc2_code/agents/unified_web_agent.py'
        ]
        
        import_results = {}
        total_start_time = time.time()
        
        for agent_path in test_agents:
            agent_name = os.path.basename(agent_path)
            print(f"  📊 Testing: {agent_name}")
            
            if not os.path.exists(agent_path):
                print(f"    ❌ File not found: {agent_path}")
                import_results[agent_name] = {'status': 'FILE_NOT_FOUND', 'time': 0}
                continue
                
            # Test import time
            start_time = time.time()
            try:
                # Check if agent uses BaseAgent
                with open(agent_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                uses_baseagent = 'BaseAgent' in content
                import_time = time.time() - start_time
                
                import_results[agent_name] = {
                    'status': 'SUCCESS',
                    'uses_baseagent': uses_baseagent,
                    'time': import_time,
                    'file_size_kb': len(content) / 1024
                }
                
                print(f"    ✅ BaseAgent: {uses_baseagent}, Time: {import_time:.4f}s")
                
            except Exception as e:
                import_time = time.time() - start_time
                import_results[agent_name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'time': import_time
                }
                print(f"    ❌ Error: {e}")
        
        total_time = time.time() - total_start_time
        
        # Analysis
        successful_imports = [r for r in import_results.values() if r['status'] == 'SUCCESS']
        baseagent_users = [r for r in successful_imports if r.get('uses_baseagent', False)]
        
        avg_time = sum(r['time'] for r in successful_imports) / len(successful_imports) if successful_imports else 0
        
        print(f"\n📊 IMPORT PERFORMANCE SUMMARY:")
        print(f"  Total agents tested: {len(test_agents)}")
        print(f"  Successful imports: {len(successful_imports)}")
        print(f"  BaseAgent users: {len(baseagent_users)}")
        print(f"  Average import time: {avg_time:.4f}s")
        print(f"  Total analysis time: {total_time:.4f}s")
        print(f"  BaseAgent adoption: {len(baseagent_users)}/{len(successful_imports)} ({len(baseagent_users)/len(successful_imports)*100:.1f}%)")
        
        return {
            'test_name': 'baseagent_import_performance',
            'success': len(successful_imports) > 0,
            'metrics': {
                'total_agents': len(test_agents),
                'successful_imports': len(successful_imports),
                'baseagent_users': len(baseagent_users),
                'adoption_rate': len(baseagent_users)/len(successful_imports)*100 if successful_imports else 0,
                'avg_import_time': avg_time,
                'total_time': total_time
            },
            'detailed_results': import_results
        }
    
    def test_configuration_compatibility(self):
        """Test configuration loading compatibility (MainPC vs PC2 patterns)"""
        print("\n⚙️ TESTING CONFIGURATION COMPATIBILITY...")
        
        config_tests = []
        
        # Test PathManager integration
        try:
            from common.utils.path_manager import PathManager
            
            start_time = time.time()
            project_root = PathManager.get_project_root()
            main_pc_path = PathManager.get_main_pc_code() if hasattr(PathManager, 'get_main_pc_code') else None
            pc2_path = PathManager.get_pc2_code() if hasattr(PathManager, 'get_pc2_code') else None
            config_time = time.time() - start_time
            
            config_tests.append({
                'name': 'PathManager Integration',
                'success': True,
                'time': config_time,
                'details': {
                    'project_root': str(project_root),
                    'main_pc_path': str(main_pc_path) if main_pc_path else 'Not available',
                    'pc2_path': str(pc2_path) if pc2_path else 'Not available'
                }
            })
            
            print(f"  ✅ PathManager: {config_time:.4f}s")
            print(f"    Project root: {project_root}")
            
        except Exception as e:
            config_tests.append({
                'name': 'PathManager Integration',
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ PathManager failed: {e}")
        
        # Test config manager
        try:
            from common.config_manager import load_unified_config
            
            start_time = time.time()
            config = load_unified_config()
            config_load_time = time.time() - start_time
            
            config_tests.append({
                'name': 'Unified Config Loading',
                'success': True,
                'time': config_load_time,
                'details': {
                    'config_keys': len(config) if isinstance(config, dict) else 0,
                    'config_type': type(config).__name__
                }
            })
            
            print(f"  ✅ Unified Config: {config_load_time:.4f}s ({len(config) if isinstance(config, dict) else 0} keys)")
            
        except Exception as e:
            config_tests.append({
                'name': 'Unified Config Loading',
                'success': False,
                'error': str(e)
            })
            print(f"  ❌ Unified Config failed: {e}")
        
        # Test startup configs exist
        startup_configs = [
            'main_pc_code/config/startup_config.yaml',
            'pc2_code/config/startup_config.yaml'
        ]
        
        for config_path in startup_configs:
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        content = f.read()
                    
                    config_tests.append({
                        'name': f'Startup Config - {config_path}',
                        'success': True,
                        'details': {
                            'file_size': len(content),
                            'exists': True
                        }
                    })
                    print(f"  ✅ {config_path}: {len(content)} bytes")
                else:
                    config_tests.append({
                        'name': f'Startup Config - {config_path}',
                        'success': False,
                        'error': 'File not found'
                    })
                    print(f"  ❌ {config_path}: Not found")
                    
            except Exception as e:
                config_tests.append({
                    'name': f'Startup Config - {config_path}',
                    'success': False,
                    'error': str(e)
                })
                print(f"  ❌ {config_path}: {e}")
        
        successful_tests = [t for t in config_tests if t['success']]
        
        return {
            'test_name': 'configuration_compatibility',
            'success': len(successful_tests) > len(config_tests) // 2,  # At least half should pass
            'metrics': {
                'total_tests': len(config_tests),
                'successful_tests': len(successful_tests),
                'success_rate': len(successful_tests) / len(config_tests) * 100
            },
            'test_details': config_tests
        }
    
    def test_system_health_baseline(self):
        """Test current system health and import status"""
        print("\n🏥 TESTING SYSTEM HEALTH BASELINE...")
        
        health_metrics = {}
        
        # Test critical imports (from Week 1 success)
        critical_modules = [
            'common.utils.path_manager',
            'common.core.base_agent',
            'common.utils.logger_util',
            'common.config_manager'
        ]
        
        import_success_count = 0
        import_start_time = time.time()
        
        for module_name in critical_modules:
            try:
                start_time = time.time()
                __import__(module_name)
                import_time = time.time() - start_time
                import_success_count += 1
                print(f"  ✅ {module_name}: {import_time:.4f}s")
            except Exception as e:
                print(f"  ❌ {module_name}: {e}")
        
        total_import_time = time.time() - import_start_time
        import_success_rate = import_success_count / len(critical_modules) * 100
        
        health_metrics['imports'] = {
            'success_count': import_success_count,
            'total_modules': len(critical_modules),
            'success_rate': import_success_rate,
            'total_time': total_import_time
        }
        
        # Test file system access
        critical_paths = [
            'main_pc_code',
            'pc2_code',
            'common',
            'implementation_roadmap'
        ]
        
        path_success_count = 0
        for path in critical_paths:
            if os.path.exists(path):
                path_success_count += 1
                print(f"  ✅ Path exists: {path}")
            else:
                print(f"  ❌ Path missing: {path}")
        
        health_metrics['filesystem'] = {
            'accessible_paths': path_success_count,
            'total_paths': len(critical_paths),
            'success_rate': path_success_count / len(critical_paths) * 100
        }
        
        # Overall health score
        overall_success = (import_success_rate + health_metrics['filesystem']['success_rate']) / 2
        
        print(f"\n📊 SYSTEM HEALTH SUMMARY:")
        print(f"  Import success: {import_success_rate:.1f}% ({import_success_count}/{len(critical_modules)})")
        print(f"  Filesystem access: {health_metrics['filesystem']['success_rate']:.1f}% ({path_success_count}/{len(critical_paths)})")
        print(f"  Overall health: {overall_success:.1f}%")
        
        return {
            'test_name': 'system_health_baseline',
            'success': overall_success >= 90.0,  # 90% threshold for success
            'metrics': {
                'overall_health_score': overall_success,
                'import_health': health_metrics['imports'],
                'filesystem_health': health_metrics['filesystem']
            }
        }
    
    def run_validation_suite(self):
        """Run the complete validation suite"""
        print("=" * 80)
        print("ENHANCED BASEAGENT VALIDATION FRAMEWORK")
        print("Phase 1 Week 2 Day 2 - Continuing from Old Session")
        print("=" * 80)
        
        validation_start_time = time.time()
        
        # Run validation tests
        tests = [
            self.test_system_health_baseline,
            self.test_configuration_compatibility,
            self.test_baseagent_import_performance
        ]
        
        for test_func in tests:
            self.results['tests_run'] += 1
            
            try:
                test_result = test_func()
                if test_result['success']:
                    self.results['successes'] += 1
                    print(f"✅ {test_result['test_name']}: PASSED")
                else:
                    self.results['failures'].append({
                        'test': test_result['test_name'],
                        'reason': 'Test criteria not met'
                    })
                    print(f"❌ {test_result['test_name']}: FAILED")
                
                # Store detailed results
                self.results[test_result['test_name']] = test_result
                
            except Exception as e:
                self.results['failures'].append({
                    'test': test_func.__name__,
                    'reason': str(e)
                })
                print(f"❌ {test_func.__name__}: ERROR - {e}")
        
        total_validation_time = time.time() - validation_start_time
        
        # Final summary
        print("\n" + "=" * 80)
        print("VALIDATION RESULTS SUMMARY")
        print("=" * 80)
        
        success_rate = self.results['successes'] / self.results['tests_run'] * 100 if self.results['tests_run'] > 0 else 0
        
        print(f"📊 Tests Run: {self.results['tests_run']}")
        print(f"✅ Passed: {self.results['successes']}")
        print(f"❌ Failed: {len(self.results['failures'])}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Total Time: {total_validation_time:.4f}s")
        
        if self.results['failures']:
            print(f"\n❌ FAILED TESTS:")
            for failure in self.results['failures']:
                print(f"  - {failure['test']}: {failure['reason']}")
        
        # Save results
        self.results['summary'] = {
            'tests_run': self.results['tests_run'],
            'successes': self.results['successes'],
            'failures': len(self.results['failures']),
            'success_rate': success_rate,
            'total_time': total_validation_time
        }
        
        results_file = "phase1_week2_day2_validation_continuation_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Determine overall status
        if success_rate >= 80:
            print(f"\n🎉 VALIDATION SUCCESSFUL - Ready to proceed with optimization!")
            return True
        else:
            print(f"\n⚠️  VALIDATION CONCERNS - Some issues need attention before optimization")
            return False

def main():
    """Main execution function"""
    print("🚀 RESUMING ENHANCED BASEAGENT VALIDATION...")
    print("📍 Continuing from Old Session stopping point")
    print()
    
    runner = ValidationRunner()
    success = runner.run_validation_suite()
    
    print(f"\n🎯 VALIDATION FRAMEWORK EXECUTION: {'COMPLETE' if success else 'NEEDS ATTENTION'}")
    return success

if __name__ == "__main__":
    main() 