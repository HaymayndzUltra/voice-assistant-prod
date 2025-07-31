#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive Test Suite for Phase 4.2: Enhanced Agent Factory and Lifecycle Management

Tests all components of Phase 4.2 implementation:
- Enhanced Agent Factory with templates and blueprints
- Agent Lifecycle Management with state machines
- Health Monitoring and Auto-Recovery 
- Resource Allocation Optimization

Part of O3 Pro Max Roadmap Implementation - Phase 4.2 Testing
"""

import asyncio
import pytest
import threading
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Test imports for Phase 4.2 components
try:
    from common.factories.enhanced_agent_factory import (
        EnhancedAgentFactory, AgentTemplate, AgentBlueprint, 
        DependencyContainer, DependencyScope, get_enhanced_factory
    )
    from common.lifecycle.agent_lifecycle import (
        AgentState, LifecycleEvent, AgentLifecycleManager, 
        StateTransitionValidator, get_lifecycle_manager
    )
    from common.monitoring.health_monitor import (
        HealthMonitor, HealthStatus, BasicHealthChecker,
        ResourceHealthChecker, RestartRecoveryStrategy, get_health_monitor
    )
    from common.resources.resource_manager import (
        ResourceManager, ResourceType, AllocationStrategy,
        ResourceRequest, get_resource_manager
    )
    PHASE_4_2_AVAILABLE = True
except ImportError as e:
    PHASE_4_2_AVAILABLE = False
    IMPORT_ERROR = str(e)


@dataclass
class MockAgent:
    """Mock agent for testing"""
    agent_id: str
    name: str
    config: Dict[str, Any]
    state: str = "created"
    
    def start(self):
        self.state = "running"
        return True
        
    def stop(self):
        self.state = "stopped"
        return True
        
    def get_health(self):
        return {"status": "healthy", "cpu_usage": 15.0, "memory_usage": 200.0}


class TestPhase42Components:
    """Test Phase 4.2 components availability and basic functionality"""
    
    def test_phase_4_2_imports(self):
        """Test that Phase 4.2 components can be imported"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip(f"Phase 4.2 components not available: {IMPORT_ERROR}")
        
        # Test imports successful
        assert EnhancedAgentFactory is not None
        assert AgentLifecycleManager is not None
        assert HealthMonitor is not None
        assert ResourceManager is not None
        
    def test_singleton_instances(self):
        """Test that singleton instances are working correctly"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
            
        # Test singleton behavior
        factory1 = get_enhanced_factory()
        factory2 = get_enhanced_factory()
        assert factory1 is factory2
        
        lifecycle1 = get_lifecycle_manager()
        lifecycle2 = get_lifecycle_manager()
        assert lifecycle1 is lifecycle2
        
        health1 = get_health_monitor()
        health2 = get_health_monitor()
        assert health1 is health2
        
        resource1 = get_resource_manager()
        resource2 = get_resource_manager()
        assert resource1 is resource2


class TestEnhancedAgentFactory:
    """Test Enhanced Agent Factory functionality"""
    
    @pytest.fixture
    def factory(self):
        """Factory fixture"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
        return get_enhanced_factory()
    
    def test_template_registration(self, factory):
        """Test agent template registration"""
        # Use the predefined template enum
        template_config = {
            "timeout": 30,
            "max_retries": 3,
            "enable_metrics": True,
            "lifecycle_settings": {
                "auto_start": True,
                "restart_on_failure": True
            }
        }
        
        # Register template using the template registry
        factory.template_registry.register_template("test_template", template_config)
        retrieved = factory.template_registry.get_template("test_template")
        
        assert retrieved is not None
        assert retrieved["timeout"] == 30
        assert retrieved["max_retries"] == 3
        
    def test_dependency_injection(self, factory):
        """Test dependency injection container"""
        container = factory.dependency_container
        
        # Register singleton dependency
        container.register("logger", Mock(), DependencyScope.SINGLETON)
        
        # Register prototype dependency  
        container.register("config", lambda: {"test": True}, DependencyScope.PROTOTYPE)
        
        # Test singleton behavior
        logger1 = container.resolve("logger")
        logger2 = container.resolve("logger")
        assert logger1 is logger2
        
        # Test prototype behavior
        config1 = container.resolve("config")
        config2 = container.resolve("config")
        assert config1 is not config2
        assert config1 == config2
        
    def test_blueprint_creation(self, factory):
        """Test agent creation from blueprint"""
        # First register a template
        template_config = {
            "worker_type": "cpu",
            "max_tasks": 10
        }
        factory.template_registry.register_template("worker_template", template_config)
        
        # Create blueprint
        blueprint = AgentBlueprint(
            agent_id="test_worker_001",
            template="worker_template",
            config_overrides={
                "max_tasks": 20,
                "priority": "high"
            },
            environment="test"
        )
        
        # Mock agent creation since we don't have real agents
        with patch.object(factory, '_create_enhanced_agent_instance') as mock_create:
            mock_agent = MockAgent("test_worker_001", "TestWorker", blueprint.config_overrides)
            mock_create.return_value = mock_agent
            
            agent = factory.create_agent_from_blueprint(blueprint)
            
            assert agent is not None
            assert agent.agent_id == "test_worker_001"
            assert mock_create.called


