from main_pc_code.src.core.base_agent import BaseAgent
"""
Streaming Text Processor Module
Processes text input and generates appropriate responses
"""

import zmq
import logging
import json
import time
import threading
import socket
import queue
import hashlib
import psutil
from typing import Dict, Optional, List
from collections import deque, OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TextProcessor")

# Constants
MAX_QUEUE_SIZE = 1000
CACHE_SIZE = 100
BATCH_SIZE = 10
BATCH_TIMEOUT = 0.1  # seconds
HEALTH_CHECK_INTERVAL = 5  # seconds
SYSTEM_LOAD_THRESHOLD = 80  # percentage

def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find available port after {max_attempts} attempts")

class LRUCache(BaseAgent):
    """Least Recently Used Cache implementation"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingTextProcessor")
        self.capacity = capacity
        self.cache = OrderedDict()
        
    def get(self, key: str) -> Optional[Dict]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
        
    def put(self, key: str, value: Dict):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

class RequestQueue(BaseAgent):
    """Priority-based request queue with batching support"""
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingTextProcessor")
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

class StreamingTextProcessor(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingTextProcessor")
        """Initialize the text processor component"""
        self.context = zmq.Context()
        self.running = True
        
        # Initialize components
        self.request_queue = RequestQueue()
        self.response_cache = LRUCache(CACHE_SIZE)
        self.processing_stats = {
            "total_requests": 0,
            "cached_responses": 0,
            "batch_processing_count": 0,
            "avg_processing_time": 0,
            "processing_times": deque(maxlen=100),
            "queue_sizes": deque(maxlen=100),
            "error_count": 0,
            "last_update": time.time()
        }
        
        # Find available ports
        try:
            self.pub_port = find_available_port(5580)  # Start from 5580
            self.sub_port = find_available_port(5581)  # Start from 5581
            self.health_port = find_available_port(5597)  # Use same health port as other components
            
            # Setup ZMQ sockets
            self.pub_socket = self.context.socket(zmq.PUB)
            self.sub_socket = self.context.socket(zmq.SUB)
            self.health_socket = self.context.socket(zmq.PUB)  # Add health socket
            
            # Bind publisher
            self.pub_socket.bind(f"tcp://*:{self.pub_port}")
            logger.info(f"Publisher bound to port {self.pub_port}")
            
            # Connect subscriber
            self.sub_socket.connect(f"tcp://localhost:{self.sub_port}")
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
            logger.info(f"Subscriber connected to port {self.sub_port}")
            
            # Bind health socket
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health socket bound to port {self.health_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ZMQ sockets: {e}")
            raise
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # Start health reporting thread
        self.health_thread = threading.Thread(target=self._health_broadcast_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        logger.info("Text processor initialized successfully")
    
    def _process_loop(self):
        """Main processing loop with batching support"""
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
                processing_time = time.time() - start_time
                self.processing_stats["processing_times"].append(processing_time)
                self.processing_stats["batch_processing_count"] += 1
                self.processing_stats["avg_processing_time"] = (
                    sum(self.processing_stats["processing_times"]) / 
                    len(self.processing_stats["processing_times"])
                )
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self.processing_stats["error_count"] += 1
    
    def _process_batch(self, batch: List[Dict]):
        """Process a batch of requests"""
        responses = []
        
        for request in batch:
            try:
                # Extract text and metadata
                text = request.get('text', '')
                metadata = request.get('metadata', {})
                
                # Check cache first
                cache_key = hashlib.md5(text.encode()).hexdigest()
                cached_response = self.response_cache.get(cache_key)
                
                if cached_response:
                    self.processing_stats["cached_responses"] += 1
                    responses.append(cached_response)
                    continue
                
                # Process the text
                response = self._generate_response(text, metadata)
                
                # Cache the response
                self.response_cache.put(cache_key, {
                    'response': response,
                    'timestamp': time.time(),
                    'metadata': metadata
                })
                
                responses.append({
                    'response': response,
                    'timestamp': time.time(),
                    'metadata': metadata
                })
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                self.processing_stats["error_count"] += 1
        
        # Send responses
        for response in responses:
            try:
                self.pub_socket.send_json(response)
            except Exception as e:
                logger.error(f"Error sending response: {e}")
    
    def _process_message(self, message: Dict):
        """Process incoming message"""
        try:
            # Determine priority based on metadata
            priority = message.get('metadata', {}).get('priority', 1)
            
            # Add to request queue
            self.request_queue.put(message, priority)
            self.processing_stats["total_requests"] += 1
            
            # Update queue size statistics
            self.processing_stats["queue_sizes"].append(
                self.request_queue.high_priority.qsize() +
                self.request_queue.normal_priority.qsize() +
                self.request_queue.low_priority.qsize()
            )
            
        except Exception as e:
            logger.error(f"Error queueing message: {e}")
            self.processing_stats["error_count"] += 1
    
    def _generate_response(self, text: str, metadata: Dict) -> str:
        """Generate response based on input text and metadata"""
        # TODO: Implement more sophisticated response generation
        return f"Processed: {text}"
    
    def _health_broadcast_loop(self):
        """Broadcast health metrics with adaptive frequency"""
        logger.info("Health broadcasting thread started")
        while self.running:
            try:
                # Calculate system load
                system_load = psutil.cpu_percent()
                
                # Adjust health check frequency based on system load
                check_interval = HEALTH_CHECK_INTERVAL
                if system_load > SYSTEM_LOAD_THRESHOLD:
                    check_interval *= 2  # Reduce frequency under high load
                
                # Calculate queue statistics
                avg_queue_size = 0
                if self.processing_stats["queue_sizes"]:
                    avg_queue_size = sum(self.processing_stats["queue_sizes"]) / len(self.processing_stats["queue_sizes"])
                
                health_data = {
                    "component": "StreamingTextProcessor",
                    "status": "healthy",
                    "timestamp": time.time(),
                    "metrics": {
                        "pub_port": self.pub_port,
                        "sub_port": self.sub_port,
                        "health_port": self.health_port,
                        "processing_active": self.running,
                        "total_requests": self.processing_stats["total_requests"],
                        "cached_responses": self.processing_stats["cached_responses"],
                        "batch_processing_count": self.processing_stats["batch_processing_count"],
                        "avg_processing_time": self.processing_stats["avg_processing_time"],
                        "avg_queue_size": avg_queue_size,
                        "error_count": self.processing_stats["error_count"],
                        "system_load": system_load
                    }
                }
                
                # Determine status based on metrics
                if self.processing_stats["error_count"] > 100:
                    health_data["status"] = "degraded"
                elif system_load > SYSTEM_LOAD_THRESHOLD:
                    health_data["status"] = "warning"
                
                health_message = json.dumps(health_data)
                self.health_socket.send_string(health_message)
                logger.debug(f"Sent health metrics: {health_message}")
                
            except Exception as e:
                logger.warning(f"Failed to send health metrics: {e}")
            
            time.sleep(check_interval)
    
    def shutdown(self):
        """Cleanup resources"""
        logger.info("Shutting down text processor...")
        self.running = False
        
        # Close ZMQ sockets
        if self.pub_socket:
            self.pub_socket.close()
        if self.sub_socket:
            self.sub_socket.close()
        if self.health_socket:
            self.health_socket.close()
        
        # Terminate ZMQ context
        if self.context:
            self.context.term()
        
        logger.info("Text processor shutdown complete")

if __name__ == "__main__":
    processor = StreamingTextProcessor()
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Text processor stopped by user")
    finally:
        processor.shutdown()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
