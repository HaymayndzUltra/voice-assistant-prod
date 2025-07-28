#!/usr/bin/env python3
"""
Auto Task Runner - Automatically handles task interruption and resumption
"""

import sys
from task_interruption_manager import auto_task_handler, get_interruption_status

def main():
    """Main function to handle automatic task management"""
    
    if len(sys.argv) < 2:
        print("🤖 Auto Task Runner")
        print("Usage: python3 auto_task_runner.py <command>")
        print("")
        print("Examples:")
        print("  python3 auto_task_runner.py 'fix the bug in login.py'")
        print("  python3 auto_task_runner.py 'gawa ng new feature'")
        print("  python3 auto_task_runner.py 'resume'")
        print("  python3 auto_task_runner.py 'status'")
        print("")
        print("Features:")
        print("  ✅ Auto-detects new tasks")
        print("  ⏸️  Automatically interrupts current task")
        print("  🔄 Automatically resumes interrupted tasks")
        print("  💾 Never forgets original tasks")
        return
    
    # Get the command
    command = " ".join(sys.argv[1:])
    
    # Process the command
    result = auto_task_handler(command)
    print(result)
    
    # Show current status after processing
    print("\n" + "="*50)
    status = get_interruption_status()
    if status['current_task'] or status['interrupted_tasks_count'] > 0:
        print("📊 Current Status:")
        if status['current_task']:
            print(f"   🚀 Active: {status['current_task']['description']}")
        if status['interrupted_tasks_count'] > 0:
            print(f"   ⏸️  Waiting: {status['interrupted_tasks_count']} task(s)")
            for task in status['interrupted_tasks']:
                print(f"      - {task['description']}")

if __name__ == "__main__":
    main() 