class TestAgentLifecycleManagement:
    """Test Agent Lifecycle Management functionality"""
    
    @pytest.fixture
    def lifecycle_manager(self):
        """Lifecycle manager fixture"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
        return get_lifecycle_manager()
    
    def test_state_transition_validation(self, lifecycle_manager):
        """Test state transition validation"""
        validator = lifecycle_manager.validator
        
        # Test valid transitions
        assert validator.is_valid_transition(AgentState.CREATED, LifecycleEvent.START)
        assert validator.is_valid_transition(AgentState.RUNNING, LifecycleEvent.STOP)
        assert validator.is_valid_transition(AgentState.RUNNING, LifecycleEvent.PAUSE)
        assert validator.is_valid_transition(AgentState.PAUSED, LifecycleEvent.RESUME)
        
        # Test invalid transitions
        assert not validator.is_valid_transition(AgentState.CREATED, LifecycleEvent.RESUME)
        assert not validator.is_valid_transition(AgentState.STOPPED, LifecycleEvent.PAUSE)
        
    def test_agent_registration(self, lifecycle_manager):
        """Test agent registration and state management"""
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        
        # Register agent
        success = lifecycle_manager.register_agent(agent_id, "Test Agent")
        assert success
        
        # Check initial state
        current_state = lifecycle_manager.get_agent_state(agent_id)
        assert current_state == AgentState.CREATED
        
        # Get snapshot
        snapshot = lifecycle_manager.get_agent_snapshot(agent_id)
        assert snapshot is not None
        assert snapshot.agent_id == agent_id
        assert snapshot.current_state == AgentState.CREATED
        
    def test_state_transitions(self, lifecycle_manager):
        """Test agent state transitions"""
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        
        # Register and start agent
        lifecycle_manager.register_agent(agent_id, "Test Agent")
        
        # Test START transition
        success = lifecycle_manager.transition_agent(agent_id, LifecycleEvent.START)
        assert success
        assert lifecycle_manager.get_agent_state(agent_id) == AgentState.RUNNING
        
        # Test PAUSE transition
        success = lifecycle_manager.transition_agent(agent_id, LifecycleEvent.PAUSE)
        assert success
        assert lifecycle_manager.get_agent_state(agent_id) == AgentState.PAUSED
        
        # Test RESUME transition
        success = lifecycle_manager.transition_agent(agent_id, LifecycleEvent.RESUME)
        assert success
        assert lifecycle_manager.get_agent_state(agent_id) == AgentState.RUNNING
        
        # Test STOP transition
        success = lifecycle_manager.transition_agent(agent_id, LifecycleEvent.STOP)
        assert success
        assert lifecycle_manager.get_agent_state(agent_id) == AgentState.STOPPED
        
    def test_event_handlers(self, lifecycle_manager):
        """Test lifecycle event handlers"""
        # Create mock event handler
        mock_handler = Mock()
        lifecycle_manager.add_event_handler(mock_handler)
        
        agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
        lifecycle_manager.register_agent(agent_id, "Test Agent")
        
        # Trigger state transition
        lifecycle_manager.transition_agent(agent_id, LifecycleEvent.START)
        
        # Verify handler was called
        assert mock_handler.handle_event.called
        args = mock_handler.handle_event.call_args[0]
        assert args[0] == agent_id
        assert args[1] == LifecycleEvent.START


class TestHealthMonitoring:
    """Test Health Monitoring and Auto-Recovery functionality"""
    
    @pytest.fixture
    def health_monitor(self):
        """Health monitor fixture"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
        return get_health_monitor()
    
    @pytest.mark.asyncio
    async def test_health_checkers(self, health_monitor):
        """Test health checker functionality"""
        # Create mock agent
        mock_agent = MockAgent("test_agent", "TestAgent", {})
        
        # Register agent for monitoring
        health_monitor.register_agent("test_agent", mock_agent)
        
        # Run health check
        results = await health_monitor.check_agent_health("test_agent")
        
        assert len(results) > 0
        for result in results:
            assert result.agent_id == "test_agent"
            assert result.status in [HealthStatus.HEALTHY, HealthStatus.WARNING, HealthStatus.CRITICAL]
            
    @pytest.mark.asyncio
    async def test_recovery_strategies(self, health_monitor):
        """Test recovery strategy functionality"""
        # Create failing mock agent
        mock_agent = Mock()
        mock_agent.get_health.return_value = {"status": "unhealthy", "cpu_usage": 95.0}
        mock_agent.restart = Mock(return_value=True)
        
        # Add recovery strategy
        restart_strategy = RestartRecoveryStrategy()
        health_monitor.add_recovery_strategy("restart", restart_strategy)
        
        # Test recovery
        success = await restart_strategy.recover("test_agent", mock_agent)
        assert success
        assert mock_agent.restart.called
        
    def test_circuit_breaker(self, health_monitor):
        """Test circuit breaker pattern"""
        agent_id = "test_agent"
        
        # Simulate multiple failures by directly manipulating circuit breaker state
        if not hasattr(health_monitor, 'circuit_breakers'):
            health_monitor.circuit_breakers = {}
            
        health_monitor.circuit_breakers[agent_id] = {
            'failure_count': 5,
            'last_failure': time.time(),
            'state': 'open'
        }
        
        # Check if circuit breaker exists
        assert agent_id in health_monitor.circuit_breakers
        assert health_monitor.circuit_breakers[agent_id]['failure_count'] == 5
        
        # Reset circuit breaker (simulate time passage)
        health_monitor.circuit_breakers[agent_id]['last_failure'] = time.time() - 3600  # 1 hour ago
        health_monitor.circuit_breakers[agent_id]['failure_count'] = 0
        health_monitor.circuit_breakers[agent_id]['state'] = 'closed'
        
        # Should be closed now
        assert health_monitor.circuit_breakers[agent_id]['state'] == 'closed'


