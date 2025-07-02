from main_pc_code.src.core.base_agent import BaseAgent
"""
Feedback Handler Module
Provides visual and voice confirmation feedback for command execution
"""
import logging
import zmq
import pickle
import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from main_pc_code.utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

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
    """Handles visual and voice feedback for command execution"""
    
    def __init__(self, gui_port: int = 5578, voice_port: int = 5574, **kwargs):
        super().__init__(port=gui_port, name="FeedbackHandler")
        """Initialize the feedback handler
        
        Args:
            gui_port: ZMQ port for GUI feedback
            voice_port: ZMQ port for voice feedback
        """
        self.context = zmq.Context()
        
        # Socket for GUI feedback (visual)
        self.gui_socket = self.context.socket(zmq.PUB)
        try:
            self.gui_socket.bind(f"tcp://*:{gui_port}")
        except zmq.ZMQError as e:
            if e.errno == zmq.EADDRINUSE:
                gui_port = self.gui_socket.bind_to_random_port("tcp://*")
                logger.warning(f"Port {gui_port} in use. Bound GUI socket to random port {gui_port}")
            else:
                raise
        
        # Socket for voice feedback (already exists at port 5574)
        self.voice_socket = self.context.socket(zmq.PUB)
        try:
            self.voice_socket.connect(f"tcp://{_agent_args.get('host', '127.0.0.1')}:5574")
            logger.info(f"Connected to voice feedback socket on port 5574")
        except Exception as e:
            logger.warning(f"Could not connect to voice feedback socket: {e}")
        
        # Connection status
        self.gui_connected = True
        self.voice_connected = True
        
        # Cooldown times for reconnection attempts
        self.last_gui_reconnect = 0
        self.last_voice_reconnect = 0
        self.reconnect_cooldown = 5  # seconds
        
        # Start health check thread
        self.running = True
        self.health_thread = threading.Thread(target=self._check_connections, daemon=True)
        self.health_thread.start()
    
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
                logger.warning("Cannot send voice feedback: Voice socket not connected")
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
            self.gui_socket.close()
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
            self.voice_socket.close()
            self.voice_socket = self.context.socket(zmq.PUB)
            self.voice_socket.connect(f"tcp://{_agent_args.get('host', '127.0.0.1')}:5574")
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
            self.gui_socket.close()
            self.voice_socket.close()
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
