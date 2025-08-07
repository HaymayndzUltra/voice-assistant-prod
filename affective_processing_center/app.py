#!/usr/bin/env python3
"""
Affective Processing Center (APC) - Main Application Bootstrap

This is the main entry point for the APC service that unifies emotional
processing modules into a DAG-based pipeline for real-time emotional
context analysis and synthesis.
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

# Adjust Python path for internal imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import APC core components
from core.cache import EmbeddingCache
from core.dag_executor import DAGExecutor
from core.fusion import create_fusion
from core.schemas import APCConfig, AudioChunk, Transcript, Payload, EmotionalContext
from modules.base import module_registry
from transport.zmq_pub import ZmqPublisher, BroadcastManager
from transport.zmq_req import ZmqSynthesisServer, SynthesisRequestHandler

# Configuration loading with fallback
import yaml

def load_unified_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration with fallback to direct YAML loading."""
    try:
        # Try to import common config manager if available
        sys.path.insert(0, os.path.join(os.path.dirname(current_dir), 'common'))
        from config_manager import load_unified_config as _load_unified_config
        return _load_unified_config(config_path)
    except ImportError:
        # Fallback to direct YAML loading
        config_path = config_path or "config/default.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}

# ZMQ for input subscription
import zmq
import zmq.asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APCApplication:
    """
    Main Affective Processing Center application.
    
    This class orchestrates the entire APC pipeline including:
    - Configuration loading and validation
    - Component initialization (cache, modules, fusion, DAG)
    - Input subscription and processing loop
    - Output publishing and synthesis services
    - Graceful shutdown handling
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the APC application.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or "affective_processing_center/config/default.yaml"
        self.config: Optional[APCConfig] = None
        
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
        self.is_initialized = False
        self.startup_time = datetime.utcnow()
        
        # Statistics
        self.stats = {
            'messages_processed': 0,
            'ecvs_published': 0,
            'synthesis_requests': 0,
            'processing_errors': 0,
            'avg_processing_time_ms': 0.0,
            'startup_time': self.startup_time
        }
        
        # Async tasks
        self._main_loop_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(f"APC Application initialized with config: {self.config_path}")
    
    async def initialize(self) -> None:
        """Initialize all APC components in the correct order."""
        if self.is_initialized:
            logger.warning("APC already initialized")
            return
        
        try:
            logger.info("🚀 Starting APC initialization...")
            
            # Step 1: Load and validate configuration
            await self._load_configuration()
            
            # Step 2: Initialize embedding cache
            await self._initialize_cache()
            
            # Step 3: Load and initialize modules
            await self._initialize_modules()
            
            # Step 4: Initialize fusion layer
            await self._initialize_fusion()
            
            # Step 5: Initialize DAG executor
            await self._initialize_dag_executor()
            
            # Step 6: Initialize transport layer
            await self._initialize_transport()
            
            # Step 7: Setup input subscription
            await self._initialize_input_subscriber()
            
            # Step 8: Warmup all components
            await self._warmup_components()
            
            self.is_initialized = True
            
            initialization_time = (datetime.utcnow() - self.startup_time).total_seconds()
            logger.info(f"✅ APC initialization complete in {initialization_time:.2f}s")
            
        except Exception as e:
            logger.error(f"❌ APC initialization failed: {e}")
            await self.cleanup()
            raise
    
    async def _load_configuration(self) -> None:
        """Load and validate application configuration."""
        logger.info("📋 Loading configuration...")
        
        try:
            # Load unified config
            raw_config = load_unified_config(self.config_path)
            
            if not raw_config:
                # Fallback to direct YAML loading
                if os.path.exists(self.config_path):
                    import yaml
                    with open(self.config_path, 'r') as f:
                        raw_config = yaml.safe_load(f)
                else:
                    raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            # Validate configuration using Pydantic
            self.config = APCConfig(**raw_config)
            
            logger.info(f"✅ Configuration loaded: {len(self.config.pipeline.enabled_modules)} modules enabled")
            logger.info(f"   Fusion algorithm: {self.config.pipeline.fusion.algorithm}")
            logger.info(f"   Device: {self.config.resources.device}")
            
        except Exception as e:
            logger.error(f"❌ Configuration loading failed: {e}")
            raise
    
    async def _initialize_cache(self) -> None:
        """Initialize the embedding cache."""
        logger.info("💾 Initializing embedding cache...")
        
        # Cache configuration from config or defaults
        cache_config = getattr(self.config, 'cache', {})
        max_size = cache_config.get('max_size', 1000)
        ttl_minutes = cache_config.get('ttl_minutes', 60)
        
        self.cache = EmbeddingCache(
            max_size=max_size,
            ttl_minutes=ttl_minutes,
            auto_cleanup_interval=300
        )
        
        logger.info(f"✅ Cache initialized: max_size={max_size}, ttl={ttl_minutes}min")
    
    async def _initialize_modules(self) -> None:
        """Load and initialize emotion processing modules."""
        logger.info("🧠 Initializing processing modules...")
        
        enabled_modules = self.config.pipeline.enabled_modules
        device = self.config.resources.device
        
        for module_name in enabled_modules:
            try:
                # Get module configuration
                module_config = self.config.models.dict().get(module_name, {})
                
                # Create module instance
                module_instance = module_registry.create_instance(
                    module_name, 
                    module_config, 
                    device
                )
                
                self.modules[module_name] = module_instance
                logger.info(f"   ✅ {module_name} module loaded")
                
            except Exception as e:
                logger.error(f"   ❌ Failed to load {module_name} module: {e}")
                raise
        
        logger.info(f"✅ {len(self.modules)} modules initialized")
    
    async def _initialize_fusion(self) -> None:
        """Initialize the fusion layer."""
        logger.info("🔀 Initializing fusion layer...")
        
        fusion_config = self.config.pipeline.fusion.dict()
        self.fusion = create_fusion(fusion_config)
        
        logger.info(f"✅ Fusion layer initialized: {fusion_config['algorithm']}")
    
    async def _initialize_dag_executor(self) -> None:
        """Initialize the DAG executor."""
        logger.info("📊 Initializing DAG executor...")
        
        max_concurrent = self.config.resources.max_concurrent_gpu_tasks
        
        self.dag_executor = DAGExecutor(
            modules=self.modules,
            fusion=self.fusion,
            cache=self.cache,
            max_concurrent=max_concurrent
        )
        
        # Get execution order for logging
        execution_order = self.dag_executor.get_execution_order()
        logger.info(f"✅ DAG executor initialized with execution order: {execution_order}")
    
    async def _initialize_transport(self) -> None:
        """Initialize transport layer components."""
        logger.info("🚀 Initializing transport layer...")
        
        # Initialize ZMQ context
        self.zmq_context = zmq.asyncio.Context()
        
        # Initialize ECV publisher
        pub_port = self.config.output.zmq_pub_port
        topic = self.config.output.topic
        
        self.publisher = ZmqPublisher(
            port=pub_port,
            topic=topic,
            bind_address="tcp://*"
        )
        await self.publisher.start()
        
        # Initialize synthesis server
        synthesis_port = getattr(self.config.output, 'synthesis_port', 5706)
        self.synthesis_server = ZmqSynthesisServer(port=synthesis_port)
        
        # Create synthesis handler using synthesis module
        if 'synthesis' in self.modules:
            self.synthesis_handler = SynthesisRequestHandler(self.modules['synthesis'])
            self.synthesis_server.set_synthesis_handler(self.synthesis_handler.handle_request)
        
        await self.synthesis_server.start()
        
        logger.info(f"✅ Transport layer initialized: pub={pub_port}, synthesis={synthesis_port}")
    
    async def _initialize_input_subscriber(self) -> None:
        """Initialize ZMQ subscriber for input data."""
        logger.info("📡 Initializing input subscriber...")
        
        # Create subscriber socket
        self.input_subscriber = self.zmq_context.socket(zmq.SUB)
        
        # Subscribe to relevant topics (e.g., from RTAP)
        input_port = getattr(self.config, 'input_port', 6553)
        input_topics = getattr(self.config, 'input_topics', ['transcript', 'audio'])
        
        # Connect to input source
        input_address = f"tcp://localhost:{input_port}"
        self.input_subscriber.connect(input_address)
        
        # Subscribe to topics
        for topic in input_topics:
            self.input_subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
        
        # Set receive timeout
        self.input_subscriber.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
        
        logger.info(f"✅ Input subscriber initialized: {input_address}, topics={input_topics}")
    
    async def _warmup_components(self) -> None:
        """Warmup all components for optimal performance."""
        logger.info("🔥 Warming up components...")
        
        # Warmup DAG executor and modules
        await self.dag_executor.warmup_modules()
        
        # Test publisher connection
        await self.publisher.test_connection()
        
        # Test synthesis server
        if self.synthesis_server.synthesis_handler:
            test_result = await self.synthesis_server.test_synthesis()
            if test_result['success']:
                logger.info(f"   ✅ Synthesis test: {test_result['processing_time_ms']:.1f}ms")
        
        logger.info("✅ Component warmup complete")
    
    async def start(self) -> None:
        """Start the main APC processing loop."""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_running:
            logger.warning("APC already running")
            return
        
        self.is_running = True
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Start main processing loop
        self._main_loop_task = asyncio.create_task(self._main_processing_loop())
        
        logger.info("🎯 APC main processing loop started")
        
        try:
            # Wait for shutdown signal
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            await self.stop()
    
    async def _main_processing_loop(self) -> None:
        """Main processing loop that handles input and publishes results."""
        logger.info("🔄 Main processing loop active")
        
        processing_times = []
        
        while self.is_running:
            try:
                # Receive input with timeout
                try:
                    topic_data = await self.input_subscriber.recv_multipart()
                    
                    if len(topic_data) >= 2:
                        topic = topic_data[0].decode('utf-8')
                        message_data = topic_data[1].decode('utf-8')
                    else:
                        continue
                        
                except zmq.Again:
                    # Timeout - publish heartbeat and continue
                    await self.publisher.publish_heartbeat()
                    continue
                
                # Parse input payload
                payload = await self._parse_input_payload(topic, message_data)
                if not payload:
                    continue
                
                # Process through DAG
                start_time = time.time()
                
                try:
                    emotional_context = await self.dag_executor.run(payload)
                    processing_time = (time.time() - start_time) * 1000
                    
                    # Update processing time for emotional context
                    emotional_context.processing_latency_ms = processing_time
                    
                    # Publish ECV
                    success = await self.publisher.publish_ecv(emotional_context)
                    
                    if success:
                        # Update statistics
                        self.stats['messages_processed'] += 1
                        self.stats['ecvs_published'] += 1
                        
                        processing_times.append(processing_time)
                        if len(processing_times) > 100:
                            processing_times = processing_times[-100:]
                        
                        self.stats['avg_processing_time_ms'] = sum(processing_times) / len(processing_times)
                        
                        logger.debug(f"Processed ECV: {emotional_context.primary_emotion.value} "
                                   f"({processing_time:.1f}ms)")
                    else:
                        self.stats['processing_errors'] += 1
                        logger.warning("Failed to publish ECV")
                        
                except Exception as e:
                    self.stats['processing_errors'] += 1
                    logger.error(f"DAG processing error: {e}")
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(0.1)
        
        logger.info("Main processing loop stopped")
    
    async def _parse_input_payload(self, topic: str, message_data: str) -> Optional[Payload]:
        """Parse input message into a Payload object."""
        try:
            data = json.loads(message_data)
            
            if topic == 'transcript' or 'text' in data:
                return Transcript(
                    text=data.get('text', ''),
                    confidence=data.get('confidence', 1.0),
                    timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat())),
                    speaker_id=data.get('speaker_id'),
                    language=data.get('language', 'en')
                )
            elif topic == 'audio' or 'audio_data' in data:
                return AudioChunk(
                    audio_data=bytes.fromhex(data.get('audio_data', '')),
                    sample_rate=data.get('sample_rate', 16000),
                    timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat())),
                    duration_ms=data.get('duration_ms', 0),
                    speaker_id=data.get('speaker_id')
                )
            else:
                logger.warning(f"Unknown payload type for topic {topic}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to parse payload: {e}")
            return None
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self._trigger_shutdown())
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def _trigger_shutdown(self) -> None:
        """Trigger graceful shutdown."""
        self._shutdown_event.set()
    
    async def stop(self) -> None:
        """Stop the APC application gracefully."""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping APC application...")
        
        self.is_running = False
        
        # Cancel main loop task
        if self._main_loop_task:
            self._main_loop_task.cancel()
            try:
                await self._main_loop_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup components
        await self.cleanup()
        
        uptime = (datetime.utcnow() - self.startup_time).total_seconds()
        logger.info(f"✅ APC stopped gracefully after {uptime:.1f}s uptime")
    
    async def cleanup(self) -> None:
        """Cleanup all resources."""
        logger.info("🧹 Cleaning up resources...")
        
        try:
            # Stop transport components
            if self.synthesis_server:
                await self.synthesis_server.stop()
            
            if self.publisher:
                await self.publisher.stop()
            
            # Close input subscriber
            if self.input_subscriber:
                self.input_subscriber.close()
            
            # Shutdown DAG executor
            if self.dag_executor:
                await self.dag_executor.shutdown_modules()
            
            # Close ZMQ context
            if self.zmq_context:
                self.zmq_context.term()
            
            logger.info("✅ Cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get application statistics."""
        uptime = (datetime.utcnow() - self.startup_time).total_seconds()
        
        stats = self.stats.copy()
        stats.update({
            'uptime_seconds': uptime,
            'is_running': self.is_running,
            'is_initialized': self.is_initialized,
            'modules_loaded': len(self.modules),
            'dag_stats': self.dag_executor.get_stats() if self.dag_executor else {},
            'cache_stats': self.cache.get_stats() if self.cache else {},
            'publisher_stats': self.publisher.get_stats() if self.publisher else {},
            'synthesis_stats': self.synthesis_server.get_stats() if self.synthesis_server else {}
        })
        
        return stats
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get application health status."""
        is_healthy = (
            self.is_running and 
            self.is_initialized and
            self.dag_executor is not None and
            self.publisher is not None
        )
        
        return {
            'status': 'healthy' if is_healthy else 'degraded',
            'is_running': self.is_running,
            'is_initialized': self.is_initialized,
            'components': {
                'dag_executor': self.dag_executor is not None,
                'cache': self.cache is not None,
                'publisher': self.publisher is not None,
                'synthesis_server': self.synthesis_server is not None,
                'modules': len(self.modules)
            },
            'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds()
        }


async def main():
    """Main entry point for the APC application."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Affective Processing Center')
    parser.add_argument('--config', '-c', 
                       help='Configuration file path',
                       default='config/default.yaml')
    parser.add_argument('--log-level', '-l',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO',
                       help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start APC application
    app = APCApplication(config_path=args.config)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))