#!/usr/bin/env python3
"""
Error Bus Integration Template

This file provides a standardized template for integrating PC2 agents with the 
central Error Bus service. This template ensures consistent error reporting across
all agents in the distributed AI system.

Usage:
1. Import the setup_error_reporting function
2. Call the function in your agent's __init__ method
3. Use the report_error method to send errors to the Error Bus

Example:
    from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
    
    class MyAgent(BaseAgent):
        
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self):
            super().__init__(name="MyAgent", port=5555)
            self.error_bus = setup_error_reporting(self)
            
        def some_method(self):
            try:
                # Some code that might fail
                pass
            except Exception as e:
                report_error(self.error_bus, "operation_failed", str(e), "ERROR", {"details": "Additional context"})
"""

import os
import zmq
import json
import time
import logging
import traceback
from typing import Dict, Any, Optional, Union

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Configure logging
logger = logging.getLogger(__name__)

def setup_error_reporting(agent, error_bus_port: int = 7150) -> Optional[Dict[str, Any]]:
    """
    Set up error reporting for an agent.
    
    Args:
        agent: The agent instance (must have zmq.Context as self.context)
        error_bus_port: Port for the central Error Bus service
        
    Returns:
        Optional[Dict[str, Any]]: Error bus configuration or None if setup failed
    """
    # Get PC2_IP from environment or use default
    error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
    error_bus_endpoint = f"tcp://{error_bus_host}:{error_bus_port}"
    
    # Create PUB socket using the agent's ZMQ context
    try:
        error_bus_pub = agent.context.socket(zmq.PUB)
        error_bus_pub.connect(error_bus_endpoint)
        logger.info(f"Connected to Error Bus at {error_bus_endpoint}")
        
        # Return configuration for future use
        return {
            "socket": error_bus_pub,
            "endpoint": error_bus_endpoint,
            "host": error_bus_host,
            "port": error_bus_port
        }
    except Exception as e:
        logger.error(f"Failed to connect to Error Bus: {e}")
        # Return None to indicate setup failure
        return None

def report_error(error_bus: Optional[Dict[str, Any]], error_type: str, message: str, 
               severity: str = "ERROR", details: Optional[Dict[str, Any]] = None) -> bool:
    """
    Report an error to the central Error Bus.
    
    Args:
        error_bus: Error bus configuration from setup_error_reporting
        error_type: Type of error (e.g., "connection_error", "timeout", etc.)
        message: Error message
        severity: Error severity ("INFO", "WARNING", "ERROR", "CRITICAL")
        details: Additional error details (optional)
    
    Returns:
        bool: True if error was sent successfully, False otherwise
    """
    if not error_bus or "socket" not in error_bus:
        logger.warning("Error bus not configured, error not reported")
        return False
    
    try:
        # Get the agent name from the error_bus object if available
        agent_name = getattr(error_bus.get("agent", None), "name", "unknown")
        
        # Prepare error data
        error_data = {
            "timestamp": time.time(),
            "agent": agent_name,
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "details": details or {}
        }
        
        # Add stack trace if available and this is an ERROR or CRITICAL
        if severity in ("ERROR", "CRITICAL"):
            error_data["details"]["stack_trace"] = traceback.format_exc()
        
        # Format message for Error Bus (ERROR: prefix + JSON)
        error_message = f"ERROR:{json.dumps(error_data)}"
        
        # Send to Error Bus
        error_bus["socket"].send_string(error_message)
        return True
    except Exception as e:
        logger.error(f"Failed to report error to Error Bus: {e}")
        return False

def cleanup_error_reporting(error_bus: Optional[Dict[str, Any]]) -> None:
    """
    Clean up error reporting resources.
    
    Args:
        error_bus: Error bus configuration from setup_error_reporting
    """
    if error_bus and "socket" in error_bus:
        try:
            error_bus["socket"].close()
        except Exception as e:
            logger.warning(f"Error closing Error Bus socket: {e}")

# Example decorator for error reporting
def report_errors(error_type: str = "function_error", severity: str = "ERROR"):
    """
    Decorator to automatically report errors from a function.
    
    Args:
        error_type: Type of error to report
        severity: Error severity level
    
    Example:
        @report_errors(error_type="database_error", severity="CRITICAL")
        def database_operation(self):
            # Function implementation
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Try to access error_bus attribute
                if hasattr(self, "error_bus"):
                    report_error(
                        self.error_bus,
                        error_type,
                        f"Error in {func.__name__}: {str(e)}",
                        severity,
                        {"function": func.__name__, "args": str(args), "kwargs": str(kwargs)}
                    )
                # Re-raise the exception
                raise
        return wrapper
    return decorator 
    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None))
        }
