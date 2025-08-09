#!/usr/bin/env python3
"""
Unified Observability Center (UOC) - Main Application

This module provides the Unified Observability Center service that inherits from BaseAgent
and uses the approved golden utilities from the common directory.
"""

import asyncio
import signal
import logging
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

# Import UOC core components
from unified_observability_center.core.kernel import Kernel
from unified_observability_center.core.ha import LeaderElector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedObservabilityCenter(BaseAgent):
    """
    Unified Observability Center - Centralized monitoring and observability hub.
    
    Inherits from BaseAgent to leverage standardized health checking,
    error handling, metrics, and configuration management.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize UOC with BaseAgent foundation.
        
        Args:
            **kwargs: Arguments passed to BaseAgent
        """
        # Initialize BaseAgent with all standard features
        super().__init__(name='UnifiedObservabilityCenter', **kwargs)
        
        # Load hub-specific configuration using UnifiedConfigLoader
        config_loader = UnifiedConfigLoader()
        self.hub_config = self._load_hub_config(config_loader)
        
        # Core components
        self.kernel: Optional[Kernel] = None
        self.elector: Optional[LeaderElector] = None
        
        # State management
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        self._startup_time = None
        self._is_leader = False
        
        # Initialize hub components
        self._initialize_hub_components()
        
        self.logger.info(f"UnifiedObservabilityCenter initialized on port {self.port}")
    
    def _load_hub_config(self, config_loader: UnifiedConfigLoader) -> Dict[str, Any]:
        """
        Load hub-specific configuration using the golden UnifiedConfigLoader.
        
        Args:
            config_loader: The unified config loader instance
            
        Returns:
            Configuration dictionary
        """
        try:
            # Get base configuration
            base_config = config_loader.get_agent_config('UnifiedObservabilityCenter')
            
            # Build UOC-specific configuration
            config = {
                'nats': {
                    'url': os.getenv('NATS_URL', base_config.get('nats_url', 'nats://localhost:4222'))
                },
                'ha': {
                    'cluster_name': os.getenv('UOC_CLUSTER', base_config.get('cluster_name', 'uoc-cluster')),
                    'election_ttl': int(os.getenv('ELECTION_TTL', base_config.get('election_ttl', 10)))
                },
                'api': {
                    'rest_port': int(os.getenv('UOC_REST_PORT', base_config.get('rest_port', 9100)))
                },
                'collectors': {
                    'prometheus': {
                        'enabled': os.getenv('PROMETHEUS_ENABLED', base_config.get('prometheus_enabled', 'true')).lower() == 'true',
                        'scrape_interval': int(os.getenv('SCRAPE_INTERVAL', base_config.get('scrape_interval', 15)))
                    },
                    'jaeger': {
                        'enabled': os.getenv('JAEGER_ENABLED', base_config.get('jaeger_enabled', 'true')).lower() == 'true',
                        'agent_host': os.getenv('JAEGER_AGENT_HOST', base_config.get('jaeger_host', 'localhost')),
                        'agent_port': int(os.getenv('JAEGER_AGENT_PORT', base_config.get('jaeger_port', 6831)))
                    },
                    'logs': {
                        'enabled': os.getenv('LOG_COLLECTION_ENABLED', base_config.get('log_collection_enabled', 'true')).lower() == 'true',
                        'buffer_size': int(os.getenv('LOG_BUFFER_SIZE', base_config.get('log_buffer_size', 1000)))
                    }
                },
                'engines': {
                    'anomaly_detection': {
                        'enabled': os.getenv('ANOMALY_DETECTION_ENABLED', base_config.get('anomaly_detection_enabled', 'true')).lower() == 'true',
                        'sensitivity': float(os.getenv('ANOMALY_SENSITIVITY', base_config.get('anomaly_sensitivity', 0.95)))
                    },
                    'alerting': {
                        'enabled': os.getenv('ALERTING_ENABLED', base_config.get('alerting_enabled', 'true')).lower() == 'true',
                        'cooldown_seconds': int(os.getenv('ALERT_COOLDOWN', base_config.get('alert_cooldown', 300)))
                    }
                }
            }
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Return minimal default configuration
            return {
                'nats': {'url': 'nats://localhost:4222'},
                'ha': {'cluster_name': 'uoc-cluster', 'election_ttl': 10},
                'api': {'rest_port': 9100},
                'collectors': {},
                'engines': {}
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
                'metrics_collection',
                'trace_aggregation',
                'log_aggregation',
                'anomaly_detection',
                'alerting',
                'dashboard_api',
                'high_availability'
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
                    context={'component': 'UnifiedObservabilityCenter', 'phase': 'initialization'}
                )
            self.logger.error(f"Failed to initialize hub components: {e}")
    
    async def initialize_kernel(self):
        """Initialize the UOC kernel and collectors."""
        self.logger.info("Initializing UOC kernel...")
        
        try:
            # Create and start kernel
            self.kernel = Kernel(self.hub_config)
            await self.kernel.start()
            self.logger.info("✅ Kernel started with collectors")
            
            # Initialize HA leader election
            self.elector = LeaderElector(
                nats_url=self.hub_config['nats']['url'],
                cluster_name=self.hub_config['ha']['cluster_name'],
                ttl_seconds=self.hub_config['ha']['election_ttl']
            )
            await self.elector.start()
            self.logger.info("✅ Leader election initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize kernel: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'UnifiedObservabilityCenter', 'phase': 'kernel_init'}
                )
            raise
    
    async def manage_leadership(self):
        """Manage HA leadership state and exclusive tasks."""
        was_leader = False
        
        while self.is_running:
            try:
                is_leader = self.elector.is_leader()
                
                if is_leader and not was_leader:
                    # Became leader
                    self.logger.info("🎖️ Became cluster leader - activating exclusive tasks")
                    self._is_leader = True
                    was_leader = True
                    
                    # Start exclusive leader tasks
                    if self.kernel:
                        await self.kernel.activate_leader_tasks()
                    
                    # Update metrics
                    if self.prometheus_exporter:
                        self.prometheus_exporter.set_gauge('uoc_is_leader', 1)
                
                if not is_leader and was_leader:
                    # Lost leadership
                    self.logger.info("📤 Lost cluster leadership - deactivating exclusive tasks")
                    self._is_leader = False
                    was_leader = False
                    
                    # Stop exclusive leader tasks
                    if self.kernel:
                        await self.kernel.deactivate_leader_tasks()
                    
                    # Update metrics
                    if self.prometheus_exporter:
                        self.prometheus_exporter.set_gauge('uoc_is_leader', 0)
                
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in leadership management: {e}")
                await asyncio.sleep(5)
    
    async def start_rest_api(self):
        """Start the REST API server."""
        import uvicorn
        
        config = uvicorn.Config(
            "unified_observability_center.api.rest:app",
            host="0.0.0.0",
            port=self.hub_config['api']['rest_port'],
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        self.logger.info(f"✅ REST API starting on port {self.hub_config['api']['rest_port']}")
        await server.serve()
    
    async def start(self):
        """Start the Unified Observability Center service."""
        try:
            self.logger.info("🚀 Starting Unified Observability Center...")
            self._startup_time = datetime.utcnow()
            
            # Initialize kernel and collectors
            await self.initialize_kernel()
            
            # Update health status
            if self.health_checker:
                self.health_checker.set_healthy()
            
            self.is_running = True
            
            # Start concurrent tasks
            self._leader_task = asyncio.create_task(self.manage_leadership())
            self._api_task = asyncio.create_task(self.start_rest_api())
            
            self.logger.info("✅ Unified Observability Center started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start UOC: {e}")
            if self.unified_error_handler:
                self.unified_error_handler.report_error(
                    error=e,
                    severity='CRITICAL',
                    context={'component': 'UnifiedObservabilityCenter', 'phase': 'startup'}
                )
            raise
    
    async def stop(self):
        """Stop the Unified Observability Center service gracefully."""
        self.logger.info("🛑 Stopping Unified Observability Center...")
        self.is_running = False
        
        # Cancel tasks
        if hasattr(self, '_leader_task'):
            self._leader_task.cancel()
            try:
                await self._leader_task
            except asyncio.CancelledError:
                pass
        
        if hasattr(self, '_api_task'):
            self._api_task.cancel()
            try:
                await self._api_task
            except asyncio.CancelledError:
                pass
        
        # Stop elector
        if self.elector:
            await self.elector.stop()
        
        # Stop kernel
        if self.kernel:
            await self.kernel.stop()
        
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
            self.logger.info(f"  • Was leader: {self._is_leader}")
        
        self.logger.info("✅ Unified Observability Center stopped successfully")
    
    async def run(self):
        """Run the Unified Observability Center service."""
        # Start the service
        await self.start()
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
        
        # Stop the service
        await self.stop()


def main():
    """Main entry point for Unified Observability Center."""
    # Create and run the hub
    hub = UnifiedObservabilityCenter(
        port=int(os.getenv('UOC_PORT', 9100)),
        health_check_port=int(os.getenv('UOC_HEALTH_PORT', 9101))
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
        logger.info("UnifiedObservabilityCenter shutdown complete")


if __name__ == "__main__":
    main()