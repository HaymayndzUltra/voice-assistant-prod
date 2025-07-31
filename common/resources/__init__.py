#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resource Management Package - Phase 4.2

Advanced resource allocation optimization with pools, load balancing,
memory optimization, and intelligent CPU scheduling.

Part of Phase 4.2: Enhanced Agent Factory and Lifecycle Management - O3 Roadmap Implementation
"""

__version__ = "4.2.0"
__author__ = "AI System Monorepo Team"
__description__ = "Resource Allocation and Optimization System"

# Core resource management components
from .resource_manager import (
    # Enums and types
    ResourceType,
    AllocationStrategy,
    
    # Data classes
    ResourceQuota,
    ResourceRequest,
    ResourceAllocation,
    
    # Core management classes
    ResourcePool,
    LoadBalancer,
    MemoryOptimizer,
    ResourceManager,
    
    # Global instance and convenience functions
    get_resource_manager,
    request_cpu_allocation,
    request_memory_allocation,
    release_allocation,
    start_resource_monitoring,
)

# Convenience imports for common use cases
__all__ = [
    # Core classes
    "ResourceManager",
    "ResourcePool",
    "LoadBalancer",
    "MemoryOptimizer",
    
    # Enums
    "ResourceType",
    "AllocationStrategy",
    
    # Data classes
    "ResourceQuota",
    "ResourceRequest",
    "ResourceAllocation",
    
    # Factory functions
    "get_resource_manager",
    "request_cpu_allocation",
    "request_memory_allocation",
    "release_allocation",
    "start_resource_monitoring",
    
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
]


def setup_resource_management(auto_start_monitoring: bool = True) -> ResourceManager:
    """
    Setup resource management system.
    
    Args:
        auto_start_monitoring: Whether to automatically start resource monitoring
        
    Returns:
        ResourceManager: Configured resource manager instance
        
    Example:
        >>> from common.resources import setup_resource_management
        >>> manager = setup_resource_management()
        >>> print(f"Resource manager initialized with {len(manager.resource_pools)} pools")
    """
    import asyncio
    
    manager = get_resource_manager()
    
    if auto_start_monitoring:
        # Start monitoring in a new event loop if none exists
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule monitoring to start
                asyncio.create_task(manager.start_monitoring())
            else:
                loop.run_until_complete(manager.start_monitoring())
        except RuntimeError:
            # No event loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.start_monitoring())
    
    return manager


def request_resources(
    requester_id: str,
    resource_type: str,
    amount: float,
    duration_seconds: float = None,
    priority: int = 0
) -> ResourceAllocation:
    """
    Request resource allocation with simplified interface.
    
    Args:
        requester_id: Identifier for the resource requester
        resource_type: Type of resource ('cpu', 'memory', 'thread_pool', etc.)
        amount: Amount of resource to allocate
        duration_seconds: Optional duration for the allocation
        priority: Priority of the request (higher = more priority)
        
    Returns:
        ResourceAllocation: Allocation object if successful, None otherwise
        
    Example:
        >>> from common.resources import request_resources
        >>> allocation = request_resources("agent_001", "memory", 512.0, duration_seconds=300)
        >>> if allocation:
        ...     print(f"Allocated {allocation.allocated_amount} MB memory")
    """
    manager = get_resource_manager()
    
    # Convert string resource type to enum
    resource_type_map = {
        'cpu': ResourceType.CPU,
        'memory': ResourceType.MEMORY,
        'disk': ResourceType.DISK,
        'network': ResourceType.NETWORK,
        'gpu': ResourceType.GPU,
        'thread_pool': ResourceType.THREAD_POOL,
        'connection_pool': ResourceType.CONNECTION_POOL,
    }
    
    resource_enum = resource_type_map.get(resource_type.lower())
    if not resource_enum:
        raise ValueError(f"Unknown resource type: {resource_type}")
    
    request = ResourceRequest(
        requester_id=requester_id,
        resource_type=resource_enum,
        amount=amount,
        priority=priority,
        duration_seconds=duration_seconds
    )
    
    return manager.request_resources(request)


def setup_load_balancing(agent_configs: list) -> LoadBalancer:
    """
    Setup load balancing for multiple agents.
    
    Args:
        agent_configs: List of agent configuration dicts with 'agent_id', 'weight', and optional 'metadata'
        
    Returns:
        LoadBalancer: Configured load balancer
        
    Example:
        >>> from common.resources import setup_load_balancing
        >>> configs = [
        ...     {'agent_id': 'agent_001', 'weight': 1.0, 'metadata': {'type': 'cpu_intensive'}},
        ...     {'agent_id': 'agent_002', 'weight': 0.5, 'metadata': {'type': 'memory_intensive'}}
        ... ]
        >>> balancer = setup_load_balancing(configs)
        >>> selected = balancer.select_agent({'type': 'cpu_intensive'})
    """
    manager = get_resource_manager()
    
    for config in agent_configs:
        agent_id = config['agent_id']
        weight = config.get('weight', 1.0)
        metadata = config.get('metadata', {})
        
        manager.register_agent_for_load_balancing(agent_id, weight, metadata)
    
    return manager.load_balancer


def set_resource_quotas(user_id: str, quotas: dict):
    """
    Set resource quotas for a user with simplified interface.
    
    Args:
        user_id: User identifier
        quotas: Dict mapping resource types to max allocations
        
    Example:
        >>> from common.resources import set_resource_quotas
        >>> quotas = {
        ...     'cpu': 400.0,  # 4 CPU cores worth (400%)
        ...     'memory': 2048.0,  # 2GB memory
        ...     'thread_pool': 50  # 50 threads
        ... }
        >>> set_resource_quotas("user_001", quotas)
    """
    manager = get_resource_manager()
    
    quota_objects = []
    for resource_type_str, max_allocation in quotas.items():
        # Convert string to enum
        resource_type_map = {
            'cpu': ResourceType.CPU,
            'memory': ResourceType.MEMORY,
            'disk': ResourceType.DISK,
            'network': ResourceType.NETWORK,
            'gpu': ResourceType.GPU,
            'thread_pool': ResourceType.THREAD_POOL,
            'connection_pool': ResourceType.CONNECTION_POOL,
        }
        
        resource_enum = resource_type_map.get(resource_type_str.lower())
        if resource_enum:
            quota = ResourceQuota(
                resource_type=resource_enum,
                max_allocation=max_allocation
            )
            quota_objects.append(quota)
    
    manager.set_quota(user_id, quota_objects)


def get_resource_utilization() -> dict:
    """
    Get current resource utilization across all pools.
    
    Returns:
        dict: Resource utilization summary
        
    Example:
        >>> from common.resources import get_resource_utilization
        >>> utilization = get_resource_utilization()
        >>> for pool, stats in utilization['pools'].items():
        ...     print(f"{pool}: {stats['utilization_percent']:.1f}% utilized")
    """
    manager = get_resource_manager()
    return manager.get_resource_summary()


def optimize_memory():
    """
    Trigger memory optimization across the system.
    
    Example:
        >>> from common.resources import optimize_memory
        >>> optimize_memory()  # Triggers cleanup and garbage collection
    """
    manager = get_resource_manager()
    manager.memory_optimizer.optimize_memory()


# Package configuration
RESOURCE_CONFIG = {
    'version': __version__,
    'components': {
        'resource_manager': 'ResourceManager',
        'resource_pools': 'ResourcePool',
        'load_balancer': 'LoadBalancer',
        'memory_optimizer': 'MemoryOptimizer'
    },
    'features': {
        'resource_allocation': True,
        'load_balancing': True,
        'memory_optimization': True,
        'quota_management': True,
        'monitoring_integration': True
    },
    'default_resource_types': [
        'cpu', 'memory', 'thread_pool', 'connection_pool'
    ]
}


def get_package_info() -> dict:
    """Get package information and configuration."""
    return RESOURCE_CONFIG.copy()


# Example usage in docstring
"""
Example Usage:

    # Basic resource allocation
    from common.resources import setup_resource_management, request_resources
    
    # Setup the resource management system
    manager = setup_resource_management()
    
    # Request CPU and memory resources
    cpu_alloc = request_resources("agent_001", "cpu", 200.0, duration_seconds=600)  # 2 CPU cores for 10 minutes
    mem_alloc = request_resources("agent_001", "memory", 1024.0)  # 1GB memory
    
    # Check resource utilization
    from common.resources import get_resource_utilization
    stats = get_resource_utilization()
    print(f"Memory pool utilization: {stats['pools']['memory']['utilization_percent']:.1f}%")
    
    # Setup load balancing
    from common.resources import setup_load_balancing
    agent_configs = [
        {'agent_id': 'worker_1', 'weight': 1.0, 'metadata': {'type': 'cpu_worker'}},
        {'agent_id': 'worker_2', 'weight': 1.5, 'metadata': {'type': 'gpu_worker'}},
    ]
    balancer = setup_load_balancing(agent_configs)
    
    # Select agent for work
    selected_agent = balancer.select_agent({'type': 'cpu_worker'})
    print(f"Selected agent: {selected_agent}")
    
    # Set quotas
    from common.resources import set_resource_quotas
    set_resource_quotas("user_001", {
        'cpu': 800.0,  # 8 CPU cores
        'memory': 4096.0,  # 4GB memory
    })
"""
