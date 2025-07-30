"""
Comprehensive Audit Trail System for AI System Monorepo

This module provides enterprise-grade audit trail capabilities with:
- Configuration change tracking
- Agent lifecycle event auditing
- User action logging with accountability
- Compliance-ready audit logs
- Tamper-evident audit records
- Real-time audit event streaming

Author: AI System Monorepo Team
Created: 2025-07-31
Phase: 4.1 - Advanced Logging and Audit Trail
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from threading import Lock
import asyncio

from common.config.unified_config_manager import Config
from common.logging.structured_logger import get_logger, LogLevel


class AuditEventType(Enum):
    """Types of events that can be audited"""
    CONFIGURATION_CHANGE = "configuration_change"
    AGENT_LIFECYCLE = "agent_lifecycle"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    ERROR_EVENT = "error_event"
    PERFORMANCE_EVENT = "performance_event"
    COMPLIANCE_EVENT = "compliance_event"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Immutable audit event record"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: str
    correlation_id: str
    source_component: str
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    resource: str
    old_value: Optional[Any]
    new_value: Optional[Any]
    metadata: Dict[str, Any]
    checksum: Optional[str] = None
    
    def __post_init__(self):
        """Calculate checksum for tamper detection"""
        if self.checksum is None:
            # Create checksum from all fields except checksum itself
            data = {k: v for k, v in asdict(self).items() if k != 'checksum'}
            self.checksum = self._calculate_checksum(data)
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA-256 checksum of event data"""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """Verify event integrity using checksum"""
        data = {k: v for k, v in asdict(self).items() if k != 'checksum'}
        expected_checksum = self._calculate_checksum(data)
        return self.checksum == expected_checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str, indent=2)


