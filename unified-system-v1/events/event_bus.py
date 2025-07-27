"""
Event Bus - Unified event-driven communication system
Provides publish-subscribe messaging to eliminate circular dependencies between agents.
"""
from __future__ import annotations
import asyncio
import threading
import time
import json
import logging
from typing import Dict, List, Callable, Any, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import weakref
from collections import defaultdict, deque
from abc import ABC, abstractmethod

# Import our event types
from events.model_events import BaseModelEvent, ModelEventType, deserialize_event as deserialize_model_event
from events.memory_events import BaseMemoryEvent, MemoryEventType, deserialize_memory_event
from common_utils.error_handling import SafeExecutor

# Event subscription and filtering
@dataclass
class EventSubscription:
    """Subscription configuration for event listeners"""
    subscriber_id: str
    event_types: Set[Union[ModelEventType, MemoryEventType, str]]
    callback: Callable[[Union[BaseModelEvent, BaseMemoryEvent]], None]
    filters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority gets events first
    is_async: bool = False
    max_retries: int = 3
    timeout_seconds: float = 5.0
    
    def matches_event(self, event: Union[BaseModelEvent, BaseMemoryEvent]) -> bool:
        """Check if event matches subscription criteria"""
        # Check event type
        if event.event_type not in self.event_types and "*" not in self.event_types:
            return False
            
        # Apply filters
        for filter_key, filter_value in self.filters.items():
            event_value = getattr(event, filter_key, None)
            if event_value != filter_value:
                return False
                
        return True

@dataclass 
class EventMetrics:
    """Metrics for event bus performance monitoring"""
    events_published: int = 0
    events_delivered: int = 0
    events_failed: int = 0
    avg_delivery_time_ms: float = 0.0
    active_subscriptions: int = 0
    queue_size: int = 0
    error_rate: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)

class EventBusError(Exception):
    """Base exception for event bus errors"""
    pass

class EventDeliveryError(EventBusError):
    """Exception raised when event delivery fails"""
    pass

class CircularDependencyError(EventBusError):
    """Exception raised when circular dependencies are detected"""
    pass

