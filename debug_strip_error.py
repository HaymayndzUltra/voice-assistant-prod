#!/usr/bin/env python3
"""Debug script to identify exactly where the strip error is happening"""

import logging
import traceback
from workflow_memory_intelligence_fixed import execute_task_intelligently

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

def debug_test():
    """Test task execution with detailed error tracking"""
    
    # Simple test case
    test_task = "Create a simple login system"
    
    print("Starting debug test...")
    print(f"Task: {test_task}")
    
    try:
        result = execute_task_intelligently(test_task)
        print(f"Result: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"ERROR TYPE: {type(e)}")
        print("FULL TRACEBACK:")
        traceback.print_exc()

if __name__ == "__main__":
    debug_test()
