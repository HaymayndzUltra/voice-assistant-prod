from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Feedback Handler Module
Provides visual and voice confirmation feedback for command execution
"""
import logging
from main_pc_code.agents.error_publisher import ErrorPublisher
import os
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import pickle
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from main_pc_code.utils.config_loader import load_config
import psutil
from common.env_helpers import get_env

# Load config at module level
config = load_config()

logger = logging.getLogger("FeedbackHandler")

# Visual feedback styles
FEEDBACK_STYLES = {
    "success": {
        "color": "#4CAF50",  # Green
        "icon": "check_circle",
        "duration": 3000  # ms
    },
    "warning": {
        "color": "#FF9800",  # Orange
        "icon": "warning",
        "duration": 4000  # ms
    },
    "error": {
        "color": "#F44336",  # Red
        "icon": "error",
        "duration": 5000  # ms
    },
    "info": {
        "color": "#2196F3",  # Blue
        "icon": "info",
        "duration": 3000  # ms
    },
    "processing": {
        "color": "#9C27B0",  # Purple
        "icon": "hourglass_empty",
        "duration": 0  # Stays until updated or cleared
    }
}

class FeedbackHandler(BaseAgent):
    """Handles visual and voice feedback for command execution Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def __init__(self):
        self.port = config.get("port", 5578)
        self.start_time = time.time()
        self.name = "FeedbackHandler"
        self.running = True
        # Initialise error publisher early
        self.error_publisher = ErrorPublisher(self.name)
        self.feedback_received_count = 0
        self.last_feedback_time = None
        super().__init__(name=self.name, port=self.port)
        self.context = None  # Using pool
        
        # Socket for GUI feedback (visual)
        self.gui_socket = self.context.socket(zmq.PUB)
        try:
            self.gui_socket.bind(f"tcp://*:{self.port}")
        except zmq.ZMQError as e:
            if e.errno == zmq.EADDRINUSE:
                self.port = self.gui_socket.bind_to_random_port("tcp://*")
                logger.warning(f"Port {self.port} in use. Bound GUI socket to random port {self.port}")
            else:
                raise
        
        # Socket for voice feedback (already exists at port 5574)
        self.voice_socket = self.context.socket(zmq.PUB)
        try:
            self.voice_socket.connect(f"tcp://{config.get('host', '127.0.0.1')}:5574")
            logger.info(f"Connected to voice feedback socket on port 5574")
        except Exception as e:
            logger.warning(f"Could not connect to voice feedback socket: {e}")
            self.error_publisher.publish_error(error_type="socket_connection", severity="medium", details=str(e))
        
        # Connection status
        self.gui_connected = True
        self.voice_connected = True
        
        # Cooldown times for reconnection attempts
        self.last_gui_reconnect = 0
        self.last_voice_reconnect = 0
        self.reconnect_cooldown = 5  # seconds
        
        # Initialise error publisher
        # Start health check thread
        self.health_thread = threading.Thread(target=self._check_connections, daemon=True)
        self.health_thread.start()
        if not hasattr(self, "_background_threads"):
            self._background_threads = []
        self._background_threads.append(self.health_thread)
    
    

        self.error_bus_port = 7150

        self.error_bus_host = get_service_ip("pc2")

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        # Deprecated direct PUB socket removed – handled by ErrorPublisher

        
    def send_visual_feedback(self, message: str, status: str = "success", 
                            data: Dict[str, Any] = None, timeout: int = None) -> bool:
        """Send visual feedback to the GUI
        
        Args:
            message: Message to display
            status: Status type (success, warning, error, info, processing)
            data: Additional data to include
            timeout: Custom timeout in ms (overrides default for status)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.gui_connected:
            self._try_reconnect_gui()
            if not self.gui_connected:
                logger.warning("Cannot send visual feedback: GUI socket not connected")
                self.error_publisher.publish_error(error_type="gui_socket", severity="low", details="GUI not connected")
                return False
        
        # Get style information
        style = FEEDBACK_STYLES.get(status, FEEDBACK_STYLES["info"])
        
        # Create feedback data
        feedback = {
            "type": "visual_feedback",
            "message": message,
            "status": status,
            "style": style,
            "timestamp": time.time(),
            "data": data or {}
        }
        
        # Override duration if specified
        if timeout is not None:
            feedback["style"]["duration"] = timeout
            
        try:
            # Send feedback to GUI
            self.gui_socket.send(pickle.dumps(feedback))
            logger.debug(f"Sent visual feedback: {message} ({status})")
            return True
        except Exception as e:
            logger.error(f"Error sending visual feedback: {e}")
            self.gui_connected = False
            return False
    
    def send_voice_feedback(self, message: str, priority: bool = False) -> bool:
        """Send voice feedback for TTS
        
        Args:
            message: Message to speak
            priority: Whether this is a priority message (interrupts others)
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.voice_connected:
            self._try_reconnect_voice()
            if not self.voice_connected:
                logger.warning("Cannot send voice feedback: voice socket not connected")
                self.error_publisher.publish_error(error_type="voice_socket", severity="low", details="Voice socket not connected")
                return False
        
        # Create feedback data
        feedback = {
            "type": "response",
            "response": message,
            "priority": priority,
            "timestamp": time.time()
        }
        
        try:
            # Send feedback to voice system
            self.voice_socket.send(pickle.dumps(feedback))
            logger.debug(f"Sent voice feedback: {message}")
            return True
        except Exception as e:
            logger.error(f"Error sending voice feedback: {e}")
            self.voice_connected = False
            return False
    
    def send_combined_feedback(self, message: str, visual_status: str = "success", 
                              voice_message: str = None, data: Dict[str, Any] = None,
                              priority: bool = False) -> Tuple[bool, bool]:
        """Send both visual and voice feedback
        
        Args:
            message: Visual message to display
            visual_status: Status for visual feedback
            voice_message: Optional different message for voice (uses message if None)
            data: Additional data to include in visual feedback
            priority: Whether this is a priority voice message
            
        Returns:
            Tuple of (visual_success, voice_success)
        """
        # Send visual feedback
        visual_success = self.send_visual_feedback(message, visual_status, data)
        
        # Send voice feedback (use visual message if no specific voice message)
        voice_message = voice_message or message
        voice_success = self.send_voice_feedback(voice_message, priority)
        
        return visual_success, voice_success
    
    def send_command_feedback(self, command: str, status: str, result_message: str,
                             include_voice: bool = True) -> Tuple[bool, bool]:
        """Send feedback for a command execution
        
        Args:
            command: The command that was executed
            status: Status of execution (success, error, warning)
            result_message: Message describing the result
            include_voice: Whether to include voice feedback
            
        Returns:
            Tuple of (visual_success, voice_success)
        """
        # Different messages for different statuses
        if status == "success":
            visual_msg = f"Command executed: {command}"
            voice_msg = result_message
        elif status == "error":
            visual_msg = f"Error executing: {command}"
            voice_msg = f"I couldn't execute that command. {result_message}"
        elif status == "warning":
            visual_msg = f"Warning: {command}"
            voice_msg = f"Command executed with warning. {result_message}"
        else:
            visual_msg = f"Command: {command}"
            voice_msg = result_message
        
        # Send visual feedback
        visual_success = self.send_visual_feedback(
            visual_msg, 
            status,
            {
                "command": command,
                "result": result_message
            }
        )
        
        # Send voice feedback if requested
        voice_success = False
        if include_voice:
            voice_success = self.send_voice_feedback(voice_msg)
            
        return visual_success, voice_success
    
    def show_processing(self, command: str) -> bool:
        """Show that a command is being processed
        
        Args:
            command: The command being processed
            
        Returns:
            True if sent successfully, False otherwise
        """
        return self.send_visual_feedback(
            f"Processing: {command}",
            "processing",
            {"command": command}
        )
    
    def clear_processing(self) -> bool:
        """Clear the processing indicator
        
        Returns:
            True if sent successfully, False otherwise
        """
        return self.send_visual_feedback(
            "",
            "info",
            {"clear_processing": True},
            timeout=100  # Very short timeout
        )
    
    def _try_reconnect_gui(self) -> None:
        """Try to reconnect to the GUI socket"""
        current_time = time.time()
        if current_time - self.last_gui_reconnect < self.reconnect_cooldown:
            return
            
        self.last_gui_reconnect = current_time
        try:
            # Close and recreate socket
            self.gui_
            self.gui_socket = self.context.socket(zmq.PUB)
            self.gui_socket.bind(f"tcp://*:5578")
            self.gui_connected = True
            logger.info("Reconnected to GUI feedback socket")
        except Exception as e:
            logger.error(f"Failed to reconnect to GUI socket: {e}")
            self.gui_connected = False
    
    def _try_reconnect_voice(self) -> None:
        """Try to reconnect to the voice socket"""
        current_time = time.time()
        if current_time - self.last_voice_reconnect < self.reconnect_cooldown:
            return
            
        self.last_voice_reconnect = current_time
        try:
            # Close and recreate socket
            self.voice_
            self.voice_socket = self.context.socket(zmq.PUB)
            self.voice_socket.connect(f"tcp://{config.get('host', '127.0.0.1')}:5574")
            self.voice_connected = True
            logger.info("Reconnected to voice feedback socket")
        except Exception as e:
            logger.error(f"Failed to reconnect to voice socket: {e}")
            self.voice_connected = False
    
    def _check_connections(self) -> None:
        """Periodically check and maintain connections"""
        while self.running:
            try:
                if not self.gui_connected:
                    self._try_reconnect_gui()
                    
                if not self.voice_connected:
                    self._try_reconnect_voice()
                    
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in connection check: {e}")
                time.sleep(30)  # Longer delay on error
    
    def shutdown(self) -> None:
        """Shutdown the feedback handler"""
        self.running = False
        time.sleep(0.2)  # Give thread time to exit
        
        try:
            self.gui_
            self.voice_
            logger.info("Feedback handler shutdown complete")
        except Exception as e:
            logger.error(f"Error during feedback handler shutdown: {e}")
    
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "handler_status": "active",
            "feedback_received_count": getattr(self, 'feedback_received_count', 0),
            "last_feedback_time": getattr(self, 'last_feedback_time', 'N/A')
        }
        base_status.update(specific_metrics)
        return base_status

    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = FeedbackHandler()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
            if hasattr(self, 'context') and self.context:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
