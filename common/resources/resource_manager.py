#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource Allocation Optimization - Phase 4.2

Advanced resource management with pools, load balancing, memory optimization,
and intelligent CPU scheduling. Provides enterprise-grade resource efficiency
and performance optimization.

Part of Phase 4.2: Enhanced Agent Factory and Lifecycle Management - O3 Roadmap Implementation
"""

import logging
import threading
import time
import psutil
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from enum import Enum, auto
import heapq
import weakref
from collections import defaultdict, deque

# Import logging and monitoring components
try:
    from common.logging.structured_logger import get_logger
    from common.monitoring.health_monitor import get_health_monitor
except ImportError:
    def get_logger(name):
        return logging.getLogger(name)
    
    def get_health_monitor():
        class MockMonitor:
            def register_agent(self, *args, **kwargs):
                pass
        return MockMonitor()


class ResourceType(Enum):
    """Types of resources that can be managed."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    THREAD_POOL = "thread_pool"
    CONNECTION_POOL = "connection_pool"
    CUSTOM = "custom"


class AllocationStrategy(Enum):
    """Resource allocation strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    PRIORITY_BASED = "priority_based"
    RESOURCE_AWARE = "resource_aware"
    LOCALITY_AWARE = "locality_aware"


@dataclass
class ResourceQuota:
    """Resource quota definition."""
    resource_type: ResourceType
    max_allocation: float
    current_allocation: float = 0.0
    reserved_allocation: float = 0.0
    unit: str = "percent"  # percent, bytes, count, etc.


@dataclass
class ResourceRequest:
    """Resource allocation request."""
    requester_id: str
    resource_type: ResourceType
    amount: float
    priority: int = 0
    duration_seconds: Optional[float] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResourceAllocation:
    """Active resource allocation."""
    allocation_id: str
    requester_id: str
    resource_type: ResourceType
    allocated_amount: float
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourcePool:
    """Manages a pool of resources of a specific type."""
    
    def __init__(
        self,
        resource_type: ResourceType,
        total_capacity: float,
        allocation_strategy: AllocationStrategy = AllocationStrategy.LEAST_LOADED
    ):
        self.resource_type = resource_type
        self.total_capacity = total_capacity
        self.allocation_strategy = allocation_strategy
        self.available_capacity = total_capacity
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.pending_requests: List[ResourceRequest] = []
        self.allocation_history: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        self.logger = get_logger(f"resource_pool_{resource_type.value}")
    
    def request_allocation(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """Request resource allocation."""
        with self._lock:
            # Check if we have enough capacity
            if request.amount > self.available_capacity:
                # Add to pending requests if we can't satisfy immediately
                self.pending_requests.append(request)
                self.logger.warning(
                    f"Insufficient capacity for {request.resource_type.value} request: "
                    f"requested={request.amount}, available={self.available_capacity}"
                )
                return None
            
            # Create allocation
            allocation_id = f"{request.requester_id}_{int(time.time() * 1000)}"
            expires_at = None
            if request.duration_seconds:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=request.duration_seconds)
            
            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                requester_id=request.requester_id,
                resource_type=request.resource_type,
                allocated_amount=request.amount,
                allocated_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                metadata=request.constraints.copy()
            )
            
            # Update capacity
            self.available_capacity -= request.amount
            self.allocations[allocation_id] = allocation
            self.allocation_history.append(allocation)
            
            self.logger.info(
                f"Allocated {request.amount} {request.resource_type.value} to {request.requester_id}"
            )
            
            return allocation
    
    def release_allocation(self, allocation_id: str) -> bool:
        """Release a resource allocation."""
        with self._lock:
            if allocation_id not in self.allocations:
                return False
            
            allocation = self.allocations[allocation_id]
            self.available_capacity += allocation.allocated_amount
            del self.allocations[allocation_id]
            
            self.logger.info(
                f"Released {allocation.allocated_amount} {allocation.resource_type.value} "
                f"from {allocation.requester_id}"
            )
            
            # Try to satisfy pending requests
            self._process_pending_requests()
            
            return True
    
    def _process_pending_requests(self):
        """Process pending requests with available capacity."""
        satisfied_requests = []
        
        # Sort pending requests by priority
        self.pending_requests.sort(key=lambda r: r.priority, reverse=True)
        
        for i, request in enumerate(self.pending_requests):
            if request.amount <= self.available_capacity:
                allocation = self._create_allocation_from_request(request)
                if allocation:
                    satisfied_requests.append(i)
        
        # Remove satisfied requests
        for i in reversed(satisfied_requests):
            del self.pending_requests[i]
    
    def _create_allocation_from_request(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """Create allocation from request without checking pending queue."""
        allocation_id = f"{request.requester_id}_{int(time.time() * 1000)}"
        expires_at = None
        if request.duration_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=request.duration_seconds)
        
        allocation = ResourceAllocation(
            allocation_id=allocation_id,
            requester_id=request.requester_id,
            resource_type=request.resource_type,
            allocated_amount=request.amount,
            allocated_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            metadata=request.constraints.copy()
        )
        
        self.available_capacity -= request.amount
        self.allocations[allocation_id] = allocation
        self.allocation_history.append(allocation)
        
        return allocation
    
    def cleanup_expired_allocations(self):
        """Clean up expired allocations."""
        now = datetime.now(timezone.utc)
        expired_allocations = []
        
        with self._lock:
            for allocation_id, allocation in self.allocations.items():
                if allocation.expires_at and allocation.expires_at <= now:
                    expired_allocations.append(allocation_id)
            
            for allocation_id in expired_allocations:
                self.release_allocation(allocation_id)
    
    def get_utilization(self) -> float:
        """Get current resource utilization percentage."""
        return ((self.total_capacity - self.available_capacity) / self.total_capacity) * 100
    
    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get allocation summary for this pool."""
        with self._lock:
            return {
                'resource_type': self.resource_type.value,
                'total_capacity': self.total_capacity,
                'available_capacity': self.available_capacity,
                'utilization_percent': self.get_utilization(),
                'active_allocations': len(self.allocations),
                'pending_requests': len(self.pending_requests),
                'allocation_strategy': self.allocation_strategy.value
            }


