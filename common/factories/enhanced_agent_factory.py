#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhanced Agent Factory - Phase 4.2

Advanced agent creation patterns with dependency injection, template system,
lifecycle management, and resource optimization. Builds on Phase 2.1 foundation
with enterprise-grade agent manufacturing capabilities.

Part of Phase 4.2: Enhanced Agent Factory and Lifecycle Management - O3 Roadmap Implementation
"""

import logging
import threading
import time
import inspect
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union, Callable, TypeVar, Generic
from contextlib import contextmanager
from enum import Enum
import json
import uuid

from common.core.base_agent import BaseAgent
from common.config.unified_config_manager import Config
from common.factories.agent_factory import EnhancedBaseAgent, AgentMetrics

# Type variables for generic factory patterns
T = TypeVar('T', bound=BaseAgent)


class AgentTemplate(Enum):
    """Predefined agent templates for common use cases."""
    
    BASIC = "basic"
    MONITORING = "monitoring"
    HIGH_PERFORMANCE = "high_performance"
    DISTRIBUTED = "distributed"
    ML_WORKER = "ml_worker"
    DATA_PROCESSOR = "data_processor"
    SERVICE_MESH = "service_mesh"
    FAULT_TOLERANT = "fault_tolerant"
    REAL_TIME = "real_time"
    BATCH_PROCESSOR = "batch_processor"


class DependencyScope(Enum):
    """Dependency injection scopes."""
    
    SINGLETON = "singleton"
    PROTOTYPE = "prototype"
    REQUEST = "request"
    SESSION = "session"
    AGENT_SCOPED = "agent_scoped"


@dataclass
class DependencyDescriptor:
    """Describes a dependency for injection."""
    
    interface: Type
    implementation: Optional[Type] = None
    scope: DependencyScope = DependencyScope.PROTOTYPE
    factory: Optional[Callable] = None
    config_key: Optional[str] = None
    lazy: bool = False
    required: bool = True


@dataclass
class AgentBlueprint:
    """Comprehensive blueprint for agent creation."""
    
    # Basic properties
    agent_class: Type[BaseAgent]
    agent_name: str
    template: AgentTemplate = AgentTemplate.BASIC
    
    # Configuration
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    environment_specific: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Dependencies
    dependencies: List[DependencyDescriptor] = field(default_factory=list)
    
    # Lifecycle settings
    auto_start: bool = True
    restart_policy: str = "on_failure"  # on_failure, always, never
    max_restarts: int = 5
    restart_delay_seconds: float = 1.0
    
    # Resource constraints
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    priority: int = 0  # Higher number = higher priority
    
    # Health monitoring
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    health_check_retries: int = 3
    
    # Performance settings
    enable_profiling: bool = False
    enable_metrics_collection: bool = True
    metrics_collection_interval: float = 10.0
    
    # Networking
    expose_metrics_port: Optional[int] = None
    expose_health_port: Optional[int] = None
    
    # Persistence
    persist_state: bool = False
    state_storage_path: Optional[str] = None
    
    # Custom properties
    custom_properties: Dict[str, Any] = field(default_factory=dict)


class DependencyContainer:
    """Dependency injection container for managing agent dependencies."""
    
    def __init__(self):
        self._dependencies: Dict[Type, DependencyDescriptor] = {}
        self._instances: Dict[Type, Any] = {}  # Singleton instances
        self._lock = threading.Lock()
        self.logger = logging.getLogger("dependency_container")
    
    def register(self, descriptor: DependencyDescriptor):
        """Register a dependency."""
        with self._lock:
            self._dependencies[descriptor.interface] = descriptor
            self.logger.debug(f"Registered dependency: {descriptor.interface.__name__}")
    
    def register_singleton(self, interface: Type, implementation: Type):
        """Register a singleton dependency."""
        descriptor = DependencyDescriptor(
            interface=interface,
            implementation=implementation,
            scope=DependencyScope.SINGLETON
        )
        self.register(descriptor)
    
    def register_factory(self, interface: Type, factory: Callable, scope: DependencyScope = DependencyScope.PROTOTYPE):
        """Register a factory function for dependency creation."""
        descriptor = DependencyDescriptor(
            interface=interface,
            factory=factory,
            scope=scope
        )
        self.register(descriptor)
    
    def resolve(self, interface: Type, context: Optional[Dict] = None) -> Any:
        """Resolve a dependency."""
        if interface not in self._dependencies:
            raise ValueError(f"Dependency not registered: {interface.__name__}")
        
        descriptor = self._dependencies[interface]
        
        # Handle singleton scope
        if descriptor.scope == DependencyScope.SINGLETON:
            if interface in self._instances:
                return self._instances[interface]
            
            instance = self._create_instance(descriptor, context)
            self._instances[interface] = instance
            return instance
        
        # Handle prototype and other scopes
        return self._create_instance(descriptor, context)
    
    def _create_instance(self, descriptor: DependencyDescriptor, context: Optional[Dict] = None):
        """Create an instance of a dependency."""
        try:
            if descriptor.factory:
                # Use factory function
                if context:
                    return descriptor.factory(**context)
                else:
                    return descriptor.factory()
            
            elif descriptor.implementation:
                # Use implementation class
                return descriptor.implementation()
            
            else:
                # Use interface as implementation
                return descriptor.interface()
                
        except Exception as e:
            if descriptor.required:
                raise RuntimeError(f"Failed to create dependency {descriptor.interface.__name__}: {e}")
            else:
                self.logger.warning(f"Optional dependency {descriptor.interface.__name__} failed to create: {e}")
                return None
    
    def inject_dependencies(self, instance: Any, context: Optional[Dict] = None):
        """Inject dependencies into an instance based on annotations."""
        if not hasattr(instance, '__annotations__'):
            return
        
        for attr_name, attr_type in instance.__annotations__.items():
            if attr_type in self._dependencies:
                try:
                    dependency = self.resolve(attr_type, context)
                    setattr(instance, attr_name, dependency)
                    self.logger.debug(f"Injected {attr_type.__name__} into {instance.__class__.__name__}.{attr_name}")
                except Exception as e:
                    self.logger.error(f"Failed to inject {attr_type.__name__}: {e}")


class TemplateRegistry:
    """Registry for agent templates with predefined configurations."""
    
    def __init__(self):
        self._templates: Dict[AgentTemplate, Dict[str, Any]] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default templates."""
        
        # Basic template - minimal configuration
        self._templates[AgentTemplate.BASIC] = {
            "enable_metrics_collection": True,
            "health_check_interval": 60.0,
            "restart_policy": "on_failure",
            "max_restarts": 3
        }
        
        # Monitoring template - enhanced observability
        self._templates[AgentTemplate.MONITORING] = {
            "enable_metrics_collection": True,
            "enable_profiling": True,
            "metrics_collection_interval": 5.0,
            "health_check_interval": 10.0,
            "expose_metrics_port": True,
            "expose_health_port": True
        }
        
        # High performance template - optimized for speed
        self._templates[AgentTemplate.HIGH_PERFORMANCE] = {
            "enable_metrics_collection": True,
            "metrics_collection_interval": 30.0,
            "health_check_interval": 30.0,
            "max_cpu_percent": 80.0,
            "priority": 10
        }
        
        # Distributed template - network-aware
        self._templates[AgentTemplate.DISTRIBUTED] = {
            "enable_metrics_collection": True,
            "health_check_interval": 15.0,
            "restart_policy": "always",
            "max_restarts": 10,
            "expose_metrics_port": True,
            "expose_health_port": True
        }
        
        # ML Worker template - ML-specific optimizations
        self._templates[AgentTemplate.ML_WORKER] = {
            "enable_metrics_collection": True,
            "enable_profiling": True,
            "max_memory_mb": 4096,
            "max_cpu_percent": 90.0,
            "health_check_interval": 30.0,
            "priority": 8
        }
        
        # Data Processor template - batch processing
        self._templates[AgentTemplate.DATA_PROCESSOR] = {
            "enable_metrics_collection": True,
            "health_check_interval": 45.0,
            "max_memory_mb": 2048,
            "restart_policy": "on_failure",
            "priority": 5
        }
        
        # Service Mesh template - microservice integration
        self._templates[AgentTemplate.SERVICE_MESH] = {
            "enable_metrics_collection": True,
            "health_check_interval": 10.0,
            "expose_metrics_port": True,
            "expose_health_port": True,
            "restart_policy": "always",
            "max_restarts": 20
        }
        
        # Fault Tolerant template - maximum resilience
        self._templates[AgentTemplate.FAULT_TOLERANT] = {
            "enable_metrics_collection": True,
            "health_check_interval": 5.0,
            "health_check_timeout": 2.0,
            "health_check_retries": 5,
            "restart_policy": "always",
            "max_restarts": 50,
            "restart_delay_seconds": 2.0,
            "persist_state": True
        }
        
        # Real Time template - low latency
        self._templates[AgentTemplate.REAL_TIME] = {
            "enable_metrics_collection": True,
            "metrics_collection_interval": 1.0,
            "health_check_interval": 5.0,
            "priority": 15,
            "max_cpu_percent": 95.0
        }
        
        # Batch Processor template - throughput optimized
        self._templates[AgentTemplate.BATCH_PROCESSOR] = {
            "enable_metrics_collection": True,
            "metrics_collection_interval": 60.0,
            "health_check_interval": 120.0,
            "max_memory_mb": 8192,
            "priority": 3
        }
    
    def get_template(self, template: AgentTemplate) -> Dict[str, Any]:
        """Get template configuration."""
        return self._templates.get(template, {}).copy()
    
    def register_template(self, template: AgentTemplate, config: Dict[str, Any]):
        """Register a custom template."""
        self._templates[template] = config.copy()
    
    def list_templates(self) -> List[AgentTemplate]:
        """List available templates."""
        return list(self._templates.keys())


