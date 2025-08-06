from common.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
"""
Command Confirmation Module for Voice Assistant
----------------------------------------------
Handles critical command confirmation and disambiguation
"""
import logging
import time
import uuid
from typing import Dict, Any, Optional, Tuple

# Setup logging
logger = configure_logging(__name__)
logger = logging.getLogger("CommandConfirmation")

# Criticality levels
CRITICALITY_LOW = "low"       # Informational queries, no state changes
CRITICALITY_MEDIUM = "medium" # Minor system changes, non-destructive operations
CRITICALITY_HIGH = "high"     # File operations, system modifications, data deletion

class CommandConfirmation(BaseAgent):
    """Handles confirmation for critical and ambiguous commands"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CommandConfirmation")
        """Initialize the command confirmation system"""
        # Dictionary of command patterns and their criticality levels
        self.command_criticality = {
            # High criticality commands (potentially destructive)
            "delete": CRITICALITY_HIGH,
            "remove": CRITICALITY_HIGH,
            "uninstall": CRITICALITY_HIGH,
            "format": CRITICALITY_HIGH,
            "wipe": CRITICALITY_HIGH,
            "reset": CRITICALITY_HIGH,
            "purge": CRITICALITY_HIGH,
            
            # Medium criticality commands (system changes)
            "install": CRITICALITY_MEDIUM,
            "update": CRITICALITY_MEDIUM,
            "upgrade": CRITICALITY_MEDIUM,
            "modify": CRITICALITY_MEDIUM,
            "change": CRITICALITY_MEDIUM,
            "edit": CRITICALITY_MEDIUM,
            "rename": CRITICALITY_MEDIUM,
            "move": CRITICALITY_MEDIUM,
            "copy": CRITICALITY_MEDIUM,
            "download": CRITICALITY_MEDIUM,
            "upload": CRITICALITY_MEDIUM,
            "create": CRITICALITY_MEDIUM,
            "open": CRITICALITY_MEDIUM,
            "close": CRITICALITY_MEDIUM,
            "run": CRITICALITY_MEDIUM,
            "execute": CRITICALITY_MEDIUM,
            
            # Low criticality commands (informational)
            "tell": CRITICALITY_LOW,
            "show": CRITICALITY_LOW,
            "display": CRITICALITY_LOW,
            "list": CRITICALITY_LOW,
            "find": CRITICALITY_LOW,
            "search": CRITICALITY_LOW,
            "get": CRITICALITY_LOW,
            "calculate": CRITICALITY_LOW,
            "what": CRITICALITY_LOW,
            "when": CRITICALITY_LOW,
            "where": CRITICALITY_LOW,
            "who": CRITICALITY_LOW,
            "why": CRITICALITY_LOW,
            "how": CRITICALITY_LOW,
        }
        
        # Tagalog command criticality
        self.tagalog_command_criticality = {
            # High criticality
            "burahin": CRITICALITY_HIGH,
            "alisin": CRITICALITY_HIGH,
            "tanggalin": CRITICALITY_HIGH,
            "i-delete": CRITICALITY_HIGH,
            
            # Medium criticality
            "i-install": CRITICALITY_MEDIUM,
            "i-update": CRITICALITY_MEDIUM,
            "baguhin": CRITICALITY_MEDIUM,
            "palitan": CRITICALITY_MEDIUM,
            "i-edit": CRITICALITY_MEDIUM,
            "i-rename": CRITICALITY_MEDIUM,
            "ilipat": CRITICALITY_MEDIUM,
            "kopyahin": CRITICALITY_MEDIUM,
            "i-download": CRITICALITY_MEDIUM,
            "i-upload": CRITICALITY_MEDIUM,
            "gumawa": CRITICALITY_MEDIUM,
            "lumikha": CRITICALITY_MEDIUM,
            "buksan": CRITICALITY_MEDIUM,
            "isara": CRITICALITY_MEDIUM,
            "patakbuhin": CRITICALITY_MEDIUM,
            "i-execute": CRITICALITY_MEDIUM,
            
            # Low criticality
            "sabihin": CRITICALITY_LOW,
            "ipakita": CRITICALITY_LOW,
            "hanapin": CRITICALITY_LOW,
            "maghanap": CRITICALITY_LOW,
            "ano": CRITICALITY_LOW,
            "kailan": CRITICALITY_LOW,
            "saan": CRITICALITY_LOW,
            "sino": CRITICALITY_LOW,
            "bakit": CRITICALITY_LOW,
            "paano": CRITICALITY_LOW,
        }
        
        # Confidence thresholds for confirmation
        self.confidence_thresholds = {
            CRITICALITY_LOW: 0.4,    # Lower threshold for low criticality
            CRITICALITY_MEDIUM: 0.6,  # Medium threshold for medium criticality
            CRITICALITY_HIGH: 0.8     # High threshold for high criticality
        }
        
        # Pending commands waiting for confirmation
        self.pending_commands = {}
        
        # Command expiration time (seconds)
        self.command_expiration = 60
    
    def determine_criticality(self, intent: str, entities: Dict[str, Any]) -> str:
        """Determine the criticality level of a command
        
        Args:
            intent: The intent of the command
            entities: Entities extracted from the command
            
        Returns:
            Criticality level (low, medium, high)
        """
        # First check if the intent itself has a criticality level
        if intent in self.command_criticality:
            return self.command_criticality[intent]
        
        # Check Tagalog commands
        if intent in self.tagalog_command_criticality:
            return self.tagalog_command_criticality[intent]
        
        # Check entity values for criticality
        for entity_type, entity_value in entities.items():
            if isinstance(entity_value, str):
                # Check if entity value contains critical words
                for word, criticality in self.command_criticality.items():
                    if word in entity_value.lower():
                        return criticality
                
                # Check Tagalog words
                for word, criticality in self.tagalog_command_criticality.items():
                    if word in entity_value.lower():
                        return criticality
        
        # Default to low criticality
        return CRITICALITY_LOW
    
    def needs_confirmation(self, intent: str, entities: Dict[str, Any], confidence: float) -> bool:
        """Check if a command needs confirmation based on criticality and confidence
        
        Args:
            intent: The intent of the command
            entities: Entities extracted from the command
            confidence: Confidence score for intent recognition (0.0 to 1.0)
            
        Returns:
            True if confirmation is needed, False otherwise
        """
        # Determine criticality
        criticality = self.determine_criticality(intent, entities)
        
        # Get confidence threshold for this criticality level
        threshold = self.confidence_thresholds.get(criticality, 0.5)
        
        # Need confirmation if confidence is below threshold
        if confidence < threshold:
            logger.info(f"Command needs confirmation: intent={intent}, criticality={criticality}, confidence={confidence}, threshold={threshold}")
            return True
        
        # Always confirm high criticality commands
        if criticality == CRITICALITY_HIGH:
            logger.info(f"High criticality command always needs confirmation: intent={intent}")
            return True
        
        return False
    
    def create_pending_command(self, intent: str, entities: Dict[str, Any], original_text: str) -> str:
        """Create a pending command waiting for confirmation
        
        Args:
            intent: The intent of the command
            entities: Entities extracted from the command
            original_text: Original text of the command
            
        Returns:
            Command ID for confirmation
        """
        command_id = str(uuid.uuid4())
        
        # Store command details
        self.pending_commands[command_id] = {
            "intent": intent,
            "entities": entities,
            "original_text": original_text,
            "timestamp": time.time(),
            "criticality": self.determine_criticality(intent, entities)
        }
        
        logger.info(f"Created pending command: {command_id}, intent={intent}")
        return command_id
    
    def get_confirmation_message(self, command_id: str) -> str:
        """Get confirmation message for a pending command
        
        Args:
            command_id: ID of pending command
            
        Returns:
            Confirmation message
        """
        if command_id not in self.pending_commands:
            return "I'm not sure what you want me to confirm."
        
        command = self.pending_commands[command_id]
        intent = command["intent"]
        criticality = command["criticality"]
        
        # Generate different messages based on criticality
        if criticality == CRITICALITY_HIGH:
            return f"This is a critical operation. Are you sure you want me to '{intent}' as requested? Please confirm."
        
        elif criticality == CRITICALITY_MEDIUM:
            return f"Just to confirm, you want me to '{intent}'. Is that correct?"
        
        else:
            return f"I'll {intent} for you. Is that what you wanted?"
    
    def confirm_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """Confirm a pending command
        
        Args:
            command_id: ID of pending command
            
        Returns:
            Command details if confirmed, None if not found or expired
        """
        if command_id not in self.pending_commands:
            logger.warning(f"Command not found for confirmation: {command_id}")
            return None
        
        command = self.pending_commands[command_id]
        
        # Check if command has expired
        if time.time() - command["timestamp"] > self.command_expiration:
            logger.warning(f"Command expired: {command_id}")
            del self.pending_commands[command_id]
            return None
        
        # Remove command from pending
        del self.pending_commands[command_id]
        
        logger.info(f"Command confirmed: {command_id}, intent={command['intent']}")
        return command
    
    def deny_command(self, command_id: str) -> bool:
        """Deny a pending command
        
        Args:
            command_id: ID of pending command
            
        Returns:
            True if command was found and denied, False otherwise
        """
        if command_id not in self.pending_commands:
            logger.warning(f"Command not found for denial: {command_id}")
            return False
        
        # Remove command from pending
        del self.pending_commands[command_id]
        
        logger.info(f"Command denied: {command_id}")
        return True
    
    def is_confirmation_response(self, text: str) -> bool:
        """Check if text is a confirmation response
        
        Args:
            text: Text to check
            
        Returns:
            True if text is a confirmation, False otherwise
        """
        text = text.lower()
        
        # Check for positive confirmation
        positive_patterns = [
            "yes", "yeah", "yep", "correct", "right", "sure", "ok", "okay", 
            "confirm", "confirmed", "do it", "proceed", "go ahead", "affirmative",
            "oo", "sige", "tama", "opo", "oho", "pwede", "pwede na"
        ]
        
        for pattern in positive_patterns:
            if pattern in text:
                return True
        
        return False
    
    def is_denial_response(self, text: str) -> bool:
        """Check if text is a denial response
        
        Args:
            text: Text to check
            
        Returns:
            True if text is a denial, False otherwise
        """
        text = text.lower()
        
        # Check for negative responses
        negative_patterns = [
            "no", "nope", "don't", "do not", "stop", "cancel", "negative",
            "wrong", "incorrect", "not right", "mistake", "hold on", "wait",
            "hindi", "ayaw", "huwag", "wag", "mali", "hindî"
        ]
        
        for pattern in negative_patterns:
            if pattern in text:
                return True
        
        return False
    
    def process_confirmation_response(self, text: str, command_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Process a confirmation response
        
        Args:
            text: Confirmation response text
            command_id: ID of pending command
            
        Returns:
            Tuple of (was_processed, command_details)
            - was_processed: True if response was processed as confirmation/denial
            - command_details: Command details if confirmed, None otherwise
        """
        # Check if text is a confirmation
        if self.is_confirmation_response(text):
            command = self.confirm_command(command_id)
            return (True, command)
        
        # Check if text is a denial
        if self.is_denial_response(text):
            self.deny_command(command_id)
            return (True, None)
        
        # Not a clear confirmation or denial
        return (False, None)
    
    def cleanup_expired_commands(self):
        """Remove expired pending commands"""
        current_time = time.time()
        expired_ids = []
        
        for command_id, command in self.pending_commands.items():
            if current_time - command["timestamp"] > self.command_expiration:
                expired_ids.append(command_id)
        
        for command_id in expired_ids:
            logger.info(f"Removing expired command: {command_id}")
            del self.pending_commands[command_id]

