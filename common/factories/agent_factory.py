#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhanced Base Agent Factory - Phase 2.1

Standardized factory pattern for creating agents with uniform metrics, monitoring,
and enhanced capabilities. Provides consistent agent lifecycle management and
performance tracking across the entire AI System Monorepo.

Part of Phase 2.1: Standardized EnhancedBaseAgent Wrapper - O3 Roadmap Implementation
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union
from contextlib import contextmanager

from common.core.base_agent import BaseAgent
from common.config.unified_config_manager import Config


@dataclass
class AgentMetrics:
    """Comprehensive metrics tracking for agents."""
    
    # Lifecycle metrics
    start_time: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0
    restart_count: int = 0
    
    # Performance metrics
    requests_processed: int = 0
    errors_encountered: int = 0
    avg_response_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Health metrics
    health_status: str = "starting"
    last_health_check: datetime = field(default_factory=datetime.now)
    consecutive_health_failures: int = 0
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_uptime(self):
        """Update uptime calculation."""
        self.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
    
    def record_request(self, response_time_ms: float, success: bool = True):
        """Record a request with response time."""
        self.requests_processed += 1
        if not success:
            self.errors_encountered += 1
        
        # Update rolling average (simple)
        if self.requests_processed == 1:
            self.avg_response_time_ms = response_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.avg_response_time_ms = (alpha * response_time_ms + 
                                       (1 - alpha) * self.avg_response_time_ms)
    
    def update_health(self, status: str):
        """Update health status."""
        self.health_status = status
        self.last_health_check = datetime.now()
        
        if status == "healthy":
            self.consecutive_health_failures = 0
        else:
            self.consecutive_health_failures += 1


class EnhancedBaseAgent(BaseAgent):
    """Enhanced base agent with metrics, monitoring, and lifecycle management."""
    
    def __init__(self, agent_name: str, config_overrides: Optional[Dict] = None):
        """Initialize enhanced base agent.
        
        Args:
            agent_name: Human-readable name for the agent
            config_overrides: Optional configuration overrides
        """
        super().__init__()
        
        self.agent_name = agent_name
        self.config_overrides = config_overrides or {}
        
        # Initialize metrics
        self.metrics = AgentMetrics()
        
        # Initialize enhanced features
        self._shutdown_event = threading.Event()
        self._metrics_lock = threading.Lock()
        self._metrics_thread = None
        
        # Load configuration
        self.config = Config.for_agent(agent_name)
        
        # Apply configuration overrides
        if config_overrides:
            self._apply_config_overrides(config_overrides)
        
        # Setup enhanced logging
        self._setup_enhanced_logging()
        
        # Initialize monitoring
        self._start_metrics_collection()
        
        self.logger.info(f"Enhanced agent '{agent_name}' initialized")
    
    def _apply_config_overrides(self, overrides: Dict):
        """Apply configuration overrides safely."""
        for key, value in overrides.items():
            try:
                # Store override in custom config space
                if not hasattr(self.config, '_overrides'):
                    self.config._overrides = {}
                self.config._overrides[key] = value
                self.logger.debug(f"Applied config override: {key} = {value}")
            except Exception as e:
                self.logger.warning(f"Failed to apply config override {key}: {e}")
    
    def _setup_enhanced_logging(self):
        """Setup enhanced logging with agent context."""
        self.logger = logging.getLogger(f"agent.{self.agent_name}")
        
        # Add agent context to all log messages
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - AGENT[{self.agent_name}] - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _start_metrics_collection(self):
        """Start background metrics collection."""
        self._metrics_thread = threading.Thread(
            target=self._metrics_collection_loop,
            name=f"{self.agent_name}_metrics",
            daemon=True
        )
        self._metrics_thread.start()
    
    def _metrics_collection_loop(self):
        """Background loop for metrics collection."""
        import psutil
        
        process = psutil.Process()
        
        while not self._shutdown_event.is_set():
            try:
                with self._metrics_lock:
                    # Update basic metrics
                    self.metrics.update_uptime()
                    
                    # Update system metrics
                    memory_info = process.memory_info()
                    self.metrics.peak_memory_mb = max(
                        self.metrics.peak_memory_mb,
                        memory_info.rss / 1024 / 1024
                    )
                    
                    self.metrics.cpu_usage_percent = process.cpu_percent()
                    
                    # Update health status
                    health_status = self._check_health_status()
                    self.metrics.update_health(health_status)
                
                # Sleep for metrics interval
                time.sleep(self.config.int("monitoring.metrics_interval", 30))
                
            except Exception as e:
                self.logger.warning(f"Metrics collection error: {e}")
                time.sleep(5)  # Shorter retry interval on error
    
    def _check_health_status(self) -> str:
        """Check current health status."""
        try:
            # Basic health checks
            if self._shutdown_event.is_set():
                return "shutting_down"
            
            # Memory check
            memory_limit_mb = self.config.int("monitoring.memory_limit_mb", 1000)
            if self.metrics.peak_memory_mb > memory_limit_mb:
                return "unhealthy_memory"
            
            # Error rate check
            if self.metrics.requests_processed > 10:
                error_rate = self.metrics.errors_encountered / self.metrics.requests_processed
                max_error_rate = self.config.float("monitoring.max_error_rate", 0.1)
                if error_rate > max_error_rate:
                    return "unhealthy_errors"
            
            return "healthy"
            
        except Exception as e:
            self.logger.warning(f"Health check error: {e}")
            return "unhealthy_check_failed"
    
    @contextmanager
    def track_request(self, operation_name: str = "request"):
        """Context manager for tracking request metrics."""
        start_time = time.time()
        success = True
        
        try:
            self.logger.debug(f"Starting {operation_name}")
            yield
            
        except Exception as e:
            success = False
            self.logger.error(f"Error in {operation_name}: {e}")
            raise
            
        finally:
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            with self._metrics_lock:
                self.metrics.record_request(response_time_ms, success)
            
            self.logger.debug(f"Completed {operation_name} in {response_time_ms:.2f}ms")
    
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self._metrics_lock:
            self.metrics.update_uptime()
            
            return {
                "agent_name": self.agent_name,
                "timestamp": datetime.now().isoformat(),
                "lifecycle": {
                    "uptime_seconds": self.metrics.uptime_seconds,
                    "restart_count": self.metrics.restart_count,
                    "health_status": self.metrics.health_status,
                },
                "performance": {
                    "requests_processed": self.metrics.requests_processed,
                    "errors_encountered": self.metrics.errors_encountered,
                    "avg_response_time_ms": self.metrics.avg_response_time_ms,
                    "error_rate": (self.metrics.errors_encountered / max(1, self.metrics.requests_processed)),
                },
                "resources": {
                    "peak_memory_mb": self.metrics.peak_memory_mb,
                    "cpu_usage_percent": self.metrics.cpu_usage_percent,
                },
                "custom": self.metrics.custom_metrics
            }
    
    def update_custom_metric(self, name: str, value: Any):
        """Update a custom metric."""
        with self._metrics_lock:
            self.metrics.custom_metrics[name] = value
            self.logger.debug(f"Updated custom metric {name} = {value}")
    
    def restart(self):
        """Restart the agent with metrics tracking."""
        self.logger.info(f"Restarting agent {self.agent_name}")
        
        with self._metrics_lock:
            self.metrics.restart_count += 1
            self.metrics.start_time = datetime.now()
        
        # Call parent restart if exists
        if hasattr(super(), 'restart'):
            super().restart()
    
    def shutdown(self):
        """Enhanced shutdown with cleanup."""
        self.logger.info(f"Shutting down agent {self.agent_name}")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for metrics thread
        if self._metrics_thread and self._metrics_thread.is_alive():
            self._metrics_thread.join(timeout=5)
        
        # Call parent shutdown
        if hasattr(super(), 'shutdown'):
            super().shutdown()
        
        self.logger.info(f"Agent {self.agent_name} shutdown complete")


