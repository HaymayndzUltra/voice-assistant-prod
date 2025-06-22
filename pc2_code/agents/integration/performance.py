import zmq
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any
import threading

# Constants
PERFORMANCE_TOPIC = "performance_metrics"
PUB_PORT = 5614  # For broadcasting metrics
PULL_PORT = 5615  # For receiving fire-and-forget logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/performance_metrics.log'),
        logging.StreamHandler()
    ]
)

class PerformanceLoggerAgent:
    def __init__(self):
        self.context = zmq.Context()
        
        # Publisher for broadcasting metrics
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://*:{PUB_PORT}")
        
        # Pull socket for receiving fire-and-forget logs
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(f"tcp://*:{PULL_PORT}")
        
        # Store metrics
        self.metrics = {
            'response_times': {},
            'throughput': {},
            'error_rates': {},
            'resource_usage': {}
        }
        
        # Start background thread for processing logs
        self._start_log_processor()

    def log_zmq_call(self, agent_name: str, operation: str, start_time: float, end_time: float, success: bool):
        """Log a ZMQ call with timing information"""
        duration = end_time - start_time
        
        # Update metrics
        if agent_name not in self.metrics['response_times']:
            self.metrics['response_times'][agent_name] = []
        self.metrics['response_times'][agent_name].append(duration)
        
        if not success:
            if agent_name not in self.metrics['error_rates']:
                self.metrics['error_rates'][agent_name] = 0
            self.metrics['error_rates'][agent_name] += 1
        
        # Broadcast metrics
        self._broadcast_metrics({
            'timestamp': datetime.now().isoformat(),
            'agent': agent_name,
            'operation': operation,
            'duration': duration,
            'success': success
        })

    def _broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast metrics to all subscribers"""
        self.publisher.send_string(f"{PERFORMANCE_TOPIC} {json.dumps(metrics)}")

    def _start_log_processor(self):
        """Start background thread to process incoming logs"""
        def process_logs():
            while True:
                try:
                    message = self.pull_socket.recv_json()
                    self._process_log_message(message)
                except Exception as e:
                    logging.error(f"Error processing log: {str(e)}")
                    time.sleep(1)

        thread = threading.Thread(target=process_logs, daemon=True)
        thread.start()

    def _process_log_message(self, message: Dict[str, Any]):
        """Process incoming log message"""
        agent_name = message.get('agent')
        operation = message.get('operation')
        duration = message.get('duration')
        success = message.get('success', True)
        
        if agent_name and operation and duration is not None:
            self.log_zmq_call(agent_name, operation, time.time() - duration, time.time(), success)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            'response_times': self._calculate_response_times(),
            'error_rates': self._calculate_error_rates(),
            'throughput': self._calculate_throughput()
        }

    def _calculate_response_times(self) -> Dict[str, Any]:
        """Calculate average response times"""
        results = {}
        for agent, times in self.metrics['response_times'].items():
            if times:
                avg_time = sum(times) / len(times)
                results[agent] = {
                    'average': avg_time,
                    'count': len(times),
                    'max': max(times),
                    'min': min(times)
                }
        return results

    def _calculate_error_rates(self) -> Dict[str, float]:
        """Calculate error rates"""
        return self.metrics['error_rates']

    def _calculate_throughput(self) -> Dict[str, float]:
        """Calculate throughput"""
        throughput = {}
        for agent, times in self.metrics['response_times'].items():
            if times:
                throughput[agent] = len(times) / sum(times)
        return throughput

    def run(self):
        """Start the performance logger agent"""
        logging.info("Performance Logger Agent started")
        try:
            while True:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            logging.info("Performance Logger Agent shutting down...")
        finally:
            self.publisher.close()
            self.pull_socket.close()
            self.context.term()

def performance_log(agent_name: str):
    """
    Decorator to add performance logging to ZMQ calls
    
    Args:
        agent_name: Name of the agent making the ZMQ call
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start timing
            start_time = time.time()
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise e
            finally:
                # Calculate duration
                end_time = time.time()
                duration = end_time - start_time
                
                # Send log to PerformanceLoggerAgent
                _send_performance_log(agent_name, func.__name__, duration, success)
            
            return result
        
        return wrapper
    
    return decorator

def _send_performance_log(agent_name: str, operation: str, duration: float, success: bool):
    """Send performance log to PerformanceLoggerAgent"""
    context = zmq.Context()
    push_socket = context.socket(zmq.PUSH)
    push_socket.connect(f"tcp://localhost:{PULL_PORT}")
    
    try:
        log_message = {
            'agent': agent_name,
            'operation': operation,
            'duration': duration,
            'success': success,
            'timestamp': time.time()
        }
        push_socket.send_json(log_message)
    except Exception as e:
        print(f"Error sending performance log: {str(e)}")
    finally:
        push_socket.close()
        context.term()
