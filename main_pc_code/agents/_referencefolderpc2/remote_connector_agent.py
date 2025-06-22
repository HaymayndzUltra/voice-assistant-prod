"""
Remote Connector / API Client Agent
- Handles API requests to remote/local models
- Provides a unified interface for all AI models
- Supports both synchronous and asynchronous requests
- Uses centralized configuration system
- Implements response caching for improved performance
- Enhanced connection handling and API management
"""
import zmq
import json
import time
import logging
import threading
import requests
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))
from config.system_config import config

# Configure logging
log_level = config.get('system.log_level', 'INFO')
log_file = Path(config.get('system.logs_dir', 'logs')) / "remote_connector.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RemoteConnector")

# Get ZMQ ports from config
REMOTE_CONNECTOR_PORT = config.get('zmq.remote_connector_port', 5557)
MODEL_MANAGER_PORT = config.get('zmq.model_manager_port', 5555)
MODEL_MANAGER_HOST = config.get('zmq.model_manager_host', '192.168.1.27')

class ConnectionState(Enum):
    """Connection state enum"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class APIConfig:
    """API configuration"""
    url: str
    timeout: int
    max_retries: int
    retry_delay: int
    headers: Dict[str, str]
    auth: Optional[Dict[str, str]] = None

class ConnectionManager:
    """Manages API connections and retries"""
    
    def __init__(self):
        self.connections: Dict[str, ConnectionState] = {}
        self.last_attempt: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.lock = threading.Lock()
    
    def update_state(self, api_name: str, state: ConnectionState):
        """Update connection state"""
        with self.lock:
            self.connections[api_name] = state
            if state == ConnectionState.ERROR:
                self.error_counts[api_name] = self.error_counts.get(api_name, 0) + 1
            else:
                self.error_counts[api_name] = 0
    
    def can_retry(self, api_name: str, max_retries: int, retry_delay: int) -> bool:
        """Check if retry is allowed"""
        with self.lock:
            if api_name not in self.error_counts:
                return True
            if self.error_counts[api_name] >= max_retries:
                return False
            last_attempt = self.last_attempt.get(api_name, 0)
            return time.time() - last_attempt >= retry_delay
    
    def record_attempt(self, api_name: str):
        """Record connection attempt"""
        with self.lock:
            self.last_attempt[api_name] = time.time()

class CacheManager:
    """Manages response caching"""
    
    def __init__(self, cache_dir: Path, ttl: int):
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0
        }
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached response"""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            self.stats['misses'] += 1
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            if time.time() - data['timestamp'] > self.ttl:
                self.stats['expired'] += 1
                return None
            
            self.stats['hits'] += 1
            return data['response']
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            self.stats['misses'] += 1
            return None
    
    def set(self, key: str, response: Dict):
        """Set cached response"""
        try:
            cache_file = self.cache_dir / f"{key}.json"
            with open(cache_file, 'w') as f:
                json.dump({
                    'response': response,
                    'timestamp': time.time()
                }, f)
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return self.stats.copy()