class AgentFactory:
    """Factory for creating enhanced agents with standardized configuration."""
    
    @staticmethod
    def create_agent(
        agent_class: Type[BaseAgent],
        agent_name: str,
        config_overrides: Optional[Dict] = None,
        enhance_with_metrics: bool = True
    ) -> Union[BaseAgent, EnhancedBaseAgent]:
        """Create an agent instance with optional enhancements.
        
        Args:
            agent_class: The agent class to instantiate
            agent_name: Human-readable name for the agent
            config_overrides: Optional configuration overrides
            enhance_with_metrics: Whether to enhance with metrics (default: True)
        
        Returns:
            Agent instance (enhanced or basic)
        """
        try:
            if enhance_with_metrics:
                # Create enhanced agent wrapper
                class EnhancedAgent(EnhancedBaseAgent, agent_class):
                    def __init__(self):
                        EnhancedBaseAgent.__init__(self, agent_name, config_overrides)
                        # Initialize the original agent class if it has __init__
                        if hasattr(agent_class, '__init__'):
                            try:
                                agent_class.__init__(self)
                            except TypeError:
                                # Some agents might not accept __init__ parameters
                                pass
                
                agent = EnhancedAgent()
                
            else:
                # Create basic agent
                agent = agent_class()
                if hasattr(agent, 'agent_name'):
                    agent.agent_name = agent_name
            
            logging.getLogger("agent_factory").info(
                f"Created {'enhanced' if enhance_with_metrics else 'basic'} agent: {agent_name}"
            )
            
            return agent
            
        except Exception as e:
            logging.getLogger("agent_factory").error(f"Failed to create agent {agent_name}: {e}")
            raise
    
    @staticmethod
    def create_enhanced_agent(
        agent_class: Type[BaseAgent],
        agent_name: str,
        **kwargs
    ) -> EnhancedBaseAgent:
        """Convenience method to create enhanced agent."""
        return AgentFactory.create_agent(
            agent_class, agent_name, 
            config_overrides=kwargs,
            enhance_with_metrics=True
        )
    
    @staticmethod
    def get_agent_metrics(agent: Union[BaseAgent, EnhancedBaseAgent]) -> Optional[Dict[str, Any]]:
        """Get metrics from an agent if available."""
        if isinstance(agent, EnhancedBaseAgent):
            return agent.get_metrics_snapshot()
        return None


# Convenience functions for common use cases
def create_enhanced_agent(agent_class: Type[BaseAgent], name: str, **config) -> EnhancedBaseAgent:
    """Quick function to create enhanced agent."""
    return AgentFactory.create_enhanced_agent(agent_class, name, **config)

def get_agent_health(agent: Union[BaseAgent, EnhancedBaseAgent]) -> str:
    """Get agent health status."""
    if isinstance(agent, EnhancedBaseAgent):
        return agent.metrics.health_status
    return "unknown"
