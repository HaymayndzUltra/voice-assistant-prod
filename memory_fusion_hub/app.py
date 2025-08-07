"""
Main application entry point for Memory Fusion Hub.

This module provides:
- Configuration loading with YAML merging and environment variables
- Service initialization and lifecycle management
- Prometheus metrics HTTP endpoint
- Async ZMQ and gRPC server startup
- Graceful shutdown handling for SIGTERM/SIGINT
"""

import asyncio
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

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


class UnifiedConfigLoader:
    """
    Configuration loader that merges default.yaml, host-specific overrides,
    and environment variables into a unified configuration.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.hostname = os.uname().nodename
        
    def load_config(self) -> FusionConfig:
        """
        Load and merge configuration from multiple sources.
        
        Returns:
            Unified FusionConfig instance
        """
        try:
            # Load default configuration
            default_config = self._load_yaml_file("default.yaml")
            logger.info("Loaded default configuration")
            
            # Try to load host-specific configuration
            host_config = {}
            host_files = [
                f"{self.hostname}.yaml",
                "main_pc.yaml" if "main" in self.hostname.lower() else None,
                "pc2.yaml" if "pc2" in self.hostname.lower() else None
            ]
            
            for host_file in host_files:
                if host_file:
                    try:
                        host_config.update(self._load_yaml_file(host_file))
                        logger.info(f"Loaded host-specific config: {host_file}")
                        break
                    except FileNotFoundError:
                        logger.debug(f"Host config not found: {host_file}")
                        continue
            
            # Merge configurations
            merged_config = self._deep_merge(default_config, host_config)
            
            # Apply environment variable overrides
            final_config = self._apply_env_overrides(merged_config)
            
            # Create and validate FusionConfig
            config = FusionConfig(**final_config)
            logger.info("Configuration loaded and validated successfully")
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_yaml_file(self, filename: str) -> dict:
        """Load YAML file with environment variable substitution."""
        filepath = os.path.join(self.config_dir, filename)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Simple environment variable substitution
        content = self._substitute_env_vars(content)
        
        return yaml.safe_load(content)
    
    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in YAML content.
        
        Supports format: ${VAR_NAME:default_value}
        """
        import re
        
        def replace_env_var(match):
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
            else:
                var_name, default_value = var_expr, ''
            
            return os.environ.get(var_name, default_value)
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, content)
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: dict) -> dict:
        """Apply environment variable overrides to config."""
        env_mappings = {
            'MFH_ZMQ_PORT': ['server', 'zmq_port'],
            'MFH_GRPC_PORT': ['server', 'grpc_port'],
            'MFH_MAX_WORKERS': ['server', 'max_workers'],
            'MFH_SQLITE': ['storage', 'sqlite_path'],
            'POSTGRES_URL': ['storage', 'postgres_url'],
            'REDIS_URL': ['storage', 'redis_url'],
            'NATS_URL': ['replication', 'nats_url'],
            'MFH_LOG_LEVEL': None  # Special case
        }
        
        result = config.copy()
        
        for env_var, config_path in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                if env_var == 'MFH_LOG_LEVEL':
                    # Set logging level
                    logging.getLogger().setLevel(getattr(logging, value.upper(), logging.INFO))
                    continue
                
                if config_path:
                    # Set nested config value
                    current = result
                    for key in config_path[:-1]:
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                    
                    # Type conversion
                    if 'port' in config_path[-1] or 'workers' in config_path[-1]:
                        value = int(value)
                    
                    current[config_path[-1]] = value
                    logger.info(f"Applied env override: {env_var} = {value}")
        
        return result