class RemoteConnectorAgent:
    """Enhanced Remote Connector Agent"""
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("Initializing Enhanced Remote Connector Agent")
        logger.info("=" * 80)
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self._setup_zmq_sockets()
        
        # Initialize managers
        self.connection_manager = ConnectionManager()
        self.cache_manager = CacheManager(
            Path(config.get('system.cache_dir', 'cache')) / "model_responses",
            config.get('models.cache_ttl', 3600)
        )
        
        # Initialize API configurations
        self.api_configs = {
            'ollama': APIConfig(
                url=config.get('models.ollama.url', 'http://localhost:11434'),
                timeout=30,
                max_retries=3,
                retry_delay=2,
                headers={'Content-Type': 'application/json'}
            ),
            'deepseek': APIConfig(
                url=config.get('models.deepseek.url', 'http://localhost:8000'),
                timeout=60,
                max_retries=3,
                retry_delay=5,
                headers={'Content-Type': 'application/json'},
                auth={'api_key': config.get('models.deepseek.api_key', '')}
            )
        }
        
        # Initialize async session
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Running flag
        self.running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_connections)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Enhanced Remote Connector Agent initialized")
        logger.info("=" * 80)
    
    def _setup_zmq_sockets(self):
        """Setup ZMQ sockets"""
        try:
            # Get host and ports from config
            self.host = config.get('system.host', '0.0.0.0')
            self.port = config.get('zmq.remote_connector_port', 5557)
            
            # Socket to receive requests
            self.receiver = self.context.socket(zmq.REP)
            self.receiver.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.receiver.bind(f"tcp://{self.host}:{self.port}")
            logger.info(f"RemoteConnectorAgent listening on {self.host}:{self.port}")
            
            # Socket to communicate with model manager
            self.model_manager = self.context.socket(zmq.REQ)
            self.model_manager.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            model_manager_host = config.get('zmq.model_manager_host', 'localhost')
            model_manager_port = config.get('zmq.model_manager_port', 5555)
            self.model_manager.connect(f"tcp://{model_manager_host}:{model_manager_port}")
            self.model_manager.setsockopt(zmq.RCVTIMEO, config.get('zmq.timeout', 500))
            logger.info(f"Connected to Model Manager at {model_manager_host}:{model_manager_port}")
            
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to setup ZMQ sockets: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in _setup_zmq_sockets: {str(e)}")
            raise
    
    async def _make_api_request(self, api_name: str, endpoint: str, data: Dict) -> Dict:
        """Make API request with retry logic"""
        config = self.api_configs[api_name]
        
        if not self.connection_manager.can_retry(api_name, config.max_retries, config.retry_delay):
            return {
                "status": "error",
                "message": f"Max retries exceeded for {api_name}"
            }
        
        self.connection_manager.record_attempt(api_name)
        self.connection_manager.update_state(api_name, ConnectionState.CONNECTING)
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"{config.url}{endpoint}"
            async with self.session.post(
                url,
                json=data,
                headers=config.headers,
                timeout=config.timeout
            ) as response:
                result = await response.json()
                self.connection_manager.update_state(api_name, ConnectionState.CONNECTED)
                return result
                
        except Exception as e:
            logger.error(f"API request failed: {e}")
            self.connection_manager.update_state(api_name, ConnectionState.ERROR)
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _monitor_connections(self):
        """Monitor API connections"""
        while self.running:
            for api_name, state in self.connection_manager.connections.items():
                if state == ConnectionState.ERROR:
                    logger.warning(f"API {api_name} in error state")
                elif state == ConnectionState.DISCONNECTED:
                    logger.info(f"API {api_name} disconnected")
            time.sleep(5)
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming request"""
        try:
            action = request.get('action')
            if not action:
                return {'error': 'No action specified'}
            
            if action == 'inference':
                return self._handle_inference(request)
            elif action == 'status':
                return self._handle_status(request)
            elif action == 'cache_stats':
                return self._handle_cache_stats()
            else:
                return {'error': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {'error': str(e)}
    
    def _handle_inference(self, request: Dict) -> Dict:
        """Handle inference request"""
        model = request.get('model')
        prompt = request.get('prompt')
        
        if not model or not prompt:
            return {'error': 'Missing model or prompt'}
        
        # Check cache
        cache_key = hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()
        cached_response = self.cache_manager.get(cache_key)
        if cached_response:
            return {
                'status': 'success',
                'response': cached_response,
                'cached': True
            }
        
        # Determine API and make request
        api_name = 'ollama' if model.startswith('ollama/') else 'deepseek'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(self._make_api_request(
            api_name,
            '/api/generate',
            {
                'model': model.replace('ollama/', ''),
                'prompt': prompt,
                'temperature': request.get('temperature', 0.7)
            }
        ))
        loop.close()
        
        if response.get('status') == 'success':
            self.cache_manager.set(cache_key, response)
        
        return response
    
    def _handle_status(self, request: Dict) -> Dict:
        """Handle status request"""
        return {
            'status': 'success',
            'connections': {
                name: state.value for name, state in self.connection_manager.connections.items()
            },
            'cache_stats': self.cache_manager.get_stats()
        }
    
    def _handle_cache_stats(self) -> Dict:
        """Handle cache statistics request"""
        return {
            'status': 'success',
            'stats': self.cache_manager.get_stats()
        }
    
    def run(self):
        """Run the agent"""
        try:
            logger.info("Starting Remote Connector Agent...")
            while self.running:
                try:
                    request = self.receiver.recv_json()
                    response = self.handle_request(request)
                    self.receiver.send_json(response)
                except zmq.error.Again:
                    continue
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    self.receiver.send_json({'error': str(e)})
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        if self.session:
            asyncio.run(self.session.close())
        self.executor.shutdown()
        self.receiver.close()
        self.model_manager.close()
        self.context.term()

def main():
    """Main entry point"""
    agent = RemoteConnectorAgent()
    agent.run()

if __name__ == "__main__":
    main()