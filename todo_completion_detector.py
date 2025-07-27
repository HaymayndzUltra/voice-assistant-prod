#!/usr/bin/env python3
"""
Todo Completion Detector - Automatic Task State Integration
===========================================================

Automatically detects when todos are completed and updates task state.
Integrates with existing todo_write tool for seamless automation.

Author: AI System Monorepo Task Continuity System
Date: July 27, 2025
"""

import json
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Any
from task_state_manager import TaskStateManager

class TodoCompletionDetector:
    """Automatically detects and processes todo completions"""
    
    def __init__(self):
        self.tsm = TaskStateManager()
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def process_todo_completion(self, todo_data: Dict[str, Any]) -> bool:
        """Process a completed todo and auto-update task state"""
        
        if not self.is_significant_completion(todo_data):
            return False
            
        # Extract task information
        task_info = self.extract_task_info(todo_data)
        
        # Auto-detect impact and tools
        impact = self.detect_impact()
        tools_created = self.detect_created_tools()
        
        # Store as completed task
        success = self.tsm.store_completed_task(
            task_id=task_info['id'],
            title=task_info['title'],
            user_request=task_info['user_request'],
            impact=impact,
            tools_created=tools_created,
            solution_summary=task_info['summary'],
            session_id=self.session_id
        )
        
        if success:
            # Remove from pending if it was there
            self.tsm.remove_pending_task(task_info['id'])
            
            # Log the automation
            print(f"🤖 AUTO-LOGGED: {task_info['title']}")
            print(f"   Impact: {impact}")
            if tools_created:
                print(f"   Tools: {', '.join(tools_created)}")
        
        return success
    
    def is_significant_completion(self, todo_data: Dict[str, Any]) -> bool:
        """Determine if this completion is significant enough to track"""
        
        if todo_data.get('status') != 'completed':
            return False
            
        content = todo_data.get('content', '').lower()
        
        # Skip trivial todos
        trivial_patterns = [
            r'\btest\b', r'\bcheck\b', r'\bverify\b',
            r'\brun\b.*\bcommand\b', r'\bprint\b', r'\bdebug\b'
        ]
        
        for pattern in trivial_patterns:
            if re.search(pattern, content):
                if len(content) < 50:  # Short trivial tasks
                    return False
        
        # Significant patterns
        significant_patterns = [
            r'\bcreate\b', r'\bimplement\b', r'\bbuild\b', r'\bdeploy\b',
            r'\bfix\b', r'\boptimize\b', r'\binstall\b', r'\bsetup\b',
            r'\bconfigure\b', r'\bdesign\b', r'\bdevelop\b'
        ]
        
        for pattern in significant_patterns:
            if re.search(pattern, content):
                return True
                
        # If todo is long and detailed, it's probably significant
        return len(content) > 100
    
    def extract_task_info(self, todo_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract structured task information from todo"""
        
        content = todo_data.get('content', '')
        todo_id = todo_data.get('id', '')
        
        # Generate meaningful task ID if not provided
        if not todo_id or todo_id.startswith('temp_'):
            task_id = self.generate_task_id(content)
        else:
            task_id = todo_id
            
        # Extract title (first line or summarize)
        title = self.extract_title(content)
        
        # Try to infer user request context
        user_request = self.infer_user_request(content)
        
        # Create summary
        summary = self.create_summary(content)
        
        return {
            'id': task_id,
            'title': title,
            'user_request': user_request,
            'summary': summary
        }
    
    def generate_task_id(self, content: str) -> str:
        """Generate a meaningful task ID from content"""
        
        # Extract key words
        words = re.findall(r'\b[a-z]+\b', content.lower())
        key_words = [w for w in words if len(w) > 3 and w not in ['create', 'implement', 'build']]
        
        # Take first 3 meaningful words
        id_parts = key_words[:3] if key_words else ['task']
        
        # Add timestamp
        timestamp = datetime.now().strftime('%Y%m%d')
        
        return f"{'_'.join(id_parts)}_{timestamp}"
    
    def extract_title(self, content: str) -> str:
        """Extract a clean title from todo content"""
        
        # Take first line or first sentence
        lines = content.split('\n')
        first_line = lines[0].strip()
        
        # Remove action words and clean up
        title = re.sub(r'^(create|implement|build|deploy|fix|setup|install)\s+', '', first_line, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Capitalize first letter
        if title:
            title = title[0].upper() + title[1:]
            
        # Limit length
        if len(title) > 80:
            title = title[:77] + '...'
            
        return title or "Task Completion"
    
    def infer_user_request(self, content: str) -> str:
        """Try to infer the original user request from todo content"""
        
        # Look for patterns that suggest user requests
        request_patterns = [
            r'user wants?:?\s*(.+)',
            r'requested:?\s*(.+)',
            r'task:?\s*(.+)',
            r'goal:?\s*(.+)'
        ]
        
        for pattern in request_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Default: use first sentence as inferred request
        sentences = re.split(r'[.!?]', content)
        if sentences:
            return sentences[0].strip()
            
        return content[:100] + ('...' if len(content) > 100 else '')
    
    def create_summary(self, content: str) -> str:
        """Create a summary of what was accomplished"""
        
        # For now, use the content as summary but clean it up
        summary = re.sub(r'\s+', ' ', content).strip()
        
        # Add prefix if it doesn't start with action word
        action_words = ['created', 'implemented', 'built', 'deployed', 'fixed', 'setup', 'installed']
        first_word = summary.split()[0].lower() if summary.split() else ''
        
        if first_word not in action_words:
            summary = f"Completed: {summary}"
            
        return summary[:200] + ('...' if len(summary) > 200 else '')
    
    def detect_impact(self) -> str:
        """Auto-detect the impact of completed work"""
        
        # Check for recent file changes
        recent_files = self.get_recent_file_changes()
        
        impact_indicators = []
        
        # Check for tool creation
        tools = self.detect_created_tools()
        if tools:
            impact_indicators.append(f"{len(tools)} tools created")
        
        # Check for file modifications
        if recent_files:
            impact_indicators.append(f"{len(recent_files)} files modified")
        
        # Check for significant file sizes
        large_files = [f for f in recent_files if self.get_file_size(f) > 1000]
        if large_files:
            impact_indicators.append(f"{len(large_files)} substantial implementations")
        
        return ', '.join(impact_indicators) if impact_indicators else "Task completed successfully"
    
    def detect_created_tools(self) -> List[str]:
        """Auto-detect recently created tools/scripts"""
        
        tool_extensions = ['.sh', '.py', '.ps1', '.bat', '.json', '.yaml', '.yml']
        recent_tools = []
        
        # Check for recent files with tool extensions
        for ext in tool_extensions:
            for file_path in self.get_recent_files_by_extension(ext):
                if self.is_tool_file(file_path):
                    recent_tools.append(os.path.basename(file_path))
        
        return recent_tools
    
    def get_recent_file_changes(self, minutes: int = 30) -> List[str]:
        """Get files modified in the last N minutes"""
        
        import time
        cutoff_time = time.time() - (minutes * 60)
        recent_files = []
        
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    if os.path.getmtime(filepath) > cutoff_time:
                        recent_files.append(filepath)
                except OSError:
                    continue
        
        return recent_files
    
    def get_recent_files_by_extension(self, ext: str, minutes: int = 30) -> List[str]:
        """Get recent files with specific extension"""
        recent_files = self.get_recent_file_changes(minutes)
        return [f for f in recent_files if f.endswith(ext)]
    
    def is_tool_file(self, filepath: str) -> bool:
        """Determine if a file is a tool/script"""
        
        filename = os.path.basename(filepath).lower()
        
        # Tool name patterns
        tool_patterns = [
            r'cleanup', r'setup', r'install', r'deploy', r'start', r'stop',
            r'config', r'manage', r'monitor', r'backup', r'restore',
            r'script', r'tool', r'utility', r'helper'
        ]
        
        for pattern in tool_patterns:
            if re.search(pattern, filename):
                return True
        
        # Check if file has executable permissions
        try:
            return os.access(filepath, os.X_OK)
        except OSError:
            return False
    
    def get_file_size(self, filepath: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(filepath)
        except OSError:
            return 0

# CLI Interface for testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 todo_completion_detector.py '<todo_json>'")
        sys.exit(1)
    
    try:
        todo_json = sys.argv[1]
        todo_data = json.loads(todo_json)
        
        detector = TodoCompletionDetector()
        success = detector.process_todo_completion(todo_data)
        
        if success:
            print("✅ Todo completion processed and logged automatically")
        else:
            print("ℹ️  Todo completion not significant enough to log")
            
    except json.JSONDecodeError:
        print("❌ Invalid JSON format")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 