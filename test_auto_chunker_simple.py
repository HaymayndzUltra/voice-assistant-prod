#!/usr/bin/env python3
"""
Simple test for auto-chunker integration
"""

def test_auto_chunker():
    print("🚀 Testing auto-chunker integration...")
    
    # Test 1: Auto-detect chunker standalone
    try:
        from auto_detect_chunker import AutoDetectChunker
        chunker = AutoDetectChunker()
        
        test_text = "Create Docker containers and configure networking and test health checks and validate deployment and monitor system performance"
        chunks, analysis = chunker.auto_chunk(test_text)
        
        print(f"✅ Auto-chunker works: {len(chunks)} chunks created")
        print(f"   Strategy: {analysis['strategy_used']}")
        print(f"   Optimal size: {analysis['optimal_chunk_size']}")
        
    except Exception as e:
        print(f"❌ Auto-chunker failed: {e}")
        return False
    
    # Test 2: Workflow integration
    try:
        from workflow_memory_intelligence_fixed import IntelligentTaskChunker
        workflow_chunker = IntelligentTaskChunker()
        
        print(f"✅ Workflow chunker created")
        print(f"   Auto-chunker available: {workflow_chunker.auto_chunker_available}")
        
        # Test chunking
        result = workflow_chunker.chunk_task(test_text)
        print(f"✅ Workflow chunking works: {len(result.subtasks)} subtasks")
        
        for i, subtask in enumerate(result.subtasks[:3], 1):  # Show first 3
            print(f"   {i}. {subtask.description[:50]}...")
        
    except Exception as e:
        print(f"❌ Workflow integration failed: {e}")
        return False
    
    # Test 3: Task command center
    try:
        from task_command_center import TaskCommandCenter
        center = TaskCommandCenter()
        print("✅ Task command center created")
        
        # Check if intelligent execution exists
        has_method = hasattr(center, 'intelligent_task_execution')
        print(f"   Has intelligent execution: {has_method}")
        
    except Exception as e:
        print(f"❌ Task command center failed: {e}")
        return False
    
    print("\n🎉 All integration tests passed!")
    return True

if __name__ == "__main__":
    test_auto_chunker()
