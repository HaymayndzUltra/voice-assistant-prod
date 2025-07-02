from main_pc_code.src.core.base_agent import BaseAgent
"""
Digital Twin Agent
-----------------
Manages user expertise profiles and enables progressive disclosure of features
based on skill level. This agent maintains a digital model of the user's preferences,
skill levels in different domains, and interaction patterns.

The agent helps customize the voice assistant experience by:
1. Tracking user expertise across different domains
2. Providing tips and advanced features progressively
3. Personalizing responses based on user preferences
4. Adapting to user behavior over time
"""

import os
import sys
import json
import time
import zmq
import uuid
import logging
import pickle
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DigitalTwinAgent")

# ZMQ port configuration
ZMQ_DIGITAL_TWIN_PORT = os.environ.get("ZMQ_DIGITAL_TWIN_PORT", "5560")
ZMQ_HEALTH_PORT = os.environ.get("ZMQ_HEALTH_PORT", "5597")
ZMQ_JARVIS_MEMORY_PORT = os.environ.get("ZMQ_JARVIS_MEMORY_PORT", "5598")

class UserProfile(BaseAgent):
    """Represents a user's expertise, preferences, and interaction history"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="DigitalTwinAgent")
        """Initialize a new user profile"""
        self.user_id = user_id
        self.created_at = datetime.now().isoformat()
        self.last_updated = self.created_at
        
        # Domain expertise levels (0-100)
        self.expertise = {
            "general": 10,          # General assistant usage
            "system": 5,            # System commands, settings
            "programming": 0,       # Programming and development
            "media": 5,             # Media control and playback
            "productivity": 5,      # Productivity tools, calendar, etc.
            "home_automation": 0,   # Smart home, IoT control
            "web": 5                # Web search, browsing
        }
        
        # Feature usage counters
        self.feature_usage = {
            "basic_commands": 0,
            "custom_commands": 0,
            "domain_commands": 0,
            "sequence_commands": 0,
            "script_commands": 0,
            "parallel_execution": 0
        }
        
        # Preferences
        self.preferences = {
            "verbosity": "medium",      # low, medium, high
            "suggestions": "medium",     # low, medium, high
            "tip_frequency": "medium",   # low, medium, high
            "language": "en",            # en, fil, en-fil (Taglish)
            "voice": "default"
        }
        
        # Command history (recent commands, limited to 100)
        self.command_history = []
        
        # Interaction stats
        self.stats = {
            "total_interactions": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "last_interaction": self.created_at,
            "active_days": 0,
            "longest_streak": 0,
            "current_streak": 0
        }
    
    def update_expertise(self, domain: str, change: float) -> None:
        """Update expertise level for a specific domain"""
        if domain in self.expertise:
            current = self.expertise[domain]
            # Apply change with limits (0-100)
            new_value = max(0, min(100, current + change))
            self.expertise[domain] = new_value
            logger.debug(f"Updated {domain} expertise for {self.user_id}: {current} → {new_value}")
        else:
            # Create new domain if it doesn't exist
            self.expertise[domain] = max(0, min(100, change))
            logger.debug(f"Created new expertise domain {domain} for {self.user_id}: {change}")
        
        self.last_updated = datetime.now().isoformat()
    
    def log_feature_usage(self, feature: str) -> None:
        """Log usage of a feature"""
        if feature in self.feature_usage:
            self.feature_usage[feature] += 1
        else:
            self.feature_usage[feature] = 1
        
        self.last_updated = datetime.now().isoformat()
    
    def log_command(self, command: str, success: bool, domain: Optional[str] = None) -> None:
        """Log a command execution"""
        # Add to command history
        timestamp = datetime.now().isoformat()
        cmd_entry = {
            "command": command,
            "timestamp": timestamp,
            "success": success,
            "domain": domain
        }
        
        self.command_history.append(cmd_entry)
        # Limit history to last 100 commands
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]
        
        # Update stats
        self.stats["total_interactions"] += 1
        if success:
            self.stats["successful_commands"] += 1
        else:
            self.stats["failed_commands"] += 1
        
        self.stats["last_interaction"] = timestamp
        
        # Update expertise
        if domain and success:
            # Successful commands slightly increase expertise
            self.update_expertise(domain, 0.5)
            
            # Also update general expertise
            self.update_expertise("general", 0.2)
        
        self.last_updated = timestamp
    
    def update_streak(self) -> None:
        """Update daily usage streak"""
        last_interaction = datetime.fromisoformat(self.stats["last_interaction"])
        now = datetime.now()
        
        # Check if this is a new day compared to last interaction
        if (last_interaction.date() < now.date()):
            # It's a new day
            self.stats["active_days"] += 1
            
            # Check if it's consecutive (yesterday)
            if (now.date() - last_interaction.date()).days == 1:
                self.stats["current_streak"] += 1
                # Update longest streak if current is longer
                if self.stats["current_streak"] > self.stats["longest_streak"]:
                    self.stats["longest_streak"] = self.stats["current_streak"]
            else:
                # Streak broken (more than one day gap)
                self.stats["current_streak"] = 1
        
        self.last_updated = now.isoformat()
    
    def set_preference(self, key: str, value: Any) -> bool:
        """Set a user preference"""
        if key in self.preferences:
            self.preferences[key] = value
            self.last_updated = datetime.now().isoformat()
            return True
        return False
    
    def get_user_level(self) -> str:
        """Get the user's overall expertise level"""
        general = self.expertise["general"]
        
        if general < 20:
            return "beginner"
        elif general < 50:
            return "intermediate"
        elif general < 80:
            return "advanced"
        else:
            return "expert"
    
    def get_domain_level(self, domain: str) -> str:
        """Get the user's expertise level in a specific domain"""
        level = self.expertise.get(domain, 0)
        
        if level < 20:
            return "beginner"
        elif level < 50:
            return "intermediate"
        elif level < 80:
            return "advanced"
        else:
            return "expert"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization"""
        return {
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "expertise": self.expertise,
            "feature_usage": self.feature_usage,
            "preferences": self.preferences,
            "command_history": self.command_history,
            "stats": self.stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create a UserProfile from a dictionary"""
        profile = cls(data["user_id"])
        profile.created_at = data["created_at"]
        profile.last_updated = data["last_updated"]
        profile.expertise = data["expertise"]
        profile.feature_usage = data["feature_usage"]
        profile.preferences = data["preferences"]
        profile.command_history = data["command_history"]
        profile.stats = data["stats"]
        return profile


