#!/usr/bin/env python3
"""
Real-Time Audio Pipeline (RTAP) - Main Application

This module provides the Real-Time Audio Pipeline service that inherits from BaseAgent
and uses the approved golden utilities from the common directory.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add common to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import BaseAgent and golden utilities
from common.core.base_agent import BaseAgent
from common.utils.unified_config_loader import UnifiedConfigLoader
from common.utils.path_manager import PathManager

# Import RTAP core components
from core.pipeline import AudioPipeline
from core.preprocessor import AudioPreprocessor
from core.gpu_inference import GPUInferenceEngine
from core.schemas import RTAPConfig, AudioFrame
from transport.zmq_stream import StreamingServer
from transport.grpc_service import RTAPGrpcService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealTimeAudioPipeline(BaseAgent):
    """
    Real-Time Audio Pipeline - High-performance audio processing hub.
    
    Inherits from BaseAgent to leverage standardized health checking,
    error handling, metrics, and configuration management.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize RTAP with BaseAgent foundation.
        
        Args:
            **kwargs: Arguments passed to BaseAgent
        """
        # Initialize BaseAgent with all standard features
        super().__init__(name='RealTimeAudioPipeline', **kwargs)
        
        # Load hub-specific configuration using UnifiedConfigLoader
        config_loader = UnifiedConfigLoader()
        self.hub_config = self._load_hub_config(config_loader)
        
        # Core components
        self.pipeline: Optional[AudioPipeline] = None
        self.preprocessor: Optional[AudioPreprocessor] = None
        self.gpu_engine: Optional[GPUInferenceEngine] = None
        
        # Transport components
        self.streaming_server: Optional[StreamingServer] = None
        self.grpc_service: Optional[RTAPGrpcService] = None
        
        # State management
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._startup_time = None
        self._frames_processed = 0
        
        # Initialize hub components
        self._initialize_hub_components()
        
        self.logger.info(f"RealTimeAudioPipeline initialized on port {self.port}")
    
    def _load_hub_config(self, config_loader: UnifiedConfigLoader) -> RTAPConfig:
        """
        Load hub-specific configuration using the golden UnifiedConfigLoader.
        
        Args:
            config_loader: The unified config loader instance
            
        Returns:
            RTAPConfig object with merged configuration
        """
        try:
            # Get base configuration
            base_config = config_loader.get_agent_config('RealTimeAudioPipeline')
            
            # Determine environment (PC2 vs MainPC)
            environment = os.getenv('RTAP_ENVIRONMENT', 'pc2')
            
            # Build RTAP-specific configuration
            config_dict = {
                'environment': environment,
                'audio': {
                    'sample_rate': int(os.getenv('SAMPLE_RATE', base_config.get('sample_rate', 16000))),
                    'frame_size': int(os.getenv('FRAME_SIZE', base_config.get('frame_size', 512))),
                    'channels': int(os.getenv('CHANNELS', base_config.get('channels', 1)))
                },
                'pipeline': {
                    'buffer_size': int(os.getenv('BUFFER_SIZE', base_config.get('buffer_size', 100))),
                    'max_latency_ms': int(os.getenv('MAX_LATENCY_MS', base_config.get('max_latency_ms', 50)))
                },
                'transport': {
                    'zmq_port': int(os.getenv('RTAP_ZMQ_PORT', base_config.get('zmq_port', 5557))),
                    'grpc_port': int(os.getenv('RTAP_GRPC_PORT', base_config.get('grpc_port', 5558)))
                },
                'gpu': {
                    'enabled': environment == 'main_pc',
                    'device': os.getenv('CUDA_DEVICE', base_config.get('cuda_device', 'cuda:0'))
                }
            }
            
            return RTAPConfig(**config_dict)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Return default configuration
            return RTAPConfig()
    
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
            if self.hub_config.environment == 'pc2':
                self.capabilities = [
                    'audio_preprocessing',
                    'feature_extraction',
                    'noise_reduction',
                    'frame_streaming'
                ]
            else:  # main_pc
                self.capabilities = [
                    'gpu_inference',
                    'speech_recognition',
                    'audio_synthesis',
                    'real_time_processing'
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
                    context={'component': 'RealTimeAudioPipeline', 'phase': 'initialization'}
                )
            self.logger.error(f"Failed to initialize hub components: {e}")
    
    async def initialize_pipeline(self):
        """Initialize the audio processing pipeline."""
        self.logger.info("Initializing audio pipeline...")
        
        try:
            # Initialize preprocessor (PC2 and MainPC)
            self.preprocessor = AudioPreprocessor(
                sample_rate=self.hub_config.audio.sample_rate,
                frame_size=self.hub_config.audio.frame_size,
                channels=self.hub_config.audio.channels
            )
            await self.preprocessor.initialize()
            self.logger.info("✅ Preprocessor initialized")
            
            # Initialize GPU engine if on MainPC
            if self.hub_config.gpu.enabled:
                self.gpu_engine = GPUInferenceEngine(
                    device=self.hub_config.gpu.device
                )
                await self.gpu_engine.initialize()
                self.logger.info("✅ GPU inference engine initialized")
            
            # Create pipeline
            self.pipeline = AudioPipeline(
                preprocessor=self.preprocessor,
                gpu_engine=self.gpu_engine,
                buffer_size=self.hub_config.pipeline.buffer_size,
                max_latency_ms=self.hub_config.pipeline.max_latency_ms
            )
            await self.pipeline.initialize()
            self.logger.info("✅ Audio pipeline created")
            
            # Initialize transport servers
            await self._initialize_transport()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'RealTimeAudioPipeline', 'phase': 'pipeline_init'}
                )
            raise
    
    async def _initialize_transport(self):
        """Initialize transport servers."""
        # Initialize ZMQ streaming server
        self.streaming_server = StreamingServer(
            port=self.hub_config.transport.zmq_port,
            pipeline=self.pipeline
        )
        await self.streaming_server.start()
        self.logger.info(f"✅ ZMQ streaming server on port {self.hub_config.transport.zmq_port}")
        
        # Initialize gRPC service
        self.grpc_service = RTAPGrpcService(
            port=self.hub_config.transport.grpc_port,
            pipeline=self.pipeline
        )
        await self.grpc_service.start()
        self.logger.info(f"✅ gRPC service on port {self.hub_config.transport.grpc_port}")
    
    async def process_audio_stream(self):
        """Main audio processing loop."""
        self.logger.info("Starting audio processing loop...")
        
        while self.is_running:
            try:
                # Process frames from pipeline
                frame = await self.pipeline.get_next_frame()
                if frame:
                    # Process frame
                    result = await self.pipeline.process_frame(frame)
                    
                    # Update metrics
                    self._frames_processed += 1
                    
                    if self.prometheus_exporter:
                        self.prometheus_exporter.record_request(
                            method='process',
                            endpoint='audio_frame',
                            status='success',
                            duration=frame.processing_time_ms / 1000.0
                        )
                
                await asyncio.sleep(0.001)  # Small delay to prevent CPU spinning
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in processing loop: {e}")
                if self.unified_error_handler:
                    self.unified_error_handler.report_error(
                        error=e,
                        severity='WARNING',
                        context={'component': 'RealTimeAudioPipeline', 'phase': 'stream_processing'}
                    )
    
    async def start(self):
        """Start the Real-Time Audio Pipeline service."""
        try:
            self.logger.info("🚀 Starting Real-Time Audio Pipeline...")
            self._startup_time = datetime.utcnow()
            
            # Initialize pipeline
            await self.initialize_pipeline()
            
            # Update health status
            if self.health_checker:
                self.health_checker.set_healthy()
            
            self.is_running = True
            
            # Start processing loop
            asyncio.create_task(self.process_audio_stream())
            
            self.logger.info(f"✅ RTAP started successfully ({self.hub_config.environment} mode)")
            
        except Exception as e:
            self.logger.error(f"Failed to start RTAP: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'RealTimeAudioPipeline', 'phase': 'startup'}
                )
            raise
    
    async def stop(self):
        """Stop the Real-Time Audio Pipeline service gracefully."""
        self.logger.info("🛑 Stopping Real-Time Audio Pipeline...")
        self.is_running = False
        
        # Stop transport servers
        if self.streaming_server:
            await self.streaming_server.stop()
        
        if self.grpc_service:
            await self.grpc_service.stop()
        
        # Cleanup pipeline
        if self.pipeline:
            await self.pipeline.cleanup()
        
        # Cleanup GPU engine
        if self.gpu_engine:
            await self.gpu_engine.cleanup()
        
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
            self.logger.info(f"  • Frames processed: {self._frames_processed}")
            self.logger.info(f"  • Environment: {self.hub_config.environment}")
        
        self.logger.info("✅ Real-Time Audio Pipeline stopped successfully")
    
    async def run(self):
        """Run the Real-Time Audio Pipeline service."""
        # Start the service
        await self.start()
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Stop the service
        await self.stop()


def main():
    """Main entry point for Real-Time Audio Pipeline."""
    # Create and run the hub
    hub = RealTimeAudioPipeline(
        port=int(os.getenv('RTAP_PORT', 5557)),
        health_check_port=int(os.getenv('RTAP_HEALTH_PORT', 6557))
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
        logger.info("RealTimeAudioPipeline shutdown complete")


if __name__ == "__main__":
    main()