class EventBus:
    """
    Unified event bus for decoupled agent communication.
    
    Features:
    - Publish-subscribe messaging
    - Event filtering and routing
    - Async and sync event handling
    - Retry mechanisms with circuit breaking
    - Performance monitoring
    - Dead letter queue for failed events
    - Circular dependency detection
    """
    
    def __init__(self, 
                 max_queue_size: int = 10000,
                 max_workers: int = 10,
                 enable_metrics: bool = True,
                 enable_dead_letter_queue: bool = True):
        # Core components
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._event_queue: deque = deque(maxlen=max_queue_size)
        self._dead_letter_queue: deque = deque(maxlen=1000)
        
        # Threading and async support
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None
        
        # Metrics and monitoring
        self._metrics = EventMetrics() if enable_metrics else None
        self._enable_dead_letter_queue = enable_dead_letter_queue
        
        # Circular dependency detection
        self._event_chain: deque = deque(maxlen=100)  # Track recent event chain
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Start processing
        self.start()
    
    def start(self) -> None:
        """Start the event bus processing"""
        if self._running:
            return
            
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processor_thread.start()
        self.logger.info("Event bus started")
    
    def stop(self) -> None:
        """Stop the event bus processing"""
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5.0)
        self._executor.shutdown(wait=True)
        self.logger.info("Event bus stopped")
    
    def subscribe(self, 
                  subscriber_id: str,
                  event_types: Union[List[Union[ModelEventType, MemoryEventType, str]], str],
                  callback: Callable[[Union[BaseModelEvent, BaseMemoryEvent]], None],
                  filters: Optional[Dict[str, Any]] = None,
                  priority: int = 0,
                  is_async: bool = False,
                  max_retries: int = 3) -> str:
        """
        Subscribe to events
        
        Args:
            subscriber_id: Unique identifier for subscriber
            event_types: List of event types to subscribe to, or "*" for all
            callback: Function to call when event matches
            filters: Additional filters for event matching
            priority: Priority level (higher = processed first)
            is_async: Whether callback is async
            max_retries: Maximum retry attempts for failed deliveries
            
        Returns:
            Subscription ID
        """
        if isinstance(event_types, str):
            if event_types == "*":
                event_types = {"*"}
            else:
                event_types = {event_types}
        else:
            event_types = set(event_types)
        
        subscription = EventSubscription(
            subscriber_id=subscriber_id,
            event_types=event_types,
            callback=callback,
            filters=filters or {},
            priority=priority,
            is_async=is_async,
            max_retries=max_retries
        )
        
        subscription_key = f"{subscriber_id}_{len(self._subscriptions)}"
        self._subscriptions[subscription_key] = subscription
        
        # Update dependency graph for circular detection
        for event_type in event_types:
            if event_type != "*":
                self._dependency_graph[subscriber_id].add(str(event_type))
        
        if self._metrics:
            self._metrics.active_subscriptions = len(self._subscriptions)
        
        self.logger.info(f"Subscription added: {subscription_key} for {subscriber_id}")
        return subscription_key
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events
        
        Args:
            subscription_id: ID returned from subscribe()
            
        Returns:
            True if subscription was removed
        """
        if subscription_id in self._subscriptions:
            subscription = self._subscriptions.pop(subscription_id)
            
            # Update dependency graph
            subscriber_id = subscription.subscriber_id
            if subscriber_id in self._dependency_graph:
                del self._dependency_graph[subscriber_id]
            
            if self._metrics:
                self._metrics.active_subscriptions = len(self._subscriptions)
            
            self.logger.info(f"Subscription removed: {subscription_id}")
            return True
        return False
    
    def publish(self, event: Union[BaseModelEvent, BaseMemoryEvent]) -> bool:
        """
        Publish an event to the bus
        
        Args:
            event: Event to publish
            
        Returns:
            True if event was queued successfully
        """
        try:
            # Add event to queue
            self._event_queue.append({
                'event': event,
                'timestamp': datetime.now(),
                'retry_count': 0
            })
            
            # Update metrics
            if self._metrics:
                self._metrics.events_published += 1
                self._metrics.queue_size = len(self._event_queue)
            
            # Add to event chain for circular dependency detection
            self._event_chain.append({
                'source_agent': event.source_agent,
                'event_type': str(event.event_type),
                'timestamp': datetime.now()
            })
            
            self.logger.debug(f"Event published: {event.event_type.value} from {event.source_agent}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            return False
    
    def _process_events(self) -> None:
        """Background thread to process events from the queue"""
        while self._running:
            try:
                if not self._event_queue:
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
                    continue
                
                event_data = self._event_queue.popleft()
                event = event_data['event']
                
                # Check for circular dependencies
                if self._detect_circular_dependency(event):
                    self.logger.warning(f"Circular dependency detected for event {event.event_type}")
                    continue
                
                # Find matching subscriptions
                matching_subscriptions = self._find_matching_subscriptions(event)
                
                # Sort by priority (higher first)
                matching_subscriptions.sort(key=lambda s: s.priority, reverse=True)
                
                # Deliver to each subscriber
                for subscription in matching_subscriptions:
                    self._deliver_event(event, subscription, event_data['retry_count'])
                
                # Update metrics
                if self._metrics:
                    self._metrics.events_delivered += len(matching_subscriptions)
                    self._metrics.queue_size = len(self._event_queue)
                
            except Exception as e:
                self.logger.error(f"Error processing events: {e}")
                time.sleep(0.1)
    
    def _find_matching_subscriptions(self, event: Union[BaseModelEvent, BaseMemoryEvent]) -> List[EventSubscription]:
        """Find subscriptions that match the given event"""
        matching = []
        for subscription in self._subscriptions.values():
            if subscription.matches_event(event):
                matching.append(subscription)
        return matching
    
    def _deliver_event(self, 
                      event: Union[BaseModelEvent, BaseMemoryEvent], 
                      subscription: EventSubscription,
                      retry_count: int) -> None:
        """Deliver an event to a specific subscription"""
        start_time = time.time()
        
        def execute_callback():
            if subscription.is_async:
                return self._execute_async_callback(subscription.callback, event)
            else:
                return subscription.callback(event)
        
        def handle_delivery():
            try:
                execute_callback()
                
                # Update metrics
                if self._metrics:
                    delivery_time = (time.time() - start_time) * 1000
                    self._update_avg_delivery_time(delivery_time)
                
                self.logger.debug(f"Event delivered to {subscription.subscriber_id}")
                
            except Exception as e:
                self.logger.error(f"Event delivery failed to {subscription.subscriber_id}: {e}")
                
                # Update error metrics
                if self._metrics:
                    self._metrics.events_failed += 1
                    self._update_error_rate()
                
                # Retry or send to dead letter queue
                if retry_count < subscription.max_retries:
                    # Retry
                    self._event_queue.append({
                        'event': event,
                        'timestamp': datetime.now(),
                        'retry_count': retry_count + 1,
                        'target_subscription': subscription.subscriber_id
                    })
                elif self._enable_dead_letter_queue:
                    # Send to dead letter queue
                    self._dead_letter_queue.append({
                        'event': event,
                        'subscription': subscription,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })
        
        # Execute with SafeExecutor for additional error handling
        SafeExecutor.execute_with_fallback(
            handle_delivery,
            fallback_value=None,
            context=f"deliver event to {subscription.subscriber_id}",
            expected_exceptions=(Exception,)
        )
    
    def _execute_async_callback(self, callback: Callable, event: Union[BaseModelEvent, BaseMemoryEvent]) -> None:
        """Execute an async callback"""
        if self._loop is None:
            # Try to get the current event loop, or create a new one
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        
        if self._loop.is_running():
            # Schedule as a task
            asyncio.create_task(callback(event))
        else:
            # Run directly
            self._loop.run_until_complete(callback(event))
    
    def _detect_circular_dependency(self, event: Union[BaseModelEvent, BaseMemoryEvent]) -> bool:
        """Detect potential circular dependencies in event chain"""
        if len(self._event_chain) < 3:
            return False
        
        # Look for patterns in recent events
        recent_events = list(self._event_chain)[-10:]  # Last 10 events
        source_agent = event.source_agent
        event_type = str(event.event_type)
        
        # Count occurrences of same agent + event type in recent chain
        same_pattern_count = sum(1 for e in recent_events 
                               if e['source_agent'] == source_agent and e['event_type'] == event_type)
        
        # If we see the same pattern more than 3 times in recent history, it's likely circular
        return same_pattern_count >= 3
    
    def _update_avg_delivery_time(self, delivery_time_ms: float) -> None:
        """Update average delivery time metric"""
        if self._metrics:
            if self._metrics.avg_delivery_time_ms == 0:
                self._metrics.avg_delivery_time_ms = delivery_time_ms
            else:
                # Exponential moving average
                alpha = 0.1
                self._metrics.avg_delivery_time_ms = (
                    alpha * delivery_time_ms + 
                    (1 - alpha) * self._metrics.avg_delivery_time_ms
                )
    
    def _update_error_rate(self) -> None:
        """Update error rate metric"""
        if self._metrics:
            total_events = self._metrics.events_delivered + self._metrics.events_failed
            if total_events > 0:
                self._metrics.error_rate = self._metrics.events_failed / total_events
    
    def get_metrics(self) -> Optional[EventMetrics]:
        """Get current event bus metrics"""
        return self._metrics
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get events from dead letter queue"""
        return list(self._dead_letter_queue)
    
    def clear_dead_letter_queue(self) -> None:
        """Clear the dead letter queue"""
        self._dead_letter_queue.clear()
    
    def get_subscription_count(self) -> int:
        """Get number of active subscriptions"""
        return len(self._subscriptions)
    
    def get_queue_size(self) -> int:
        """Get current event queue size"""
        return len(self._event_queue)

