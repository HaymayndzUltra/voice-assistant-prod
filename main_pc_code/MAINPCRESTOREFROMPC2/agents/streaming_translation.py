from main_pc_code.src.core.base_agent import BaseAgent
import threading
import logging

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
