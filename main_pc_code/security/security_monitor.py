#!/usr/bin/env python3
"""
Security Monitor - Real-time Security Threat Detection and Response
Provides comprehensive security monitoring with threat detection and incident response.

Features:
- Real-time threat detection and analysis
- Automated incident response and remediation
- Security information and event management (SIEM)
- Intrusion detection and prevention
- Behavioral anomaly detection
- Security compliance monitoring and reporting
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import json
import logging
import threading
import hashlib
import ipaddress
import subprocess
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import statistics

# Core imports
from common.core.base_agent import BaseAgent

# Security imports

# Event system imports
from events.memory_events import (
    create_memory_pressure_warning
)
from events.event_bus import publish_memory_event

class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """Types of security threats"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    MALWARE = "malware"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    NETWORK_INTRUSION = "network_intrusion"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    POLICY_VIOLATION = "policy_violation"

class IncidentStatus(Enum):
    """Security incident status"""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class ResponseAction(Enum):
    """Automated response actions"""
    ALERT_ONLY = "alert_only"
    BLOCK_IP = "block_ip"
    SUSPEND_USER = "suspend_user"
    ISOLATE_SYSTEM = "isolate_system"
    BACKUP_DATA = "backup_data"
    NOTIFY_ADMIN = "notify_admin"
    ESCALATE = "escalate"

@dataclass
class SecurityThreat:
    """Security threat detection"""
    threat_id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    title: str
    description: str
    source_ip: Optional[str] = None
    target_resource: Optional[str] = None
    user_id: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.now)
    evidence: Dict[str, Any] = field(default_factory=dict)
    indicators: List[str] = field(default_factory=list)
    confidence_score: float = 0.5  # 0-1 scale
    
    @property
    def age_minutes(self) -> float:
        return (datetime.now() - self.detected_at).total_seconds() / 60

@dataclass
class SecurityIncident:
    """Security incident record"""
    incident_id: str
    threat_ids: List[str]
    incident_type: ThreatType
    severity: ThreatLevel
    status: IncidentStatus
    title: str
    description: str
    detected_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    response_actions: List[ResponseAction] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class SecurityMetrics:
    """Security monitoring metrics"""
    total_threats: int = 0
    threats_by_level: Dict[str, int] = field(default_factory=dict)
    threats_by_type: Dict[str, int] = field(default_factory=dict)
    incidents_created: int = 0
    incidents_resolved: int = 0
    mean_detection_time: float = 0.0
    mean_response_time: float = 0.0
    false_positive_rate: float = 0.0

@dataclass
class MonitoringRule:
    """Security monitoring rule"""
    rule_id: str
    name: str
    description: str
    threat_type: ThreatType
    conditions: Dict[str, Any]
    threshold: float
    window_minutes: int
    enabled: bool = True
    response_actions: List[ResponseAction] = field(default_factory=list)

