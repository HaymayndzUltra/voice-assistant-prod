#!/usr/bin/env python3
"""
Vision Capture Agent
-------------------
Captures screenshots from the primary display and provides them via ZMQ.

This agent runs on mainPC and serves as the first step in the vision pipeline,
capturing visual data that can be processed by the VisionProcessingAgent.
"""

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
from utils.config_parser import parse_agent_args
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

class VisionCaptureAgent:
    """Agent for capturing screenshots and providing them via ZMQ"""
    
    def __init__(self, port: int = VISION_CAPTURE_PORT):
        """Initialize the Vision Capture Agent"""
        self.port = port
        
        # Create ZMQ context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Create screenshot directory if it doesn't exist
        self.screenshot_dir = Path("data/screenshots")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the screen capture tool
        self.sct = mss.mss()
        
        # Flag to control the agent
        self.running = True
        
        logger.info(f"VisionCaptureAgent initialized and listening on port {self.port}")
    
    def start(self):
        """Start the Vision Capture Agent"""
        logger.info("Starting VisionCaptureAgent")
        
        try:
            self._handle_requests()
        except KeyboardInterrupt:
            logger.info("VisionCaptureAgent interrupted by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the Vision Capture Agent"""
        logger.info("Stopping VisionCaptureAgent")
        self.running = False
        self.socket.close()
        self.context.term()
        self.sct.close()
    
    def _handle_requests(self):
        """Handle incoming ZMQ requests"""
        while self.running:
            try:
                # Wait for a request
                request = self.socket.recv_json()
                logger.debug(f"Received request: {request}")
                
                # Process the request
                response = self._process_request(request)
                
                # Send the response
                self.socket.send_json(response)
                
            except zmq.ZMQError as e:
                logger.error(f"ZMQ error: {e}")
                # Try to send an error response
                try:
                    self.socket.send_json({"status": "error", "error": str(e)})
                except:
                    pass
            except Exception as e:
                logger.error(f"Error handling request: {e}")
                # Try to send an error response
                try:
                    self.socket.send_json({"status": "error", "error": str(e)})
                except:
                    pass
    
    def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
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
    agent = VisionCaptureAgent()
    agent.start() 