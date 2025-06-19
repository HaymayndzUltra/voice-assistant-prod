"""
Window Detector Component for detecting active windows
"""

import time
import logging
from typing import Dict, Any
from dataclasses import dataclass
import win32gui
import win32process
import psutil

logger = logging.getLogger(__name__)

@dataclass
class WindowInfo:
    """Class for storing window information."""
    title: str
    process_name: str
    is_active: bool
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "process_name": self.process_name,
            "is_active": self.is_active,
            "timestamp": self.timestamp
        }

class WindowDetector:
    """Detector for active windows."""
    
    def __init__(self):
        """Initialize the window detector."""
        logger.info("Initializing Window Detector")
    
    def get_active_window_info(self) -> WindowInfo:
        """Get information about the currently active window.
        
        Returns:
            WindowInfo object with window details
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            
            return WindowInfo(
                title=win32gui.GetWindowText(hwnd),
                process_name=process.name(),
                is_active=True,
                timestamp=time.time()
            )
        except Exception as e:
            logger.error(f"Error getting window info: {e}")
            return WindowInfo(
                title="Unknown",
                process_name="Unknown",
                is_active=False,
                timestamp=time.time()
            ) 