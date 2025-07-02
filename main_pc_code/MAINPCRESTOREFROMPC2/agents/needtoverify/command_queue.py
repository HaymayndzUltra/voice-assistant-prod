from main_pc_code.src.core.base_agent import BaseAgent
"""
Command Queue Module
Implements a priority queue for voice commands
"""
import heapq
import time
import threading
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger("CommandQueue")

# Priority levels - lower number = higher priority
PRIORITY_CRITICAL = 0
PRIORITY_HIGH = 1
PRIORITY_NORMAL = 2
PRIORITY_LOW = 3
PRIORITY_BACKGROUND = 4

class CommandQueue(BaseAgent):
    """A priority queue implementation for handling commands with different priority levels"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CommandQueue")
        """Initialize the command queue with thread safety"""
        self.queue = []  # Priority queue (heap)
        self._queue_lock = threading.Lock()
        self.command_history = []  # History of executed commands
        self.max_history = 100  # Maximum number of commands to keep in history
        self.processing = False  # Flag to indicate if a command is being processed
        self._processor_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "commands_processed": 0,
            "commands_by_priority": {
                PRIORITY_CRITICAL: 0,
                PRIORITY_HIGH: 0,
                PRIORITY_NORMAL: 0,
                PRIORITY_LOW: 0,
                PRIORITY_BACKGROUND: 0
            },
            "avg_processing_time": 0,
            "avg_wait_time": 0
        }
    
    def add_command(self, command: Dict[str, Any], priority: int = PRIORITY_NORMAL) -> str:
        """
        Add a command to the queue with a specified priority
        
        Args:
            command: Dictionary containing command details
            priority: Priority level (0-4, lower = higher priority)
            
        Returns:
            Command ID
        """
        # Generate unique ID for the command
        command_id = str(uuid.uuid4())
        
        # Add metadata to the command
        command.update({
            "id": command_id,
            "priority": priority,
            "timestamp": time.time(),
            "status": "queued"
        })
        
        # Add to queue with priority sorting
        with self._queue_lock:
            # Store as (priority, timestamp, command) to ensure FIFO ordering within same priority
            heapq.heappush(self.queue, (priority, command["timestamp"], command))
            
        logger.info(f"Added command to queue: {command.get('intent', 'unknown')} (Priority: {priority})")
        return command_id
    
    def get_next_command(self) -> Optional[Dict[str, Any]]:
        """
        Get the next command from the queue based on priority
        
        Returns:
            Next command dictionary or None if queue is empty
        """
        with self._queue_lock:
            if not self.queue:
                return None
            
            # Pop the highest priority command
            _, _, command = heapq.heappop(self.queue)
            command["status"] = "processing"
            return command
    
    def mark_complete(self, command_id: str, result: str = "success", response: str = "") -> None:
        """
        Mark a command as complete and move it to history
        
        Args:
            command_id: The ID of the command to mark
            result: The result status (success, failed, etc.)
            response: The response text from command execution
        """
        command = self._find_command_by_id(command_id)
        if command:
            # Update command metadata
            command["status"] = "completed"
            command["result"] = result
            command["response"] = response
            command["completion_time"] = time.time()
            command["processing_time"] = command["completion_time"] - command["timestamp"]
            
            # Add to history
            self.command_history.append(command)
            
            # Trim history if needed
            if len(self.command_history) > self.max_history:
                self.command_history = self.command_history[-self.max_history:]
                
            # Update statistics
            self.stats["commands_processed"] += 1
            self.stats["commands_by_priority"][command["priority"]] += 1
            
            # Update average processing time
            if self.stats["commands_processed"] > 1:
                self.stats["avg_processing_time"] = (
                    (self.stats["avg_processing_time"] * (self.stats["commands_processed"] - 1) + 
                     command["processing_time"]) / self.stats["commands_processed"]
                )
                
            logger.info(f"Command {command_id} completed with result: {result}")
    
    def cancel_command(self, command_id: str) -> bool:
        """
        Cancel a command in the queue
        
        Args:
            command_id: The ID of the command to cancel
            
        Returns:
            True if command was found and canceled, False otherwise
        """
        with self._queue_lock:
            # Find the command
            found = False
            for i, (priority, timestamp, cmd) in enumerate(self.queue):
                if cmd["id"] == command_id:
                    found = True
                    cmd["status"] = "canceled"
                    self.command_history.append(cmd)
                    break
            
            if found:
                # Rebuild the queue without the canceled command
                self.queue = [(p, t, c) for p, t, c in self.queue if c["id"] != command_id]
                heapq.heapify(self.queue)
                logger.info(f"Command {command_id} canceled")
                return True
            
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the command queue
        
        Returns:
            Dictionary with queue status information
        """
        with self._queue_lock:
            queue_length = len(self.queue)
            # Count commands by priority
            priority_counts = {}
            for priority, _, _ in self.queue:
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
                
            return {
                "queue_length": queue_length,
                "priority_counts": priority_counts,
                "processing": self.processing,
                "commands_processed": self.stats["commands_processed"],
                "avg_processing_time": self.stats["avg_processing_time"]
            }
    
    def clear_queue(self) -> int:
        """
        Clear all commands from the queue
        
        Returns:
            Number of commands cleared
        """
        with self._queue_lock:
            count = len(self.queue)
            self.queue = []
            logger.info(f"Command queue cleared, removed {count} commands")
            return count
    
    def _find_command_by_id(self, command_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a command by its ID (either in queue or history)
        
        Args:
            command_id: The ID of the command to find
            
        Returns:
            Command dictionary or None if not found
        """
        # Check queue first
        with self._queue_lock:
            for _, _, command in self.queue:
                if command["id"] == command_id:
                    return command
        
        # Check history
        for command in self.command_history:
            if command["id"] == command_id:
                return command
                
        return None
    
    def get_command_by_id(self, command_id: str) -> Optional[Dict[str, Any]]:
        """
        Public method to get a command by its ID
        
        Args:
            command_id: The ID of the command to get
            
        Returns:
            Command dictionary or None if not found
        """
        return self._find_command_by_id(command_id)

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
