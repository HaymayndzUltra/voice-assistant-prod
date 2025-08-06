"""
Circular Import Refactor Example
Demonstrates how to replace direct circular imports with event-driven communication.

BEFORE (Circular Import):
  ModelManagerAgent imports VRAMOptimizerAgent
  VRAMOptimizerAgent imports ModelManagerAgent
  → Import error!

AFTER (Event-Driven):
  ModelManagerAgent publishes MODEL_LOAD_REQUESTED events
  VRAMOptimizerAgent subscribes to VRAM_THRESHOLD_EXCEEDED events
  → No direct imports, loose coupling!
"""

# =============================================================================
# BEFORE: Circular Import Problem
# =============================================================================

# This would cause circular import errors:
"""
# model_manager_agent.py
from vram_optimizer_agent import VRAMOptimizerAgent  # ❌ Circular import
from common.utils.log_setup import configure_logging

class ModelManagerAgent:
    def __init__(self):
        self.vram_optimizer = VRAMOptimizerAgent()  # ❌ Direct dependency
    
    def load_model(self, model_id):
        # Direct call to VRAM optimizer
        if not self.vram_optimizer.check_vram_available():  # ❌ Tight coupling
            return False
        # ... load model

# vram_optimizer_agent.py  
from model_manager_agent import ModelManagerAgent  # ❌ Circular import

class VRAMOptimizerAgent:
    def __init__(self):
        self.model_manager = ModelManagerAgent()  # ❌ Circular dependency
    
    def optimize_vram(self):
        # Direct call to model manager
        self.model_manager.unload_unused_models()  # ❌ Tight coupling
"""

# =============================================================================
# AFTER: Event-Driven Solution
# =============================================================================

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from events.model_events import (
    ModelEventType, create_model_load_request, create_vram_warning, 
    ModelLoadEvent, VRAMEvent, ModelStatus, create_model_status_change
)
from events.memory_events import MemoryEventType, create_memory_pressure_warning
from events.event_bus import (
    get_event_bus, publish_model_event, subscribe_to_model_events,
    event_handler, auto_subscribe_handlers
)
from common.core.base_agent import BaseAgent
from common_utils.error_handling import SafeExecutor
import time
from typing import Dict, Any
import logging

# Configure logging for the example
logger = configure_logging(__name__, level="INFO")
logger = logging.getLogger(__name__)

class EventDrivenModelManagerAgent(BaseAgent):
    """
    Model Manager using event-driven communication.
    No direct imports of other agents - uses events instead.
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ModelManagerAgent", **kwargs)
        self.loaded_models: Dict[str, Dict[str, Any]] = {}
        self.subscription_ids = []
        
        # Subscribe to relevant events
        self._setup_event_subscriptions()
    
    def _setup_event_subscriptions(self):
        """Subscribe to events we care about"""
        # Subscribe to VRAM warnings to unload models
        sub_id = subscribe_to_model_events(
            subscriber_id="ModelManagerAgent",
            event_types=[ModelEventType.VRAM_THRESHOLD_EXCEEDED, ModelEventType.GPU_MEMORY_WARNING],
            callback=self._handle_vram_warning,
            priority=10  # High priority for resource management
        )
        self.subscription_ids.append(sub_id)
        
        logger.info("ModelManagerAgent: Event subscriptions set up")
    
    def load_model(self, model_id: str, model_path: str, model_type: str) -> bool:
        """
        Load a model by publishing an event instead of direct calls.
        """
        logger.info(f"ModelManagerAgent: Loading model {model_id}")
        
        # Create and publish model load request event
        load_event = create_model_load_request(
            model_id=model_id,
            model_path=model_path,
            model_type=model_type,
            requester_agent=self.name,
            expected_vram_mb=2048,  # Estimated VRAM usage
            priority=5,
            source_agent=self.name,
            machine_id="MainPC"
        )
        
        # Publish the event instead of calling VRAMOptimizer directly
        success = publish_model_event(load_event)
        
        if success:
            # Simulate model loading
            self.loaded_models[model_id] = {
                "path": model_path,
                "type": model_type,
                "vram_mb": 2048,
                "load_time": time.time()
            }
            
            # Publish model loaded event
            status_event = create_model_status_change(
                model_id=model_id,
                old_status=None,
                new_status=ModelStatus.LOADED,
                vram_usage_mb=2048,
                load_time_seconds=1.5,
                source_agent=self.name,
                machine_id="MainPC"
            )
            publish_model_event(status_event)
            
            logger.info(f"ModelManagerAgent: Model {model_id} loaded successfully")
            return True
        
        logger.error(f"ModelManagerAgent: Failed to publish load event for {model_id}")
        return False
    
    def _handle_vram_warning(self, event: VRAMEvent) -> None:
        """
        Handle VRAM warning events by unloading models.
        This replaces direct calls from VRAMOptimizerAgent.
        """
        logger.warning(f"ModelManagerAgent: Received VRAM warning - {event.used_vram_mb}MB used")
        
        def unload_least_used_model():
            if not self.loaded_models:
                return
            
            # Find least recently used model
            oldest_model = min(
                self.loaded_models.items(),
                key=lambda x: x[1]["load_time"]
            )
            
            model_id = oldest_model[0]
            model_info = oldest_model[1]
            
            # Unload the model
            del self.loaded_models[model_id]
            
            # Publish model unloaded event
            unload_event = create_model_status_change(
                model_id=model_id,
                old_status=ModelStatus.LOADED,
                new_status=ModelStatus.UNLOADED,
                vram_usage_mb=0,
                source_agent=self.name,
                machine_id="MainPC"
            )
            publish_model_event(unload_event)
            
            logger.info(f"ModelManagerAgent: Unloaded model {model_id} to free VRAM")
        
        # Use SafeExecutor for robust error handling
        SafeExecutor.execute_with_fallback(
            unload_least_used_model,
            fallback_value=None,
            context="unload model for VRAM optimization",
            expected_exceptions=(KeyError, ValueError, Exception)
        )
    
    def get_loaded_models(self) -> Dict[str, Dict[str, Any]]:
        """Get currently loaded models"""
        return self.loaded_models.copy()
    
    def shutdown(self):
        """Clean up subscriptions"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        super().shutdown()

