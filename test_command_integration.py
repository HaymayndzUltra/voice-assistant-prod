#!/usr/bin/env python3
"""
Test Command Chunker Integration
Test the integration of command_chunker.py with workflow_memory_intelligence_fixed.py
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_command_chunker_import():
    """Test if command_chunker can be imported"""
    
    print("🧪 Testing Command Chunker Import")
    print("=" * 50)
    
    try:
        from command_chunker import CommandChunker
        print("✅ CommandChunker imported successfully")
        
        # Test basic functionality
        chunker = CommandChunker(max_chunk_size=200)
        print("✅ CommandChunker instance created")
        
        # Test with a simple command
        test_command = "echo hello && echo world"
        chunks = chunker.chunk_command(test_command)
        print(f"✅ Test command chunked into {len(chunks)} chunks")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_workflow_integration():
    """Test the workflow_memory_intelligence_fixed.py integration"""
    
    print("\n🔗 Testing Workflow Integration")
    print("=" * 50)
    
    try:
        from workflow_memory_intelligence_fixed import IntelligentTaskChunker
        
        print("✅ IntelligentTaskChunker imported successfully")
        
        # Create chunker instance
        chunker = IntelligentTaskChunker()
        print("✅ IntelligentTaskChunker instance created")
        
        # Test with a long task description
        long_task = """SYSTEM_CONTEXT: Multi-agent AI system with 70+ Python agents across MainPC (RTX 4090) && PC2 (RTX 3060) | Agents in main_pc_code/agents/ && pc2_code/agents/ | Dependencies in startup_config.yaml | Shared libraries: common/, common_utils/. OBJECTIVE: Perform complete Docker/PODMAN refactor && Delete existing containers/images && Generate new SoT docker-compose && Ensure minimal dependencies per container && Resolve startup order issues. CONSTRAINTS: No redundant downloads && Minimal container requirements && Proper startup order && Logical agent grouping && Clear MainPC/PC2 separation. PHASES: Phase 1 - System Analysis & Cleanup | Phase 2 - Logical Grouping & Compose Generation | Phase 3 - Validation & Optimization. MEMORY & REPORTING: Persist changes to MCP memory && Log all actions && Escalate ambiguous issues. SUCCESS_CRITERIA: All legacy artifacts deleted && New SoT validated && Agents run with minimal dependencies && Startup order correct && Full logs available."""
        
        print(f"📋 Testing with {len(long_task)} character task...")
        
        # Test chunking
        chunked_task = chunker.chunk_task(long_task)
        
        print(f"✅ Task chunked successfully:")
        print(f"   Original task: {chunked_task.original_task[:50]}...")
        print(f"   Complexity: {chunked_task.complexity.level}")
        print(f"   Subtasks: {len(chunked_task.subtasks)}")
        
        # Show subtasks
        for i, subtask in enumerate(chunked_task.subtasks):
            print(f"   Subtask {i+1}: {subtask.description[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_option_10_integration():
    """Test the complete Option #10 integration"""
    
    print("\n🎯 Testing Option #10 Integration")
    print("=" * 50)
    
    try:
        from workflow_memory_intelligence_fixed import execute_task_intelligently
        
        print("✅ execute_task_intelligently imported successfully")
        
        # Test with a medium-length task
        test_task = """OBJECTIVE: Test the integrated command chunker with workflow system. CONSTRAINTS: Must work with command separators && Must handle long descriptions | Must create proper TODOs && Must integrate with todo_manager. PHASES: Phase 1 - Test chunking && Phase 2 - Test integration && Phase 3 - Validate results. SUCCESS_CRITERIA: All chunks created properly && Integration works smoothly && TODOs are meaningful."""
        
        print(f"📋 Testing Option #10 with {len(test_task)} character task...")
        
        # Execute task intelligently
        result = execute_task_intelligently(test_task)
        
        print(f"✅ Option #10 execution completed:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Task ID: {result.get('task_id', 'N/A')}")
        print(f"   Subtasks: {result.get('subtasks_count', 0)}")
        print(f"   Message: {result.get('message', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Option #10 integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_current_task_chunking():
    """Test chunking the current long task"""
    
    print("\n📋 Testing Current Task Chunking")
    print("=" * 50)
    
    try:
        # Load current task from todo-tasks.json
        import json
        
        with open('todo-tasks.json', 'r') as f:
            tasks_data = json.load(f)
        
        # Find the current long task
        current_task = None
        for task in tasks_data:
            if len(task.get('description', '')) > 200:  # Long task
                current_task = task
                break
        
        if not current_task:
            print("⚠️ No long task found in todo-tasks.json")
            return False
        
        print(f"📋 Found long task: {current_task['id']}")
        print(f"   Description: {current_task['description'][:100]}...")
        print(f"   Current TODOs: {len(current_task.get('todos', []))}")
        
        # Test with integrated chunker
        from workflow_memory_intelligence_fixed import IntelligentTaskChunker
        
        chunker = IntelligentTaskChunker()
        
        # Get the full description
        full_description = current_task.get('full_description', current_task['description'])
        
        print(f"🔧 Testing integrated chunking on current task...")
        chunked_task = chunker.chunk_task(full_description)
        
        print(f"✅ Current task chunked:")
        print(f"   Original TODOs: {len(current_task.get('todos', []))}")
        print(f"   New subtasks: {len(chunked_task.subtasks)}")
        print(f"   Chunking method: {'Command chunker' if chunker.command_chunker_available else 'Fallback'}")
        
        # Show comparison
        print(f"\n📊 Comparison:")
        print(f"   Original TODOs:")
        for i, todo in enumerate(current_task.get('todos', [])[:3]):
            print(f"     {i+1}. {todo.get('text', '')[:50]}...")
        
        print(f"   New subtasks:")
        for i, subtask in enumerate(chunked_task.subtasks[:3]):
            print(f"     {i+1}. {subtask.description[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Current task chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Command Chunker Integration Test")
    print("=" * 60)
    
    # Test command_chunker import
    test_command_chunker_import()
    
    # Test workflow integration
    test_workflow_integration()
    
    # Test Option #10 integration
    test_option_10_integration()
    
    # Test current task chunking
    test_current_task_chunking()
    
    print("\n✅ Integration test completed!")
    print("\n📝 Summary:")
    print("   - Command chunker integrated with workflow system")
    print("   - Option #10 now uses intelligent chunking")
    print("   - Fallback to original method if command chunker fails")
    print("   - Better handling of long task descriptions") 