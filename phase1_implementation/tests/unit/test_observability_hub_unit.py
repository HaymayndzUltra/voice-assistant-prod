#!/usr/bin/env python3
"""
Unit tests for ObservabilityHub unified functionality
Tests the consolidated monitoring and observability features
"""

import sys
import os
from pathlib import Path
import threading
import time
from datetime import datetime, timedelta

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import what we need for testing
from phase1_implementation.consolidated_agents.observability_hub.observability_hub import (
    MetricData, HealthStatus, AlertRule, MetricsCollector, HealthMonitor, 
    AnomalyDetector, AlertManager
)

class TestObservabilityHubComponents:
    """Test suite for ObservabilityHub individual components"""
    
    def setup_method(self):
        """Setup for each test method"""
        os.environ['ENABLE_UNIFIED_HEALTH'] = 'true'
        os.environ['ENABLE_UNIFIED_PERFORMANCE'] = 'true' 
        os.environ['ENABLE_UNIFIED_PREDICTION'] = 'true'
    
    def test_metrics_collector_basic(self):
        """Test basic metrics collection functionality"""
        collector = MetricsCollector()
        
        # Test system metrics collection
        system_metrics = collector.collect_system_metrics()
        assert len(system_metrics) > 0
        
        # Check metric structure
        for metric in system_metrics:
            assert hasattr(metric, 'name')
            assert hasattr(metric, 'value')
            assert hasattr(metric, 'timestamp')
            assert hasattr(metric, 'tags')
            assert hasattr(metric, 'source')
            assert metric.source == "system"
        
        # Test GPU metrics collection (returns mock data)
        gpu_metrics = collector.collect_gpu_metrics()
        assert len(gpu_metrics) >= 0  # May return empty if no GPU
        
        print("✓ MetricsCollector basic functionality test passed")
    
    def test_health_monitor_basic(self):
        """Test basic health monitoring functionality"""
        monitor = HealthMonitor()
        
        # Test agent health update
        monitor.update_agent_health(
            agent_name="TestAgent",
            status="healthy",
            details={"cpu": 50.0, "memory": 60.0},
            location="MainPC"
        )
        
        # Test health retrieval
        health = monitor.get_agent_health("TestAgent")
        assert health is not None
        assert health.agent_name == "TestAgent"
        assert health.status == "healthy"
        assert health.location == "MainPC"
        assert "cpu" in health.details
        
        # Test non-existent agent
        health = monitor.get_agent_health("NonExistent")
        assert health is None
        
        # Test get all health status
        all_health = monitor.get_all_health_status()
        assert "TestAgent" in all_health
        assert len(all_health) == 1
        
        print("✓ HealthMonitor basic functionality test passed")
    
    def test_health_monitor_stale_detection(self):
        """Test stale agent detection"""
        monitor = HealthMonitor()
        
        # Add a current agent
        monitor.update_agent_health("CurrentAgent", "healthy", location="MainPC")
        
        # Add a stale agent by manually setting old timestamp
        stale_health = HealthStatus(
            agent_name="StaleAgent",
            status="healthy", 
            last_seen=datetime.utcnow() - timedelta(minutes=10),
            details={},
            location="PC2"
        )
        monitor.health_status["StaleAgent"] = stale_health
        
        # Test stale detection
        stale_agents = monitor.check_stale_agents(max_age_seconds=300)  # 5 minutes
        assert "StaleAgent" in stale_agents
        assert "CurrentAgent" not in stale_agents
        
        print("✓ HealthMonitor stale detection test passed")
    
    def test_anomaly_detector_basic(self):
        """Test basic anomaly detection functionality"""
        detector = AnomalyDetector()
        
        # Create baseline metrics (normal values around 50)
        baseline_values = [45, 48, 52, 49, 51, 47, 53, 50, 46, 54, 49, 52]
        for i, value in enumerate(baseline_values):
            metric = MetricData(
                name="test_metric",
                value=value,
                timestamp=datetime.utcnow(),
                tags={},
                source="test"
            )
            # First few won't trigger anomaly detection (need baseline)
            is_anomaly = detector.detect_anomaly(metric)
            if i < 10:
                assert not is_anomaly  # Not enough data for detection
        
        # Test normal value (should not be anomaly)
        normal_metric = MetricData(
            name="test_metric",
            value=48.0,
            timestamp=datetime.utcnow(),
            tags={},
            source="test"
        )
        is_anomaly = detector.detect_anomaly(normal_metric)
        assert not is_anomaly
        
        # Test anomalous value (very high)
        anomaly_metric = MetricData(
            name="test_metric", 
            value=150.0,  # Much higher than baseline ~50
            timestamp=datetime.utcnow(),
            tags={},
            source="test"
        )
        is_anomaly = detector.detect_anomaly(anomaly_metric)
        assert is_anomaly
        
        print("✓ AnomalyDetector basic functionality test passed")
    
    def test_alert_manager_basic(self):
        """Test basic alert management functionality"""
        manager = AlertManager()
        
        # Test adding alert rule
        rule = AlertRule(
            rule_id="cpu_high_test",
            metric_name="cpu_percent",
            condition="gt",
            threshold=80.0,
            enabled=True,
            severity="warning"
        )
        manager.add_alert_rule(rule)
        
        # Test rule was added
        assert "cpu_high_test" in manager.alert_rules
        
        # Test alert evaluation - no trigger
        normal_metric = MetricData(
            name="cpu_percent",
            value=60.0,
            timestamp=datetime.utcnow(),
            tags={},
            source="system"
        )
        alerts = manager.evaluate_alerts(normal_metric)
        assert len(alerts) == 0
        
        # Test alert evaluation - trigger
        high_metric = MetricData(
            name="cpu_percent",
            value=90.0,
            timestamp=datetime.utcnow(),
            tags={},
            source="system"
        )
        alerts = manager.evaluate_alerts(high_metric)
        assert len(alerts) == 1
        assert alerts[0]["rule_id"] == "cpu_high_test"
        assert alerts[0]["metric_value"] == 90.0
        assert alerts[0]["severity"] == "warning"
        
        # Test removing rule
        manager.remove_alert_rule("cpu_high_test")
        assert "cpu_high_test" not in manager.alert_rules
        
        print("✓ AlertManager basic functionality test passed")
    
    def test_alert_manager_conditions(self):
        """Test different alert conditions"""
        manager = AlertManager()
        
        # Add rules for different conditions
        rules = [
            AlertRule("gt_test", "test_metric", "gt", 50.0, True, "info"),
            AlertRule("lt_test", "test_metric", "lt", 50.0, True, "info"),
            AlertRule("eq_test", "test_metric", "eq", 50.0, True, "info"),
            AlertRule("ne_test", "test_metric", "ne", 50.0, True, "info"),
        ]
        
        for rule in rules:
            manager.add_alert_rule(rule)
        
        # Test with value 60 (should trigger gt and ne)
        test_metric = MetricData(
            name="test_metric",
            value=60.0,
            timestamp=datetime.utcnow(),
            tags={},
            source="test"
        )
        alerts = manager.evaluate_alerts(test_metric)
        triggered_rules = [alert["rule_id"] for alert in alerts]
        assert "gt_test" in triggered_rules
        assert "ne_test" in triggered_rules
        assert "lt_test" not in triggered_rules
        assert "eq_test" not in triggered_rules
        
        # Test with value 40 (should trigger lt and ne)
        test_metric.value = 40.0
        alerts = manager.evaluate_alerts(test_metric)
        triggered_rules = [alert["rule_id"] for alert in alerts]
        assert "lt_test" in triggered_rules
        assert "ne_test" in triggered_rules
        assert "gt_test" not in triggered_rules
        assert "eq_test" not in triggered_rules
        
        # Test with value 50 (should trigger eq only)
        test_metric.value = 50.0
        alerts = manager.evaluate_alerts(test_metric)
        triggered_rules = [alert["rule_id"] for alert in alerts]
        assert "eq_test" in triggered_rules
        assert "gt_test" not in triggered_rules
        assert "lt_test" not in triggered_rules
        assert "ne_test" not in triggered_rules
        
        print("✓ AlertManager conditions test passed")
    
    def test_thread_safety_health_monitor(self):
        """Test thread safety of health monitor"""
        monitor = HealthMonitor()
        results = []
        
        def update_agent_health(agent_id):
            """Helper function to update agent health"""
            agent_name = f"Agent_{agent_id}"
            monitor.update_agent_health(
                agent_name=agent_name,
                status="healthy",
                details={"test": "data"},
                location="MainPC"
            )
            results.append(agent_name)
        
        # Create multiple threads to update health concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_agent_health, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all updates succeeded
        assert len(results) == 10
        all_health = monitor.get_all_health_status()
        assert len(all_health) == 10
        
        for i in range(10):
            agent_name = f"Agent_{i}"
            assert agent_name in all_health
            assert all_health[agent_name].status == "healthy"
        
        print("✓ HealthMonitor thread safety test passed")
    
    def test_metrics_data_structure(self):
        """Test MetricData data structure"""
        timestamp = datetime.utcnow()
        metric = MetricData(
            name="test_metric",
            value=42.0,
            timestamp=timestamp,
            tags={"type": "test", "source": "unit_test"},
            source="test_collector"
        )
        
        assert metric.name == "test_metric"
        assert metric.value == 42.0
        assert metric.timestamp == timestamp
        assert metric.tags["type"] == "test"
        assert metric.source == "test_collector"
        
        print("✓ MetricData structure test passed")
    
    def test_health_status_data_structure(self):
        """Test HealthStatus data structure"""
        timestamp = datetime.utcnow()
        health = HealthStatus(
            agent_name="TestAgent",
            status="healthy",
            last_seen=timestamp,
            details={"cpu": 50.0, "memory": 60.0},
            location="MainPC"
        )
        
        assert health.agent_name == "TestAgent"
        assert health.status == "healthy"
        assert health.last_seen == timestamp
        assert health.details["cpu"] == 50.0
        assert health.location == "MainPC"
        
        print("✓ HealthStatus structure test passed")

if __name__ == "__main__":
    # Run tests with basic assertions
    test_suite = TestObservabilityHubComponents()
    
    try:
        test_suite.setup_method()
        
        test_suite.test_metrics_collector_basic()
        test_suite.test_health_monitor_basic()
        test_suite.test_health_monitor_stale_detection()
        test_suite.test_anomaly_detector_basic()
        test_suite.test_alert_manager_basic()
        test_suite.test_alert_manager_conditions()
        test_suite.test_thread_safety_health_monitor()
        test_suite.test_metrics_data_structure()
        test_suite.test_health_status_data_structure()
        
        print("\n🎉 All ObservabilityHub unit tests passed!")
        print("✅ Phase 1 ObservabilityHub functionality validated")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 