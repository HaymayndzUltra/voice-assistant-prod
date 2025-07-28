#!/usr/bin/env python3
"""
Comprehensive test for lazy loading functionality.
Tests both the lazy_loader module and the underlying agent_helpers lazy_import.
"""

import sys
import time
import traceback
from typing import List, Dict, Any

def print_header(title: str):
    """Print a formatted test header."""
    print(f"\n{'='*50}")
    print(f"🧪 {title}")
    print(f"{'='*50}")

def print_section(title: str):
    """Print a formatted test section."""
    print(f"\n📋 {title}")
    print("-" * 30)

def assert_lazy_loaded(name: str) -> bool:
    """Assert that a module is properly registered as lazy."""
    try:
        assert name in sys.modules, f"{name} not in sys.modules after enable()"
        module = sys.modules[name]
        assert hasattr(module, "__getattr__"), f"{name} is not a LazyModule proxy"
        assert hasattr(module, "_load"), f"{name} missing _load method"
        print(f"✅ {name} is registered as a lazy module")
        return True
    except AssertionError as e:
        print(f"❌ {name} lazy registration failed: {e}")
        return False

def assert_real_import(name: str, attr: str) -> bool:
    """Assert that a module is fully loaded after attribute access."""
    try:
        module = __import__(name)
        value = getattr(module, attr)
        assert not hasattr(module, "__getattr__"), f"{name} is still lazy after usage"
        print(f"✅ {name} is fully loaded after accessing {attr}")
        return True
    except AssertionError as e:
        print(f"❌ {name} real import failed: {e}")
        return False

def test_recursion_edge_cases() -> Dict[str, bool]:
    """Test edge cases that might cause recursion."""
    print_section("Testing Recursion Edge Cases")
    
    results = {}
    
    # Test 1: Multiple rapid attribute accesses
    try:
        import math
        for i in range(10):
            _ = math.sqrt(i)
        results["rapid_access"] = True
        print("✅ Rapid attribute access test passed")
    except RecursionError:
        results["rapid_access"] = False
        print("❌ Rapid attribute access caused recursion")
    except Exception as e:
        results["rapid_access"] = False
        print(f"❌ Rapid attribute access failed: {e}")
    
    # Test 2: Nested attribute access
    try:
        import json
        data = json.dumps({"nested": {"deep": {"value": 42}}})
        parsed = json.loads(data)
        results["nested_access"] = True
        print("✅ Nested attribute access test passed")
    except RecursionError:
        results["nested_access"] = False
        print("❌ Nested attribute access caused recursion")
    except Exception as e:
        results["nested_access"] = False
        print(f"❌ Nested attribute access failed: {e}")
    
    # Test 3: Module reload scenario
    try:
        import random
        # Simulate module reload scenario
        if "random" in sys.modules:
            del sys.modules["random"]
        import random
        _ = random.randint(1, 100)
        results["reload_scenario"] = True
        print("✅ Module reload scenario test passed")
    except RecursionError:
        results["reload_scenario"] = False
        print("❌ Module reload scenario caused recursion")
    except Exception as e:
        results["reload_scenario"] = False
        print(f"❌ Module reload scenario failed: {e}")
    
    return results

def test_lazy_loader_basic() -> Dict[str, bool]:
    """Test basic lazy loader functionality."""
    print_section("Testing Basic Lazy Loader")
    
    results = {}
    
    # Clear any existing imports
    for mod in ["math", "json", "random"]:
        if mod in sys.modules:
            del sys.modules[mod]
    
    # Enable lazy loading
    from common_utils.lazy_loader import enable
    enable(["math", "json", "random"])
    
    # Stage 1: Check lazy registration
    for mod in ["math", "json", "random"]:
        results[f"lazy_{mod}"] = assert_lazy_loaded(mod)
    
    # Stage 2: Trigger actual use
    try:
        import math
        _ = math.sqrt(16)
        results["real_math"] = assert_real_import("math", "sqrt")
    except Exception as e:
        results["real_math"] = False
        print(f"❌ Math real import failed: {e}")
    
    try:
        import json
        _ = json.dumps({"hello": "world"})
        results["real_json"] = assert_real_import("json", "dumps")
    except Exception as e:
        results["real_json"] = False
        print(f"❌ JSON real import failed: {e}")
    
    try:
        import random
        _ = random.randint(1, 10)
        results["real_random"] = assert_real_import("random", "randint")
    except Exception as e:
        results["real_random"] = False
        print(f"❌ Random real import failed: {e}")
    
    return results

