#!/usr/bin/env python3
"""
Queue CLI - Command Line Interface for Task Queue System

Provides command-line interface for:
1. Starting/stopping queue engine
2. Adding tasks to queue
3. Checking queue status
4. Managing interruptions
5. Manual queue operations

This CLI complements the automatic queue engine with manual control options.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Import our queue engine
try:
    from task_queue_engine import TaskQueueEngine, get_queue_engine
except ImportError:
    print("❌ Could not import task_queue_engine. Make sure it's in the same directory.")
    sys.exit(1)

def cmd_start(args):
    """Start queue engine monitoring"""
    print("🚀 Starting queue engine...")
    
    engine = get_queue_engine()
    
    if engine.running:
        print("⚠️ Queue engine already running")
        return
    
    engine.start_monitoring()
    
    status = engine.get_status()
    print("✅ Queue engine started successfully!")
    print(f"📊 Status: Q:{status['queue_count']} A:{status['active_count']} D:{status['done_count']} I:{status['interrupted_count']}")
    
    if args.daemon:
        print("🔄 Running in daemon mode...")
        try:
            import time
            while True:
                time.sleep(10)
                status = engine.get_status()
                if status['queue_count'] > 0 or status['active_count'] > 0:
                    print(f"📊 Q:{status['queue_count']} A:{status['active_count']} D:{status['done_count']} I:{status['interrupted_count']}")
        except KeyboardInterrupt:
            print("\n🛑 Stopping queue engine...")
            engine.stop_monitoring()

def cmd_stop(args):
    """Stop queue engine monitoring"""
    print("🛑 Stopping queue engine...")
    
    engine = get_queue_engine()
    engine.stop_monitoring()
    
    print("✅ Queue engine stopped")

def cmd_status(args):
    """Show queue status"""
    engine = get_queue_engine()
    status = engine.get_status()
    
    print("📊 Task Queue Status")
    print("===================")
    print(f"Queue (waiting):     {status['queue_count']:3d}")
    print(f"Active (working):    {status['active_count']:3d}")
    print(f"Done (completed):    {status['done_count']:3d}")
    print(f"Interrupted (paused): {status['interrupted_count']:3d}")
    print(f"System idle:         {'Yes' if status['is_idle'] else 'No'}")
    print(f"Monitoring:          {'Active' if status['monitoring'] else 'Stopped'}")
    print(f"Last check:          {status['timestamp']}")
    
    if args.detailed:
        print("\n📋 Detailed View:")
        
        # Show active tasks
        active_tasks = engine._read_json(engine.queue_files['active'])
        if active_tasks:
            print("\n🔄 Active Tasks:")
            for i, task in enumerate(active_tasks, 1):
                desc = task.get('description', 'No description')[:60]
                todos_done = sum(1 for todo in task.get('todos', []) if todo.get('done', False))
                todos_total = len(task.get('todos', []))
                print(f"  {i}. {desc}... ({todos_done}/{todos_total} todos)")
        
        # Show queue tasks
        queue_tasks = engine._read_json(engine.queue_files['queue'])
        if queue_tasks:
            print("\n📋 Queued Tasks:")
            for i, task in enumerate(queue_tasks, 1):
                desc = task.get('description', 'No description')[:60]
                todos_count = len(task.get('todos', []))
                print(f"  {i}. {desc}... ({todos_count} todos)")

def cmd_add(args):
    """Add task to queue"""
    print(f"📝 Adding task to queue: {args.description}")
    
    # Create task structure
    task = {
        "id": f"queue_{int(__import__('time').time())}",
        "description": args.description,
        "todos": [],
        "status": "queued"
    }
    
    # Add todos if provided
    if args.todos:
        for todo_text in args.todos:
            task["todos"].append({
                "text": todo_text,
                "done": False
            })
    
    # Add to queue
    engine = get_queue_engine()
    engine.add_task_to_queue(task)
    
    print(f"✅ Task added to queue: {task['id']}")
    
    # Show updated status
    status = engine.get_status()
    print(f"📊 Queue status: Q:{status['queue_count']} A:{status['active_count']}")

def cmd_interrupt(args):
    """Interrupt current tasks with urgent work"""
    print(f"🚨 Interrupting current tasks for: {args.description}")
    
    # Create urgent task
    urgent_task = {
        "id": f"urgent_{int(__import__('time').time())}",
        "description": args.description,
        "todos": [],
        "status": "urgent",
        "priority": "urgent"
    }
    
    # Add todos if provided
    if args.todos:
        for todo_text in args.todos:
            urgent_task["todos"].append({
                "text": todo_text,
                "done": False
            })
    
    # Interrupt with urgent task
    engine = get_queue_engine()
    engine.interrupt_current_tasks(urgent_task)
    
    print(f"✅ Urgent task started: {urgent_task['id']}")
    
    # Show updated status
    status = engine.get_status()
    print(f"📊 Status: Q:{status['queue_count']} A:{status['active_count']} I:{status['interrupted_count']}")

def cmd_list(args):
    """List tasks in specific queue"""
    engine = get_queue_engine()
    
    queue_name = args.queue
    if queue_name not in engine.queue_files:
        print(f"❌ Unknown queue: {queue_name}")
        print(f"Available queues: {', '.join(engine.queue_files.keys())}")
        return
    
    tasks = engine._read_json(engine.queue_files[queue_name])
    
    print(f"📋 {queue_name.title()} Queue ({len(tasks)} tasks)")
    print("=" * 50)
    
    if not tasks:
        print("  (empty)")
        return
    
    for i, task in enumerate(tasks, 1):
        task_id = task.get('id', 'unknown')
        desc = task.get('description', 'No description')
        todos = task.get('todos', [])
        todos_done = sum(1 for todo in todos if todo.get('done', False))
        status = task.get('status', 'unknown')
        
        print(f"  {i}. [{task_id}] {desc}")
        print(f"     Status: {status} | TODOs: {todos_done}/{len(todos)}")
        
        if args.todos and todos:
            for j, todo in enumerate(todos, 1):
                mark = "✓" if todo.get('done', False) else "○"
                print(f"       {mark} {j}. {todo.get('text', 'No text')}")
        print()

def cmd_migrate(args):
    """Migrate from old system to queue system"""
    print("🚀 Starting migration to queue system...")
    
    try:
        from migrate_to_queue_system import QueueSystemMigrator
        migrator = QueueSystemMigrator()
        
        if args.force:
            success = migrator.run_migration()
        else:
            print("This will migrate from todo-tasks.json to the new queue system.")
            response = input("Continue? (y/N): ")
            if response.lower() == 'y':
                success = migrator.run_migration()
            else:
                print("❌ Migration cancelled")
                return
        
        if success:
            print("✅ Migration completed successfully!")
        else:
            print("❌ Migration failed!")
            
    except ImportError:
        print("❌ Migration tool not found. Make sure migrate_to_queue_system.py exists.")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Task Queue System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start queue engine monitoring')
    start_parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    start_parser.set_defaults(func=cmd_start)
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop queue engine monitoring')
    stop_parser.set_defaults(func=cmd_stop)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show queue status')
    status_parser.add_argument('--detailed', action='store_true', help='Show detailed task information')
    status_parser.set_defaults(func=cmd_status)
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add task to queue')
    add_parser.add_argument('description', help='Task description')
    add_parser.add_argument('--todos', nargs='*', help='TODO items for the task')
    add_parser.set_defaults(func=cmd_add)
    
    # Interrupt command
    interrupt_parser = subparsers.add_parser('interrupt', help='Interrupt current tasks with urgent work')
    interrupt_parser.add_argument('description', help='Urgent task description')
    interrupt_parser.add_argument('--todos', nargs='*', help='TODO items for urgent task')
    interrupt_parser.set_defaults(func=cmd_interrupt)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List tasks in queue')
    list_parser.add_argument('queue', choices=['queue', 'active', 'done', 'interrupted'], help='Queue to list')
    list_parser.add_argument('--todos', action='store_true', help='Show TODO items')
    list_parser.set_defaults(func=cmd_list)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Migrate from old system to queue system')
    migrate_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    migrate_parser.set_defaults(func=cmd_migrate)
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
