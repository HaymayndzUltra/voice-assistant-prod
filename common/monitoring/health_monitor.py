#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Health Monitoring and Auto-Recovery - Phase 4.2

Comprehensive health monitoring system with automated failure detection,
circuit breaker patterns, and intelligent recovery mechanisms.

Part of Phase 4.2: Enhanced Agent Factory and Lifecycle Management - O3 Roadmap Implementation
"""

import logging
import threading
import time
import psutil
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import weakref

# Import lifecycle components
try:
    from common.logging.structured_logger import get_logger
    from common.lifecycle.agent_lifecycle import get_lifecycle_manager, LifecycleEvent
except ImportError:
    # Fallback implementations
    def get_logger(name):
        return logging.getLogger(name)
    
    def get_lifecycle_manager():
        class MockManager:
            def transition_agent(self, *args, **kwargs):
                return True
        return MockManager()
    
    class LifecycleEvent:
        RECOVERY_STARTED = "recovery_started"
        RECOVERY_COMPLETED = "recovery_completed"
        RECOVERY_FAILED = "recovery_failed"


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    RECOVERING = "recovering"
    FAILED = "failed"


@dataclass
class HealthMetrics:
    """Health metrics for an agent."""
    uptime_seconds: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    response_time_ms: float = 0.0
    error_count: int = 0
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    agent_id: str
    status: HealthStatus
    message: str
    metrics: HealthMetrics
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    check_duration_ms: float = 0.0


class HealthChecker(ABC):
    """Abstract base class for health checkers."""
    
    @abstractmethod
    async def check_health(self, agent_id: str, agent_instance: Any) -> HealthCheckResult:
        """Perform health check on an agent."""
        pass


class BasicHealthChecker(HealthChecker):
    """Basic health checker that verifies agent responsiveness."""
    
    async def check_health(self, agent_id: str, agent_instance: Any) -> HealthCheckResult:
        """Check basic agent health."""
        start_time = time.time()
        metrics = HealthMetrics()
        
        try:
            # Check if agent has basic attributes
            if hasattr(agent_instance, 'agent_name'):
                metrics.last_seen_at = datetime.now(timezone.utc)
            
            # Check if agent is responsive
            if hasattr(agent_instance, 'is_alive') and callable(agent_instance.is_alive):
                try:
                    is_alive = await asyncio.wait_for(
                        asyncio.to_thread(agent_instance.is_alive),
                        timeout=5.0
                    )
                    if not is_alive:
                        return HealthCheckResult(
                            agent_id=agent_id,
                            status=HealthStatus.CRITICAL,
                            message="Agent reports not alive",
                            metrics=metrics,
                            check_duration_ms=(time.time() - start_time) * 1000
                        )
                except asyncio.TimeoutError:
                    return HealthCheckResult(
                        agent_id=agent_id,
                        status=HealthStatus.CRITICAL,
                        message="Health check timeout",
                        metrics=metrics,
                        check_duration_ms=(time.time() - start_time) * 1000
                    )
            
            metrics.response_time_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                agent_id=agent_id,
                status=HealthStatus.HEALTHY,
                message="Basic health check passed",
                metrics=metrics,
                check_duration_ms=metrics.response_time_ms
            )
            
        except Exception as e:
            return HealthCheckResult(
                agent_id=agent_id,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {str(e)}",
                metrics=metrics,
                check_duration_ms=(time.time() - start_time) * 1000
            )


class ResourceHealthChecker(HealthChecker):
    """Health checker that monitors resource usage."""
    
    def __init__(self, max_cpu_percent: float = 80.0, max_memory_percent: float = 80.0):
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
    
    async def check_health(self, agent_id: str, agent_instance: Any) -> HealthCheckResult:
        """Check resource health."""
        start_time = time.time()
        metrics = HealthMetrics()
        
        try:
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            metrics.cpu_usage_percent = cpu_percent
            metrics.memory_usage_mb = memory.used / 1024 / 1024
            metrics.memory_usage_percent = memory.percent
            
            # Determine health status
            status = HealthStatus.HEALTHY
            messages = []
            
            if cpu_percent > self.max_cpu_percent:
                status = HealthStatus.WARNING if cpu_percent < 90 else HealthStatus.CRITICAL
                messages.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory.percent > self.max_memory_percent:
                if memory.percent > 90:
                    status = HealthStatus.CRITICAL
                elif status == HealthStatus.HEALTHY:
                    status = HealthStatus.WARNING
                messages.append(f"High memory usage: {memory.percent:.1f}%")
            
            message = "Resource usage normal" if not messages else "; ".join(messages)
            
            return HealthCheckResult(
                agent_id=agent_id,
                status=status,
                message=message,
                metrics=metrics,
                check_duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return HealthCheckResult(
                agent_id=agent_id,
                status=HealthStatus.UNKNOWN,
                message=f"Resource check failed: {str(e)}",
                metrics=metrics,
                check_duration_ms=(time.time() - start_time) * 1000
            )


class RecoveryStrategy(ABC):
    """Abstract base class for recovery strategies."""
    
    @abstractmethod
    async def recover(self, agent_id: str, agent_instance: Any) -> bool:
        """Attempt to recover an agent."""
        pass


class RestartRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy that restarts the agent."""
    
    async def recover(self, agent_id: str, agent_instance: Any) -> bool:
        """Attempt to recover by restarting the agent."""
        try:
            lifecycle_manager = get_lifecycle_manager()
            lifecycle_manager.transition_agent(agent_id, LifecycleEvent.RECOVERY_STARTED)
            
            # Restart the agent if it has restart method
            if hasattr(agent_instance, 'restart') and callable(agent_instance.restart):
                await asyncio.to_thread(agent_instance.restart)
                await asyncio.sleep(2.0)
                lifecycle_manager.transition_agent(agent_id, LifecycleEvent.RECOVERY_COMPLETED)
                return True
            
            lifecycle_manager.transition_agent(agent_id, LifecycleEvent.RECOVERY_FAILED)
            return False
            
        except Exception as e:
            logging.getLogger("restart_recovery").error(f"Recovery failed for agent {agent_id}: {e}")
            return False


