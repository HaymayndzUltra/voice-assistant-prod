#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent Lifecycle Management Package - Phase 4.2

Comprehensive agent lifecycle management with state machines, event handling,
state persistence, and transition validation.

Part of Phase 4.2: Enhanced Agent Factory and Lifecycle Management - O3 Roadmap Implementation
"""

__version__ = "4.2.0"
__author__ = "AI System Monorepo Team"
__description__ = "Agent Lifecycle Management System"

# Core lifecycle components
from .agent_lifecycle import (
    # State and event enums
    AgentState,
    LifecycleEvent,
    
    # Data classes
    StateTransition,
    AgentStateSnapshot,
    
    # Core management classes
    StateTransitionValidator,
    AgentLifecycleManager,
    StatePersistenceManager,
    
    # Event handlers
    LifecycleEventHandler,
    LoggingEventHandler,
    AuditEventHandler,
    
    # Global instance and convenience functions
    get_lifecycle_manager,
    register_agent_lifecycle,
    transition_agent_state,
    get_agent_current_state,
)

# Convenience imports for common use cases
__all__ = [
    # Core classes
    "AgentLifecycleManager",
    "StateTransitionValidator",
    "StatePersistenceManager",
    
    # Enums
    "AgentState",
    "LifecycleEvent",
    
    # Data classes
    "StateTransition",
    "AgentStateSnapshot",
    
    # Event handlers
    "LifecycleEventHandler",
    "LoggingEventHandler", 
    "AuditEventHandler",
    
    # Factory functions
    "get_lifecycle_manager",
    "register_agent_lifecycle",
    "transition_agent_state",
    "get_agent_current_state",
    
    # Package metadata
    "__version__",
    "__author__",
    "__description__",
]


def setup_agent_lifecycle(agent_id: str, agent_name: str, persistence_enabled: bool = True) -> bool:
    """
    Setup agent lifecycle management for an agent.
    
    Args:
        agent_id: Unique identifier for the agent
        agent_name: Human-readable name for the agent  
        persistence_enabled: Whether to enable state persistence
        
    Returns:
        bool: True if setup successful, False otherwise
        
    Example:
        >>> from common.lifecycle import setup_agent_lifecycle
        >>> success = setup_agent_lifecycle("agent_001", "TestAgent")
        >>> if success:
        ...     print("Lifecycle management enabled for agent")
    """
    try:
        manager = get_lifecycle_manager()
        return manager.register_agent(agent_id, agent_name)
    except Exception:
        return False


def start_agent(agent_id: str, **context) -> bool:
    """
    Start an agent using lifecycle management.
    
    Args:
        agent_id: Agent identifier
        **context: Additional context for the transition
        
    Returns:
        bool: True if transition successful
        
    Example:
        >>> from common.lifecycle import start_agent
        >>> success = start_agent("agent_001", user_id="system")
    """
    return transition_agent_state(agent_id, LifecycleEvent.START, **context)


def stop_agent(agent_id: str, **context) -> bool:
    """
    Stop an agent using lifecycle management.
    
    Args:
        agent_id: Agent identifier
        **context: Additional context for the transition
        
    Returns:
        bool: True if transition successful
        
    Example:
        >>> from common.lifecycle import stop_agent
        >>> success = stop_agent("agent_001", reason="maintenance")
    """
    return transition_agent_state(agent_id, LifecycleEvent.STOP, **context)


def pause_agent(agent_id: str, **context) -> bool:
    """
    Pause an agent using lifecycle management.
    
    Args:
        agent_id: Agent identifier
        **context: Additional context for the transition
        
    Returns:
        bool: True if transition successful
        
    Example:
        >>> from common.lifecycle import pause_agent
        >>> success = pause_agent("agent_001", reason="resource_pressure")
    """
    return transition_agent_state(agent_id, LifecycleEvent.PAUSE, **context)


def resume_agent(agent_id: str, **context) -> bool:
    """
    Resume an agent using lifecycle management.
    
    Args:
        agent_id: Agent identifier
        **context: Additional context for the transition
        
    Returns:
        bool: True if transition successful
        
    Example:
        >>> from common.lifecycle import resume_agent
        >>> success = resume_agent("agent_001", reason="resources_available")
    """
    return transition_agent_state(agent_id, LifecycleEvent.RESUME, **context)


def get_agent_info(agent_id: str) -> dict:
    """
    Get comprehensive agent lifecycle information.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        dict: Agent lifecycle information
        
    Example:
        >>> from common.lifecycle import get_agent_info
        >>> info = get_agent_info("agent_001")
        >>> print(f"Agent state: {info.get('current_state')}")
    """
    manager = get_lifecycle_manager()
    snapshot = manager.get_agent_snapshot(agent_id)
    
    if not snapshot:
        return {}
    
    return {
        'agent_id': snapshot.agent_id,
        'agent_name': snapshot.agent_name,
        'current_state': snapshot.current_state.value,
        'previous_state': snapshot.previous_state.value if snapshot.previous_state else None,
        'state_entered_at': snapshot.state_entered_at.isoformat(),
        'state_duration_seconds': snapshot.state_duration_seconds,
        'transition_count': len(snapshot.transition_history),
        'valid_events': [event.value for event in manager.get_valid_events(agent_id)]
    }


# Package configuration
LIFECYCLE_CONFIG = {
    'version': __version__,
    'components': {
        'lifecycle_manager': 'AgentLifecycleManager',
        'state_validator': 'StateTransitionValidator', 
        'persistence_manager': 'StatePersistenceManager',
        'event_handlers': ['LoggingEventHandler', 'AuditEventHandler']
    },
    'features': {
        'state_machine': True,
        'event_handling': True,
        'state_persistence': True,
        'transition_validation': True,
        'audit_trail_integration': True
    }
}


def get_package_info() -> dict:
    """Get package information and configuration."""
    return LIFECYCLE_CONFIG.copy()


# Example usage in docstring
"""
Example Usage:

    # Basic lifecycle setup
    from common.lifecycle import setup_agent_lifecycle, start_agent, get_agent_info
    
    # Setup lifecycle management for an agent
    setup_agent_lifecycle("my_agent", "MyTestAgent")
    
    # Start the agent
    start_agent("my_agent", user_id="system")
    
    # Check agent status
    info = get_agent_info("my_agent")
    print(f"Agent is in state: {info['current_state']}")
    
    # Advanced usage with custom event handlers
    from common.lifecycle import AgentLifecycleManager, LifecycleEventHandler
    
    class CustomEventHandler(LifecycleEventHandler):
        def handle_event(self, agent_id, event, transition, context):
            print(f"Custom handling: {agent_id} -> {event.value}")
    
    manager = get_lifecycle_manager()
    manager.add_event_handler(CustomEventHandler())
"""