class EventDrivenVRAMOptimizerAgent(BaseAgent):
    """
    VRAM Optimizer using event-driven communication.
    No direct imports of ModelManagerAgent - uses events instead.
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="VRAMOptimizerAgent", **kwargs)
        self.vram_threshold_mb = 8192  # 8GB threshold
        self.current_vram_usage = 0
        self.subscription_ids = []
        
        # Subscribe to model events
        self._setup_event_subscriptions()
        
        # Start monitoring thread
        self._start_vram_monitoring()
    
    def _setup_event_subscriptions(self):
        """Subscribe to model loading events"""
        # Subscribe to model load requests to check VRAM
        sub_id = subscribe_to_model_events(
            subscriber_id="VRAMOptimizerAgent",
            event_types=[ModelEventType.MODEL_LOAD_REQUESTED],
            callback=self._handle_model_load_request,
            priority=20  # Higher priority than model manager
        )
        self.subscription_ids.append(sub_id)
        
        # Subscribe to model status changes to track VRAM usage
        sub_id = subscribe_to_model_events(
            subscriber_id="VRAMOptimizerAgent", 
            event_types=[ModelEventType.MODEL_LOADED, ModelEventType.MODEL_UNLOADED],
            callback=self._handle_model_status_change,
            priority=15
        )
        self.subscription_ids.append(sub_id)
        
        logger.info("VRAMOptimizerAgent: Event subscriptions set up")
    
    def _handle_model_load_request(self, event: ModelLoadEvent) -> None:
        """
        Handle model load requests by checking VRAM availability.
        This replaces ModelManagerAgent calling us directly.
        """
        logger.info(f"VRAMOptimizerAgent: Checking VRAM for model {event.model_id}")
        
        required_vram = event.expected_vram_mb
        available_vram = self.vram_threshold_mb - self.current_vram_usage
        
        if required_vram > available_vram:
            # Publish VRAM warning event instead of calling ModelManager directly
            warning_event = create_vram_warning(
                used_vram_mb=self.current_vram_usage,
                total_vram_mb=self.vram_threshold_mb,
                threshold_percentage=85.0,
                affected_models=[event.model_id],
                source_agent=self.name,
                machine_id="MainPC"
            )
            
            publish_model_event(warning_event)
            logger.warning(f"VRAMOptimizerAgent: VRAM warning sent for model {event.model_id}")
    
    def _handle_model_status_change(self, event) -> None:
        """Update VRAM usage tracking based on model status changes"""
        if event.new_status == ModelStatus.LOADED:
            self.current_vram_usage += event.vram_usage_mb
            logger.info(f"VRAMOptimizerAgent: VRAM usage increased to {self.current_vram_usage}MB")
        elif event.new_status == ModelStatus.UNLOADED:
            self.current_vram_usage -= event.vram_usage_mb
            if self.current_vram_usage < 0:
                self.current_vram_usage = 0
            logger.info(f"VRAMOptimizerAgent: VRAM usage decreased to {self.current_vram_usage}MB")
    
    def _start_vram_monitoring(self):
        """Start background VRAM monitoring"""
        def monitor_vram():
            while self.running:
                try:
                    # Simulate VRAM monitoring
                    usage_percentage = (self.current_vram_usage / self.vram_threshold_mb) * 100
                    
                    if usage_percentage > 85:
                        # Publish critical VRAM event
                        critical_event = create_vram_warning(
                            used_vram_mb=self.current_vram_usage,
                            total_vram_mb=self.vram_threshold_mb,
                            threshold_percentage=usage_percentage,
                            affected_models=[],
                            source_agent=self.name,
                            machine_id="MainPC"
                        )
                        critical_event.event_type = ModelEventType.GPU_MEMORY_CRITICAL
                        publish_model_event(critical_event)
                    
                    time.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    logger.error(f"VRAMOptimizerAgent: VRAM monitoring error: {e}")
                    time.sleep(1)
        
        import threading
        self.monitor_thread = threading.Thread(target=monitor_vram, daemon=True)
        self.monitor_thread.start()
    
    def get_vram_stats(self) -> Dict[str, Any]:
        """Get current VRAM statistics"""
        return {
            "used_mb": self.current_vram_usage,
            "total_mb": self.vram_threshold_mb,
            "usage_percentage": (self.current_vram_usage / self.vram_threshold_mb) * 100,
            "available_mb": self.vram_threshold_mb - self.current_vram_usage
        }
    
    def shutdown(self):
        """Clean up subscriptions"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        super().shutdown()