class SecurityMonitor(BaseAgent):
    """
    Comprehensive security monitoring and threat detection system.
    
    Provides real-time security monitoring, threat detection,
    incident management, and automated response capabilities.
    """
    
    def __init__(self, 
                 monitoring_interval_seconds: int = 30,
                 enable_automated_response: bool = True,
                 **kwargs):
        super().__init__(name="SecurityMonitor", **kwargs)
        
        # Configuration
        self.monitoring_interval = monitoring_interval_seconds
        self.enable_automated_response = enable_automated_response
        
        # Threat detection
        self.threats: Dict[str, SecurityThreat] = {}
        self.incidents: Dict[str, SecurityIncident] = {}
        self.monitoring_rules = self._initialize_monitoring_rules()
        
        # Security metrics and analytics
        self.security_metrics = SecurityMetrics()
        self.threat_history: deque = deque(maxlen=10000)
        self.behavioral_baselines: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Network monitoring
        self.network_connections: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        
        # System monitoring
        self.system_processes: Dict[str, Dict[str, Any]] = {}
        self.file_integrity_hashes: Dict[str, str] = {}
        self.critical_files = self._get_critical_files()
        
        # Incident response
        self.response_playbooks = self._initialize_response_playbooks()
        self.notification_channels = []
        
        # Initialize monitoring
        self._start_security_monitoring()
        
        self.logger.info("Security Monitor initialized")
    
    def _initialize_monitoring_rules(self) -> List[MonitoringRule]:
        """Initialize security monitoring rules"""
        return [
            MonitoringRule(
                rule_id="brute_force_login",
                name="Brute Force Login Detection",
                description="Detect multiple failed login attempts",
                threat_type=ThreatType.BRUTE_FORCE,
                conditions={
                    "failed_logins_threshold": 5,
                    "time_window_minutes": 5,
                    "per_ip": True
                },
                threshold=5.0,
                window_minutes=5,
                response_actions=[ResponseAction.BLOCK_IP, ResponseAction.NOTIFY_ADMIN]
            ),
            MonitoringRule(
                rule_id="sql_injection_pattern",
                name="SQL Injection Detection",
                description="Detect SQL injection attempts in requests",
                threat_type=ThreatType.SQL_INJECTION,
                conditions={
                    "patterns": [
                        r"(?i)(union.*select|select.*from|insert.*into|delete.*from)",
                        r"(?i)(\';|\"|\-\-|\/\*|\*\/)",
                        r"(?i)(exec|execute|xp_cmdshell)"
                    ]
                },
                threshold=1.0,
                window_minutes=1,
                response_actions=[ResponseAction.BLOCK_IP, ResponseAction.ALERT_ONLY]
            ),
            MonitoringRule(
                rule_id="unusual_data_access",
                name="Unusual Data Access Pattern",
                description="Detect anomalous data access patterns",
                threat_type=ThreatType.DATA_EXFILTRATION,
                conditions={
                    "data_volume_threshold_mb": 100,
                    "access_frequency_multiplier": 5.0
                },
                threshold=3.0,
                window_minutes=60,
                response_actions=[ResponseAction.ALERT_ONLY, ResponseAction.NOTIFY_ADMIN]
            ),
            MonitoringRule(
                rule_id="privilege_escalation",
                name="Privilege Escalation Detection",
                description="Detect unauthorized privilege escalation attempts",
                threat_type=ThreatType.PRIVILEGE_ESCALATION,
                conditions={
                    "sudo_attempts": 3,
                    "admin_access_attempts": 2
                },
                threshold=2.0,
                window_minutes=15,
                response_actions=[ResponseAction.SUSPEND_USER, ResponseAction.ESCALATE]
            ),
            MonitoringRule(
                rule_id="network_intrusion",
                name="Network Intrusion Detection",
                description="Detect suspicious network activity",
                threat_type=ThreatType.NETWORK_INTRUSION,
                conditions={
                    "port_scan_threshold": 20,
                    "connection_frequency": 100
                },
                threshold=4.0,
                window_minutes=10,
                response_actions=[ResponseAction.BLOCK_IP, ResponseAction.ISOLATE_SYSTEM]
            )
        ]
    
    def _initialize_response_playbooks(self) -> Dict[ThreatType, Dict[str, Any]]:
        """Initialize automated response playbooks"""
        return {
            ThreatType.BRUTE_FORCE: {
                "immediate_actions": [
                    {"action": "block_source_ip", "duration_minutes": 60},
                    {"action": "notify_security_team", "priority": "medium"}
                ],
                "escalation_threshold": 10,
                "escalation_actions": [
                    {"action": "permanent_ip_block", "duration_hours": 24},
                    {"action": "notify_incident_response", "priority": "high"}
                ]
            },
            ThreatType.SQL_INJECTION: {
                "immediate_actions": [
                    {"action": "block_source_ip", "duration_minutes": 120},
                    {"action": "log_detailed_request", "retention_days": 30},
                    {"action": "notify_security_team", "priority": "high"}
                ],
                "escalation_threshold": 3,
                "escalation_actions": [
                    {"action": "isolate_database", "backup_first": True},
                    {"action": "escalate_to_ciso", "priority": "critical"}
                ]
            },
            ThreatType.DATA_EXFILTRATION: {
                "immediate_actions": [
                    {"action": "suspend_user_session", "notify_user": False},
                    {"action": "backup_audit_logs", "priority": "immediate"},
                    {"action": "notify_data_protection_officer", "priority": "critical"}
                ],
                "escalation_threshold": 1,
                "escalation_actions": [
                    {"action": "isolate_affected_systems", "scope": "user_access"},
                    {"action": "initiate_forensic_capture", "preserve_evidence": True}
                ]
            }
        }
    
    def _get_critical_files(self) -> List[str]:
        """Get list of critical files to monitor"""
        return [
            "/etc/passwd", "/etc/shadow", "/etc/hosts",
            "main_pc_code/security/auth_hardening.py",
            "main_pc_code/security/vulnerability_scanner.py",
            "startup_config.yaml", ".env", "config.json"
        ]
    
    def _start_security_monitoring(self) -> None:
        """Start security monitoring threads"""
        # Main threat detection thread
        detection_thread = threading.Thread(target=self._threat_detection_loop, daemon=True)
        detection_thread.start()
        
        # Network monitoring thread
        network_thread = threading.Thread(target=self._network_monitoring_loop, daemon=True)
        network_thread.start()
        
        # System integrity monitoring thread
        integrity_thread = threading.Thread(target=self._system_integrity_loop, daemon=True)
        integrity_thread.start()
        
        # Behavioral analysis thread
        behavior_thread = threading.Thread(target=self._behavioral_analysis_loop, daemon=True)
        behavior_thread.start()
        
        # Incident management thread
        incident_thread = threading.Thread(target=self._incident_management_loop, daemon=True)
        incident_thread.start()
    
    def _threat_detection_loop(self) -> None:
        """Main threat detection loop"""
        while self.running:
            try:
                self._analyze_security_events()
                self._evaluate_monitoring_rules()
                self._update_security_metrics()
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Threat detection error: {e}")
                time.sleep(60)
    
    def _network_monitoring_loop(self) -> None:
        """Monitor network activity for threats"""
        while self.running:
            try:
                self._monitor_network_connections()
                self._detect_port_scanning()
                self._analyze_traffic_patterns()
                
                time.sleep(60)  # Network monitoring every minute
                
            except Exception as e:
                self.logger.error(f"Network monitoring error: {e}")
                time.sleep(120)
    
    def _system_integrity_loop(self) -> None:
        """Monitor system integrity"""
        while self.running:
            try:
                self._check_file_integrity()
                self._monitor_system_processes()
                self._check_system_configurations()
                
                time.sleep(300)  # System integrity check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"System integrity monitoring error: {e}")
                time.sleep(600)
    
    def _behavioral_analysis_loop(self) -> None:
        """Analyze user and system behavior for anomalies"""
        while self.running:
            try:
                self._analyze_user_behavior()
                self._detect_anomalous_patterns()
                self._update_behavioral_baselines()
                
                time.sleep(600)  # Behavioral analysis every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Behavioral analysis error: {e}")
                time.sleep(900)
    
    def _incident_management_loop(self) -> None:
        """Manage security incidents and responses"""
        while self.running:
            try:
                self._process_new_threats()
                self._update_incident_status()
                self._execute_automated_responses()
                
                time.sleep(30)  # Incident management every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Incident management error: {e}")
                time.sleep(60)
    
    def _analyze_security_events(self) -> None:
        """Analyze security events for threats"""
        # This would integrate with auth system and other security components
        # For now, simulate analysis
    
    def _evaluate_monitoring_rules(self) -> None:
        """Evaluate monitoring rules against current data"""
        for rule in self.monitoring_rules:
            if not rule.enabled:
                continue
            
            try:
                threat_detected = self._evaluate_rule(rule)
                if threat_detected:
                    self._create_threat_from_rule(rule, threat_detected)
                    
            except Exception as e:
                self.logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
    
    def _evaluate_rule(self, rule: MonitoringRule) -> Optional[Dict[str, Any]]:
        """Evaluate a specific monitoring rule"""
        if rule.threat_type == ThreatType.BRUTE_FORCE:
            return self._evaluate_brute_force_rule(rule)
        elif rule.threat_type == ThreatType.SQL_INJECTION:
            return self._evaluate_sql_injection_rule(rule)
        elif rule.threat_type == ThreatType.DATA_EXFILTRATION:
            return self._evaluate_data_exfiltration_rule(rule)
        elif rule.threat_type == ThreatType.PRIVILEGE_ESCALATION:
            return self._evaluate_privilege_escalation_rule(rule)
        elif rule.threat_type == ThreatType.NETWORK_INTRUSION:
            return self._evaluate_network_intrusion_rule(rule)
        
        return None
    
    def _evaluate_brute_force_rule(self, rule: MonitoringRule) -> Optional[Dict[str, Any]]:
        """Evaluate brute force detection rule"""
        # This would integrate with authentication system
        # For now, simulate detection based on network patterns
        
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=rule.window_minutes)
        
        # Check for suspicious connection patterns
        for ip, connections in self.network_connections.items():
            recent_connections = [
                conn for conn in connections 
                if conn > window_start
            ]
            
            if len(recent_connections) > rule.threshold:
                return {
                    "source_ip": ip,
                    "connection_count": len(recent_connections),
                    "time_window": rule.window_minutes,
                    "evidence": {
                        "connection_times": [conn.isoformat() for conn in recent_connections[-10:]]
                    }
                }
        
        return None
    
    def _evaluate_sql_injection_rule(self, rule: MonitoringRule) -> Optional[Dict[str, Any]]:
        """Evaluate SQL injection detection rule"""
        # This would analyze web requests/database queries
        # For now, simulate based on suspicious patterns
        
        patterns = rule.conditions.get("patterns", [])
        
        # In a real implementation, this would analyze actual web requests
        # For simulation, we'll check if any suspicious patterns were detected
        for pattern in patterns:
            if self.suspicious_patterns.get(f"sql_pattern_{pattern}", 0) > 0:
                return {
                    "pattern_matched": pattern,
                    "detection_count": self.suspicious_patterns[f"sql_pattern_{pattern}"],
                    "evidence": {
                        "pattern_type": "sql_injection_attempt",
                        "detection_method": "regex_pattern_matching"
                    }
                }
        
        return None
    
    def _evaluate_data_exfiltration_rule(self, rule: MonitoringRule) -> Optional[Dict[str, Any]]:
        """Evaluate data exfiltration detection rule"""
        # This would analyze data access patterns and volumes
        # For simulation, check for unusual data access
        
        threshold_mb = rule.conditions.get("data_volume_threshold_mb", 100)
        
        # Simulate data access monitoring
        # In practice, this would integrate with database monitoring
        if self.suspicious_patterns.get("large_data_access", 0) > 0:
            return {
                "data_volume_mb": threshold_mb * 2,  # Simulated large access
                "access_pattern": "bulk_download",
                "evidence": {
                    "access_frequency": "unusual",
                    "data_types": ["user_data", "sensitive_information"]
                }
            }
        
        return None
    
    def _evaluate_privilege_escalation_rule(self, rule: MonitoringRule) -> Optional[Dict[str, Any]]:
        """Evaluate privilege escalation detection rule"""
        # This would monitor system calls and privilege changes
        # For simulation, check for suspicious administrative activities
        
        if self.suspicious_patterns.get("admin_attempts", 0) >= rule.threshold:
            return {
                "escalation_attempts": self.suspicious_patterns["admin_attempts"],
                "privilege_level": "administrative",
                "evidence": {
                    "access_method": "unauthorized_elevation",
                    "target_resources": ["system_configuration", "user_accounts"]
                }
            }
        
        return None
    
    def _evaluate_network_intrusion_rule(self, rule: MonitoringRule) -> Optional[Dict[str, Any]]:
        """Evaluate network intrusion detection rule"""
        # Check for port scanning and unusual network activity
        port_scan_threshold = rule.conditions.get("port_scan_threshold", 20)
        
        if self.suspicious_patterns.get("port_scans", 0) >= port_scan_threshold:
            return {
                "scan_attempts": self.suspicious_patterns["port_scans"],
                "scan_type": "port_enumeration",
                "evidence": {
                    "scan_pattern": "sequential_port_scan",
                    "target_ports": ["22", "80", "443", "3389"]
                }
            }
        
        return None
    
    def _create_threat_from_rule(self, rule: MonitoringRule, detection_data: Dict[str, Any]) -> None:
        """Create threat from rule detection"""
        threat_id = self._generate_threat_id()
        
        # Determine threat level based on rule and detection data
        threat_level = self._calculate_threat_level(rule, detection_data)
        
        threat = SecurityThreat(
            threat_id=threat_id,
            threat_type=rule.threat_type,
            threat_level=threat_level,
            title=f"{rule.name} - {rule.threat_type.value}",
            description=rule.description,
            source_ip=detection_data.get("source_ip"),
            evidence=detection_data.get("evidence", {}),
            indicators=[f"Rule: {rule.rule_id}"],
            confidence_score=self._calculate_confidence_score(rule, detection_data)
        )
        
        self.threats[threat_id] = threat
        self.threat_history.append(threat)
        
        self.logger.warning(f"Security threat detected: {threat.title} (Level: {threat_level.value})")
        
        # Execute automated response if enabled
        if self.enable_automated_response:
            self._execute_response_actions(threat, rule.response_actions)
        
        # Publish threat detection event
        threat_event = create_memory_pressure_warning(
            memory_utilization_percentage=80.0,  # High utilization for threat
            fragmentation_percentage=0.0,
            optimization_suggestions=[f"Security threat detected: {threat.title}"],
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(threat_event)
    
    def _calculate_threat_level(self, rule: MonitoringRule, detection_data: Dict[str, Any]) -> ThreatLevel:
        """Calculate threat level based on rule and detection data"""
        base_severity = {
            ThreatType.BRUTE_FORCE: ThreatLevel.MEDIUM,
            ThreatType.SQL_INJECTION: ThreatLevel.HIGH,
            ThreatType.DATA_EXFILTRATION: ThreatLevel.CRITICAL,
            ThreatType.PRIVILEGE_ESCALATION: ThreatLevel.HIGH,
            ThreatType.NETWORK_INTRUSION: ThreatLevel.MEDIUM
        }
        
        severity = base_severity.get(rule.threat_type, ThreatLevel.MEDIUM)
        
        # Escalate based on detection strength
        detection_strength = detection_data.get("connection_count", detection_data.get("detection_count", 1))
        
        if detection_strength > rule.threshold * 3:
            if severity == ThreatLevel.LOW:
                severity = ThreatLevel.MEDIUM
            elif severity == ThreatLevel.MEDIUM:
                severity = ThreatLevel.HIGH
            elif severity == ThreatLevel.HIGH:
                severity = ThreatLevel.CRITICAL
        
        return severity
    
    def _calculate_confidence_score(self, rule: MonitoringRule, detection_data: Dict[str, Any]) -> float:
        """Calculate confidence score for threat detection"""
        base_confidence = 0.7
        
        # Increase confidence based on evidence quality
        evidence = detection_data.get("evidence", {})
        
        if "pattern_type" in evidence:
            base_confidence += 0.1
        
        if "detection_method" in evidence:
            base_confidence += 0.1
        
        # Adjust based on detection strength vs threshold
        detection_value = detection_data.get("connection_count", detection_data.get("detection_count", 1))
        
        if detection_value > rule.threshold * 2:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _execute_response_actions(self, threat: SecurityThreat, actions: List[ResponseAction]) -> None:
        """Execute automated response actions"""
        for action in actions:
            try:
                if action == ResponseAction.BLOCK_IP and threat.source_ip:
                    self._block_ip_address(threat.source_ip)
                elif action == ResponseAction.SUSPEND_USER and threat.user_id:
                    self._suspend_user(threat.user_id)
                elif action == ResponseAction.NOTIFY_ADMIN:
                    self._notify_administrators(threat)
                elif action == ResponseAction.ESCALATE:
                    self._escalate_threat(threat)
                elif action == ResponseAction.ALERT_ONLY:
                    self._log_alert(threat)
                
                self.logger.info(f"Executed response action: {action.value} for threat {threat.threat_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to execute response action {action.value}: {e}")
    
    def _block_ip_address(self, ip_address: str) -> None:
        """Block IP address"""
        self.blocked_ips.add(ip_address)
        self.logger.warning(f"Blocked IP address: {ip_address}")
        
        # In production, this would update firewall rules
        # For now, just track in memory
    
    def _suspend_user(self, user_id: str) -> None:
        """Suspend user account"""
        self.logger.warning(f"User account suspended: {user_id}")
        
        # In production, this would integrate with authentication system
        # For now, just log the action
    
    def _notify_administrators(self, threat: SecurityThreat) -> None:
        """Notify system administrators"""
        notification = {
            "type": "security_threat",
            "threat_id": threat.threat_id,
            "threat_type": threat.threat_type.value,
            "threat_level": threat.threat_level.value,
            "title": threat.title,
            "description": threat.description,
            "detected_at": threat.detected_at.isoformat()
        }
        
        # In production, this would send emails/SMS/Slack notifications
        self.logger.critical(f"SECURITY ALERT: {threat.title}")
    
    def _escalate_threat(self, threat: SecurityThreat) -> None:
        """Escalate threat to incident"""
        incident_id = self._generate_incident_id()
        
        incident = SecurityIncident(
            incident_id=incident_id,
            threat_ids=[threat.threat_id],
            incident_type=threat.threat_type,
            severity=threat.threat_level,
            status=IncidentStatus.DETECTED,
            title=f"Security Incident: {threat.title}",
            description=threat.description,
            detected_at=threat.detected_at,
            updated_at=datetime.now(),
            timeline=[{
                "timestamp": datetime.now().isoformat(),
                "action": "incident_created",
                "details": f"Escalated from threat {threat.threat_id}"
            }]
        )
        
        self.incidents[incident_id] = incident
        self.logger.critical(f"Security incident created: {incident_id}")
    
    def _log_alert(self, threat: SecurityThreat) -> None:
        """Log security alert"""
        self.logger.warning(f"Security Alert: {threat.title} - {threat.description}")
    
    def _monitor_network_connections(self) -> None:
        """Monitor network connections"""
        try:
            # Use netstat to get current connections
            result = subprocess.run(
                ['netstat', '-an'], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                self._analyze_netstat_output(result.stdout)
                
        except subprocess.TimeoutExpired:
            self.logger.warning("Network monitoring timeout")
        except FileNotFoundError:
            # netstat not available, use alternative method
            self._simulate_network_monitoring()
        except Exception as e:
            self.logger.error(f"Network monitoring error: {e}")
    
    def _analyze_netstat_output(self, output: str) -> None:
        """Analyze netstat output for suspicious activity"""
        lines = output.strip().split('\n')
        
        for line in lines:
            parts = line.split()
            if len(parts) >= 4 and parts[0] in ['tcp', 'tcp4', 'tcp6']:
                try:
                    # Extract remote IP
                    remote_addr = parts[4] if len(parts) > 4 else parts[3]
                    if ':' in remote_addr:
                        ip_part = remote_addr.rsplit(':', 1)[0]
                        # Remove IPv6 brackets if present
                        ip_part = ip_part.strip('[]')
                        
                        # Skip local addresses
                        if not self._is_local_address(ip_part):
                            self.network_connections[ip_part].append(datetime.now())
                            
                except Exception:
                    continue
    
    def _simulate_network_monitoring(self) -> None:
        """Simulate network monitoring when tools aren't available"""
        # Add some simulated network activity
        test_ips = ["192.168.1.100", "10.0.0.50", "172.16.0.25"]
        
        for ip in test_ips:
            if len(self.network_connections[ip]) < 10:  # Don't spam
                self.network_connections[ip].append(datetime.now())
    
    def _is_local_address(self, ip_str: str) -> bool:
        """Check if IP address is local/private"""
        try:
            ip = ipaddress.ip_address(ip_str)
            return (ip.is_private or ip.is_loopback or 
                   ip_str in ['0.0.0.0', '127.0.0.1', '::1'])
        except ValueError:
            return True  # If we can't parse it, assume it's local
    
    def _detect_port_scanning(self) -> None:
        """Detect port scanning attempts"""
        # This would analyze connection patterns for port scanning
        # For simulation, increment suspicious patterns
        
        for ip, connections in self.network_connections.items():
            recent_connections = [
                conn for conn in connections
                if (datetime.now() - conn).total_seconds() < 300  # Last 5 minutes
            ]
            
            if len(recent_connections) > 20:  # Many connections in short time
                self.suspicious_patterns["port_scans"] += 1
                self.logger.warning(f"Potential port scan detected from {ip}")
    
    def _analyze_traffic_patterns(self) -> None:
        """Analyze network traffic patterns"""
        # This would perform deeper traffic analysis
        # For now, clean up old connection data
        
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for ip in list(self.network_connections.keys()):
            self.network_connections[ip] = [
                conn for conn in self.network_connections[ip]
                if conn > cutoff_time
            ]
            
            if not self.network_connections[ip]:
                del self.network_connections[ip]
    
    def _check_file_integrity(self) -> None:
        """Check integrity of critical files"""
        for file_path in self.critical_files:
            try:
                full_path = Path(PROJECT_ROOT) / file_path
                if full_path.exists():
                    # Calculate file hash
                    with open(full_path, 'rb') as f:
                        file_content = f.read()
                        file_hash = hashlib.sha256(file_content).hexdigest()
                    
                    # Check against stored hash
                    stored_hash = self.file_integrity_hashes.get(str(full_path))
                    
                    if stored_hash is None:
                        # First time seeing this file
                        self.file_integrity_hashes[str(full_path)] = file_hash
                    elif stored_hash != file_hash:
                        # File has been modified
                        self._detect_file_modification(str(full_path), stored_hash, file_hash)
                        self.file_integrity_hashes[str(full_path)] = file_hash
                        
            except Exception as e:
                self.logger.debug(f"Could not check integrity of {file_path}: {e}")
    
    def _detect_file_modification(self, file_path: str, old_hash: str, new_hash: str) -> None:
        """Detect unauthorized file modification"""
        threat_id = self._generate_threat_id()
        
        threat = SecurityThreat(
            threat_id=threat_id,
            threat_type=ThreatType.POLICY_VIOLATION,
            threat_level=ThreatLevel.MEDIUM,
            title="Critical File Modified",
            description=f"Critical file {file_path} has been modified",
            target_resource=file_path,
            evidence={
                "old_hash": old_hash,
                "new_hash": new_hash,
                "modification_detected": datetime.now().isoformat()
            },
            indicators=["file_integrity_violation"],
            confidence_score=0.9
        )
        
        self.threats[threat_id] = threat
        self.logger.warning(f"Critical file modified: {file_path}")
    
    def _monitor_system_processes(self) -> None:
        """Monitor running system processes"""
        try:
            # Use ps to get process information
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                self._analyze_process_output(result.stdout)
                
        except subprocess.TimeoutExpired:
            self.logger.warning("Process monitoring timeout")
        except FileNotFoundError:
            self.logger.debug("ps command not available")
        except Exception as e:
            self.logger.error(f"Process monitoring error: {e}")
    
    def _analyze_process_output(self, output: str) -> None:
        """Analyze process output for suspicious activity"""
        lines = output.strip().split('\n')[1:]  # Skip header
        
        suspicious_processes = [
            'nc', 'netcat', 'nmap', 'metasploit', 'sqlmap',
            'john', 'hashcat', 'aircrack', 'wireshark'
        ]
        
        for line in lines:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                command = parts[10].lower()
                
                for suspicious in suspicious_processes:
                    if suspicious in command:
                        self.logger.warning(f"Suspicious process detected: {command}")
                        self.suspicious_patterns[f"suspicious_process_{suspicious}"] += 1
    
    def _check_system_configurations(self) -> None:
        """Check system configurations for security issues"""
        # Check for common security misconfigurations
        config_checks = [
            self._check_ssh_configuration,
            self._check_firewall_status,
            self._check_user_permissions
        ]
        
        for check in config_checks:
            try:
                check()
            except Exception as e:
                self.logger.debug(f"Configuration check failed: {e}")
    
    def _check_ssh_configuration(self) -> None:
        """Check SSH configuration for security issues"""
        ssh_config_path = "/etc/ssh/sshd_config"
        
        try:
            if os.path.exists(ssh_config_path):
                with open(ssh_config_path, 'r') as f:
                    config_content = f.read()
                
                # Check for insecure configurations
                if "PermitRootLogin yes" in config_content:
                    self.logger.warning("SSH allows root login - security risk")
                    self.suspicious_patterns["insecure_ssh_config"] += 1
                    
        except Exception:
            pass  # SSH config might not be accessible
    
    def _check_firewall_status(self) -> None:
        """Check firewall status"""
        try:
            # Check iptables
            result = subprocess.run(['iptables', '-L'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "Chain INPUT (policy ACCEPT)" in result.stdout:
                self.logger.warning("Firewall appears to be in permissive mode")
        except Exception:
            pass
    
    def _check_user_permissions(self) -> None:
        """Check for unusual user permissions"""
        # This would check for users with unusual privileges
        # For now, just a placeholder
    
    def _analyze_user_behavior(self) -> None:
        """Analyze user behavior patterns"""
        # This would analyze user access patterns, login times, etc.
        # For simulation, just update behavioral baselines
        
        current_hour = datetime.now().hour
        if "login_hours" not in self.behavioral_baselines["system"]:
            self.behavioral_baselines["system"]["login_hours"] = []
        
        self.behavioral_baselines["system"]["login_hours"].append(current_hour)
        
        # Keep only recent data
        if len(self.behavioral_baselines["system"]["login_hours"]) > 168:  # One week
            self.behavioral_baselines["system"]["login_hours"] = \
                self.behavioral_baselines["system"]["login_hours"][-168:]
    
    def _detect_anomalous_patterns(self) -> None:
        """Detect anomalous behavior patterns"""
        # This would use machine learning or statistical analysis
        # For now, check for simple anomalies
        
        if "login_hours" in self.behavioral_baselines["system"]:
            hours = self.behavioral_baselines["system"]["login_hours"]
            
            if len(hours) > 20:
                # Check for unusual login times
                current_hour = datetime.now().hour
                hour_frequency = hours.count(current_hour) / len(hours)
                
                # If this hour is very rare (< 5% of logins), flag as anomalous
                if hour_frequency < 0.05 and len(hours) > 50:
                    self.suspicious_patterns["unusual_login_time"] += 1
    
    def _update_behavioral_baselines(self) -> None:
        """Update behavioral baselines"""
        # Clean up old baseline data
        for entity, baselines in self.behavioral_baselines.items():
            for metric, values in baselines.items():
                if isinstance(values, list) and len(values) > 1000:
                    baselines[metric] = values[-1000:]  # Keep last 1000 values
    
    def _process_new_threats(self) -> None:
        """Process newly detected threats"""
        # Check for threats that need incident creation
        unprocessed_threats = [
            threat for threat in self.threats.values()
            if threat.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL] and
            threat.age_minutes < 60 and  # Within last hour
            not any(threat.threat_id in incident.threat_ids for incident in self.incidents.values())
        ]
        
        for threat in unprocessed_threats:
            if threat.threat_level == ThreatLevel.CRITICAL:
                self._escalate_threat(threat)
    
    def _update_incident_status(self) -> None:
        """Update status of security incidents"""
        for incident in self.incidents.values():
            if incident.status == IncidentStatus.DETECTED:
                # Auto-escalate critical incidents
                if incident.severity == ThreatLevel.CRITICAL:
                    incident.status = IncidentStatus.INVESTIGATING
                    incident.updated_at = datetime.now()
                    incident.timeline.append({
                        "timestamp": datetime.now().isoformat(),
                        "action": "auto_escalated",
                        "details": "Critical severity incident auto-escalated"
                    })
    
    def _execute_automated_responses(self) -> None:
        """Execute automated response actions"""
        # Check for incidents that need automated response
        for incident in self.incidents.values():
            if (incident.status == IncidentStatus.INVESTIGATING and
                incident.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]):
                
                playbook = self.response_playbooks.get(incident.incident_type)
                if playbook:
                    self._execute_playbook(incident, playbook)
    
    def _execute_playbook(self, incident: SecurityIncident, playbook: Dict[str, Any]) -> None:
        """Execute incident response playbook"""
        immediate_actions = playbook.get("immediate_actions", [])
        
        for action_config in immediate_actions:
            action_type = action_config.get("action")
            
            if action_type == "block_source_ip":
                # Find source IP from related threats
                for threat_id in incident.threat_ids:
                    threat = self.threats.get(threat_id)
                    if threat and threat.source_ip:
                        self._block_ip_address(threat.source_ip)
            
            elif action_type == "notify_security_team":
                self._notify_administrators_for_incident(incident)
            
            # Log the action
            incident.timeline.append({
                "timestamp": datetime.now().isoformat(),
                "action": action_type,
                "details": f"Automated response executed: {action_type}"
            })
    
    def _notify_administrators_for_incident(self, incident: SecurityIncident) -> None:
        """Notify administrators about security incident"""
        self.logger.critical(f"SECURITY INCIDENT: {incident.title} (ID: {incident.incident_id})")
    
    def _update_security_metrics(self) -> None:
        """Update security monitoring metrics"""
        self.security_metrics.total_threats = len(self.threats)
        
        # Count by threat level
        threat_level_counts = defaultdict(int)
        threat_type_counts = defaultdict(int)
        
        for threat in self.threats.values():
            threat_level_counts[threat.threat_level.value] += 1
            threat_type_counts[threat.threat_type.value] += 1
        
        self.security_metrics.threats_by_level = dict(threat_level_counts)
        self.security_metrics.threats_by_type = dict(threat_type_counts)
        
        # Update incident metrics
        self.security_metrics.incidents_created = len(self.incidents)
        self.security_metrics.incidents_resolved = len([
            i for i in self.incidents.values() 
            if i.status == IncidentStatus.RESOLVED
        ])
        
        # Calculate detection and response times
        if self.threat_history:
            detection_times = [
                threat.age_minutes for threat in self.threat_history
                if threat.age_minutes < 1440  # Within 24 hours
            ]
            
            if detection_times:
                self.security_metrics.mean_detection_time = statistics.mean(detection_times)
    
    def _generate_threat_id(self) -> str:
        """Generate unique threat ID"""
        import secrets
        return f"threat_{secrets.token_urlsafe(12)}"
    
    def _generate_incident_id(self) -> str:
        """Generate unique incident ID"""
        import secrets
        return f"incident_{secrets.token_urlsafe(12)}"
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security monitoring status"""
        active_threats = [
            threat for threat in self.threats.values()
            if threat.age_minutes < 60  # Threats from last hour
        ]
        
        recent_incidents = sorted(
            self.incidents.values(),
            key=lambda x: x.detected_at,
            reverse=True
        )[:10]
        
        return {
            'security_overview': {
                'monitoring_status': 'active' if self.running else 'stopped',
                'total_threats': len(self.threats),
                'active_threats': len(active_threats),
                'total_incidents': len(self.incidents),
                'blocked_ips': len(self.blocked_ips),
                'monitoring_rules': len([r for r in self.monitoring_rules if r.enabled])
            },
            'threat_metrics': asdict(self.security_metrics),
            'recent_threats': [
                {
                    'threat_id': threat.threat_id,
                    'threat_type': threat.threat_type.value,
                    'threat_level': threat.threat_level.value,
                    'title': threat.title,
                    'detected_at': threat.detected_at.isoformat(),
                    'source_ip': threat.source_ip,
                    'confidence_score': threat.confidence_score
                }
                for threat in active_threats
            ],
            'recent_incidents': [
                {
                    'incident_id': incident.incident_id,
                    'incident_type': incident.incident_type.value,
                    'severity': incident.severity.value,
                    'status': incident.status.value,
                    'title': incident.title,
                    'detected_at': incident.detected_at.isoformat(),
                    'threat_count': len(incident.threat_ids)
                }
                for incident in recent_incidents
            ],
            'network_monitoring': {
                'monitored_connections': len(self.network_connections),
                'blocked_ips': list(self.blocked_ips),
                'suspicious_patterns': dict(self.suspicious_patterns)
            },
            'system_integrity': {
                'monitored_files': len(self.critical_files),
                'file_hashes_stored': len(self.file_integrity_hashes)
            }
        }
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def shutdown(self):
        """Shutdown the security monitor"""
        # Clear sensitive data
        self.threats.clear()
        self.incidents.clear()
        self.blocked_ips.clear()
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    security_monitor = SecurityMonitor(monitoring_interval_seconds=30)
    
    try:
        # Print initial status
        status = security_monitor.get_security_status()
        print(json.dumps(status, indent=2, default=str))
        
        # Keep monitoring
        import time
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("Shutting down Security Monitor...")
        security_monitor.shutdown() 