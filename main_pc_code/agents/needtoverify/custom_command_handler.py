from common.core.base_agent import BaseAgent
"""
Custom Command Handler for Voice Assistant
------------------------------------------
Manages user-defined commands and aliases using Jarvis Memory Agent
"""
import zmq
import json
import logging
import time
import sys
import os
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union

# Import CLI/agent args parser
from main_pc_code.utils.config_parser import parse_agent_args
from common.env_helpers import get_env

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
_agent_args = parse_agent_args()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CustomCommandHandler")

# ZMQ Configuration
ZMQ_JARVIS_MEMORY_PORT = 5598

class CustomCommandHandler(BaseAgent):
    """Manages user-defined commands and command aliases"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CustomCommandHandler")
        """Initialize the custom command handler
        
        Args:
            zmq_port: Port for Jarvis Memory Agent
        """
        # Determine port for Jarvis Memory Agent safely
        zmq_port = kwargs.get('zmq_port', getattr(_agent_args, 'port', ZMQ_JARVIS_MEMORY_PORT))
        # Use a separate context for the memory socket
        self.memory_context = zmq.Context()
        self.memory_socket = self.memory_context.socket(zmq.REQ)
        self.memory_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.connect(f"tcp://localhost:{zmq_port}")
        logger.info(f"Connected to Jarvis Memory Agent on port {zmq_port}")
        
        # Command cache for faster lookup
        self.command_cache = {}
        self.cache_last_updated = 0
        self.cache_ttl = 60  # Cache TTL in seconds
        
        # Command registration patterns
        self.registration_patterns = [
            # "Create a command X to do Y"
            re.compile(r'create\s+(?:a\s+)?command\s+(?:called\s+)?["\']?([^"\']+)["\']?\s+to\s+(.*)', re.IGNORECASE),
            
            # "Add an alias X for Y"
            re.compile(r'add\s+(?:an\s+)?alias\s+(?:called\s+)?["\']?([^"\']+)["\']?\s+for\s+(.*)', re.IGNORECASE),
            
            # Tagalog: "Gumawa ng command na X para gawin Y"
            re.compile(r'gumawa\s+ng\s+command\s+na\s+["\']?([^"\']+)["\']?\s+para\s+(.*)', re.IGNORECASE),
        ]
    
    def _refresh_command_cache(self, user_id="default"):
        """Refresh the command cache from Jarvis Memory
        
        Args:
            user_id: User ID to get commands for
        """
        current_time = time.time()
        
        # Only refresh cache if TTL has expired
        if current_time - self.cache_last_updated < self.cache_ttl and user_id in self.command_cache:
            return
        
        try:
            # Request all user memories from Jarvis Memory Agent
            request = {
                "action": "get_memories",
                "user_id": user_id
            }
            
            self.memory_socket.send_string(json.dumps(request))
            response = self.memory_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                memories = result.get("memories", [])
                
                # Filter for custom commands
                commands = {}
                for memory in memories:
                    memory_data = memory.get("memory", {})
                    if memory_data.get("type") == "custom_command":
                        trigger = memory_data.get("trigger_phrase", "").lower()
                        if trigger:
                            commands[trigger] = memory_data
                
                # Update cache
                self.command_cache[user_id] = commands
                self.cache_last_updated = current_time
                
                logger.info(f"Refreshed command cache for user {user_id}: {len(commands)} commands")
            else:
                logger.warning(f"Failed to get memories from Jarvis Memory Agent: {result.get('reason', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error refreshing command cache: {e}")
    
    def get_command(self, text: str, user_id="default") -> Optional[Dict[str, Any]]:
        """Check if text matches any custom command
        
        Args:
            text: The text to check for command matches
            user_id: User ID to get commands for
            
        Returns:
            Command data if matched, None otherwise
        """
        # Refresh cache if needed
        self._refresh_command_cache(user_id)
        
        # Clean and normalize input text
        text = text.lower().strip()
        
        # Check for exact matches
        user_commands = self.command_cache.get(user_id, {})
        if text in user_commands:
            return user_commands[text]
        
        # Check for partial matches at the beginning of the text
        for trigger, command in user_commands.items():
            if text.startswith(trigger + " "):
                # Extract parameters from remaining text
                params = text[len(trigger):].strip()
                
                # Clone command and add extracted parameters
                result = command.copy()
                result["params"] = params
                return result
        
        return None
    
    def detect_command_registration(self, text: str) -> Optional[Tuple[str, str]]:
        """Detect command registration intent in text
        
        Args:
            text: Text to check for command registration
            
        Returns:
            Tuple of (trigger_phrase, action_value) if command registration detected,
            None otherwise
        """
        text = text.strip()
        
        for pattern in self.registration_patterns:
            match = pattern.search(text)
            if match:
                trigger_phrase = match.group(1).strip()
                action_value = match.group(2).strip()
                return (trigger_phrase, action_value)
        
        return None
    
    def register_command(self, trigger_phrase: str, action_type: str, action_value: str, user_id="default") -> bool:
        """Register a new custom command
        
        Args:
            trigger_phrase: Phrase that triggers the command
            action_type: Type of action ("alias_for" or "execute_command")
            action_value: Value for the action (original command or command to execute)
            user_id: User ID to register command for
            
        Returns:
            True if command was registered successfully, False otherwise
        """
        try:
            # Normalize trigger phrase
            trigger_phrase = trigger_phrase.lower().strip()
            
            # Create command memory entry
            command_data = {
                "type": "custom_command",
                "trigger_phrase": trigger_phrase,
                "action_type": action_type,
                "action_value": action_value,
                "created_at": time.time()
            }
            
            # Add to Jarvis Memory
            request = {
                "action": "add_memory",
                "user_id": user_id,
                "memory": command_data
            }
            
            self.memory_socket.send_string(json.dumps(request))
            response = self.memory_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                # Update cache
                if user_id not in self.command_cache:
                    self.command_cache[user_id] = {}
                
                self.command_cache[user_id][trigger_phrase] = command_data
                logger.info(f"Registered command '{trigger_phrase}' for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to register command: {result.get('reason', 'Unknown error')}")
                return False
        
        except Exception as e:
            logger.error(f"Error registering command: {e}")
            return False
    
    def delete_command(self, trigger_phrase: str, user_id="default") -> bool:
        """Delete a custom command
        
        Args:
            trigger_phrase: Trigger phrase of command to delete
            user_id: User ID the command belongs to
            
        Returns:
            True if command was deleted successfully, False otherwise
        """
        try:
            # Normalize trigger phrase
            trigger_phrase = trigger_phrase.lower().strip()
            
            # Refresh cache to get latest commands
            self._refresh_command_cache(user_id)
            
            # Find command in cache
            user_commands = self.command_cache.get(user_id, {})
            if trigger_phrase not in user_commands:
                logger.warning(f"Command '{trigger_phrase}' not found for user {user_id}")
                return False
            
            # Request all memories to find the one to delete
            request = {
                "action": "get_memories",
                "user_id": user_id
            }
            
            self.memory_socket.send_string(json.dumps(request))
            response = self.memory_socket.recv_string()
            result = json.loads(response)
            
            if result.get("status") == "ok":
                memories = result.get("memories", [])
                
                # Find memory with matching command
                for memory in memories:
                    memory_data = memory.get("memory", {})
                    if (memory_data.get("type") == "custom_command" and 
                        memory_data.get("trigger_phrase", "").lower() == trigger_phrase):
                        
                        # Delete memory
                        delete_request = {
                            "action": "delete_memory",
                            "user_id": user_id,
                            "memory_id": memory.get("id")
                        }
                        
                        self.memory_socket.send_string(json.dumps(delete_request))
                        delete_response = self.memory_socket.recv_string()
                        delete_result = json.loads(delete_response)
                        
                        if delete_result.get("status") == "ok":
                            # Update cache
                            if user_id in self.command_cache and trigger_phrase in self.command_cache[user_id]:
                                del self.command_cache[user_id][trigger_phrase]
                            
                            logger.info(f"Deleted command '{trigger_phrase}' for user {user_id}")
                            return True
                        else:
                            logger.warning(f"Failed to delete command: {delete_result.get('reason', 'Unknown error')}")
                            return False
                
                logger.warning(f"Command '{trigger_phrase}' not found in memories for user {user_id}")
                return False
            else:
                logger.warning(f"Failed to get memories: {result.get('reason', 'Unknown error')}")
                return False
        
        except Exception as e:
            logger.error(f"Error deleting command: {e}")
            return False
    
    def list_commands(self, user_id="default") -> List[Dict[str, Any]]:
        """List all custom commands for a user
        
        Args:
            user_id: User ID to list commands for
            
        Returns:
            List of command data dictionaries
        """
        # Refresh cache to get latest commands
        self._refresh_command_cache(user_id)
        
        # Get commands from cache
        user_commands = self.command_cache.get(user_id, {})
        return list(user_commands.values())
    
    def process_command_registration(self, text: str, user_id="default") -> Optional[str]:
        """Process command registration from text
        
        Args:
            text: Text containing command registration
            user_id: User ID to register command for
            
        Returns:
            Confirmation message if command was registered, None otherwise
        """
        registration = self.detect_command_registration(text)
        if not registration:
            return None
        
        trigger_phrase, action_value = registration
        
        # Determine if this is an alias or a new command
        if "alias" in text.lower():
            action_type = "alias_for"
            success = self.register_command(trigger_phrase, action_type, action_value, user_id)
            
            if success:
                return f"I've created the alias '{trigger_phrase}' for '{action_value}'"
            else:
                return f"I couldn't create the alias. Please try again."
        else:
            action_type = "execute_command"
            success = self.register_command(trigger_phrase, action_type, action_value, user_id)
            
            if success:
                return f"I've created the command '{trigger_phrase}' that will do: {action_value}"
            else:
                return f"I couldn't create the command. Please try again."

# Example usage
if __name__ == "__main__":
    handler = CustomCommandHandler()
    
    # Test command registration
    test_texts = [
        "Create a command weather to tell me the current weather",
        "Add an alias 'wm' for weather in Manila",
        "Gumawa ng command na 'bukas' para open the file",
        "What time is it?",  # Not a command registration
    ]
    
    for text in test_texts:
        print(f"\nText: {text}")
        result = handler.process_command_registration(text)
        if result:
            print(f"Registration result: {result}")
        else:
            print("Not a command registration")
    
    # Test command lookup
    test_commands = [
        "weather",
        "wm",
        "bukas",
        "what time is it",  # Not a custom command
    ]
    
    for command in test_commands:
        print(f"\nCommand: {command}")
        result = handler.get_command(command)
        if result:
            print(f"Command found: {result}")
        else:
            print("Command not found")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise