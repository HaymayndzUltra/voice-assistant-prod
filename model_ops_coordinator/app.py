"""
Main application entry-point for ModelOps Coordinator.

This module provides the ModelOps Coordinator service that inherits from BaseAgent
and uses the approved golden utilities from the common directory.
"""

import asyncio
import signal
import sys
import os
from typing import Optional, Any
from datetime import datetime
from pathlib import Path

# Add common to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import BaseAgent and golden utilities
from common.core.base_agent import BaseAgent
from common.utils.unified_config_loader import UnifiedConfigLoader
from common.utils.path_manager import PathManager

# Import hub-specific modules
from core.kernel import Kernel
from core.errors import ConfigurationError, ModelOpsError
from transport.zmq_server import ZMQServer
from transport.grpc_server import GRPCServer
from transport.rest_api import RESTAPIServer


class ModelOpsCoordinator(BaseAgent):
    """
    ModelOps Coordinator - Central GPU resource management and model lifecycle hub.
    
    Inherits from BaseAgent to leverage standardized health checking,
    error handling, metrics, and configuration management.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize ModelOps Coordinator with BaseAgent foundation.
        
        Args:
            **kwargs: Arguments passed to BaseAgent
        """
        # Initialize BaseAgent with all standard features
        super().__init__(name='ModelOpsCoordinator', **kwargs)
        
        # Load hub-specific configuration using UnifiedConfigLoader
        config_loader = UnifiedConfigLoader()
        self.hub_config = self._load_hub_config(config_loader)
        
        # Core components
        self.kernel: Optional[Kernel] = None
        
        # Server instances
        self.zmq_server: Optional[ZMQServer] = None
        self.grpc_server: Optional[GRPCServer] = None
        self.rest_server: Optional[RESTAPIServer] = None
        
        # Application state
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._startup_time: Optional[datetime] = None
        
        # Initialize hub components
        self._initialize_hub_components()
        
        self.logger.info(f"ModelOpsCoordinator initialized on port {self.port}")
    
    def _load_hub_config(self, config_loader: UnifiedConfigLoader) -> Any:
        """
        Load hub-specific configuration using the golden UnifiedConfigLoader.
        
        Args:
            config_loader: The unified config loader instance
            
        Returns:
            Configuration object
        """
        try:
            # Get base configuration
            base_config = config_loader.get_agent_config('ModelOpsCoordinator')
            
            # Apply environment overrides
            config = {
                'server': {
                    'zmq_port': int(os.getenv('MOC_ZMQ_PORT', base_config.get('zmq_port', 7211))),
                    'grpc_port': int(os.getenv('MOC_GRPC_PORT', base_config.get('grpc_port', 7212))),
                    'rest_port': int(os.getenv('MOC_REST_PORT', base_config.get('rest_port', 8008))),
                    'max_workers': int(os.getenv('MOC_MAX_WORKERS', base_config.get('max_workers', 10)))
                },
                'resources': {
                    'gpu_poll_interval': int(os.getenv('GPU_POLL_INTERVAL', base_config.get('gpu_poll_interval', 5))),
                    'vram_soft_limit_mb': int(os.getenv('VRAM_SOFT_LIMIT_MB', base_config.get('vram_soft_limit_mb', 24000))),
                    'eviction_threshold_pct': int(os.getenv('EVICTION_THRESHOLD_PCT', base_config.get('eviction_threshold_pct', 90)))
                },
                'models': {
                    'preload': base_config.get('preload', []),
                    'default_dtype': os.getenv('DEFAULT_DTYPE', base_config.get('default_dtype', 'float16')),
                    'quantization': os.getenv('ENABLE_QUANTIZATION', base_config.get('quantization', 'true')).lower() == 'true'
                },
                'learning': {
                    'enable_auto_tune': os.getenv('ENABLE_AUTO_TUNE', base_config.get('enable_auto_tune', 'true')).lower() == 'true',
                    'max_parallel_jobs': int(os.getenv('MAX_PARALLEL_JOBS', base_config.get('max_parallel_jobs', 2))),
                    'job_store': os.getenv('JOB_STORE', base_config.get('job_store', 'learning_jobs.db'))
                },
                'goals': {
                    'policy': os.getenv('GOAL_POLICY', base_config.get('policy', 'priority_queue')),
                    'max_active_goals': int(os.getenv('MAX_ACTIVE_GOALS', base_config.get('max_active_goals', 5)))
                },
                'resilience': {
                    'circuit_breaker': base_config.get('circuit_breaker', {}),
                    'bulkhead': base_config.get('bulkhead', {})
                }
            }
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Return minimal default configuration
            return {
                'server': {'zmq_port': 7211, 'grpc_port': 7212, 'rest_port': 8008, 'max_workers': 10},
                'resources': {'gpu_poll_interval': 5, 'vram_soft_limit_mb': 24000, 'eviction_threshold_pct': 90},
                'models': {'preload': [], 'default_dtype': 'float16', 'quantization': True},
                'learning': {'enable_auto_tune': True, 'max_parallel_jobs': 2, 'job_store': 'learning_jobs.db'},
                'goals': {'policy': 'priority_queue', 'max_active_goals': 5},
                'resilience': {'circuit_breaker': {}, 'bulkhead': {}}
            }
    
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
                'gpu_management',
                'model_lifecycle',
                'inference_routing',
                'learning_orchestration',
                'goal_management',
                'vram_optimization',
                'gpu_lease_api'
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
                    context={'component': 'ModelOpsCoordinator', 'phase': 'initialization'}
                )
            self.logger.error(f"Failed to initialize hub components: {e}")
    
    async def start(self):
        """
        Start the ModelOps Coordinator service.
        """
        try:
            self.logger.info("Starting ModelOpsCoordinator...")
            self._startup_time = datetime.utcnow()
            
            # Initialize kernel with configuration
            await self._initialize_kernel()
            
            # Start servers concurrently
            await self._start_servers()
            
            # Update health status
            if self.health_checker:
                self.health_checker.set_healthy()
            
            self._running = True
            self.logger.info("✅ ModelOpsCoordinator started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start ModelOpsCoordinator: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'ModelOpsCoordinator', 'phase': 'startup'}
                )
            raise
    
    async def _initialize_kernel(self):
        """Initialize the kernel with all modules."""
        try:
            # Convert config dict to the format expected by Kernel
            from core.schemas import Config
            kernel_config = Config(
                server=self.hub_config['server'],
                resources=self.hub_config['resources'],
                models=self.hub_config['models'],
                learning=self.hub_config['learning'],
                goals=self.hub_config['goals'],
                resilience=self.hub_config['resilience']
            )
            
            self.kernel = Kernel(kernel_config)
            await self.kernel.initialize()
            self.logger.info("✅ Kernel initialized successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize kernel: {e}")
            raise ModelOpsError(f"Kernel initialization failed: {e}")
    
    async def _start_servers(self):
        """Start all transport servers concurrently."""
        try:
            server_tasks = []
            
            # Start ZMQ server
            if self.hub_config['server'].get('zmq_port'):
                self.zmq_server = ZMQServer(
                    self.kernel,
                    port=self.hub_config['server']['zmq_port']
                )
                server_tasks.append(asyncio.create_task(
                    self.zmq_server.start(),
                    name="zmq-server"
                ))
                self.logger.info(f"🚀 Starting ZMQ server on port {self.hub_config['server']['zmq_port']}")
            
            # Start gRPC server
            if self.hub_config['server'].get('grpc_port'):
                self.grpc_server = GRPCServer(
                    self.kernel,
                    port=self.hub_config['server']['grpc_port'],
                    max_workers=self.hub_config['server']['max_workers']
                )
                server_tasks.append(asyncio.create_task(
                    self.grpc_server.start(),
                    name="grpc-server"
                ))
                self.logger.info(f"🚀 Starting gRPC server on port {self.hub_config['server']['grpc_port']}")
            
            # Start REST API server
            if self.hub_config['server'].get('rest_port'):
                self.rest_server = RESTAPIServer(
                    self.kernel,
                    host="0.0.0.0",
                    port=self.hub_config['server']['rest_port']
                )
                server_tasks.append(asyncio.create_task(
                    self.rest_server.start(),
                    name="rest-server"
                ))
                self.logger.info(f"🚀 Starting REST API server on port {self.hub_config['server']['rest_port']}")
            
            # Wait for all servers to start
            if server_tasks:
                await asyncio.gather(*server_tasks)
            
            self.logger.info("✅ All servers started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start servers: {e}")
            raise
    
    async def stop(self):
        """
        Stop the ModelOps Coordinator service gracefully.
        """
        if not self._running:
            return
        
        self.logger.info("🛑 Stopping ModelOpsCoordinator...")
        self._running = False
        
        # Stop servers
        stop_tasks = []
        
        if self.zmq_server:
            stop_tasks.append(self.zmq_server.stop())
        
        if self.grpc_server:
            stop_tasks.append(self.grpc_server.stop())
        
        if self.rest_server:
            stop_tasks.append(self.rest_server.stop())
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Shutdown kernel
        if self.kernel:
            await self.kernel.shutdown()
        
        # Update health status
        if self.health_checker:
            self.health_checker.set_unhealthy()
        
        # Set shutdown event
        self._shutdown_event.set()
        
        # Log runtime
        if self._startup_time:
            runtime = datetime.utcnow() - self._startup_time
            self.logger.info(f"⏱️ ModelOpsCoordinator ran for {runtime}")
        
        self.logger.info("✅ ModelOpsCoordinator stopped successfully")
    
    async def run(self):
        """
        Run the ModelOps Coordinator service.
        """
        # Start the service
        await self.start()
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Stop the service
        await self.stop()


def main():
    """
    Main entry point for ModelOps Coordinator.
    """
    # Create and run the hub
    hub = ModelOpsCoordinator(
        port=int(os.getenv('MOC_PORT', 7212)),
        health_check_port=int(os.getenv('MOC_HEALTH_PORT', 8212))
    )
    
    # Setup signal handlers
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}, initiating graceful shutdown...")
        hub._shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows compatibility
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)
    
    try:
        # Run the hub
        loop.run_until_complete(hub.run())
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    finally:
        # Cleanup
        loop.close()
        print("ModelOpsCoordinator shutdown complete")


if __name__ == "__main__":
    main()