#!/usr/bin/env python3
"""
Test your prompt using your rule-based parser with phi3:instruct
This is the recommended way for task decomposition
"""

from workflow_memory_intelligence_fixed import execute_task_intelligently

def test_with_rule_parser(task_description):
    """Test task using your rule-based parser with phi3:instruct"""
    
    print(f"🎯 Testing with your rule-based parser...")
    print(f"📤 Your task: {task_description}")
    
    # Use your intelligent task execution
    result = execute_task_intelligently(task_description)
    
    if result:
        print(f"\n✅ Task execution result:")
        print(f"📋 Execution type: {result.get('execution_type', 'unknown')}")
        print(f"📝 Status: {result.get('status', 'unknown')}")
        
        if 'subtasks' in result:
            print(f"📋 Subtasks created: {len(result['subtasks'])}")
            for i, subtask in enumerate(result['subtasks'][:3], 1):
                print(f"   {i}. {subtask.get('description', 'No description')[:50]}...")
            if len(result['subtasks']) > 3:
                print(f"   ... and {len(result['subtasks']) - 3} more")
        
        if 'complexity' in result:
            complexity = result['complexity']
            print(f"🎯 Complexity: {complexity.get('level', 'unknown')} (score: {complexity.get('score', 'unknown')})")
        
        if 'message' in result:
            print(f"💬 Message: {result['message']}")
        
        return result
    else:
        print(f"\n❌ No result from task execution")
        return None

if __name__ == "__main__":
    # 🔥 REPLACE THIS WITH YOUR READY TASK! 🔥
    your_task = "Create a user authentication system with login, registration, and password reset functionality"
    
    # Test your task with the rule-based parser
    result = test_with_rule_parser(your_task)
    
    if result:
        print(f"\n🎉 Success! Your task was processed by the rule-based parser")
        print(f"🔗 Task ID: {result.get('task_id', 'No ID')}")
    else:
        print(f"\n❌ Failed to process task") 