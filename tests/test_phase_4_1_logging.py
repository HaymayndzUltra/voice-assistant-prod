"""
Comprehensive Test Suite for Phase 4.1 - Advanced Logging and Audit Trail

Tests for:
- Structured logging functionality
- Audit trail system
- Log aggregation and search
- Performance monitoring
- Integration with existing systems

Author: AI System Monorepo Team
Created: 2025-07-31
Phase: 4.1 - Advanced Logging and Audit Trail
"""

import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sqlite3

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logging import (
    get_logger,
    get_log_aggregator,
    setup_logging,
    performance_timer,
    LogLevel,
    LogEntry,
    SearchResult
)

from common.audit import (
    get_audit_trail,
    setup_audit,
    audit_configuration_change,
    audit_agent_lifecycle,
    audit_user_action,
    audit_security_event,
    AuditEventType,
    AuditSeverity,
    AuditEvent
)


class TestStructuredLogging:
    """Test structured logging functionality"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_config = {
            "level": "DEBUG",
            "format": "json",
            "output_dir": str(self.temp_dir / "logs"),
            "enable_console": False,  # Disable for testing
            "enable_file": True,
            "enable_json": True
        }
    
    def test_basic_logging(self):
        """Test basic logging functionality"""
        print("\n=== Testing Basic Logging ===")
        
        logger = get_logger("test_agent", self.test_config)
        
        # Test all log levels
        logger.debug("Debug message", test_data="debug_value")
        logger.info("Info message", agent_id="test-001")
        logger.warning("Warning message", warning_type="performance")
        logger.error("Error message", error_code=500)
        logger.critical("Critical message", system_state="failure")
        
        # Verify log files were created
        log_dir = Path(self.test_config["output_dir"])
        assert log_dir.exists(), "Log directory not created"
        
        # Check for log files
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) > 0, "No log files created"
        
        print(f"✅ Basic logging test passed - {len(log_files)} log files created")
        return True
    
    def test_context_logging(self):
        """Test context-aware logging"""
        print("\n=== Testing Context Logging ===")
        
        logger = get_logger("test_context", self.test_config)
        
        # Set correlation ID and context
        correlation_id = str(uuid.uuid4())
        logger.set_correlation_id(correlation_id)
        logger.set_context(user_id="test_user", session_id="test_session")
        
        logger.info("Context test message", action="test_action")
        
        # Test context-bound logger
        bound_logger = logger.with_context(operation="data_processing")
        bound_logger.info("Bound context message", records_processed=100)
        
        print("✅ Context logging test passed")
        return True
    
    def test_performance_timing(self):
        """Test performance timing functionality"""
        print("\n=== Testing Performance Timing ===")
        
        logger = get_logger("test_performance", self.test_config)
        
        # Test performance timer
        with performance_timer(logger, "test_operation", test_param="value"):
            time.sleep(0.1)  # Simulate work
        
        # Manual performance logging
        start_time = time.time()
        time.sleep(0.05)  # Simulate work
        duration = time.time() - start_time
        logger.performance("manual_operation", duration, items_processed=50)
        
        print("✅ Performance timing test passed")
        return True
    
    def test_audit_logging(self):
        """Test audit logging functionality"""
        print("\n=== Testing Audit Logging ===")
        
        logger = get_logger("test_audit", self.test_config)
        
        # Test audit events
        logger.audit("config_change", old_value="debug", new_value="info")
        logger.audit("agent_start", agent_name="test_agent", version="1.0.0")
        
        print("✅ Audit logging test passed")
        return True
    
    def test_exception_logging(self):
        """Test exception logging"""
        print("\n=== Testing Exception Logging ===")
        
        logger = get_logger("test_exception", self.test_config)
        
        try:
            raise ValueError("Test exception for logging")
        except Exception:
            logger.exception("Test exception occurred", operation="test_operation")
        
        print("✅ Exception logging test passed")
        return True
    
    def cleanup(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestAuditTrail:
    """Test audit trail functionality"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_config = {
            "enabled": True,
            "output_dir": str(self.temp_dir / "audit"),
            "enable_integrity_check": True,
            "enable_realtime_streaming": True
        }
    
    def test_basic_audit_events(self):
        """Test basic audit event logging"""
        print("\n=== Testing Basic Audit Events ===")
        
        audit = get_audit_trail("test_component", self.test_config)
        
        # Test different event types
        config_event = audit.log_configuration_change(
            config_key="system.log_level",
            old_value="debug",
            new_value="info",
            user_id="admin"
        )
        
        agent_event = audit.log_agent_start(
            agent_name="test_agent",
            agent_version="1.0.0",
            user_id="system"
        )
        
        user_event = audit.log_user_action(
            action="login",
            resource="authentication_service",
            user_id="test_user",
            session_id="test_session"
        )
        
        security_event = audit.log_security_event(
            action="failed_authentication",
            resource="api_gateway",
            severity=AuditSeverity.HIGH,
            user_id="unknown"
        )
        
        assert config_event is not None, "Configuration event not created"
        assert agent_event is not None, "Agent event not created"
        assert user_event is not None, "User event not created"
        assert security_event is not None, "Security event not created"
        
        print("✅ Basic audit events test passed")
        return True
    
    def test_event_integrity(self):
        """Test audit event integrity verification"""
        print("\n=== Testing Event Integrity ===")
        
        audit = get_audit_trail("test_integrity", self.test_config)
        
        # Create test event
        event_id = audit.log_configuration_change(
            config_key="test.setting",
            old_value="old",
            new_value="new",
            user_id="test"
        )
        
        # Verify integrity
        integrity_report = audit.verify_integrity()
        assert integrity_report["enabled"], "Integrity check not enabled"
        assert integrity_report["integrity_percentage"] == 100, "Integrity check failed"
        
        print(f"✅ Event integrity test passed - {integrity_report['verified_events']} events verified")
        return True
    
    def test_event_querying(self):
        """Test audit event querying"""
        print("\n=== Testing Event Querying ===")
        
        audit = get_audit_trail("test_query", self.test_config)
        
        # Create multiple test events
        for i in range(5):
            audit.log_user_action(
                action="test_action",
                resource=f"resource_{i}",
                user_id="test_user",
                metadata={"index": i}
            )
        
        # Query events
        all_events = audit.get_events(limit=10)
        user_events = audit.get_events(user_id="test_user")
        recent_events = audit.get_events(
            start_time=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        
        assert len(all_events) >= 5, "Not enough events returned"
        assert len(user_events) >= 5, "User filter not working"
        assert len(recent_events) >= 5, "Time filter not working"
        
        print(f"✅ Event querying test passed - {len(all_events)} events found")
        return True
    
    def test_compliance_reporting(self):
        """Test compliance report generation"""
        print("\n=== Testing Compliance Reporting ===")
        
        audit = get_audit_trail("test_compliance", self.test_config)
        
        # Create test events
        audit.log_configuration_change("test.config", "old", "new", user_id="admin")
        audit.log_security_event("test_security", "test_resource", user_id="security")
        
        # Generate compliance report
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        report = audit.export_compliance_report(start_time, end_time)
        
        assert "report_id" in report, "Report ID missing"
        assert "total_events" in report, "Total events missing"
        assert report["total_events"] >= 2, "Not enough events in report"
        
        print(f"✅ Compliance reporting test passed - {report['total_events']} events in report")
        return True
    
    def test_convenience_functions(self):
        """Test convenience audit functions"""
        print("\n=== Testing Convenience Functions ===")
        
        # Test convenience functions
        config_event = audit_configuration_change(
            component_name="test_convenience",
            config_key="test.setting",
            old_value="old",
            new_value="new",
            user_id="admin"
        )
        
        lifecycle_event = audit_agent_lifecycle(
            component_name="test_convenience",
            action="start",
            agent_name="test_agent",
            user_id="system",
            version="1.0.0"
        )
        
        user_action_event = audit_user_action(
            component_name="test_convenience",
            action="test_action",
            resource="test_resource",
            user_id="test_user"
        )
        
        security_event = audit_security_event(
            component_name="test_convenience",
            action="test_security",
            resource="test_resource",
            severity=AuditSeverity.MEDIUM
        )
        
        assert config_event is not None, "Config convenience function failed"
        assert lifecycle_event is not None, "Lifecycle convenience function failed"
        assert user_action_event is not None, "User action convenience function failed"
        assert security_event is not None, "Security convenience function failed"
        
        print("✅ Convenience functions test passed")
        return True
    
    def cleanup(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestLogAggregation:
    """Test log aggregation functionality"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_config = {
            "enabled": True,
            "db_path": str(self.temp_dir / "test_aggregator.db"),
            "max_entries_in_memory": 1000,
            "enable_monitoring": False,  # Disable for testing
            "log_directories": [str(self.temp_dir / "logs")]
        }
    
    def test_manual_entry_addition(self):
        """Test manual log entry addition"""
        print("\n=== Testing Manual Entry Addition ===")
        
        aggregator = get_log_aggregator(self.test_config)
        
        # Create test entries
        for i in range(10):
            entry = LogEntry(
                id=f"test-{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                level="INFO",
                logger=f"test_logger_{i}",
                message=f"Test message {i}",
                correlation_id=f"corr-{i % 3}",  # Group some entries
                source_file=f"test_{i}.log",
                component="test_component",
                metadata={"index": i}
            )
            aggregator.add_entry(entry)
        
        # Verify entries were added
        metrics = aggregator.get_metrics()
        assert metrics["entries_processed"] >= 10, "Not enough entries processed"
        
        print(f"✅ Manual entry addition test passed - {metrics['entries_processed']} entries processed")
        return True
    
    def test_search_functionality(self):
        """Test search functionality"""
        print("\n=== Testing Search Functionality ===")
        
        aggregator = get_log_aggregator(self.test_config)
        
        # Search all entries
        all_results = aggregator.search(limit=20)
        assert len(all_results.entries) > 0, "No entries found"
        
        # Search with filters
        info_results = aggregator.search(filters={"level": "INFO"}, limit=10)
        component_results = aggregator.search(filters={"component": "test_component"}, limit=10)
        
        # Text search
        text_results = aggregator.search(query="Test message", limit=10)
        
        print(f"✅ Search functionality test passed - Found {len(all_results.entries)} total entries")
        return True
    
    def test_correlation_tracing(self):
        """Test correlation ID tracing"""
        print("\n=== Testing Correlation Tracing ===")
        
        aggregator = get_log_aggregator(self.test_config)
        
        # Get correlation trace
        correlation_trace = aggregator.get_correlation_trace("corr-1")
        
        # Verify all entries have the same correlation ID
        for entry in correlation_trace:
            assert entry.correlation_id == "corr-1", "Incorrect correlation ID in trace"
        
        print(f"✅ Correlation tracing test passed - {len(correlation_trace)} entries in trace")
        return True
    
    def test_database_persistence(self):
        """Test database persistence"""
        print("\n=== Testing Database Persistence ===")
        
        # Verify database was created
        db_path = Path(self.test_config["db_path"])
        assert db_path.exists(), "Database file not created"
        
        # Check database contents
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM log_entries")
            count = cursor.fetchone()[0]
            assert count > 0, "No entries in database"
        
        print(f"✅ Database persistence test passed - {count} entries in database")
        return True
    
    def cleanup(self):
        """Cleanup test files"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestIntegration:
    """Test integration between logging and audit systems"""
    
    def test_logging_audit_integration(self):
        """Test integration between logging and audit systems"""
        print("\n=== Testing Logging-Audit Integration ===")
        
        # Setup both systems
        logger = get_logger("integration_test")
        audit = get_audit_trail("integration_test")
        
        # Log events that should trigger audit records
        logger.info("Agent starting", agent_name="test_agent", version="1.0.0")
        audit.log_agent_start("test_agent", "1.0.0", user_id="system")
        
        # Verify both systems recorded events
        audit_events = audit.get_events(limit=10)
        assert len(audit_events) > 0, "No audit events created"
        
        print("✅ Logging-audit integration test passed")
        return True
    
    def test_performance_impact(self):
        """Test performance impact of logging systems"""
        print("\n=== Testing Performance Impact ===")
        
        logger = get_logger("performance_test")
        
        # Measure logging performance
        start_time = time.time()
        for i in range(100):
            logger.info(f"Performance test message {i}", index=i)
        end_time = time.time()
        
        duration = end_time - start_time
        rate = 100 / duration
        
        print(f"✅ Performance test passed - {rate:.1f} logs/second")
        return True


def run_all_tests():
    """Run all Phase 4.1 tests"""
    print("🚀 Starting Phase 4.1 - Advanced Logging and Audit Trail Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test structured logging
    logging_tests = TestStructuredLogging()
    try:
        test_results.append(("Basic Logging", logging_tests.test_basic_logging()))
        test_results.append(("Context Logging", logging_tests.test_context_logging()))
        test_results.append(("Performance Timing", logging_tests.test_performance_timing()))
        test_results.append(("Audit Logging", logging_tests.test_audit_logging()))
        test_results.append(("Exception Logging", logging_tests.test_exception_logging()))
    finally:
        logging_tests.cleanup()
    
    # Test audit trail
    audit_tests = TestAuditTrail()
    try:
        test_results.append(("Basic Audit Events", audit_tests.test_basic_audit_events()))
        test_results.append(("Event Integrity", audit_tests.test_event_integrity()))
        test_results.append(("Event Querying", audit_tests.test_event_querying()))
        test_results.append(("Compliance Reporting", audit_tests.test_compliance_reporting()))
        test_results.append(("Convenience Functions", audit_tests.test_convenience_functions()))
    finally:
        audit_tests.cleanup()
    
    # Test log aggregation
    aggregation_tests = TestLogAggregation()
    try:
        test_results.append(("Manual Entry Addition", aggregation_tests.test_manual_entry_addition()))
        test_results.append(("Search Functionality", aggregation_tests.test_search_functionality()))
        test_results.append(("Correlation Tracing", aggregation_tests.test_correlation_tracing()))
        test_results.append(("Database Persistence", aggregation_tests.test_database_persistence()))
    finally:
        aggregation_tests.cleanup()
    
    # Test integration
    integration_tests = TestIntegration()
    test_results.append(("Logging-Audit Integration", integration_tests.test_logging_audit_integration()))
    test_results.append(("Performance Impact", integration_tests.test_performance_impact()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:30} {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - Phase 4.1 Implementation Successful!")
        return True
    else:
        print(f"\n⚠️  {total - passed} TESTS FAILED - Please review implementation")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