class AuditTrail:
    """
    Enterprise-grade audit trail system with tamper-evident logging,
    compliance support, and real-time event streaming.
    """
    
    def __init__(self, component_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize audit trail system
        
        Args:
            component_name: Name of the component generating audit events
            config: Optional configuration override
        """
        self.component_name = component_name
        self.config = config or self._load_default_config()
        self.logger = get_logger(f"audit.{component_name}")
        
        # Thread safety
        self._lock = Lock()
        
        # Event storage
        self.events: List[AuditEvent] = []
        self.max_events = self.config.get("max_events_in_memory", 10000)
        
        # Initialize audit storage
        self._setup_audit_storage()
        
        # Event subscribers
        self._subscribers: List[callable] = []
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load audit configuration from unified config"""
        try:
            config = Config.for_agent(__file__)
            return {
                "enabled": config.bool("audit.enabled", True),
                "output_dir": config.str("audit.output_dir", "logs/audit"),
                "max_file_size": config.int("audit.max_file_size", 50 * 1024 * 1024),  # 50MB
                "backup_count": config.int("audit.backup_count", 50),
                "max_events_in_memory": config.int("audit.max_events_in_memory", 10000),
                "enable_integrity_check": config.bool("audit.enable_integrity_check", True),
                "enable_realtime_streaming": config.bool("audit.enable_realtime_streaming", True),
                "retention_days": config.int("audit.retention_days", 365),
                "compliance_format": config.str("audit.compliance_format", "json"),
                "required_fields": config.list("audit.required_fields", [
                    "event_id", "timestamp", "user_id", "action", "resource"
                ]),
                "sensitive_fields": config.list("audit.sensitive_fields", [
                    "password", "token", "secret", "key"
                ])
            }
        except Exception:
            # Fallback configuration
            return {
                "enabled": True,
                "output_dir": "logs/audit",
                "max_file_size": 50 * 1024 * 1024,
                "backup_count": 50,
                "max_events_in_memory": 10000,
                "enable_integrity_check": True,
                "enable_realtime_streaming": True,
                "retention_days": 365,
                "compliance_format": "json",
                "required_fields": ["event_id", "timestamp", "user_id", "action", "resource"],
                "sensitive_fields": ["password", "token", "secret", "key"]
            }
    
    def _setup_audit_storage(self):
        """Initialize audit log storage"""
        if not self.config["enabled"]:
            return
        
        # Create audit directory
        audit_dir = Path(self.config["output_dir"])
        audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize audit log file
        self.audit_file = audit_dir / f"{self.component_name}_audit.jsonl"
    
    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        resource: str,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        correlation_id: Optional[str] = None,
        **metadata
    ) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of audit event
            action: Action performed
            resource: Resource affected
            severity: Event severity level
            user_id: User who performed the action
            session_id: Session identifier
            old_value: Previous value (for changes)
            new_value: New value (for changes)
            correlation_id: Request correlation ID
            **metadata: Additional metadata
            
        Returns:
            Event ID of the logged event
        """
        if not self.config["enabled"]:
            return None
        
        # Sanitize sensitive data
        old_value = self._sanitize_sensitive_data(old_value)
        new_value = self._sanitize_sensitive_data(new_value)
        metadata = self._sanitize_sensitive_data(metadata)
        
        # Create audit event
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id or str(uuid.uuid4()),
            source_component=self.component_name,
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource=resource,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata
        )
        
        # Store event
        with self._lock:
            self._store_event(event)
            self._manage_memory_limit()
        
        # Log to structured logger
        self.logger.audit(
            action,
            event_id=event.event_id,
            event_type=event_type.value,
            severity=severity.value,
            resource=resource,
            user_id=user_id,
            old_value=old_value,
            new_value=new_value,
            **metadata
        )
        
        # Real-time streaming
        if self.config["enable_realtime_streaming"]:
            self._stream_event(event)
        
        return event.event_id
    
    def _store_event(self, event: AuditEvent):
        """Store audit event to file and memory"""
        # Add to memory
        self.events.append(event)
        
        # Write to file
        if self.audit_file:
            try:
                with open(self.audit_file, 'a', encoding='utf-8') as f:
                    f.write(event.to_json() + '\n')
            except Exception as e:
                self.logger.error(f"Failed to write audit event to file: {e}")
    
    def _manage_memory_limit(self):
        """Manage memory usage by removing old events"""
        if len(self.events) > self.max_events:
            # Remove oldest events
            excess = len(self.events) - self.max_events
            self.events = self.events[excess:]
    
    def _sanitize_sensitive_data(self, data: Any) -> Any:
        """Remove or mask sensitive data from audit logs"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.config.get("sensitive_fields", [])):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_sensitive_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_sensitive_data(item) for item in data]
        else:
            return data
    
    def _stream_event(self, event: AuditEvent):
        """Stream event to real-time subscribers"""
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as e:
                self.logger.error(f"Failed to stream audit event to subscriber: {e}")
    
    def subscribe(self, callback: callable):
        """Subscribe to real-time audit events"""
        self._subscribers.append(callback)
    
    def unsubscribe(self, callback: callable):
        """Unsubscribe from real-time audit events"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    # Convenience methods for common audit events
    def log_configuration_change(
        self,
        config_key: str,
        old_value: Any,
        new_value: Any,
        user_id: Optional[str] = None,
        **metadata
    ) -> str:
        """Log configuration change event"""
        return self.log_event(
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            action="configuration_change",
            resource=config_key,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            old_value=old_value,
            new_value=new_value,
            **metadata
        )
    
    def log_agent_start(
        self,
        agent_name: str,
        agent_version: str,
        user_id: Optional[str] = None,
        **metadata
    ) -> str:
        """Log agent start event"""
        return self.log_event(
            event_type=AuditEventType.AGENT_LIFECYCLE,
            action="agent_start",
            resource=agent_name,
            severity=AuditSeverity.LOW,
            user_id=user_id,
            new_value={"version": agent_version, "status": "started"},
            **metadata
        )
    
    def log_agent_stop(
        self,
        agent_name: str,
        reason: str,
        user_id: Optional[str] = None,
        **metadata
    ) -> str:
        """Log agent stop event"""
        return self.log_event(
            event_type=AuditEventType.AGENT_LIFECYCLE,
            action="agent_stop",
            resource=agent_name,
            severity=AuditSeverity.LOW,
            user_id=user_id,
            new_value={"reason": reason, "status": "stopped"},
            **metadata
        )
    
    def log_user_action(
        self,
        action: str,
        resource: str,
        user_id: str,
        session_id: Optional[str] = None,
        **metadata
    ) -> str:
        """Log user action event"""
        return self.log_event(
            event_type=AuditEventType.USER_ACTION,
            action=action,
            resource=resource,
            severity=AuditSeverity.MEDIUM,
            user_id=user_id,
            session_id=session_id,
            **metadata
        )
    
    def log_security_event(
        self,
        action: str,
        resource: str,
        severity: AuditSeverity = AuditSeverity.HIGH,
        user_id: Optional[str] = None,
        **metadata
    ) -> str:
        """Log security event"""
        return self.log_event(
            event_type=AuditEventType.SECURITY_EVENT,
            action=action,
            resource=resource,
            severity=severity,
            user_id=user_id,
            **metadata
        )
    
    def log_error_event(
        self,
        error_type: str,
        error_message: str,
        resource: str,
        user_id: Optional[str] = None,
        **metadata
    ) -> str:
        """Log error event"""
        return self.log_event(
            event_type=AuditEventType.ERROR_EVENT,
            action="error_occurred",
            resource=resource,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            new_value={
                "error_type": error_type,
                "error_message": error_message
            },
            **metadata
        )
    
    # Query and analysis methods
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """Query audit events with filters"""
        filtered_events = self.events.copy()
        
        # Apply filters
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if resource:
            filtered_events = [e for e in filtered_events if resource in e.resource]
        
        if start_time:
            start_iso = start_time.isoformat()
            filtered_events = [e for e in filtered_events if e.timestamp >= start_iso]
        
        if end_time:
            end_iso = end_time.isoformat()
            filtered_events = [e for e in filtered_events if e.timestamp <= end_iso]
        
        # Apply limit
        if limit:
            filtered_events = filtered_events[-limit:]
        
        return filtered_events
    
    def verify_integrity(self) -> Dict[str, Any]:
        """Verify integrity of all events in memory"""
        if not self.config["enable_integrity_check"]:
            return {"enabled": False}
        
        total_events = len(self.events)
        verified_events = 0
        corrupted_events = []
        
        for event in self.events:
            if event.verify_integrity():
                verified_events += 1
            else:
                corrupted_events.append(event.event_id)
        
        return {
            "enabled": True,
            "total_events": total_events,
            "verified_events": verified_events,
            "corrupted_events": corrupted_events,
            "integrity_percentage": (verified_events / total_events * 100) if total_events > 0 else 100
        }
    
    def export_compliance_report(
        self,
        start_time: datetime,
        end_time: datetime,
        output_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Export compliance report for given time range"""
        events = self.get_events(start_time=start_time, end_time=end_time)
        
        report = {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "component": self.component_name,
            "total_events": len(events),
            "events_by_type": {},
            "events_by_severity": {},
            "events": [event.to_dict() for event in events]
        }
        
        # Aggregate by type and severity
        for event in events:
            event_type = event.event_type.value
            severity = event.severity.value
            
            report["events_by_type"][event_type] = report["events_by_type"].get(event_type, 0) + 1
            report["events_by_severity"][severity] = report["events_by_severity"].get(severity, 0) + 1
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
        
        return report