# Global event bus instance
_global_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus

def publish_model_event(event: BaseModelEvent) -> bool:
    """Convenience function to publish model events"""
    return get_event_bus().publish(event)

def publish_memory_event(event: BaseMemoryEvent) -> bool:
    """Convenience function to publish memory events"""
    return get_event_bus().publish(event)

def subscribe_to_model_events(
    subscriber_id: str,
    event_types: Union[List[ModelEventType], str],
    callback: Callable[[BaseModelEvent], None],
    **kwargs
) -> str:
    """Convenience function to subscribe to model events"""
    return get_event_bus().subscribe(subscriber_id, event_types, callback, **kwargs)

def subscribe_to_memory_events(
    subscriber_id: str,
    event_types: Union[List[MemoryEventType], str],
    callback: Callable[[BaseMemoryEvent], None],
    **kwargs
) -> str:
    """Convenience function to subscribe to memory events"""
    return get_event_bus().subscribe(subscriber_id, event_types, callback, **kwargs)

# Context manager for event bus
class EventBusContext:
    """Context manager for event bus lifecycle"""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.event_bus = None
    
    def __enter__(self) -> EventBus:
        self.event_bus = EventBus(**self.kwargs)
        return self.event_bus
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.event_bus:
            self.event_bus.stop()

# Decorators for event handling
def event_handler(event_types: Union[List[Union[ModelEventType, MemoryEventType]], str], 
                  subscriber_id: Optional[str] = None,
                  **subscription_kwargs):
    """Decorator to mark functions as event handlers"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Store event handler metadata
        wrapper._event_types = event_types
        wrapper._subscriber_id = subscriber_id or func.__name__
        wrapper._subscription_kwargs = subscription_kwargs
        wrapper._is_event_handler = True
        
        return wrapper
    return decorator

def auto_subscribe_handlers(instance: Any, prefix: str = "") -> List[str]:
    """Automatically subscribe methods marked with @event_handler decorator"""
    subscription_ids = []
    subscriber_prefix = prefix or instance.__class__.__name__
    
    for attr_name in dir(instance):
        attr = getattr(instance, attr_name)
        if hasattr(attr, '_is_event_handler') and attr._is_event_handler:
            subscriber_id = f"{subscriber_prefix}_{attr._subscriber_id}"
            subscription_id = get_event_bus().subscribe(
                subscriber_id=subscriber_id,
                event_types=attr._event_types,
                callback=attr,
                **attr._subscription_kwargs
            )
            subscription_ids.append(subscription_id)
    
    return subscription_ids 