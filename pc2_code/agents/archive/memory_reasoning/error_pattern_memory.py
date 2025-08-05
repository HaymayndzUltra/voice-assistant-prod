#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# Error Pattern Memory - For tracking, learning, and suggesting fixes for common errors
# Maintains a database of encountered errors and their successful fixes
# Enables more intelligent auto-fix workflows

import zmq
import json
import os
import threading
import time
import logging
import re
import hashlib
from pathlib import Path
from datetime import datetime
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Setup logging
LOG_PATH = Path(os.path.dirname(__file__).parent / "logs" / str(PathManager.get_logs_dir() / "error_pattern_memory.log")
LOG_PATH.parent.mkdir(exist_ok=True)
ERROR_STORE_PATH = Path(os.path.dirname(__file__).parent / "data" / "error_pattern_store.json"
ERROR_STORE_PATH.parent.mkdir(exist_ok=True)
ZMQ_ERROR_PATTERN_PORT = 5611  # Port for error pattern memory agent
MODEL_MANAGER_HOST = "192.168.1.27"  # Main PC's IP address
MODEL_MANAGER_PORT = 5556  # Main PC's MMA port

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ErrorPatternMemory")

class ErrorPatternMemory:
    def __init__(self, zmq_port=ZMQ_ERROR_PATTERN_PORT):
        """Initialize the Error Pattern Memory Agent"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Try to bind to the specified port
        try:
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
            self.port = zmq_port
            logger.info(f"Successfully bound to port {zmq_port}")
        except zmq.error.ZMQError as e:
            # If port is in use, try alternative ports
            if "Address in use" in str(e):
                logger.warning(f"Port {zmq_port} is in use, trying alternative ports")
                # Try a range of alternative ports
                alt_ports = [7611, 7612, 7613, 7614, 7615]
                for alt_port in alt_ports:
                    try:
                        self.socket.bind(f"tcp://0.0.0.0:{alt_port}")
                        self.port = alt_port
                        logger.info(f"Successfully bound to alternative port {alt_port}")
                        break
                    except zmq.error.ZMQError:
                        continue
                else:
                    # If we get here, all ports failed
                    logger.error("Could not bind to any port. Will keep running but won't process requests.")
                    self.port = None
            else:
                # Some other ZMQ error
                logger.error(f"Error binding to port: {e}")
                self.port = None
        
        self.patterns = self.load_patterns()
        self.lock = threading.Lock()
        self.running = True
        
        # Agent state
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        self.health_check_count = 0
        self.update_count = 0
        self.get_count = 0
        self.delete_count = 0
        self.successful_updates = 0
        self.failed_updates = 0
        
        logger.info(f"[ErrorPatternMemory] Agent started on port {self.port}")
        logger.info(f"[ErrorPatternMemory] Pattern store path: {ERROR_STORE_PATH}")

    def load_patterns(self):
        """Load error patterns from the store file"""
        try:
            if ERROR_STORE_PATH.exists():
                with open(ERROR_STORE_PATH, "r", encoding="utf-8") as f:
                    patterns = json.load(f)
                logger.info(f"Loaded {len(patterns)} error patterns from store")
                return patterns
            logger.info("No existing pattern store found, starting with empty store")
            return {}
        except Exception as e:
            logger.error(f"Error loading pattern store: {e}")
            return {}

    def save_patterns(self):
        """Save error patterns to the store file"""
        try:
            with open(ERROR_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.patterns, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.patterns)} error patterns to store")
                return True
        except Exception as e:
            logger.error(f"Error saving pattern store: {e}")
            return False
    
    def get_status(self):
        """Get the current status of the Error Pattern Memory agent"""
        with self.lock:
            uptime = time.time() - self.start_time
                return {
                "status": "ok",
                "service": "error_pattern_memory",
                "timestamp": time.time(),
                "uptime_seconds": uptime,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "last_request_time": self.last_request_time,
                "health_check_count": self.health_check_count,
                "update_count": self.update_count,
                "get_count": self.get_count,
                "delete_count": self.delete_count,
                "successful_updates": self.successful_updates,
                "failed_updates": self.failed_updates,
                "total_patterns": len(self.patterns),
                "bind_address": f"tcp://0.0.0.0:{self.port}" if self.port else None
            }
    
    def handle_query(self, query):
        """Handle incoming queries"""
        try:
        action = query.get("action")
            pattern_id = query.get("pattern_id", "default")
            
            # Update request tracking
            with self.lock:
                self.request_count += 1
                self.last_request_time = time.time()
            
            if action == "health_check":
                self.health_check_count += 1
                return self.get_status()
            elif action == "update_pattern":
                self.update_count += 1
                pattern_data = query.get("pattern_data")
                if not pattern_data:
                    self.failed_updates += 1
                    return {"status": "error", "reason": "No pattern data provided"}
                
                with self.lock:
                    self.patterns[pattern_id] = pattern_data
                    if self.save_patterns():
                        self.successful_updates += 1
                        logger.info(f"[ErrorPatternMemory] Updated pattern for {pattern_id}: {pattern_data}")
                        return {"status": "ok"}
            else:
                        self.failed_updates += 1
                        return {"status": "error", "reason": "Failed to save pattern data"}
            elif action == "get_pattern":
                self.get_count += 1
                with self.lock:
                    pattern = self.patterns.get(pattern_id, {})
                logger.info(f"[ErrorPatternMemory] Retrieved pattern for {pattern_id}")
                return {"status": "ok", "pattern": pattern}
            elif action == "delete_pattern":
                self.delete_count += 1
                with self.lock:
                    if pattern_id in self.patterns:
                        del self.patterns[pattern_id]
                        if self.save_patterns():
                            logger.info(f"[ErrorPatternMemory] Deleted pattern for {pattern_id}")
                            return {"status": "ok"}
            else:
                            return {"status": "error", "reason": "Failed to save pattern store after deletion"}
        else:
                        return {"status": "error", "reason": "Pattern not found"}
        except Exception as e:
            logger.error(f"[ErrorPatternMemory] Error handling query: {e}")
            with self.lock:
                self.error_count += 1
            return {"status": "error", "reason": str(e)}
    
    def run(self):
        """Main service loop"""
        logger.info("[ErrorPatternMemory] Service loop started")
        while self.running:
            try:
                msg = self.socket.recv_string()
                query = json.loads(msg)
                resp = self.handle_query(query)
                self.socket.send_string(json.dumps(resp)
            except Exception as e:
                logger.error(f"[ErrorPatternMemory] Error in service loop: {e}")
                with self.lock:
                    self.error_count += 1
                self.socket.send_string(json.dumps({"status": "error", "reason": str(e)})
    
    def stop(self):
        """Stop the Error Pattern Memory agent"""
        logger.info("[ErrorPatternMemory] Stopping agent...")
        self.running = False
        self.socket.close()
        self.context.term()
        logger.info("[ErrorPatternMemory] Agent stopped")

# Helper function to send requests to the agent
def send_error_pattern_request(request, port=ZMQ_ERROR_PATTERN_PORT):
    """
    Send a request to the Error Pattern Memory Agent
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://127.0.0.1:{port}")
    
    socket.send_string(json.dumps(request)
    response = socket.recv_string()
    
    socket.close()
    context.term()
    
    return json.loads(response)

# Helper functions for other agents to use
def record_error(error_text, code_context=None, language="python"):
    """
    Record an error occurrence
    Returns the error_id for later reference
    """
    request = {
        "action": "record_error",
        "error_text": error_text,
        "code_context": code_context,
        "language": language
    }
    response = send_error_pattern_request(request)
    return response.get("error_id") if response.get("status") == "ok" else None

def record_fix(error_id, fix_code, successful=True):
    """
    Record a fix for an error and whether it worked
    """
    request = {
        "action": "record_fix",
        "error_id": error_id,
        "fix_code": fix_code,
        "successful": successful
    }
    response = send_error_pattern_request(request)
    return response.get("status") == "ok"

def find_similar_errors(error_text, max_results=3):
    """
    Find errors similar to the given error text
    Returns a list of error_ids
    """
    request = {
        "action": "find_similar_errors",
        "error_text": error_text,
        "max_results": max_results
    }
    response = send_error_pattern_request(request)
    return response.get("similar_errors", []) if response.get("status") == "ok" else []

def get_best_fix(error_id):
    """
    Get the most successful fix for an error
    """
    request = {
        "action": "get_best_fix",
        "error_id": error_id
    }
    response = send_error_pattern_request(request)
    return response.get("fix_code") if response.get("status") == "ok" else None

def get_all_fixes(error_id, ranked=True):
    """
    Get all recorded fixes for an error
    """
    request = {
        "action": "get_all_fixes",
        "error_id": error_id,
        "ranked": ranked
    }
    response = send_error_pattern_request(request)
    return response.get("fixes", []) if response.get("status") == "ok" else []

def main():
    """
    Run the Error Pattern Memory Agent
    """
    agent = ErrorPatternMemory()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        logging.error(f"[ErrorPatternMemory] Fatal error: {str(e)}")
    finally:
        agent.stop()

if __name__ == "__main__":
    main()
