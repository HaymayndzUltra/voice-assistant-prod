import asyncio
import zmq
import json
import time
from typing import Dict, Any, Callable, List
import logging
from datetime import datetime
import threading
import os
from utils.config_parser import parse_agent_args
from src.core.base_agent import BaseAgent
_agent_args = parse_agent_args()

# Constants
ZMQ_PULL_PORT = 5617  # Port for receiving proactive signals
ZMQ_PUSH_PORT = 5618  # Port for sending pre-load requests
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 5  # seconds
MAX_RETRIES = 3

class PredictiveLoader(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        """Initialize the PredictiveLoader with ZMQ sockets."""
        # Port selection logic
        if port is not None:
            self.port = port
        elif hasattr(_agent_args, 'port') and _agent_args.port is not None:
            self.port = int(_agent_args.port)
        else:
            self.port = 5619  # fallback default
            
        super().__init__(port=self.port, name="PredictiveLoader", strict_port=True)
        
        # Initialize sockets (will be set up in async initialization)
        self.pull_socket = None
        self.push_socket = None
        self.health_socket = None
        
        # Health monitoring
        self.health_status = {
            "status": "ok",
            "service": "predictive_loader",
            "last_check": time.time(),
            "connections": {
                "pull_socket": False,
                "push_socket": False,
                "health_socket": False
            }
        }
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._monitor_health, daemon=True)
        self.health_thread.start()
        
        # Running flag
        self.running = True
        
        print(f"PredictiveLoader initialized on port {self.port}")
        
    def _perform_initialization(self):
        """Initialize agent components asynchronously."""
        try:
            self._setup_sockets()
            self._setup_predictive_tasks()
            self._setup_logging()
            self.logger.info("PredictiveLoader initialization completed successfully")
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Initialization error: {e}")
            else:
                print(f"Initialization error: {e}")
            raise
        
    def _setup_sockets(self):
        """Set up ZMQ sockets for communication"""
        # Socket for receiving proactive signals
        self.pull_socket = self.context.socket(zmq.PULL)
        self.pull_socket.bind(f"tcp://*:{ZMQ_PULL_PORT}")
        
        # Socket for sending pre-load requests
        self.push_socket = self.context.socket(zmq.PUSH)
        self.push_socket.bind(f"tcp://*:{ZMQ_PUSH_PORT}")
        
        # Socket for health monitoring (use main port + 2 to avoid conflicts)
        health_port = self.port + 2
        self.health_socket = self.context.socket(zmq.PUB)
        try:
            self.health_socket.connect(f"tcp://{getattr(_agent_args, 'host', 'localhost')}:{health_port}")
            self.health_status["connections"]["health_socket"] = True
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Could not connect to health dashboard: {e}")
            else:
                print(f"Could not connect to health dashboard: {e}")
        
        # Update health status
        self.health_status["connections"]["pull_socket"] = True
        self.health_status["connections"]["push_socket"] = True
        
    def _setup_predictive_tasks(self):
        """Set up predictive task handlers"""
        self.predictive_tasks = {
            'coding': self._prepare_code_generation,
            'travel': self._prepare_travel_planning,
            'finance': self._prepare_financial_analysis,
            'general_knowledge': self._prepare_general_knowledge,
            'tts': self._prepare_tts_resources,
            'translation': self._prepare_translation_resources,
            'emotion': self._prepare_emotion_resources
        }
        
    def _setup_logging(self):
        """Set up logging configuration"""
        log_dir = os.path.join(os.path.dirname(__file__), '../../logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'predictive_loader.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PredictiveLoader')
        
    def _monitor_health(self):
        """Monitor health of all connections"""
        while self.running:
            try:
                # Update health status
                self.health_status.update({
                    "last_check": time.time(),
                    "connections": {
                        "pull_socket": self.pull_socket is not None,
                        "push_socket": self.push_socket is not None,
                        "health_socket": self.health_socket is not None
                    }
                })
                
                # Send health update
                if self.health_socket:
                    self.health_socket.send_json({
                        "service": "predictive_loader",
                        "status": self.health_status
                    })
                
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.error(f"Health monitoring error: {e}")
                else:
                    print(f"Health monitoring error: {e}")
                time.sleep(HEALTH_CHECK_INTERVAL)
    
    def _handle_proactive_signal(self, signal: Dict[str, Any]):
        """Handle proactive signal from context monitor"""
        context_type = signal.get('context_type')
        confidence = signal.get('confidence', 0.0)
        
        if context_type and confidence >= 0.7:  # Only act on high confidence signals
            task = self.predictive_tasks.get(context_type)
            if task:
                asyncio.run(task())
                self.logger.info(f"Processed proactive signal for {context_type} with confidence {confidence}")
            else:
                self.logger.warning(f"Unknown context type: {context_type}")
    
    async def _prepare_code_generation(self):
        """Pre-load code generation resources"""
        self.logger.info("Preparing code generation resources")
        await self._send_preload_request('code_generator', {
            'model': 'codellama',
            'warmup': True
        })
        
    async def _prepare_travel_planning(self):
        """Pre-load travel planning resources"""
        self.logger.info("Preparing travel planning resources")
        await self._send_preload_request('travel_planner', {
            'locations': True,
            'weather': True,
            'accommodation': True
        })
        
    async def _prepare_financial_analysis(self):
        """Pre-load financial analysis resources"""
        self.logger.info("Preparing financial analysis resources")
        await self._send_preload_request('financial_analyzer', {
            'market_data': True,
            'portfolio': True,
            'news': True
        })
        
    async def _prepare_general_knowledge(self):
        """Pre-load general knowledge resources"""
        self.logger.info("Preparing general knowledge resources")
        await self._send_preload_request('knowledge_base', {
            'fast_model': 'tinylama',
            'cache': True
        })
        
    async def _prepare_tts_resources(self):
        """Pre-load TTS resources"""
        self.logger.info("Preparing TTS resources")
        await self._send_preload_request('streaming_tts_agent', {
            'model': 'xtts_v2',
            'warmup': True,
            'cache': True
        })
        
    async def _prepare_translation_resources(self):
        """Pre-load translation resources"""
        self.logger.info("Preparing translation resources")
        await self._send_preload_request('nllb_adapter', {
            'model': 'nllb-200-distilled',
            'warmup': True
        })
        
    async def _prepare_emotion_resources(self):
        """Pre-load emotion analysis resources"""
        self.logger.info("Preparing emotion analysis resources")
        await self._send_preload_request('emotion_engine', {
            'models': ['emotion_detector', 'sentiment_analyzer'],
            'warmup': True
        })
        
    async def _send_preload_request(self, agent: str, data: Dict[str, Any]):
        """Send preload request to specific agent"""
        if not self.push_socket:
            self.logger.warning("Push socket not ready, skipping preload request")
            return
            
        request = {
            'type': 'preload',
            'agent': agent,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.push_socket.send_json(request)
        self.logger.info(f"Sent preload request to {agent}")

    def preload_topic(self, topic: str):
        """Manually trigger preload for a specific topic"""
        if topic in self.predictive_tasks:
            asyncio.run(self.predictive_tasks[topic]())

    def start(self):
        """Start the predictive loader"""
        self.logger.info("Predictive Loader started")
        self._start_task_processor()
        
    def _start_task_processor(self):
        """Start background thread for processing proactive signals"""
        def process_signals():
            while self.running:
                try:
                    if not self.pull_socket:
                        time.sleep(1)
                        continue
                        
                    if self.pull_socket.poll(1000) == 0:  # 1 second timeout
                        continue
                    signal = self.pull_socket.recv_json()
                    self._handle_proactive_signal(signal)
                except Exception as e:
                    self.logger.error(f"Error processing signal: {str(e)}")
                    time.sleep(1)

        thread = threading.Thread(target=process_signals, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop the predictive loader"""
        self.running = False
        self.logger.info("Predictive Loader shutting down...")
        
        # Close sockets
        if self.pull_socket:
            self.pull_socket.close()
        if self.push_socket:
            self.push_socket.close()
        if self.health_socket:
            self.health_socket.close()
        
        super().cleanup()
        
    def run(self):
        """Run the predictive loader"""
        try:
            self.start()
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            self.stop()

    def _health_check_loop(self):
        """Override BaseAgent health check to avoid conflicts with custom health socket."""
        # Use the custom health monitoring instead
        self._monitor_health()

def main():
    loader = PredictiveLoader()
    loader.run()

if __name__ == "__main__":
    main()
