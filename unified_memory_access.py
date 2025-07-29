#!/usr/bin/env python3
"""
Unified Memory Access Layer
Provides consistent memory interface for all AI agents in the codebase
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import the memory system
try:
    from memory_system.services.memory_provider import get_provider, MemoryProvider
    MEMORY_SYSTEM_AVAILABLE = True
except ImportError:
    MEMORY_SYSTEM_AVAILABLE = False

logger = logging.getLogger(__name__)

class UnifiedMemoryManager:
    """Unified memory manager for all AI agents"""
    
    def __init__(self, provider_type: str = "sqlite"):
        """Initialize with specified provider (fs, sqlite, chroma)"""
        self.provider_type = provider_type
        self._provider: Optional[MemoryProvider] = None
        self._session_context = {}
        
        if MEMORY_SYSTEM_AVAILABLE:
            try:
                self._provider = get_provider(provider_type)
                logger.info(f"✅ Memory system initialized with {provider_type} provider")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {provider_type} provider: {e}")
                # Fallback to filesystem
                self._provider = get_provider("fs")
                logger.info("✅ Fallback to filesystem provider")
        else:
            logger.warning("⚠️ Memory system not available, using simple fallback")
    
    def search(self, keyword: str, limit: int = 10) -> List[str]:
        """Search memories - alias for search_memories"""
        return self.search_memories(keyword, limit)
    
    def search_memories(self, keyword: str, limit: int = 10) -> List[str]:
        """Search for memories containing keyword"""
        if self._provider:
            return self._provider.search(keyword, limit)
        else:
            # Simple fallback - search memory-bank directory
            return self._fallback_search(keyword, limit)
    
    def add(self, title: str, content: str) -> bool:
        """Add memory - alias for add_memory"""
        return self.add_memory(title, content)
    
    def add_memory(self, title: str, content: str) -> bool:
        """Add a new memory"""
        try:
            if self._provider:
                self._provider.add(title, content)
                logger.info(f"✅ Added memory: {title}")
                return True
            else:
                return self._fallback_add(title, content)
        except Exception as e:
            logger.error(f"❌ Failed to add memory: {e}")
            return False
    
    def get_session_context(self) -> Dict[str, Any]:
        """Get current session context"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "provider": self.provider_type,
            "session_data": self._session_context
        }
        
        # Add current tasks from TODO system
        try:
            todo_path = Path("todo-tasks.json")
            if todo_path.exists():
                with open(todo_path) as f:
                    context["active_tasks"] = json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Could not load TODO tasks: {e}")
        
        # Add cursor state
        try:
            cursor_path = Path("cursor_state.json")
            if cursor_path.exists():
                with open(cursor_path) as f:
                    context["cursor_state"] = json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Could not load cursor state: {e}")
        
        return context
    
    def update_session_context(self, key: str, value: Any) -> None:
        """Update session context"""
        self._session_context[key] = value
        logger.debug(f"📝 Updated session context: {key}")
    
    def continue_from_last_session(self) -> Dict[str, Any]:
        """Continue from where we left off"""
        context = self.get_session_context()
        
        # Search for recent memories
        recent_memories = self.search_memories("2025-07", limit=5)
        context["recent_memories"] = recent_memories
        
        # Get current active task
        if "active_tasks" in context and context["active_tasks"].get("tasks"):
            active_task = None
            for task in context["active_tasks"]["tasks"]:
                if task.get("status") == "in_progress":
                    active_task = task
                    break
            context["current_active_task"] = active_task
        
        logger.info("🔄 Session context loaded for continuity")
        return context
    
    def _fallback_search(self, keyword: str, limit: int) -> List[str]:
        """Fallback search in memory-bank directory"""
        results = []
        memory_bank = Path("memory-bank")
        if memory_bank.exists():
            for md_file in memory_bank.glob("*.md"):
                try:
                    content = md_file.read_text()
                    if keyword.lower() in content.lower():
                        results.append(str(md_file))
                        if len(results) >= limit:
                            break
                except Exception:
                    continue
        return results
    
    def _fallback_add(self, title: str, content: str) -> bool:
        """Fallback memory addition"""
        try:
            memory_bank = Path("memory-bank")
            memory_bank.mkdir(exist_ok=True)
            
            safe_title = title.replace(" ", "_").replace("/", "_")[:50]
            file_path = memory_bank / f"{safe_title}.md"
            
            file_path.write_text(f"# {title}\n\n{content}\n\nCreated: {datetime.now().isoformat()}")
            logger.info(f"✅ Added fallback memory: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Fallback memory add failed: {e}")
            return False

# Global instance for easy access
unified_memory = UnifiedMemoryManager()

# Helper functions for easy integration
def search_memory(keyword: str, limit: int = 10) -> List[str]:
    """Quick memory search"""
    return unified_memory.search_memories(keyword, limit)

def add_memory(title: str, content: str) -> bool:
    """Quick memory addition"""
    return unified_memory.add_memory(title, content)

def get_context() -> Dict[str, Any]:
    """Get current session context"""
    return unified_memory.get_session_context()

def continue_session() -> Dict[str, Any]:
    """Continue from last session"""
    return unified_memory.continue_from_last_session()

if __name__ == "__main__":
    # Test the unified memory system
    print("🧠 Testing Unified Memory System...")
    
    # Test search
    results = search_memory("docker")
    print(f"📋 Found {len(results)} memories about 'docker'")
    
    # Test context
    context = get_context()
    print(f"📊 Session context keys: {list(context.keys())}")
    
    # Test continuity
    continue_data = continue_session()
    print(f"🔄 Continuity data: {len(continue_data)} items")
    
    print("✅ Unified memory system ready!")
