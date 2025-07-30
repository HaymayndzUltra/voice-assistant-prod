#!/usr/bin/env python3
"""
Task Queue Engine - Automatic Queue Management System

This module implements a fully automatic task queue management system that:
1. Monitors tasks_active.json for completed tasks
2. Automatically moves completed tasks to tasks_done.json
3. Automatically pulls new work from tasks_queue.json when active is empty
4. Handles task interruptions and resumption
5. Provides real-time file watching for instant detection

The system ensures AI assistants (Cursor/Cascade) only need to focus on
tasks_active.json while all queue management is handled autonomously.
"""

import json
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskQueueEngine:
    """Automatic task queue management engine"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.check_interval = 3  # Check every 3 seconds
        self.running = False
        self.monitor_thread = None
        self.file_observer = None
        
        # Queue file paths in memory-bank
        queue_dir = self.base_path / 'memory-bank' / 'queue-system'
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        self.queue_files = {
            'queue': queue_dir / 'tasks_queue.json',
            'active': queue_dir / 'tasks_active.json', 
            'done': queue_dir / 'tasks_done.json',
            'interrupted': queue_dir / 'tasks_interrupted.json'
        }
        
        # Initialize queue files if they don't exist
        self._initialize_queue_files()
        
        logger.info("🚀 TaskQueueEngine initialized")
    
    def _initialize_queue_files(self):
        """Create queue files if they don't exist"""
        for name, file_path in self.queue_files.items():
            if not file_path.exists():
                self._write_json(file_path, [])
                logger.info(f"📁 Created {name} queue file: {file_path}")
    
    def _read_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """Safely read JSON file"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"❌ Failed to read {file_path}: {e}")
            return []
    
    def _write_json(self, file_path: Path, data: List[Dict[str, Any]]):
        """Safely write JSON file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Failed to write {file_path}: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()
    
    def _detect_completed_tasks(self) -> List[Dict[str, Any]]:
        """Detect completed tasks in tasks_active.json"""
        active_tasks = self._read_json(self.queue_files['active'])
        completed_tasks = []
        
        for task in active_tasks:
            # Check if task is marked as completed
            if task.get("status") == "completed":
                completed_tasks.append(task)
                continue
            
            # Check if all TODOs are done
            todos = task.get("todos", [])
            if todos and all(todo.get("done", False) for todo in todos):
                # Mark task as completed
                task["status"] = "completed"
                task["completed_at"] = self._get_timestamp()
                completed_tasks.append(task)
        
        return completed_tasks
    
    def _move_completed_tasks(self):
        """Move completed tasks from active to done"""
        completed_tasks = self._detect_completed_tasks()
        
        if not completed_tasks:
            return 0
        
        # Read current state
        active_tasks = self._read_json(self.queue_files['active'])
        done_tasks = self._read_json(self.queue_files['done'])
        
        # Remove completed from active
        remaining_active = [
            task for task in active_tasks 
            if task not in completed_tasks
        ]
        
        # Add completed to done
        done_tasks.extend(completed_tasks)
        
        # Write updated files
        self._write_json(self.queue_files['active'], remaining_active)
        self._write_json(self.queue_files['done'], done_tasks)
        
        logger.info(f"✅ Moved {len(completed_tasks)} completed tasks to done")
        return len(completed_tasks)
    
    def _is_active_idle(self) -> bool:
        """Check if active queue needs work"""
        active_tasks = self._read_json(self.queue_files['active'])
        
        # Empty = idle
        if not active_tasks:
            return True
        
        # All completed = idle (waiting for cleanup)
        working_tasks = [
            task for task in active_tasks 
            if task.get("status") != "completed"
        ]
        
        return len(working_tasks) == 0
    
    def _has_interrupted_tasks(self) -> bool:
        """Check if there are interrupted tasks to resume"""
        interrupted_tasks = self._read_json(self.queue_files['interrupted'])
        return len(interrupted_tasks) > 0
    
    def _has_queued_tasks(self) -> bool:
        """Check if there are queued tasks to start"""
        queue_tasks = self._read_json(self.queue_files['queue'])
        return len(queue_tasks) > 0
    
    def _resume_interrupted_tasks(self):
        """Move interrupted tasks back to active"""
        interrupted_tasks = self._read_json(self.queue_files['interrupted'])
        
        if not interrupted_tasks:
            return 0
        
        # Move all interrupted tasks to active
        current_active = self._read_json(self.queue_files['active'])
        current_active.extend(interrupted_tasks)
        
        # Update files
        self._write_json(self.queue_files['active'], current_active)
        self._write_json(self.queue_files['interrupted'], [])
        
        logger.info(f"🔄 Resumed {len(interrupted_tasks)} interrupted tasks")
        return len(interrupted_tasks)
    
    def _pull_from_queue(self, batch_size: int = 3):
        """Pull batch of tasks from queue to active"""
        queue_tasks = self._read_json(self.queue_files['queue'])
        
        if not queue_tasks:
            return 0
        
        # Take first batch
        batch = queue_tasks[:batch_size]
        remaining = queue_tasks[batch_size:]
        
        # Update files
        current_active = self._read_json(self.queue_files['active'])
        current_active.extend(batch)
        
        self._write_json(self.queue_files['active'], current_active)
        self._write_json(self.queue_files['queue'], remaining)
        
        logger.info(f"🚀 Pulled {len(batch)} tasks from queue to active")
        return len(batch)
    
    def _manage_queue_flow(self):
        """Main queue management logic"""
        try:
            # Step 1: Handle completed tasks
            completed_count = self._move_completed_tasks()
            
            # Step 2: Check if active is idle
            if self._is_active_idle():
                
                # Priority 1: Resume interrupted work
                if self._has_interrupted_tasks():
                    self._resume_interrupted_tasks()
                    
                # Priority 2: Pull new work from queue
                elif self._has_queued_tasks():
                    self._pull_from_queue()
                    
                else:
                    # All queues empty - system idle
                    if completed_count > 0:  # Only log if we just completed something
                        logger.info("✅ All queues empty - system idle")
            
        except Exception as e:
            logger.error(f"❌ Queue management error: {e}")
    
    def start_monitoring(self):
        """Start automatic queue monitoring"""
        if self.running:
            logger.warning("⚠️ Queue monitoring already running")
            return
        
        self.running = True
        
        def monitor_loop():
            logger.info("🤖 Starting automatic queue monitoring...")
            
            while self.running:
                try:
                    self._manage_queue_flow()
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"💥 Monitor loop error: {e}")
                    time.sleep(10)  # Wait longer on error
            
            logger.info("⏹️ Queue monitoring stopped")
        
        # Start monitoring in background thread
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("✅ Automatic queue monitoring started")
    
    def stop_monitoring(self):
        """Stop automatic queue monitoring"""
        if not self.running:
            return
        
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("🛑 Queue monitoring stopped")
    
    def add_task_to_queue(self, task: Dict[str, Any]):
        """Add a new task to the queue"""
        queue_tasks = self._read_json(self.queue_files['queue'])
        
        # Add timestamp if not present
        if 'created' not in task:
            task['created'] = self._get_timestamp()
        
        queue_tasks.append(task)
        self._write_json(self.queue_files['queue'], queue_tasks)
        
        logger.info(f"📋 Added task to queue: {task.get('description', 'Unknown')[:50]}...")
        
        # Check if we should auto-pull to active
        if self._is_active_idle():
            self._manage_queue_flow()
    
    def interrupt_current_tasks(self, urgent_task: Dict[str, Any]):
        """Interrupt current tasks with urgent work"""
        # Move current active tasks to interrupted
        current_active = self._read_json(self.queue_files['active'])
        interrupted_tasks = self._read_json(self.queue_files['interrupted'])
        
        # Add current active to interrupted
        interrupted_tasks.extend(current_active)
        
        # Set urgent task as new active
        urgent_task['created'] = self._get_timestamp()
        urgent_task['priority'] = 'urgent'
        
        # Update files
        self._write_json(self.queue_files['interrupted'], interrupted_tasks)
        self._write_json(self.queue_files['active'], [urgent_task])
        
        logger.info(f"🚨 Interrupted {len(current_active)} tasks for urgent work")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queue_count": len(self._read_json(self.queue_files['queue'])),
            "active_count": len(self._read_json(self.queue_files['active'])),
            "done_count": len(self._read_json(self.queue_files['done'])),
            "interrupted_count": len(self._read_json(self.queue_files['interrupted'])),
            "is_idle": self._is_active_idle(),
            "monitoring": self.running,
            "timestamp": self._get_timestamp()
        }


