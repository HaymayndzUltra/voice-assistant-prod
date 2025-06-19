import zmq
import json
import logging
import threading
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.config_parser import parse_agent_args

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/task_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TaskScheduler')

class TaskSchedulerAgent:
    def __init__(self, port=7115, health_port=7116, async_processor_port=5555):
        self.port = port
        self.health_port = health_port
        self.async_processor_port = async_processor_port
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        self._setup_sockets()
        self._start_health_check()
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        logger.info(f"TaskSchedulerAgent starting on port {port} (health: {health_port})")

    def _setup_sockets(self):
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"TaskSchedulerAgent main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {str(e)}")
            raise
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check endpoint on port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check to port {self.health_port}: {str(e)}")
            raise
        # Socket to communicate with AsyncProcessor
        self.async_socket = self.context.socket(zmq.REQ)
        self.async_socket.connect(f"tcp://localhost:{self.async_processor_port}")

    def _start_health_check(self):
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'TaskScheduler',
                            'initialization_status': 'complete' if self.initialized else 'in_progress',
                            'port': self.port,
                            'health_port': self.health_port,
                            'timestamp': datetime.now().isoformat()
                        }
                        if self.initialization_error:
                            response['initialization_error'] = str(self.initialization_error)
                    else:
                        response = {
                            'status': 'unknown_action',
                            'message': f"Unknown action: {request.get('action', 'none')}"
                        }
                    self.health_socket.send_json(response)
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                    time.sleep(1)
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()

    def _initialize_background(self):
        try:
            # Simulate any heavy initialization if needed
            time.sleep(1)
            self.initialized = True
            logger.info("TaskSchedulerAgent initialization completed")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"TaskSchedulerAgent initialization failed: {str(e)}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get('action')
        if action == 'schedule_task':
            # Forward to AsyncProcessor
            self.async_socket.send_json({
                'type': request.get('type'),
                'data': request.get('data'),
                'priority': request.get('priority', 'medium')
            })
            response = self.async_socket.recv_json()
            return response
        elif action == 'ping':
            return {'status': 'success', 'message': 'pong'}
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info("Starting TaskSchedulerAgent main loop")
        while True:
            try:
                if self.socket.poll(1000) > 0:
                    request = self.socket.recv_json()
                    response = self.handle_request(request)
                    self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)

    def shutdown(self):
        self.socket.close()
        self.health_socket.close()
        self.async_socket.close()
        self.context.term()
        logger.info("TaskSchedulerAgent shutdown complete")

if __name__ == "__main__":
    args = parse_agent_args()
    agent = TaskSchedulerAgent(
        port=getattr(args, 'port', 7115),
        health_port=getattr(args, 'health_port', 7116),
        async_processor_port=getattr(args, 'async_processor_port', 5555)
    )
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        agent.shutdown() 