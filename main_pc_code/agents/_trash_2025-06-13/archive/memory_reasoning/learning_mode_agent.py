from main_pc_code.src.core.base_agent import BaseAgent
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging
sys.path.append(str(Path(__file__).parent.parent))
import zmq
import json
import os
from main_pc_code.agents.proactive_agent_interface import send_proactive_event

import threading
import time
import logging
import psutil
from datetime import datetime

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = str(PathManager.get_logs_dir() / "learning_mode_agent.log")
LEARNING_MODE_STORE_PATH = "learning_mode_store.json"
ZMQ_LEARNING_MODE_PORT = 5598  # Changed from 5599 to avoid conflict with health monitoring

logger = configure_logging(__name__):
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
    agent = LearningModeAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise