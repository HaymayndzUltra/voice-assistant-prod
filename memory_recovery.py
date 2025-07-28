#!/usr/bin/env python3
"""
Memory Recovery System - Recovers from memory loss and corruption

This script provides tools to recover from various memory loss scenarios
and validate the integrity of the memory system.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from cursor_session_manager import session_manager
from conversation_context_manager import conversation_manager


class MemoryRecoverySystem:
    """Handles memory recovery and integrity validation."""
    
    def __init__(self):
        self.recovery_log = []
    
    def log_recovery_action(self, action: str, details: str) -> None:
        """Log recovery actions for audit trail."""
        self.recovery_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        })
    
    def validate_all_memory(self) -> Dict[str, bool]:
        """Validate integrity of all memory components."""
        results = {
            "cursor_state": session_manager.validate_integrity(),
            "conversation_context": conversation_manager.validate_integrity(),
            "task_state": self._validate_task_state(),
            "todo_tasks": self._validate_todo_tasks()
        }
        return results
    
    def _validate_task_state(self) -> bool:
        """Validate task-state.json integrity."""
        try:
            if not os.path.exists("task-state.json"):
                return False
            with open("task-state.json", "r", encoding="utf-8") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, OSError):
            return False
    
    def _validate_todo_tasks(self) -> bool:
        """Validate todo-tasks.json integrity."""
        try:
            if not os.path.exists("todo-tasks.json"):
                return False
            with open("todo-tasks.json", "r", encoding="utf-8") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, OSError):
            return False
    
    def recover_from_backups(self) -> Dict[str, bool]:
        """Attempt recovery from backup files."""
        recovery_results = {}
        
        # Recover cursor state
        if os.path.exists("cursor_state.json.backup"):
            try:
                shutil.copy("cursor_state.json.backup", "cursor_state.json")
                recovery_results["cursor_state"] = True
                self.log_recovery_action("cursor_state_recovery", "Restored from backup")
            except OSError:
                recovery_results["cursor_state"] = False
                self.log_recovery_action("cursor_state_recovery", "Failed to restore from backup")
        
        # Recover conversation context
        if os.path.exists("conversation-context.json.backup"):
            try:
                shutil.copy("conversation-context.json.backup", "conversation-context.json")
                recovery_results["conversation_context"] = True
                self.log_recovery_action("conversation_context_recovery", "Restored from backup")
            except OSError:
                recovery_results["conversation_context"] = False
                self.log_recovery_action("conversation_context_recovery", "Failed to restore from backup")
        
        return recovery_results
    
    def create_snapshot(self) -> str:
        """Create a complete memory snapshot for backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = f"memory_snapshot_{timestamp}"
        
        try:
            os.makedirs(snapshot_dir, exist_ok=True)
            
            # Copy all memory files
            memory_files = [
                "cursor_state.json",
                "conversation-context.json", 
                "task-state.json",
                "todo-tasks.json"
            ]
            
            for file in memory_files:
                if os.path.exists(file):
                    shutil.copy(file, snapshot_dir)
            
            # Copy backup files
            backup_files = [f for f in os.listdir('.') if f.endswith('.backup')]
            for backup in backup_files:
                shutil.copy(backup, snapshot_dir)
            
            # Create snapshot metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "files_copied": memory_files + backup_files,
                "integrity_check": self.validate_all_memory()
            }
            
            with open(f"{snapshot_dir}/snapshot_metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            self.log_recovery_action("snapshot_created", f"Created snapshot: {snapshot_dir}")
            return snapshot_dir
            
        except OSError as e:
            self.log_recovery_action("snapshot_failed", f"Failed to create snapshot: {e}")
            return ""
    
    def restore_from_snapshot(self, snapshot_dir: str) -> bool:
        """Restore memory from a snapshot."""
        try:
            if not os.path.exists(snapshot_dir):
                return False
            
            # Restore main files
            memory_files = [
                "cursor_state.json",
                "conversation-context.json",
                "task-state.json", 
                "todo-tasks.json"
            ]
            
            for file in memory_files:
                snapshot_file = os.path.join(snapshot_dir, file)
                if os.path.exists(snapshot_file):
                    shutil.copy(snapshot_file, file)
            
            self.log_recovery_action("snapshot_restore", f"Restored from snapshot: {snapshot_dir}")
            return True
            
        except OSError as e:
            self.log_recovery_action("snapshot_restore_failed", f"Failed to restore: {e}")
            return False
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """Get summary of recovery actions and current state."""
        return {
            "integrity_check": self.validate_all_memory(),
            "recovery_actions": self.recovery_log,
            "backup_files": [f for f in os.listdir('.') if f.endswith('.backup')],
            "snapshots": [d for d in os.listdir('.') if d.startswith('memory_snapshot_')]
        }


# Global recovery system instance
recovery_system = MemoryRecoverySystem()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Recovery System")
    parser.add_argument("--validate", action="store_true", help="Validate all memory integrity")
    parser.add_argument("--recover", action="store_true", help="Attempt recovery from backups")
    parser.add_argument("--snapshot", action="store_true", help="Create memory snapshot")
    parser.add_argument("--restore", metavar="SNAPSHOT_DIR", help="Restore from snapshot")
    parser.add_argument("--summary", action="store_true", help="Show recovery summary")
    
    args = parser.parse_args()
    
    if args.validate:
        results = recovery_system.validate_all_memory()
        print("🔍 Memory Integrity Check:")
        for component, is_valid in results.items():
            print(f"   {'✅' if is_valid else '❌'} {component}: {'Valid' if is_valid else 'Invalid'}")
    
    if args.recover:
        results = recovery_system.recover_from_backups()
        print("🔄 Recovery Results:")
        for component, success in results.items():
            print(f"   {'✅' if success else '❌'} {component}: {'Recovered' if success else 'Failed'}")
    
    if args.snapshot:
        snapshot_dir = recovery_system.create_snapshot()
        if snapshot_dir:
            print(f"📸 Snapshot created: {snapshot_dir}")
        else:
            print("❌ Failed to create snapshot")
    
    if args.restore:
        success = recovery_system.restore_from_snapshot(args.restore)
        if success:
            print(f"✅ Restored from snapshot: {args.restore}")
        else:
            print(f"❌ Failed to restore from snapshot: {args.restore}")
    
    if args.summary:
        summary = recovery_system.get_recovery_summary()
        print("📊 Recovery System Summary:")
        print(f"   • Backup Files: {len(summary['backup_files'])}")
        print(f"   • Snapshots: {len(summary['snapshots'])}")
        print(f"   • Recovery Actions: {len(summary['recovery_actions'])}")
        
        integrity = summary['integrity_check']
        print("   • Integrity Status:")
        for component, is_valid in integrity.items():
            print(f"     {'✅' if is_valid else '❌'} {component}") 