class TaskFileWatcher(FileSystemEventHandler):
    """Real-time file watcher for task files"""
    
    def __init__(self, queue_engine: TaskQueueEngine):
        self.queue_engine = queue_engine
        self.last_check = 0
        self.debounce_interval = 1  # 1 second debounce
    
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        # Only watch tasks_active.json in memory-bank/queue-system
        if not event.src_path.endswith("memory-bank/queue-system/tasks_active.json"):
            return
        
        # Debounce rapid file changes
        current_time = time.time()
        if current_time - self.last_check < self.debounce_interval:
            return
        
        self.last_check = current_time
        
        logger.debug("👁️ Detected tasks_active.json change - checking queue flow")
        
        # Trigger queue management
        threading.Thread(
            target=self.queue_engine._manage_queue_flow, 
            daemon=True
        ).start()


def start_queue_engine_with_watcher(base_path: str = ".") -> TaskQueueEngine:
    """Start queue engine with real-time file watching"""
    
    # Create engine
    engine = TaskQueueEngine(base_path)
    
    # Start monitoring
    engine.start_monitoring()
    
    # Start file watcher
    try:
        from watchdog.observers import Observer
        
        watcher = TaskFileWatcher(engine)
        observer = Observer()
        queue_watch_path = Path(base_path) / 'memory-bank' / 'queue-system'
        queue_watch_path.mkdir(parents=True, exist_ok=True)
        observer.schedule(watcher, path=str(queue_watch_path), recursive=False)
        observer.start()
        
        # Store observer for cleanup
        engine.file_observer = observer
        
        logger.info("👁️ Real-time file watching started")
        
    except ImportError:
        logger.warning("⚠️ watchdog not available - file watching disabled")
    except Exception as e:
        logger.error(f"❌ Failed to start file watcher: {e}")
    
    return engine


# Global queue engine instance
_queue_engine = None

def get_queue_engine() -> TaskQueueEngine:
    """Get global queue engine instance"""
    global _queue_engine
    if _queue_engine is None:
        _queue_engine = start_queue_engine_with_watcher()
    return _queue_engine


if __name__ == "__main__":
    # Test the queue engine
    engine = start_queue_engine_with_watcher()
    
    try:
        print("🚀 Task Queue Engine started")
        print("Status:", engine.get_status())
        
        # Keep running
        while True:
            time.sleep(5)
            status = engine.get_status()
            print(f"📊 Status: Q:{status['queue_count']} A:{status['active_count']} D:{status['done_count']} I:{status['interrupted_count']}")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping queue engine...")
        engine.stop_monitoring()
        if engine.file_observer:
            engine.file_observer.stop()
