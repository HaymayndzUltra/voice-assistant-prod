from common.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
"""
Optimized Command Suggestion System

This module provides an optimized version of the command suggestion system with:
1. Performance improvements for real-time suggestion generation
2. Caching mechanism to reduce redundant computations
3. Pre-computation of common patterns
4. Background processing for non-critical operations
5. Memory usage optimization

This enhanced version maintains the same interface as the original but delivers
better performance for real-time voice assistant interactions.
"""

import os
import sys
import json
import csv
import time
import threading
import queue
from datetime import datetime
from typing import Dict, List, Any, Tuple, Set, Optional
from collections import defaultdict, Counter
import logging
import signal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import clustering if available
try:
    from core_agents.command_clustering import CommandClusteringEngine

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
    except ImportError as e:
        print(f"Import error: {e}")
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False


# Configure logging
logger = configure_logging(__name__))),
            "logs",
            str(PathManager.get_logs_dir() / "command_suggestion.log")
        )),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CommandSuggestion")


class CommandSuggestionOptimized(BaseAgent):
    """
    Optimized version of the command suggestion system with performance enhancements.
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CommandSuggestionOptimized")
        """
        Initialize the optimized command suggestion system.
        
        Args:
            history_file: Path to command history CSV file
            suggestion_file: Path to save suggestion patterns
            max_suggestions: Maximum number of suggestions to return
            min_confidence: Minimum confidence for commands to be considered
            cache_size: Size of the suggestion cache
            auto_update_interval: Interval in seconds for automatic suggestion updates
            use_clustering: Whether to use command clustering for enhanced suggestions
        """
        self.history_file = history_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "command_history.csv"
        )
        
        self.suggestion_file = suggestion_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "command_suggestions.json"
        )
        
        self.max_suggestions = max_suggestions
        self.min_confidence = min_confidence
        self.cache_size = cache_size
        self.auto_update_interval = auto_update_interval
        self.use_clustering = use_clustering and CLUSTERING_AVAILABLE
        
        # Performance optimization: suggestion patterns are stored by user_id and trigger_intent
        self.suggestion_patterns = defaultdict(dict)
        
        # Cache for quick suggestion lookup
        self.suggestion_cache = {}
        
        # Counter for cache stats
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Command sequence tracking
        self.user_last_commands = {}  # Track last N commands for each user
        self.last_command_limit = 10  # Keep track of last 10 commands
        
        # Performance metrics
        self.performance_metrics = {
            "record_command_time": [],
            "get_suggestions_time": [],
            "update_suggestions_time": []
        }
        
        # Background processing
        self.processing_queue = queue.Queue()
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # Precomputed common patterns
        self.common_patterns = {
            "turn_on": ["set_volume", "play_music", "turn_off"],
            "play_music": ["set_volume", "pause_music", "next_track"],
            "set_timer": ["set_reminder", "check_time", "set_alarm"],
            "check_weather": ["set_reminder", "check_time", "check_news"],
            "send_message": ["call", "read_messages", "video_call"]
        }
        
        # Pre-initialized file structure
        self._ensure_files_exist()
        
        # Initialize clustering engine if available
        self.clustering_engine = None
        if self.use_clustering:
            try:
                self.clustering_engine = CommandClusteringEngine()
                logger.info("Command clustering engine initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize clustering engine: {e}")
                self.use_clustering = False
        
        # Load existing suggestion patterns
        self._load_suggestions()
        
        # Start background processing thread
        self._start_background_processing()
    
    def _ensure_files_exist(self):
        """
        Ensure that required files exist and have proper structure.
        """
        # Create history file if it doesn't exist
        if not os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp", "user_id", "intent", "entities", "confidence"])
                logger.info(f"Created new command history file: {self.history_file}")
            except Exception as e:
                logger.error(f"Failed to create history file: {e}")
        
        # Create suggestion file if it doesn't exist
        if not os.path.exists(self.suggestion_file):
            try:
                with open(self.suggestion_file, 'w') as f:
                    json.dump({}, f)
                logger.info(f"Created new suggestion file: {self.suggestion_file}")
            except Exception as e:
                logger.error(f"Failed to create suggestion file: {e}")
    
    def _start_background_processing(self):
        """
        Start the background processing thread.
        """
        if self.processing_thread is not None and self.processing_thread.is_alive():
            return  # Thread is already running
        
        self.stop_event.clear()
        self.processing_thread = threading.Thread(
            target=self._background_processor,
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Background processing thread started")
        
        # Set up signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """
        Handle signals for clean shutdown.
        """
        logger.info("Shutdown signal received, cleaning up...")
        self.stop()
        sys.exit(0)
    
    def _background_processor(self):
        """
        Background thread for processing non-critical operations.
        """
        last_update_time = time.time()
        
        while not self.stop_event.is_set():
            try:
                # Process items from the queue with a timeout
                try:
                    item = self.processing_queue.get(timeout=1.0)
                    self._process_queue_item(item)
                    self.processing_queue.task_done()
                except queue.Empty:
                    pass
                
                # Check if it's time for auto-update
                current_time = time.time()
                if current_time - last_update_time > self.auto_update_interval:
                    self._update_suggestions()
                    last_update_time = current_time
                    
                    # Prune the cache if it's too large
                    if len(self.suggestion_cache) > self.cache_size:
                        self._prune_cache()
                    
                    # Update clustering if available
                    if self.use_clustering and self.clustering_engine:
                        self.clustering_engine.update_clusters()
                
            except Exception as e:
                logger.error(f"Error in background processor: {e}")
        
        logger.info("Background processor stopped")
    
    def _process_queue_item(self, item):
        """
        Process an item from the background queue.
        
        Args:
            item: Queue item to process
        """
        if not item or not isinstance(item, dict):
            return
        
        action = item.get("action")
        
        if action == "record_command":
            # Record command in history file
            self._record_command_to_file(
                item.get("user_id", "unknown"),
                item.get("intent", "unknown"),
                item.get("entities", {}),
                item.get("confidence", 0.0),
                item.get("timestamp")
            )
        elif action == "update_suggestions":
            # Update suggestion patterns
            self._update_suggestions()
        elif action == "clear_cache":
            # Clear suggestion cache
            self.suggestion_cache.clear()
            self.cache_hits = 0
            self.cache_misses = 0
    
    def _load_suggestions(self):
        """
        Load suggestion patterns from file.
        """
        if not os.path.exists(self.suggestion_file):
            logger.warning(f"Suggestion file not found: {self.suggestion_file}")
            return
        
        try:
            with open(self.suggestion_file, 'r') as f:
                patterns = json.load(f)
            
            # Convert to our internal format
            for trigger_key, suggestions in patterns.items():
                if not trigger_key or not isinstance(trigger_key, str):
                    continue
                
                # Parse trigger key (format: "user_id:intent")
                parts = trigger_key.split(':', 1)
                if len(parts) != 2:
                    continue
                
                user_id, intent = parts
                self.suggestion_patterns[user_id][intent] = suggestions
            
            logger.info(f"Loaded {len(patterns)} suggestion patterns")
        except Exception as e:
            logger.error(f"Error loading suggestions: {e}")
    
    def _save_suggestions(self):
        """
        Save suggestion patterns to file.
        """
        try:
            # Convert from internal format to file format
            patterns = {}
            for user_id, user_patterns in self.suggestion_patterns.items():
                for intent, suggestions in user_patterns.items():
                    key = f"{user_id}:{intent}"
                    patterns[key] = suggestions
            
            with open(self.suggestion_file, 'w') as f:
                json.dump(patterns, f, indent=2)
            
            logger.info(f"Saved {len(patterns)} suggestion patterns")
        except Exception as e:
            logger.error(f"Error saving suggestions: {e}")
    
    def _record_command_to_file(self, user_id, intent, entities, confidence, timestamp=None):
        """
        Record a command to the history file.
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            confidence: Confidence score
            timestamp: Optional timestamp (default: current time)
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        try:
            with open(self.history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, user_id, intent, json.dumps(entities), confidence])
        except Exception as e:
            logger.error(f"Error recording command to file: {e}")
    
    def _update_user_last_commands(self, user_id, intent, entities, confidence):
        """
        Update the record of the user's last commands.
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            confidence: Confidence score
        """
        if user_id not in self.user_last_commands:
            self.user_last_commands[user_id] = []
        
        # Add current command to the list
        self.user_last_commands[user_id].append({
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limit the list size
        if len(self.user_last_commands[user_id]) > self.last_command_limit:
            self.user_last_commands[user_id].pop(0)
    
    def _get_command_history(self) -> List[Dict[str, Any]]:
        """
        Get command history from file.
        
        Returns:
            List of command history records
        """
        commands = []
        
        if not os.path.exists(self.history_file):
            return commands
        
        try:
            with open(self.history_file, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 5:
                        timestamp, user_id, intent, entities_str, confidence = row[:5]
                        try:
                            entities = json.loads(entities_str)
                            commands.append({
                                "timestamp": timestamp,
                                "user_id": user_id,
                                "intent": intent,
                                "entities": entities,
                                "confidence": float(confidence)
                            })
                        except (json.JSONDecodeError, ValueError):
                            continue
        except Exception as e:
            logger.error(f"Error reading command history: {e}")
        
        return commands
    
    def _extract_patterns(self, commands: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Extract suggestion patterns from command history.
        
        Args:
            commands: List of command history records
            
        Returns:
            Dictionary of suggestion patterns by user and intent
        """
        # Group commands by user
        user_commands = defaultdict(list)
        for cmd in commands:
            if cmd.get("confidence", 0) >= self.min_confidence:
                user_commands[cmd["user_id"]].append(cmd)
        
        # Extract patterns for each user
        patterns = defaultdict(dict)
        
        for user_id, user_cmds in user_commands.items():
            # Sort by timestamp
            user_cmds.sort(key=lambda x: x["timestamp"])
            
            # Look for sequential patterns
            for i in range(len(user_cmds) - 1):
                current_cmd = user_cmds[i]
                next_cmd = user_cmds[i + 1]
                
                # Skip if there's too much time between commands (optional enhancement)
                # This would require parsing timestamps and comparing them
                
                # Get current command intent
                current_intent = current_cmd["intent"]
                
                # Initialize pattern for this intent if not exists
                if current_intent not in patterns[user_id]:
                    patterns[user_id][current_intent] = []
                
                # Check if this next intent is already in the pattern
                next_intent_exists = False
                for suggestion in patterns[user_id][current_intent]:
                    if suggestion["intent"] == next_cmd["intent"]:
                        # Increment count for existing pattern
                        suggestion["count"] += 1
                        next_intent_exists = True
                        break
                
                # Add new pattern if not found
                if not next_intent_exists:
                    patterns[user_id][current_intent].append({
                        "intent": next_cmd["intent"],
                        "entities": next_cmd["entities"],
                        "count": 1
                    })
        
        # Sort patterns by count (descending) and limit to max_suggestions
        for user_id in patterns:
            for intent in patterns[user_id]:
                patterns[user_id][intent].sort(key=lambda x: x["count"], reverse=True)
                patterns[user_id][intent] = patterns[user_id][intent][:self.max_suggestions]
        
        return patterns
    
    def _update_suggestions(self):
        """
        Update suggestion patterns based on command history.
        """
        start_time = time.time()
        
        try:
            # Get command history
            commands = self._get_command_history()
            
            if not commands:
                logger.warning("No command history available for pattern extraction")
                return
            
            # Extract patterns
            new_patterns = self._extract_patterns(commands)
            
            # Update suggestion patterns
            self.suggestion_patterns = new_patterns
            
            # Save updated patterns
            self._save_suggestions()
            
            # Clear cache after update
            self.suggestion_cache.clear()
            
            # Track performance
            elapsed_time = time.time() - start_time
            self.performance_metrics["update_suggestions_time"].append(elapsed_time)
            
            logger.info(f"Updated suggestion patterns in {elapsed_time:.3f} seconds")
            
        except Exception as e:
            logger.error(f"Error updating suggestions: {e}")
    
    def _get_cache_key(self, user_id, intent, entities) -> str:
        """
        Generate a cache key for suggestion lookup.
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            
        Returns:
            Cache key string
        """
        # Use a combination of user_id, intent, and sorted entity keys
        # This allows cache hits even if entity values change but types are the same
        entity_keys = sorted(entities.keys())
        return f"{user_id}:{intent}:{','.join(entity_keys)}"
    
    def _prune_cache(self):
        """
        Prune the suggestion cache if it exceeds the size limit.
        """
        if len(self.suggestion_cache) <= self.cache_size:
            return
        
        # Remove oldest entries (simple approach)
        excess = len(self.suggestion_cache) - self.cache_size
        keys_to_remove = list(self.suggestion_cache.keys())[:excess]
        
        for key in keys_to_remove:
            del self.suggestion_cache[key]
        
        logger.info(f"Pruned {len(keys_to_remove)} entries from suggestion cache")
    
    def _get_suggestions_from_clustering(self, user_id, intent, entities, confidence) -> List[Dict[str, Any]]:
        """
        Get suggestions using the command clustering engine.
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            confidence: Confidence score
            
        Returns:
            List of suggested commands
        """
        if not self.use_clustering or not self.clustering_engine:
            return []
        
        try:
            # Get base suggestions
            base_suggestions = []
            
            # First try user-specific patterns
            if user_id in self.suggestion_patterns and intent in self.suggestion_patterns[user_id]:
                base_suggestions = self.suggestion_patterns[user_id][intent]
            
            # If no user-specific patterns, use common patterns
            if not base_suggestions and intent in self.common_patterns:
                base_suggestions = [
                    {"intent": suggested_intent, "entities": {}, "count": 1}
                    for suggested_intent in self.common_patterns[intent]
                ]
            
            # Enhance with clustering
            enhanced_suggestions = self.clustering_engine.enhance_suggestion_with_clusters(
                intent, entities, base_suggestions
            )
            
            return enhanced_suggestions
            
        except Exception as e:
            logger.error(f"Error getting suggestions from clustering: {e}")
            return []
    
    def record_command(self, user_id: str, intent: str, entities: Dict[str, Any], confidence: float) -> None:
        """
        Record a command for learning patterns.
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            confidence: Confidence score
        """
        start_time = time.time()
        
        # Update user's last commands in memory
        self._update_user_last_commands(user_id, intent, entities, confidence)
        
        # Queue the command recording for background processing
        self.processing_queue.put({
            "action": "record_command",
            "user_id": user_id,
            "intent": intent,
            "entities": entities,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        
        # Track performance
        elapsed_time = time.time() - start_time
        self.performance_metrics["record_command_time"].append(elapsed_time)
    
    def get_suggestions(self, user_id: str, intent: str, entities: Dict[str, Any], confidence: float) -> List[Dict[str, Any]]:
        """
        Get command suggestions based on the current command.
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            confidence: Confidence score
            
        Returns:
            List of suggested commands
        """
        start_time = time.time()
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            logger.debug(f"Command confidence {confidence} below threshold {self.min_confidence}")
            return []
        
        # Check cache first
        cache_key = self._get_cache_key(user_id, intent, entities)
        if cache_key in self.suggestion_cache:
            self.cache_hits += 1
            
            # Track performance
            elapsed_time = time.time() - start_time
            self.performance_metrics["get_suggestions_time"].append(elapsed_time)
            
            return self.suggestion_cache[cache_key]
        
        self.cache_misses += 1
        
        # Get suggestions
        suggestions = []
        
        # Try user-specific patterns first
        if user_id in self.suggestion_patterns and intent in self.suggestion_patterns[user_id]:
            suggestions = self.suggestion_patterns[user_id][intent]
        
        # If no user-specific patterns or they're insufficient, use clustering if available
        if self.use_clustering and (not suggestions or len(suggestions) < self.max_suggestions):
            cluster_suggestions = self._get_suggestions_from_clustering(
                user_id, intent, entities, confidence
            )
            
            # Merge with existing suggestions
            if cluster_suggestions:
                # Only add suggestions that aren't already present
                existing_intents = {s["intent"] for s in suggestions}
                new_suggestions = [s for s in cluster_suggestions if s["intent"] not in existing_intents]
                
                suggestions.extend(new_suggestions)
                suggestions = suggestions[:self.max_suggestions]
        
        # If still no suggestions, use common patterns
        if not suggestions and intent in self.common_patterns:
            suggestions = [
                {"intent": suggested_intent, "entities": {}, "count": 1}
                for suggested_intent in self.common_patterns[intent]
            ]
            suggestions = suggestions[:self.max_suggestions]
        
        # Cache the results
        self.suggestion_cache[cache_key] = suggestions
        
        # Track performance
        elapsed_time = time.time() - start_time
        self.performance_metrics["get_suggestions_time"].append(elapsed_time)
        
        return suggestions
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the suggestion system.
        
        Returns:
            Dictionary of performance metrics
        """
        metrics = {
            "cache_stats": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "size": len(self.suggestion_cache),
                "hit_ratio": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            },
            "average_times": {}
        }
        
        # Calculate average times
        for metric, times in self.performance_metrics.items():
            if times:
                metrics["average_times"][metric] = sum(times) / len(times)
            else:
                metrics["average_times"][metric] = 0
        
        return metrics
    
    def clear_cache(self):
        """
        Clear the suggestion cache.
        """
        self.processing_queue.put({"action": "clear_cache"})
    
    def force_update(self):
        """
        Force an update of suggestion patterns.
        """
        self.processing_queue.put({"action": "update_suggestions"})
    
    def stop(self):
        """
        Stop the background processing thread.
        """
        if self.processing_thread and self.processing_thread.is_alive():
            logger.info("Stopping background processing...")
            self.stop_event.set()
            self.processing_thread.join(timeout=5.0)
            
            # Save any pending changes
            self._save_suggestions()
            
            logger.info("Background processing stopped")


# Example usage and testing
def main():
    """Test the optimized command suggestion system."""
    print("Optimized Command Suggestion System - Test")
    
    # Create suggestion system
    suggestion_system = CommandSuggestionOptimized(auto_update_interval=30)
    
    try:
        # Record some test commands
        for i in range(5):
            user_id = "test_user"
            
            # Pattern 1: turn_on → set_volume
            suggestion_system.record_command(
                user_id, 
                "turn_on", 
                {"device": "lights"}, 
                0.95
            )
            time.sleep(0.1)
            suggestion_system.record_command(
                user_id, 
                "set_volume", 
                {"level": "60%"}, 
                0.9
            )
            
            # Pattern 2: play_music → check_weather
            suggestion_system.record_command(
                user_id, 
                "play_music", 
                {"genre": "rock"}, 
                0.88
            )
            time.sleep(0.1)
            suggestion_system.record_command(
                user_id, 
                "check_weather", 
                {"location": "Manila"}, 
                0.92
            )
        
        # Force update to process the test data
        suggestion_system.force_update()
        time.sleep(2)  # Give time for background processing
        
        # Test suggestions
        print("\nTesting suggestions:")
        
        # Test after turn_on
        suggestions = suggestion_system.get_suggestions(
            "test_user", "turn_on", {"device": "lights"}, 0.95
        )
        print(f"\nSuggestions after 'turn_on':")
        for i, suggestion in enumerate(suggestions):
            print(f"{i+1}. {suggestion['intent']}")
        
        # Test after play_music
        suggestions = suggestion_system.get_suggestions(
            "test_user", "play_music", {"genre": "rock"}, 0.88
        )
        print(f"\nSuggestions after 'play_music':")
        for i, suggestion in enumerate(suggestions):
            print(f"{i+1}. {suggestion['intent']}")
        
        # Display performance metrics
        print("\nPerformance Metrics:")
        metrics = suggestion_system.get_performance_metrics()
        
        print(f"Cache Hit Ratio: {metrics['cache_stats']['hit_ratio']:.2f}")
        print(f"Average get_suggestions time: {metrics['average_times'].get('get_suggestions_time', 0):.6f} seconds")
        print(f"Average record_command time: {metrics['average_times'].get('record_command_time', 0):.6f} seconds")
        
        print("\nTest completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    finally:
        # Clean shutdown
        suggestion_system.stop()


if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
