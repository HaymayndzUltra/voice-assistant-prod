#!/usr/bin/env python3
"""
Test script to verify imports of the memory system components
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_imports():
    """Test importing both memory components"""
    print("Testing imports...")
    
    # Test PC2 UnifiedMemoryReasoningAgent
    try:
        import pc2_code.agents.UnifiedMemoryReasoningAgent as umr
        print("✅ Successfully imported UnifiedMemoryReasoningAgent")
    except Exception as e:
        print(f"❌ Failed to import UnifiedMemoryReasoningAgent: {e}")
    
    # Test MainPC MemoryOrchestrator
    try:
        import main_pc_code.src.memory.memory_orchestrator as mo
        print("✅ Successfully imported MemoryOrchestrator")
    except Exception as e:
        print(f"❌ Failed to import MemoryOrchestrator: {e}")
    
if __name__ == "__main__":
    test_imports() 