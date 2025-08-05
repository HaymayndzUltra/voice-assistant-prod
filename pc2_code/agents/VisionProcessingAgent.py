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
import time
import logging
import base64
import io
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from PIL import Image


# ✅ MODERNIZED: Standardized path management using PathManager only
from common.utils.path_manager import PathManager

# Add project root to path using PathManager (standardized approach)
PROJECT_ROOT = PathManager.get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    

from common.core.base_agent import BaseAgent
from pc2_code.utils.config_loader import parse_agent_args
import psutil

# Standard imports for PC2 agents
# ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
# Removed: from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
# Now using: self.report_error() method from BaseAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(PathManager.get_project_root() / "logs" / str(PathManager.get_logs_dir() / "vision_processing_agent.log")))
    ]
)
logger = logging.getLogger("VisionProcessingAgent")

class VisionProcessingAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()

    """Agent for processing images and providing descriptions Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').

    """

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
        self.output_dir = Path(PathManager.get_project_root() / "data" / "vision_output"
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"VisionProcessingAgent initialized and listening on port {self.port}")
        # self.error_bus = setup_error_reporting(self) # This line is removed as per the edit hint

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request and return a response"""
        request_type = request.get("type", "")
        
        if request_type == "describe_image":
            return self._describe_image(request)
        elif request_type == "health_check":
            return self.health_check()
        else:
            return {"status": "error", "error": f"Unknown request type: {request_type}"}
    
        # PC2 Error Bus Integration (Phase 1.3)
        self.error_publisher = create_pc2_error_publisher("VisionProcessingAgent")
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
                image = Image.open(io.BytesIO(image_bytes)
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

    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None)
        }
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        logger.info("Starting VisionProcessingAgent...")
        agent = VisionProcessingAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        import traceback
        logger.error(f"Error in VisionProcessingAgent main: {e}", exc_info=True)
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            
            if hasattr(self, 'context') and self.context:
                self.context.term()
                
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