# Example usage
if __name__ == "__main__":
    confirmation = CommandConfirmation()
    
    # Test criticality determination
    test_intents = [
        ("delete", {"file": "important.txt"}),
        ("show", {"information": "weather"}),
        ("open", {"file": "document.pdf"}),
        ("burahin", {"file": "file.txt"}),
        ("ipakita", {"information": "weather"}),
    ]
    
    for intent, entities in test_intents:
        criticality = confirmation.determine_criticality(intent, entities)
        print(f"Intent: {intent}, Criticality: {criticality}")
        
        # Test confirmation needs
        needs_conf_low = confirmation.needs_confirmation(intent, entities, 0.3)
        needs_conf_med = confirmation.needs_confirmation(intent, entities, 0.6)
        needs_conf_high = confirmation.needs_confirmation(intent, entities, 0.9)
        
        print(f"  Needs confirmation (conf=0.3): {needs_conf_low}")
        print(f"  Needs confirmation (conf=0.6): {needs_conf_med}")
        print(f"  Needs confirmation (conf=0.9): {needs_conf_high}")
    
    # Test confirmation flow
    test_command = ("delete", {"file": "important.txt"}, "Delete the important.txt file")
    command_id = confirmation.create_pending_command(*test_command)
    
    conf_message = confirmation.get_confirmation_message(command_id)
    print(f"\nConfirmation message: {conf_message}")
    
    # Test confirmation responses
    test_responses = [
        "yes, go ahead",
        "no, don't do that",
        "what time is it?",  # Not a confirmation response
        "oo, sige na",
        "hindi, wag muna"
    ]
    
    for response in test_responses:
        print(f"\nResponse: {response}")
        was_processed, command = confirmation.process_confirmation_response(response, command_id)
        if was_processed:
            if command:
                print(f"Command confirmed: {command}")
            else:
                print("Command denied")
        else:
            print("Not a confirmation response")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
