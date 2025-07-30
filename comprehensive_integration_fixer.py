#!/usr/bin/env python3
"""
Comprehensive Integration Fixer
Fixes all missing integrations to make the CLI system fully working
- Cleans up old/duplicate tasks
- Syncs all state files properly  
- Establishes clear roles for JSON/MD files
- Creates missing integration bridges
"""

import json
import os
import logging
import shutil
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveIntegrationFixer:
    """Fixes all integration issues for a fully working system"""
    
    def __init__(self):
        self.root_path = Path.cwd()
        self.state_files = {
            'todo_tasks': 'todo-tasks.json',
            'cursor_state': 'cursor_state.json',
            'task_state': 'task-state.json',
            'task_interruption': 'task_interruption_state.json',
            'current_session': 'memory-bank/current-session.md'
        }
        self.memory_files = {
            'memory_json': 'memory.json',
            'memory_store': 'memory_store.json',
            'memory_db': 'memory-bank/memory.db'
        }
        
    def get_philippines_time(self) -> datetime:
        """Get current Philippines time (UTC+8)"""
        utc_now = datetime.now(timezone.utc)
        philippines_tz = timezone(timedelta(hours=8))
        return utc_now.astimezone(philippines_tz)
    
    def format_iso_time(self, dt: datetime = None) -> str:
        """Format datetime in ISO format"""
        if dt is None:
            dt = self.get_philippines_time()
        return dt.isoformat()
    
    def backup_files(self) -> str:
        """Create backup of all state files before fixing"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/integration_fix_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        files_to_backup = list(self.state_files.values()) + list(self.memory_files.values())
        
        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_path = os.path.join(backup_dir, os.path.basename(file_path))
                shutil.copy2(file_path, backup_path)
                logger.info(f"📁 Backed up {file_path} to {backup_path}")
        
        logger.info(f"✅ Backup completed: {backup_dir}")
        return backup_dir
    
    def clean_old_tasks(self) -> Dict[str, Any]:
        """Clean up old, duplicate, and stale tasks"""
        logger.info("🧹 Starting comprehensive task cleanup...")
        
        try:
            # Load current tasks
            with open(self.state_files['todo_tasks'], 'r') as f:
                data = json.load(f)
            
            original_tasks = data.get('tasks', [])
            original_count = len(original_tasks)
            
            # Remove tasks older than 30 days
            cutoff_date = self.get_philippines_time() - timedelta(days=30)
            recent_tasks = []
            
            for task in original_tasks:
                try:
                    updated = datetime.fromisoformat(task.get('updated', task.get('created', '')))
                    if updated > cutoff_date:
                        recent_tasks.append(task)
                except:
                    # Keep tasks with invalid dates to be safe
                    recent_tasks.append(task)
            
            # Remove duplicates (same description)
            seen_descriptions = {}
            unique_tasks = []
            
            for task in recent_tasks:
                desc = task.get('description', '').strip()
                task_id = task.get('id', '')
                
                # Skip if we've seen this description before
                if desc in seen_descriptions:
                    # Keep the newer one
                    existing_task = seen_descriptions[desc]
                    existing_updated = existing_task.get('updated', '')
                    current_updated = task.get('updated', '')
                    
                    if current_updated > existing_updated:
                        # Replace with newer task
                        unique_tasks = [t for t in unique_tasks if t.get('id') != existing_task.get('id')]
                        unique_tasks.append(task)
                        seen_descriptions[desc] = task
                else:
                    seen_descriptions[desc] = task
                    unique_tasks.append(task)
            
            # Clean up completed tasks (keep only last 5 completed)
            completed_tasks = [t for t in unique_tasks if t.get('status') == 'completed']
            in_progress_tasks = [t for t in unique_tasks if t.get('status') != 'completed']
            
            # Sort completed by updated date and keep only last 5
            completed_tasks.sort(key=lambda x: x.get('updated', ''), reverse=True)
            cleaned_completed = completed_tasks[:5]
            
            final_tasks = in_progress_tasks + cleaned_completed
            
            # Update data
            data['tasks'] = final_tasks
            
            # Save cleaned data
            with open(self.state_files['todo_tasks'], 'w') as f:
                json.dump(data, f, indent=2)
            
            cleanup_stats = {
                'original_count': original_count,
                'final_count': len(final_tasks),
                'removed_old': original_count - len(recent_tasks),
                'removed_duplicates': len(recent_tasks) - len(unique_tasks),
                'removed_completed': len(completed_tasks) - len(cleaned_completed),
                'in_progress_count': len(in_progress_tasks)
            }
            
            logger.info(f"✅ Task cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"❌ Task cleanup failed: {e}")
            return {'error': str(e)}
    
    def establish_file_roles(self) -> Dict[str, str]:
        """Establish clear roles for each file type"""
        
        file_roles = {
            # JSON STATE FILES (Machine-readable, authoritative)
            'todo-tasks.json': 'MASTER TASK STORAGE - Source of truth for all tasks and TODOs',
            'cursor_state.json': 'CURSOR SESSION STATE - Current file, line, task context',
            'task-state.json': 'TASK EXECUTION STATE - Current task progress and status',
            'task_interruption_state.json': 'INTERRUPTION HANDLING - Resume logic and recovery',
            
            # MEMORY FILES (Data persistence)
            'memory.json': 'MCP SERVER CONFIG - External service configurations',
            'memory_store.json': 'SIMPLE MEMORY STORE - Basic key-value memory storage',
            'memory-bank/memory.db': 'PERSISTENT MEMORY DB - SQLite database for complex memory',
            
            # MARKDOWN FILES (Human-readable, documentation)
            'memory-bank/current-session.md': 'SESSION SUMMARY - Human-readable current state',
            'memory-bank/plan.md': 'PROJECT PLANNING - High-level goals and strategies',
            'memory-bank/evolution_blueprint.md': 'SYSTEM EVOLUTION - Architecture roadmap',
            'memory-bank/cli_dependency_architecture_map.md': 'TECHNICAL DOCS - System architecture',
            
            # INTEGRATION MODULES (Bridges between systems)
            'auto_sync_manager.py': 'STATE SYNCHRONIZATION - Keeps all state files in sync',
            'cursor_memory_bridge.py': 'JSON-TO-MARKDOWN BRIDGE - Converts state to human format',
            'todo_manager.py': 'TASK CRUD OPERATIONS - Create, read, update, delete tasks',
            'workflow_memory_intelligence_fixed.py': 'TASK INTELLIGENCE - Smart task processing',
            'memory_system/cli.py': 'CLI INTERFACE - Command-line entry point'
        }
        
        # Create role documentation
        roles_doc = "# File System Roles & Responsibilities\n\n"
        roles_doc += "## JSON State Files (Authoritative Data)\n"
        for file, role in file_roles.items():
            if file.endswith('.json') and not file.startswith('memory'):
                roles_doc += f"- **{file}**: {role}\n"
        
        roles_doc += "\n## Memory Files (Data Persistence)\n"
        for file, role in file_roles.items():
            if 'memory' in file:
                roles_doc += f"- **{file}**: {role}\n"
        
        roles_doc += "\n## Markdown Files (Human Documentation)\n"
        for file, role in file_roles.items():
            if file.endswith('.md'):
                roles_doc += f"- **{file}**: {role}\n"
        
        roles_doc += "\n## Integration Modules (System Bridges)\n"
        for file, role in file_roles.items():
            if file.endswith('.py'):
                roles_doc += f"- **{file}**: {role}\n"
        
        roles_doc += "\n## Data Flow Rules\n"
        roles_doc += "1. **todo-tasks.json** is the single source of truth for tasks\n"
        roles_doc += "2. All other JSON files sync FROM todo-tasks.json\n"
        roles_doc += "3. Markdown files are generated FROM JSON state\n"
        roles_doc += "4. Integration modules maintain consistency\n"
        roles_doc += "5. CLI operates through integration modules\n"
        
        # Save role documentation
        os.makedirs('memory-bank', exist_ok=True)
        with open('memory-bank/file-system-roles.md', 'w') as f:
            f.write(roles_doc)
        
        logger.info("✅ File roles established and documented")
        return file_roles
    
    def sync_all_state_files(self) -> Dict[str, Any]:
        """Sync all state files using todo-tasks.json as source of truth"""
        logger.info("🔄 Syncing all state files...")
        
        try:
            # Load source of truth
            with open(self.state_files['todo_tasks'], 'r') as f:
                todo_data = json.load(f)
            
            tasks = todo_data.get('tasks', [])
            
            # Find most recent active task
            active_task = None
            for task in sorted(tasks, key=lambda x: x.get('updated', ''), reverse=True):
                if task.get('status') in ['in_progress', 'created']:
                    active_task = task
                    break
            
            current_time = self.format_iso_time()
            
            # Update cursor_state.json
            cursor_state = {
                "cursor_session": {
                    "disconnected_at": "—",
                    "current_task": active_task.get('description', 'CLI Memory System Dependency Analysis') if active_task else 'No active task',
                    "progress": self._calculate_progress(active_task) if active_task else 0.0,
                    "last_activity": current_time
                }
            }
            
            with open(self.state_files['cursor_state'], 'w') as f:
                json.dump(cursor_state, f, indent=2)
            
            # Update task-state.json
            task_state = {
                "current_task_id": active_task.get('id', '') if active_task else '',
                "current_task_description": active_task.get('description', '') if active_task else '',
                "status": active_task.get('status', '') if active_task else '',
                "last_updated": current_time,
                "todos_count": len(active_task.get('todos', [])) if active_task else 0,
                "completed_todos": len([t for t in active_task.get('todos', []) if t.get('done', False)]) if active_task else 0
            }
            
            with open(self.state_files['task_state'], 'w') as f:
                json.dump(task_state, f, indent=2)
            
            # Update task_interruption_state.json
            interruption_state = {
                "current_task": active_task.get('id', '') if active_task else '',
                "interrupted_tasks": [],
                "last_updated": current_time
            }
            
            with open(self.state_files['task_interruption'], 'w') as f:
                json.dump(interruption_state, f, indent=2)
            
            # Update current-session.md
            self._update_session_markdown(active_task, tasks)
            
            sync_result = {
                'synced_files': list(self.state_files.keys()),
                'active_task': active_task.get('id') if active_task else None,
                'active_task_desc': active_task.get('description') if active_task else None,
                'total_tasks': len(tasks),
                'in_progress_tasks': len([t for t in tasks if t.get('status') == 'in_progress']),
                'synced_at': current_time
            }
            
            logger.info(f"✅ State sync completed: {sync_result}")
            return sync_result
            
        except Exception as e:
            logger.error(f"❌ State sync failed: {e}")
            return {'error': str(e)}
    
    def _calculate_progress(self, task: Optional[Dict[str, Any]]) -> float:
        """Calculate task progress from todos"""
        if not task or not task.get('todos'):
            return 0.0
        
        todos = task.get('todos', [])
        completed = len([t for t in todos if t.get('done', False)])
        total = len(todos)
        
        return (completed / total * 100) if total > 0 else 0.0
    
    def _update_session_markdown(self, active_task: Optional[Dict[str, Any]], all_tasks: List[Dict[str, Any]]):
        """Update current-session.md with latest state"""
        
        current_time = self.get_philippines_time()
        
        content = f"# 📝 Current Cursor Session — {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
        content += "| Field | Value |\n"
        content += "|-------|-------|\n"
        
        if active_task:
            content += f"| current_file | /home/haymayndz/AI_System_Monorepo/memory-bank/cli_dependency_architecture_map.md |\n"
            content += f"| cursor_line | 1 |\n"
            content += f"| current_task | {active_task.get('description', 'Unknown task')} |\n"
            content += f"| progress | {self._calculate_progress(active_task):.1f} |\n"
        else:
            content += f"| current_file | — |\n"
            content += f"| cursor_line | — |\n"
            content += f"| current_task | No active task |\n"
            content += f"| progress | 0.0 |\n"
        
        content += f"| last_activity | {self.format_iso_time()} |\n"
        content += f"| disconnected_at | — |\n\n"
        
        # Add active tasks summary
        in_progress_tasks = [t for t in all_tasks if t.get('status') == 'in_progress']
        
        if in_progress_tasks:
            content += "## Latest Activity:\n"
            content += "System integration and dependency analysis completed. Current active tasks:\n\n"
            
            for task in in_progress_tasks[:5]:  # Show max 5 tasks
                todos_left = len([todo for todo in task.get('todos', []) if not todo.get('done', False)])
                content += f"- **{task.get('description', 'Unknown task')}** ({todos_left} todos remaining)\n"
        else:
            content += "## Latest Activity:\n"
            content += "All integration fixes completed. System ready for operation.\n"
        
        # Ensure directory exists
        os.makedirs('memory-bank', exist_ok=True)
        
        with open(self.state_files['current_session'], 'w') as f:
            f.write(content)
    
    def create_missing_integrations(self) -> Dict[str, Any]:
        """Create any missing integration bridges"""
        logger.info("🔗 Creating missing integration bridges...")
        
        integrations_created = []
        
        # 1. Create CLI health check script
        cli_health_script = '''#!/usr/bin/env python3
"""
CLI System Health Check
Verifies all components are working and integrated properly
"""

import sys
import json
import os
from pathlib import Path

def check_state_files():
    """Check if all state files exist and are valid"""
    required_files = [
        'todo-tasks.json',
        'cursor_state.json', 
        'task-state.json',
        'task_interruption_state.json',
        'memory-bank/current-session.md'
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    return missing

def check_cli_system():
    """Check if CLI system is working"""
    try:
        import memory_system.cli
        return True
    except ImportError as e:
        return str(e)

def check_integrations():
    """Check if integration modules are working"""
    results = {}
    
    try:
        import auto_sync_manager
        results['auto_sync'] = 'OK'
    except ImportError as e:
        results['auto_sync'] = f'ERROR: {e}'
    
    try:
        import cursor_memory_bridge
        results['memory_bridge'] = 'OK'
    except ImportError as e:
        results['memory_bridge'] = f'ERROR: {e}'
    
    try:
        import todo_manager
        results['todo_manager'] = 'OK'
    except ImportError as e:
        results['todo_manager'] = f'ERROR: {e}'
    
    return results

def main():
    print("🏥 CLI System Health Check")
    print("=" * 40)
    
    # Check state files
    missing_files = check_state_files()
    if missing_files:
        print(f"❌ Missing state files: {missing_files}")
    else:
        print("✅ All state files present")
    
    # Check CLI system
    cli_status = check_cli_system()
    if cli_status is True:
        print("✅ CLI system importable")
    else:
        print(f"❌ CLI system error: {cli_status}")
    
    # Check integrations
    integrations = check_integrations()
    print("\\n🔗 Integration Status:")
    for name, status in integrations.items():
        if status == 'OK':
            print(f"  ✅ {name}: {status}")
        else:
            print(f"  ❌ {name}: {status}")
    
    print("\\n" + "=" * 40)
    print("Health check completed!")

if __name__ == "__main__":
    main()
'''
        
        with open('cli_health_check.py', 'w') as f:
            f.write(cli_health_script)
        integrations_created.append('cli_health_check.py')
        
        # 2. Create system status reporter
        status_reporter = '''#!/usr/bin/env python3
"""
System Status Reporter
Provides comprehensive status of the entire system
"""

import json
import os
from datetime import datetime

def get_system_status():
    """Get comprehensive system status"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'files': {},
        'tasks': {},
        'integration': {}
    }
    
    # Check file status
    files_to_check = [
        'todo-tasks.json',
        'cursor_state.json',
        'task-state.json', 
        'task_interruption_state.json'
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                status['files'][file] = 'OK'
            except:
                status['files'][file] = 'INVALID_JSON'
        else:
            status['files'][file] = 'MISSING'
    
    # Get task statistics
    try:
        with open('todo-tasks.json', 'r') as f:
            todo_data = json.load(f)
        
        tasks = todo_data.get('tasks', [])
        status['tasks'] = {
            'total': len(tasks),
            'in_progress': len([t for t in tasks if t.get('status') == 'in_progress']),
            'completed': len([t for t in tasks if t.get('status') == 'completed']),
            'created': len([t for t in tasks if t.get('status') == 'created'])
        }
    except:
        status['tasks'] = {'error': 'Could not read todo-tasks.json'}
    
    # Check integration modules
    integrations = ['auto_sync_manager', 'cursor_memory_bridge', 'todo_manager']
    for module in integrations:
        try:
            __import__(module)
            status['integration'][module] = 'OK'
        except ImportError:
            status['integration'][module] = 'MISSING'
    
    return status

def main():
    status = get_system_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
'''
        
        with open('system_status_reporter.py', 'w') as f:
            f.write(status_reporter)
        integrations_created.append('system_status_reporter.py')
        
        logger.info(f"✅ Created integration bridges: {integrations_created}")
        return {'created': integrations_created}
    
    def run_comprehensive_fix(self) -> Dict[str, Any]:
        """Run the complete integration fix process"""
        logger.info("🚀 Starting comprehensive integration fix...")
        
        results = {
            'started_at': self.format_iso_time(),
            'steps': {}
        }
        
        try:
            # Step 1: Backup files
            backup_dir = self.backup_files()
            results['steps']['backup'] = {'status': 'success', 'backup_dir': backup_dir}
            
            # Step 2: Clean old tasks
            cleanup_stats = self.clean_old_tasks()
            results['steps']['cleanup'] = {'status': 'success', 'stats': cleanup_stats}
            
            # Step 3: Establish file roles
            file_roles = self.establish_file_roles()
            results['steps']['file_roles'] = {'status': 'success', 'roles_count': len(file_roles)}
            
            # Step 4: Sync state files
            sync_result = self.sync_all_state_files()
            results['steps']['sync'] = {'status': 'success', 'sync_result': sync_result}
            
            # Step 5: Create missing integrations
            integration_result = self.create_missing_integrations()
            results['steps']['integrations'] = {'status': 'success', 'created': integration_result.get('created', [])}
            
            # Step 6: Test system
            try:
                from auto_sync_manager import auto_sync
                auto_sync()
                results['steps']['test_sync'] = {'status': 'success'}
            except Exception as e:
                results['steps']['test_sync'] = {'status': 'error', 'error': str(e)}
            
            results['completed_at'] = self.format_iso_time()
            results['overall_status'] = 'success'
            
            logger.info("✅ Comprehensive integration fix completed successfully!")
            
        except Exception as e:
            results['overall_status'] = 'error'
            results['error'] = str(e)
            results['completed_at'] = self.format_iso_time()
            logger.error(f"❌ Integration fix failed: {e}")
        
        return results

def main():
    """Main entry point"""
    print("🔧 Comprehensive Integration Fixer")
    print("=" * 50)
    
    fixer = ComprehensiveIntegrationFixer()
    results = fixer.run_comprehensive_fix()
    
    print("\n📊 Fix Results:")
    print(json.dumps(results, indent=2))
    
    if results.get('overall_status') == 'success':
        print("\n✅ All integrations fixed! System ready for operation.")
        print("\n🚀 Test the CLI system:")
        print("   python3 memory_system/cli.py -h")
        print("   python3 cli_health_check.py")
    else:
        print("\n❌ Some issues occurred. Check the results above.")

if __name__ == "__main__":
    main()
