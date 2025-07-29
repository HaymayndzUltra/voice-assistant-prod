#!/usr/bin/env python3
"""
Simple Integration Test
Test integration of command_chunker.py with task system
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_command_chunker():
    """Test the command_chunker.py functionality"""
    
    print("🧪 Testing Command Chunker Integration")
    print("=" * 50)
    
    try:
        # Import command_chunker
        from command_chunker import CommandChunker
        
        # Create chunker instance
        chunker = CommandChunker(max_chunk_size=200)
        
        # Test with a long command-like task
        long_task = """SYSTEM_CONTEXT: Multi-agent AI system with 70+ Python agents across MainPC (RTX 4090) && PC2 (RTX 3060) | Agents in main_pc_code/agents/ && pc2_code/agents/ | Dependencies in startup_config.yaml | Shared libraries: common/, common_utils/. OBJECTIVE: Perform complete Docker/PODMAN refactor && Delete existing containers/images && Generate new SoT docker-compose && Ensure minimal dependencies per container && Resolve startup order issues. CONSTRAINTS: No redundant downloads && Minimal container requirements && Proper startup order && Logical agent grouping && Clear MainPC/PC2 separation. PHASES: Phase 1 - System Analysis & Cleanup | Phase 2 - Logical Grouping & Compose Generation | Phase 3 - Validation & Optimization. MEMORY & REPORTING: Persist changes to MCP memory && Log all actions && Escalate ambiguous issues. SUCCESS_CRITERIA: All legacy artifacts deleted && New SoT validated && Agents run with minimal dependencies && Startup order correct && Full logs available."""
        
        print(f"📋 Testing with {len(long_task)} character task...")
        
        # Analyze size
        analysis = chunker.analyze_command_size(long_task)
        print(f"   Analysis: {analysis}")
        
        # Test different chunking strategies
        strategies = ["auto", "operators", "arguments", "size"]
        
        for strategy in strategies:
            print(f"\n🔧 Strategy: {strategy}")
            chunks = chunker.chunk_command(long_task, strategy=strategy)
            print(f"   Created {len(chunks)} chunks:")
            for i, chunk in enumerate(chunks):
                print(f"     Chunk {i+1}: {len(chunk)} chars - {chunk[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing command_chunker: {e}")
        return False

def test_task_integration():
    """Test integration with task system"""
    
    print("\n🔗 Testing Task System Integration")
    print("=" * 50)
    
    try:
        # Import task-related modules
        from todo_manager import list_open_tasks
        
        print("✅ Todo manager import successful")
        
        # List current tasks
        tasks = list_open_tasks()
        print(f"📋 Current open tasks: {len(tasks)}")
        
        for task in tasks:
            print(f"   - {task['id']}: {task['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing task integration: {e}")
        return False

def create_integrated_chunker():
    """Create a simple integrated chunker class"""
    
    print("\n🔧 Creating Simple Integrated Chunker")
    print("=" * 50)
    
    class SimpleIntegratedChunker:
        def __init__(self):
            self.max_chunk_size = 200
        
        def chunk_long_task(self, task_description: str):
            """Simple chunking for long tasks"""
            
            # Import command_chunker
            from command_chunker import CommandChunker
            
            # Create command chunker
            cmd_chunker = CommandChunker(max_chunk_size=self.max_chunk_size)
            
            # Use auto strategy
            chunks = cmd_chunker.chunk_command(task_description, strategy="auto")
            
            return chunks
        
        def create_task_with_chunks(self, long_description: str):
            """Create a task with proper chunking"""
            
            chunks = self.chunk_long_task(long_description)
            
            # Create short description
            short_desc = long_description[:100] + "..." if len(long_description) > 100 else long_description
            
            task = {
                "description": short_desc,
                "full_description": long_description,
                "todos": [
                    {"text": chunk, "done": False}
                    for chunk in chunks
                ],
                "total_chunks": len(chunks),
                "chunking_method": "integrated_command"
            }
            
            return task
    
    # Test the simple integrated chunker
    chunker = SimpleIntegratedChunker()
    
    test_description = """SYSTEM_CONTEXT: Multi-agent AI system with 70+ Python agents across MainPC (RTX 4090) && PC2 (RTX 3060) | Agents in main_pc_code/agents/ && pc2_code/agents/ | Dependencies in startup_config.yaml | Shared libraries: common/, common_utils/. OBJECTIVE: Perform complete Docker/PODMAN refactor && Delete existing containers/images && Generate new SoT docker-compose && Ensure minimal dependencies per container && Resolve startup order issues. CONSTRAINTS: No redundant downloads && Minimal container requirements && Proper startup order && Logical agent grouping && Clear MainPC/PC2 separation. PHASES: Phase 1 - System Analysis & Cleanup | Phase 2 - Logical Grouping & Compose Generation | Phase 3 - Validation & Optimization. MEMORY & REPORTING: Persist changes to MCP memory && Log all actions && Escalate ambiguous issues. SUCCESS_CRITERIA: All legacy artifacts deleted && New SoT validated && Agents run with minimal dependencies && Startup order correct && Full logs available."""
    
    print(f"📋 Testing integrated chunker with {len(test_description)} characters...")
    
    task = chunker.create_task_with_chunks(test_description)
    
    print(f"✅ Created task:")
    print(f"   Description: {task['description']}")
    print(f"   Total chunks: {task['total_chunks']}")
    print(f"   Chunking method: {task['chunking_method']}")
    
    print(f"\n📝 Chunks:")
    for i, todo in enumerate(task['todos']):
        print(f"   Chunk {i+1}: {len(todo['text'])} chars - {todo['text'][:60]}...")
    
    return True

if __name__ == "__main__":
    print("🔧 Simple Integration Test")
    print("=" * 50)
    
    # Test command_chunker
    test_command_chunker()
    
    # Test task integration
    test_task_integration()
    
    # Test integrated chunker
    create_integrated_chunker()
    
    print("\n✅ Integration test completed!") 