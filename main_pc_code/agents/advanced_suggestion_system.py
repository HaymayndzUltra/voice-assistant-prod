from common.config_manager import get_service_ip, get_service_url
from common.utils.path_env import get_main_pc_code, get_project_root
from main_pc_code.src.core.base_agent import BaseAgent
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Advanced Command Suggestion System
----------------------------------
Enhanced suggestion system with deep learning integration,
user feedback analysis, and contextual awareness.

Features:
- Command pattern learning with neural networks
- User feedback and preference tracking
- Context-aware recommendations
- Integration with Digital Twin and Learning Mode agents
"""

import os
import sys
import json
import csv
import time
import threading
import pickle
import logging
import zmq
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter

# Add parent directory to path to import modules

# Import optimized suggestion system as base
from command_suggestion_optimized import CommandSuggestionOptimized

# Import clustering if available
try:
    from command_clustering import CommandClusteringEngine
from common.utils.path_env import get_main_pc_code, get_project_root
    except ImportError as e:
        print(f"Import error: {e}")

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logs",
            "advanced_suggestion.log"
        )),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AdvancedSuggestion")

# ZMQ Configuration
ZMQ_LEARNING_MODE_PORT = 5561  # Port for Learning Mode Agent
ZMQ_DIGITAL_TWIN_PORT = 5560   # Port for Digital Twin Agent
ZMQ_CONTEXTUAL_MEMORY_PORT = 5596  # For Contextual Memory Agent (replaced Context Summarizer)

class AdvancedSuggestionSystem(BaseAgent)(CommandSuggestionOptimized):
    """
    Advanced command suggestion system with deep learning and context awareness
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="AdvancedSuggestionSystem")
        """
        Initialize the advanced suggestion system
        
        Args:
            history_file: Path to command history CSV file
            suggestion_file: Path to save suggestion patterns
            learning_mode_port: Port for Learning Mode Agent
            digital_twin_port: Port for Digital Twin Agent
            context_summarizer_port: Port for Context Summarizer Agent
        """
        # Initialize base class super(BaseAgent)().__init__(history_file, suggestion_file)
        
        # ZMQ setup for additional agents
        self.learning_mode_socket = self.context.socket(zmq.REQ)
        self.learning_mode_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.learning_mode_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.learning_mode_socket.connect(f"tcp://{get_service_ip("pc2")}:{learning_mode_port}")  # PC2
        logger.info(f"Connected to Learning Mode Agent on port {learning_mode_port}")
        
        self.digital_twin_socket = self.context.socket(zmq.REQ)
        self.digital_twin_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.digital_twin_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.digital_twin_socket.connect(f"tcp://{get_service_ip("pc2")}:{digital_twin_port}")  # PC2
        logger.info(f"Connected to Digital Twin Agent on port {digital_twin_port}")
        
        # Connect to Contextual Memory Agent (PC2)
        self.contextual_memory_socket = self.context.socket(zmq.REQ)
        self.contextual_memory_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.contextual_memory_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.contextual_memory_socket.setsockopt(zmq.LINGER, 0)
        self.contextual_memory_socket.connect(f"tcp://{get_service_ip("pc2")}:{contextual_memory_port}")  # PC2
        logger.info(f"Connected to Contextual Memory Agent on port {contextual_memory_port}")
        
        # User expertise tracking
        self.user_expertise = {}  # Cache for user expertise levels
        self.expertise_cache_ttl = 3600  # TTL in seconds (1 hour)
        self.expertise_last_updated = {}  # Timestamp of last update by user
        
        # Context awareness
        self.context_cache = {}  # Cache for context summaries
        self.context_cache_ttl = 300  # TTL in seconds (5 minutes)
        self.context_last_updated = {}  # Timestamp of last update by user
        
        # Advanced suggestion model state
        self.model_initialized = False
        self.model = None
        self.embeddings = {}
        self.init_advanced_model()
        
        # Feedback history
        self.feedback_history_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "command_feedback.csv"
        )
        self._ensure_feedback_file_exists()
        
        # Start additional background thread for model training
        self.model_training_thread = threading.Thread(
            target=self._model_training_loop,
            daemon=True
        )
        self.model_training_thread.start()
    
    def _ensure_feedback_file_exists(self):
        """Ensure feedback history file exists with proper structure"""
        if not os.path.exists(self.feedback_history_file):
            try:
                with open(self.feedback_history_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp", "user_id", "suggestion_id", "suggested_command", 
                                     "accepted", "context", "expertise_level"])
                logger.info(f"Created feedback history file: {self.feedback_history_file}")
            except Exception as e:
                logger.error(f"Error creating feedback history file: {e}")
    
    def init_advanced_model(self):
        """Initialize the advanced suggestion model"""
        try:
            # Try to load a pre-trained model if it exists
            model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "suggestion_model.pkl"
            )
            
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data.get("model")
                    self.embeddings = model_data.get("embeddings", {})
                    logger.info("Loaded pre-trained suggestion model")
                    self.model_initialized = True
            else:
                # If no model exists, initialize with default values
                # In a real implementation, this would use a proper ML model
                # For now, we'll use a simple placeholder
                self.model = {
                    "weights": defaultdict(lambda: 0.5),
                    "features": ["time_of_day", "day_of_week", "previous_command", 
                                "user_expertise", "context_keywords"]
                }
                logger.info("Initialized default suggestion model")
                self.model_initialized = True
                
        except Exception as e:
            logger.error(f"Error initializing advanced model: {e}")
            # Fall back to base implementation
            self.model_initialized = False
    
    def _model_training_loop(self):
        """Background thread for periodic model training"""
        while True:
            try:
                # Sleep for a longer period between training sessions
                time.sleep(3600)  # Train once per hour
                
                if not self.model_initialized:
                    self.init_advanced_model()
                    continue
                
                # Get command history and feedback data
                commands = self._get_command_history()
                feedback = self._get_feedback_history()
                
                if not commands or not feedback:
                    logger.info("Not enough data for model training")
                    continue
                
                logger.info("Training suggestion model...")
                self._train_model(commands, feedback)
                logger.info("Model training complete")
                
                # Save the model
                self._save_model()
                
            except Exception as e:
                logger.error(f"Error in model training loop: {e}")
                time.sleep(600)  # Wait 10 minutes on error
    
    def _train_model(self, commands, feedback):
        """
        Train the suggestion model using command history and feedback
        
        Args:
            commands: List of command history records
            feedback: List of feedback records
        """
        # In a real implementation, this would use actual machine learning
        # For demonstration, we'll use a simple weights update based on feedback
        
        # Group feedback by suggestion
        suggestion_feedback = defaultdict(list)
        for record in feedback:
            suggestion_id = record.get("suggestion_id", "")
            if suggestion_id:
                suggestion_feedback[suggestion_id].append(record)
        
        # Update weights based on feedback
        for suggestion_id, records in suggestion_feedback.items():
            # Calculate acceptance rate
            accepted = sum(1 for r in records if r.get("accepted", False))
            total = len(records)
            acceptance_rate = accepted / total if total > 0 else 0.5
            
            # Update model weights
            feature_key = f"suggestion:{suggestion_id}"
            self.model["weights"][feature_key] = 0.7 * self.model["weights"].get(feature_key, 0.5) + 0.3 * acceptance_rate
        
        # Analyze command patterns and update weights
        for i in range(len(commands) - 1):
            current_cmd = commands[i]
            next_cmd = commands[i + 1]
            
            # Update transition probability
            transition_key = f"transition:{current_cmd['intent']}:{next_cmd['intent']}"
            self.model["weights"][transition_key] = self.model["weights"].get(transition_key, 0) + 1
        
        # Normalize transition weights
        transitions = {}
        for key, value in self.model["weights"].items():
            if key.startswith("transition:"):
                parts = key.split(":")
                if len(parts) == 3:
                    source = parts[1]
                    if source not in transitions:
                        transitions[source] = []
                    transitions[source].append((key, value))
        
        for source, items in transitions.items():
            total = sum(weight for _, weight in items)
            if total > 0:
                for key, _ in items:
                    self.model["weights"][key] /= total
    
    def _save_model(self):
        """Save the trained model to disk"""
        try:
            model_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "suggestion_model.pkl"
            )
            
            model_data = {
                "model": self.model,
                "embeddings": self.embeddings,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Saved suggestion model to {model_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def _get_feedback_history(self) -> List[Dict[str, Any]]:
        """
        Get feedback history from CSV file
        
        Returns:
            List of feedback records
        """
        records = []
        
        if not os.path.exists(self.feedback_history_file):
            return records
        
        try:
            with open(self.feedback_history_file, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 7:
                        timestamp, user_id, suggestion_id, suggested_command, accepted, context, expertise_level = row
                        records.append({
                            "timestamp": timestamp,
                            "user_id": user_id,
                            "suggestion_id": suggestion_id,
                            "suggested_command": suggested_command,
                            "accepted": accepted.lower() == "true",
                            "context": context,
                            "expertise_level": expertise_level
                        })
            
            return records
            
        except Exception as e:
            logger.error(f"Error reading feedback history: {e}")
            return []
    
    def record_feedback(self, user_id: str, suggestion_id: str, suggested_command: str, 
                       accepted: bool, context: str = "", expertise_level: str = ""):
        """
        Record user feedback on a suggestion
        
        Args:
            user_id: User ID
            suggestion_id: Suggestion ID
            suggested_command: The suggested command
            accepted: Whether the suggestion was accepted
            context: Context information
            expertise_level: User expertise level
        """
        try:
            # Get user expertise if not provided
            if not expertise_level:
                expertise_level = self._get_user_expertise(user_id)
            
            # Append to feedback history file
            with open(self.feedback_history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().isoformat(),
                    user_id,
                    suggestion_id,
                    suggested_command,
                    str(accepted),
                    context,
                    expertise_level
                ])
            
            logger.info(f"Recorded feedback for suggestion {suggestion_id}: {'accepted' if accepted else 'rejected'}")
            
            # Send feedback to Learning Mode Agent for further analysis
            self._send_feedback_to_learning_mode(user_id, suggestion_id, suggested_command, accepted, context, expertise_level)
            
        except Exception as e:
            logger.error(f"Error recording feedback: {e}")
    
    def _send_feedback_to_learning_mode(self, user_id, suggestion_id, suggested_command, accepted, context, expertise_level):
        """Send feedback data to Learning Mode Agent"""
        try:
            feedback_data = {
                "action": "process_suggestion_feedback",
                "user_id": user_id,
                "suggestion_id": suggestion_id,
                "suggested_command": suggested_command,
                "accepted": accepted,
                "context": context,
                "expertise_level": expertise_level,
                "timestamp": datetime.now().isoformat()
            }
            
            self.learning_mode_socket.send_string(json.dumps(feedback_data))
            _ = self.learning_mode_socket.recv_string()  # Wait for acknowledgment
            
        except Exception as e:
            logger.error(f"Error sending feedback to Learning Mode: {e}")
    
    def _get_user_expertise(self, user_id: str) -> str:
        """
        Get user expertise level from Digital Twin Agent
        
        Args:
            user_id: User ID
            
        Returns:
            Expertise level (beginner, intermediate, advanced, expert)
        """
        # Check cache first
        current_time = time.time()
        if user_id in self.user_expertise and current_time - self.expertise_last_updated.get(user_id, 0) < self.expertise_cache_ttl:
            return self.user_expertise[user_id]
        
        try:
            # Request expertise from Digital Twin Agent
            request = {
                "action": "get_user_expertise",
                "user_id": user_id
            }
            
            self.digital_twin_socket.send_string(json.dumps(request))
            response = self.digital_twin_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                expertise = result.get("expertise", "beginner")
                # Update cache
                self.user_expertise[user_id] = expertise
                self.expertise_last_updated[user_id] = current_time
                return expertise
            else:
                logger.warning(f"Failed to get expertise: {result.get('reason', 'Unknown error')}")
                return "beginner"  # Default to beginner
        
        except Exception as e:
            logger.error(f"Error getting user expertise: {e}")
            return "beginner"  # Default to beginner
            
    def _get_context_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get context summary from Contextual Memory Agent
        
        Args:
            user_id: User ID
            
        Returns:
            Context summary dictionary
        """
        # Check cache first
        current_time = time.time()
        if user_id in self.context_cache and current_time - self.context_last_updated.get(user_id, 0) < self.context_cache_ttl:
            return self.context_cache[user_id]
        
        try:
            # Request context from Contextual Memory Agent
            request = {
                "action": "get_context_summary",
                "user_id": user_id
            }
            
            self.contextual_memory_socket.send_string(json.dumps(request))
            response = self.contextual_memory_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                context = result.get("context", {})
                # Update cache
                self.context_cache[user_id] = context
                self.context_last_updated[user_id] = current_time
                return context
            else:
                logger.warning(f"Failed to get context: {result.get('reason', 'Unknown error')}")
                return {}  # Default empty context
                
        except Exception as e:
            logger.error(f"Error getting context summary: {e}")
            return {}  # Default empty context
    
    def _extract_features(self, user_id: str, intent: str, entities: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract features for advanced suggestion ranking
        
        Args:
            user_id: User ID
            intent: Current command intent
            entities: Command entities
            
        Returns:
            Dictionary of feature values
        """
        features = {}
        
        # Basic time features
        now = datetime.now()
        features["time_of_day"] = now.hour / 24.0  # Normalize to 0-1
        features["day_of_week"] = now.weekday() / 6.0  # Normalize to 0-1
        
        # User expertise
        expertise_level = self._get_user_expertise(user_id)
        expertise_values = {"beginner": 0.0, "intermediate": 0.33, "advanced": 0.67, "expert": 1.0}
        features["user_expertise"] = expertise_values.get(expertise_level, 0.0)
        
        # Previous commands
        if user_id in self.user_last_commands and self.user_last_commands[user_id]:
            previous = self.user_last_commands[user_id][-1]
            features[f"prev_intent_{previous['intent']}"] = 1.0
        
        # Context features
        context = self._get_context_summary(user_id)
        for key, value in context.items():
            if isinstance(value, (int, float)):
                features[f"context_{key}"] = float(value)
            elif isinstance(value, bool):
                features[f"context_{key}"] = 1.0 if value else 0.0
            elif isinstance(value, str) and key == "location":
                features[f"context_location_{value.lower()}"] = 1.0
                
        # Intent and entity features
        features[f"intent_{intent}"] = 1.0
        for entity_key, entity_value in entities.items():
            if isinstance(entity_value, (int, float)):
                features[f"entity_{entity_key}"] = float(entity_value)
            elif isinstance(entity_value, bool):
                features[f"entity_{entity_key}"] = 1.0 if entity_value else 0.0
            elif isinstance(entity_value, str):
                features[f"entity_{entity_key}_{entity_value.lower()}"] = 1.0
        
        return features
    
    def _rank_suggestions(self, user_id: str, intent: str, entities: Dict[str, Any], 
                         base_suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank suggestions using the advanced model
        
        Args:
            user_id: User ID
            intent: Current command intent
            entities: Command entities
            base_suggestions: Original list of suggestions
            
        Returns:
            Ranked list of suggestions
        """
        if not self.model_initialized or not base_suggestions:
            return base_suggestions
        
        try:
            # Extract features
            features = self._extract_features(user_id, intent, entities)
            
            # Score each suggestion
            scored_suggestions = []
            for suggestion in base_suggestions:
                score = 0.0
                
                # Base score from transition probability
                transition_key = f"transition:{intent}:{suggestion['intent']}"
                transition_prob = self.model["weights"].get(transition_key, 0.1)
                score += transition_prob * 0.5  # 50% weight on transition probability
                
                # Score from suggestion feedback
                suggestion_id = suggestion.get("id", f"{suggestion['intent']}_{str(uuid.uuid4())[:8]}")
                if "id" not in suggestion:
                    suggestion["id"] = suggestion_id
                
                feedback_key = f"suggestion:{suggestion_id}"
                feedback_score = self.model["weights"].get(feedback_key, 0.5)
                score += feedback_score * 0.3  # 30% weight on feedback score
                
                # Score from context match
                context_score = 0.0
                context_count = 0
                for feature_key, feature_value in features.items():
                    if feature_key.startswith("context_"):
                        context_weight = self.model["weights"].get(f"context_weight:{feature_key}", 0.5)
                        context_score += feature_value * context_weight
                        context_count += 1
                
                if context_count > 0:
                    context_score /= context_count
                    score += context_score * 0.2  # 20% weight on context match
                
                # Add expertise-specific adjustment
                expertise = features.get("user_expertise", 0.0)
                if expertise < 0.3:  # Beginner
                    # Beginners get simpler suggestions
                    simplicity = self.model["weights"].get(f"simplicity:{suggestion['intent']}", 0.5)
                    score += simplicity * 0.1  # 10% extra weight for simplicity
                elif expertise > 0.7:  # Expert
                    # Experts get more advanced suggestions
                    advanced = self.model["weights"].get(f"advanced:{suggestion['intent']}", 0.5)
                    score += advanced * 0.1  # 10% extra weight for advanced features
                
                scored_suggestions.append((suggestion, score))
            
            # Sort by score (descending)
            scored_suggestions.sort(key=lambda x: x[1], reverse=True)
            
            # Return sorted suggestions
            return [s[0] for s in scored_suggestions]
            
        except Exception as e:
            logger.error(f"Error ranking suggestions: {e}")
            return base_suggestions  # Fall back to original order
    
    def get_suggestions(self, user_id: str, intent: str, entities: Dict[str, Any], confidence: float) -> List[Dict[str, Any]]:
        """
        Get command suggestions with advanced ranking and context awareness
        
        Args:
            user_id: User ID
            intent: Command intent
            entities: Command entities
            confidence: Confidence score
            
        Returns:
            List of suggested commands
        """
        # Get base suggestions from parent class base_suggestions(BaseAgent) = super().get_suggestions(user_id, intent, entities, confidence)
        
        # Apply advanced ranking if model is initialized
        if self.model_initialized:
            enhanced_suggestions = self._rank_suggestions(user_id, intent, entities, base_suggestions)
        else:
            enhanced_suggestions = base_suggestions
        
        # Add suggestion IDs if not present
        for suggestion in enhanced_suggestions:
            if "id" not in suggestion:
                suggestion["id"] = f"{suggestion['intent']}_{str(uuid.uuid4())[:8]}"
        
        # Add user expertise level to suggestions for UI adaptation
        expertise_level = self._get_user_expertise(user_id)
        for suggestion in enhanced_suggestions:
            suggestion["user_expertise"] = expertise_level
        
        return enhanced_suggestions
    
    def get_progressive_tips(self, user_id: str, intent: str, expertise_level: str = None) -> List[Dict[str, Any]]:
        """
        Get progressive tips based on user expertise level
        
        Args:
            user_id: User ID
            intent: Current command intent
            expertise_level: Optional expertise level override
            
        Returns:
            List of tips appropriate for user expertise
        """
        if expertise_level is None:
            expertise_level = self._get_user_expertise(user_id)
        
        # Define tips for different expertise levels
        all_tips = {
            "beginner": [
                {"tip": "Try saying 'help' to see available commands", "intent": "help"},
                {"tip": "You can say 'repeat that' to hear the last response again", "intent": "repeat"},
                {"tip": f"The '{intent}' command has basic options you can try", "intent": intent}
            ],
            "intermediate": [
                {"tip": f"Try '{intent}' with specific parameters for better results", "intent": intent},
                {"tip": "You can chain commands with 'then' between them", "intent": "command_chain"},
                {"tip": "Create custom commands with 'create a command...'", "intent": "create_command"}
            ],
            "advanced": [
                {"tip": "You can create command sequences for frequent tasks", "intent": "sequence"},
                {"tip": "Try using domain-specific commands for more power", "intent": "domain_commands"},
                {"tip": "Background tasks can be run with 'in background' suffix", "intent": "background"}
            ],
            "expert": [
                {"tip": "Create scripts and link them to voice commands", "intent": "script"},
                {"tip": "Use the coordinator to run parallel tasks", "intent": "parallel"},
                {"tip": "You can fine-tune suggestion algorithms in settings", "intent": "settings"}
            ]
        }
        
        # Get tips for the user's level and below
        tips = []
        expertise_order = ["beginner", "intermediate", "advanced", "expert"]
        expertise_index = expertise_order.index(expertise_level) if expertise_level in expertise_order else 0
        
        # Include some tips from their level and some from the level below (if available)
        if expertise_index > 0:
            # Add 1 tip from the level below
            previous_level = expertise_order[expertise_index - 1]
            tips.extend(random.sample(all_tips[previous_level], min(1, len(all_tips[previous_level]))))
        
        # Add 2 tips from their current level
        tips.extend(random.sample(all_tips[expertise_level], min(2, len(all_tips[expertise_level]))))
        
        # If they're not at expert level, add 1 tip from the level above
        if expertise_index < len(expertise_order) - 1:
            next_level = expertise_order[expertise_index + 1]
            tips.extend(random.sample(all_tips[next_level], min(1, len(all_tips[next_level]))))
        
        # Shuffle the tips
        random.shuffle(tips)
        
        return tips[:2]  # Return at most 2 tips

# Example usage and testing
def main():
    """Test the advanced suggestion system"""
    print("Advanced Suggestion System - Test")
    
    # Create suggestion system
    suggestion_system = AdvancedSuggestionSystem()
    
    try:
        # Test with different user expertise levels
        test_users = {
            "user1": "beginner",
            "user2": "intermediate",
            "user3": "advanced",
            "user4": "expert"
        }
        
        for user_id, expertise in test_users.items():
            # Override the expertise getter
            suggestion_system.user_expertise[user_id] = expertise
            suggestion_system.expertise_last_updated[user_id] = time.time()
            
            # Test getting suggestions
            suggestions = suggestion_system.get_suggestions(
                user_id, "play_music", {"genre": "rock"}, 0.9
            )
            
            print(f"\nUser: {user_id} (Expertise: {expertise})")
            print(f"Suggestions after 'play_music':")
            for i, suggestion in enumerate(suggestions):
                print(f"{i+1}. {suggestion['intent']}")
            
            # Test progressive tips
            tips = suggestion_system.get_progressive_tips(user_id, "play_music")
            print(f"Progressive tips:")
            for tip in tips:
                print(f"- {tip['tip']}")
        
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