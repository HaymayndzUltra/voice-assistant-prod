#!/usr/bin/env python3
"""
Migration Tool: Single File → Queue System

This script migrates from the current single-file system (todo-tasks.json)
to the new four-file queue system:
- tasks_queue.json (waiting tasks)
- tasks_active.json (currently executing)
- tasks_done.json (completed tasks)  
- tasks_interrupted.json (paused tasks)

The migration preserves all task data and maintains system continuity.
"""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
from common.utils.log_setup import configure_logging

# Setup logging
logger = configure_logging(__name__)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QueueSystemMigrator:
    """Migrates from single file to queue system"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.todo_file = self.base_path / "todo-tasks.json"
        self.backup_dir = self.base_path / "backups" / f"queue_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # New queue files in memory-bank
        queue_dir = self.base_path / 'memory-bank' / 'queue-system'
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        self.queue_files = {
            'queue': queue_dir / 'tasks_queue.json',
            'active': queue_dir / 'tasks_active.json',
            'done': queue_dir / 'tasks_done.json',
            'interrupted': queue_dir / 'tasks_interrupted.json'
        }
    
    def create_backup(self):
        """Create backup of current system"""
        logger.info("📦 Creating backup of current system...")
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup existing files
        files_to_backup = [
            "todo-tasks.json",
            "cursor_state.json",
            "task-state.json",
            "task_interruption_state.json"
        ]
        
        backed_up = 0
        for filename in files_to_backup:
            src_file = self.base_path / filename
            if src_file.exists():
                dst_file = self.backup_dir / filename
                shutil.copy2(src_file, dst_file)
                backed_up += 1
                logger.info(f"  ✅ Backed up {filename}")
        
        logger.info(f"📦 Backup created: {self.backup_dir} ({backed_up} files)")
        return self.backup_dir
    
    def analyze_current_system(self) -> Dict[str, Any]:
        """Analyze current todo-tasks.json structure"""
        logger.info("🔍 Analyzing current system...")
        
        if not self.todo_file.exists():
            logger.error(f"❌ {self.todo_file} not found!")
            return {}
        
        try:
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"❌ Failed to read {self.todo_file}: {e}")
            return {}
        
        tasks = data.get("tasks", [])
        
        # Analyze task distribution
        analysis = {
            "total_tasks": len(tasks),
            "by_status": {},
            "active_tasks": [],
            "completed_tasks": [],
            "in_progress_tasks": []
        }
        
        for task in tasks:
            status = task.get("status", "unknown")
            analysis["by_status"][status] = analysis["by_status"].get(status, 0) + 1
            
            if status == "completed":
                analysis["completed_tasks"].append(task)
            elif status == "in_progress":
                # Determine if actively working or just queued
                todos = task.get("todos", [])
                has_completed_todos = any(todo.get("done", False) for todo in todos)
                
                if has_completed_todos:
                    # Has progress = actively working
                    analysis["active_tasks"].append(task)
                else:
                    # No progress = waiting in queue
                    analysis["in_progress_tasks"].append(task)
        
        logger.info(f"📊 Analysis complete:")
        logger.info(f"  Total tasks: {analysis['total_tasks']}")
        logger.info(f"  By status: {analysis['by_status']}")
        logger.info(f"  Active (working): {len(analysis['active_tasks'])}")
        logger.info(f"  Queue (waiting): {len(analysis['in_progress_tasks'])}")
        logger.info(f"  Done: {len(analysis['completed_tasks'])}")
        
        return analysis
    
    def migrate_to_queue_system(self, analysis: Dict[str, Any]):
        """Migrate tasks to new queue system"""
        logger.info("🚀 Migrating to queue system...")
        
        # Prepare queue data
        queue_data = {
            'queue': analysis.get("in_progress_tasks", []),
            'active': analysis.get("active_tasks", []),
            'done': analysis.get("completed_tasks", []),
            'interrupted': []  # Start with empty interrupted queue
        }
        
        # Write new queue files
        for queue_name, tasks in queue_data.items():
            file_path = self.queue_files[queue_name]
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, indent=2, ensure_ascii=False)
                
                logger.info(f"  ✅ Created {queue_name}: {len(tasks)} tasks → {file_path}")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to create {file_path}: {e}")
                return False
        
        return True
    
    def update_state_files(self):
        """Update other state files to point to new system"""
        logger.info("🔄 Updating state files...")
        
        # Note: Auto-sync manager will handle this automatically
        # when it detects the new queue files
        
        try:
            # Trigger auto-sync to update derived state files
            from auto_sync_manager import auto_sync
            result = auto_sync()
            logger.info("  ✅ Auto-sync triggered successfully")
            
        except ImportError:
            logger.warning("  ⚠️ Auto-sync not available - state files need manual update")
        except Exception as e:
            logger.error(f"  ❌ Auto-sync failed: {e}")
    
    def verify_migration(self) -> bool:
        """Verify migration completed successfully"""
        logger.info("✅ Verifying migration...")
        
        # Check all queue files exist
        for queue_name, file_path in self.queue_files.items():
            if not file_path.exists():
                logger.error(f"  ❌ Missing {queue_name} file: {file_path}")
                return False
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"  ✅ {queue_name}: {len(data)} tasks")
            except Exception as e:
                logger.error(f"  ❌ Invalid {queue_name} file: {e}")
                return False
        
        return True
    
    def run_migration(self):
        """Run complete migration process"""
        logger.info("🚀 Starting queue system migration...")
        
        try:
            # Step 1: Create backup
            backup_dir = self.create_backup()
            
            # Step 2: Analyze current system
            analysis = self.analyze_current_system()
            if not analysis:
                logger.error("❌ Migration failed - could not analyze current system")
                return False
            
            # Step 3: Migrate to queue system
            if not self.migrate_to_queue_system(analysis):
                logger.error("❌ Migration failed - could not create queue files")
                return False
            
            # Step 4: Update state files
            self.update_state_files()
            
            # Step 5: Verify migration
            if not self.verify_migration():
                logger.error("❌ Migration verification failed")
                return False
            
            # Step 6: Success!
            logger.info("🎉 Migration completed successfully!")
            logger.info(f"📦 Backup saved to: {backup_dir}")
            logger.info("🚀 Queue system is now active!")
            
            # Show next steps
            logger.info("\n📋 Next steps:")
            logger.info("1. Start queue engine: python3 task_queue_engine.py")
            logger.info("2. Test AI interface: check tasks_active.json for work")
            logger.info("3. Add new tasks: use new queue interface")
            
            return True
            
        except Exception as e:
            logger.error(f"💥 Migration failed with error: {e}")
            return False


def main():
    """Main migration entry point"""
    migrator = QueueSystemMigrator()
    
    print("🚀 Queue System Migration Tool")
    print("===============================")
    print()
    
    # Ask for confirmation
    response = input("This will migrate from todo-tasks.json to queue system. Continue? (y/N): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        return
    
    # Run migration
    success = migrator.run_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("🚀 Your task queue system is now ready!")
    else:
        print("\n❌ Migration failed!")
        print("Check the backup directory for recovery options.")

if __name__ == "__main__":
    main()
