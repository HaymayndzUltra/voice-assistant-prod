#!/usr/bin/env python3
"""
Vision Processing Agent
---------------------
Processes images received from VisionCaptureAgent and provides descriptions.

This agent runs on PC2 and serves as the second step in the vision pipeline,
processing visual data captured by the VisionCaptureAgent on mainPC.
"""

import sys
import os
import json
import time
import logging
import base64
import io
from datetime import datetime
from typing import Dict, Any, Optional
from PIL import Image

# Add the project's pc2_code directory to the Python path
PC2_CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PC2_CODE_DIR not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR)

from agents.agent_utils import BaseAgent
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/vision_processing_agent.log")
    ]
)
logger = logging.getLogger("VisionProcessingAgent")

class VisionProcessingAgent(BaseAgent):
    """Agent for processing images and providing descriptions"""

    def __init__(self, **kwargs):
        """Initialize the Vision Processing Agent."""
        # Get configuration values with fallbacks
        port = kwargs.get('port', 7150)
        name = kwargs.get('name', "VisionProcessingAgent")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=name, port=port, **kwargs)
        
        # Store important attributes
        self.start_time = time.time()
        self.running = True
        
        # Create output directory if it doesn't exist
        self.output_dir = os.path.join(PC2_CODE_DIR, "data", "vision_output")
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"VisionProcessingAgent initialized and listening on port {self.port}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request and return a response"""
        request_type = request.get("type", "")
        
        if request_type == "describe_image":
            return self._describe_image(request)
        elif request_type == "health_check":
            return self.health_check()
        else:
            return {"status": "error", "error": f"Unknown request type: {request_type}"}
    
    def _describe_image(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an image and return a description"""
        try:
            # Extract image data and prompt
            image_base64 = request.get("image_base64", "")
            prompt = request.get("prompt", "Describe what you see in this image.")
            
            if not image_base64:
                return {"status": "error", "error": "No image data provided"}
            
            # Decode the base64 image
            try:
                image_bytes = base64.b64decode(image_base64)
                image = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                logger.error(f"Error decoding image: {e}")
                return {"status": "error", "error": f"Failed to decode image: {str(e)}"}
            
            # Save the image for debugging if needed
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            image_path = os.path.join(self.output_dir, f"received_image_{timestamp}.jpg")
            image.save(image_path)
            
            # Generate a simple description (in a real system, this would use a vision model)
            description = f"I can see a {image.width}x{image.height} image. "
            description += "This is a placeholder description from the VisionProcessingAgent. "
            description += f"In response to your prompt: '{prompt}', "
            description += "I would normally analyze the image using a vision model, but this is a simplified implementation."
            
            logger.info(f"Generated description for image: {description[:100]}...")
            
            return {
                "status": "ok",
                "description": description,
                "image_size": f"{image.width}x{image.height}",
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error describing image: {e}")
            return {"status": "error", "error": f"Failed to describe image: {str(e)}"}

    def health_check(self):
        """Perform a health check and return status."""
        try:
            # Basic health check logic
            is_healthy = True
            
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
                    "output_directory": self.output_dir
                }
            }
            return status_report
        except Exception as e:
            return {
                "status": "unhealthy",
                "agent_name": self.name,
                "error": f"Health check failed with exception: {str(e)}"
            }

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting VisionProcessingAgent...")
        agent = VisionProcessingAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        logger.error(f"An unexpected error occurred in {agent.name if agent else 'VisionProcessingAgent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logger.info(f"Cleaning up {agent.name}...")
            agent.cleanup() 