def test_agent_helpers_direct() -> Dict[str, bool]:
    """Test agent_helpers lazy_import directly."""
    print_section("Testing Agent Helpers Direct Import")
    
    results = {}
    
    # Clear any existing imports
    for mod in ["os", "datetime"]:
        if mod in sys.modules:
            del sys.modules[mod]
    
    # Test direct lazy_import
    from common_utils.agent_helpers import lazy_import
    
    try:
        os = lazy_import("os")
        assert hasattr(os, "__getattr__"), "os should be lazy"
        path = os.path.join("/tmp", "test")
        # ✅ FIX: Check sys.modules instead of the variable
        real_os = sys.modules["os"]
        assert not hasattr(real_os, "__getattr__"), "os in sys.modules should be real after use"
        results["direct_os"] = True
        print("✅ Direct lazy_import(os) test passed")
    except Exception as e:
        results["direct_os"] = False
        print(f"❌ Direct lazy_import(os) failed: {e}")
    
    try:
        dt = lazy_import("datetime")
        assert hasattr(dt, "__getattr__"), "datetime should be lazy"
        now = dt.datetime.now()
        # ✅ FIX: Check sys.modules instead of the variable
        real_dt = sys.modules["datetime"]
        assert not hasattr(real_dt, "__getattr__"), "datetime in sys.modules should be real after use"
        results["direct_datetime"] = True
        print("✅ Direct lazy_import(datetime) test passed")
    except Exception as e:
        results["direct_datetime"] = False
        print(f"❌ Direct lazy_import(datetime) failed: {e}")
    
    return results

def print_summary(all_results: Dict[str, Dict[str, bool]]):
    """Print test summary."""
    print_header("Test Summary")
    
    total_tests = 0
    passed_tests = 0
    
    for test_name, results in all_results.items():
        print(f"\n📊 {test_name}:")
        for test_key, passed in results.items():
            total_tests += 1
            if passed:
                passed_tests += 1
                print(f"  ✅ {test_key}")
            else:
                print(f"  ❌ {test_key}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("🎉 All tests passed! Lazy loading is working perfectly.")
    elif success_rate >= 80:
        print("⚠️  Most tests passed, but there are some issues to investigate.")
    else:
        print("🚨 Many tests failed. Lazy loading needs attention.")

def main():
    """Run all tests."""
    print_header("Lazy Loading Comprehensive Test Suite")
    
    start_time = time.time()
    all_results = {}
    
    try:
        # Test 1: Basic lazy loader
        all_results["Basic Lazy Loader"] = test_lazy_loader_basic()
        
        # Test 2: Recursion edge cases
        all_results["Recursion Edge Cases"] = test_recursion_edge_cases()
        
        # Test 3: Direct agent_helpers testing
        all_results["Direct Agent Helpers"] = test_agent_helpers_direct()
        
    except Exception as e:
        print(f"❌ Test suite failed with exception: {e}")
        traceback.print_exc()
        return 1
    
    execution_time = time.time() - start_time
    
    # Print summary
    print_summary(all_results)
    
    print(f"\n⏱️  Total execution time: {execution_time:.3f}s")
    
    # Return appropriate exit code
    total_tests = sum(len(results) for results in all_results.values())
    passed_tests = sum(sum(1 for passed in results.values() if passed) 
                      for results in all_results.values())
    
    return 0 if passed_tests == total_tests else 1

if __name__ == "__main__":
    exit(main())
