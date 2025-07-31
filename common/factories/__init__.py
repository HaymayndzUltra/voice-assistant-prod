#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common Factories Module

Provides factory patterns for creating enhanced agents and components
with standardized configuration, metrics, and monitoring.

Extended in Phase 4.2: Enhanced Agent Factory and Lifecycle Management
"""

from .agent_factory import (
    AgentFactory,
    EnhancedBaseAgent,
    AgentMetrics,
    create_enhanced_agent,
    get_agent_health
)

# Enhanced Agent Factory (Phase 4.2)
try:
    from .enhanced_agent_factory import (
        EnhancedAgentFactory,
        AgentTemplate,
        AgentBlueprint,
        DependencyContainer,
        DependencyScope,
        get_enhanced_factory,
        create_ml_worker_agent,
        create_service_mesh_agent,
        create_fault_tolerant_agent
    )
    ENHANCED_FACTORY_AVAILABLE = True
    
    __enhanced_exports = [
        "EnhancedAgentFactory",
        "AgentTemplate",
        "AgentBlueprint",
        "DependencyContainer",
        "DependencyScope",
        "get_enhanced_factory",
        "create_ml_worker_agent",
        "create_service_mesh_agent",
        "create_fault_tolerant_agent"
    ]
except ImportError:
    ENHANCED_FACTORY_AVAILABLE = False
    __enhanced_exports = []

__all__ = [
    # Original factory components
    "AgentFactory",
    "EnhancedBaseAgent", 
    "AgentMetrics",
    "create_enhanced_agent",
    "get_agent_health",
    
    # Enhanced factory availability
    "ENHANCED_FACTORY_AVAILABLE"
] + __enhanced_exports

# Version info
__version__ = "4.2.0"
__phase__ = "Phase 4.2: Enhanced Agent Factory and Lifecycle Management"
