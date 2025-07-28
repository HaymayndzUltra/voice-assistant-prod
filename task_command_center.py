#!/usr/bin/env python3
"""
Task Command & Control Center - Interactive menu system for task management
"""

import sys
import os
import json
from typing import List, Dict, Any
from task_interruption_manager import auto_task_handler, get_interruption_status, resume_all_interrupted_tasks
from todo_manager import list_open_tasks, add_todo, mark_done, delete_todo, show_task_details, new_task, hard_delete_task
# 🚀 Intelligent workflow integration
from workflow_memory_intelligence import execute_task_intelligently

class TaskCommandCenter:
    """Interactive command and control center for task management"""
    
    def __init__(self):
        self.running = True
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_header(self):
        """Show the command center header"""
        print("=" * 60)
        print("🎮 TASK COMMAND & CONTROL CENTER")
        print("=" * 60)
        print()
    
    def show_current_status(self):
        """Show current task status"""
        status = get_interruption_status()
        
        print("📊 CURRENT STATUS:")
        print("-" * 30)
        
        if status['current_task']:
            print(f"🚀 ACTIVE TASK:")
            print(f"   {status['current_task']['description']}")
            print(f"   ID: {status['current_task']['task_id']}")
        else:
            print("ℹ️  No active task")
        
        if status['interrupted_tasks_count'] > 0:
            print(f"\n⏸️  INTERRUPTED TASKS ({status['interrupted_tasks_count']}):")
            for i, task in enumerate(status['interrupted_tasks'], 1):
                print(f"   {i}. {task['description']}")
        else:
            print("\nℹ️  No interrupted tasks")
        
        print()
    
    def show_main_menu(self):
        """Show the main menu"""
        print("🎯 MAIN MENU:")
        print("1. 📋 View All Tasks")
        print("2. 🚀 Start New Task")
        print("3. ⏸️  Interrupt Current Task")
        print("4. 🔄 Resume Interrupted Tasks")
        print("5. ✏️  Add TODO to Task")
        print("6. ✅ Mark TODO as Done")
        print("7. 🗑️  Delete TODO")
        print("8. 📖 Show Task Details")
        print("9. 🗑️  Delete Task")
        print("10. 🧠 Intelligent Task Execution")
        print("0. ❌ Exit")
        print()
    
    def get_user_choice(self, max_choice: int) -> int:
        """Get user choice with validation"""
        while True:
            try:
                choice = input(f"Enter your choice (0-{max_choice}): ").strip()
                choice_num = int(choice)
                if 0 <= choice_num <= max_choice:
                    return choice_num
                else:
                    print(f"❌ Please enter a number between 0 and {max_choice}")
            except ValueError:
                print("❌ Please enter a valid number")
    
    def view_all_tasks(self):
        """View all open tasks"""
        self.clear_screen()
        self.show_header()
        
        print("📋 ALL OPEN TASKS:")
        print("=" * 40)
        
        tasks = list_open_tasks()
        if tasks:
            for i, task in enumerate(tasks, 1):
                print(f"\n{i}. 🗒️  {task['id']}")
                print(f"   Description: {task['description'][:80]}...")
                print(f"   Status: {task['status']}")
                print(f"   Created: {task['created']}")
                
                if task['todos']:
                    print(f"   TODO Items ({len(task['todos'])}):")
                    for j, todo in enumerate(task['todos']):
                        mark = "✔" if todo["done"] else "✗"
                        print(f"      [{mark}] {j}. {todo['text']}")
                else:
                    print("   TODO Items: None")
        else:
            print("ℹ️  No open tasks found")
        
        input("\nPress Enter to continue...")
    
    def start_new_task(self):
        """Start a new task"""
        self.clear_screen()
        self.show_header()
        
        print("🚀 START NEW TASK:")
        print("=" * 30)
        
        # Show current status first
        self.show_current_status()
        
        print("Enter your new task description:")
        task_description = input("> ").strip()
        
        if task_description:
            result = auto_task_handler(task_description)
            print(f"\n{result}")
        else:
            print("❌ Task description cannot be empty")
        
        input("\nPress Enter to continue...")
    
    def interrupt_current_task(self):
        """Interrupt current task"""
        self.clear_screen()
        self.show_header()
        
        print("⏸️  INTERRUPT CURRENT TASK:")
        print("=" * 35)
        
        status = get_interruption_status()
        
        if status['current_task']:
            print(f"Current task: {status['current_task']['description']}")
            print(f"Task ID: {status['current_task']['task_id']}")
            
            confirm = input("\nAre you sure you want to interrupt this task? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                # Start a dummy task to trigger interruption
                result = auto_task_handler("Temporary interruption")
                print(f"\n{result}")
            else:
                print("❌ Task interruption cancelled")
        else:
            print("ℹ️  No active task to interrupt")
        
        input("\nPress Enter to continue...")
    
    def resume_interrupted_tasks(self):
        """Resume interrupted tasks"""
        self.clear_screen()
        self.show_header()
        
        print("🔄 RESUME INTERRUPTED TASKS:")
        print("=" * 35)
        
        status = get_interruption_status()
        
        if status['interrupted_tasks_count'] > 0:
            print(f"Found {status['interrupted_tasks_count']} interrupted task(s):")
            for i, task in enumerate(status['interrupted_tasks'], 1):
                print(f"   {i}. {task['description']}")
            
            confirm = input("\nResume all interrupted tasks? (y/N): ").strip().lower()
            if confirm in ['y', 'yes']:
                resume_all_interrupted_tasks()
                print("✅ All tasks resumed successfully")
            else:
                print("❌ Task resumption cancelled")
        else:
            print("ℹ️  No interrupted tasks to resume")
        
        input("\nPress Enter to continue...")
    
    def add_todo_to_task(self):
        """Add TODO to a task"""
        self.clear_screen()
        self.show_header()
        
        print("✏️  ADD TODO TO TASK:")
        print("=" * 25)
        
        tasks = list_open_tasks()
        if not tasks:
            print("ℹ️  No tasks available")
            input("\nPress Enter to continue...")
            return
        
        print("Available tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['description'][:50]}...")
        
        try:
            choice = int(input(f"\nSelect task (1-{len(tasks)}): ")) - 1
            if 0 <= choice < len(tasks):
                selected_task = tasks[choice]
                todo_text = input(f"Enter TODO text for task '{selected_task['description'][:30]}...': ").strip()
                
                if todo_text:
                    add_todo(selected_task['id'], todo_text)
                    print("✅ TODO added successfully")
                else:
                    print("❌ TODO text cannot be empty")
            else:
                print("❌ Invalid task selection")
        except ValueError:
            print("❌ Please enter a valid number")
        
        input("\nPress Enter to continue...")
    
    def mark_todo_done(self):
        """Mark TODO as done"""
        self.clear_screen()
        self.show_header()
        
        print("✅ MARK TODO AS DONE:")
        print("=" * 25)
        
        tasks = list_open_tasks()
        if not tasks:
            print("ℹ️  No tasks available")
            input("\nPress Enter to continue...")
            return
        
        # Find tasks with TODO items
        tasks_with_todos = []
        for task in tasks:
            if task['todos']:
                tasks_with_todos.append(task)
        
        if not tasks_with_todos:
            print("ℹ️  No tasks with TODO items")
            input("\nPress Enter to continue...")
            return
        
        print("Tasks with TODO items:")
        for i, task in enumerate(tasks_with_todos, 1):
            print(f"   {i}. {task['description'][:50]}...")
            print(f"      TODO items: {len(task['todos'])}")
        
        try:
            choice = int(input(f"\nSelect task (1-{len(tasks_with_todos)}): ")) - 1
            if 0 <= choice < len(tasks_with_todos):
                selected_task = tasks_with_todos[choice]
                
                print(f"\nTODO items in '{selected_task['description'][:30]}...':")
                for i, todo in enumerate(selected_task['todos']):
                    mark = "✔" if todo["done"] else "✗"
                    print(f"   [{mark}] {i}. {todo['text']}")
                
                todo_choice = int(input(f"\nSelect TODO to mark as done (0-{len(selected_task['todos'])-1}): "))
                if 0 <= todo_choice < len(selected_task['todos']):
                    mark_done(selected_task['id'], todo_choice)
                    print("✅ TODO marked as done")
                else:
                    print("❌ Invalid TODO selection")
            else:
                print("❌ Invalid task selection")
        except ValueError:
            print("❌ Please enter a valid number")
        
        input("\nPress Enter to continue...")
    
    def delete_todo_item(self):
        """Delete TODO item"""
        self.clear_screen()
        self.show_header()
        
        print("🗑️  DELETE TODO ITEM:")
        print("=" * 25)
        
        tasks = list_open_tasks()
        if not tasks:
            print("ℹ️  No tasks available")
            input("\nPress Enter to continue...")
            return
        
        # Find tasks with TODO items
        tasks_with_todos = []
        for task in tasks:
            if task['todos']:
                tasks_with_todos.append(task)
        
        if not tasks_with_todos:
            print("ℹ️  No tasks with TODO items")
            input("\nPress Enter to continue...")
            return
        
        print("Tasks with TODO items:")
        for i, task in enumerate(tasks_with_todos, 1):
            print(f"   {i}. {task['description'][:50]}...")
            print(f"      TODO items: {len(task['todos'])}")
        
        try:
            choice = int(input(f"\nSelect task (1-{len(tasks_with_todos)}): ")) - 1
            if 0 <= choice < len(tasks_with_todos):
                selected_task = tasks_with_todos[choice]
                
                print(f"\nTODO items in '{selected_task['description'][:30]}...':")
                for i, todo in enumerate(selected_task['todos']):
                    mark = "✔" if todo["done"] else "✗"
                    print(f"   [{mark}] {i}. {todo['text']}")
                
                todo_choice = int(input(f"\nSelect TODO to delete (0-{len(selected_task['todos'])-1}): "))
                if 0 <= todo_choice < len(selected_task['todos']):
                    delete_todo(selected_task['id'], todo_choice)
                    print("✅ TODO deleted successfully")
                else:
                    print("❌ Invalid TODO selection")
            else:
                print("❌ Invalid task selection")
        except ValueError:
            print("❌ Please enter a valid number")
        
        input("\nPress Enter to continue...")
    
    def show_task_details(self):
        """Show detailed task information"""
        self.clear_screen()
        self.show_header()
        
        print("📖 SHOW TASK DETAILS:")
        print("=" * 25)
        
        tasks = list_open_tasks()
        if not tasks:
            print("ℹ️  No tasks available")
            input("\nPress Enter to continue...")
            return
        
        print("Available tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['description'][:50]}...")
        
        try:
            choice = int(input(f"\nSelect task (1-{len(tasks)}): ")) - 1
            if 0 <= choice < len(tasks):
                selected_task = tasks[choice]
                show_task_details(selected_task['id'])
            else:
                print("❌ Invalid task selection")
        except ValueError:
            print("❌ Please enter a valid number")
        
        input("\nPress Enter to continue...")
    
    def delete_task(self):
        """Delete a task"""
        self.clear_screen()
        self.show_header()
        
        print("🗑️  DELETE TASK:")
        print("=" * 15)
        
        tasks = list_open_tasks()
        if not tasks:
            print("ℹ️  No tasks available")
            input("\nPress Enter to continue...")
            return
        
        print("Available tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task['description'][:50]}...")
        
        try:
            choice = int(input(f"\nSelect task to delete (1-{len(tasks)}): ")) - 1
            if 0 <= choice < len(tasks):
                selected_task = tasks[choice]
                
                print(f"\nTask to delete: {selected_task['description']}")
                confirm = input("Are you sure you want to delete this task? (y/N): ").strip().lower()
                
                if confirm in ['y', 'yes']:
                    hard_delete_task(selected_task['id'])
                    print("✅ Task deleted successfully")
                else:
                    print("❌ Task deletion cancelled")
            else:
                print("❌ Invalid task selection")
        except ValueError:
            print("❌ Please enter a valid number")
        
        input("\nPress Enter to continue...")
    
    def run(self):
        """Run the command center"""
        while self.running:
            self.clear_screen()
            self.show_header()
            self.show_current_status()
            self.show_main_menu()
            
            choice = self.get_user_choice(10)
            
            if choice == 0:
                print("👋 Goodbye!")
                self.running = False
            elif choice == 1:
                self.view_all_tasks()
            elif choice == 2:
                self.start_new_task()
            elif choice == 3:
                self.interrupt_current_task()
            elif choice == 4:
                self.resume_interrupted_tasks()
            elif choice == 5:
                self.add_todo_to_task()
            elif choice == 6:
                self.mark_todo_done()
            elif choice == 7:
                self.delete_todo_item()
            elif choice == 8:
                self.show_task_details()
            elif choice == 9:
                self.delete_task()
            elif choice == 10:
                self.intelligent_task_execution()

    # ------------------------------------------------------------------
    # 🧠 Intelligent Task Execution Integration
    # ------------------------------------------------------------------
    def intelligent_task_execution(self):
        """Execute a task using intelligent workflow integration"""
        self.clear_screen()
        self.show_header()

        print("🧠 INTELLIGENT TASK EXECUTION:")
        print("=" * 35)
        print("Enter your task description (will be analyzed and executed intelligently):")

        task_description = input("> ").strip()

        if not task_description:
            print("❌ Task description cannot be empty")
            input("\nPress Enter to continue...")
            return

        # Execute task using intelligent workflow system
        print("\n🚀 Processing task with intelligent executor...\n")
        try:
            result = execute_task_intelligently(task_description)
            # Pretty-print the JSON result for the user
            print("\n✅ Intelligent Execution Result:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            # Catch any unexpected errors to ensure command center stability
            print(f"❌ An error occurred during intelligent execution: {e}")

        input("\nPress Enter to continue...")


def main():
    """Main function"""
    command_center = TaskCommandCenter()
    command_center.run()


if __name__ == "__main__":
    main() 