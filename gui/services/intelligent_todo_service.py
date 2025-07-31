"""
🎯 Intelligent TODO Service
Converts natural language GUI commands into structured TODO tasks
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import our AI intelligence system
import sys
sys.path.append('..')
try:
    from memory_system.ai_cursor_intelligence import AIProductionIntelligence
except ImportError:
    # Fallback if import fails
    class AIProductionIntelligence:
        def generate_intelligent_response(self, query):
            return {
                'analysis': {'confidence': 0.5, 'interaction_type': 'general'},
                'immediate_actions': [f"Process: {query}"],
                'potential_issues': [],
                'relevant_documentation': []
            }

class IntelligentTodoService:
    """Service for converting GUI commands to intelligent TODOs"""
    
    def __init__(self, todo_manager_path="todo_manager.py"):
        self.todo_manager = todo_manager_path
        self.project_root = Path(__file__).parent.parent.parent
        self.ai_intelligence = AIProductionIntelligence()
        
        # Command mapping for GUI-specific operations
        self.gui_command_mappings = {
            'deploy production': {
                'task_type': 'production_deployment',
                'priority': 'high',
                'estimated_time': '30-45 minutes'
            },
            'fix docker': {
                'task_type': 'troubleshooting', 
                'priority': 'medium',
                'estimated_time': '15-30 minutes'
            },
            'setup monitoring': {
                'task_type': 'monitoring_setup',
                'priority': 'medium', 
                'estimated_time': '20-40 minutes'
            },
            'security check': {
                'task_type': 'security_audit',
                'priority': 'high',
                'estimated_time': '15-25 minutes'
            }
        }
    
    def process_gui_command(self, command: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process a GUI command and convert to structured TODO
        
        Args:
            command: Natural language command from GUI
            context: Optional context (current view, system state, etc.)
            
        Returns:
            Dict with task creation result and AI response
        """
        try:
            # Get AI intelligence response
            ai_response = self.ai_intelligence.generate_intelligent_response(command)
            
            result = {
                'success': False,
                'task_id': None,
                'ai_response': ai_response,
                'todo_count': 0,
                'message': ''
            }
            
            # Check if command should create a structured TODO
            if self._should_create_todo(ai_response):
                task_result = self._create_structured_todo(command, ai_response, context)
                result.update(task_result)
            else:
                result['message'] = f"Command processed but no TODO created (confidence: {ai_response['analysis']['confidence']})"
                result['success'] = True
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to process command: {command}"
            }
    
    def _should_create_todo(self, ai_response: Dict) -> bool:
        """Determine if AI response should create a TODO"""
        confidence = float(ai_response['analysis']['confidence'].rstrip('%')) / 100
        interaction_type = ai_response['analysis']['interaction_type']
        
        # Create TODO for high-confidence actionable commands
        return (confidence > 0.7 and 
                interaction_type in ['deployment_request', 'troubleshooting', 'optimization'])
    
    def _create_structured_todo(self, command: str, ai_response: Dict, context: Dict = None) -> Dict[str, Any]:
        """Create a structured TODO from AI response"""
        try:
            # Generate task ID and description
            task_id = self._generate_task_id(command)
            task_description = self._generate_task_description(command, ai_response)
            
            # Create main task
            create_result = self._create_main_task(task_id, task_description)
            
            if not create_result['success']:
                return create_result
            
            # Add TODO items from AI response
            todo_results = self._add_ai_todos(task_id, ai_response)
            
            return {
                'success': True,
                'task_id': task_id,
                'todo_count': len(ai_response['immediate_actions']),
                'message': f"Created task '{task_description}' with {len(ai_response['immediate_actions'])} TODO items",
                'ai_confidence': ai_response['analysis']['confidence'],
                'ai_topic': ai_response['analysis']['topic']
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to create structured TODO for: {command}"
            }
    
    def _generate_task_id(self, command: str) -> str:
        """Generate unique task ID"""
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        command_slug = command.lower().replace(' ', '_').replace('-', '_')[:30]
        return f"{timestamp}_GUI_{command_slug}"
    
    def _generate_task_description(self, command: str, ai_response: Dict) -> str:
        """Generate comprehensive task description"""
        topic = ai_response['analysis']['topic']
        confidence = ai_response['analysis']['confidence']
        
        description = f"GUI Command: {command.title()}"
        
        if topic != 'general':
            description += f" ({topic.replace('_', ' ').title()})"
        
        return description
    
    def _create_main_task(self, task_id: str, description: str) -> Dict[str, Any]:
        """Create main task using todo_manager"""
        try:
            cmd = [
                sys.executable, 
                str(self.project_root / self.todo_manager),
                "new", 
                task_id,
                description
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'output': result.stdout}
            else:
                return {
                    'success': False, 
                    'error': result.stderr,
                    'message': f"todo_manager failed with code {result.returncode}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'timeout',
                'message': "todo_manager did not respond in time"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to execute todo_manager: {e}"
            }
    
    def _add_ai_todos(self, task_id: str, ai_response: Dict) -> List[Dict[str, Any]]:
        """Add TODO items from AI response"""
        results = []
        
        for i, action in enumerate(ai_response['immediate_actions']):
            todo_result = self._add_single_todo(task_id, action)
            results.append({
                'index': i,
                'action': action,
                'success': todo_result['success'],
                'error': todo_result.get('error', None)
            })
        
        return results
    
    def _add_single_todo(self, task_id: str, todo_text: str) -> Dict[str, Any]:
        """Add single TODO item to task"""
        try:
            # Clean up TODO text (remove numbering, etc.)
            clean_text = self._clean_todo_text(todo_text)
            
            cmd = [
                sys.executable,
                str(self.project_root / self.todo_manager),
                "add",
                task_id,
                clean_text
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'output': result.stdout}
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'message': f"Failed to add TODO: {clean_text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Exception adding TODO: {todo_text}"
            }
    
    def _clean_todo_text(self, text: str) -> str:
        """Clean TODO text for task manager"""
        # Remove numbering (1., 2., etc.)
        import re
        text = re.sub(r'^\d+\.\s*', '', text.strip())
        
        # Remove backticks and code formatting
        text = text.replace('`', '')
        
        # Limit length
        if len(text) > 100:
            text = text[:97] + "..."
        
        return text
    
    def get_command_suggestions(self, partial_command: str) -> List[str]:
        """Get AI-powered command suggestions for autocomplete"""
        try:
            suggestions = []
            
            # Check against known command mappings
            for cmd in self.gui_command_mappings.keys():
                if partial_command.lower() in cmd.lower():
                    suggestions.append(cmd)
            
            # Add contextual suggestions based on system state
            contextual = self._get_contextual_suggestions(partial_command)
            suggestions.extend(contextual)
            
            return list(set(suggestions))[:5]  # Limit to 5 unique suggestions
            
        except Exception:
            return []
    
    def _get_contextual_suggestions(self, partial: str) -> List[str]:
        """Get contextual command suggestions"""
        contextual = {
            'deploy': ['deploy production', 'deploy monitoring', 'deploy security'],
            'fix': ['fix docker issues', 'fix gpu problems', 'fix network connectivity'],
            'setup': ['setup monitoring', 'setup gpu partitioning', 'setup security'],
            'check': ['check system health', 'check production status', 'check security'],
            'run': ['run tests', 'run security audit', 'run performance check']
        }
        
        suggestions = []
        for key, values in contextual.items():
            if key in partial.lower():
                suggestions.extend(values)
        
        return suggestions
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get statistics about GUI-created tasks"""
        try:
            # This would query the todo system for GUI-created tasks
            # For now, return mock data
            return {
                'total_gui_tasks': 0,
                'completed_gui_tasks': 0,
                'average_completion_time': '25 minutes',
                'most_common_commands': ['deploy production', 'fix issues', 'setup monitoring']
            }
        except Exception:
            return {'error': 'Could not retrieve task statistics'}

# Example usage and testing
if __name__ == "__main__":
    service = IntelligentTodoService()
    
    # Test commands
    test_commands = [
        "deploy production",
        "fix docker containers",
        "setup monitoring dashboard",
        "check system security"
    ]
    
    print("🧪 Testing Intelligent TODO Service")
    print("=" * 50)
    
    for cmd in test_commands:
        print(f"\n📝 Processing: '{cmd}'")
        result = service.process_gui_command(cmd)
        
        if result['success']:
            print(f"✅ Created task: {result.get('task_id', 'N/A')}")
            print(f"   TODOs: {result.get('todo_count', 0)}")
            print(f"   AI Confidence: {result.get('ai_confidence', 'N/A')}")
        else:
            print(f"❌ Failed: {result.get('message', 'Unknown error')}")
    
    print(f"\n🔍 Command suggestions for 'deploy':")
    suggestions = service.get_command_suggestions('deploy')
    for suggestion in suggestions:
        print(f"   💡 {suggestion}")