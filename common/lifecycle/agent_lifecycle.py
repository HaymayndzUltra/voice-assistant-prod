#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent Lifecycle Management - Phase 4.2

Comprehensive agent state management system with state machines, lifecycle events,
state persistence, and transition validation. Provides enterprise-grade agent
lifecycle control with event-driven architecture.

Part of Phase 4.2: Enhanced Agent Factory and Lifecycle Management - O3 Roadmap Implementation
"""

import logging
import threading
import time
import json
import uuid
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Set, Union
from enum import Enum, auto
from pathlib import Path
import weakref

# Import our logging and audit systems from Phase 4.1
try:
    from common.logging.structured_logger import get_logger
    from common.audit.audit_trail import AuditTrail, AuditEventType
except ImportError:
    # Fallback if Phase 4.1 components not available
    def get_logger(name):
        return logging.getLogger(name)
    
    class AuditTrail:
        def __init__(self, *args, **kwargs):
            pass
        def log_agent_start(self, *args, **kwargs):
            pass
        def log_agent_stop(self, *args, **kwargs):
            pass
    
    class AuditEventType:
        AGENT_LIFECYCLE = "agent_lifecycle"


class AgentState(Enum):
    """Agent lifecycle states."""
    
    # Initial states
    CREATED = "created"
    INITIALIZING = "initializing"
    
    # Running states
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    
    # Transitional states
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    
    # Stopping states
    STOPPING = "stopping"
    STOPPED = "stopped"
    
    # Error states
    ERROR = "error"
    RECOVERING = "recovering"
    FAILED = "failed"
    
    # Final states
    TERMINATED = "terminated"
    DESTROYED = "destroyed"


class LifecycleEvent(Enum):
    """Lifecycle events that can trigger state transitions."""
    
    # Control events
    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    RESTART = "restart"
    TERMINATE = "terminate"
    DESTROY = "destroy"
    
    # Automatic events
    INITIALIZATION_COMPLETE = "initialization_complete"
    STARTUP_COMPLETE = "startup_complete"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    IDLE_TIMEOUT = "idle_timeout"
    
    # Error events
    ERROR_OCCURRED = "error_occurred"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    
    # Health events
    HEALTH_CHECK_PASSED = "health_check_passed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    
    # Resource events
    RESOURCE_ALLOCATED = "resource_allocated"
    RESOURCE_RELEASED = "resource_released"
    MEMORY_PRESSURE = "memory_pressure"
    CPU_PRESSURE = "cpu_pressure"


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    
    from_state: AgentState
    to_state: AgentState
    event: LifecycleEvent
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class AgentStateSnapshot:
    """Snapshot of agent state for persistence."""
    
    agent_id: str
    agent_name: str
    current_state: AgentState
    previous_state: Optional[AgentState]
    state_entered_at: datetime
    state_duration_seconds: float
    transition_history: List[StateTransition]
    custom_data: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"


class StateTransitionValidator:
    """Validates state transitions according to business rules."""
    
    def __init__(self):
        # Define valid state transitions
        self.valid_transitions = {
            AgentState.CREATED: {
                LifecycleEvent.START: AgentState.INITIALIZING,
                LifecycleEvent.DESTROY: AgentState.DESTROYED
            },
            AgentState.INITIALIZING: {
                LifecycleEvent.INITIALIZATION_COMPLETE: AgentState.STARTING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR,
                LifecycleEvent.STOP: AgentState.STOPPING
            },
            AgentState.STARTING: {
                LifecycleEvent.STARTUP_COMPLETE: AgentState.RUNNING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR,
                LifecycleEvent.STOP: AgentState.STOPPING
            },
            AgentState.RUNNING: {
                LifecycleEvent.TASK_ASSIGNED: AgentState.BUSY,
                LifecycleEvent.IDLE_TIMEOUT: AgentState.IDLE,
                LifecycleEvent.PAUSE: AgentState.PAUSING,
                LifecycleEvent.STOP: AgentState.STOPPING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR,
                LifecycleEvent.RESTART: AgentState.STOPPING
            },
            AgentState.IDLE: {
                LifecycleEvent.TASK_ASSIGNED: AgentState.BUSY,
                LifecycleEvent.PAUSE: AgentState.PAUSING,
                LifecycleEvent.STOP: AgentState.STOPPING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR
            },
            AgentState.BUSY: {
                LifecycleEvent.TASK_COMPLETED: AgentState.RUNNING,
                LifecycleEvent.IDLE_TIMEOUT: AgentState.IDLE,
                LifecycleEvent.PAUSE: AgentState.PAUSING,
                LifecycleEvent.STOP: AgentState.STOPPING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR
            },
            AgentState.PAUSING: {
                LifecycleEvent.TASK_COMPLETED: AgentState.PAUSED,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR
            },
            AgentState.PAUSED: {
                LifecycleEvent.RESUME: AgentState.RESUMING,
                LifecycleEvent.STOP: AgentState.STOPPING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR
            },
            AgentState.RESUMING: {
                LifecycleEvent.STARTUP_COMPLETE: AgentState.RUNNING,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR
            },
            AgentState.STOPPING: {
                LifecycleEvent.TASK_COMPLETED: AgentState.STOPPED,
                LifecycleEvent.ERROR_OCCURRED: AgentState.FAILED
            },
            AgentState.STOPPED: {
                LifecycleEvent.START: AgentState.STARTING,
                LifecycleEvent.TERMINATE: AgentState.TERMINATED,
                LifecycleEvent.DESTROY: AgentState.DESTROYED
            },
            AgentState.ERROR: {
                LifecycleEvent.RECOVERY_STARTED: AgentState.RECOVERING,
                LifecycleEvent.STOP: AgentState.STOPPING,
                LifecycleEvent.TERMINATE: AgentState.FAILED
            },
            AgentState.RECOVERING: {
                LifecycleEvent.RECOVERY_COMPLETED: AgentState.RUNNING,
                LifecycleEvent.RECOVERY_FAILED: AgentState.FAILED,
                LifecycleEvent.ERROR_OCCURRED: AgentState.ERROR
            },
            AgentState.FAILED: {
                LifecycleEvent.RESTART: AgentState.INITIALIZING,
                LifecycleEvent.TERMINATE: AgentState.TERMINATED,
                LifecycleEvent.DESTROY: AgentState.DESTROYED
            },
            AgentState.TERMINATED: {
                LifecycleEvent.DESTROY: AgentState.DESTROYED
            },
            AgentState.DESTROYED: {
                # Final state - no transitions allowed
            }
        }
    
    def is_valid_transition(self, from_state: AgentState, event: LifecycleEvent) -> bool:
        """Check if a state transition is valid."""
        if from_state not in self.valid_transitions:
            return False
        
        return event in self.valid_transitions[from_state]
    
    def get_target_state(self, from_state: AgentState, event: LifecycleEvent) -> Optional[AgentState]:
        """Get the target state for a transition."""
        if not self.is_valid_transition(from_state, event):
            return None
        
        return self.valid_transitions[from_state][event]
    
    def get_valid_events(self, from_state: AgentState) -> Set[LifecycleEvent]:
        """Get valid events for a given state."""
        if from_state not in self.valid_transitions:
            return set()
        
        return set(self.valid_transitions[from_state].keys())


class LifecycleEventHandler(ABC):
    """Abstract base class for lifecycle event handlers."""
    
    @abstractmethod
    def handle_event(self, agent_id: str, event: LifecycleEvent, transition: StateTransition, context: Dict[str, Any]):
        """Handle a lifecycle event."""
        pass


class LoggingEventHandler(LifecycleEventHandler):
    """Event handler that logs lifecycle events."""
    
    def __init__(self, logger_name: str = "agent_lifecycle"):
        self.logger = get_logger(logger_name)
    
    def handle_event(self, agent_id: str, event: LifecycleEvent, transition: StateTransition, context: Dict[str, Any]):
        """Log the lifecycle event."""
        self.logger.info(
            f"Agent lifecycle event",
            agent_id=agent_id,
            event=event.value,
            from_state=transition.from_state.value,
            to_state=transition.to_state.value,
            success=transition.success,
            duration_ms=(datetime.now(timezone.utc) - transition.timestamp).total_seconds() * 1000
        )


class AuditEventHandler(LifecycleEventHandler):
    """Event handler that creates audit trail entries."""
    
    def __init__(self, audit_trail: Optional[AuditTrail] = None):
        self.audit_trail = audit_trail or AuditTrail("agent_lifecycle")
    
    def handle_event(self, agent_id: str, event: LifecycleEvent, transition: StateTransition, context: Dict[str, Any]):
        """Create audit trail entry for lifecycle event."""
        try:
            if event in [LifecycleEvent.START, LifecycleEvent.STARTUP_COMPLETE]:
                self.audit_trail.log_agent_start(
                    agent_name=agent_id,
                    version=context.get('version', '1.0'),
                    user_id=context.get('user_id', 'system')
                )
            elif event in [LifecycleEvent.STOP, LifecycleEvent.TERMINATE]:
                self.audit_trail.log_agent_stop(
                    agent_name=agent_id,
                    reason=f"Lifecycle event: {event.value}",
                    user_id=context.get('user_id', 'system')
                )
        except Exception as e:
            # Don't fail lifecycle operations due to audit issues
            logging.getLogger("audit_event_handler").warning(f"Failed to create audit entry: {e}")


class StatePersistenceManager:
    """Manages persistence of agent state snapshots."""
    
    def __init__(self, storage_path: str = "logs/agent_states"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("state_persistence")
    
    def save_state(self, snapshot: AgentStateSnapshot):
        """Save agent state snapshot to disk."""
        try:
            state_file = self.storage_path / f"{snapshot.agent_id}_state.json"
            
            # Convert snapshot to JSON-serializable format
            state_data = asdict(snapshot)
            state_data['current_state'] = snapshot.current_state.value
            if snapshot.previous_state:
                state_data['previous_state'] = snapshot.previous_state.value
            state_data['state_entered_at'] = snapshot.state_entered_at.isoformat()
            
            # Convert transition history
            transitions = []
            for transition in snapshot.transition_history:
                transition_data = asdict(transition)
                transition_data['from_state'] = transition.from_state.value
                transition_data['to_state'] = transition.to_state.value
                transition_data['event'] = transition.event.value
                transition_data['timestamp'] = transition.timestamp.isoformat()
                transitions.append(transition_data)
            state_data['transition_history'] = transitions
            
            # Save to file
            with open(state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            self.logger.debug(f"Saved state for agent {snapshot.agent_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to save state for agent {snapshot.agent_id}: {e}")
    
    def load_state(self, agent_id: str) -> Optional[AgentStateSnapshot]:
        """Load agent state snapshot from disk."""
        try:
            state_file = self.storage_path / f"{agent_id}_state.json"
            
            if not state_file.exists():
                return None
            
            with open(state_file, 'r') as f:
                state_data = json.load(f)
            
            # Convert back to proper types
            state_data['current_state'] = AgentState(state_data['current_state'])
            if state_data['previous_state']:
                state_data['previous_state'] = AgentState(state_data['previous_state'])
            state_data['state_entered_at'] = datetime.fromisoformat(state_data['state_entered_at'])
            
            # Convert transition history
            transitions = []
            for transition_data in state_data.get('transition_history', []):
                transition = StateTransition(
                    from_state=AgentState(transition_data['from_state']),
                    to_state=AgentState(transition_data['to_state']),
                    event=LifecycleEvent(transition_data['event']),
                    timestamp=datetime.fromisoformat(transition_data['timestamp']),
                    metadata=transition_data.get('metadata', {}),
                    success=transition_data.get('success', True),
                    error_message=transition_data.get('error_message')
                )
                transitions.append(transition)
            state_data['transition_history'] = transitions
            
            snapshot = AgentStateSnapshot(**state_data)
            self.logger.debug(f"Loaded state for agent {agent_id}")
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to load state for agent {agent_id}: {e}")
            return None
    
    def delete_state(self, agent_id: str):
        """Delete agent state snapshot from disk."""
        try:
            state_file = self.storage_path / f"{agent_id}_state.json"
            if state_file.exists():
                state_file.unlink()
                self.logger.debug(f"Deleted state for agent {agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to delete state for agent {agent_id}: {e}")


class AgentLifecycleManager:
    """Central manager for agent lifecycle operations."""
    
    def __init__(self, persistence_enabled: bool = True, storage_path: str = "logs/agent_states"):
        self.validator = StateTransitionValidator()
        self.persistence_manager = StatePersistenceManager(storage_path) if persistence_enabled else None
        self.event_handlers: List[LifecycleEventHandler] = []
        self.agent_states: Dict[str, AgentStateSnapshot] = {}
        self._lock = threading.Lock()
        self.logger = get_logger("agent_lifecycle_manager")
        
        # Default event handlers
        self.add_event_handler(LoggingEventHandler())
        self.add_event_handler(AuditEventHandler())
    
    def add_event_handler(self, handler: LifecycleEventHandler):
        """Add an event handler."""
        self.event_handlers.append(handler)
    
    def remove_event_handler(self, handler: LifecycleEventHandler):
        """Remove an event handler."""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
    
    def register_agent(self, agent_id: str, agent_name: str) -> bool:
        """Register a new agent with the lifecycle manager."""
        with self._lock:
            if agent_id in self.agent_states:
                self.logger.warning(f"Agent {agent_id} already registered")
                return False
            
            # Try to load existing state
            if self.persistence_manager:
                existing_state = self.persistence_manager.load_state(agent_id)
                if existing_state:
                    self.agent_states[agent_id] = existing_state
                    self.logger.info(f"Restored agent {agent_id} from persisted state: {existing_state.current_state.value}")
                    return True
            
            # Create new state
            snapshot = AgentStateSnapshot(
                agent_id=agent_id,
                agent_name=agent_name,
                current_state=AgentState.CREATED,
                previous_state=None,
                state_entered_at=datetime.now(timezone.utc),
                state_duration_seconds=0.0,
                transition_history=[]
            )
            
            self.agent_states[agent_id] = snapshot
            self.logger.info(f"Registered new agent {agent_id} in state {AgentState.CREATED.value}")
            
            # Persist state if enabled
            if self.persistence_manager:
                self.persistence_manager.save_state(snapshot)
            
            return True
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from the lifecycle manager."""
        with self._lock:
            if agent_id in self.agent_states:
                del self.agent_states[agent_id]
                
                # Delete persisted state
                if self.persistence_manager:
                    self.persistence_manager.delete_state(agent_id)
                
                self.logger.info(f"Unregistered agent {agent_id}")
    
    def transition_agent(self, agent_id: str, event: LifecycleEvent, context: Optional[Dict[str, Any]] = None) -> bool:
        """Transition an agent to a new state based on an event."""
        context = context or {}
        
        with self._lock:
            if agent_id not in self.agent_states:
                self.logger.error(f"Agent {agent_id} not registered")
                return False
            
            current_snapshot = self.agent_states[agent_id]
            current_state = current_snapshot.current_state
            
            # Validate transition
            if not self.validator.is_valid_transition(current_state, event):
                self.logger.warning(f"Invalid transition for agent {agent_id}: {current_state.value} -> {event.value}")
                return False
            
            target_state = self.validator.get_target_state(current_state, event)
            if not target_state:
                self.logger.error(f"No target state found for transition {current_state.value} -> {event.value}")
                return False
            
            # Create transition
            transition = StateTransition(
                from_state=current_state,
                to_state=target_state,
                event=event,
                metadata=context.copy()
            )
            
            try:
                # Update state
                now = datetime.now(timezone.utc)
                current_snapshot.previous_state = current_state
                current_snapshot.current_state = target_state
                current_snapshot.state_duration_seconds = (now - current_snapshot.state_entered_at).total_seconds()
                current_snapshot.state_entered_at = now
                current_snapshot.transition_history.append(transition)
                
                # Limit transition history to last 100 entries
                if len(current_snapshot.transition_history) > 100:
                    current_snapshot.transition_history = current_snapshot.transition_history[-100:]
                
                # Persist state if enabled
                if self.persistence_manager:
                    self.persistence_manager.save_state(current_snapshot)
                
                # Notify event handlers
                for handler in self.event_handlers:
                    try:
                        handler.handle_event(agent_id, event, transition, context)
                    except Exception as e:
                        self.logger.error(f"Event handler failed: {e}")
                
                self.logger.info(f"Agent {agent_id} transitioned: {current_state.value} -> {target_state.value}")
                return True
                
            except Exception as e:
                transition.success = False
                transition.error_message = str(e)
                self.logger.error(f"Failed to transition agent {agent_id}: {e}")
                return False
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get the current state of an agent."""
        with self._lock:
            if agent_id in self.agent_states:
                return self.agent_states[agent_id].current_state
            return None
    
    def get_agent_snapshot(self, agent_id: str) -> Optional[AgentStateSnapshot]:
        """Get the complete state snapshot of an agent."""
        with self._lock:
            return self.agent_states.get(agent_id)
    
    def get_valid_events(self, agent_id: str) -> Set[LifecycleEvent]:
        """Get valid events for an agent's current state."""
        current_state = self.get_agent_state(agent_id)
        if current_state:
            return self.validator.get_valid_events(current_state)
        return set()
    
    def get_all_agents(self) -> Dict[str, AgentStateSnapshot]:
        """Get all registered agents and their states."""
        with self._lock:
            return self.agent_states.copy()
    
    def get_agents_by_state(self, state: AgentState) -> List[str]:
        """Get all agents in a specific state."""
        with self._lock:
            return [agent_id for agent_id, snapshot in self.agent_states.items() 
                   if snapshot.current_state == state]


# Global lifecycle manager instance
_global_lifecycle_manager = None
_lifecycle_lock = threading.Lock()


def get_lifecycle_manager() -> AgentLifecycleManager:
    """Get the global agent lifecycle manager instance."""
    global _global_lifecycle_manager
    
    if _global_lifecycle_manager is None:
        with _lifecycle_lock:
            if _global_lifecycle_manager is None:
                _global_lifecycle_manager = AgentLifecycleManager()
    
    return _global_lifecycle_manager


# Convenience functions
def register_agent_lifecycle(agent_id: str, agent_name: str) -> bool:
    """Register an agent with the global lifecycle manager."""
    manager = get_lifecycle_manager()
    return manager.register_agent(agent_id, agent_name)


def transition_agent_state(agent_id: str, event: LifecycleEvent, **context) -> bool:
    """Transition an agent's state using the global lifecycle manager."""
    manager = get_lifecycle_manager()
    return manager.transition_agent(agent_id, event, context)


def get_agent_current_state(agent_id: str) -> Optional[AgentState]:
    """Get an agent's current state from the global lifecycle manager."""
    manager = get_lifecycle_manager()
    return manager.get_agent_state(agent_id)
