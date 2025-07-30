from common.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Memory Agent
- Manages short-term and long-term memory for the system
- Handles memory storage, retrieval, and cleanup
- Provides memory-based context for other agents
"""

import zmq
import json
import time
import logging
import threading
from pathlib import Path
import sys

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from pc2_code.config.system_config import config

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / str(PathManager.get_logs_dir() / "memory_agent.log")
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MemoryAgent")

class MemoryAgent(BaseAgent):
    def __init__(self, port=5590, bind_address="0.0.0.0"):

        super().__init__(*args, **kwargs)        """Initialize the Memory Agent"""
        self.port = port
        self.bind_address = bind_address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        try:
            self.socket.bind(f"tcp://{self.bind_address}:{self.port}")
            logger.info(f"Memory Agent bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Error binding to port {self.port}: {e}")
            raise RuntimeError(f"Cannot bind to port {self.port}")
        
        # Initialize memory stores
        self.short_term_memory = {}
        self.long_term_memory = {}
        self.memory_lock = threading.Lock()
        
        # Initialize state
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.health_check_count = 0
        
        logger.info("Memory Agent initialized")
    
    def get_status(self):
        """Get the current status of the Memory Agent"""
        uptime = time.time() - self.start_time
        return {
            "status": "ok",
            "service": "memory_agent",
            "timestamp": time.time(),
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "health_check_count": self.health_check_count,
            "short_term_memory_size": len(self.short_term_memory),
            "long_term_memory_size": len(self.long_term_memory),
            "bind_address": f"tcp://{self.bind_address}:{self.port}"
        }
    
    def handle_request(self, request):
        """Handle incoming memory requests"""
        try:
            action = request.get("action")
            
            if action == "health_check":
                self.health_check_count += 1
                return self.get_status()
            elif action == "store":
                self.total_requests += 1
                key = request.get("key")
                value = request.get("value")
                memory_type = request.get("memory_type", "short_term")
                
                if not key or value is None:
                    self.failed_requests += 1
                    return {"status": "error", "reason": "Missing key or value"}
                
                with self.memory_lock:
                    if memory_type == "long_term":
                        self.long_term_memory[key] = value
                    else:
                        self.short_term_memory[key] = value
                
                self.successful_requests += 1
                return {"status": "ok"}
            elif action == "retrieve":
                self.total_requests += 1
                key = request.get("key")
                memory_type = request.get("memory_type", "short_term")
                
                if not key:
                    self.failed_requests += 1
                    return {"status": "error", "reason": "Missing key"}
                
                with self.memory_lock:
                    if memory_type == "long_term":
                        value = self.long_term_memory.get(key)
                    else:
                        value = self.short_term_memory.get(key)
                
                if value is None:
                    self.failed_requests += 1
                    return {"status": "error", "reason": "Key not found"}
                
                self.successful_requests += 1
                return {"status": "ok", "value": value}
            elif action == "delete":
                self.total_requests += 1
                key = request.get("key")
                memory_type = request.get("memory_type", "short_term")
                
                if not key:
                    self.failed_requests += 1
                    return {"status": "error", "reason": "Missing key"}
                
                with self.memory_lock:
                    if memory_type == "long_term":
                        if key in self.long_term_memory:
                            del self.long_term_memory[key]
                            self.successful_requests += 1
                            return {"status": "ok"}
                    else:
                        if key in self.short_term_memory:
                            del self.short_term_memory[key]
                            self.successful_requests += 1
                            return {"status": "ok"}
                
                self.failed_requests += 1
                return {"status": "error", "reason": "Key not found"}
            else:
                return {"status": "error", "reason": f"Unknown action: {action}"}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.failed_requests += 1
            return {"status": "error", "reason": str(e)}
    
    def run(self):
        """Main service loop"""
        logger.info("Memory Agent service loop started")
        while True:
            try:
                msg = self.socket.recv_string()
                request = json.loads(msg)
                response = self.handle_request(request)
                self.socket.send_string(json.dumps(response))
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                self.socket.send_string(json.dumps({
                    "status": "error",
                    "reason": str(e)
                }))

def main():
    """Main entry point"""
    try:
        agent = MemoryAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down Memory Agent")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 