#!/usr/bin/env python3
"""
Real-Time Audio Pipeline (RTAP) - Main Application Entry Point

Ultra-low-latency real-time audio processing service with ≤150ms p95 latency target.
Integrates audio capture, wake word detection, speech recognition, language analysis,
and real-time transcript broadcasting via ZMQ and WebSocket.

Usage:
    python3 app.py [--environment ENV] [--config CONFIG_FILE] [--log-level LEVEL]

Environment Variables:
    AUDIO_DEVICE: Audio input device name (default: system default)
    RTAP_ENVIRONMENT: Runtime environment (default, main_pc, pc2)
    RTAP_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.loader import ConfigurationError, UnifiedConfigLoader
from core.pipeline import AudioPipeline
from core.telemetry import get_global_metrics

# Import with fallback for compatibility
try:
    from transport.schemas import EventTypes, create_event_notification
    SCHEMAS_AVAILABLE = True
except ImportError:
    # Fallback for compatibility issues
    SCHEMAS_AVAILABLE = False
    class EventTypes:
        PIPELINE_STARTED = "pipeline_started"
        PIPELINE_STOPPED = "pipeline_stopped"
        WAKE_WORD_DETECTED = "wake_word_detected"
        PROCESSING_STARTED = "processing_started"
        ERROR_OCCURRED = "error_occurred"

    def create_event_notification(event_type, metadata=None):
        return {"event_type": event_type, "metadata": metadata or {}}

try:
    from transport.schemas import EventTypes, create_event_notification
except ImportError:
    # Fallback for compatibility issues
    class EventTypes:
        PIPELINE_STARTED = "pipeline_started"
        PIPELINE_STOPPED = "pipeline_stopped"
    def create_event_notification(event_type, metadata=None):
        return {"event_type": event_type, "metadata": metadata or {}}

# Import transport components with graceful fallbacks
try:
    from transport.zmq_pub import ZmqPublisher
    ZMQ_AVAILABLE = True
except ImportError:
    ZmqPublisher = None
    ZMQ_AVAILABLE = False

try:
    from transport.ws_server import WebSocketServer
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WebSocketServer = None
    WEBSOCKET_AVAILABLE = False


class RTAPApplication:
    """
    Real-Time Audio Pipeline Application.

    Main orchestrator for the RTAP service, managing configuration loading,
    component initialization, concurrent startup, and graceful shutdown.

    Features:
    - Automatic configuration loading with environment detection
    - Model warm-up for reduced first-request latency
    - Concurrent component execution with asyncio.gather
    - Comprehensive error handling and recovery
    - Graceful shutdown with resource cleanup
    - Performance monitoring and health checks
    """

    def __init__(self,
                 environment: Optional[str] = None,
                 config_file: Optional[str] = None,
                 log_level: str = "INFO"):
        """
        Initialize RTAP application.

        Args:
            environment: Target environment (auto-detected if None)
            config_file: Specific config file to use
            log_level: Logging level
        """
        self.environment = environment
        self.config_file = config_file
        self.log_level = log_level

        # Setup logging first
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

        # Application state
        self.config: Dict[str, Any] = {}
        self.is_running = False
        self.start_time = 0.0
        self.session_id = f"rtap_{int(time.time())}"

        # Core components
        self.pipeline: Optional[AudioPipeline] = None
        self.zmq_publisher: Optional[ZmqPublisher] = None
        self.websocket_server: Optional[WebSocketServer] = None

        # Component tasks
        self.component_tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()

        # Performance tracking
        self.metrics = get_global_metrics()

        self.logger.info(f"RTAP Application initialized (session: {self.session_id})")

    def _setup_logging(self) -> None:
        """Setup comprehensive logging configuration."""
        # Convert log level
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)

        # Configure root logger
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'rtap_{int(time.time())}.log')
            ]
        )

        # Set specific logger levels for noisy libraries
        logging.getLogger('asyncio').setLevel(logging.WARNING)
        logging.getLogger('websockets').setLevel(logging.WARNING)

    async def initialize_and_run(self) -> None:
        """
        Main application initialization and execution.

        Performs complete application lifecycle:
        1. Configuration loading and validation
        2. Model warm-up for optimal performance
        3. Component initialization
        4. Concurrent startup with asyncio.gather
        5. Runtime monitoring and health checks
        6. Graceful shutdown handling
        """
        try:
            self.logger.info("=== Real-Time Audio Pipeline (RTAP) Starting ===")
            self.start_time = time.perf_counter()

            # Step 1: Load and validate configuration
            await self._load_configuration()

            # Step 2: Perform system checks
            await self._perform_system_checks()

            # Step 3: Warm up models and components
            await self._warmup_models()

            # Step 4: Initialize core components
            await self._initialize_components()

            # Step 5: Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()

            # Step 6: Start all components concurrently
            await self._start_components()

            self.logger.info("RTAP application startup complete")

            # Step 7: Wait for shutdown signal
            await self._run_until_shutdown()

        except Exception as e:
            self.logger.error(f"Critical error in RTAP application: {e}")
            await self._emergency_shutdown()
            raise
        finally:
            await self._cleanup()

    async def _load_configuration(self) -> None:
        """Load and validate application configuration."""
        try:
            self.logger.info("Loading configuration...")

            # Initialize configuration loader
            config_loader = UnifiedConfigLoader()

            # Load configuration with environment detection
            self.config = config_loader.load_config(
                environment=self.environment,
                config_file=self.config_file,
                validate=True
            )

            # Log configuration summary
            self.logger.info(f"Configuration loaded: {self.config.get('title', 'Unknown')}")
            self.logger.info(f"Environment: {self.environment or 'auto-detected'}")
            self.logger.info(f"Audio: {self.config['audio']['sample_rate']}Hz, "
                           f"{self.config['audio']['frame_ms']}ms frames")
            self.logger.info(f"Ports: Events={self.config['output']['zmq_pub_port_events']}, "
                           f"Transcripts={self.config['output']['zmq_pub_port_transcripts']}, "
                           f"WebSocket={self.config['output']['websocket_port']}")

            # Validate environment variables
            env_vars = config_loader.validate_environment_variables(self.config)
            if env_vars:
                self.logger.debug("Environment variables in use:")
                for var_name, var_info in env_vars.items():
                    self.logger.debug(f"  {var_name}: {var_info['value']}")

        except ConfigurationError as e:
            self.logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    async def _perform_system_checks(self) -> None:
        """Perform system compatibility and resource checks."""
        self.logger.info("Performing system checks...")

        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 8):
                raise RuntimeError(f"Python 3.8+ required, found {python_version}")

            # Check memory availability
            memory = psutil.virtual_memory()
            if memory.available < 1024 * 1024 * 1024:  # 1GB
                self.logger.warning(f"Low memory available: {memory.available / (1024**3):.1f}GB")

            # Check CPU cores
            cpu_count = psutil.cpu_count()
            if cpu_count < 2:
                self.logger.warning(f"Limited CPU cores: {cpu_count}")

            # Check disk space
            disk = psutil.disk_usage('.')
            if disk.free < 1024 * 1024 * 100:  # 100MB
                self.logger.warning(f"Low disk space: {disk.free / (1024**2):.1f}MB")

            # Check component availability
            self.logger.info(f"Component availability: ZMQ={ZMQ_AVAILABLE}, WebSocket={WEBSOCKET_AVAILABLE}")

            self.logger.info("System checks completed")

        except Exception as e:
            self.logger.error(f"System check failed: {e}")
            raise

    async def _warmup_models(self) -> None:
        """Warm up STT and wake-word models for reduced first-request latency."""
        self.logger.info("Starting model warm-up...")
        warmup_start = time.perf_counter()

        try:
            # Note: In this implementation, individual stages handle their own warmup
            # This function could be extended to perform global model preloading

            # Warm up STT model (placeholder for future Whisper preloading)
            stt_start = time.perf_counter()
            await self._warmup_stt_model()
            stt_time = time.perf_counter() - stt_start
            self.logger.info(f"STT model warm-up completed in {stt_time*1000:.1f}ms")

            # Warm up wake-word model (placeholder for future Porcupine preloading)
            wakeword_start = time.perf_counter()
            await self._warmup_wakeword_model()
            wakeword_time = time.perf_counter() - wakeword_start
            self.logger.info(f"Wake-word model warm-up completed in {wakeword_time*1000:.1f}ms")

            total_warmup_time = time.perf_counter() - warmup_start
            self.logger.info(f"Model warm-up completed in {total_warmup_time*1000:.1f}ms")

            # Record warmup metrics
            self.metrics.record_warmup_time('global', total_warmup_time)

        except Exception as e:
            self.logger.error(f"Model warm-up failed: {e}")
            # Continue execution - warmup failure shouldn't stop the service

    async def _warmup_stt_model(self) -> None:
        """Warm up Speech-to-Text model (Whisper)."""
        # Placeholder for future Whisper model preloading
        # In production, this would load the Whisper model into memory
        await asyncio.sleep(0.1)  # Simulate warmup time
        self.logger.debug("STT model warm-up (placeholder)")

    async def _warmup_wakeword_model(self) -> None:
        """Warm up wake-word detection model (Porcupine)."""
        # Placeholder for future Porcupine model preloading
        # In production, this would load the Porcupine model into memory
        await asyncio.sleep(0.05)  # Simulate warmup time
        self.logger.debug("Wake-word model warm-up (placeholder)")

    async def _initialize_components(self) -> None:
        """Initialize all core components."""
        self.logger.info("Initializing components...")

        try:
            # Initialize AudioPipeline
            self.logger.info("Initializing AudioPipeline...")
            self.pipeline = AudioPipeline(self.config)

            # Initialize ZMQ Publisher if available
            if ZMQ_AVAILABLE and ZmqPublisher:
                self.logger.info("Initializing ZMQ Publisher...")
                self.zmq_publisher = ZmqPublisher(self.config)
                self.zmq_publisher.set_session_id(self.session_id)
            else:
                self.logger.warning("ZMQ Publisher not available")

            # Initialize WebSocket Server if available
            if WEBSOCKET_AVAILABLE and WebSocketServer:
                self.logger.info("Initializing WebSocket Server...")
                self.websocket_server = WebSocketServer(self.config)
            else:
                self.logger.warning("WebSocket Server not available")

            self.logger.info("Component initialization completed")

        except Exception as e:
            self.logger.error(f"Component initialization failed: {e}")
            raise

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request

        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)  # Hangup

        self.logger.debug("Signal handlers registered")

    async def _start_components(self) -> None:
        """Start all components concurrently using asyncio.gather."""
        self.logger.info("Starting components concurrently...")

        # Prepare component coroutines
        coroutines = []

        # Add pipeline startup
        if self.pipeline:
            coroutines.append(self.pipeline.start())

        # Add ZMQ publisher startup
        if self.zmq_publisher:
            coroutines.append(self.zmq_publisher.start())

        # Add WebSocket server startup
        if self.websocket_server:
            coroutines.append(self.websocket_server.start())

        if not coroutines:
            raise RuntimeError("No components available to start")

        # Connect pipeline output to publishers
        if self.pipeline and (self.zmq_publisher or self.websocket_server):
            coroutines.append(self._connect_pipeline_outputs())

        # Start all components concurrently
        self.logger.info(f"Starting {len(coroutines)} components...")

        try:
            # Create tasks for all components
            self.component_tasks = [
                asyncio.create_task(coro, name=f"component_{i}")
                for i, coro in enumerate(coroutines)
            ]

            self.is_running = True

            # Publish startup event
            if self.zmq_publisher:
                await self.zmq_publisher.publish_system_event(
                    EventTypes.PIPELINE_STARTED,
                    metadata={
                        'session_id': self.session_id,
                        'components': len(self.component_tasks),
                        'startup_time_ms': (time.perf_counter() - self.start_time) * 1000
                    }
                )

            self.logger.info("All components started successfully")

        except Exception as e:
            self.logger.error(f"Component startup failed: {e}")
            await self._emergency_shutdown()
            raise

    async def _connect_pipeline_outputs(self) -> None:
        """Connect pipeline output stream to transport publishers."""
        if not self.pipeline:
            return

        self.logger.info("Connecting pipeline outputs to transport layer...")

        try:
            # Get pipeline output stream
            output_stream = self.pipeline.output_stream()

            # Fan out to multiple publishers
            async for output_data in output_stream:
                try:
                    # Send to ZMQ publisher
                    if self.zmq_publisher:
                        await self.zmq_publisher.consume_pipeline_output([output_data])

                    # Send to WebSocket server
                    if self.websocket_server:
                        await self.websocket_server.consume_pipeline_output([output_data])

                except Exception as e:
                    self.logger.error(f"Error forwarding pipeline output: {e}")

        except asyncio.CancelledError:
            self.logger.info("Pipeline output connection cancelled")
        except Exception as e:
            self.logger.error(f"Pipeline output connection failed: {e}")

    async def _run_until_shutdown(self) -> None:
        """Run application until shutdown is requested."""
        self.logger.info("RTAP application running - waiting for shutdown signal")

        try:
            # Wait for shutdown event or component failure
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(self.shutdown_event.wait()),
                    *self.component_tasks
                ],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Check if any component failed
            for task in done:
                if task.exception() and not self.shutdown_event.is_set():
                    self.logger.error(f"Component failed: {task.exception()}")
                    await self.shutdown()

        except Exception as e:
            self.logger.error(f"Runtime error: {e}")
            await self.shutdown()

    async def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        if self.shutdown_event.is_set():
            return  # Already shutting down

        self.logger.info("Initiating graceful shutdown...")
        shutdown_start = time.perf_counter()

        # Set shutdown event
        self.shutdown_event.set()
        self.is_running = False

        try:
            # Publish shutdown event
            if self.zmq_publisher:
                await self.zmq_publisher.publish_system_event(
                    EventTypes.PIPELINE_STOPPED,
                    metadata={
                        'session_id': self.session_id,
                        'uptime_seconds': time.perf_counter() - self.start_time
                    }
                )

            # Shutdown components in reverse order
            if self.websocket_server:
                await self.websocket_server.shutdown()

            if self.zmq_publisher:
                await self.zmq_publisher.shutdown()

            if self.pipeline:
                await self.pipeline.shutdown()

            # Cancel any remaining tasks
            for task in self.component_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete with timeout
            if self.component_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*self.component_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Some tasks did not complete within timeout")

            shutdown_time = time.perf_counter() - shutdown_start
            self.logger.info(f"Graceful shutdown completed in {shutdown_time*1000:.1f}ms")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    async def _emergency_shutdown(self) -> None:
        """Emergency shutdown for critical errors."""
        self.logger.error("Emergency shutdown initiated")

        self.is_running = False
        self.shutdown_event.set()

        # Force cancel all tasks
        for task in self.component_tasks:
            task.cancel()

    async def _cleanup(self) -> None:
        """Final cleanup and resource deallocation."""
        try:
            # Final statistics
            uptime = time.perf_counter() - self.start_time
            final_stats = self.metrics.get_stats()

            self.logger.info("=== RTAP Application Shutdown Complete ===")
            self.logger.info(f"Session: {self.session_id}")
            self.logger.info(f"Uptime: {uptime:.1f} seconds")
            self.logger.info(f"Frames processed: {final_stats.get('frames_processed', 0)}")
            self.logger.info(f"Transcripts completed: {final_stats.get('transcripts_completed', 0)}")
            self.logger.info("All resources cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Error in final cleanup: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive application status."""
        uptime = time.perf_counter() - self.start_time if self.start_time > 0 else 0

        return {
            'session_id': self.session_id,
            'is_running': self.is_running,
            'uptime_seconds': uptime,
            'environment': self.environment,
            'config_title': self.config.get('title', 'Unknown'),
            'components': {
                'pipeline': self.pipeline is not None,
                'zmq_publisher': self.zmq_publisher is not None,
                'websocket_server': self.websocket_server is not None,
            },
            'component_availability': {
                'zmq': ZMQ_AVAILABLE,
                'websocket': WEBSOCKET_AVAILABLE,
            },
            'metrics': self.metrics.get_stats() if self.metrics else {},
        }


async def main():
    """Main entry point for the RTAP application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Real-Time Audio Pipeline (RTAP) - Ultra-low-latency speech processing"
    )
    parser.add_argument(
        '--environment', '-e',
        choices=['default', 'main_pc', 'pc2'],
        help='Target environment (auto-detected if not specified)'
    )
    parser.add_argument(
        '--config', '-c',
        help='Specific configuration file to use'
    )
    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=os.environ.get('RTAP_LOG_LEVEL', 'INFO'),
        help='Logging level (default: INFO)'
    )
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='RTAP 1.0'
    )

    args = parser.parse_args()

    # Override with environment variables
    environment = args.environment or os.environ.get('RTAP_ENVIRONMENT')

    try:
        # Create and run application
        app = RTAPApplication(
            environment=environment,
            config_file=args.config,
            log_level=args.log_level
        )

        await app.initialize_and_run()

    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        print(f"Critical application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nApplication interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)
