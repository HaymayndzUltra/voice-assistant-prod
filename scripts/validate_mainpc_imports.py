#!/usr/bin/env python3
"""
Main-PC Import Validation Script
Part of D. EXECUTION SCRIPT SKELETON

Validates that all critical imports work correctly across the system
Tests canonical helpers, BaseAgent patterns, and key dependencies
"""

import sys
import os
import importlib
import traceback
from pathlib import Path
from typing import List, Tuple, Dict

# Ensure proper path setup
sys.path.insert(0, '/workspace')
sys.path.insert(0, '/app')
os.environ['PYTHONPATH'] = '/workspace:/app'

class ImportValidator:
    """Validates critical imports for Main-PC system"""
    
    def __init__(self):
        self.results: Dict[str, List[Tuple[str, bool, str]]] = {
            'core_dependencies': [],
            'canonical_helpers': [],
            'base_agents': [],
            'agent_specific': []
        }
        self.failed_imports = []
        
    def test_import(self, module_name: str, category: str, description: str = "") -> bool:
        """Test a single import and record results"""
        try:
            importlib.import_module(module_name)
            self.results[category].append((module_name, True, description))
            print(f"✓ {module_name} - {description}")
            return True
        except ImportError as e:
            error_msg = str(e)
            self.results[category].append((module_name, False, f"{description} - {error_msg}"))
            self.failed_imports.append((module_name, error_msg))
            print(f"✗ {module_name} - {description} - FAILED: {error_msg}")
            return False
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.results[category].append((module_name, False, f"{description} - {error_msg}"))
            self.failed_imports.append((module_name, error_msg))
            print(f"✗ {module_name} - {description} - ERROR: {error_msg}")
            return False
    
    def test_core_dependencies(self):
        """Test core system dependencies"""
        print("\n🔧 Testing Core Dependencies")
        print("=" * 40)
        
        self.test_import('zmq', 'core_dependencies', 'ZeroMQ messaging')
        self.test_import('redis', 'core_dependencies', 'Redis client')
        self.test_import('yaml', 'core_dependencies', 'YAML parser')
        self.test_import('json', 'core_dependencies', 'JSON parser')
        self.test_import('logging', 'core_dependencies', 'Python logging')
        self.test_import('threading', 'core_dependencies', 'Threading support')
        self.test_import('asyncio', 'core_dependencies', 'Async I/O')
        self.test_import('pydantic', 'core_dependencies', 'Data validation')
        self.test_import('aiohttp', 'core_dependencies', 'Async HTTP client')
        self.test_import('numpy', 'core_dependencies', 'Numerical computing')
        
    def test_canonical_helpers(self):
        """Test canonical helper modules"""
        print("\n🛠️ Testing Canonical Helpers")
        print("=" * 40)
        
        # Path manager
        self.test_import('common.utils.path_manager', 'canonical_helpers', 'Path management')
        
        # Configuration
        self.test_import('common.config_manager', 'canonical_helpers', 'Configuration management')
        
        # Environment standardizer
        self.test_import('common.utils.env_standardizer', 'canonical_helpers', 'Environment standardization')
        
        # Logging setup (our new canonical module)
        self.test_import('common.utils.log_setup', 'canonical_helpers', 'Canonical logging setup')
        
        # Error publisher
        self.test_import('main_pc_code.agents.error_publisher', 'canonical_helpers', 'Error publishing')
        
        # ZMQ pools
        self.test_import('common.pools.zmq_pool', 'canonical_helpers', 'ZMQ connection pooling')
        
        # Service discovery
        self.test_import('main_pc_code.utils.service_discovery_client', 'canonical_helpers', 'Service discovery')
        
    def test_base_agents(self):
        """Test BaseAgent and core agent infrastructure"""
        print("\n👥 Testing Base Agent Infrastructure")
        print("=" * 40)
        
        # Base agent
        self.test_import('common.core.base_agent', 'base_agents', 'BaseAgent template')
        
        # Data models
        self.test_import('common.utils.data_models', 'base_agents', 'Common data models')
        
        # Error handling
        self.test_import('common_utils.error_handling', 'base_agents', 'Error handling utilities')
        
    def test_specific_functionality(self):
        """Test specific functionality from canonical helpers"""
        print("\n🧪 Testing Specific Functionality")
        print("=" * 40)
        
        # Test canonical logging function
        try:
            from common.utils.log_setup import configure_logging
            logger = configure_logging(__name__, log_to_file=False)
            logger.info("Test log message")
            self.results['agent_specific'].append(('configure_logging', True, 'Canonical logging function'))
            print("✓ configure_logging function works correctly")
        except Exception as e:
            self.results['agent_specific'].append(('configure_logging', False, f'Function test failed: {e}'))
            print(f"✗ configure_logging function failed: {e}")
            
        # Test BaseAgent instantiation
        try:
            from common.core.base_agent import BaseAgent
            # Don't actually instantiate to avoid port conflicts
            assert hasattr(BaseAgent, '__init__')
            assert hasattr(BaseAgent, 'start')
            assert hasattr(BaseAgent, 'stop')
            self.results['agent_specific'].append(('BaseAgent', True, 'BaseAgent class structure'))
            print("✓ BaseAgent class structure validated")
        except Exception as e:
            self.results['agent_specific'].append(('BaseAgent', False, f'Class validation failed: {e}'))
            print(f"✗ BaseAgent class validation failed: {e}")
            
        # Test error publisher function
        try:
            from main_pc_code.agents.error_publisher import create_mainpc_error_publisher
            # Just test that the function exists and can be imported
            assert callable(create_mainpc_error_publisher)
            self.results['agent_specific'].append(('create_mainpc_error_publisher', True, 'Error publisher function'))
            print("✓ create_mainpc_error_publisher function available")
        except Exception as e:
            self.results['agent_specific'].append(('create_mainpc_error_publisher', False, f'Function test failed: {e}'))
            print(f"✗ create_mainpc_error_publisher function failed: {e}")
    
    def test_gpu_dependencies(self):
        """Test GPU-specific dependencies (optional)"""
        print("\n🚀 Testing GPU Dependencies (Optional)")
        print("=" * 40)
        
        # PyTorch
        try:
            import torch
            version = torch.__version__
            self.results['agent_specific'].append(('torch', True, f'PyTorch version {version}'))
            print(f"✓ PyTorch {version} available")
            
            # Test CUDA availability
            if torch.cuda.is_available():
                print(f"✓ CUDA available: {torch.cuda.device_count()} devices")
            else:
                print("ℹ CUDA not available (CPU-only environment)")
                
        except ImportError:
            self.results['agent_specific'].append(('torch', False, 'PyTorch not available'))
            print("ℹ PyTorch not available (expected in some environments)")
            
        # TensorFlow
        try:
            import tensorflow as tf
            version = tf.__version__
            self.results['agent_specific'].append(('tensorflow', True, f'TensorFlow version {version}'))
            print(f"✓ TensorFlow {version} available")
        except ImportError:
            self.results['agent_specific'].append(('tensorflow', False, 'TensorFlow not available'))
            print("ℹ TensorFlow not available (expected in some environments)")
    
    def run_all_tests(self):
        """Run all import validation tests"""
        print("🔍 Main-PC Import Validation")
        print("=" * 50)
        
        self.test_core_dependencies()
        self.test_canonical_helpers()
        self.test_base_agents()
        self.test_specific_functionality()
        self.test_gpu_dependencies()
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate final validation report"""
        print("\n" + "=" * 50)
        print("📊 IMPORT VALIDATION REPORT")
        print("=" * 50)
        
        total_tests = 0
        total_passed = 0
        
        for category, tests in self.results.items():
            if not tests:
                continue
                
            passed = sum(1 for _, success, _ in tests if success)
            total = len(tests)
            total_tests += total
            total_passed += passed
            
            print(f"\n{category.replace('_', ' ').title()}:")
            print(f"  ✅ Passed: {passed}/{total}")
            
            # Show failed imports for this category
            failed_in_category = [(name, desc) for name, success, desc in tests if not success]
            if failed_in_category:
                print(f"  ❌ Failed:")
                for name, desc in failed_in_category:
                    print(f"    - {name}: {desc}")
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {(total_passed/total_tests*100):.1f}%")
        
        if self.failed_imports:
            print(f"\n❌ CRITICAL FAILURES ({len(self.failed_imports)}):")
            for module, error in self.failed_imports:
                print(f"   - {module}: {error}")
            return False
        else:
            print(f"\n🎉 ALL CRITICAL IMPORTS SUCCESSFUL!")
            return True

def main():
    """Main execution function"""
    validator = ImportValidator()
    
    try:
        success = validator.run_all_tests()
        
        if success:
            print("\n✅ Import validation completed successfully")
            print("🚀 Main-PC system imports are ready for deployment")
            sys.exit(0)
        else:
            print("\n❌ Import validation failed")
            print("🔧 Please resolve import issues before deployment")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Validation script failed with unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()