#!/usr/bin/env python3
"""
Conversation Context Manager - Prevents conversation context loss during AI memory loss

This module provides persistent storage for user-AI conversation history,
including context, reasoning, and decision-making process.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConversationContextManager:
    """Manages persistent conversation context to prevent memory loss."""
    
    def __init__(self, context_file: str = "conversation-context.json"):
        self.context_file = Path(context_file)
        self.backup_file = Path(f"{context_file}.backup")
        self.context: Dict[str, Any] = self._load_context()
        
    def _load_context(self) -> Dict[str, Any]:
        """Load conversation context from disk with backup recovery."""
        # Try main file first
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        
        # Try backup file if main file failed
        if self.backup_file.exists():
            try:
                with open(self.backup_file, 'r', encoding='utf-8') as f:
                    context = json.load(f)
                    # Restore main file from backup
                    self._save_context(context)
                    return context
            except (json.JSONDecodeError, OSError):
                pass
        
        # Return fresh context if both files failed
        return {
            "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "conversations": [],
            "current_task_context": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_context(self, context: Dict[str, Any]) -> None:
        """Save context with backup protection."""
        # Create backup first
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r', encoding='utf-8') as src:
                    with open(self.backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            except OSError:
                pass
        
        # Save new context
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2, ensure_ascii=False)
        except OSError:
            # If main save fails, try backup
            try:
                with open(self.backup_file, 'w', encoding='utf-8') as f:
                    json.dump(context, f, indent=2, ensure_ascii=False)
            except OSError:
                pass
    
    def add_conversation(self, 
                        user_input: str, 
                        ai_response: str, 
                        file_context: Optional[str] = None,
                        task_context: Optional[str] = None,
                        reasoning: Optional[str] = None) -> None:
        """Add a conversation exchange with full context."""
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "ai_response": ai_response,
            "file_context": file_context,
            "task_context": task_context,
            "reasoning": reasoning,
            "session_id": self.context["session_id"]
        }
        
        self.context["conversations"].append(conversation)
        self.context["last_updated"] = datetime.now().isoformat()
        self._save_context(self.context)
    
    def get_recent_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context for memory recovery."""
        return self.context["conversations"][-limit:]
    
    def get_task_context(self) -> Dict[str, Any]:
        """Get current task context."""
        return self.context.get("current_task_context", {})
    
    def update_task_context(self, task_info: Dict[str, Any]) -> None:
        """Update current task context."""
        self.context["current_task_context"] = task_info
        self.context["last_updated"] = datetime.now().isoformat()
        self._save_context(self.context)
    
    def validate_integrity(self) -> bool:
        """Validate conversation context integrity."""
        try:
            # Check if context file exists and is valid JSON
            if not self.context_file.exists():
                return False
            
            with open(self.context_file, 'r', encoding='utf-8') as f:
                json.load(f)
            
            return True
        except (json.JSONDecodeError, OSError):
            return False
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of conversation context."""
        return {
            "total_conversations": len(self.context["conversations"]),
            "session_id": self.context["session_id"],
            "last_updated": self.context["last_updated"],
            "current_task": self.context.get("current_task_context", {}).get("task", "None"),
            "integrity_check": self.validate_integrity()
        }


# Global instance for easy access
conversation_manager = ConversationContextManager()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Conversation Context Manager")
    parser.add_argument("--add", nargs=2, metavar=("USER_INPUT", "AI_RESPONSE"), 
                       help="Add conversation exchange")
    parser.add_argument("--summary", action="store_true", help="Show context summary")
    parser.add_argument("--recent", type=int, default=5, help="Show recent conversations")
    parser.add_argument("--validate", action="store_true", help="Validate context integrity")
    
    args = parser.parse_args()
    
    if args.add:
        conversation_manager.add_conversation(args.add[0], args.add[1])
        print("✅ Conversation added to context")
    
    if args.summary:
        summary = conversation_manager.get_context_summary()
        print("📊 Conversation Context Summary:")
        for key, value in summary.items():
            print(f"   • {key}: {value}")
    
    if args.recent > 0:
        recent = conversation_manager.get_recent_context(args.recent)
        print(f"📝 Recent {len(recent)} conversations:")
        for i, conv in enumerate(recent, 1):
            print(f"   {i}. [{conv['timestamp']}] {conv['user_input'][:50]}...")
    
    if args.validate:
        is_valid = conversation_manager.validate_integrity()
        print(f"🔍 Context Integrity: {'✅ Valid' if is_valid else '❌ Invalid'}") 