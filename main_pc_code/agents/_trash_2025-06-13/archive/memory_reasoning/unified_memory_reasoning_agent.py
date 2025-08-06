from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any
import time
import psutil
from datetime import datetime
from common.utils.log_setup import configure_logging

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedMemoryReasoningAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="UnifiedMemoryReasoningAgent")
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://0.0.0.0:{port}")
        
        # Memory storage
        self.short_term_memory: Dict[str, Any] = {}
        self.long_term_memory: Dict[str, Any] = {}
        self.context_memory: Dict[str, Any] = {}
        self.error_patterns: Dict[str, List[Dict]] = {}
        
        # Start processing thread
        self.running = True
        self.process_thread = threading.Thread(target=self._process_requests)
        self.process_thread.start()
        
        logger.info(f"UnifiedMemoryReasoningAgent initialized on port {port}")

    def _process_requests(self):
        while self.running:
            try:
                message = self.socket.recv_json()
                response = self._handle_request(message)
                self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                self.socket.send_json({"status": "error", "message": str(e)})

    def _handle_request(self, message: Dict) -> Dict:
        request_type = message.get("request_type", "")
        
        handlers = {
            "store_memory": self._store_memory,
            "retrieve_memory": self._retrieve_memory,
            "update_context": self._update_context,
            "get_context": self._get_context,
            "store_error_pattern": self._store_error_pattern,
            "get_error_patterns": self._get_error_patterns,
            "health_check": self._health_check
        }
        
        handler = handlers.get(request_type)
        if handler:
            return handler(message)
        return {"status": "error", "message": f"Unknown request type: {request_type}"}

    def _store_memory(self, message: Dict) -> Dict:
        memory_type = message.get("memory_type", "short_term")
        key = message.get("key")
        value = message.get("value")
        timestamp = datetime.now().isoformat()
        
        if memory_type == "long_term":
            self.long_term_memory[key] = {"value": value, "timestamp": timestamp}
        else:
            self.short_term_memory[key] = {"value": value, "timestamp": timestamp}
        
        return {"status": "success", "message": f"Memory stored in {memory_type}"}

    def _retrieve_memory(self, message: Dict) -> Dict:
        memory_type = message.get("memory_type", "short_term")
        key = message.get("key")
        
        if memory_type == "long_term":
            memory = self.long_term_memory.get(key)
        else:
            memory = self.short_term_memory.get(key)
        
        return {
            "status": "success" if memory else "not_found",
            "memory": memory
        }

    def _update_context(self, message: Dict) -> Dict:
        context_key = message.get("context_key")
        context_value = message.get("context_value")
        self.context_memory[context_key] = context_value
        return {"status": "success", "message": "Context updated"}

    def _get_context(self, message: Dict) -> Dict:
        context_key = message.get("context_key")
        context = self.context_memory.get(context_key)
        return {
            "status": "success" if context else "not_found",
            "context": context
        }

    def _store_error_pattern(self, message: Dict) -> Dict:
        pattern_type = message.get("pattern_type")
        pattern = message.get("pattern")
        if pattern_type not in self.error_patterns:
            self.error_patterns[pattern_type] = []
        self.error_patterns[pattern_type].append(pattern)
        return {"status": "success", "message": "Error pattern stored"}

    def _get_error_patterns(self, message: Dict) -> Dict:
        pattern_type = message.get("pattern_type")
        patterns = self.error_patterns.get(pattern_type, [])
        return {
            "status": "success",
            "patterns": patterns
        }

    def _health_check(self, message: Dict) -> Dict:
        return {
            "status": "healthy",
            "memory_stats": {
                "short_term": len(self.short_term_memory),
                "long_term": len(self.long_term_memory),
                "context": len(self.context_memory),
                "error_patterns": len(self.error_patterns)
            }
        }

    def shutdown(self):
        self.running = False
        self.process_thread.join()
        self.socket.close()
        self.context.term()
        logger.info("UnifiedMemoryReasoningAgent shutdown complete")


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

if __name__ == "__main__":
    agent = UnifiedMemoryReasoningAgent()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        agent.shutdown() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise