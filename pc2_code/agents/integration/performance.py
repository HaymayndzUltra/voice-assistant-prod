import zmq
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Callable
import threading
from functools import wraps

# BaseAgent import - REQUIRED for migration
from common.core.base_agent import BaseAgent

# Standardized utilities
from common.utils.path_manager import PathManager
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.logger_util import get_json_logger
from common.utils.path_manager import PathManager
from common.env_helpers import get_env

# Constants
PERFORMANCE_TOPIC = "performance_metrics"
PUB_PORT = 5614  # For broadcasting metrics
PULL_PORT = 5615  # For receiving fire-and-forget logs

class PerformanceLoggerAgent(BaseAgent):
    """
    Performance Logger Agent migrated to BaseAgent inheritance.
    
    Provides performance monitoring and metrics collection for ZMQ operations
    across the agent system.
    """
    
    def __init__(self, port: int = None, health_check_port: int = None, **kwargs):
        """
        Initialize the Performance Logger Agent with BaseAgent inheritance.
        
        Args:
            port: Main service port (optional, will use PULL_PORT if not provided)
            health_check_port: Health check port (optional, defaults to port+1)
            **kwargs: Additional configuration parameters
        """
        # CRITICAL: Call BaseAgent.__init__() FIRST
        super().__init__(
            name=kwargs.get('name', 'PerformanceLoggerAgent'),
            port=port or PULL_PORT,
            health_check_port=health_check_port,
            **kwargs
        )
        
        # Get JSON logger for standardized logging
        self.logger = get_json_logger(self.name)
        
        # Store metrics
        self.metrics = {
            'response_times': {},
            'throughput': {},
            'error_rates': {},
            'resource_usage': {}
        }
        
        # Set up custom sockets for performance monitoring
        self._setup_performance_sockets()
        
        # Start background log processor
        self._start_log_processor()
        
        self.logger.info(f"{self.name} initialized successfully", extra={
            "port": self.port,
            "health_check_port": self.health_check_port,
            "pub_port": PUB_PORT,
            "pull_port": PULL_PORT,
            "component": "initialization"
        })
    
    def _setup_performance_sockets(self):
        """Set up custom ZMQ sockets for performance monitoring."""
        try:
            # Publisher for broadcasting metrics
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(f"tcp://*:{PUB_PORT}")
            self.logger.info(f"Publisher socket bound to port {PUB_PORT}")
            
            # Pull socket for receiving fire-and-forget logs
            self.pull_socket = self.context.socket(zmq.PULL)
            self.pull_socket.bind(f"tcp://*:{PULL_PORT}")
            self.logger.info(f"Pull socket bound to port {PULL_PORT}")
            
        except Exception as e:
            self.logger.error(f"Failed to set up performance sockets: {e}")
            raise

    def log_zmq_call(self, agent_name: str, operation: str, start_time: float, end_time: float, success: bool):
        """Log a ZMQ call with timing information"""
        try:
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
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'agent': agent_name,
                'operation': operation,
                'duration': duration,
                'success': success
            }
            
            self._broadcast_metrics(metrics_data)
            
            self.logger.info("ZMQ call logged", extra={
                "agent_name": agent_name,
                "operation": operation,
                "duration": duration,
                "success": success,
                "component": "performance_logging"
            })
            
        except Exception as e:
            self.logger.error(f"Error logging ZMQ call: {e}", extra={
                "agent_name": agent_name,
                "operation": operation,
                "component": "performance_logging"
            })

    def _broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast metrics to all subscribers"""
        try:
            message = f"{PERFORMANCE_TOPIC} {json.dumps(metrics)}"
            self.publisher.send_string(message)
        except Exception as e:
            self.logger.error(f"Error broadcasting metrics: {e}")

    def _start_log_processor(self):
        """Start background thread to process incoming logs"""
        def process_logs():
            self.logger.info("Log processor thread started")
            while self.running:
                try:
                    # Set a timeout to allow checking self.running
                    if self.pull_socket.poll(timeout=1000):  # 1 second timeout
                        message = self.pull_socket.recv_json(zmq.NOBLOCK)
                        self._process_log_message(message)
                except zmq.Again:
                    # Timeout occurred, continue loop to check self.running
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing log: {e}")
                    time.sleep(1)
            
            self.logger.info("Log processor thread stopped")

        self.log_processor_thread = threading.Thread(target=process_logs, daemon=True)
        self.log_processor_thread.start()

    def _process_log_message(self, message: Dict[str, Any]):
        """Process incoming log message"""
        try:
            agent_name = message.get('agent')
            operation = message.get('operation')
            duration = message.get('duration')
            success = message.get('success', True)
            
            if agent_name and operation and duration is not None:
                current_time = time.time()
                start_time = current_time - duration
                self.log_zmq_call(agent_name, operation, start_time, current_time, success)
            else:
                self.logger.warning("Incomplete log message received", extra={
                    "message": message,
                    "component": "log_processing"
                })
                
        except Exception as e:
            self.logger.error(f"Error processing log message: {e}", extra={
                "message": message,
                "component": "log_processing"
            })

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        try:
            return {
                'response_times': self._calculate_response_times(),
                'error_rates': self._calculate_error_rates(),
                'throughput': self._calculate_throughput(),
                'timestamp': datetime.now().isoformat(),
                'agent_name': self.name
            }
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            return {}

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
        return self.metrics['error_rates'].copy()

    def _calculate_throughput(self) -> Dict[str, float]:
        """Calculate throughput (operations per second)"""
        throughput = {}
        for agent, times in self.metrics['response_times'].items():
            if times:
                total_time = sum(times)
                if total_time > 0:
                    throughput[agent] = len(times) / total_time
                else:
                    throughput[agent] = 0
        return throughput

    def run(self):
        """
        Main execution method using BaseAgent's run() framework.
        """
        try:
            self.logger.info(f"Starting {self.name}")
            
            # Start metrics reporting thread
            self._start_metrics_reporting()
            
            # Call parent run() method for standard startup
            super().run()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested via KeyboardInterrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in {self.name}: {e}")
            raise
        finally:
            self.cleanup()
    
    def _start_metrics_reporting(self):
        """Start periodic metrics reporting"""
        def metrics_reporter():
            while self.running:
                try:
                    metrics = self.get_current_metrics()
                    if metrics:
                        self.logger.info("Performance metrics report", extra={
                            "metrics": metrics,
                            "component": "metrics_reporting"
                        })
                    time.sleep(60)  # Report every minute
                except Exception as e:
                    self.logger.error(f"Error in metrics reporting: {e}")
                    time.sleep(10)
        
        self.metrics_reporter_thread = threading.Thread(target=metrics_reporter, daemon=True)
        self.metrics_reporter_thread.start()

    def cleanup(self):
        """
        Cleanup method with custom cleanup logic for performance monitoring.
        """
        try:
            self.logger.info(f"Cleaning up {self.name}")
            
            # Custom cleanup logic
            if hasattr(self, 'publisher'):
                self.publisher.close()
            
            if hasattr(self, 'pull_socket'):
                self.pull_socket.close()
            
            # Call parent cleanup
            super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


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
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                # Calculate duration
                end_time = time.time()
                duration = end_time - start_time
                
                # Send log to PerformanceLoggerAgent
                _send_performance_log(agent_name, func.__name__, duration, success)
        
        return wrapper
    
    return decorator


def _send_performance_log(agent_name: str, operation: str, duration: float, success: bool):
    """Send performance log to PerformanceLoggerAgent"""
    context = zmq.Context()
    push_socket = context.socket(zmq.PUSH)
    
    try:
        push_socket.connect(f"tcp://localhost:{PULL_PORT}")
        
        log_message = {
            'agent': agent_name,
            'operation': operation,
            'duration': duration,
            'success': success,
            'timestamp': time.time()
        }
        
        push_socket.send_json(log_message)
        
    except Exception as e:
        # Use basic logging here to avoid circular dependencies
        print(f"Error sending performance log: {str(e)}")
    finally:
        push_socket.close()
        context.term()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run PerformanceLoggerAgent")
    parser.add_argument('--port', type=int, help='Main service port')
    parser.add_argument('--health-port', type=int, help='Health check port')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Create and run agent
    agent = PerformanceLoggerAgent(
        port=args.port,
        health_check_port=args.health_port
    )
    
    agent.run()
