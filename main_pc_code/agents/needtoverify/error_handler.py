from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum

class ErrorSeverity(BaseAgent)(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ErrorHandler(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ErrorHandler")
        self.logger = logging.getLogger("ErrorHandler")
        self.setup_logging()
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Initialize ZMQ context
        self.context = zmq.Context()
        
        # Setup error handling sockets
        self.setup_sockets()
        
        # Initialize error tracking
        self.error_history = []
        self.recovery_attempts = {}
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename='logs/error_handler.log'
        )
        
    def load_config(self, config_path: str) -> Dict:
        """Load error handling configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return self.get_default_config()
            
    def get_default_config(self) -> Dict:
        """Get default error handling configuration"""
        return {
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 5,
                "recovery_timeout": 30,
                "error_port": 5582,
                "recovery_port": 5583
            }
        }
        
    def setup_sockets(self):
        """Setup ZMQ sockets for error handling"""
        # Error socket
        self.error_socket = self.context.socket(zmq.PUB)
        self.error_socket.bind(f"tcp://*:{self.config['error_handling']['error_port']}")
        
        # Recovery socket
        self.recovery_socket = self.context.socket(zmq.PUB)
        self.recovery_socket.bind(f"tcp://*:{self.config['error_handling']['recovery_port']}")
        
    def handle_error(self, error_type: str, error_data: Dict, severity: ErrorSeverity):
        """Handle incoming error"""
        try:
            # Create error record
            error_record = {
                "type": error_type,
                "data": error_data,
                "severity": severity.name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to history
            self.error_history.append(error_record)
            
            # Log error
            self.logger.error(f"Error received: {error_record}")
            
            # Send error notification
            self.error_socket.send_json(error_record)
            
            # Attempt recovery if needed
            if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                self.attempt_recovery(error_type, error_data)
                
        except Exception as e:
            self.logger.error(f"Error in handle_error: {e}")
            
    def attempt_recovery(self, error_type: str, error_data: Dict):
        """Attempt to recover from error"""
        try:
            # Check if we've exceeded retry attempts
            if error_type in self.recovery_attempts:
                if self.recovery_attempts[error_type] >= self.config["error_handling"]["max_retries"]:
                    self.logger.error(f"Max retry attempts exceeded for error: {error_type}")
                    return
                    
            # Increment recovery attempts
            self.recovery_attempts[error_type] = self.recovery_attempts.get(error_type, 0) + 1
            
            # Create recovery record
            recovery_record = {
                "error_type": error_type,
                "error_data": error_data,
                "attempt": self.recovery_attempts[error_type],
                "timestamp": datetime.now().isoformat()
            }
            
            # Send recovery notification
            self.recovery_socket.send_json(recovery_record)
            
            # Log recovery attempt
            self.logger.info(f"Recovery attempt {self.recovery_attempts[error_type]} for error: {error_type}")
            
            # Wait before next attempt
            time.sleep(self.config["error_handling"]["retry_delay"])
            
        except Exception as e:
            self.logger.error(f"Error in attempt_recovery: {e}")
            
    def get_error_history(self, limit: int = 100) -> List[Dict]:
        """Get recent error history"""
        return self.error_history[-limit:]
        
    def clear_error_history(self):
        """Clear error history"""
        self.error_history = []
        self.recovery_attempts = {}
        
    def run(self):
        """Main error handling loop"""
        self.logger.info("Starting error handling system")
        
        while True:
            try:
                # Process any pending errors
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in error handling loop: {e}")
                time.sleep(5)  # Wait before retrying
                
if __name__ == "__main__":
    handler = ErrorHandler()
    handler.run() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