class HealthMonitor:
    """Central health monitoring system with auto-recovery."""
    
    def __init__(self, check_interval_seconds: float = 30.0):
        self.check_interval_seconds = check_interval_seconds
        self.health_checkers: List[HealthChecker] = []
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self.monitored_agents: Dict[str, weakref.ReferenceType] = {}
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.auto_recovery_enabled: Dict[str, bool] = {}
        
        self._monitoring_task = None
        self._stop_monitoring = threading.Event()
        self.logger = get_logger("health_monitor")
        
        # Initialize default components
        self.add_health_checker(BasicHealthChecker())
        self.add_health_checker(ResourceHealthChecker())
        self.add_recovery_strategy("restart", RestartRecoveryStrategy())
    
    def add_health_checker(self, checker: HealthChecker):
        """Add a health checker."""
        self.health_checkers.append(checker)
    
    def add_recovery_strategy(self, name: str, strategy: RecoveryStrategy):
        """Add a recovery strategy."""
        self.recovery_strategies[name] = strategy
    
    def register_agent(self, agent_id: str, agent_instance: Any, auto_recovery: bool = True):
        """Register an agent for health monitoring."""
        self.monitored_agents[agent_id] = weakref.ref(agent_instance)
        self.health_history[agent_id] = []
        self.auto_recovery_enabled[agent_id] = auto_recovery
        self.logger.info(f"Registered agent {agent_id} for health monitoring")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from health monitoring."""
        self.monitored_agents.pop(agent_id, None)
        self.health_history.pop(agent_id, None)
        self.auto_recovery_enabled.pop(agent_id, None)
        self.logger.info(f"Unregistered agent {agent_id}")
    
    async def check_agent_health(self, agent_id: str) -> List[HealthCheckResult]:
        """Run all health checks for a specific agent."""
        if agent_id not in self.monitored_agents:
            return []
        
        agent_ref = self.monitored_agents[agent_id]
        agent_instance = agent_ref()
        
        if agent_instance is None:
            self.unregister_agent(agent_id)
            return []
        
        results = []
        for checker in self.health_checkers:
            try:
                result = await checker.check_health(agent_id, agent_instance)
                results.append(result)
                
                # Store in history (keep last 100)
                if agent_id not in self.health_history:
                    self.health_history[agent_id] = []
                self.health_history[agent_id].append(result)
                if len(self.health_history[agent_id]) > 100:
                    self.health_history[agent_id] = self.health_history[agent_id][-100:]
                
            except Exception as e:
                self.logger.error(f"Health check failed for agent {agent_id}: {e}")
        
        return results
    
    async def _attempt_recovery(self, agent_id: str, health_results: List[HealthCheckResult]):
        """Attempt to recover an unhealthy agent."""
        if not self.auto_recovery_enabled.get(agent_id, False):
            return
        
        # Check if recovery is needed
        needs_recovery = any(r.status == HealthStatus.CRITICAL for r in health_results)
        if not needs_recovery:
            return
        
        agent_ref = self.monitored_agents.get(agent_id)
        if not agent_ref:
            return
        
        agent_instance = agent_ref()
        if agent_instance is None:
            return
        
        # Try recovery strategies
        for strategy_name, strategy in self.recovery_strategies.items():
            try:
                self.logger.info(f"Attempting {strategy_name} recovery for agent {agent_id}")
                success = await strategy.recover(agent_id, agent_instance)
                
                if success:
                    self.logger.info(f"Recovery successful for agent {agent_id}")
                    return
                
            except Exception as e:
                self.logger.error(f"Recovery strategy {strategy_name} failed: {e}")
        
        self.logger.error(f"All recovery strategies failed for agent {agent_id}")
    
    async def start_monitoring(self):
        """Start the health monitoring loop."""
        if self._monitoring_task is not None:
            return
        
        self._stop_monitoring.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop the health monitoring loop."""
        if self._monitoring_task is None:
            return
        
        self._stop_monitoring.set()
        await self._monitoring_task
        self._monitoring_task = None
        self.logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while not self._stop_monitoring.is_set():
            try:
                for agent_id in list(self.monitored_agents.keys()):
                    health_results = await self.check_agent_health(agent_id)
                    
                    if health_results:
                        overall_status = self._determine_overall_status(health_results)
                        self.logger.debug(f"Agent {agent_id} health: {overall_status.value}")
                        await self._attempt_recovery(agent_id, health_results)
                
                await asyncio.sleep(self.check_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5.0)
    
    def _determine_overall_status(self, health_results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from multiple check results."""
        if not health_results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in health_results]
        
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def get_agent_health_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get health summary for an agent."""
        if agent_id not in self.health_history or not self.health_history[agent_id]:
            return None
        
        recent_results = self.health_history[agent_id][-10:]
        current_result = recent_results[-1]
        
        successful_checks = sum(1 for r in recent_results if r.status == HealthStatus.HEALTHY)
        success_rate = (successful_checks / len(recent_results)) * 100
        
        return {
            'agent_id': agent_id,
            'current_status': current_result.status.value,
            'last_check_at': current_result.timestamp.isoformat(),
            'success_rate_percent': success_rate,
            'auto_recovery_enabled': self.auto_recovery_enabled.get(agent_id, False)
        }


# Global health monitor instance
_global_health_monitor = None
_health_monitor_lock = threading.Lock()


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    global _global_health_monitor
    
    if _global_health_monitor is None:
        with _health_monitor_lock:
            if _global_health_monitor is None:
                _global_health_monitor = HealthMonitor()
    
    return _global_health_monitor


# Convenience functions
def register_agent_health_monitoring(agent_id: str, agent_instance: Any, auto_recovery: bool = True):
    """Register an agent for health monitoring."""
    monitor = get_health_monitor()
    monitor.register_agent(agent_id, agent_instance, auto_recovery)


async def start_health_monitoring():
    """Start the global health monitoring system."""
    monitor = get_health_monitor()
    await monitor.start_monitoring()


async def stop_health_monitoring():
    """Stop the global health monitoring system."""
    monitor = get_health_monitor()
    await monitor.stop_monitoring()
