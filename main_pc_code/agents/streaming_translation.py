from main_pc_code.src.core.base_agent import BaseAgent
import threading
import logging
import time
import psutil
from datetime import datetime


# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

class FixedStreamingTranslation(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingTranslation")
        # ... existing code ...
        self._running = False
        self._thread = None

    def start(self):
        """Start the translation process."""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self.process_text_loop)
        self._thread.daemon = True
        self._thread.start()
        logging.info("Translation process started")

    def shutdown(self):
        """Shutdown the translation process."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.cleanup()
        logging.info("Translation process shutdown complete")

    def join(self, timeout=None):
        """Wait for the processing thread to complete."""
        if self._thread:
            self._thread.join(timeout=timeout)

    def cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'subscriber'):
                self.subscriber.close()
            if hasattr(self, 'publisher'):
                self.publisher.close()
            if hasattr(self, 'health_socket'):
                self.health_socket.close()
            if hasattr(self, 'context'):
                self.context.term()
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    # ... existing code ... 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise

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