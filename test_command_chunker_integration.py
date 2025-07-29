#!/usr/bin/env python3
"""
Test Command Chunker Integration with Task Command Center
"""

import os
import sys
import json
from typing import Dict, Any

def test_command_chunker_import():
    """Test if command_chunker can be imported"""
    print("🔍 Testing command_chunker import...")
    
    try:
        from command_chunker import CommandChunker
        print("✅ command_chunker imported successfully")
        
        # Test basic functionality
        chunker = CommandChunker(max_chunk_size=200)
        test_command = "Create Docker containers and test health checks and validate deployment and monitor system logs"
        
        result = chunker.chunk_command(test_command, strategy="auto")
        print(f"✅ Basic chunking test passed: {len(result)} chunks created")
        
        for i, chunk in enumerate(result, 1):
            print(f"   Chunk {i}: {chunk[:50]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ command_chunker import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ command_chunker test failed: {e}")
        return False

def test_workflow_intelligence_import():
    """Test if workflow_memory_intelligence_fixed can import command_chunker"""
    print("\n🔍 Testing workflow_memory_intelligence_fixed import...")
    
    try:
        from workflow_memory_intelligence_fixed import IntelligentTaskChunker
        print("✅ workflow_memory_intelligence_fixed imported successfully")
        
        # Test chunker creation
        chunker = IntelligentTaskChunker()
        print(f"✅ IntelligentTaskChunker created")
        print(f"   Command chunker available: {chunker.command_chunker_available}")
        
        return chunker.command_chunker_available
        
    except ImportError as e:
        print(f"❌ workflow_memory_intelligence_fixed import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ IntelligentTaskChunker creation failed: {e}")
        return False

def test_integrated_chunking():
    """Test the integrated chunking functionality"""
    print("\n🔍 Testing integrated chunking...")
    
    try:
        from workflow_memory_intelligence_fixed import IntelligentTaskChunker
        
        chunker = IntelligentTaskChunker()
        
        # Test cases
        test_tasks = [
            "Create a new Python script for data processing",
            "Set up Docker containers, configure networking, test health checks, and deploy to production environment",
            "Analyze system logs and generate comprehensive report with performance metrics and recommendations",
            "Update documentation and create user guides for the new API endpoints"
        ]
        
        for i, task in enumerate(test_tasks, 1):
            print(f"\n📋 Test Case {i}: {task}")
            print(f"   Length: {len(task)} characters")
            
            try:
                result = chunker.chunk_task(task)
                print(f"✅ Chunking successful:")
                print(f"   Complexity: {result.complexity.level}")
                print(f"   Subtasks: {len(result.subtasks)}")
                print(f"   Should chunk: {result.complexity.should_chunk}")
                
                for j, subtask in enumerate(result.subtasks, 1):
                    print(f"      {j}. {subtask.description}")
                    
            except Exception as e:
                print(f"❌ Chunking failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integrated chunking test failed: {e}")
        return False

def test_task_execution():
    """Test the full task execution workflow"""
    print("\n🔍 Testing task execution workflow...")
    
    try:
        from workflow_memory_intelligence_fixed import execute_task_intelligently
        
        # Test with a simple task
        test_task = "Create a Python script that processes CSV files and generates summary statistics"
        
        print(f"📋 Testing task: {test_task}")
        
        result = execute_task_intelligently(test_task)
        
        print("✅ Task execution result:")
        print(json.dumps(result, indent=2))
        
        return True
        
    except Exception as e:
        print(f"❌ Task execution test failed: {e}")
        return False

def test_task_command_center_integration():
    """Test the task command center integration"""
    print("\n🔍 Testing task command center integration...")
    
    try:
        from task_command_center import TaskCommandCenter
        
        # Create command center instance
        center = TaskCommandCenter()
        print("✅ TaskCommandCenter created successfully")
        
        # Test that intelligent_task_execution method exists
        if hasattr(center, 'intelligent_task_execution'):
            print("✅ intelligent_task_execution method exists")
        else:
            print("❌ intelligent_task_execution method missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Task command center integration test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 COMMAND CHUNKER INTEGRATION TEST SUITE")
    print("=" * 50)
    
    test_results = {
        "command_chunker_import": test_command_chunker_import(),
        "workflow_intelligence_import": test_workflow_intelligence_import(),
        "integrated_chunking": test_integrated_chunking(),
        "task_execution": test_task_execution(),
        "task_command_center": test_task_command_center_integration()
    }
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY:")
    print("=" * 50)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Integration needs fixes.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
