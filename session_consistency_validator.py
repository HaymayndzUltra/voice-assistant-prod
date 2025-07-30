#!/usr/bin/env python3
"""
Session Consistency Validator
Ensures all AI assistants (Cascade, Cursor, etc.) follow the same session protocols
Provides validation and automatic correction for inconsistent states
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

class SessionConsistencyValidator:
    """Validates and enforces session consistency across all AI assistants"""
    
    def __init__(self):
        self.state_files = {
            'cursor_state': 'cursor_state.json',
            'task_interruption': 'memory-bank/task_interruption_state.json', 
            'current_session': 'memory-bank/current-session.md',
            'todo_tasks': 'memory-bank/queue-system/tasks_active.json'  # Source of truth
        }
        self.validation_errors = []
        self.fixes_applied = []
    
    def validate_all_states(self) -> Dict[str, Any]:
        """Comprehensive validation of all session states"""
        
        print("🔍 Running comprehensive session consistency validation...")
        
        results = {
            'is_consistent': True,
            'errors': [],
            'warnings': [],
            'fixes_applied': [],
            'source_of_truth': None
        }
        
        try:
            # Step 1: Establish source of truth
            source_of_truth = self._establish_source_of_truth()
            results['source_of_truth'] = source_of_truth
            
            # Step 2: Validate each state file
            for state_name, file_path in self.state_files.items():
                validation_result = self._validate_state_file(state_name, file_path, source_of_truth)
                
                if not validation_result['is_valid']:
                    results['is_consistent'] = False
                    results['errors'].extend(validation_result['errors'])
                
                results['warnings'].extend(validation_result.get('warnings', []))
            
            # Step 3: Cross-reference validation
            cross_ref_result = self._cross_reference_validation()
            if not cross_ref_result['is_consistent']:
                results['is_consistent'] = False
                results['errors'].extend(cross_ref_result['errors'])
            
            # Step 4: Auto-fix if enabled
            if not results['is_consistent']:
                fixes = self._apply_automatic_fixes(results['errors'])
                results['fixes_applied'] = fixes
                
                # Re-validate after fixes
                if fixes:
                    print("🔄 Re-validating after automatic fixes...")
                    return self.validate_all_states()
            
        except Exception as e:
            results['is_consistent'] = False
            results['errors'].append(f"Validation system error: {str(e)}")
        
        return results
    
    def _establish_source_of_truth(self) -> Dict[str, Any]:
        """Establish which state represents the source of truth"""
        
        # Priority order: todo-tasks.json > cursor_state.json > others
        
        try:
            # Check tasks_active.json first (highest priority)
            todo_file = 'memory-bank/queue-system/tasks_active.json'
            if os.path.exists(todo_file):
                with open(todo_file, 'r') as f:
                    todo_data = json.load(f)
                    # Handle list format from todo_manager
                    if isinstance(todo_data, list) and todo_data:
                        latest_task = max(todo_data, 
                                        key=lambda x: x.get('created_at', ''))
                        return {
                            'source': 'tasks_active.json',
                            'current_task': latest_task.get('description'),
                            'status': latest_task.get('status'),
                            'last_updated': latest_task.get('updated_at')
                        }
            
            # Fallback to cursor_state.json
            if os.path.exists('cursor_state.json'):
                with open('cursor_state.json', 'r') as f:
                    cursor_data = json.load(f)
                    session = cursor_data.get('cursor_session', {})
                    return {
                        'source': 'cursor_state.json',
                        'current_task': session.get('current_task'),
                        'status': session.get('completion_status', 'in_progress'),
                        'last_updated': session.get('last_activity')
                    }
                    
        except Exception as e:
            print(f"⚠️ Error establishing source of truth: {e}")
        
        return {
            'source': 'default',
            'current_task': 'No active task',
            'status': 'idle',
            'last_updated': datetime.now().isoformat()
        }
    
    def _validate_state_file(self, state_name: str, file_path: str, 
                           source_of_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual state file against source of truth"""
        
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if not os.path.exists(file_path):
                result['is_valid'] = False
                result['errors'].append(f"Missing state file: {file_path}")
                return result
            
            if file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # Validate JSON structure and content
                validation = self._validate_json_state(state_name, data, source_of_truth)
                result.update(validation)
                
            elif file_path.endswith('.md'):
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Validate markdown content
                validation = self._validate_markdown_state(state_name, content, source_of_truth)
                result.update(validation)
                
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Error validating {file_path}: {str(e)}")
        
        return result
    
    def _validate_json_state(self, state_name: str, data: Dict[str, Any], 
                            source_of_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON state file structure and content"""
        
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        if state_name == 'cursor_state':
            session = data.get('cursor_session', {})
            task = session.get('current_task', '')
            
            if source_of_truth['current_task'] and task != source_of_truth['current_task']:
                result['warnings'].append(
                    f"cursor_state task '{task}' differs from source of truth '{source_of_truth['current_task']}'"
                )
        
        elif state_name == 'task_interruption':
            current_task = data.get('current_task')
            if source_of_truth['status'] == 'completed' and current_task:
                result['warnings'].append(
                    f"task_interruption shows active task but source indicates completion"
                )
        
        return result
    
    def _validate_markdown_state(self, state_name: str, content: str, 
                                source_of_truth: Dict[str, Any]) -> Dict[str, Any]:
        """Validate markdown state file content"""
        
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        if state_name == 'current_session':
            if source_of_truth['current_task']:
                if source_of_truth['current_task'] not in content:
                    result['warnings'].append(
                        f"current-session.md doesn't contain source of truth task"
                    )
        
        return result
    
    def _cross_reference_validation(self) -> Dict[str, Any]:
        """Cross-reference validation between all state files"""
        
        result = {'is_consistent': True, 'errors': []}
        
        try:
            # Load all JSON states
            states = {}
            
            for state_name, file_path in self.state_files.items():
                if file_path.endswith('.json') and os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        states[state_name] = json.load(f)
            
            # Cross-reference key fields
            if 'cursor_state' in states and 'task_interruption' in states:
                cursor_task = states['cursor_state'].get('cursor_session', {}).get('current_task')
                interrupt_task = states['task_interruption'].get('current_task')
                
                if cursor_task and interrupt_task and cursor_task != interrupt_task:
                    result['is_consistent'] = False
                    result['errors'].append(
                        f"Task mismatch: cursor_state='{cursor_task}' vs task_interruption='{interrupt_task}'"
                    )
        
        except Exception as e:
            result['is_consistent'] = False
            result['errors'].append(f"Cross-reference validation error: {str(e)}")
        
        return result
    
    def _apply_automatic_fixes(self, errors: List[str]) -> List[str]:
        """Apply automatic fixes for common consistency issues"""
        
        fixes_applied = []
        
        for error in errors:
            if "Missing state file" in error:
                # Create missing state files
                if "cursor_state.json" in error:
                    self._create_default_cursor_state()
                    fixes_applied.append("Created default cursor_state.json")
                
                elif "task_interruption_state.json" in error:
                    self._create_default_task_interruption_state()
                    fixes_applied.append("Created default task_interruption_state.json")
            
            elif "Task mismatch" in error:
                # Sync task information
                self._sync_task_states()
                fixes_applied.append("Synchronized task states")
        
        return fixes_applied
    
    def _create_default_cursor_state(self):
        """Create default cursor state file"""
        default_state = {
            "cursor_session": {
                "disconnected_at": datetime.now().isoformat(),
                "current_task": "System initialization",
                "progress": 0.0,
                "last_activity": datetime.now().isoformat(),
                "completion_status": "initialized"
            }
        }
        
        with open('cursor_state.json', 'w') as f:
            json.dump(default_state, f, indent=2)
    
    def _create_default_task_interruption_state(self):
        """Create default task interruption state file"""
        default_state = {
            "current_task": None,
            "interrupted_tasks": [],
            "last_updated": datetime.now().isoformat()
        }
        
        os.makedirs('memory-bank', exist_ok=True)
        with open('memory-bank/task_interruption_state.json', 'w') as f:
            json.dump(default_state, f, indent=2)
    
    def _sync_task_states(self):
        """Synchronize task states across all files"""
        # Use existing auto_state_sync_hook for this
        os.system("python3 auto_state_sync_hook.py --sync")
    
    def generate_validation_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive validation report"""
        
        report = f"""
# 🔍 SESSION CONSISTENCY VALIDATION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

## 📊 OVERALL STATUS: {'✅ CONSISTENT' if results['is_consistent'] else '⚠️ INCONSISTENT'}

### 🎯 SOURCE OF TRUTH:
- **Source:** {results.get('source_of_truth', {}).get('source', 'Unknown')}
- **Current Task:** {results.get('source_of_truth', {}).get('current_task', 'None')}
- **Status:** {results.get('source_of_truth', {}).get('status', 'Unknown')}

### ❌ ERRORS FOUND: {len(results.get('errors', []))}
"""
        
        for error in results.get('errors', []):
            report += f"- {error}\n"
        
        report += f"\n### ⚠️ WARNINGS: {len(results.get('warnings', []))}\n"
        for warning in results.get('warnings', []):
            report += f"- {warning}\n"
        
        report += f"\n### 🔧 FIXES APPLIED: {len(results.get('fixes_applied', []))}\n"
        for fix in results.get('fixes_applied', []):
            report += f"- {fix}\n"
        
        report += "\n### 💡 RECOMMENDATIONS:\n"
        if not results['is_consistent']:
            report += "- Run session consistency validation on every session start\n"
            report += "- Enable automatic state synchronization after major tasks\n"
            report += "- Ensure all AI assistants follow the same workflow protocols\n"
        else:
            report += "- ✅ All state files are consistent\n"
            report += "- ✅ Session continuity is maintained\n"
            report += "- ✅ Ready for multi-assistant collaboration\n"
        
        return report

def main():
    validator = SessionConsistencyValidator()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        # Generate detailed report
        results = validator.validate_all_states()
        report = validator.generate_validation_report(results)
        
        # Save report
        with open('session_consistency_report.md', 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\n📋 Full report saved to: session_consistency_report.md")
        
    else:
        # Quick validation
        results = validator.validate_all_states()
        
        if results['is_consistent']:
            print("✅ All session states are consistent!")
        else:
            print("⚠️ Session inconsistencies detected:")
            for error in results['errors']:
                print(f"  - {error}")
            
            if results['fixes_applied']:
                print("\n🔧 Automatic fixes applied:")
                for fix in results['fixes_applied']:
                    print(f"  - {fix}")

if __name__ == "__main__":
    main()
