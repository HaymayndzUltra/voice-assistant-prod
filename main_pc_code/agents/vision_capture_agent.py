#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Vision Capture Agent
-------------------
Captures screenshots from the primary display and provides them via ZMQ.

This agent runs on mainPC and serves as the first step in the vision pipeline,
capturing visual data that can be processed by the VisionProcessingAgent.
"""

import sys
import json
import os
import io
import zmq
import time
import logging
import threading
import base64
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import mss
import mss.tools


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Add the project's main_pc_code directory to the Python path
MAIN_PC_CODE_DIR = os.path.abspath(PathManager.join_path("main_pc_code", "..")))
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR)

from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from main_pc_code.utils.env_loader import get_env
import psutil
from datetime import datetime

# Load configuration at module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging
logger = configure_logging(__name__),
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "vision_capture_agent.log")))
    ]
)
logger = logging.getLogger("VisionCaptureAgent")

# Constants
VISION_CAPTURE_PORT = 5587
SCREENSHOT_QUALITY = 90  # JPEG quality (0-100)
MAX_IMAGE_SIZE = (1920, 1080)  # Maximum dimensions for screenshots

class VisionCaptureAgent(BaseAgent):
    """Agent for capturing screenshots and providing them via ZMQ Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""

    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5711)) if port is None else port
        agent_name = config.get("name", "VisionCaptureAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        # Set running flag
        self.running = True

        # Create screenshot directory if it doesn't exist
        self.screenshot_dir = Path(PathManager.join_path("data", "screenshots"))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the screen capture tool
        self.sct = mss.mss()

        logger.info(f"VisionCaptureAgent initialized and listening on port {self.port}")

    

        self.error_bus_port = 7150

        self.error_bus_host = get_pc2_ip()

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
def run(self):
        """Start the Vision Capture Agent's main loop."""
        logger.info("Starting VisionCaptureAgent main loop.")
        super().run()  # This will handle requests via handle_request

    def cleanup(self):
        """Clean up resources before stopping."""
        logger.info("Stopping VisionCaptureAgent")
        if hasattr(self, 'sct'):
            self.sct.close()
        super().cleanup()

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request and return a response"""
        action = request.get("action", "")
        
        if action == "capture_screen":
            return self._capture_screen(request)
        elif action == "health_check":
            return {"status": "ok", "message": "VisionCaptureAgent is running"}
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _capture_screen(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a screenshot and return it as base64-encoded bytes"""
        try:
            # Capture the primary monitor
            monitor = self.sct.monitors[1]  # Monitor 1 is usually the primary display
            screenshot = self.sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            # Resize if needed
            if img.width > MAX_IMAGE_SIZE[0] or img.height > MAX_IMAGE_SIZE[1]:
                img.thumbnail(MAX_IMAGE_SIZE, Image.LANCZOS)
            
            # Save to memory buffer as JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=SCREENSHOT_QUALITY)
            image_bytes = buffer.getvalue()
            
            # Encode as base64 for JSON transmission
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Save to disk if requested
            save_to_disk = request.get("save_to_disk", False)
            if save_to_disk:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = self.screenshot_dir / f"screenshot_{timestamp}.jpg"
                img.save(filename, format="JPEG", quality=SCREENSHOT_QUALITY)
                logger.info(f"Screenshot saved to {filename}")
            
            # Return the image data
            return {
                "status": "ok",
                "image_base64": image_base64,
                "format": "jpeg",
                "width": img.width,
                "height": img.height,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return {"status": "error", "error": f"Failed to capture screenshot: {str(e)}"}

    def health_check(self):
        """Perform a health check and return status."""
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {
                    "screenshot_directory": str(self.screenshot_dir)
                }
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

    def _get_health_status(self):
        """Default health status implementation required by BaseAgent."""
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational" if self.running else "Agent is not running",
            "uptime_seconds": time.time() - self.start_time
        }
        return {"status": status, "details": details}

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting VisionCaptureAgent...")
        agent = VisionCaptureAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env
        logger.error(f"An unexpected error occurred in {agent.name if agent else 'VisionCaptureAgent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logger.info(f"Cleaning up {agent.name}...")
            agent.cleanup() 