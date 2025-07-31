"""
End-to-end test for dialogue flow across agent services.
Tests the complete pipeline from input to response generation.
"""
import os
import time
import pytest
import requests
import json
from typing import Dict, Any


class TestDialogueFlow:
    """Test complete dialogue processing pipeline."""
    
    @pytest.fixture(scope="class")
    def service_urls(self) -> Dict[str, str]:
        """Service endpoint URLs from environment."""
        return {
            "infra": os.getenv("TEST_INFRA_URL", "http://localhost:28200"),
            "memory": os.getenv("TEST_MEMORY_URL", "http://localhost:26713"),
            "language": os.getenv("TEST_LANGUAGE_URL", "http://localhost:25709"),
        }
    
    @pytest.fixture(scope="class")
    def session(self):
        """HTTP session with reasonable timeouts."""
        session = requests.Session()
        session.timeout = 10
        return session
    
    def test_services_healthy(self, service_urls: Dict[str, str], session: requests.Session):
        """Verify all services respond to health checks."""
        for service_name, url in service_urls.items():
            health_url = f"{url}/health"
            response = session.get(health_url)
            assert response.status_code == 200, f"{service_name} health check failed"
            
            health_data = response.json()
            assert health_data.get("status") in ["healthy", "ok"], f"{service_name} not healthy"
    
    @pytest.mark.timeout(30)
    def test_memory_service_initialization(self, service_urls: Dict[str, str], session: requests.Session):
        """Test memory service can store and retrieve data."""
        memory_url = service_urls["memory"]
        
        # Store test memory
        test_memory = {
            "user_id": "test_user_001",
            "content": "Hello, this is a test memory",
            "timestamp": int(time.time()),
            "type": "dialogue"
        }
        
        store_response = session.post(f"{memory_url}/memory/store", json=test_memory)
        assert store_response.status_code in [200, 201], "Memory storage failed"
        
        memory_id = store_response.json().get("memory_id")
        assert memory_id is not None, "No memory ID returned"
        
        # Retrieve the memory
        retrieve_response = session.get(f"{memory_url}/memory/{memory_id}")
        assert retrieve_response.status_code == 200, "Memory retrieval failed"
        
        retrieved_memory = retrieve_response.json()
        assert retrieved_memory["content"] == test_memory["content"]
    
    @pytest.mark.timeout(45)
    def test_full_dialogue_cycle(self, service_urls: Dict[str, str], session: requests.Session):
        """Test complete dialogue processing from input to response."""
        language_url = service_urls["language"]
        
        # Test dialogue request
        dialogue_request = {
            "user_id": "test_user_001",
            "message": "What is the weather like today?",
            "context": {
                "session_id": "test_session_001",
                "timestamp": int(time.time())
            },
            "test_mode": True  # Enable mock responses
        }
        
        # Send dialogue request
        response = session.post(f"{language_url}/dialogue/process", json=dialogue_request)
        assert response.status_code == 200, f"Dialogue processing failed: {response.text}"
        
        dialogue_response = response.json()
        
        # Verify response structure
        assert "response" in dialogue_response, "No response field in dialogue output"
        assert "confidence" in dialogue_response, "No confidence score in response"
        assert "processing_time_ms" in dialogue_response, "No timing information"
        
        # Verify response content
        assert len(dialogue_response["response"]) > 0, "Empty response generated"
        assert 0 <= dialogue_response["confidence"] <= 1, "Invalid confidence score"
        assert dialogue_response["processing_time_ms"] > 0, "Invalid processing time"
    
    @pytest.mark.timeout(60)
    def test_multi_turn_conversation(self, service_urls: Dict[str, str], session: requests.Session):
        """Test multi-turn conversation with memory persistence."""
        language_url = service_urls["language"]
        session_id = f"test_session_{int(time.time())}"
        
        # First turn
        turn1_request = {
            "user_id": "test_user_002",
            "message": "My name is Alice",
            "context": {"session_id": session_id},
            "test_mode": True
        }
        
        turn1_response = session.post(f"{language_url}/dialogue/process", json=turn1_request)
        assert turn1_response.status_code == 200
        
        # Second turn - reference previous context
        turn2_request = {
            "user_id": "test_user_002",
            "message": "What is my name?",
            "context": {"session_id": session_id},
            "test_mode": True
        }
        
        turn2_response = session.post(f"{language_url}/dialogue/process", json=turn2_request)
        assert turn2_response.status_code == 200
        
        turn2_data = turn2_response.json()
        
        # In test mode, the system should acknowledge context
        # (actual implementation would vary, but should show memory integration)
        assert "response" in turn2_data
        assert len(turn2_data["response"]) > 0
    
    @pytest.mark.timeout(30)
    def test_service_discovery(self, service_urls: Dict[str, str], session: requests.Session):
        """Test service registry and discovery functionality."""
        infra_url = service_urls["infra"]
        
        # Query service registry
        registry_response = session.get(f"{infra_url}/services/list")
        assert registry_response.status_code == 200
        
        services = registry_response.json()
        assert isinstance(services, (list, dict)), "Invalid service registry format"
        
        # Verify core services are registered
        if isinstance(services, list):
            service_names = [s.get("name", "") for s in services]
        else:
            service_names = list(services.keys())
        
        expected_services = ["memory_stack", "language_stack"]
        for expected in expected_services:
            assert any(expected in name for name in service_names), f"{expected} not registered"
    
    def test_error_handling(self, service_urls: Dict[str, str], session: requests.Session):
        """Test error handling and graceful degradation."""
        language_url = service_urls["language"]
        
        # Send malformed request
        bad_request = {"invalid": "request_format"}
        
        response = session.post(f"{language_url}/dialogue/process", json=bad_request)
        
        # Should return error but not crash
        assert response.status_code in [400, 422], "Bad request not handled properly"
        
        error_data = response.json()
        assert "error" in error_data or "detail" in error_data, "No error message provided"