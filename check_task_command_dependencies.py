#!/usr/bin/env python3
"""
Task Command Center Dependency Checker
=====================================
Verifies all dependencies for task_command_center.py are working correctly
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

def check_imports() -> List[Tuple[str, bool, str]]:
    """Check if all required imports work"""
    results = []
    
    # Core Python modules
    core_modules = [
        ('sys', 'System operations'),
        ('os', 'Operating system interface'),
        ('json', 'JSON data handling'),
        ('typing', 'Type hints')
    ]
    
    for module, description in core_modules:
        try:
            __import__(module)
            results.append((module, True, f"✅ {description}"))
        except ImportError as e:
            results.append((module, False, f"❌ {description}: {e}"))
    
    # Custom modules
    custom_modules = [
        ('task_interruption_manager', 'Task interruption management'),
        ('todo_manager', 'Todo management system'),
        ('workflow_memory_intelligence', 'Intelligent workflow system')
    ]
    
    for module, description in custom_modules:
        try:
            __import__(module)
            results.append((module, True, f"✅ {description}"))
        except ImportError as e:
            results.append((module, False, f"❌ {description}: {e}"))
    
    return results

def check_files() -> List[Tuple[str, bool, str]]:
    """Check if required files exist"""
    results = []
    
    required_files = [
        ('todo-tasks.json', 'Main task storage'),
        ('task_interruption_state.json', 'Interruption state'),
        ('task-state.json', 'Current task state'),
        ('memory-bank/', 'Memory bank directory')
    ]
    
    for file_path, description in required_files:
        path = Path(file_path)
        if path.exists():
            if path.is_file():
                size = path.stat().st_size
                results.append((file_path, True, f"✅ {description} ({size} bytes)"))
            else:
                results.append((file_path, True, f"✅ {description} (directory)"))
        else:
            results.append((file_path, False, f"❌ {description}: File not found"))
    
    return results

def check_functions() -> List[Tuple[str, bool, str]]:
    """Check if required functions are available"""
    results = []
    
    try:
        from task_interruption_manager import (
            auto_task_handler, 
            get_interruption_status, 
            resume_all_interrupted_tasks
        )
        results.append(('auto_task_handler', True, "✅ Task interruption handler"))
        results.append(('get_interruption_status', True, "✅ Interruption status getter"))
        results.append(('resume_all_interrupted_tasks', True, "✅ Task resumption function"))
    except ImportError as e:
        results.append(('task_interruption_manager functions', False, f"❌ Import error: {e}"))
    
    try:
        from todo_manager import (
            list_open_tasks, 
            add_todo, 
            mark_done, 
            delete_todo, 
            show_task_details, 
            new_task, 
            hard_delete_task
        )
        results.append(('list_open_tasks', True, "✅ List open tasks"))
        results.append(('add_todo', True, "✅ Add todo"))
        results.append(('mark_done', True, "✅ Mark done"))
        results.append(('delete_todo', True, "✅ Delete todo"))
        results.append(('show_task_details', True, "✅ Show task details"))
        results.append(('new_task', True, "✅ New task"))
        results.append(('hard_delete_task', True, "✅ Hard delete task"))
    except ImportError as e:
        results.append(('todo_manager functions', False, f"❌ Import error: {e}"))
    
    try:
        from workflow_memory_intelligence import execute_task_intelligently
        results.append(('execute_task_intelligently', True, "✅ Intelligent task execution"))
    except ImportError as e:
        results.append(('execute_task_intelligently', False, f"❌ Import error: {e}"))
    
    return results

def test_basic_operations() -> List[Tuple[str, bool, str]]:
    """Test basic operations"""
    results = []
    
    try:
        from todo_manager import list_open_tasks
        tasks = list_open_tasks()
        results.append(('list_open_tasks()', True, f"✅ Returns {len(tasks)} tasks"))
    except Exception as e:
        results.append(('list_open_tasks()', False, f"❌ Error: {e}"))
    
    try:
        from task_interruption_manager import get_interruption_status
        status = get_interruption_status()
        results.append(('get_interruption_status()', True, f"✅ Status: {status.get('interrupted_tasks_count', 0)} interrupted tasks"))
    except Exception as e:
        results.append(('get_interruption_status()', False, f"❌ Error: {e}"))
    
    return results

def main():
    """Main dependency check function"""
    print("🔍 TASK COMMAND CENTER DEPENDENCY CHECK")
    print("=" * 50)
    
    # Check imports
    print("\n📦 IMPORT CHECKS:")
    print("-" * 30)
    import_results = check_imports()
    for module, success, message in import_results:
        print(f"  {message}")
    
    # Check files
    print("\n📁 FILE CHECKS:")
    print("-" * 30)
    file_results = check_files()
    for file_path, success, message in file_results:
        print(f"  {message}")
    
    # Check functions
    print("\n🔧 FUNCTION CHECKS:")
    print("-" * 30)
    function_results = check_functions()
    for func_name, success, message in function_results:
        print(f"  {message}")
    
    # Test operations
    print("\n🧪 OPERATION TESTS:")
    print("-" * 30)
    operation_results = test_basic_operations()
    for op_name, success, message in operation_results:
        print(f"  {message}")
    
    # Summary
    print("\n📊 SUMMARY:")
    print("-" * 30)
    
    all_results = import_results + file_results + function_results + operation_results
    successful = sum(1 for _, success, _ in all_results if success)
    total = len(all_results)
    
    print(f"  Total checks: {total}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {total - successful}")
    print(f"  Success rate: {(successful/total)*100:.1f}%")
    
    if successful == total:
        print("\n🎉 ALL DEPENDENCIES ARE WORKING CORRECTLY!")
        print("   Task Command Center is ready to use.")
    else:
        print(f"\n⚠️  {total - successful} DEPENDENCY ISSUES FOUND")
        print("   Please fix the issues above before using Task Command Center.")
    
    # Show failed items
    failed_items = [(name, message) for name, success, message in all_results if not success]
    if failed_items:
        print("\n❌ FAILED ITEMS:")
        print("-" * 30)
        for name, message in failed_items:
            print(f"  {name}: {message}")

if __name__ == "__main__":
    main() 