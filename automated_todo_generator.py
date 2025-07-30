#!/usr/bin/env python3
"""
Automated TODO Generation System

This script creates an automation task for generating TODOs automatically
based on task descriptions using intelligent task chunking and analysis.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import re

# Add the parent directory to sys.path to import our modules
sys.path.append(str(Path(__file__).parent))

try:
    from workflow_memory_intelligence_fixed import SmartTaskExecutionManager
    from todo_manager import add_todo, new_task
except ImportError as e:
    print(f"⚠️ Import warning: {e}")
    print("Some advanced features may not be available")

class AutomatedTODOGenerator:
    """Automated TODO generation system for complex tasks"""
    
    def __init__(self):
        self.active_tasks_file = Path("memory-bank/queue-system/tasks_active.json")
        self.smart_executor = None
        try:
            self.smart_executor = SmartTaskExecutionManager()
        except Exception as e:
            print(f"⚠️ Smart executor not available: {e}")
    
    def load_active_tasks(self) -> List[Dict[str, Any]]:
        """Load active tasks from the queue system"""
        try:
            if self.active_tasks_file.exists():
                with open(self.active_tasks_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"❌ Error loading active tasks: {e}")
            return []
    
    def save_active_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Save active tasks back to the queue system"""
        try:
            with open(self.active_tasks_file, 'w') as f:
                json.dump(tasks, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving active tasks: {e}")
    
    def analyze_task_complexity(self, description: str) -> int:
        """Analyze task complexity to determine if TODO generation is needed"""
        complexity_indicators = [
            r'\b(implement|create|build|develop|design)\b',
            r'\b(analyze|research|investigate|study)\b', 
            r'\b(test|validate|verify|check)\b',
            r'\b(integrate|connect|link|combine)\b',
            r'\b(optimize|improve|enhance|upgrade)\b',
            r'\b(and|or|then|also|additionally)\b',
            r'\b(step|phase|stage|part)\b',
            r'\b(multiple|several|various|different)\b'
        ]
        
        complexity_score = 0
        for pattern in complexity_indicators:
            matches = len(re.findall(pattern, description.lower()))
            complexity_score += matches
        
        # Length-based complexity
        if len(description) > 100:
            complexity_score += 2
        elif len(description) > 50:
            complexity_score += 1
            
        return complexity_score
    
    def generate_basic_todos(self, description: str) -> List[str]:
        """Generate basic TODOs for simple tasks"""
        basic_todos = []
        
        # Common task patterns and their TODOs
        if re.search(r'\b(create|build|implement)\b', description.lower()):
            basic_todos.extend([
                f"Plan the structure and requirements for: {description}",
                f"Research existing solutions and approaches",
                f"Design the implementation approach",
                f"Implement the core functionality",
                f"Test and validate the implementation",
                f"Document the solution and usage"
            ])
        elif re.search(r'\b(analyze|research|investigate)\b', description.lower()):
            basic_todos.extend([
                f"Define the scope and objectives for: {description}",
                f"Gather relevant information and data",
                f"Analyze the collected information",
                f"Identify key findings and insights",
                f"Document the analysis results",
                f"Provide recommendations based on findings"
            ])
        elif re.search(r'\b(test|validate|verify)\b', description.lower()):
            basic_todos.extend([
                f"Define test criteria and success metrics",
                f"Prepare test environment and data",
                f"Execute the testing procedures",
                f"Analyze test results and identify issues",
                f"Document test outcomes and findings",
                f"Provide testing recommendations"
            ])
        else:
            # Generic TODO structure
            basic_todos.extend([
                f"Understand the requirements for: {description}",
                f"Plan the approach and methodology",
                f"Execute the main task activities",
                f"Review and validate the results",
                f"Document the process and outcomes",
                f"Complete any follow-up actions"
            ])
        
        return basic_todos
    
    def generate_smart_todos(self, description: str) -> List[str]:
        """Generate intelligent TODOs using the smart task execution manager"""
        if not self.smart_executor:
            return self.generate_basic_todos(description)
        
        try:
            # Use the smart executor to chunk the task
            result = self.smart_executor.execute_task(description)
            
            if result.get('status') == 'success' and 'task_id' in result:
                # The smart executor already created the task and TODOs
                return []  # TODOs already added by smart executor
            else:
                # Fallback to basic TODO generation
                return self.generate_basic_todos(description)
                
        except Exception as e:
            print(f"⚠️ Smart TODO generation failed: {e}")
            return self.generate_basic_todos(description)
    
    def auto_generate_todos_for_task(self, task_id: str, description: str) -> Dict[str, Any]:
        """Automatically generate TODOs for a specific task"""
        print(f"🤖 Generating TODOs for task: {task_id}")
        print(f"📝 Description: {description}")
        
        # Analyze complexity
        complexity = self.analyze_task_complexity(description)
        print(f"🔍 Complexity score: {complexity}")
        
        if complexity >= 3:
            # Use smart TODO generation for complex tasks
            print("🧠 Using intelligent TODO generation...")
            todos = self.generate_smart_todos(description)
        else:
            # Use basic TODO generation for simple tasks
            print("📋 Using basic TODO generation...")
            todos = self.generate_basic_todos(description)
        
        # Add TODOs to the task
        todos_added = 0
        for todo_text in todos:
            try:
                add_todo(task_id, todo_text)
                todos_added += 1
            except Exception as e:
                print(f"⚠️ Error adding TODO: {e}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "complexity_score": complexity,
            "todos_generated": todos_added,
            "method": "smart" if complexity >= 3 else "basic"
        }
    
    def scan_and_generate_todos(self) -> Dict[str, Any]:
        """Scan active tasks and generate TODOs for tasks without them"""
        print("🔍 Scanning active tasks for TODO generation opportunities...")
        
        tasks = self.load_active_tasks()
        results = {
            "scanned_tasks": len(tasks),
            "tasks_processed": 0,
            "todos_generated": 0,
            "processed_tasks": []
        }
        
        for task in tasks:
            task_id = task.get('id', '')
            description = task.get('description', '')
            todos = task.get('todos', [])
            
            # Only generate TODOs for tasks that don't have any or have very few
            if len(todos) <= 1:  # Tasks with 0 or 1 TODO
                print(f"\n🎯 Processing task: {task_id}")
                
                try:
                    result = self.auto_generate_todos_for_task(task_id, description)
                    results["tasks_processed"] += 1
                    results["todos_generated"] += result.get("todos_generated", 0)
                    results["processed_tasks"].append(result)
                    
                except Exception as e:
                    print(f"❌ Error processing task {task_id}: {e}")
            else:
                print(f"✅ Task {task_id} already has {len(todos)} TODOs - skipping")
        
        return results


def main():
    """Main function for automated TODO generation"""
    print("🤖 Automated TODO Generator - Starting...")
    print("=" * 50)
    
    generator = AutomatedTODOGenerator()
    
    # Scan and generate TODOs for tasks that need them
    results = generator.scan_and_generate_todos()
    
    print("\n" + "=" * 50)
    print("📊 TODO Generation Results:")
    print(f"   Scanned tasks: {results['scanned_tasks']}")
    print(f"   Tasks processed: {results['tasks_processed']}")
    print(f"   TODOs generated: {results['todos_generated']}")
    
    if results['processed_tasks']:
        print("\n📋 Processed Tasks Details:")
        for task_result in results['processed_tasks']:
            print(f"   • {task_result['task_id']}: {task_result['todos_generated']} TODOs ({task_result['method']})")
    
    print("\n✅ Automated TODO generation complete!")
    return results


if __name__ == "__main__":
    main()