class EnhancedAgentFactory(Generic[T]):
    """Advanced agent factory with dependency injection, templates, and lifecycle management."""
    
    def __init__(self):
        self.dependency_container = DependencyContainer()
        self.template_registry = TemplateRegistry()
        self.created_agents: Dict[str, weakref.ReferenceType] = {}
        self._agent_counter = 0
        self._lock = threading.Lock()
        self.logger = logging.getLogger("enhanced_agent_factory")
        
        # Initialize default dependencies
        self._initialize_default_dependencies()
    
    def _initialize_default_dependencies(self):
        """Initialize common dependencies."""
        # Configuration manager
        self.dependency_container.register_singleton(
            Config, Config
        )
        
        # Logger factory
        self.dependency_container.register_factory(
            logging.Logger,
            lambda name="default": logging.getLogger(name),
            DependencyScope.PROTOTYPE
        )
    
    def create_agent_from_blueprint(self, blueprint: AgentBlueprint) -> T:
        """Create an agent from a comprehensive blueprint."""
        try:
            with self._lock:
                self._agent_counter += 1
                agent_id = f"{blueprint.agent_name}_{self._agent_counter}"
            
            self.logger.info(f"Creating agent from blueprint: {blueprint.agent_name}")
            
            # Apply template configuration
            template_config = self.template_registry.get_template(blueprint.template)
            merged_config = {**template_config, **blueprint.config_overrides}
            
            # Apply environment-specific configuration
            current_env = merged_config.get('environment', 'dev')
            if current_env in blueprint.environment_specific:
                env_config = blueprint.environment_specific[current_env]
                merged_config.update(env_config)
            
            # Create enhanced agent instance
            enhanced_blueprint = self._enhance_blueprint_with_config(blueprint, merged_config)
            agent = self._create_enhanced_agent_instance(enhanced_blueprint, agent_id)
            
            # Inject dependencies
            dependency_context = {
                'agent_name': blueprint.agent_name,
                'agent_id': agent_id,
                'config': merged_config
            }
            self.dependency_container.inject_dependencies(agent, dependency_context)
            
            # Register dependencies specific to this blueprint
            for dep in blueprint.dependencies:
                if dep not in self.dependency_container._dependencies:
                    self.dependency_container.register(dep)
            
            # Store weak reference to created agent
            self.created_agents[agent_id] = weakref.ref(agent)
            
            self.logger.info(f"Successfully created agent: {blueprint.agent_name} (ID: {agent_id})")
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to create agent from blueprint {blueprint.agent_name}: {e}")
            raise
    
    def _enhance_blueprint_with_config(self, blueprint: AgentBlueprint, config: Dict[str, Any]) -> AgentBlueprint:
        """Enhance blueprint with merged configuration."""
        # Create a copy of the blueprint
        enhanced = AgentBlueprint(
            agent_class=blueprint.agent_class,
            agent_name=blueprint.agent_name,
            template=blueprint.template,
            config_overrides=config,
            environment_specific=blueprint.environment_specific,
            dependencies=blueprint.dependencies.copy(),
            auto_start=config.get('auto_start', blueprint.auto_start),
            restart_policy=config.get('restart_policy', blueprint.restart_policy),
            max_restarts=config.get('max_restarts', blueprint.max_restarts),
            restart_delay_seconds=config.get('restart_delay_seconds', blueprint.restart_delay_seconds),
            max_memory_mb=config.get('max_memory_mb', blueprint.max_memory_mb),
            max_cpu_percent=config.get('max_cpu_percent', blueprint.max_cpu_percent),
            priority=config.get('priority', blueprint.priority),
            health_check_interval=config.get('health_check_interval', blueprint.health_check_interval),
            health_check_timeout=config.get('health_check_timeout', blueprint.health_check_timeout),
            health_check_retries=config.get('health_check_retries', blueprint.health_check_retries),
            enable_profiling=config.get('enable_profiling', blueprint.enable_profiling),
            enable_metrics_collection=config.get('enable_metrics_collection', blueprint.enable_metrics_collection),
            metrics_collection_interval=config.get('metrics_collection_interval', blueprint.metrics_collection_interval),
            expose_metrics_port=config.get('expose_metrics_port', blueprint.expose_metrics_port),
            expose_health_port=config.get('expose_health_port', blueprint.expose_health_port),
            persist_state=config.get('persist_state', blueprint.persist_state),
            state_storage_path=config.get('state_storage_path', blueprint.state_storage_path),
            custom_properties={**blueprint.custom_properties, **config.get('custom_properties', {})}
        )
        
        return enhanced
    
    def _create_enhanced_agent_instance(self, blueprint: AgentBlueprint, agent_id: str) -> T:
        """Create the actual enhanced agent instance."""
        
        # Create enhanced agent class dynamically
        class BlueprintEnhancedAgent(EnhancedBaseAgent, blueprint.agent_class):
            def __init__(self):
                # Initialize enhanced base agent
                EnhancedBaseAgent.__init__(self, blueprint.agent_name, blueprint.config_overrides)
                
                # Store blueprint for reference
                self.blueprint = blueprint
                self.agent_id = agent_id
                
                # Apply custom properties
                for key, value in blueprint.custom_properties.items():
                    setattr(self, key, value)
                
                # Initialize the original agent class
                if hasattr(blueprint.agent_class, '__init__'):
                    try:
                        blueprint.agent_class.__init__(self)
                    except TypeError:
                        # Some agents might not accept parameters
                        pass
                
                # Apply resource constraints
                self._apply_resource_constraints()
            
            def _apply_resource_constraints(self):
                """Apply resource constraints from blueprint."""
                if blueprint.max_memory_mb:
                    self.max_memory_mb = blueprint.max_memory_mb
                
                if blueprint.max_cpu_percent:
                    self.max_cpu_percent = blueprint.max_cpu_percent
                
                self.priority = blueprint.priority
        
        return BlueprintEnhancedAgent()
    
    def create_agent_from_template(
        self,
        agent_class: Type[T],
        agent_name: str,
        template: AgentTemplate,
        **kwargs
    ) -> T:
        """Create an agent using a predefined template."""
        blueprint = AgentBlueprint(
            agent_class=agent_class,
            agent_name=agent_name,
            template=template,
            config_overrides=kwargs
        )
        return self.create_agent_from_blueprint(blueprint)
    
    def create_ml_worker(self, agent_class: Type[T], agent_name: str, **kwargs) -> T:
        """Convenience method to create ML worker agent."""
        return self.create_agent_from_template(
            agent_class, agent_name, AgentTemplate.ML_WORKER, **kwargs
        )
    
    def create_service_mesh_agent(self, agent_class: Type[T], agent_name: str, **kwargs) -> T:
        """Convenience method to create service mesh agent."""
        return self.create_agent_from_template(
            agent_class, agent_name, AgentTemplate.SERVICE_MESH, **kwargs
        )
    
    def create_fault_tolerant_agent(self, agent_class: Type[T], agent_name: str, **kwargs) -> T:
        """Convenience method to create fault-tolerant agent."""
        return self.create_agent_from_template(
            agent_class, agent_name, AgentTemplate.FAULT_TOLERANT, **kwargs
        )
    
    def get_created_agents(self) -> Dict[str, BaseAgent]:
        """Get all created agents that are still alive."""
        alive_agents = {}
        dead_refs = []
        
        for agent_id, agent_ref in self.created_agents.items():
            agent = agent_ref()
            if agent is not None:
                alive_agents[agent_id] = agent
            else:
                dead_refs.append(agent_id)
        
        # Clean up dead references
        for agent_id in dead_refs:
            del self.created_agents[agent_id]
        
        return alive_agents
    
    def get_agent_count(self) -> int:
        """Get the number of currently alive agents."""
        return len(self.get_created_agents())
    
    def register_dependency(self, descriptor: DependencyDescriptor):
        """Register a dependency in the container."""
        self.dependency_container.register(descriptor)
    
    def register_template(self, template: AgentTemplate, config: Dict[str, Any]):
        """Register a custom template."""
        self.template_registry.register_template(template, config)