# =============================================================================
# Alternative: Using Decorators for Event Handling
# =============================================================================

class DecoratorBasedAgent(BaseAgent):
    """
    Example agent using @event_handler decorators for automatic subscription.
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="DecoratorBasedAgent", **kwargs)
        # Automatically subscribe all methods marked with @event_handler
        self.subscription_ids = auto_subscribe_handlers(self)
    
    @event_handler([ModelEventType.MODEL_LOADED, ModelEventType.MODEL_UNLOADED])
    def handle_model_events(self, event):
        """This method will automatically subscribe to model load/unload events"""
        logger.info(f"DecoratorBasedAgent: Handling {event.event_type.value} for model {event.model_id}")
    
    @event_handler([ModelEventType.VRAM_THRESHOLD_EXCEEDED], priority=5)
    def handle_vram_warnings(self, event):
        """This method will automatically subscribe to VRAM warnings with priority 5"""
        logger.info(f"DecoratorBasedAgent: VRAM warning - {event.used_vram_mb}MB used")
    
    def shutdown(self):
        """Clean up subscriptions"""
        event_bus = get_event_bus()
        for sub_id in self.subscription_ids:
            event_bus.unsubscribe(sub_id)
        super().shutdown()

# =============================================================================
# Demonstration Function
# =============================================================================

def demonstrate_event_driven_refactor():
    """
    Demonstrate the event-driven refactor in action.
    """
    logger.info("=" * 60)
    logger.info("CIRCULAR IMPORT REFACTOR DEMONSTRATION")
    logger.info("=" * 60)
    
    # Create agents without circular imports
    model_manager = EventDrivenModelManagerAgent(port=9001)
    vram_optimizer = EventDrivenVRAMOptimizerAgent(port=9002)
    decorator_agent = DecoratorBasedAgent(port=9003)
    
    # Wait a moment for subscriptions to be set up
    time.sleep(0.5)
    
    logger.info("\n1. Loading a small model (should succeed)")
    model_manager.load_model("small_model", "/models/small.pt", "transformer")
    time.sleep(1)
    
    logger.info("\n2. Loading a large model (should trigger VRAM warning)")
    model_manager.load_model("large_model", "/models/large.pt", "transformer")
    time.sleep(1)
    
    logger.info("\n3. Loading another large model (should trigger optimization)")
    model_manager.load_model("huge_model", "/models/huge.pt", "transformer")
    time.sleep(2)
    
    # Show final state
    logger.info("\n4. Final state:")
    logger.info(f"   Loaded models: {list(model_manager.get_loaded_models().keys())}")
    logger.info(f"   VRAM stats: {vram_optimizer.get_vram_stats()}")
    
    # Show event bus metrics
    event_bus = get_event_bus()
    metrics = event_bus.get_metrics()
    if metrics:
        logger.info(f"\n5. Event Bus Metrics:")
        logger.info(f"   Events published: {metrics.events_published}")
        logger.info(f"   Events delivered: {metrics.events_delivered}")
        logger.info(f"   Active subscriptions: {metrics.active_subscriptions}")
        logger.info(f"   Avg delivery time: {metrics.avg_delivery_time_ms:.2f}ms")
        logger.info(f"   Error rate: {metrics.error_rate:.2%}")
    
    # Cleanup
    logger.info("\n6. Cleaning up...")
    model_manager.shutdown()
    vram_optimizer.shutdown()
    decorator_agent.shutdown()
    
    logger.info("=" * 60)
    logger.info("DEMONSTRATION COMPLETE")
    logger.info("=" * 60)

if __name__ == "__main__":
    demonstrate_event_driven_refactor() 