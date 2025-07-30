from common.core.base_agent import BaseAgent
"""
Command Clustering Module

This module enhances the command suggestion system by:
1. Clustering similar commands based on intent and entity patterns
2. Identifying related command groups for smarter suggestions
3. Providing better context-aware command recommendations

It uses simple clustering techniques to group commands that are functionally
similar or commonly used together.
"""

import os
import sys
import json
import csv
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CommandClusteringEngine(BaseAgent):
    """
    Engine for clustering similar commands and enhancing suggestion quality.
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CommandClustering")
        """
        Initialize the command clustering engine.
        
        Args:
            command_history_file: Path to the command history CSV file
            cluster_output_file: Path to save the cluster data
            min_similarity: Minimum similarity threshold for commands to be in same cluster
        """
        self.command_history_file = command_history_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "command_history.csv"
        )
        
        self.cluster_output_file = cluster_output_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "command_clusters.json"
        )
        
        self.min_similarity = min_similarity
        self.command_clusters = {}
        self.command_embeddings = {}
        
        # Entity type importance weights
        self.entity_weights = {
            "device": 1.0,      # Devices are very important for context
            "location": 0.9,    # Locations are important
            "time": 0.7,        # Time has moderate importance
            "duration": 0.7,    # Duration has moderate importance
            "person": 0.8,      # Person has high importance
            "generic": 0.5      # Generic entities have lower importance
        }
        
        # Define known command groups for faster clustering
        self.predefined_clusters = {
            "media_control": [
                "play_music", "pause_music", "stop_music", "next_track", "previous_track",
                "volume_up", "volume_down", "set_volume", "mute", "unmute"
            ],
            "smart_home": [
                "turn_on", "turn_off", "dim_lights", "brighten_lights", "set_temperature",
                "lock_door", "unlock_door", "close_blinds", "open_blinds"
            ],
            "time_management": [
                "set_timer", "set_alarm", "set_reminder", "check_time", "check_date",
                "start_stopwatch", "pause_stopwatch", "reset_stopwatch"
            ],
            "information": [
                "check_weather", "search_web", "get_news", "check_sports", 
                "get_definition", "translate"
            ],
            "communication": [
                "send_message", "call", "video_call", "send_email", "read_messages",
                "read_emails"
            ]
        }
        
        # Load existing clusters if available
        self.load_clusters()
    
    def load_clusters(self):
        """
        Load existing command clusters from file.
        """
        if os.path.exists(self.cluster_output_file):
            try:
                with open(self.cluster_output_file, 'r') as f:
                    self.command_clusters = json.load(f)
                print(f"Loaded {len(self.command_clusters)} command clusters")
            except Exception as e:
                print(f"Error loading command clusters: {e}")
                self.command_clusters = {}
    
    def save_clusters(self):
        """
        Save command clusters to file.
        """
        try:
            with open(self.cluster_output_file, 'w') as f:
                json.dump(self.command_clusters, f, indent=2)
            print(f"Saved {len(self.command_clusters)} command clusters")
        except Exception as e:
            print(f"Error saving command clusters: {e}")
    
    def load_command_history(self) -> List[Dict[str, Any]]:
        """
        Load command history data from CSV file.
        
        Returns:
            List of command history records
        """
        if not os.path.exists(self.command_history_file):
            print(f"Command history file not found: {self.command_history_file}")
            return []
            
        try:
            commands = []
            with open(self.command_history_file, 'r', newline='') as f:
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
                        except (json.JSONDecodeError, ValueError) as e:
                            print(f"Error parsing row: {row} - {e}")
                            continue
            
            return commands
            
        except Exception as e:
            print(f"Error loading command history: {e}")
            return []
    
    def compute_command_similarity(self, cmd1: Dict[str, Any], cmd2: Dict[str, Any]) -> float:
        """
        Compute similarity between two commands based on intent and entities.
        
        Args:
            cmd1: First command
            cmd2: Second command
            
        Returns:
            Similarity score between 0 and 1
        """
        # If intents are different, start with a base similarity
        if cmd1["intent"] == cmd2["intent"]:
            base_similarity = 0.7  # High base similarity for same intent
        else:
            # Check if intents belong to the same predefined cluster
            same_cluster = False
            for cluster_name, intents in self.predefined_clusters.items():
                if cmd1["intent"] in intents and cmd2["intent"] in intents:
                    same_cluster = True
                    break
            
            base_similarity = 0.4 if same_cluster else 0.1  # Lower base for different intents
        
        # Compare entities
        entity_similarity = 0.0
        entity_weight_total = 0.0
        
        # Get all entity types from both commands
        all_entity_types = set(cmd1["entities"].keys()) | set(cmd2["entities"].keys())
        
        for entity_type in all_entity_types:
            # Get the weight for this entity type
            weight = self.entity_weights.get(entity_type, 0.5)  # Default weight if not specified
            entity_weight_total += weight
            
            # If both commands have this entity type
            if entity_type in cmd1["entities"] and entity_type in cmd2["entities"]:
                # If entity values are the same, add full weight
                if cmd1["entities"][entity_type] == cmd2["entities"][entity_type]:
                    entity_similarity += weight
                else:
                    # Partial match for different values of same entity type
                    entity_similarity += weight * 0.5
        
        # Normalize entity similarity
        if entity_weight_total > 0:
            normalized_entity_similarity = entity_similarity / entity_weight_total
        else:
            normalized_entity_similarity = 0.0
        
        # Combined similarity (intent similarity + entity similarity)
        combined_similarity = base_similarity * 0.6 + normalized_entity_similarity * 0.4
        
        return combined_similarity
    
    def find_command_cluster(self, command: Dict[str, Any]) -> str:
        """
        Find the most appropriate cluster for a command.
        
        Args:
            command: Command to cluster
            
        Returns:
            Cluster ID for the command
        """
        # Check if the intent is in a predefined cluster
        for cluster_name, intents in self.predefined_clusters.items():
            if command["intent"] in intents:
                return cluster_name
        
        # No predefined cluster found, create a new one based on the intent
        return f"cluster_{command['intent']}"
    
    def enhance_suggestion_with_clusters(self, current_intent: str, current_entities: Dict[str, Any],
                                          base_suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance suggestions by considering command clusters.
        
        Args:
            current_intent: Current command intent
            current_entities: Current command entities
            base_suggestions: Original suggestions from command suggestion system
            
        Returns:
            Enhanced list of suggestions
        """
        # If no base suggestions, return empty list
        if not base_suggestions:
            return []
        
        # Create a command object for similarity comparison
        current_command = {
            "intent": current_intent,
            "entities": current_entities
        }
        
        # Find the cluster for the current command
        current_cluster = self.find_command_cluster(current_command)
        
        # Get all commands in the same cluster
        self.command_clusters.get(current_cluster, [])
        
        # Calculate similarity of base suggestions with the current command
        suggestion_scores = []
        for suggestion in base_suggestions:
            suggestion_command = {
                "intent": suggestion["intent"],
                "entities": suggestion.get("entities", {})
            }
            
            # Check if suggestion is in the same cluster
            suggestion_cluster = self.find_command_cluster(suggestion_command)
            cluster_bonus = 0.2 if suggestion_cluster == current_cluster else 0.0
            
            # Compute base similarity
            similarity = self.compute_command_similarity(current_command, suggestion_command)
            
            # Apply cluster bonus
            adjusted_score = min(1.0, similarity + cluster_bonus)
            
            suggestion_scores.append((suggestion, adjusted_score))
        
        # Sort suggestions by adjusted score
        suggestion_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return the enhanced suggestions
        enhanced_suggestions = [item[0] for item in suggestion_scores]
        
        return enhanced_suggestions
    
    def update_clusters(self):
        """
        Update command clusters based on command history.
        """
        # Load command history
        commands = self.load_command_history()
        
        if not commands:
            print("No command history available for clustering")
            return
        
        # Reset clusters
        self.command_clusters = {cluster_name: [] for cluster_name in self.predefined_clusters.keys()}
        
        # Assign commands to clusters
        for command in commands:
            cluster_id = self.find_command_cluster(command)
            
            # Add to appropriate cluster
            if cluster_id not in self.command_clusters:
                self.command_clusters[cluster_id] = []
            
            # Add command to cluster if not already present
            command_key = f"{command['intent']}_{json.dumps(command['entities'], sort_keys=True)}"
            if command_key not in self.command_clusters[cluster_id]:
                self.command_clusters[cluster_id].append(command_key)
        
        # Save updated clusters
        self.save_clusters()
        
        print(f"Updated {len(self.command_clusters)} command clusters")
    
    def get_cluster_for_intent(self, intent: str) -> str:
        """
        Get the cluster ID for a given intent.
        
        Args:
            intent: Command intent
            
        Returns:
            Cluster ID
        """
        # Check predefined clusters first
        for cluster_name, intents in self.predefined_clusters.items():
            if intent in intents:
                return cluster_name
        
        # If not found in predefined clusters, use intent-based cluster
        return f"cluster_{intent}"
    
    def get_related_intents(self, intent: str, max_count: int = 5) -> List[str]:
        """
        Get related intents from the same cluster.
        
        Args:
            intent: Current intent
            max_count: Maximum number of related intents to return
            
        Returns:
            List of related intents
        """
        # Get the cluster for this intent
        cluster_id = self.get_cluster_for_intent(intent)
        
        # Get all commands in this cluster
        cluster_commands = self.command_clusters.get(cluster_id, [])
        
        # Extract unique intents from the cluster commands
        related_intents = set()
        for command_key in cluster_commands:
            # Extract intent from command_key (format: "intent_entities")
            command_intent = command_key.split('_')[0]
            if command_intent != intent:  # Don't include the original intent
                related_intents.add(command_intent)
        
        # If we found related intents in the same cluster, return them
        if related_intents:
            return list(related_intents)[:max_count]
        
        # If no related intents found in the same cluster, use predefined clusters
        for cluster_name, intents in self.predefined_clusters.items():
            if intent in intents:
                # Return other intents from this predefined cluster
                return [i for i in intents if i != intent][:max_count]
        
        # If all else fails, return an empty list
        return []


def main():
    """Test and demonstrate the command clustering engine."""
    print("Command Clustering Engine - Test")
    
    engine = CommandClusteringEngine()
    engine.update_clusters()
    
    # Test finding related intents
    test_intents = ["play_music", "turn_on", "set_timer", "check_weather", "send_message"]
    
    for intent in test_intents:
        related = engine.get_related_intents(intent)
        print(f"\nIntent: {intent}")
        print(f"Related intents: {related}")
    
    print("\nClustering complete!")


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
