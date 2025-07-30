"""
Comprehensive Audit Trail Package for AI System Monorepo

This package provides enterprise-grade audit trail capabilities including:
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

from .audit_trail import (
    AuditTrail,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    get_audit_trail
)

# Version information
__version__ = "1.0.0"
__author__ = "AI System Monorepo Team"
__phase__ = "4.1 - Advanced Logging and Audit Trail"

# Package exports
__all__ = [
    "AuditTrail",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "get_audit_trail",
    
    # Convenience functions
    "setup_audit",
    "audit_configuration_change",
    "audit_agent_lifecycle",
    "audit_user_action",
    "audit_security_event"
]


def setup_audit(component_name: str, config: dict = None) -> AuditTrail:
    """
    Setup audit trail for a component
    
    Args:
        component_name: Name of the component
        config: Optional configuration override
        
    Returns:
        Configured AuditTrail instance
    """
    return get_audit_trail(component_name, config)


def audit_configuration_change(
    component_name: str,
    config_key: str,
    old_value: any,
    new_value: any,
    user_id: str = None,
    **metadata
) -> str:
    """
    Convenience function to audit configuration changes
    
    Args:
        component_name: Name of the component
        config_key: Configuration key that changed
        old_value: Previous value
        new_value: New value
        user_id: User who made the change
        **metadata: Additional metadata
        
    Returns:
        Event ID of the audit record
    """
    audit = get_audit_trail(component_name)
    return audit.log_configuration_change(
        config_key=config_key,
        old_value=old_value,
        new_value=new_value,
        user_id=user_id,
        **metadata
    )


def audit_agent_lifecycle(
    component_name: str,
    action: str,
    agent_name: str,
    user_id: str = None,
    **metadata
) -> str:
    """
    Convenience function to audit agent lifecycle events
    
    Args:
        component_name: Name of the component
        action: Lifecycle action (start, stop, restart, etc.)
        agent_name: Name of the agent
        user_id: User who performed the action
        **metadata: Additional metadata
        
    Returns:
        Event ID of the audit record
    """
    audit = get_audit_trail(component_name)
    
    if action == "start":
        return audit.log_agent_start(
            agent_name=agent_name,
            agent_version=metadata.get("version", "unknown"),
            user_id=user_id,
            **metadata
        )
    elif action == "stop":
        return audit.log_agent_stop(
            agent_name=agent_name,
            reason=metadata.get("reason", "unknown"),
            user_id=user_id,
            **metadata
        )
    else:
        return audit.log_event(
            event_type=AuditEventType.AGENT_LIFECYCLE,
            action=action,
            resource=agent_name,
            user_id=user_id,
            **metadata
        )


def audit_user_action(
    component_name: str,
    action: str,
    resource: str,
    user_id: str,
    session_id: str = None,
    **metadata
) -> str:
    """
    Convenience function to audit user actions
    
    Args:
        component_name: Name of the component
        action: Action performed
        resource: Resource affected
        user_id: User who performed the action
        session_id: Session identifier
        **metadata: Additional metadata
        
    Returns:
        Event ID of the audit record
    """
    audit = get_audit_trail(component_name)
    return audit.log_user_action(
        action=action,
        resource=resource,
        user_id=user_id,
        session_id=session_id,
        **metadata
    )


def audit_security_event(
    component_name: str,
    action: str,
    resource: str,
    severity: AuditSeverity = AuditSeverity.HIGH,
    user_id: str = None,
    **metadata
) -> str:
    """
    Convenience function to audit security events
    
    Args:
        component_name: Name of the component
        action: Security action/event
        resource: Resource affected
        severity: Event severity
        user_id: User involved (if applicable)
        **metadata: Additional metadata
        
    Returns:
        Event ID of the audit record
    """
    audit = get_audit_trail(component_name)
    return audit.log_security_event(
        action=action,
        resource=resource,
        severity=severity,
        user_id=user_id,
        **metadata
    )


# Example usage documentation
EXAMPLE_USAGE = '''
# Basic audit setup
from common.audit import setup_audit, audit_configuration_change

audit = setup_audit("my_component")

# Audit configuration change
event_id = audit_configuration_change(
    component_name="my_component",
    config_key="log_level",
    old_value="DEBUG",
    new_value="INFO",
    user_id="admin",
    reason="Performance optimization"
)

# Audit agent lifecycle
from common.audit import audit_agent_lifecycle

audit_agent_lifecycle(
    component_name="agent_manager",
    action="start",
    agent_name="nlu_agent",
    user_id="system",
    version="2.1.0"
)

# Audit user action
from common.audit import audit_user_action

audit_user_action(
    component_name="web_interface",
    action="login",
    resource="authentication_service",
    user_id="user123",
    session_id="sess456",
    ip_address="192.168.1.100"
)

# Audit security event
from common.audit import audit_security_event, AuditSeverity

audit_security_event(
    component_name="security_monitor",
    action="failed_authentication",
    resource="api_gateway",
    severity=AuditSeverity.CRITICAL,
    user_id="attacker",
    ip_address="192.168.1.200",
    attempts=5
)

# Query audit events
audit = get_audit_trail("my_component")
events = audit.get_events(
    event_type=AuditEventType.CONFIGURATION_CHANGE,
    user_id="admin",
    limit=50
)

# Export compliance report
from datetime import datetime, timedelta
end_time = datetime.now()
start_time = end_time - timedelta(days=30)

report = audit.export_compliance_report(start_time, end_time)
'''

# Audit configuration recommendations
AUDIT_CONFIG_RECOMMENDATIONS = {
    "development": {
        "enabled": True,
        "output_dir": "logs/audit_dev",
        "enable_integrity_check": False,
        "enable_realtime_streaming": False,
        "retention_days": 30
    },
    "staging": {
        "enabled": True,
        "output_dir": "logs/audit_staging",
        "enable_integrity_check": True,
        "enable_realtime_streaming": True,
        "retention_days": 90
    },
    "production": {
        "enabled": True,
        "output_dir": "logs/audit_production",
        "enable_integrity_check": True,
        "enable_realtime_streaming": True,
        "retention_days": 365
    }
}
