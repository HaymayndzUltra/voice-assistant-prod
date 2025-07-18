from common.core.base_agent import BaseAgent
"""
Command Suggestion Module
Analyzes command usage patterns to suggest related commands
"""
import logging
import json
import os
import time
import threading
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
logger = logging.getLogger("CommandSuggestion")

class CommandSuggestion(BaseAgent):
    """Command suggestion system that learns from usage patterns"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CommandSuggestion")
        """Initialize the command suggestion system
        
        Args:
            data_file: Optional path to save/load command pattern data
            min_confidence: Minimum confidence threshold for suggestions
            max_suggestions: Maximum number of suggestions to return
        """
        self.data_file = data_file or join_path("data", "command_patterns.json")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        
        # Main data structures
        self.command_sequences = defaultdict(Counter)  # Maps command to subsequent commands with counts
        self.command_counts = Counter()  # Total count of each command
        self.last_commands = {}  # Maps user_id to their last command
        
        # Settings
        self.min_confidence = min_confidence
        self.max_suggestions = max_suggestions
        
        # Load existing data if available
        self.load_data()
        
        # Track modifications for efficient saving
        self.modified = False
        self._last_save = time.time()
        self._save_interval = 300  # Save every 5 minutes if modified
        
        # Thread lock for thread safety
        self._lock = threading.Lock()
        
        # Blacklist of commands that shouldn't be suggested
        self.suggestion_blacklist = {
            "unknown", "command_denied", "command_confirmation", "help"
        }
        
        # Commands that should always be suggested in certain contexts
        self.context_suggestions = {
            "weather": ["forecast", "temperature", "umbrella"],
            "music": ["skip", "pause", "volume"],
            "timer": ["cancel", "check", "extend"],
            "light": ["dim", "brighten", "color"],
            "shopping": ["add_item", "remove_item", "show_list"]
        }
        
    def record_command(self, user_id: str, intent: str, entities: Dict[str, Any], confidence: float) -> None:
        """Record a command execution to learn patterns
        
        Args:
            user_id: User identifier
            intent: Command intent
            entities: Command parameters/entities
            confidence: Confidence score of the intent detection
        """
        # Skip recording low-confidence commands
        if confidence < 0.5:
            return
            
        # Skip blacklisted commands
        if intent in self.suggestion_blacklist:
            return
            
        with self._lock:
            # Get the previous command for this user
            prev_command = self.last_commands.get(user_id)
            
            # Update command counts
            self.command_counts[intent] += 1
            
            # If there was a previous command, update sequence data
            if prev_command:
                prev_intent = prev_command.get("intent")
                if prev_intent and prev_intent != intent:
                    self.command_sequences[prev_intent][intent] += 1
            
            # Store this command as the last command for this user
            self.last_commands[user_id] = {
                "intent": intent,
                "entities": entities,
                "timestamp": time.time()
            }
            
            # Mark as modified
            self.modified = True
            
            # Save periodically if modified
            if time.time() - self._last_save > self._save_interval and self.modified:
                self.save_data()
    
    def get_suggestions(self, user_id: str, current_intent: str = None, 
                       context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get suggested commands based on usage patterns
        
        Args:
            user_id: User identifier
            current_intent: Optional current intent to base suggestions on
            context: Optional context information for better suggestions
            
        Returns:
            List of suggested commands with confidence scores
        """
        suggestions = []
        
        with self._lock:
            # If no current intent provided, use the last command's intent
            if not current_intent and user_id in self.last_commands:
                current_intent = self.last_commands[user_id]["intent"]
                
            if not current_intent:
                return suggestions
                
            # Get suggestions based on sequence patterns
            if current_intent in self.command_sequences:
                total_follows = sum(self.command_sequences[current_intent].values())
                
                # Get top commands that follow the current command
                for next_command, count in self.command_sequences[current_intent].most_common(self.max_suggestions * 2):
                    # Skip blacklisted commands
                    if next_command in self.suggestion_blacklist:
                        continue
                        
                    # Calculate confidence
                    confidence = count / total_follows if total_follows > 0 else 0
                    
                    if confidence >= self.min_confidence:
                        suggestions.append({
                            "intent": next_command,
                            "source": "pattern",
                            "confidence": confidence
                        })
            
            # Add context-based suggestions if relevant
            if context:
                # Check if any context keywords match our context suggestions
                for keyword, related_commands in self.context_suggestions.items():
                    if any(keyword in str(v).lower() for v in context.values()):
                        for cmd in related_commands:
                            # Avoid duplicates
                            if not any(s["intent"] == cmd for s in suggestions):
                                suggestions.append({
                                    "intent": cmd,
                                    "source": "context",
                                    "confidence": 0.6  # Fixed confidence for context suggestions
                                })
            
            # Sort by confidence and limit to max_suggestions
            suggestions.sort(key=lambda x: x["confidence"], reverse=True)
            suggestions = suggestions[:self.max_suggestions]
            
            # Add human-readable descriptions
            for suggestion in suggestions:
                suggestion["description"] = self._get_command_description(suggestion["intent"])
                
            return suggestions
    
    def _get_command_description(self, intent: str) -> str:
        """Get a human-readable description of a command
        
        Args:
            intent: Command intent
            
        Returns:
            Human-readable description
        """
        # Map of intents to natural language descriptions
        descriptions = {
            "weather": "Check the weather",
            "forecast": "View the weather forecast",
            "temperature": "Check the temperature",
            "umbrella": "Check if you need an umbrella",
            "music": "Play music",
            "skip": "Skip to the next song",
            "pause": "Pause playback",
            "volume": "Adjust the volume",
            "timer": "Set a timer",
            "cancel": "Cancel the timer",
            "check": "Check the timer status",
            "extend": "Add time to the timer",
            "light": "Control the lights",
            "dim": "Dim the lights",
            "brighten": "Brighten the lights",
            "color": "Change light color",
            "shopping": "View shopping list",
            "add_item": "Add to shopping list",
            "remove_item": "Remove from shopping list",
            "show_list": "Show the shopping list"
        }
        
        return descriptions.get(intent, f"Use the {intent} command")
    
    def save_data(self) -> None:
        """Save command pattern data to file"""
        if not self.modified:
            return
            
        try:
            with open(self.data_file, 'w') as f:
                data = {
                    "command_sequences": {k: dict(v) for k, v in self.command_sequences.items()},
                    "command_counts": dict(self.command_counts),
                    "timestamp": time.time()
                }
                json.dump(data, f, indent=2)
                
            self.modified = False
            self._last_save = time.time()
            logger.info(f"Command pattern data saved to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving command pattern data: {e}")
    
    def load_data(self) -> None:
        """Load command pattern data from file"""
        if not os.path.exists(self.data_file):
            logger.info(f"No command pattern data file found at {self.data_file}")
            return
            
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                
            # Convert loaded data back to the appropriate types
            self.command_sequences = defaultdict(Counter)
            for cmd, follows in data.get("command_sequences", {}).items():
                self.command_sequences[cmd] = Counter(follows)
                
            self.command_counts = Counter(data.get("command_counts", {}))
            
            logger.info(f"Command pattern data loaded from {self.data_file}")
        except Exception as e:
            logger.error(f"Error loading command pattern data: {e}")
    
    def clear_data(self) -> None:
        """Clear all learned pattern data"""
        with self._lock:
            self.command_sequences = defaultdict(Counter)
            self.command_counts = Counter()
            self.last_commands = {}
            self.modified = True
            self.save_data()
            logger.info("Command pattern data cleared")
    
    def format_suggestions(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format suggestions into a natural language response
        
        Args:
            suggestions: List of suggestion dictionaries
            
        Returns:
            Formatted natural language string with suggestions
        """
        if not suggestions:
            return ""
            
        if len(suggestions) == 1:
            return f"You might want to {suggestions[0]['description']} next."
            
        suggestion_texts = [s['description'] for s in suggestions]
        
        if len(suggestions) == 2:
            return f"You might want to {suggestion_texts[0]} or {suggestion_texts[1]} next."
            
        # For 3 or more suggestions
        last_suggestion = suggestion_texts.pop()
        return f"You might want to {', '.join(suggestion_texts)}, or {last_suggestion} next."

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