# Global factory instance
_global_factory = None
_factory_lock = threading.Lock()


def get_enhanced_factory() -> EnhancedAgentFactory:
    """Get the global enhanced agent factory instance."""
    global _global_factory
    
    if _global_factory is None:
        with _factory_lock:
            if _global_factory is None:
                _global_factory = EnhancedAgentFactory()
    
    return _global_factory


# Convenience functions for common use cases
def create_agent_with_template(
    agent_class: Type[BaseAgent],
    agent_name: str,
    template: AgentTemplate,
    **kwargs
) -> BaseAgent:
    """Create an agent using a template."""
    factory = get_enhanced_factory()
    return factory.create_agent_from_template(agent_class, agent_name, template, **kwargs)


def create_ml_worker_agent(agent_class: Type[BaseAgent], agent_name: str, **kwargs) -> BaseAgent:
    """Create an ML worker agent."""
    factory = get_enhanced_factory()
    return factory.create_ml_worker(agent_class, agent_name, **kwargs)


def create_monitoring_agent(agent_class: Type[BaseAgent], agent_name: str, **kwargs) -> BaseAgent:
    """Create a monitoring agent."""
    factory = get_enhanced_factory()
    return factory.create_agent_from_template(agent_class, agent_name, AgentTemplate.MONITORING, **kwargs)


def create_distributed_agent(agent_class: Type[BaseAgent], agent_name: str, **kwargs) -> BaseAgent:
    """Create a distributed agent."""
    factory = get_enhanced_factory()
    return factory.create_agent_from_template(agent_class, agent_name, AgentTemplate.DISTRIBUTED, **kwargs)
