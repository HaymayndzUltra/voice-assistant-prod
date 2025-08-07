"""Main application entry-point for ModelOps Coordinator."""

import asyncio
import signal
import sys
import time
from typing import Optional, Any
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.loader import load_config  # noqa: E402
from core.kernel import Kernel  # noqa: E402
from core.errors import ConfigurationError, ModelOpsError  # noqa: E402
from transport.zmq_server import ZMQServer  # noqa: E402
from transport.grpc_server import GRPCServer  # noqa: E402
from transport.rest_api import RESTAPIServer  # noqa: E402


class ModelOpsCoordinatorApp:
    """
    Main ModelOps Coordinator application.
    
    Manages the complete application lifecycle including:
    - Configuration loading
    - Kernel initialization  
    - Server startup and coordination
    - Graceful shutdown handling
    """
    
    def __init__(self, config_file: Optional[str] = None, config_dir: str = "config"):
        """
        Initialize ModelOps Coordinator application.
        
        Args:
            config_file: Optional specific config file
            config_dir: Configuration directory
        """
        self.config_file = config_file
        self.config_dir = config_dir
        
        # Core components
        self.config: Optional[Any] = None
        self.kernel: Optional[Kernel] = None
        
        # Server instances
        self.zmq_server: Optional[ZMQServer] = None
        self.grpc_server: Optional[GRPCServer] = None
        self.rest_server: Optional[RESTAPIServer] = None
        
        # Application state
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._startup_time: Optional[datetime] = None
        
        # Shutdown handling
        self._shutdown_handlers = []
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            """Handle shutdown signals."""
            print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
            
            # Set shutdown event in async context
            if self._shutdown_event:
                try:
                    loop = asyncio.get_running_loop()
                    loop.call_soon_threadsafe(self._shutdown_event.set)
                except RuntimeError:
                    # No running loop, handle synchronously
                    asyncio.run(self._shutdown_async())
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request
        
        # Windows compatibility
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    
    async def start(self):
        """Start the ModelOps Coordinator application."""
        try:
            print("🚀 Starting ModelOps Coordinator...")
            self._startup_time = datetime.utcnow()
            
            # Load configuration
            await self._load_configuration()
            
            # Initialize kernel
            await self._initialize_kernel()
            
            # Start servers concurrently
            await self._start_servers()
            
            self._running = True
            print("✅ ModelOps Coordinator started successfully!")
            
            # Print startup summary
            self._print_startup_summary()
            
            # Wait for shutdown signal
            await self._wait_for_shutdown()
            
        except Exception as e:
            print(f"❌ Failed to start ModelOps Coordinator: {e}")
            await self._cleanup()
            raise
    
    async def _load_configuration(self):
        """Load and validate configuration."""
        print("📋 Loading configuration...")
        
        try:
            # Use UnifiedConfigLoader to load config
            self.config = load_config(
                config_file=self.config_file,
                config_dir=self.config_dir
            )
            print(f"✅ Configuration loaded from {self.config_dir}")
            
            # Log configuration sources
            from config.loader import UnifiedConfigLoader
            loader = UnifiedConfigLoader(self.config_dir)
            loader.load_config(self.config_file)
            sources = loader.get_source_info()
            
            print("📂 Configuration sources:")
            for source in sources:
                if source['loaded']:
                    print(f"   • {source['path']} ({source['type']}, priority: {source['priority']})")
            
        except Exception as e:
            raise ConfigurationError(f"Configuration loading failed: {e}", "CONFIG_LOAD_FAILED")
    
    async def _initialize_kernel(self):
        """Initialize the ModelOps kernel."""
        print("🔧 Initializing ModelOps kernel...")
        
        try:
            # Create kernel with loaded configuration
            self.kernel = Kernel(self.config)
            
            # Wait a moment for kernel initialization
            await asyncio.sleep(0.1)
            
            # Verify kernel health
            if self.kernel.is_healthy():
                print("✅ Kernel initialized and healthy")
            else:
                raise ModelOpsError("Kernel health check failed", "KERNEL_UNHEALTHY")
                
        except Exception as e:
            raise ModelOpsError(f"Kernel initialization failed: {e}", "KERNEL_INIT_FAILED")
    
    async def _start_servers(self):
        """Start all transport servers concurrently."""
        print("🌐 Starting transport servers...")
        
        try:
            # Create server instances
            self._create_server_instances()
            
            # Start servers concurrently
            await self._start_servers_concurrent()
            
            print("✅ All transport servers started successfully")
            
        except Exception as e:
            raise ModelOpsError(f"Server startup failed: {e}", "SERVER_START_FAILED")
    
    def _create_server_instances(self):
        """Create server instances with kernel."""
        # ZMQ Server
        zmq_bind_address = f"tcp://*:{self.config.server.zmq_port}"
        self.zmq_server = ZMQServer(
            kernel=self.kernel,
            bind_address=zmq_bind_address,
            max_workers=self.config.server.max_workers
        )
        
        # gRPC Server
        grpc_bind_address = f"[::]:{self.config.server.grpc_port}"
        self.grpc_server = GRPCServer(
            kernel=self.kernel,
            bind_address=grpc_bind_address,
            max_workers=self.config.server.max_workers
        )
        
        # REST API Server
        self.rest_server = RESTAPIServer(
            kernel=self.kernel,
            host="0.0.0.0",
            port=self.config.server.rest_port
        )
    
    async def _start_servers_concurrent(self):
        """Start servers concurrently using asyncio."""
        async def start_zmq():
            """Start ZMQ server."""
            try:
                self.zmq_server.start()
                print(f"✅ ZMQ server listening on port {self.config.server.zmq_port}")
            except Exception as e:
                print(f"❌ ZMQ server failed: {e}")
                raise
        
        async def start_grpc():
            """Start gRPC server."""
            try:
                self.grpc_server.start()
                print(f"✅ gRPC server listening on port {self.config.server.grpc_port}")
            except Exception as e:
                print(f"❌ gRPC server failed: {e}")
                raise
        
        async def start_rest():
            """Start REST API server."""
            try:
                self.rest_server.start()
                print(f"✅ REST API server listening on port {self.config.server.rest_port}")
                await asyncio.sleep(0.5)  # Give REST server time to start
            except Exception as e:
                print(f"❌ REST API server failed: {e}")
                raise
        
        # Start all servers concurrently
        await asyncio.gather(
            start_zmq(),
            start_grpc(),
            start_rest(),
            return_exceptions=False
        )
    
    def _print_startup_summary(self):
        """Print startup summary information."""
        uptime = datetime.utcnow() - self._startup_time
        
        print("\n" + "="*60)
        print("🎉 ModelOps Coordinator - Startup Complete")
        print("="*60)
        print("📊 System Status:")
        print(f"   • Startup Time: {uptime.total_seconds():.2f}s")
        print(f"   • Kernel Health: {'✅ Healthy' if self.kernel.is_healthy() else '❌ Unhealthy'}")
        print(f"   • Configuration: {len(self.config.__dict__)} sections loaded")
        
        print("\n🌐 Transport Endpoints:")
        print(f"   • ZMQ Server:  tcp://localhost:{self.config.server.zmq_port}")
        print(f"   • gRPC Server: localhost:{self.config.server.grpc_port}")
        print(f"   • REST API:    http://localhost:{self.config.server.rest_port}")
        print(f"   • Swagger UI:  http://localhost:{self.config.server.rest_port}/docs")
        
        # Get system status
        system_status = self.kernel.get_system_status()
        print("\n📈 Resource Status:")
        print(f"   • GPU Available: {'✅' if system_status.get('gpu', {}).get('available', False) else '❌'}")
        print(f"   • Models Loaded: {system_status.get('models', {}).get('loaded_count', 0)}")
        print(f"   • Active Jobs: {system_status.get('learning', {}).get('running_jobs', 0)}")
        print(f"   • Active Goals: {system_status.get('goals', {}).get('active_goals', 0)}")
        
        print("\n💡 Ready to accept requests!")
        print("   Press Ctrl+C to shutdown gracefully")
        print("="*60)
    
    async def _wait_for_shutdown(self):
        """Wait for shutdown signal."""
        try:
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            print("\n🛑 Keyboard interrupt received")
        
        print("🔄 Initiating graceful shutdown...")
        await self._shutdown_async()
    
    async def _shutdown_async(self):
        """Perform graceful shutdown asynchronously."""
        if not self._running:
            return
        
        self._running = False
        shutdown_start = time.time()
        
        try:
            print("📊 Saving system state...")
            
            # Stop accepting new requests
            await self._stop_servers()
            
            # Shutdown kernel and save state
            await self._shutdown_kernel()
            
            # Run custom shutdown handlers
            await self._run_shutdown_handlers()
            
            shutdown_duration = time.time() - shutdown_start
            print(f"✅ Graceful shutdown completed in {shutdown_duration:.2f}s")
            
        except Exception as e:
            print(f"⚠️ Error during shutdown: {e}")
        finally:
            await self._cleanup()
    
    async def _stop_servers(self):
        """Stop all transport servers."""
        print("🌐 Stopping transport servers...")
        
        stop_tasks = []
        
        # Stop ZMQ server
        if self.zmq_server:
            async def stop_zmq():
                try:
                    self.zmq_server.stop()
                    print("✅ ZMQ server stopped")
                except Exception as e:
                    print(f"⚠️ Error stopping ZMQ server: {e}")
            stop_tasks.append(stop_zmq())
        
        # Stop gRPC server
        if self.grpc_server:
            async def stop_grpc():
                try:
                    self.grpc_server.stop()
                    print("✅ gRPC server stopped")
                except Exception as e:
                    print(f"⚠️ Error stopping gRPC server: {e}")
            stop_tasks.append(stop_grpc())
        
        # Stop REST server
        if self.rest_server:
            async def stop_rest():
                try:
                    self.rest_server.stop()
                    print("✅ REST API server stopped")
                except Exception as e:
                    print(f"⚠️ Error stopping REST server: {e}")
            stop_tasks.append(stop_rest())
        
        # Wait for all servers to stop
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
    
    async def _shutdown_kernel(self):
        """Shutdown kernel and save state."""
        if self.kernel:
            print("🔧 Shutting down kernel...")
            try:
                # Save learning job states
                if hasattr(self.kernel, 'learning'):
                    print("💾 Saving learning job states...")
                    # Learning module handles its own state persistence
                
                # Save goal states
                if hasattr(self.kernel, 'goals'):
                    print("🎯 Saving goal states...")
                    # Goal module handles its own state persistence
                
                # Shutdown kernel
                self.kernel.shutdown()
                print("✅ Kernel shutdown completed")
                
            except Exception as e:
                print(f"⚠️ Error during kernel shutdown: {e}")
    
    async def _run_shutdown_handlers(self):
        """Run custom shutdown handlers."""
        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                print(f"⚠️ Error in shutdown handler: {e}")
    
    async def _cleanup(self):
        """Final cleanup operations."""
        print("🧹 Performing final cleanup...")
        
        # Clear references
        self.kernel = None
        self.zmq_server = None
        self.grpc_server = None
        self.rest_server = None
        
        print("✅ Cleanup completed")
    
    def add_shutdown_handler(self, handler):
        """Add custom shutdown handler."""
        self._shutdown_handlers.append(handler)
    
    def is_running(self) -> bool:
        """Check if application is running."""
        return self._running
    
    def get_status(self) -> dict:
        """Get application status."""
        status = {
            'running': self._running,
            'startup_time': self._startup_time.isoformat() if self._startup_time else None,
            'kernel_healthy': self.kernel.is_healthy() if self.kernel else False,
            'servers': {
                'zmq': self.zmq_server.is_running() if self.zmq_server else False,
                'grpc': self.grpc_server.is_running() if self.grpc_server else False,
                'rest': self.rest_server.is_running() if self.rest_server else False
            }
        }
        
        if self._startup_time:
            uptime = datetime.utcnow() - self._startup_time
            status['uptime_seconds'] = uptime.total_seconds()
        
        return status


async def main():
    """Main application entry point."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ModelOps Coordinator')
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--config-dir', type=str, default='config', help='Configuration directory')
    parser.add_argument('--version', action='version', version='ModelOps Coordinator 1.0.0')
    
    args = parser.parse_args()
    
    # Create and start application
    app = ModelOpsCoordinatorApp(
        config_file=args.config,
        config_dir=args.config_dir
    )
    
    try:
        await app.start()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure we're running in the correct directory
    if not Path("config/default.yaml").exists():
        print("❌ Error: Must run from ModelOps Coordinator project root")
        print("   Expected to find config/default.yaml")
        sys.exit(1)
    
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)