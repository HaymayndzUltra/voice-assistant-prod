#!/usr/bin/env python3
"""
Unified Error Handler
====================
Bridge between legacy ZMQ error reporting (SystemDigitalTwin) and modern NATS error bus
Provides gradual migration strategy with dual-send capability during transition
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

# Legacy imports
from common.utils.data_models import ErrorReport, ErrorSeverity as LegacyErrorSeverity

# Modern NATS imports  
from .nats_error_bus import NATSErrorBus, ErrorSeverity as NATSErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

class UnifiedErrorHandler:
    """
    Unified error handler that bridges legacy ZMQ and modern NATS systems
    Supports gradual migration with dual-send capability
    """
    
    def __init__(self, 
                 agent_name: str,
                 enable_legacy_zmq: bool = True,
                 enable_nats: bool = True,
                 nats_servers: List[str] = None):
        self.agent_name = agent_name
        self.enable_legacy_zmq = enable_legacy_zmq
        self.enable_nats = enable_nats
        
        # Legacy ZMQ components (will be injected by BaseAgent)
        self.digital_twin_socket = None
        self.legacy_send_method = None
        
        # Modern NATS error bus
        self.nats_error_bus: Optional[NATSErrorBus] = None
        self.nats_servers = nats_servers
        
        # Statistics
        self.stats = {
            "legacy_sent": 0,
            "legacy_failed": 0,
            "nats_sent": 0,
            "nats_failed": 0,
            "dual_sent": 0
        }
    
    def set_legacy_handler(self, send_method):
        """Set the legacy ZMQ send method (injected by BaseAgent)"""
        self.legacy_send_method = send_method
    
    async def initialize_nats(self):
        """Initialize NATS error bus if enabled"""
        if not self.enable_nats:
            return
        
        try:
            self.nats_error_bus = NATSErrorBus(
                nats_servers=self.nats_servers,
                agent_name=self.agent_name
            )
            await self.nats_error_bus.connect()
            logger.info(f"✅ NATS error bus initialized for {self.agent_name}")
        except Exception as e:
            logger.warning(f"⚠️ NATS error bus initialization failed for {self.agent_name}: {e}")
            self.nats_error_bus = None
    
    async def report_error(self,
                          severity: Union[str, LegacyErrorSeverity, NATSErrorSeverity],
                          message: str,
                          error_type: str = "system_error",
                          details: Optional[Dict[str, Any]] = None,
                          category: Optional[ErrorCategory] = None,
                          stack_trace: Optional[str] = None,
                          related_task_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Unified error reporting that sends to both legacy and modern systems
        
        Returns:
            Dict with success status for each system: {"legacy": bool, "nats": bool}
        """
        results = {"legacy": False, "nats": False}
        error_id = str(uuid.uuid4())
        
        # Normalize severity
        legacy_severity = self._normalize_legacy_severity(severity)
        nats_severity = self._normalize_nats_severity(severity)
        
        # 1. Send to Legacy ZMQ System (SystemDigitalTwin) - CRITICAL PATH
        if self.enable_legacy_zmq:
            results["legacy"] = await self._send_to_legacy(
                error_id=error_id,
                severity=legacy_severity,
                message=message,
                error_type=error_type,
                details=details,
                stack_trace=stack_trace,
                related_task_id=related_task_id
            )
        
        # 2. Send to Modern NATS System - OPTIONAL/NEW
        if self.enable_nats:
            results["nats"] = await self._send_to_nats(
                severity=nats_severity,
                message=message,
                category=category or self._map_error_type_to_category(error_type),
                details=details,
                stack_trace=stack_trace,
                correlation_id=error_id
            )
        
        # Update statistics
        if results["legacy"] and results["nats"]:
            self.stats["dual_sent"] += 1
        
        return results
    
    async def _send_to_legacy(self,
                             error_id: str,
                             severity: LegacyErrorSeverity,
                             message: str,
                             error_type: str,
                             details: Optional[Dict] = None,
                             stack_trace: Optional[str] = None,
                             related_task_id: Optional[str] = None) -> bool:
        """Send error to legacy ZMQ SystemDigitalTwin"""
        try:
            # Create legacy ErrorReport
            error_report = ErrorReport(
                error_id=error_id,
                agent_id=self.agent_name,
                severity=severity,
                error_type=error_type,
                message=message,
                timestamp=datetime.now(),
                context=details or {},
                stack_trace=stack_trace,
                related_task_id=related_task_id,
                recovery_attempted=False
            )
            
            # Send via legacy method (usually ZMQ to SystemDigitalTwin)
            if self.legacy_send_method:
                await self.legacy_send_method(error_report)
                self.stats["legacy_sent"] += 1
                logger.debug(f"✅ Legacy error sent: {error_id}")
                return True
            else:
                logger.warning("❌ Legacy send method not configured")
                return False
                
        except Exception as e:
            self.stats["legacy_failed"] += 1
            logger.error(f"❌ Failed to send error to legacy system: {e}")
            return False
    
    async def _send_to_nats(self,
                           severity: NATSErrorSeverity,
                           message: str,
                           category: ErrorCategory,
                           details: Optional[Dict] = None,
                           stack_trace: Optional[str] = None,
                           correlation_id: Optional[str] = None) -> bool:
        """Send error to modern NATS error bus"""
        if not self.nats_error_bus or not self.nats_error_bus.connected:
            logger.debug("⚠️ NATS error bus not available")
            return False
        
        try:
            error_id = await self.nats_error_bus.publish_error(
                severity=severity,
                category=category,
                message=message,
                details=details or {},
                stack_trace=stack_trace,
                correlation_id=correlation_id
            )
            
            if error_id:
                self.stats["nats_sent"] += 1
                logger.debug(f"✅ NATS error sent: {error_id}")
                return True
            else:
                self.stats["nats_failed"] += 1
                return False
                
        except Exception as e:
            self.stats["nats_failed"] += 1
            logger.warning(f"⚠️ Failed to send error to NATS (non-critical): {e}")
            return False
    
    def _normalize_legacy_severity(self, severity: Union[str, LegacyErrorSeverity, NATSErrorSeverity]) -> LegacyErrorSeverity:
        """Convert any severity format to legacy ErrorSeverity"""
        if isinstance(severity, LegacyErrorSeverity):
            return severity
        
        severity_str = str(severity).lower() if severity else "error"
        
        # Map NATS severities to legacy
        mapping = {
            "debug": LegacyErrorSeverity.INFO,
            "info": LegacyErrorSeverity.INFO,
            "warning": LegacyErrorSeverity.WARNING,
            "error": LegacyErrorSeverity.ERROR,
            "critical": LegacyErrorSeverity.CRITICAL,
            "fatal": LegacyErrorSeverity.CRITICAL
        }
        
        return mapping.get(severity_str, LegacyErrorSeverity.ERROR)
    
    def _normalize_nats_severity(self, severity: Union[str, LegacyErrorSeverity, NATSErrorSeverity]) -> NATSErrorSeverity:
        """Convert any severity format to NATS ErrorSeverity"""
        if isinstance(severity, NATSErrorSeverity):
            return severity
        
        severity_str = str(severity).lower() if severity else "error"
        
        # Map legacy severities to NATS
        mapping = {
            "info": NATSErrorSeverity.INFO,
            "warning": NATSErrorSeverity.WARNING,
            "error": NATSErrorSeverity.ERROR,
            "critical": NATSErrorSeverity.CRITICAL
        }
        
        return mapping.get(severity_str, NATSErrorSeverity.ERROR)
    
    def _map_error_type_to_category(self, error_type: str) -> ErrorCategory:
        """Map legacy error_type to NATS ErrorCategory"""
        error_type_lower = error_type.lower()
        
        if "network" in error_type_lower or "connection" in error_type_lower:
            return ErrorCategory.NETWORK
        elif "database" in error_type_lower or "db" in error_type_lower:
            return ErrorCategory.DATABASE
        elif "auth" in error_type_lower or "permission" in error_type_lower:
            return ErrorCategory.AUTHENTICATION
        elif "validation" in error_type_lower or "invalid" in error_type_lower:
            return ErrorCategory.VALIDATION
        elif "resource" in error_type_lower or "memory" in error_type_lower:
            return ErrorCategory.RESOURCE
        elif "config" in error_type_lower:
            return ErrorCategory.CONFIGURATION
        elif "api" in error_type_lower or "external" in error_type_lower:
            return ErrorCategory.EXTERNAL_API
        elif "user" in error_type_lower or "input" in error_type_lower:
            return ErrorCategory.USER_INPUT
        elif "business" in error_type_lower or "logic" in error_type_lower:
            return ErrorCategory.BUSINESS_LOGIC
        else:
            return ErrorCategory.SYSTEM
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        total_attempts = self.stats["legacy_sent"] + self.stats["legacy_failed"]
        nats_attempts = self.stats["nats_sent"] + self.stats["nats_failed"]
        
        return {
            "agent_name": self.agent_name,
            "legacy_enabled": self.enable_legacy_zmq,
            "nats_enabled": self.enable_nats,
            "nats_connected": self.nats_error_bus.connected if self.nats_error_bus else False,
            "statistics": self.stats.copy(),
            "success_rates": {
                "legacy": (self.stats["legacy_sent"] / total_attempts * 100) if total_attempts > 0 else 0,
                "nats": (self.stats["nats_sent"] / nats_attempts * 100) if nats_attempts > 0 else 0
            }
        }
    
    async def close(self):
        """Cleanup resources"""
        if self.nats_error_bus:
            try:
                await self.nats_error_bus.close()
                logger.info(f"✅ Unified error handler closed for {self.agent_name}")
            except Exception as e:
                logger.warning(f"Failed to close NATS error bus: {e}")

# Convenience function for creating unified error handlers
async def create_unified_error_handler(agent_name: str,
                                     enable_legacy: bool = True,
                                     enable_nats: bool = True,
                                     nats_servers: List[str] = None) -> UnifiedErrorHandler:
    """Create and initialize a unified error handler"""
    handler = UnifiedErrorHandler(
        agent_name=agent_name,
        enable_legacy_zmq=enable_legacy,
        enable_nats=enable_nats,
        nats_servers=nats_servers
    )
    
    if enable_nats:
        await handler.initialize_nats()
    
    return handler 