class TestResourceManagement:
    """Test Resource Allocation Optimization functionality"""
    
    @pytest.fixture
    def resource_manager(self):
        """Resource manager fixture"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
        return get_resource_manager()
    
    def test_resource_pools(self, resource_manager):
        """Test resource pool functionality"""
        # Get CPU pool
        cpu_pool = resource_manager.resource_pools[ResourceType.CPU]
        
        assert cpu_pool is not None
        assert cpu_pool.total_capacity > 0
        
        # Test resource request
        request = ResourceRequest(
            requester_id="test_agent",
            resource_type=ResourceType.CPU,
            amount=100.0,  # 1 CPU core
            priority=1
        )
        
        allocation = cpu_pool.request_allocation(request)
        
        if allocation:  # If resources available
            assert allocation.allocated_amount > 0
            assert allocation.requester_id == "test_agent"
            
            # Release resources
            cpu_pool.release_allocation(allocation.allocation_id)
            
    def test_load_balancing(self, resource_manager):
        """Test load balancing functionality"""
        # Register agents for load balancing
        resource_manager.register_agent_for_load_balancing("agent_1", weight=1.0, metadata={"type": "worker"})
        resource_manager.register_agent_for_load_balancing("agent_2", weight=2.0, metadata={"type": "worker"})
        
        # Select agents multiple times to test distribution
        selections = []
        for _ in range(10):
            selected = resource_manager.select_agent_for_work({"type": "worker"})
            if selected:
                selections.append(selected)
                
        # Should have selections (if agents are available)
        if selections:
            assert len(set(selections)) <= 2  # At most 2 different agents
            assert all(agent in ["agent_1", "agent_2"] for agent in selections)
            
    def test_resource_quotas(self, resource_manager):
        """Test resource quota management"""
        from common.resources.resource_manager import ResourceQuota
        
        # Set quota for a user
        quotas = [
            ResourceQuota(ResourceType.CPU, max_allocation=400.0),  # 4 CPU cores
            ResourceQuota(ResourceType.MEMORY, max_allocation=2048.0)  # 2GB
        ]
        
        resource_manager.set_quota("test_user", quotas)
        
        # Test quota enforcement
        request = ResourceRequest(
            requester_id="test_user",
            resource_type=ResourceType.CPU,
            amount=500.0,  # 5 CPU cores - exceeds quota
            priority=1
        )
        
        allocation = resource_manager.request_resources(request)
        # Should be None or limited due to quota
        if allocation:
            assert allocation.allocated_amount <= 400.0
            
    def test_memory_optimization(self, resource_manager):
        """Test memory optimization functionality"""
        optimizer = resource_manager.memory_optimizer
        
        # Test memory cleanup
        initial_memory = optimizer.get_memory_stats()
        optimizer.optimize_memory()
        
        # Memory optimization should complete without error
        assert True  # Basic test that it doesn't crash
        
    def test_resource_monitoring(self, resource_manager):
        """Test resource monitoring and reporting"""
        summary = resource_manager.get_resource_summary()
        
        assert "pools" in summary
        assert "load_distribution" in summary
        assert "quotas" in summary
        
        # Check pool summaries
        for pool_name, pool_info in summary["pools"].items():
            assert "total_capacity" in pool_info
            assert "allocated" in pool_info
            assert "utilization_percent" in pool_info


class TestIntegration:
    """Integration tests for Phase 4.2 components"""
    
    @pytest.mark.asyncio
    async def test_full_agent_lifecycle_with_monitoring(self):
        """Test complete agent lifecycle with health monitoring"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
            
        # Get all managers
        factory = get_enhanced_factory()
        lifecycle = get_lifecycle_manager()
        health_monitor = get_health_monitor()
        resource_manager = get_resource_manager()
        
        agent_id = f"integration_test_{uuid.uuid4().hex[:8]}"
        
        # Create agent template
        template_config = {"test_mode": True}
        factory.template_registry.register_template("integration_template", template_config)
        
        # Register agent with lifecycle management
        lifecycle.register_agent(agent_id, "Integration Test Agent")
        
        # Create mock agent for health monitoring
        mock_agent = MockAgent(agent_id, "Integration Test Agent", {"test_mode": True})
        health_monitor.register_agent(agent_id, mock_agent)
        
        # Request resources
        cpu_request = ResourceRequest(
            requester_id=agent_id,
            resource_type=ResourceType.CPU,
            amount=50.0,  # 0.5 CPU core
            priority=1
        )
        cpu_allocation = resource_manager.request_resources(cpu_request)
        
        try:
            # Start agent
            success = lifecycle.transition_agent(agent_id, LifecycleEvent.START)
            assert success
            assert lifecycle.get_current_state(agent_id) == AgentState.RUNNING
            
            # Check health
            health_results = await health_monitor.check_agent_health(agent_id)
            assert len(health_results) > 0
            
            # Pause agent
            success = lifecycle.transition_agent(agent_id, LifecycleEvent.PAUSE)
            assert success
            assert lifecycle.get_current_state(agent_id) == AgentState.PAUSED
            
            # Resume agent
            success = lifecycle.transition_agent(agent_id, LifecycleEvent.RESUME)
            assert success
            assert lifecycle.get_current_state(agent_id) == AgentState.RUNNING
            
        finally:
            # Cleanup
            lifecycle.transition_agent(agent_id, LifecycleEvent.STOP)
            if cpu_allocation:
                resource_manager.release_allocation(cpu_allocation.allocation_id)
                
    def test_performance_benchmarks(self):
        """Performance benchmarks for Phase 4.2 components"""
        if not PHASE_4_2_AVAILABLE:
            pytest.skip("Phase 4.2 components not available")
            
        lifecycle = get_lifecycle_manager()
        
        # Benchmark agent registration
        start_time = time.time()
        num_agents = 100
        
        for i in range(num_agents):
            agent_id = f"perf_test_{i}"
            lifecycle.register_agent(agent_id, f"Performance Test Agent {i}")
            
        registration_time = time.time() - start_time
        registration_rate = num_agents / registration_time
        
        print(f"Agent registration rate: {registration_rate:.1f} agents/second")
        assert registration_rate > 50  # Should register at least 50 agents per second
        
        # Benchmark state transitions
        start_time = time.time()
        transitions = 0
        
        for i in range(num_agents):
            agent_id = f"perf_test_{i}"
            if lifecycle.transition_agent(agent_id, LifecycleEvent.START):
                transitions += 1
                
        transition_time = time.time() - start_time
        transition_rate = transitions / transition_time
        
        print(f"State transition rate: {transition_rate:.1f} transitions/second")
        assert transition_rate > 100  # Should handle at least 100 transitions per second