class DigitalTwinAgent(BaseAgent):
    """
    Manages user profiles and provides progressive disclosure
    based on user expertise level
    """
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="DigitalTwinAgent")
        """Initialize the Digital Twin Agent"""
        self.data_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "user_profiles"
        )
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing profiles
        self.profiles: Dict[str, UserProfile] = {}
        self._load_profiles()
        
        # Progressive tips database - tips revealed based on expertise level
        self.tips = self._load_tips()
        
        # ZMQ setup
        self.context = zmq.Context()
        
        # Set up REP socket for responding to requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{ZMQ_DIGITAL_TWIN_PORT}")
        logger.info(f"Digital Twin Agent listening on port {ZMQ_DIGITAL_TWIN_PORT}")
        
        # Health reporting socket
        self.health_socket = self.context.socket(zmq.PUB)
        self.health_socket.connect(f"tcp://localhost:{ZMQ_HEALTH_PORT}")
        
        # Memory access socket
        self.memory_socket = self.context.socket(zmq.REQ)
        self.memory_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.connect(f"tcp://localhost:{ZMQ_JARVIS_MEMORY_PORT}")
        
        # Thread for automatic saving
        self.save_thread = threading.Thread(target=self._autosave_thread, daemon=True)
        self.running = True
    
    def _load_profiles(self) -> None:
        """Load user profiles from disk"""
        try:
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    user_id = filename.replace(".json", "")
                    profile_path = os.path.join(self.data_dir, filename)
                    
                    try:
                        with open(profile_path, 'r') as f:
                            profile_data = json.load(f)
                            self.profiles[user_id] = UserProfile.from_dict(profile_data)
                            logger.info(f"Loaded profile for user: {user_id}")
                    except Exception as e:
                        logger.error(f"Error loading profile {profile_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
    
    def _save_profile(self, user_id: str) -> None:
        """Save a user profile to disk"""
        if user_id in self.profiles:
            profile_path = os.path.join(self.data_dir, f"{user_id}.json")
            
            try:
                with open(profile_path, 'w') as f:
                    json.dump(self.profiles[user_id].to_dict(), f, indent=2)
                logger.debug(f"Saved profile for user: {user_id}")
            except Exception as e:
                logger.error(f"Error saving profile {profile_path}: {e}")
    
    def _autosave_thread(self) -> None:
        """Thread for periodically saving profiles"""
        while self.running:
            for user_id in self.profiles:
                self._save_profile(user_id)
            
            # Sleep for 5 minutes
            time.sleep(300)
    
    def _load_tips(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Load progressive tips from embedded data"""
        # Format: {domain: {level: [tips]}}
        return {
            "general": {
                "beginner": [
                    {"tip": "Try saying 'help' to see what I can do.", "shown": False},
                    {"tip": "You can say 'what time is it' to check the current time.", "shown": False},
                    {"tip": "Say 'weather' to get the current weather conditions.", "shown": False}
                ],
                "intermediate": [
                    {"tip": "You can create custom commands with 'create command X to do Y'.", "shown": False},
                    {"tip": "Try chaining commands with 'then' like 'check weather then set a timer'.", "shown": False},
                    {"tip": "Say 'what can you do' to explore more capabilities.", "shown": False}
                ],
                "advanced": [
                    {"tip": "Try creating sequence commands to automate multiple tasks.", "shown": False},
                    {"tip": "Use domain-specific commands for better results in specialized areas.", "shown": False},
                    {"tip": "You can run commands in parallel by saying 'run X and Y at the same time'.", "shown": False}
                ],
                "expert": [
                    {"tip": "Create script commands to execute custom Python or shell scripts.", "shown": False},
                    {"tip": "You can access full documentation with 'show command documentation'.", "shown": False},
                    {"tip": "Try advanced voice command patterns for complex operations.", "shown": False}
                ]
            },
            "programming": {
                "beginner": [
                    {"tip": "Try 'open code editor' to start programming.", "shown": False},
                    {"tip": "You can say 'create a new Python file' to get started.", "shown": False}
                ],
                "intermediate": [
                    {"tip": "Try 'git status' to check your repository status.", "shown": False},
                    {"tip": "Say 'run tests' to execute your test suite.", "shown": False}
                ],
                "advanced": [
                    {"tip": "Create a coding sequence like 'git pull then run tests then git push'.", "shown": False},
                    {"tip": "Use 'explain this code' to analyze selected code snippets.", "shown": False}
                ],
                "expert": [
                    {"tip": "Try 'optimize this function' for code improvement suggestions.", "shown": False},
                    {"tip": "Create custom script commands for your development workflow.", "shown": False}
                ]
            },
            "media": {
                "beginner": [
                    {"tip": "Say 'play music' to start playing music.", "shown": False},
                    {"tip": "Try 'pause' or 'stop' to control playback.", "shown": False}
                ],
                "intermediate": [
                    {"tip": "You can specify genres like 'play jazz music'.", "shown": False},
                    {"tip": "Try 'volume up' or 'volume down' to adjust audio levels.", "shown": False}
                ],
                "advanced": [
                    {"tip": "Create playlists with 'create a playlist called X with Y and Z'.", "shown": False},
                    {"tip": "Use media commands while other tasks are running.", "shown": False}
                ],
                "expert": [
                    {"tip": "Create advanced media automation sequences for your entertainment system.", "shown": False},
                    {"tip": "Try integrating with smart home devices for synchronized experiences.", "shown": False}
                ]
            }
            # Additional domains can be added here
        }
    
    def get_profile(self, user_id: str = "default") -> UserProfile:
        """Get a user profile, creating it if it doesn't exist"""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id)
            logger.info(f"Created new profile for user: {user_id}")
        
        return self.profiles[user_id]
    
    def log_command(self, user_id: str, command: str, success: bool, domain: Optional[str] = None) -> None:
        """Log a command execution for a user"""
        profile = self.get_profile(user_id)
        profile.log_command(command, success, domain)
        profile.update_streak()
    
    def log_feature_usage(self, user_id: str, feature: str) -> None:
        """Log usage of a feature for a user"""
        profile = self.get_profile(user_id)
        profile.log_feature_usage(feature)
    
    def get_expertise_level(self, user_id: str, domain: Optional[str] = None) -> str:
        """Get a user's expertise level overall or in a specific domain"""
        profile = self.get_profile(user_id)
        
        if domain:
            return profile.get_domain_level(domain)
        else:
            return profile.get_user_level()
    
    def update_expertise(self, user_id: str, domain: str, change: float) -> None:
        """Update a user's expertise in a specific domain"""
        profile = self.get_profile(user_id)
        profile.update_expertise(domain, change)
    
    def get_contextual_tip(self, user_id: str, domain: Optional[str] = "general") -> Optional[str]:
        """Get a contextual tip based on user expertise that hasn't been shown before"""
        domain = domain or "general"
        if domain not in self.tips:
            domain = "general"
        
        profile = self.get_profile(user_id)
        level = profile.get_domain_level(domain)
        
        # Get tips for this domain and level
        if level in self.tips[domain]:
            # Find unshown tips
            unshown_tips = [tip for tip in self.tips[domain][level] if not tip["shown"]]
            
            if unshown_tips:
                # Mark the first unshown tip as shown and return it
                tip = unshown_tips[0]
                tip["shown"] = True
                return tip["tip"]
            
            # If all tips at this level have been shown, try the next level
            levels = ["beginner", "intermediate", "advanced", "expert"]
            current_idx = levels.index(level)
            
            # Check if there's a higher level available
            if current_idx < len(levels) - 1:
                next_level = levels[current_idx + 1]
                if next_level in self.tips[domain]:
                    unshown_tips = [tip for tip in self.tips[domain][next_level] if not tip["shown"]]
                    
                    if unshown_tips:
                        # Mark the first unshown tip as shown and return it
                        tip = unshown_tips[0]
                        tip["shown"] = True
                        return tip["tip"]
        
        # No suitable tip found
        return None
    
    def get_appropriate_help(self, user_id: str, command_context: Optional[str] = None) -> str:
        """Get help appropriate to the user's expertise level"""
        profile = self.get_profile(user_id)
        level = profile.get_user_level()
        
        if level == "beginner":
            return self._get_beginner_help(command_context)
        elif level == "intermediate":
            return self._get_intermediate_help(command_context)
        elif level == "advanced":
            return self._get_advanced_help(command_context)
        else:  # expert
            return self._get_expert_help(command_context)
    
    def _get_beginner_help(self, command_context: Optional[str] = None) -> str:
        """Get help for beginner users"""
        if command_context:
            # Context-specific help for beginners
            return f"To use the {command_context} command, just say '{command_context}' followed by what you want. For example, '{command_context} help'."
        
        # General help for beginners
        return """
Here are some basic commands to get started:
- "What time is it" - Check the current time
- "Weather" - Get current weather conditions
- "Play music" - Start playing music
- "Set a timer for X minutes" - Set a countdown timer
- "What can you do" - Learn more about my capabilities
        """
    
    def _get_intermediate_help(self, command_context: Optional[str] = None) -> str:
        """Get help for intermediate users"""
        if command_context:
            # Context-specific help for intermediates
            return f"The {command_context} command supports various options. You can try '{command_context} help' for specific details, or check the documentation."
        
        # General help for intermediates
        return """
Here are some intermediate commands you might find useful:
- Create custom commands with "create command X to do Y"
- Chain commands with "then" like "check weather then set a timer"
- Use "volume up/down" to control audio levels
- Try domain-specific commands like "git status" for programming
- Say "help with X" to get specific guidance on a feature
        """
    
    def _get_advanced_help(self, command_context: Optional[str] = None) -> str:
        """Get help for advanced users"""
        if command_context:
            # Context-specific help for advanced users
            return f"For advanced usage of {command_context}, you can use parameters, chain with other commands, or create custom sequences including it."
        
        # General help for advanced users
        return """
Advanced features you might want to explore:
- Create sequence commands to automate multiple tasks
- Use domain-specific command sets for specialized tasks
- Run commands in parallel with "run X and Y at the same time"
- Create aliases for frequently used commands
- Use custom parameters in your commands
- Try the documentation system with "show command documentation"
        """
    
    def _get_expert_help(self, command_context: Optional[str] = None) -> str:
        """Get help for expert users"""
        if command_context:
            # Context-specific help for experts
            return f"As an expert user, you might want to explore creating script commands that incorporate {command_context}, or integrate it into your custom workflow sequences."
        
        # General help for experts
        return """
Expert features for power users:
- Create script commands to execute custom Python or shell scripts
- Design complex command workflows with conditional execution
- Use advanced voice command patterns for complex operations
- Configure the system with custom parameters
- Explore the API documentation for deep integration
- Contribute to the command ecosystem
        """
    
    def should_show_tip(self, user_id: str) -> bool:
        """Determine if a tip should be shown based on user preferences"""
        profile = self.get_profile(user_id)
        frequency = profile.preferences.get("tip_frequency", "medium")
        
        if frequency == "low":
            # Show tips rarely (1 in 10 chance)
            return random.random() < 0.1
        elif frequency == "medium":
            # Show tips occasionally (1 in 5 chance)
            return random.random() < 0.2
        elif frequency == "high":
            # Show tips frequently (1 in 3 chance)
            return random.random() < 0.33
        else:
            # Default to medium
            return random.random() < 0.2
    
    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a request to the Digital Twin Agent"""
        action = request_data.get("action", "")
        user_id = request_data.get("user_id", "default")
        
        if action == "get_profile":
            # Return the user profile
            profile = self.get_profile(user_id)
            return {
                "status": "success",
                "profile": profile.to_dict()
            }
        
        elif action == "log_command":
            # Log a command execution
            command = request_data.get("command", "")
            success = request_data.get("success", True)
            domain = request_data.get("domain")
            
            self.log_command(user_id, command, success, domain)
            return {"status": "success"}
        
        elif action == "log_feature":
            # Log feature usage
            feature = request_data.get("feature", "")
            
            self.log_feature_usage(user_id, feature)
            return {"status": "success"}
        
        elif action == "get_expertise":
            # Get expertise level
            domain = request_data.get("domain")
            
            level = self.get_expertise_level(user_id, domain)
            return {
                "status": "success",
                "level": level
            }
        
        elif action == "update_expertise":
            # Update expertise level
            domain = request_data.get("domain", "general")
            change = float(request_data.get("change", 0))
            
            self.update_expertise(user_id, domain, change)
            return {"status": "success"}
        
        elif action == "get_tip":
            # Get a contextual tip
            domain = request_data.get("domain", "general")
            
            # Check if we should show a tip based on user preferences
            if not self.should_show_tip(user_id):
                return {
                    "status": "success",
                    "tip": None
                }
            
            tip = self.get_contextual_tip(user_id, domain)
            return {
                "status": "success",
                "tip": tip
            }
        
        elif action == "get_help":
            # Get appropriate help
            context = request_data.get("context")
            
            help_text = self.get_appropriate_help(user_id, context)
            return {
                "status": "success",
                "help": help_text
            }
        
        elif action == "set_preference":
            # Set a user preference
            key = request_data.get("key", "")
            value = request_data.get("value", "")
            
            profile = self.get_profile(user_id)
            success = profile.set_preference(key, value)
            
            return {
                "status": "success" if success else "error",
                "message": f"Preference {key} set to {value}" if success else f"Invalid preference {key}"
            }
        
        else:
            # Unknown action
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
    
    def report_health(self) -> None:
        """Report health status to the health monitoring system"""
        health_data = {
            "agent": "digital_twin",
            "status": "healthy",
            "timestamp": time.time(),
            "details": {
                "profiles_loaded": len(self.profiles),
                "memory_usage_mb": self._get_memory_usage()
            }
        }
        
        try:
            self.health_socket.send_string(f"health {json.dumps(health_data)}")
        except Exception as e:
            logger.error(f"Error reporting health: {e}")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
    except ImportError as e:
        print(f"Import error: {e}")
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def start(self) -> None:
        """Start the Digital Twin Agent"""
        # Start autosave thread
        self.save_thread.start()
        
        logger.info("Digital Twin Agent started")
        
        try:
            # Report initial health
            self.report_health()
            
            # Main loop
            last_health_report = time.time()
            
            while self.running:
                try:
                    # Poll socket with timeout to allow for clean shutdown
                    if self.socket.poll(timeout=1000) == zmq.POLLIN:
                        # Receive request
                        request = self.socket.recv_string()
                        logger.debug(f"Received request: {request}")
                        
                        try:
                            # Parse request JSON
                            request_data = json.loads(request)
                            
                            # Handle request
                            response = self.handle_request(request_data)
                            
                            # Send response
                            self.socket.send_string(json.dumps(response))
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in request: {request}")
                            self.socket.send_string(json.dumps({
                                "status": "error",
                                "message": "Invalid JSON request"
                            }))
                        except Exception as e:
                            logger.error(f"Error handling request: {e}")
                            self.socket.send_string(json.dumps({
                                "status": "error",
                                "message": f"Error: {str(e)}"
                            }))
                    
                    # Report health every 60 seconds
                    current_time = time.time()
                    if current_time - last_health_report >= 60:
                        self.report_health()
                        last_health_report = current_time
                
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
        
        finally:
            # Save all profiles
            for user_id in self.profiles:
                self._save_profile(user_id)
            
            # Clean up
            self.running = False
            self.socket.close()
            self.health_socket.close()
            self.memory_socket.close()
            self.context.term()
            
            logger.info("Digital Twin Agent stopped")

if __name__ == "__main__":
    import random  # For random tip selection probability
    
    # Parse command line arguments
    import argparse

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    parser = argparse.ArgumentParser(description='Digital Twin Agent')
    parser.add_argument('--data-dir', type=str, help='Directory for user profile data')
    args = parser.parse_args()
    
    # Create and start agent
    agent = DigitalTwinAgent(data_dir=args.data_dir)
    
    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("Digital Twin Agent interrupted")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise