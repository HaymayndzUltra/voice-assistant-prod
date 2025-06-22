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

class PerformanceMonitor:
    def __init__(self):
        self.context = zmq.Context()
        
        # Publisher for broadcasting metrics
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://*:{PUB_PORT}")
        
        # Store metrics
        self.metrics = {
            'response_times': {},
            'throughput': {},
            'error_rates': {},
            'resource_usage': {}
        }
        
    def log_metric(self, agent_name: str, operation: str, duration: float, success: bool):
        """Log a performance metric"""
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
        """Start the performance monitor"""
        logging.info("Performance Monitor started")
        try:
            while True:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            logging.info("Performance Monitor shutting down...")
        finally:
            self.publisher.close()
            self.context.term()

def main():
    monitor = PerformanceMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