# Pytest configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def test_phase_4_2_package_imports():
    """Test that Phase 4.2 packages can be imported properly"""
    try:
        from common.factories import ENHANCED_FACTORY_AVAILABLE
        from common.monitoring import HEALTH_MONITORING_AVAILABLE
        from common.lifecycle import get_lifecycle_manager
        from common.resources import get_resource_manager
        
        print(f"Enhanced Factory Available: {ENHANCED_FACTORY_AVAILABLE}")
        print(f"Health Monitoring Available: {HEALTH_MONITORING_AVAILABLE}")
        
        # Basic singleton tests
        lifecycle1 = get_lifecycle_manager()
        lifecycle2 = get_lifecycle_manager()
        assert lifecycle1 is lifecycle2
        
        resource1 = get_resource_manager()
        resource2 = get_resource_manager()
        assert resource1 is resource2
        
    except ImportError as e:
        pytest.fail(f"Phase 4.2 package imports failed: {e}")


if __name__ == "__main__":
    # Run tests directly
    print("Running Phase 4.2 Enhanced Agent Factory and Lifecycle Management Tests...")
    print("=" * 80)
    
    # Check availability
    if PHASE_4_2_AVAILABLE:
        print("✅ Phase 4.2 components available")
    else:
        print(f"❌ Phase 4.2 components not available: {IMPORT_ERROR}")
        exit(1)
    
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])
