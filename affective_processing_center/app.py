#!/usr/bin/env python3
"""
Affective Processing Center (APC) - Main Application Bootstrap

This module provides the Affective Processing Center service that inherits from BaseAgent
and uses the approved golden utilities from the common directory.
"""

import asyncio
import logging
import signal
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add common to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import BaseAgent and golden utilities
from common.core.base_agent import BaseAgent
from common.utils.unified_config_loader import UnifiedConfigLoader
from common.utils.path_manager import PathManager

# Import APC core components
from core.cache import EmbeddingCache
from core.dag_executor import DAGExecutor
from core.fusion import create_fusion
from core.schemas import APCConfig, AudioChunk, Transcript, Payload, EmotionalContext
from modules.base import module_registry
from transport.zmq_pub import ZmqPublisher, BroadcastManager
from transport.zmq_req import ZmqSynthesisServer, SynthesisRequestHandler

# ZMQ for input subscription
import zmq
import zmq.asyncio
import yaml

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AffectiveProcessingCenter(BaseAgent):
    """
    Affective Processing Center - Unified emotional processing hub.
    
    Inherits from BaseAgent to leverage standardized health checking,
    error handling, metrics, and configuration management.
    
    This class orchestrates the entire APC pipeline including:
    - Configuration loading and validation
    - Component initialization (cache, modules, fusion, DAG)
    - Input subscription and processing loop
    - Output publishing and synthesis services
    - Graceful shutdown handling
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the APC with BaseAgent foundation.
        
        Args:
            **kwargs: Arguments passed to BaseAgent
        """
        # Initialize BaseAgent with all standard features
        super().__init__(name='AffectiveProcessingCenter', **kwargs)
        
        # Load hub-specific configuration using UnifiedConfigLoader
        config_loader = UnifiedConfigLoader()
        self.hub_config = self._load_hub_config(config_loader)
        
        # Core components
        self.cache: Optional[EmbeddingCache] = None
        self.modules: Dict[str, Any] = {}
        self.fusion: Optional[Any] = None
        self.dag_executor: Optional[DAGExecutor] = None
        
        # Transport components
        self.input_subscriber: Optional[zmq.asyncio.Socket] = None
        self.zmq_context: Optional[zmq.asyncio.Context] = None
        self.publisher: Optional[ZmqPublisher] = None
        self.synthesis_server: Optional[ZmqSynthesisServer] = None
        self.synthesis_handler: Optional[SynthesisRequestHandler] = None
        
        # State management
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._startup_time = None
        self._processed_messages = 0
        self._error_count = 0
        
        # Initialize hub components
        self._initialize_hub_components()
        
        self.logger.info(f"AffectiveProcessingCenter initialized on port {self.port}")
    
    def _load_hub_config(self, config_loader: UnifiedConfigLoader) -> APCConfig:
        """
        Load hub-specific configuration using the golden UnifiedConfigLoader.
        
        Args:
            config_loader: The unified config loader instance
            
        Returns:
            APCConfig object with merged configuration
        """
        try:
            # Get base configuration
            base_config = config_loader.get_agent_config('AffectiveProcessingCenter')
            
            # Build APC-specific configuration
            config_dict = {
                'app': {
                    'name': 'AffectiveProcessingCenter',
                    'version': '2.0.0'
                },
                'modules': base_config.get('modules', {
                    'enabled': [
                        'audio_emotion',
                        'text_emotion',
                        'face_emotion',
                        'context_fusion'
                    ]
                }),
                'cache': {
                    'redis_url': os.getenv('REDIS_URL', base_config.get('redis_url', 'redis://localhost:6379/0')),
                    'ttl_seconds': int(os.getenv('CACHE_TTL', base_config.get('cache_ttl', 3600))),
                    'max_size': int(os.getenv('CACHE_MAX_SIZE', base_config.get('cache_max_size', 1000)))
                },
                'zmq': {
                    'subscriber': {
                        'endpoints': base_config.get('zmq_endpoints', [
                            'tcp://localhost:5555',
                            'tcp://localhost:5556'
                        ])
                    },
                    'publisher': {
                        'bind_address': os.getenv('APC_PUB_ADDRESS', base_config.get('pub_address', 'tcp://*:5560'))
                    },
                    'synthesis_server': {
                        'bind_address': os.getenv('APC_SYNTH_ADDRESS', base_config.get('synth_address', 'tcp://*:5561'))
                    }
                },
                'pipeline': {
                    'batch_size': int(os.getenv('BATCH_SIZE', base_config.get('batch_size', 10))),
                    'timeout_seconds': int(os.getenv('PIPELINE_TIMEOUT', base_config.get('timeout', 30)))
                },
                'fusion': {
                    'weights': base_config.get('fusion_weights', {
                        'audio': 0.3,
                        'text': 0.4,
                        'face': 0.3
                    })
                }
            }
            
            return APCConfig(**config_dict)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Return default configuration
            return APCConfig()
    
    def _initialize_hub_components(self):
        """
        Initialize hub-specific components.
        
        Uses inherited features from BaseAgent:
        - self.health_checker (StandardizedHealthChecker)
        - self.unified_error_handler (UnifiedErrorHandler)
        - self.prometheus_exporter (PrometheusExporter)
        - self.logger (Rotating JSON logger)
        """
        try:
            # Register hub capabilities with service discovery
            self.capabilities = [
                'emotional_processing',
                'multimodal_fusion',
                'audio_emotion_analysis',
                'text_emotion_analysis',
                'face_emotion_analysis',
                'context_synthesis'
            ]
            
            # Register with digital twin (inherited from BaseAgent)
            self._register_with_digital_twin()
            
            self.logger.info("Hub components initialized successfully")
            
        except Exception as e:
            # Use inherited error handler
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='ERROR',
                    context={'component': 'AffectiveProcessingCenter', 'phase': 'initialization'}
                )
            self.logger.error(f"Failed to initialize hub components: {e}")
    
    async def initialize_components(self):
        """Initialize all APC components asynchronously."""
        self.logger.info("Initializing APC components...")
        
        try:
            # Initialize Redis cache
            self.cache = EmbeddingCache(
                redis_url=self.hub_config.cache.redis_url,
                ttl_seconds=self.hub_config.cache.ttl_seconds,
                max_size=self.hub_config.cache.max_size
            )
            await self.cache.connect()
            self.logger.info("✅ Redis cache connected")
            
            # Load and initialize modules
            self.modules = await self._load_modules()
            self.logger.info(f"✅ Loaded {len(self.modules)} processing modules")
            
            # Initialize fusion component
            self.fusion = create_fusion(
                config=self.hub_config.fusion,
                modules=self.modules
            )
            self.logger.info("✅ Fusion component initialized")
            
            # Create DAG executor
            self.dag_executor = DAGExecutor(
                modules=self.modules,
                fusion=self.fusion,
                cache=self.cache
            )
            self.logger.info("✅ DAG executor created")
            
            # Initialize ZMQ context
            self.zmq_context = zmq.asyncio.Context()
            
            # Set up input subscriber
            await self._setup_input_subscriber()
            
            # Set up output publisher
            await self._setup_output_publisher()
            
            # Set up synthesis server
            await self._setup_synthesis_server()
            
            self.logger.info("✅ All components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'AffectiveProcessingCenter', 'phase': 'component_init'}
                )
            raise
    
    async def _load_modules(self) -> Dict[str, Any]:
        """Load and initialize processing modules."""
        modules = {}
        
        for module_name in self.hub_config.modules.enabled:
            try:
                module_class = module_registry.get(module_name)
                if module_class:
                    module = module_class()
                    await module.initialize()
                    modules[module_name] = module
                    self.logger.info(f"  • Loaded module: {module_name}")
                else:
                    self.logger.warning(f"  ⚠ Module not found: {module_name}")
            except Exception as e:
                self.logger.error(f"  ✗ Failed to load module {module_name}: {e}")
        
        return modules
    
    async def _setup_input_subscriber(self):
        """Set up ZMQ subscriber for input data."""
        self.input_subscriber = self.zmq_context.socket(zmq.SUB)
        
        # Connect to all configured endpoints
        for endpoint in self.hub_config.zmq.subscriber.endpoints:
            self.input_subscriber.connect(endpoint)
            self.logger.info(f"  • Subscribed to: {endpoint}")
        
        # Subscribe to all topics
        self.input_subscriber.subscribe(b"")
    
    async def _setup_output_publisher(self):
        """Set up ZMQ publisher for output data."""
        self.publisher = ZmqPublisher(
            bind_address=self.hub_config.zmq.publisher.bind_address,
            context=self.zmq_context
        )
        await self.publisher.start()
        self.logger.info(f"  • Publisher bound to: {self.hub_config.zmq.publisher.bind_address}")
    
    async def _setup_synthesis_server(self):
        """Set up synthesis request server."""
        self.synthesis_handler = SynthesisRequestHandler(
            dag_executor=self.dag_executor,
            cache=self.cache
        )
        
        self.synthesis_server = ZmqSynthesisServer(
            handler=self.synthesis_handler,
            bind_address=self.hub_config.zmq.synthesis_server.bind_address,
            context=self.zmq_context
        )
        await self.synthesis_server.start()
        self.logger.info(f"  • Synthesis server bound to: {self.hub_config.zmq.synthesis_server.bind_address}")
    
    async def process_message(self, message: bytes):
        """
        Process an incoming message through the APC pipeline.
        
        Args:
            message: Raw message bytes from ZMQ
        """
        try:
            # Parse message
            data = json.loads(message.decode('utf-8'))
            
            # Create payload
            payload = Payload(
                timestamp=datetime.utcnow(),
                source=data.get('source', 'unknown'),
                data=data
            )
            
            # Process through DAG
            result = await self.dag_executor.execute(payload)
            
            # Publish result
            if self.publisher and result:
                await self.publisher.publish(
                    topic="emotional_context",
                    data=result.dict()
                )
            
            self._processed_messages += 1
            
            # Update metrics
            if self.prometheus_exporter:
                self.prometheus_exporter.record_request(
                    method='process',
                    endpoint='message',
                    status='success',
                    duration=0.0  # TODO: Add timing
                )
                
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Error processing message: {e}")
            
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='WARNING',
                    context={'component': 'AffectiveProcessingCenter', 'phase': 'message_processing'}
                )
            
            if self.prometheus_exporter:
                self.prometheus_exporter.record_error(
                    error_type='processing_error',
                    severity='warning'
                )
    
    async def run_processing_loop(self):
        """Main processing loop for incoming messages."""
        self.logger.info("Starting message processing loop...")
        
        while self.is_running:
            try:
                # Receive message with timeout
                if await self.input_subscriber.poll(timeout=100):
                    message = await self.input_subscriber.recv()
                    await self.process_message(message)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def start(self):
        """Start the Affective Processing Center service."""
        try:
            self.logger.info("🚀 Starting Affective Processing Center...")
            self._startup_time = datetime.utcnow()
            
            # Initialize components
            await self.initialize_components()
            
            # Update health status
            if self.health_checker:
                self.health_checker.set_healthy()
            
            self.is_running = True
            
            # Start processing loop
            asyncio.create_task(self.run_processing_loop())
            
            self.logger.info("✅ Affective Processing Center started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start APC: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'AffectiveProcessingCenter', 'phase': 'startup'}
                )
            raise
    
    async def stop(self):
        """Stop the Affective Processing Center service gracefully."""
        self.logger.info("🛑 Stopping Affective Processing Center...")
        self.is_running = False
        
        # Stop synthesis server
        if self.synthesis_server:
            await self.synthesis_server.stop()
        
        # Stop publisher
        if self.publisher:
            await self.publisher.stop()
        
        # Close subscriber
        if self.input_subscriber:
            self.input_subscriber.close()
        
        # Disconnect cache
        if self.cache:
            await self.cache.disconnect()
        
        # Cleanup modules
        for module in self.modules.values():
            if hasattr(module, 'cleanup'):
                await module.cleanup()
        
        # Close ZMQ context
        if self.zmq_context:
            self.zmq_context.term()
        
        # Update health status
        if self.health_checker:
            self.health_checker.set_unhealthy()
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Log statistics
        if self._startup_time:
            runtime = datetime.utcnow() - self._startup_time
            self.logger.info(f"📊 Statistics:")
            self.logger.info(f"  • Runtime: {runtime}")
            self.logger.info(f"  • Messages processed: {self._processed_messages}")
            self.logger.info(f"  • Errors: {self._error_count}")
        
        self.logger.info("✅ Affective Processing Center stopped successfully")
    
    async def run(self):
        """Run the Affective Processing Center service."""
        # Start the service
        await self.start()
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Stop the service
        await self.stop()


def main():
    """Main entry point for Affective Processing Center."""
    # Create and run the hub
    hub = AffectiveProcessingCenter(
        port=int(os.getenv('APC_PORT', 5560)),
        health_check_port=int(os.getenv('APC_HEALTH_PORT', 6560))
    )
    
    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        hub._shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the hub
        loop.run_until_complete(hub.run())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        # Cleanup
        loop.close()
        logger.info("AffectiveProcessingCenter shutdown complete")


if __name__ == "__main__":
    main()