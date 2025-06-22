import sys
import os
# Ensure project root is on PYTHONPATH so 'src' can be imported when the agent
# is launched as a standalone subprocess.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
PROJECT_SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for _p in (PROJECT_SRC_ROOT, PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.core.base_agent import BaseAgent
except ImportError:
    # Fallback when running from project root already containing 'main_pc_code'
    from main_pc_code.src.core.base_agent import BaseAgent
"""
TTS Connector Module
Connects the modular system's text processor to the Bark TTS agent
"""
import zmq
import pickle
import json
import logging
import time
import sys
import threading
import queue
import psutil
from collections import deque, OrderedDict
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Logging setup
log_dir = os.path.join(os.path.dirname(__file__), '../../logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'tts_connector.log')
file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger("TTSConnector")
logger.setLevel(logging.INFO)
logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Constants
TEXT_PROCESSOR_PORT = 5564  # Port where language_and_translation_coordinator publishes
TTS_AGENT_PORT = 5562  # Port where streaming_tts_agent.py is listening (Ultimate TTS Agent)
HEALTH_CHECK_PORT = 5563  # New dedicated port for health checks
ZMQ_HEALTH_PORT = 5597  # Port for system health dashboard
MAX_QUEUE_SIZE = 1000
BATCH_SIZE = 5
BATCH_TIMEOUT = 0.1  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
CONNECTION_POOL_SIZE = 5
HEALTH_CHECK_INTERVAL = 5  # seconds
SYSTEM_LOAD_THRESHOLD = 80  # percentage

class ConnectionPool:
    """ZMQ connection pool for TTS agent"""
    def __init__(self, context: zmq.Context, address: str, pool_size: int, port: int = None, **kwargs):

        self.context = context
        self.address = address
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        
        # Initialize pool
        for _ in range(pool_size):
            socket = context.socket(zmq.REQ)
            socket.connect(address)
            self.pool.put(socket)
            
    def acquire(self, timeout: float = 5.0) -> Optional[zmq.Socket]:
        """Acquire a socket from the pool"""
        try:
            return self.pool.get(timeout=timeout)
        except queue.Empty:
            logger.warning("Connection pool exhausted")
            return None
            
    def release(self, socket: zmq.Socket):
        """Release a socket back to the pool"""
        try:
            self.pool.put(socket, block=False)
        except queue.Full:
            socket.close()
            
    def close(self):
        """Close all sockets in the pool"""
        while not self.pool.empty():
            try:
                socket = self.pool.get_nowait()
                socket.close()
            except queue.Empty:
                break

class RequestQueue:
    """Priority-based request queue with batching support"""
    def __init__(self, max_size: int = MAX_QUEUE_SIZE, port: int = None, **kwargs):

        self.high_priority = queue.PriorityQueue(maxsize=max_size)
        self.normal_priority = queue.PriorityQueue(maxsize=max_size)
        self.low_priority = queue.PriorityQueue(maxsize=max_size)
        self.lock = threading.Lock()
        
    def put(self, request: Dict, priority: int = 1):
        """Add request to appropriate queue based on priority"""
        with self.lock:
            if priority == 0:  # High priority
                self.high_priority.put(request)
            elif priority == 1:  # Normal priority
                self.normal_priority.put(request)
            else:  # Low priority
                self.low_priority.put(request)
                
    def get_batch(self, size: int = BATCH_SIZE, timeout: float = BATCH_TIMEOUT) -> List[Dict]:
        """Get a batch of requests, prioritizing higher priority queues"""
        batch = []
        start_time = time.time()
        
        while len(batch) < size and time.time() - start_time < timeout:
            try:
                # Try high priority first
                if not self.high_priority.empty():
                    batch.append(self.high_priority.get_nowait())
                    continue
                    
                # Then normal priority
                if not self.normal_priority.empty():
                    batch.append(self.normal_priority.get_nowait())
                    continue
                    
                # Finally low priority
                if not self.low_priority.empty():
                    batch.append(self.low_priority.get_nowait())
                    continue
                    
                # If all queues are empty, wait a bit
                time.sleep(0.01)
                
            except queue.Empty:
                break
                
        return batch

class TTSConnector(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        # If port not explicitly passed, fall back to command-line argument (if any)
        if port is None:
            port = getattr(_agent_args, 'port', None)
        super().__init__(port=port, name="TtsConnector", strict_port=True)


        host = getattr(_agent_args, 'host', 'localhost')
        
        # Initialize connection pool
        self.connection_pool = ConnectionPool(
            self.context,
            f"tcp://{host}:{TTS_AGENT_PORT}",
            CONNECTION_POOL_SIZE
        )
        
        # Socket to receive messages from text processor
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{host}:{TEXT_PROCESSOR_PORT}")
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"")
        logger.info(f"Connected to language and translation coordinator on port {TEXT_PROCESSOR_PORT}")
        
        # Setup health reporting
        self.health_socket = self.context.socket(zmq.PUB)
        try:
            self.health_socket.connect(f"tcp://{host}:{ZMQ_HEALTH_PORT}")
            logger.info(f"Connected to health dashboard on port {ZMQ_HEALTH_PORT}")
        except Exception as e:
            logger.warning(f"Could not connect to health dashboard: {e}")
            
        # Initialize request queue
        self.request_queue = RequestQueue()
        
        # BaseAgent already provides a dedicated REP health socket; we don't create another.
        self.health_rep_socket = None
        
        # Statistics tracking
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_count": 0,
            "voice_distribution": {
                "en_male": 0,
                "tl_male": 0,
                "other": 0
            },
            "response_lengths": deque(maxlen=50),
            "tts_latencies": deque(maxlen=20),
            "avg_latency": 0,
            "batch_processing_count": 0,
            "queue_sizes": deque(maxlen=100),
            "error_count": 0,
            "last_update": time.time()
        }
        
        self.running = True
        self.health_thread = None
        
    def report_health(self):
        """Report health metrics to the system health dashboard"""
        logger.info("Health reporting thread started")
        
        while self.running:
            try:
                # Calculate system load
                system_load = psutil.cpu_percent()
                
                # Adjust health check frequency based on system load
                check_interval = HEALTH_CHECK_INTERVAL
                if system_load > SYSTEM_LOAD_THRESHOLD:
                    check_interval *= 2  # Reduce frequency under high load
                
                # Calculate derived metrics
                current_time = time.time()
                total = self.stats["total_requests"]
                
                # Calculate success rate
                success_rate = (self.stats["successful_requests"] / total) * 100 if total > 0 else 0
                failure_rate = 100 - success_rate if total > 0 else 0
                
                # Calculate voice distribution
                voice_distribution = {}
                for voice, count in self.stats["voice_distribution"].items():
                    voice_distribution[voice] = (count / total) * 100 if total > 0 else 0
                
                # Calculate average response length
                avg_response_length = 0
                if self.stats["response_lengths"]:
                    avg_response_length = sum(self.stats["response_lengths"]) / len(self.stats["response_lengths"])
                
                # Calculate average latency
                if self.stats["tts_latencies"]:
                    self.stats["avg_latency"] = sum(self.stats["tts_latencies"]) / len(self.stats["tts_latencies"])
                
                # Calculate queue statistics
                avg_queue_size = 0
                if self.stats["queue_sizes"]:
                    avg_queue_size = sum(self.stats["queue_sizes"]) / len(self.stats["queue_sizes"])
                
                # Update last update timestamp
                self.stats["last_update"] = current_time
                
                # Determine overall status
                status = "healthy"
                if success_rate < 50 and total > 5:
                    status = "degraded"
                elif system_load > SYSTEM_LOAD_THRESHOLD:
                    status = "warning"
                
                # Create health data
                health_data = {
                    "component": "TTSConnector",
                    "status": status,
                    "timestamp": current_time,
                    "metrics": {
                        "total_requests": total,
                        "successful_requests": self.stats["successful_requests"],
                        "failed_requests": self.stats["failed_requests"],
                        "success_rate": success_rate,
                        "retry_count": self.stats["retry_count"],
                        "voice_distribution": voice_distribution,
                        "avg_response_length": avg_response_length,
                        "avg_latency": self.stats["avg_latency"],
                        "batch_processing_count": self.stats["batch_processing_count"],
                        "avg_queue_size": avg_queue_size,
                        "error_count": self.stats["error_count"],
                        "system_load": system_load,
                        "processing_active": self.running
                    }
                }
                
                # Send health data
                try:
                    self.health_socket.send_string(json.dumps(health_data))
                    logger.debug(f"Sent health metrics to dashboard")
                except Exception as e:
                    logger.warning(f"Failed to send health metrics: {e}")
            
            except Exception as e:
                logger.error(f"Error in health reporting: {e}")
            
            time.sleep(check_interval)
            
    def send_to_tts(self, text: str, voice_preset: Optional[str] = None) -> bool:
        """Send text to TTS agent for speech synthesis with retry mechanism"""
        max_retries = MAX_RETRIES
        retry_count = 0
        retry_delay = RETRY_DELAY
        
        while retry_count < max_retries:
            try:
                logger.info(f"Sending to TTS (attempt {retry_count+1}/{max_retries}): {text[:50]}...")
                
                # Determine voice preset if not specified
                if not voice_preset:
                    voice_preset = "en_male"  # Default to English male voice
                    
                # Update statistics for this request
                self.stats["total_requests"] += 1
                
                # Track voice distribution
                if voice_preset in self.stats["voice_distribution"]:
                    self.stats["voice_distribution"][voice_preset] += 1
                else:
                    self.stats["voice_distribution"]["other"] += 1
                    
                # Track response length
                self.stats["response_lengths"].append(len(text))
                
                tts_command = {
                    "command": "speak",
                    "text": text,
                    "voice": voice_preset
                }
                
                # Get socket from pool
                socket = self.connection_pool.acquire()
                if not socket:
                    raise Exception("Failed to acquire socket from pool")
                
                try:
                    # Set socket timeout
                    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
                    socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
                    
                    # Record start time for latency tracking
                    start_time = time.time()
                    
                    socket.send_string(json.dumps(tts_command))
                    response = socket.recv_json()
                    
                    # Calculate and record latency
                    latency = time.time() - start_time
                    self.stats["tts_latencies"].append(latency)
                    
                    if response.get('status') != 'ok':
                        logger.error(f"TTS agent returned error: {response}")
                        self.stats["failed_requests"] += 1
                        return False
                    
                    logger.info(f"TTS successfully processed: '{text[:30]}...' in {latency:.3f}s")
                    self.stats["successful_requests"] += 1
                    return True
                    
                finally:
                    # Always release socket back to pool
                    self.connection_pool.release(socket)
                
            except zmq.error.Again as e:
                # Timeout occurred
                logger.warning(f"TTS request timed out (attempt {retry_count+1}/{max_retries}): {e}")
                retry_count += 1
                self.stats["retry_count"] += 1
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Error communicating with TTS agent: {e}")
                retry_count += 1
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        logger.error(f"Failed to send to TTS after {max_retries} attempts")
        self.stats["failed_requests"] += 1
        return False
        
    def run(self):
        logger.info("TTS Connector running...")
        
        # Start health reporting thread
        self.health_thread = threading.Thread(target=self.report_health, daemon=True)
        self.health_thread.start()
        

        while self.running:
            try:

                # Get batch of requests
                batch = self.request_queue.get_batch()
                if not batch:
                    time.sleep(0.01)
                    continue
                # Process batch
                start_time = time.time()
                self._process_batch(batch)
                # Update statistics
                self.stats["batch_processing_count"] += 1
                self.stats["queue_sizes"].append(
                    self.request_queue.high_priority.qsize() +
                    self.request_queue.normal_priority.qsize() +
                    self.request_queue.low_priority.qsize()
                )
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self.stats["error_count"] += 1
    
    def _process_batch(self, batch: List[Dict]):
        """Process a batch of requests"""
        for request in batch:
            try:
                if request.get('type') == 'response':
                    response_text = request.get('response', '')
                    language_type = request.get('language_type', 'english')
                    
                    # Determine voice based on language
                    voice = "en_male"  # Default voice
                    if language_type.lower() == 'tagalog':
                        voice = "tl_male"
                    
                    # Send to TTS agent
                    self.send_to_tts(response_text, voice)
                    
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                self.stats["error_count"] += 1
    
    def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down TTS Connector...")
        self.running = False
        
        # Close connection pool
        if self.connection_pool:
            self.connection_pool.close()
        
        # Close ZMQ sockets
        if self.sub_socket:
            self.sub_socket.close()
        if self.health_socket:
            self.health_socket.close()
        
        # Terminate ZMQ context
        if self.context:
            self.context.term()
        
        logger.info("TTS Connector shutdown complete")

if __name__ == "__main__":
    try:
        logger.info("=== TTS Connector starting up ===")
        connector = TTSConnector()
        connector.run()
    except Exception as e:
        logger.exception(f"TTS Connector crashed on startup: {e}")
        sys.exit(1)
    finally:
        try:
            connector.shutdown()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
