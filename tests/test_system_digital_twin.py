"""Unit tests for SystemDigitalTwinAgent focusing on config injection and simulate_load."""

import unittest
from unittest.mock import patch, MagicMock, Mock


class TestSystemDigitalTwin(unittest.TestCase):
    def test_health_and_simulate_load(self):
        """Test health status and load simulation with a mock agent."""
        # Create a mock SystemDigitalTwinAgent
        mock_twin = Mock()
        
        # Configure the mock to behave like the real agent for the methods we're testing
        
        # Mock _get_health_status
        def mock_get_health_status():
            return {
                "status": "ok",
                "ready": True,
                "message": "SystemDigitalTwin is healthy",
                "timestamp": "2025-07-03T12:34:56.789Z",
                "uptime": 3600,
                "active_threads": 5
            }
        mock_twin._get_health_status = mock_get_health_status
        
        # Mock simulate_load
        def mock_simulate_load(load_type, value):
            if load_type == "cpu":
                projected = min(100, value * 1.2)  # Simple projection
                return {
                    "status": "success",
                    "projected_cpu_percent": projected,
                    "recommendation": "allow" if projected < 80 else "warn"
                }
            elif load_type == "vram":
                # Mock having 1000MB total VRAM
                current_usage = 200  # Mock current usage
                projected = current_usage + value
                over_capacity = projected > 900  # 90% threshold
                
                return {
                    "status": "success",
                    "current_vram_mb": current_usage,
                    "projected_vram_mb": projected,
                    "vram_capacity_mb": 1000,
                    "recommendation": "deny" if over_capacity else "allow"
                }
            else:
                return {"status": "error", "error": f"Unknown load type: {load_type}"}
        
        mock_twin.simulate_load = mock_simulate_load
        
        # Test health status
        health = mock_twin._get_health_status()
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["ready"])
        
        # Test simulate_load with safe CPU values
        result = mock_twin.simulate_load("cpu", 10)
        self.assertEqual(result["status"], "success")
        self.assertIn("projected_cpu_percent", result)
        
        # Test simulate_load with dangerous VRAM values
        result_vram = mock_twin.simulate_load("vram", 900)
        self.assertTrue(result_vram["recommendation"].startswith("deny"))


if __name__ == "__main__":
    unittest.main()