class LoadBalancer:
    """Load balancer for distributing work across agents."""
    
    def __init__(self, strategy: AllocationStrategy = AllocationStrategy.LEAST_LOADED):
        self.strategy = strategy
        self.agents: Dict[str, Dict[str, Any]] = {}  # agent_id -> metadata
        self.load_metrics: Dict[str, float] = {}  # agent_id -> current load
        self.weights: Dict[str, float] = {}  # agent_id -> weight
        self.round_robin_index = 0
        self._lock = threading.Lock()
        self.logger = get_logger("load_balancer")
    
    def register_agent(self, agent_id: str, weight: float = 1.0, metadata: Optional[Dict] = None):
        """Register an agent for load balancing."""
        with self._lock:
            self.agents[agent_id] = metadata or {}
            self.load_metrics[agent_id] = 0.0
            self.weights[agent_id] = weight
            self.logger.info(f"Registered agent {agent_id} with weight {weight}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from load balancing."""
        with self._lock:
            self.agents.pop(agent_id, None)
            self.load_metrics.pop(agent_id, None)
            self.weights.pop(agent_id, None)
            self.logger.info(f"Unregistered agent {agent_id}")
    
    def update_agent_load(self, agent_id: str, load: float):
        """Update the current load for an agent."""
        with self._lock:
            if agent_id in self.load_metrics:
                self.load_metrics[agent_id] = load
    
    def select_agent(self, constraints: Optional[Dict] = None) -> Optional[str]:
        """Select an agent based on the load balancing strategy."""
        with self._lock:
            available_agents = list(self.agents.keys())
            
            if not available_agents:
                return None
            
            # Apply constraints if provided
            if constraints:
                available_agents = self._filter_agents_by_constraints(available_agents, constraints)
                if not available_agents:
                    return None
            
            # Select agent based on strategy
            if self.strategy == AllocationStrategy.ROUND_ROBIN:
                return self._select_round_robin(available_agents)
            elif self.strategy == AllocationStrategy.LEAST_LOADED:
                return self._select_least_loaded(available_agents)
            elif self.strategy == AllocationStrategy.WEIGHTED_ROUND_ROBIN:
                return self._select_weighted_round_robin(available_agents)
            elif self.strategy == AllocationStrategy.PRIORITY_BASED:
                return self._select_priority_based(available_agents, constraints)
            else:
                return self._select_least_loaded(available_agents)
    
    def _filter_agents_by_constraints(self, agents: List[str], constraints: Dict) -> List[str]:
        """Filter agents based on constraints."""
        filtered = []
        for agent_id in agents:
            agent_metadata = self.agents[agent_id]
            
            # Check if agent satisfies constraints
            satisfies_constraints = True
            for key, value in constraints.items():
                if key in agent_metadata and agent_metadata[key] != value:
                    satisfies_constraints = False
                    break
            
            if satisfies_constraints:
                filtered.append(agent_id)
        
        return filtered
    
    def _select_round_robin(self, agents: List[str]) -> str:
        """Select agent using round-robin strategy."""
        if not agents:
            return None
        
        agent = agents[self.round_robin_index % len(agents)]
        self.round_robin_index += 1
        return agent
    
    def _select_least_loaded(self, agents: List[str]) -> str:
        """Select agent with least load."""
        if not agents:
            return None
        
        return min(agents, key=lambda a: self.load_metrics.get(a, 0.0))
    
    def _select_weighted_round_robin(self, agents: List[str]) -> str:
        """Select agent using weighted round-robin."""
        if not agents:
            return None
        
        # Simple weighted selection based on inverse of current load
        weights = []
        for agent_id in agents:
            load = self.load_metrics.get(agent_id, 0.0)
            weight = self.weights.get(agent_id, 1.0)
            # Higher weight for lower load
            effective_weight = weight / (load + 0.1)  # Add small constant to avoid division by zero
            weights.append(effective_weight)
        
        # Select based on weights
        total_weight = sum(weights)
        if total_weight == 0:
            return agents[0]
        
        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return agents[i]
        
        return agents[-1]
    
    def _select_priority_based(self, agents: List[str], constraints: Optional[Dict]) -> str:
        """Select agent based on priority."""
        if not agents:
            return None
        
        # Use priority from constraints if provided
        priority = constraints.get('priority', 0) if constraints else 0
        
        # For now, select least loaded agent with consideration of priority
        # This can be enhanced with more sophisticated priority logic
        return self._select_least_loaded(agents)
    
    def get_load_distribution(self) -> Dict[str, float]:
        """Get current load distribution across all agents."""
        with self._lock:
            return self.load_metrics.copy()


class MemoryOptimizer:
    """Memory optimization and management."""
    
    def __init__(self, target_usage_percent: float = 80.0):
        self.target_usage_percent = target_usage_percent
        self.memory_pools: Dict[str, Any] = {}
        self.cleanup_callbacks: List[Callable] = []
        self.logger = get_logger("memory_optimizer")
    
    def register_cleanup_callback(self, callback: Callable):
        """Register a callback for memory cleanup."""
        self.cleanup_callbacks.append(callback)
    
    def check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        memory = psutil.virtual_memory()
        return memory.percent > self.target_usage_percent
    
    def optimize_memory(self):
        """Perform memory optimization."""
        if not self.check_memory_pressure():
            return
        
        self.logger.info("Memory pressure detected, running optimization")
        
        # Run cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Memory cleanup callback failed: {e}")
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Log results
        memory = psutil.virtual_memory()
        self.logger.info(f"Memory optimization complete, usage: {memory.percent:.1f}%")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics."""
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / 1024**3,
            'available_gb': memory.available / 1024**3,
            'used_gb': memory.used / 1024**3,
            'usage_percent': memory.percent,
            'under_pressure': self.check_memory_pressure()
        }


class ResourceManager:
    """Central resource management system."""
    
    def __init__(self):
        self.resource_pools: Dict[ResourceType, ResourcePool] = {}
        self.load_balancer = LoadBalancer()
        self.memory_optimizer = MemoryOptimizer()
        self.quotas: Dict[str, List[ResourceQuota]] = {}  # user_id -> quotas
        self.active_allocations: Dict[str, List[ResourceAllocation]] = defaultdict(list)
        
        self._cleanup_task = None
        self._monitoring_task = None
        self._stop_monitoring = threading.Event()
        self.logger = get_logger("resource_manager")
        
        # Initialize default resource pools
        self._initialize_default_pools()
    
    def _initialize_default_pools(self):
        """Initialize default resource pools."""
        # CPU pool (percentage-based)
        cpu_count = psutil.cpu_count()
        self.add_resource_pool(ResourceType.CPU, cpu_count * 100.0)  # 100% per CPU core
        
        # Memory pool (MB-based)
        memory = psutil.virtual_memory()
        memory_mb = memory.total / 1024 / 1024
        self.add_resource_pool(ResourceType.MEMORY, memory_mb * 0.8)  # 80% of total memory
        
        # Thread pool
        self.add_resource_pool(ResourceType.THREAD_POOL, 100)  # 100 threads
        
        # Connection pool
        self.add_resource_pool(ResourceType.CONNECTION_POOL, 1000)  # 1000 connections
    
    def add_resource_pool(
        self,
        resource_type: ResourceType,
        capacity: float,
        strategy: AllocationStrategy = AllocationStrategy.LEAST_LOADED
    ):
        """Add a new resource pool."""
        pool = ResourcePool(resource_type, capacity, strategy)
        self.resource_pools[resource_type] = pool
        self.logger.info(f"Added resource pool: {resource_type.value} (capacity: {capacity})")
    
    def request_resources(self, request: ResourceRequest) -> Optional[ResourceAllocation]:
        """Request resource allocation."""
        if request.resource_type not in self.resource_pools:
            self.logger.error(f"Resource type {request.resource_type.value} not available")
            return None
        
        # Check quotas
        if not self._check_quota(request.requester_id, request):
            self.logger.warning(f"Quota exceeded for {request.requester_id}")
            return None
        
        pool = self.resource_pools[request.resource_type]
        allocation = pool.request_allocation(request)
        
        if allocation:
            self.active_allocations[request.requester_id].append(allocation)
            self.logger.info(
                f"Resource allocated: {allocation.allocated_amount} {allocation.resource_type.value} "
                f"to {allocation.requester_id}"
            )
        
        return allocation
    
    def release_resources(self, allocation_id: str, requester_id: str) -> bool:
        """Release resource allocation."""
        # Find the allocation
        allocation = None
        for alloc in self.active_allocations[requester_id]:
            if alloc.allocation_id == allocation_id:
                allocation = alloc
                break
        
        if not allocation:
            return False
        
        # Release from pool
        pool = self.resource_pools.get(allocation.resource_type)
        if pool and pool.release_allocation(allocation_id):
            self.active_allocations[requester_id].remove(allocation)
            return True
        
        return False
    
    def set_quota(self, user_id: str, quotas: List[ResourceQuota]):
        """Set resource quotas for a user."""
        self.quotas[user_id] = quotas
        self.logger.info(f"Set quotas for {user_id}: {len(quotas)} quota(s)")
    
    def _check_quota(self, user_id: str, request: ResourceRequest) -> bool:
        """Check if request is within quota limits."""
        if user_id not in self.quotas:
            return True  # No quota set means unlimited
        
        user_quotas = self.quotas[user_id]
        for quota in user_quotas:
            if quota.resource_type == request.resource_type:
                # Calculate current usage
                current_usage = sum(
                    alloc.allocated_amount
                    for alloc in self.active_allocations[user_id]
                    if alloc.resource_type == request.resource_type
                )
                
                if current_usage + request.amount > quota.max_allocation:
                    return False
        
        return True
    
    def register_agent_for_load_balancing(self, agent_id: str, weight: float = 1.0, metadata: Optional[Dict] = None):
        """Register an agent for load balancing."""
        self.load_balancer.register_agent(agent_id, weight, metadata)
    
    def select_agent_for_work(self, constraints: Optional[Dict] = None) -> Optional[str]:
        """Select an agent for work assignment."""
        return self.load_balancer.select_agent(constraints)
    
    def update_agent_load(self, agent_id: str, load: float):
        """Update agent load metrics."""
        self.load_balancer.update_agent_load(agent_id, load)
    
    async def start_monitoring(self):
        """Start resource monitoring and cleanup tasks."""
        if self._monitoring_task is not None:
            return
        
        self._stop_monitoring.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Resource monitoring started")
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        if self._monitoring_task is None:
            return
        
        self._stop_monitoring.set()
        await self._monitoring_task
        self._monitoring_task = None
        self.logger.info("Resource monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring and cleanup loop."""
        while not self._stop_monitoring.is_set():
            try:
                # Cleanup expired allocations
                for pool in self.resource_pools.values():
                    pool.cleanup_expired_allocations()
                
                # Check memory pressure and optimize if needed
                self.memory_optimizer.optimize_memory()
                
                # Wait before next iteration
                await asyncio.sleep(60.0)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in resource monitoring loop: {e}")
                await asyncio.sleep(10.0)
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive resource usage summary."""
        summary = {
            'pools': {},
            'memory_stats': self.memory_optimizer.get_memory_stats(),
            'load_distribution': self.load_balancer.get_load_distribution(),
            'total_active_allocations': sum(len(allocs) for allocs in self.active_allocations.values())
        }
        
        for resource_type, pool in self.resource_pools.items():
            summary['pools'][resource_type.value] = pool.get_allocation_summary()
        
        return summary


# Global resource manager instance
_global_resource_manager = None
_resource_manager_lock = threading.Lock()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance."""
    global _global_resource_manager
    
    if _global_resource_manager is None:
        with _resource_manager_lock:
            if _global_resource_manager is None:
                _global_resource_manager = ResourceManager()
    
    return _global_resource_manager


# Convenience functions
def request_cpu_allocation(requester_id: str, cpu_cores: float, duration_seconds: Optional[float] = None) -> Optional[ResourceAllocation]:
    """Request CPU allocation."""
    manager = get_resource_manager()
    request = ResourceRequest(
        requester_id=requester_id,
        resource_type=ResourceType.CPU,
        amount=cpu_cores * 100,  # Convert to percentage
        duration_seconds=duration_seconds
    )
    return manager.request_resources(request)


def request_memory_allocation(requester_id: str, memory_mb: float, duration_seconds: Optional[float] = None) -> Optional[ResourceAllocation]:
    """Request memory allocation."""
    manager = get_resource_manager()
    request = ResourceRequest(
        requester_id=requester_id,
        resource_type=ResourceType.MEMORY,
        amount=memory_mb,
        duration_seconds=duration_seconds
    )
    return manager.request_resources(request)


def release_allocation(allocation_id: str, requester_id: str) -> bool:
    """Release a resource allocation."""
    manager = get_resource_manager()
    return manager.release_resources(allocation_id, requester_id)


async def start_resource_monitoring():
    """Start the global resource monitoring system."""
    manager = get_resource_manager()
    await manager.start_monitoring()
