#!/usr/bin/env python3
"""
Clean up duplicate tasks in todo-tasks.json
Keep the most recent task and remove older duplicates
"""

import json
import os
from datetime import datetime
from collections import defaultdict

def cleanup_duplicate_tasks():
    """Clean up duplicate tasks in todo-tasks.json"""
    
    # Read current todo-tasks.json
    with open('todo-tasks.json', 'r') as f:
        data = json.load(f)
    
    print(f"📊 Original tasks count: {len(data['tasks'])}")
    
    # Group tasks by description
    tasks_by_description = defaultdict(list)
    
    for task in data['tasks']:
        description = task['description'].strip()
        tasks_by_description[description].append(task)
    
    # Keep only the most recent task for each description
    cleaned_tasks = []
    duplicates_removed = 0
    
    for description, tasks in tasks_by_description.items():
        if len(tasks) > 1:
            print(f"🔍 Found {len(tasks)} duplicates for: {description[:50]}...")
            
            # Sort by updated timestamp (most recent first)
            tasks.sort(key=lambda x: x['updated'], reverse=True)
            
            # Keep the most recent one
            most_recent = tasks[0]
            cleaned_tasks.append(most_recent)
            
            # Count duplicates removed
            duplicates_removed += len(tasks) - 1
            
            print(f"   ✅ Kept: {most_recent['id']} (updated: {most_recent['updated']})")
            print(f"   ❌ Removed: {len(tasks) - 1} duplicates")
        else:
            # No duplicates, keep as is
            cleaned_tasks.append(tasks[0])
    
    # Update the data
    data['tasks'] = cleaned_tasks
    
    # Save back to file
    with open('todo-tasks.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n🎯 Cleanup complete!")
    print(f"📊 Tasks after cleanup: {len(cleaned_tasks)}")
    print(f"🗑️  Duplicates removed: {duplicates_removed}")
    
    return cleaned_tasks

if __name__ == "__main__":
    cleanup_duplicate_tasks() 