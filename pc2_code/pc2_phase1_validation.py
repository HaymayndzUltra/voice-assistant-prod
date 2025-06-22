#!/usr/bin/env python3
"""
PC2 Phase 1 - Core Agents Implementation Validation
Test & Validate workflow for all four core agents
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

def run_agent_test(agent_name, test_script):
    """Run individual agent test and return result"""
    print(f"\n{'='*60}")
    print(f"Testing {agent_name}...")
    print(f"{'='*60}")
    
    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, test_script],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout per test
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print(f"✗ {agent_name} test TIMEOUT")
        return False, "", "Test timed out after 30 seconds"
    except Exception as e:
        print(f"✗ {agent_name} test FAILED with exception: {str(e)}")
        return False, "", str(e)

def main():
    """Main validation function"""
    print("PC2 Phase 1 - Core Agents Implementation Validation")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Define agents to test
    agents = [
        ("TieredResponder", "test_tiered_responder.py"),
        ("AsyncProcessor", "test_async_processor.py"),
        ("CacheManager", "test_cache_manager.py"),
        ("PerformanceMonitor", "test_performance_monitor.py")
    ]
    
    results = []
    all_passed = True
    
    # Test each agent
    for agent_name, test_script in agents:
        success, stdout, stderr = run_agent_test(agent_name, test_script)
        results.append((agent_name, success, stdout, stderr))
        
        if not success:
            all_passed = False
            print(f"\nFAILED: {agent_name} FAILED - Stopping validation sequence")
            break
    
    # Print final report
    print(f"\n{'='*60}")
    print("PC2 Phase 1 Validation Report")
    print(f"{'='*60}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if all_passed:
        print("SUCCESS: PC2 Phase 1 Complete. All four agents were validated successfully.")
        print()
        print("Validated Agents:")
        for agent_name, success, _, _ in results:
            print(f"  SUCCESS: {agent_name}")
        return 0
    else:
        print("FAILED: PC2 Phase 1 FAILED")
        print()
        print("Failed Agents:")
        for agent_name, success, stdout, stderr in results:
            if not success:
                print(f"  FAILED: {agent_name}")
                if stderr:
                    print(f"    Error: {stderr}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 