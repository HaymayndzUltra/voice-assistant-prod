#!/usr/bin/env python3
"""
Vision Capture Agent
-------------------
Captures screenshots from the primary display and provides them via ZMQ.

This agent runs on mainPC and serves as the first step in the vision pipeline,
capturing visual data that can be processed by the VisionProcessingAgent.
"""

import sys
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

# Add the project's main_pc_code directory to the Python path
MAIN_PC_CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR)

from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_parser import parse_agent_args

_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/vision_capture_agent.log")
    ]
)
logger = logging.getLogger("VisionCaptureAgent")

# Constants
VISION_CAPTURE_PORT = 5587
SCREENSHOT_QUALITY = 90  # JPEG quality (0-100)
MAX_IMAGE_SIZE = (1920, 1080)  # Maximum dimensions for screenshots

class VisionCaptureAgent(BaseAgent):
    """Agent for capturing screenshots and providing them via ZMQ"""

    def __init__(self, port: int = VISION_CAPTURE_PORT, **kwargs):
        """Initialize the Vision Capture Agent"""
        super().__init__(port=port, name="VisionCaptureAgent", **kwargs)

        # Create screenshot directory if it doesn't exist
        self.screenshot_dir = Path("data/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the screen capture tool
        self.sct = mss.mss()

        logger.info(f"VisionCaptureAgent initialized and listening on port {self.port}")

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

if __name__ == "__main__":
    # Create and start the Vision Capture Agent
    agent = VisionCaptureAgent(port=_agent_args.port if _agent_args.port else VISION_CAPTURE_PORT)
    agent.run() 