# Global audit trail instance
_audit_trail_instances: Dict[str, AuditTrail] = {}
_audit_lock = Lock()


def get_audit_trail(component_name: str, config: Optional[Dict[str, Any]] = None) -> AuditTrail:
    """
    Get or create audit trail instance for component
    
    Args:
        component_name: Name of the component
        config: Optional configuration override
        
    Returns:
        AuditTrail instance
    """
    with _audit_lock:
        if component_name not in _audit_trail_instances:
            _audit_trail_instances[component_name] = AuditTrail(component_name, config)
        return _audit_trail_instances[component_name]


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    audit = get_audit_trail("test_component")
    
    # Configuration change
    audit.log_configuration_change(
        config_key="system.log_level",
        old_value="debug",
        new_value="info",
        user_id="admin",
        reason="Performance optimization"
    )
    
    # Agent lifecycle
    audit.log_agent_start(
        agent_name="test_agent",
        agent_version="1.0.0",
        user_id="system"
    )
    
    # User action
    audit.log_user_action(
        action="login",
        resource="system",
        user_id="user123",
        session_id="sess456",
        ip_address="192.168.1.100"
    )
    
    # Security event
    audit.log_security_event(
        action="failed_login",
        resource="authentication_service",
        severity=AuditSeverity.HIGH,
        user_id="unknown",
        attempts=3,
        ip_address="192.168.1.200"
    )
    
    # Query events
    recent_events = audit.get_events(limit=10)
    print(f"Recent events: {len(recent_events)}")
    
    # Verify integrity
    integrity = audit.verify_integrity()
    print(f"Integrity check: {integrity}")
    
    # Export compliance report
    from datetime import timedelta
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=1)
    
    report = audit.export_compliance_report(start_time, end_time)
    print(f"Compliance report: {report['total_events']} events")
