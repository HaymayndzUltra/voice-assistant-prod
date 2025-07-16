#!/usr/bin/env python3
"""
Integration tests for CoreOrchestrator
Tests the facade pattern implementation and delegation to existing agents
"""

import sys
import os
from pathlib import Path
import pytest
import requests
import time
import threading
import asyncio
import json

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from phase1_implementation.consolidated_agents.core_orchestrator.core_orchestrator import CoreOrchestrator

class TestCoreOrchestrator:
    """Test suite for CoreOrchestrator Phase 1 implementation"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.core_orchestrator_url = "http://localhost:7000"
        cls.orchestrator = None
        cls.server_thread = None
        
    @classmethod
    def teardown_class(cls):
        """Cleanup test environment"""
        if cls.orchestrator:
            cls.orchestrator.cleanup()
    
    def setup_method(self):
        """Setup for each test method"""
        # Set feature flags for testing
        os.environ['ENABLE_UNIFIED_REGISTRY'] = 'false'  # Start in delegation mode
        os.environ['ENABLE_UNIFIED_TWIN'] = 'false'
        os.environ['ENABLE_UNIFIED_COORDINATOR'] = 'false'
        os.environ['ENABLE_UNIFIED_SYSTEM'] = 'false'
    
    def test_core_orchestrator_initialization(self):
        """Test CoreOrchestrator initializes correctly"""
        orchestrator = CoreOrchestrator()
        
        # Check basic properties
        assert orchestrator.name == "CoreOrchestrator"
        assert orchestrator.port == 7000
        assert orchestrator.health_check_port == 7100
        
        # Check feature flags are read correctly
        assert orchestrator.enable_unified_registry == False
        assert orchestrator.enable_unified_twin == False
        assert orchestrator.enable_unified_coordinator == False
        assert orchestrator.enable_unified_system == False
        
        # Check internal state
        assert isinstance(orchestrator.internal_registry, dict)
        assert isinstance(orchestrator.agent_endpoints, dict)
        assert isinstance(orchestrator.system_metrics, dict)
        
        orchestrator.cleanup()
    
    def test_facade_pattern_feature_flags(self):
        """Test that feature flags control facade vs unified behavior"""
        # Test delegation mode
        os.environ['ENABLE_UNIFIED_REGISTRY'] = 'false'
        orchestrator = CoreOrchestrator()
        assert orchestrator.enable_unified_registry == False
        orchestrator.cleanup()
        
        # Test unified mode
        os.environ['ENABLE_UNIFIED_REGISTRY'] = 'true'
        orchestrator = CoreOrchestrator()
        assert orchestrator.enable_unified_registry == True
        orchestrator.cleanup()
        
        # Reset for other tests
        os.environ['ENABLE_UNIFIED_REGISTRY'] = 'false'
    
    def test_unified_registry_functionality(self):
        """Test unified registry mode functionality"""
        os.environ['ENABLE_UNIFIED_REGISTRY'] = 'true'
        orchestrator = CoreOrchestrator()
        
        # Test agent registration
        test_agent_data = {
            "name": "TestAgent",
            "port": 9999,
            "host": "localhost",
            "capabilities": ["testing"],
            "agent_type": "test"
        }
        
        result = orchestrator._handle_unified_registration(test_agent_data)
        assert result["status"] == "success"
        assert "TestAgent" in orchestrator.internal_registry
        
        # Test agent discovery
        discovery_result = orchestrator._handle_unified_discovery("TestAgent")
        assert discovery_result["status"] == "success"
        assert discovery_result["agent"]["name"] == "TestAgent"
        
        # Test non-existent agent
        not_found_result = orchestrator._handle_unified_discovery("NonExistentAgent")
        assert not_found_result["status"] == "error"
        
        orchestrator.cleanup()
    
    def test_unified_coordination_functionality(self):
        """Test unified coordination mode functionality"""
        os.environ['ENABLE_UNIFIED_COORDINATOR'] = 'true'
        orchestrator = CoreOrchestrator()
        
        # Register a test agent first
        test_agent_data = {
            "name": "TargetAgent",
            "port": 8888,
            "host": "localhost"
        }
        orchestrator._handle_unified_registration(test_agent_data)
        
        # Test request coordination
        coordination_request = {
            "target_agent": "TargetAgent",
            "action": "test_action",
            "data": {"test": "value"}
        }
        
        result = orchestrator._handle_unified_coordination(coordination_request)
        assert result["status"] == "success"
        assert "request_id" in result
        assert result["target_endpoint"]["port"] == 8888
        
        # Test coordination to non-existent agent
        bad_request = {
            "target_agent": "NonExistentAgent",
            "action": "test_action"
        }
        
        bad_result = orchestrator._handle_unified_coordination(bad_request)
        assert bad_result["status"] == "error"
        
        orchestrator.cleanup()
    
    def test_unified_system_status(self):
        """Test unified system status functionality"""
        os.environ['ENABLE_UNIFIED_TWIN'] = 'true'
        orchestrator = CoreOrchestrator()
        
        # Test system status
        status_result = orchestrator._handle_unified_status()
        assert status_result["status"] == "success"
        assert status_result["system_status"] == "operational"
        assert "metrics" in status_result
        
        # Check metrics content
        metrics = status_result["metrics"]
        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "registered_agents" in metrics
        assert "timestamp" in metrics
        
        orchestrator.cleanup()
    
    def test_unified_event_handling(self):
        """Test unified event handling functionality"""
        os.environ['ENABLE_UNIFIED_TWIN'] = 'true'
        orchestrator = CoreOrchestrator()
        
        # Test event publishing
        test_event = {
            "event_type": "test_event",
            "source_agent": "TestAgent",
            "data": {"test": "data"}
        }
        
        result = orchestrator._handle_unified_event(test_event)
        assert result["status"] == "success"
        assert "event_id" in result
        
        orchestrator.cleanup()
    
    def test_migration_state_import(self):
        """Test state import functionality for migration"""
        orchestrator = CoreOrchestrator()
        
        # Test registry state import
        registry_state = {
            "agents": {
                "Agent1": {
                    "name": "Agent1",
                    "port": 5001,
                    "host": "localhost",
                    "status": "healthy"
                },
                "Agent2": {
                    "name": "Agent2", 
                    "port": 5002,
                    "host": "localhost",
                    "status": "healthy"
                }
            }
        }
        
        import_result = orchestrator._import_registry_state(registry_state)
        assert import_result["status"] == "success"
        assert import_result["imported_agents"] == 2
        assert "Agent1" in orchestrator.internal_registry
        assert "Agent2" in orchestrator.internal_registry
        
        # Test twin state import
        twin_state = {
            "system_metrics": {
                "cpu_usage": 50.0,
                "memory_usage": 60.0
            }
        }
        
        twin_import_result = orchestrator._import_twin_state(twin_state)
        assert twin_import_result["status"] == "success"
        
        # Test coordinator state import
        coordinator_state = {
            "routing_config": {"default_route": "agent1"},
            "task_queue": {"pending": []}
        }
        
        coord_import_result = orchestrator._import_coordinator_state(coordinator_state)
        assert coord_import_result["status"] == "success"
        
        orchestrator.cleanup()
    
    def test_api_route_setup(self):
        """Test that FastAPI routes are properly configured"""
        orchestrator = CoreOrchestrator()
        
        # Check that FastAPI app is created
        assert orchestrator.app is not None
        assert orchestrator.app.title == "CoreOrchestrator"
        
        # Check that routes are defined (we can't easily test HTTP endpoints without starting server)
        routes = [getattr(route, 'path', '') for route in orchestrator.app.routes if hasattr(route, 'path')]
        
        expected_routes = [
            "/health",
            "/status", 
            "/register_agent",
            "/get_agent_endpoint/{agent_name}",
            "/list_agents",
            "/coordinate_request",
            "/metrics",
            "/publish_event",
            "/system_info",
            "/import_registry_state",
            "/import_twin_state",
            "/import_coordinator_state"
        ]
        
        for expected_route in expected_routes:
            # Check if route exists (may have different formatting)
            route_exists = any(expected_route.replace("{agent_name}", "agent_name") in route or 
                             expected_route in route for route in routes)
            assert route_exists, f"Route {expected_route} not found in {routes}"
        
        orchestrator.cleanup()
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        orchestrator = CoreOrchestrator()
        
        # Test invalid registration data
        invalid_data = {"invalid": "data"}
        result = orchestrator._handle_unified_registration(invalid_data)
        assert result["status"] == "error"
        
        # Test discovery of non-existent agent
        result = orchestrator._handle_unified_discovery("NonExistent")
        assert result["status"] == "error"
        
        # Test coordination with invalid data
        invalid_coord = {"invalid": "coordination"}
        result = orchestrator._handle_unified_coordination(invalid_coord)
        assert result["status"] == "error"
        
        orchestrator.cleanup()
    
    def test_thread_safety(self):
        """Test that the orchestrator handles concurrent operations safely"""
        os.environ['ENABLE_UNIFIED_REGISTRY'] = 'true'
        orchestrator = CoreOrchestrator()
        
        results = []
        
        def register_agent(agent_id):
            """Helper function to register an agent"""
            agent_data = {
                "name": f"Agent_{agent_id}",
                "port": 5000 + agent_id,
                "host": "localhost"
            }
            result = orchestrator._handle_unified_registration(agent_data)
            results.append(result)
        
        # Create multiple threads to register agents concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_agent, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all registrations succeeded
        assert len(results) == 10
        for result in results:
            assert result["status"] == "success"
        
        # Check that all agents are in registry
        assert len(orchestrator.internal_registry) == 10
        
        orchestrator.cleanup()
    
    def test_delegation_fallback(self):
        """Test that delegation methods handle errors gracefully"""
        orchestrator = CoreOrchestrator()
        
        # These will fail since no actual services are running, but should handle gracefully
        import asyncio
        
        async def test_delegations():
            # Test service registry delegation
            result = await orchestrator._delegate_to_service_registry({"action": "test"})
            assert "error" in result["status"] or "delegated" in result.get("status", "")
            
            # Test system twin delegation
            result = await orchestrator._delegate_to_system_twin({"action": "test"})
            assert "error" in result["status"] or "delegated" in result.get("status", "")
            
            # Test request coordinator delegation
            result = await orchestrator._delegate_to_request_coordinator({"action": "test"})
            assert "error" in result["status"] or "delegated" in result.get("status", "")
        
        asyncio.run(test_delegations())
        orchestrator.cleanup()

if __name__ == "__main__":
    # Run tests with basic assertions
    test_suite = TestCoreOrchestrator()
    test_suite.setup_class()
    
    try:
        test_suite.test_core_orchestrator_initialization()
        print("✓ Core orchestrator initialization test passed")
        
        test_suite.test_facade_pattern_feature_flags()
        print("✓ Facade pattern feature flags test passed")
        
        test_suite.test_unified_registry_functionality()
        print("✓ Unified registry functionality test passed")
        
        test_suite.test_unified_coordination_functionality()
        print("✓ Unified coordination functionality test passed")
        
        test_suite.test_unified_system_status()
        print("✓ Unified system status test passed")
        
        test_suite.test_unified_event_handling()
        print("✓ Unified event handling test passed")
        
        test_suite.test_migration_state_import()
        print("✓ Migration state import test passed")
        
        test_suite.test_api_route_setup()
        print("✓ API route setup test passed")
        
        test_suite.test_error_handling()
        print("✓ Error handling test passed")
        
        test_suite.test_thread_safety()
        print("✓ Thread safety test passed")
        
        test_suite.test_delegation_fallback()
        print("✓ Delegation fallback test passed")
        
        print("\n🎉 All CoreOrchestrator tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        test_suite.teardown_class() 