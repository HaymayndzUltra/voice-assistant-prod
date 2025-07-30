"""
Advanced Context Management for Voice Assistant
This module provides enhanced context management capabilities for the voice assistant,
including dynamic context sizing, importance scoring, and speaker-specific context.
"""

import logging
import time
import numpy as np
from collections import deque
import re

class ContextManager:
    """Advanced context management for voice assistant conversations"""
    
    def __init__(self, min_size=5, max_size=20, initial_size=10):

        super().__init__(*args, **kwargs)        # Context window configuration
        self.min_size = min_size
        self.max_size = max_size
        self.current_size = initial_size
        self.context_window = deque(maxlen=self.current_size)
        
        # Context importance scoring
        self.importance_scores = {}
        self.importance_threshold = 0.5  # Minimum score to keep in context
        
        # Speaker-specific context
        self.speaker_contexts = {}
        
        # Keywords that indicate important context
        self.important_keywords = [
            'remember', 'don\'t forget', 'important', 'critical', 'essential',
            'alalahanin', 'tandaan', 'mahalaga', 'importante', 'kailangan'
        ]
        
        logging.info(f"[ContextManager] Initialized with size range {min_size}-{max_size}, current: {initial_size}")
    
    def add_to_context(self, text, speaker=None, metadata=None):
        """Add a new item to the context window with importance scoring"""
        if not text:
            return
            
        # Generate timestamp
        timestamp = time.time()
        
        # Calculate importance score
        importance = self._calculate_importance(text)
        
        # Create context item
        context_item = {
            'text': text,
            'timestamp': timestamp,
            'speaker': speaker,
            'importance': importance,
            'metadata': metadata or {}
        }
        
        # Add to main context window
        self.context_window.append(context_item)
        self.importance_scores[text] = importance
        
        # Add to speaker-specific context if applicable
        if speaker:
            if speaker not in self.speaker_contexts:
                self.speaker_contexts[speaker] = deque(maxlen=self.max_size)
            self.speaker_contexts[speaker].append(context_item)
        
        # Adjust context window size if needed
        self._adjust_context_size()
        
        logging.debug(f"[ContextManager] Added to context: '{text[:30]}...' (Score: {importance:.2f})")
    
    def get_context(self, speaker=None, max_items=None):
        """Get current context, optionally filtered by speaker"""
        if speaker and speaker in self.speaker_contexts:
            # Return speaker-specific context
            context = list(self.speaker_contexts[speaker])
        else:
            # Return general context
            context = list(self.context_window)
        
        # Sort by importance and recency
        context.sort(key=lambda x: (x['importance'], x['timestamp']), reverse=True)
        
        # Limit number of items if specified
        if max_items:
            context = context[:max_items]
            
        return context
    
    def get_context_text(self, speaker=None, max_items=None):
        """Get context as formatted text for LLM input"""
        context = self.get_context(speaker, max_items)
        
        # Format context items
        formatted_items = []
        for item in context:
            speaker_prefix = f"[{item['speaker']}]: " if item['speaker'] else ""
            formatted_items.append(f"{speaker_prefix}{item['text']}")
        
        return "\n".join(formatted_items)
    
    def clear_context(self, speaker=None):
        """Clear context, optionally only for a specific speaker"""
        if speaker:
            if speaker in self.speaker_contexts:
                self.speaker_contexts[speaker].clear()
                logging.info(f"[ContextManager] Cleared context for speaker: {speaker}")
        else:
            self.context_window.clear()
            self.importance_scores.clear()
            logging.info("[ContextManager] Cleared all context")
    
    def _calculate_importance(self, text):
        """Calculate importance score for a context item"""
        # Base importance
        importance = 0.5
        
        # Check for important keywords
        for keyword in self.important_keywords:
            if keyword.lower() in text.lower():
                importance += 0.2
                break
        
        # Check for questions (likely important)
        if '?' in text:
            importance += 0.1
        
        # Check for commands/requests
        command_patterns = [
            r'\b(please|paki|pakiusap)\b',
            r'\b(can you|could you|would you)\b',
            r'\b(i want|i need|i would like)\b',
            r'\b(gusto ko|kailangan ko)\b'
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, text.lower()):
                importance += 0.1
                break
        
        # Longer texts might contain more information
        if len(text.split()) > 15:
            importance += 0.1
        
        # Cap importance between 0 and 1
        return min(1.0, max(0.0, importance))
    
    def _adjust_context_size(self):
        """Dynamically adjust context window size based on conversation complexity"""
        # Calculate average importance
        avg_importance = np.mean(list(self.importance_scores.values())) if self.importance_scores else 0.5
        
        # Calculate conversation complexity (higher importance = more complex)
        if avg_importance > 0.7:
            # Complex conversation, increase context size
            target_size = min(self.max_size, self.current_size + 2)
        elif avg_importance < 0.3:
            # Simple conversation, decrease context size
            target_size = max(self.min_size, self.current_size - 1)
        else:
            # Maintain current size
            return
        
        # Only change if different from current
        if target_size != self.current_size:
            # Create new deque with new size
            new_context = deque(self.context_window, maxlen=target_size)
            self.context_window = new_context
            self.current_size = target_size
            logging.info(f"[ContextManager] Adjusted context size to {target_size} (avg importance: {avg_importance:.2f})")
    
    def prune_context(self):
        """Remove low-importance items if context is full"""
        if len(self.context_window) < self.current_size:
            return
            
        # Find items below threshold
        items_to_remove = []
        for item in self.context_window:
            if item['importance'] < self.importance_threshold:
                items_to_remove.append(item)
        
        # Remove low-importance items (up to 25% of window)
        max_to_remove = max(1, self.current_size // 4)
        for item in items_to_remove[:max_to_remove]:
            self.context_window.remove(item)
            if item['text'] in self.importance_scores:
                del self.importance_scores[item['text']]
            
        if items_to_remove:
            logging.debug(f"[ContextManager] Pruned {len(items_to_remove[:max_to_remove])} low-importance items")

# Helper functions for easy integration
def create_context_manager():
    """Create and return a new ContextManager instance"""
    return ContextManager()

def add_to_context(manager, text, speaker=None, metadata=None):
    """Add text to context manager"""
    manager.add_to_context(text, speaker, metadata)

def get_context(manager, speaker=None, max_items=None):
    """Get context from manager"""
    return manager.get_context(speaker, max_items)

def get_context_text(manager, speaker=None, max_items=None):
    """Get formatted context text from manager"""
    return manager.get_context_text(speaker, max_items)

def clear_context(manager, speaker=None):
    """Clear context in manager"""
    manager.clear_context(speaker)
