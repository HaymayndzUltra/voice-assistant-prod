#!/usr/bin/env python3
"""
Simple memory check script for Cascade
Usage: python3 check_my_memory.py
"""

from cascade_memory_integration import check_memory, continue_from_memory
import json

def main():
    print("🧠 Checking Cascade memory...")
    
    # Check current memory state
    memory_status = check_memory()
    
    print(f"""
📊 CURRENT MEMORY STATE:
========================
🎯 Current Focus: {memory_status['current_focus']}
📋 Active Tasks: {len(memory_status['active_tasks'])}
✅ Total TODOs: {memory_status['todo_count']}
🔗 Memory Provider: {memory_status['memory_provider']}
⏰ Session Start: {memory_status['session_start']}

📋 ACTIVE TASKS:
""")
    
    for i, task in enumerate(memory_status['active_tasks'], 1):
        print(f"{i}. {task['description'][:80]}...")
        print(f"   Status: {task['status']} | TODOs remaining: {task['todos_remaining']}")
        print()
    
    # Get continuation plan
    continuation = continue_from_memory()
    
    print(f"""
🔄 CONTINUATION PLAN:
====================
Can continue: {continuation['continuation_plan']['can_continue']}
Next action: {continuation['continuation_plan']['next_action']}
Context: {continuation['continuation_plan']['context_summary']}

💡 SUGGESTED COMMANDS:
""")
    
    for cmd in continuation['continuation_plan']['suggested_commands']:
        print(f"   • {cmd}")
    
    print("\n✅ Memory check complete!")

if __name__ == "__main__":
    main()
