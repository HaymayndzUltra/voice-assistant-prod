#!/usr/bin/env python3

import sys
import time
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Function timed out")

print("🧪 Testing Option #10 Hang Fix")
print("=" * 35)

# Test 1: Check if the fix works
print("1️⃣ Testing with timeout protection...")

try:
    # Set timeout for 30 seconds
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)
    
    from workflow_memory_intelligence_fixed import execute_task_intelligently
    
    test_task = "Test hang fix with timeout protection"
    print(f"   Executing: {test_task}")
    
    start_time = time.time()
    result = execute_task_intelligently(test_task)
    end_time = time.time()
    
    # Cancel timeout
    signal.alarm(0)
    
    print(f"   ✅ Execution completed in {end_time - start_time:.2f} seconds")
    print(f"   Status: {result.get('status', 'unknown')}")
    print(f"   Task ID: {result.get('task_id', 'unknown')}")
    print(f"   TODOs added: {result.get('todos_added', 'unknown')}")
    
    if result.get('status') == 'completed':
        print("   🎉 SUCCESS: Option #10 is working!")
    else:
        print(f"   ⚠️  Issue: {result.get('error', 'Unknown error')}")
        
except TimeoutError:
    print("   ❌ TIMEOUT: Option #10 is still hanging")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n🎯 Test completed!") 