"""
Main application entry point for Memory Fusion Hub.

This module provides the Memory Fusion Hub service that inherits from BaseAgent
and uses the approved golden utilities from the common directory.
"""

import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from pathlib import Path

# Add common to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import BaseAgent and golden utilities
from common.core.base_agent import BaseAgent
from common.utils.unified_config_loader import UnifiedConfigLoader
from common.utils.path_manager import PathManager

try:
    import uvloop  # High-performance event loop
except ImportError:
    uvloop = None

import yaml
from prometheus_client import start_http_server

from .core.models import FusionConfig
from .core.fusion_service import FusionService, create_fusion_service
from .transport.zmq_server import run_zmq_server
from .transport.grpc_server import run_grpc_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/workspace/memory_fusion_hub.log')
    ]
)

logger = logging.getLogger(__name__)


class MemoryFusionHub(BaseAgent):
    """
    Memory Fusion Hub - A consolidated memory management service.
    
    Inherits from BaseAgent to leverage standardized health checking,
    error handling, metrics, and configuration management.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize Memory Fusion Hub with BaseAgent foundation.
        
        Args:
            **kwargs: Arguments passed to BaseAgent
        """
        # Initialize BaseAgent with all standard features
        super().__init__(name='MemoryFusionHub', **kwargs)
        
        # Load hub-specific configuration using UnifiedConfigLoader
        config_loader = UnifiedConfigLoader()
        self.hub_config = self._load_hub_config(config_loader)
        
        # Initialize fusion service
        self.fusion_service: Optional[FusionService] = None
        self.zmq_task: Optional[asyncio.Task] = None
        self.grpc_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Initialize hub components
        self._initialize_hub_components()
        
        logger.info(f"MemoryFusionHub initialized on port {self.port}")
    
    def _load_hub_config(self, config_loader: UnifiedConfigLoader) -> FusionConfig:
        """
        Load hub-specific configuration using the golden UnifiedConfigLoader.
        
        Args:
            config_loader: The unified config loader instance
            
        Returns:
            FusionConfig object with merged configuration
        """
        try:
            # Get base configuration
            base_config = config_loader.get_agent_config('MemoryFusionHub')
            
            # Load additional config from environment
            config_dict = {
                'server': {
                    'zmq_port': int(os.getenv('MFH_ZMQ_PORT', base_config.get('zmq_port', 5713))),
                    'grpc_port': int(os.getenv('MFH_GRPC_PORT', base_config.get('grpc_port', 5714))),
                    'metrics_port': int(os.getenv('MFH_METRICS_PORT', base_config.get('metrics_port', 8080)))
                },
                'storage': {
                    'redis_url': os.getenv('REDIS_URL', base_config.get('redis_url', 'redis://localhost:6379/0')),
                    'postgres_url': os.getenv('POSTGRES_URL', base_config.get('postgres_url', '')),
                    'sqlite_path': os.getenv('SQLITE_PATH', base_config.get('sqlite_path', '/workspace/memory.db'))
                },
                'replication': {
                    'enabled': os.getenv('REPLICATION_ENABLED', 'false').lower() == 'true',
                    'role': os.getenv('REPLICATION_ROLE', 'primary'),
                    'sync_interval': int(os.getenv('REPLICATION_SYNC_INTERVAL', '60'))
                },
                'resilience': {
                    'circuit_breaker': {
                        'failure_threshold': int(os.getenv('CB_FAILURE_THRESHOLD', '5')),
                        'timeout': int(os.getenv('CB_TIMEOUT', '60'))
                    },
                    'bulkhead': {
                        'max_concurrent': int(os.getenv('BH_MAX_CONCURRENT', '10')),
                        'queue_size': int(os.getenv('BH_QUEUE_SIZE', '100'))
                    }
                }
            }
            
            return FusionConfig(**config_dict)
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Use default configuration as fallback
            return FusionConfig()
    
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
                'memory_management',
                'key_value_storage',
                'session_management',
                'knowledge_storage',
                'event_sourcing',
                'caching'
            ]
            
            # Register with digital twin (inherited from BaseAgent)
            self._register_with_digital_twin()
            
            logger.info("Hub components initialized successfully")
            
        except Exception as e:
            # Use inherited error handler
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='ERROR',
                    context={'component': 'MemoryFusionHub', 'phase': 'initialization'}
                )
            logger.error(f"Failed to initialize hub components: {e}")
    
    async def start(self):
        """
        Start the Memory Fusion Hub service.
        """
        try:
            logger.info("Starting MemoryFusionHub service...")
            
            # Create fusion service
            self.fusion_service = await create_fusion_service(self.hub_config)
            
            # Start Prometheus metrics server (using inherited exporter)
            if self.prometheus_exporter:
                start_http_server(self.hub_config.server.metrics_port)
                logger.info(f"Prometheus metrics available at :{self.hub_config.server.metrics_port}/metrics")
            
            # Start ZMQ server
            self.zmq_task = asyncio.create_task(
                run_zmq_server(self.fusion_service, self.hub_config.server.zmq_port)
            )
            logger.info(f"ZMQ server started on port {self.hub_config.server.zmq_port}")
            
            # Start gRPC server
            self.grpc_task = asyncio.create_task(
                run_grpc_server(self.fusion_service, self.hub_config.server.grpc_port)
            )
            logger.info(f"gRPC server started on port {self.hub_config.server.grpc_port}")
            
            # Update health status
            if self.health_checker:
                self.health_checker.set_healthy()
            
            logger.info("MemoryFusionHub service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'MemoryFusionHub', 'phase': 'startup'}
                )
            raise
    
    async def stop(self):
        """
        Stop the Memory Fusion Hub service gracefully.
        """
        logger.info("Stopping MemoryFusionHub service...")
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Cancel server tasks
        if self.zmq_task:
            self.zmq_task.cancel()
            try:
                await self.zmq_task
            except asyncio.CancelledError:
                pass
        
        if self.grpc_task:
            self.grpc_task.cancel()
            try:
                await self.grpc_task
            except asyncio.CancelledError:
                pass
        
        # Stop fusion service
        if self.fusion_service:
            await self.fusion_service.stop()
        
        # Update health status
        if self.health_checker:
            self.health_checker.set_unhealthy()
        
        logger.info("MemoryFusionHub service stopped")
    
    async def run(self):
        """
        Run the Memory Fusion Hub service.
        """
        # Start the service
        await self.start()
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Stop the service
        await self.stop()


def main():
    """
    Main entry point for Memory Fusion Hub.
    """
    # Configure uvloop if available for better performance
    if uvloop:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop for enhanced async performance")
    
    # Create and run the hub
    hub = MemoryFusionHub(
        port=int(os.getenv('MFH_PORT', 5713)),
        health_check_port=int(os.getenv('MFH_HEALTH_PORT', 6713))
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
        logger.info("MemoryFusionHub shutdown complete")


if __name__ == "__main__":
    main()