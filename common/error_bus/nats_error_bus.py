#!/usr/bin/env python3
"""
NATS Error Bus System
====================
Modern error handling infrastructure using NATS messaging
Replaces legacy ZMQ-based error handling with scalable, distributed error management
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import nats
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout, ErrNoServers

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"

class ErrorCategory(Enum):
    """Error categories for better classification"""
    SYSTEM = "system"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    EXTERNAL_API = "external_api"
    USER_INPUT = "user_input"
    BUSINESS_LOGIC = "business_logic"

@dataclass
class ErrorEvent:
    """Standardized error event structure"""
    id: str
    timestamp: datetime
    agent_name: str
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    details: Dict[str, Any]
    stack_trace: Optional[str] = None
    correlation_id: Optional[str] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None

class NATSErrorBus:
    """
    NATS-based error bus for distributed error handling
    """
    
    def __init__(self, 
                 nats_servers: List[str] = None,
                 agent_name: str = "unknown",
                 max_reconnect_attempts: int = 10):
        self.nats_servers = nats_servers or ["nats://localhost:4222"]
        self.agent_name = agent_name
        self.max_reconnect_attempts = max_reconnect_attempts
        
        self.nc: Optional[NATS] = None
        self.js = None  # JetStream context
        self.connected = False
        self.error_handlers: Dict[str, List[Callable]] = {}
        self.subscription_handlers = []
        
        # Error subjects
        self.error_subject = "errors.events"
        self.agent_error_subject = f"errors.agents.{agent_name}"
        self.system_error_subject = "errors.system"
        
    async def connect(self):
        """Connect to NATS with proper error handling"""
        try:
            self.nc = NATS()
            
            await self.nc.connect(
                servers=self.nats_servers,
                max_reconnect_attempts=self.max_reconnect_attempts,
                reconnect_time_wait=2,
                error_cb=self._error_callback,
                disconnected_cb=self._disconnected_callback,
                reconnected_cb=self._reconnected_callback
            )
            
            # Initialize JetStream
            self.js = self.nc.jetstream()
            
            # Create streams if they don't exist
            await self._setup_streams()
            
            # Subscribe to error events
            await self._setup_subscriptions()
            
            self.connected = True
            logger.info(f"✅ NATS Error Bus connected for {self.agent_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
            self.connected = False
            raise
    
    async def _setup_streams(self):
        """Create JetStream streams for error persistence"""
        try:
            # Error events stream
            await self.js.add_stream(
                name="ERRORS",
                subjects=["errors.>"],
                max_msgs=100000,  # Keep last 100k errors
                max_age=7 * 24 * 3600,  # Keep for 7 days
                storage="file"
            )
            
            # Agent-specific error stream
            await self.js.add_stream(
                name="AGENT_ERRORS",
                subjects=["errors.agents.>"],
                max_msgs=50000,
                max_age=3 * 24 * 3600,  # Keep for 3 days
                storage="file"
            )
            
            logger.info("✅ NATS Error streams configured")
            
        except Exception as e:
            if "stream name already in use" not in str(e):
                logger.warning(f"Failed to setup streams: {e}")
    
    async def _setup_subscriptions(self):
        """Setup error event subscriptions"""
        try:
            # Subscribe to all errors for this agent
            sub = await self.nc.subscribe(
                self.agent_error_subject,
                cb=self._handle_agent_error
            )
            self.subscription_handlers.append(sub)
            
            # Subscribe to system-wide critical errors
            sub = await self.nc.subscribe(
                "errors.system.critical",
                cb=self._handle_critical_error
            )
            self.subscription_handlers.append(sub)
            
            logger.info(f"✅ Error subscriptions active for {self.agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup subscriptions: {e}")
    
    async def publish_error(self, 
                          severity: ErrorSeverity,
                          category: ErrorCategory,
                          message: str,
                          details: Dict[str, Any] = None,
                          stack_trace: str = None,
                          correlation_id: str = None):
        """Publish an error event"""
        if not self.connected:
            logger.warning("NATS not connected, error not published")
            return None
        
        try:
            error_event = ErrorEvent(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                agent_name=self.agent_name,
                severity=severity,
                category=category,
                message=message,
                details=details or {},
                stack_trace=stack_trace,
                correlation_id=correlation_id
            )
            
            # Convert to JSON
            error_data = asdict(error_event)
            error_data["timestamp"] = error_event.timestamp.isoformat()
            error_data["severity"] = severity.value
            error_data["category"] = category.value
            
            # Publish to multiple subjects based on severity
            subjects = [self.error_subject, self.agent_error_subject]
            
            if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                subjects.append(self.system_error_subject)
                subjects.append("errors.system.critical")
            
            # Publish to all relevant subjects
            for subject in subjects:
                await self.js.publish(
                    subject,
                    json.dumps(error_data).encode(),
                    headers={"agent": self.agent_name, "severity": severity.value}
                )
            
            logger.debug(f"📤 Error published: {error_event.id} ({severity.value})")
            return error_event.id
            
        except Exception as e:
            logger.error(f"Failed to publish error: {e}")
            return None
    
    async def _handle_agent_error(self, msg):
        """Handle errors for this specific agent"""
        try:
            error_data = json.loads(msg.data.decode())
            
            # Call registered error handlers
            error_category = error_data.get("category", "system")
            if error_category in self.error_handlers:
                for handler in self.error_handlers[error_category]:
                    try:
                        await handler(error_data)
                    except Exception as e:
                        logger.error(f"Error handler failed: {e}")
            
        except Exception as e:
            logger.error(f"Failed to handle agent error: {e}")
    
    async def _handle_critical_error(self, msg):
        """Handle system-wide critical errors"""
        try:
            error_data = json.loads(msg.data.decode())
            logger.critical(f"🚨 CRITICAL SYSTEM ERROR: {error_data.get('message', 'Unknown')}")
            
            # Could trigger alerts, notifications, etc.
            
        except Exception as e:
            logger.error(f"Failed to handle critical error: {e}")
    
    def register_error_handler(self, category: str, handler: Callable):
        """Register a callback for specific error categories"""
        if category not in self.error_handlers:
            self.error_handlers[category] = []
        self.error_handlers[category].append(handler)
    
    async def get_recent_errors(self, 
                              hours: int = 24,
                              severity: Optional[ErrorSeverity] = None) -> List[Dict]:
        """Retrieve recent errors from the error bus"""
        if not self.connected:
            return []
        
        try:
            # Query JetStream for recent errors
            consumer = await self.js.subscribe(
                f"errors.agents.{self.agent_name}",
                durable=f"{self.agent_name}_error_query"
            )
            
            errors = []
            start_time = datetime.now() - timedelta(hours=hours)
            
            async for msg in consumer.messages:
                try:
                    error_data = json.loads(msg.data.decode())
                    error_time = datetime.fromisoformat(error_data["timestamp"])
                    
                    if error_time >= start_time:
                        if not severity or error_data["severity"] == severity.value:
                            errors.append(error_data)
                    
                    await msg.ack()
                    
                    # Limit results
                    if len(errors) >= 1000:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to parse error message: {e}")
                    await msg.ack()
            
            return errors
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent errors: {e}")
            return []
    
    async def _error_callback(self, error):
        """Handle NATS connection errors"""
        logger.error(f"NATS Error: {error}")
    
    async def _disconnected_callback(self):
        """Handle NATS disconnection"""
        logger.warning("NATS disconnected")
        self.connected = False
    
    async def _reconnected_callback(self):
        """Handle NATS reconnection"""
        logger.info("NATS reconnected")
        self.connected = True
    
    async def close(self):
        """Close NATS connection gracefully"""
        if self.nc and not self.nc.is_closed:
            # Unsubscribe from all subscriptions
            for sub in self.subscription_handlers:
                try:
                    await sub.unsubscribe()
                except Exception as e:
                    logger.warning(f"Failed to unsubscribe: {e}")
            
            await self.nc.close()
            self.connected = False
            logger.info("✅ NATS Error Bus disconnected")

# Convenience functions for easy integration
async def create_error_bus(agent_name: str, 
                          nats_servers: List[str] = None) -> NATSErrorBus:
    """Create and connect to NATS error bus"""
    error_bus = NATSErrorBus(nats_servers, agent_name)
    await error_bus.connect()
    return error_bus

# Legacy compatibility functions
class ErrorBusAdapter:
    """Adapter to provide legacy ZMQ-like interface"""
    
    def __init__(self, nats_error_bus: NATSErrorBus):
        self.error_bus = nats_error_bus
    
    async def report_error(self, error_type: str, message: str, details: Dict = None):
        """Legacy error reporting interface"""
        severity = ErrorSeverity.ERROR
        category = ErrorCategory.SYSTEM
        
        # Map legacy error types to new categories
        if "network" in error_type.lower():
            category = ErrorCategory.NETWORK
        elif "database" in error_type.lower():
            category = ErrorCategory.DATABASE
        elif "auth" in error_type.lower():
            category = ErrorCategory.AUTHENTICATION
        
        return await self.error_bus.publish_error(
            severity=severity,
            category=category,
            message=message,
            details=details
        )
    
    async def get_errors(self, hours: int = 24) -> List[Dict]:
        """Legacy error retrieval interface"""
        return await self.error_bus.get_recent_errors(hours=hours) 