class MemoryFusionHubApp:
    """
    Main application class for Memory Fusion Hub.
    
    Handles service lifecycle, server management, and graceful shutdown.
    """
    
    def __init__(self):
        """Initialize the application."""
        self.config: Optional[FusionConfig] = None
        self.fusion_service: Optional[FusionService] = None
        self.zmq_task: Optional[asyncio.Task] = None
        self.grpc_task: Optional[asyncio.Task] = None
        self.prometheus_server = None
        self.executor: Optional[ThreadPoolExecutor] = None
        self.shutdown_event = asyncio.Event()
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("Memory Fusion Hub application initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating graceful shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def startup(self):
        """
        Application startup sequence.
        
        1. Load configuration
        2. Initialize FusionService
        3. Start Prometheus metrics server
        4. Launch transport servers
        """
        try:
            logger.info("Starting Memory Fusion Hub...")
            
            # Step 1: Load configuration
            config_loader = UnifiedConfigLoader()
            self.config = config_loader.load_config()
            logger.info(f"Configuration loaded for {self.config.title} v{self.config.version}")
            
            # Step 2: Initialize FusionService
            self.fusion_service = create_fusion_service(self.config)
            await self.fusion_service.initialize()
            logger.info("FusionService initialized successfully")
            
            # Step 3: Start Prometheus metrics server
            prometheus_port = int(os.environ.get('MFH_METRICS_PORT', '8080'))
            self.prometheus_server = start_http_server(prometheus_port)
            logger.info(f"Prometheus metrics server started on port {prometheus_port}")
            
            # Step 4: Create thread pool executor
            self.executor = ThreadPoolExecutor(
                max_workers=self.config.server.max_workers,
                thread_name_prefix="mfh-worker"
            )
            logger.info(f"Thread pool executor created with {self.config.server.max_workers} workers")
            
            # Step 5: Launch transport servers asynchronously
            await self._start_transport_servers()
            
            logger.info("Memory Fusion Hub startup complete")
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            await self.shutdown()
            raise
    
    async def _start_transport_servers(self):
        """Start ZMQ and gRPC transport servers."""
        try:
            # Start ZMQ server
            self.zmq_task = asyncio.create_task(
                run_zmq_server(self.fusion_service, self.config.server.zmq_port),
                name="zmq-server"
            )
            logger.info(f"ZMQ server task created for port {self.config.server.zmq_port}")
            
            # Start gRPC server
            self.grpc_task = asyncio.create_task(
                run_grpc_server(
                    self.fusion_service, 
                    self.config.server.grpc_port,
                    self.config.server.max_workers
                ),
                name="grpc-server"
            )
            logger.info(f"gRPC server task created for port {self.config.server.grpc_port}")
            
            # Give servers a moment to start
            await asyncio.sleep(0.5)
            
            # Check if servers started successfully
            if self.zmq_task.done():
                exception = self.zmq_task.exception()
                if exception:
                    logger.error(f"ZMQ server failed to start: {exception}")
                    raise exception
            
            if self.grpc_task.done():
                exception = self.grpc_task.exception()
                if exception:
                    logger.error(f"gRPC server failed to start: {exception}")
                    raise exception
            
            logger.info("Transport servers started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start transport servers: {e}")
            raise
    
    async def run(self):
        """
        Main application run loop.
        
        Starts the application and waits for shutdown signal.
        """
        try:
            await self.startup()
            
            # Wait for shutdown signal
            logger.info("Memory Fusion Hub is running. Press Ctrl+C to stop.")
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """
        Graceful shutdown sequence.
        
        1. Stop accepting new requests
        2. Finish processing current requests
        3. Close service components
        4. Clean up resources
        """
        try:
            logger.info("Initiating graceful shutdown...")
            
            # Stop transport servers
            if self.zmq_task and not self.zmq_task.done():
                logger.info("Stopping ZMQ server...")
                self.zmq_task.cancel()
                try:
                    await asyncio.wait_for(self.zmq_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.warning("ZMQ server shutdown timeout")
            
            if self.grpc_task and not self.grpc_task.done():
                logger.info("Stopping gRPC server...")
                self.grpc_task.cancel()
                try:
                    await asyncio.wait_for(self.grpc_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.warning("gRPC server shutdown timeout")
            
            # Close FusionService
            if self.fusion_service:
                logger.info("Closing FusionService...")
                await self.fusion_service.close()
                logger.info("FusionService closed")
            
            # Shutdown thread pool executor
            if self.executor:
                logger.info("Shutting down thread pool executor...")
                self.executor.shutdown(wait=True)
                logger.info("Thread pool executor shutdown complete")
            
            # Stop Prometheus server (this is synchronous)
            if self.prometheus_server:
                logger.info("Stopping Prometheus metrics server...")
                # Note: prometheus_client doesn't have a clean shutdown method
                # The server will stop when the process exits
            
            logger.info("Graceful shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point."""
    # Use uvloop for better performance (Unix only)
    if uvloop is not None and hasattr(uvloop, 'install'):
        try:
            uvloop.install()
            logger.info("Using uvloop for enhanced performance")
        except Exception as e:
            logger.warning(f"Failed to install uvloop: {e}")
            logger.info("Using default event loop")
    else:
        logger.info("uvloop not available, using default event loop")
    
    # Create and run application
    app = MemoryFusionHubApp()
    await app.run()


if __name__ == "__main__":
    # Change to the directory containing the config files
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)