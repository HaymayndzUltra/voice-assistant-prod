import zmq
import json
import os
import threading
import time
import logging
from pathlib import Path
from datetime import datetime
from common.core.base_agent import BaseAgent

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Setup logging
LOG_PATH = Path(os.path.dirname(__file__).parent / "logs" / str(PathManager.get_logs_dir() / "context_summarizer.log")
LOG_PATH.parent.mkdir(exist_ok=True)
SUMMARY_STORE_PATH = Path(os.path.dirname(__file__).parent / "data" / "context_summary_store.json"
SUMMARY_STORE_PATH.parent.mkdir(exist_ok=True)
ZMQ_CONTEXT_SUMMARIZER_PORT = 5610

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ContextSummarizer")

class ContextSummarizer:
    def __init__(self, zmq_port=ZMQ_CONTEXT_SUMMARIZER_PORT):

        super().__init__(*args, **kwargs)        """Initialize the Context Summarizer agent"""
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
                alt_ports = [7610, 7611, 7612, 7613, 7614]
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
        
        self.summaries = self.load_summaries()
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
        
        logger.info(f"[ContextSummarizer] Agent started on port {self.port}")
        logger.info(f"[ContextSummarizer] Summary store path: {SUMMARY_STORE_PATH}")

    def load_summaries(self):
        """Load context summaries from the store file"""
        try:
            if SUMMARY_STORE_PATH.exists():
                with open(SUMMARY_STORE_PATH, "r", encoding="utf-8") as f:
                    summaries = json.load(f)
                logger.info(f"Loaded {len(summaries)} context summaries from store")
                return summaries
            logger.info("No existing summary store found, starting with empty store")
            return {}
        except Exception as e:
            logger.error(f"Error loading summary store: {e}")
            return {}

    def save_summaries(self):
        """Save context summaries to the store file"""
        try:
            with open(SUMMARY_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.summaries, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.summaries)} context summaries to store")
            return True
        except Exception as e:
            logger.error(f"Error saving summary store: {e}")
            return False

    def get_status(self):
        """Get the current status of the Context Summarizer agent"""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                "status": "ok",
                "service": "context_summarizer",
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
                "total_summaries": len(self.summaries),
                "bind_address": f"tcp://0.0.0.0:{self.port}" if self.port else None
            }

    def handle_query(self, query):
        """Handle incoming queries"""
        try:
            action = query.get("action")
            summary_id = query.get("summary_id", "default")
            
            # Update request tracking
            with self.lock:
                self.request_count += 1
                self.last_request_time = time.time()
            
            if action == "health_check":
                self.health_check_count += 1
                return self.get_status()
            elif action == "update_summary":
                self.update_count += 1
                summary_data = query.get("summary_data")
                if not summary_data:
                    self.failed_updates += 1
                    return {"status": "error", "reason": "No summary data provided"}
                
                with self.lock:
                    self.summaries[summary_id] = summary_data
                    if self.save_summaries():
                        self.successful_updates += 1
                        logger.info(f"[ContextSummarizer] Updated summary for {summary_id}: {summary_data}")
                        return {"status": "ok"}
                    else:
                        self.failed_updates += 1
                        return {"status": "error", "reason": "Failed to save summary data"}
            elif action == "get_summary":
                self.get_count += 1
                with self.lock:
                    summary = self.summaries.get(summary_id, {})
                logger.info(f"[ContextSummarizer] Retrieved summary for {summary_id}")
                return {"status": "ok", "summary": summary}
            elif action == "delete_summary":
                self.delete_count += 1
                with self.lock:
                    if summary_id in self.summaries:
                        del self.summaries[summary_id]
                        if self.save_summaries():
                            logger.info(f"[ContextSummarizer] Deleted summary for {summary_id}")
                            return {"status": "ok"}
                        else:
                            return {"status": "error", "reason": "Failed to save summary store after deletion"}
                    else:
                        return {"status": "error", "reason": "Summary not found"}
            else:
                return {"status": "error", "reason": "Unknown action"}
        except Exception as e:
            logger.error(f"[ContextSummarizer] Error handling query: {e}")
            with self.lock:
                self.error_count += 1
            return {"status": "error", "reason": str(e)}

    def run(self):
        """Main service loop"""
        logger.info("[ContextSummarizer] Service loop started")
        while self.running:
            try:
                msg = self.socket.recv_string()
                query = json.loads(msg)
                resp = self.handle_query(query)
                self.socket.send_string(json.dumps(resp)
            except Exception as e:
                logger.error(f"[ContextSummarizer] Error in service loop: {e}")
                with self.lock:
                    self.error_count += 1
                self.socket.send_string(json.dumps({"status": "error", "reason": str(e)})

    def stop(self):
        """Stop the Context Summarizer agent"""
        logger.info("[ContextSummarizer] Stopping agent...")
        self.running = False
        self.socket.close()
        self.context.term()
        logger.info("[ContextSummarizer] Agent stopped")

if __name__ == "__main__":
    agent = ContextSummarizer()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 