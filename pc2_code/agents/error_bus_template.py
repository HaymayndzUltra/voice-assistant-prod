#!/usr/bin/env python3
"""
PC2 Error Bus Template
Simple error reporting interface for PC2 agents
Provides compatibility layer for agents that haven't been modernized to use BaseAgent
"""

import logging
import sys
import traceback
from typing import Optional, Dict, Any
from datetime import datetime

# Initialize logger
logger = logging.getLogger("PC2ErrorBus")

# Global error reporting state
_error_reporting_initialized = False
_error_count = 0

def setup_error_reporting(agent_name: str = "Unknown", **kwargs) -> bool:
    """
    Setup error reporting for a PC2 agent
    
    Args:
        agent_name: Name of the agent setting up error reporting
        **kwargs: Additional configuration options
        
    Returns:
        bool: True if setup successful, False otherwise
    """
    global _error_reporting_initialized
    
    try:
        # Simple setup - just ensure logging is configured
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - PC2ErrorBus - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        _error_reporting_initialized = True
        logger.info(f"Error reporting setup completed for agent: {agent_name}")
        return True
        
    except Exception as e:
        print(f"Failed to setup error reporting for {agent_name}: {e}")
        return False

def report_error(
    message: str, 
    severity: str = "ERROR", 
    agent_name: str = "Unknown",
    error_type: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    **kwargs
) -> bool:
    """
    Report an error through the error bus
    
    Args:
        message: Error message
        severity: Error severity (ERROR, WARNING, INFO, etc.)
        agent_name: Name of the agent reporting the error
        error_type: Type/category of error
        details: Additional error details
        **kwargs: Additional parameters
        
    Returns:
        bool: True if error reported successfully, False otherwise
    """
    global _error_count
    
    try:
        _error_count += 1
        
        # Format error message
        timestamp = datetime.now().isoformat()
        error_info = {
            "timestamp": timestamp,
            "agent": agent_name,
            "severity": severity.upper(),
            "message": message,
            "error_type": error_type or "UnknownError",
            "details": details or {},
            "error_id": _error_count
        }
        
        # Log the error
        log_message = f"[{agent_name}] {severity}: {message}"
        if error_type:
            log_message += f" (Type: {error_type})"
        
        # Log based on severity
        if severity.upper() in ["ERROR", "CRITICAL"]:
            logger.error(log_message)
        elif severity.upper() == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Add stack trace for errors
        if severity.upper() in ["ERROR", "CRITICAL"]:
            stack_trace = traceback.format_stack()
            logger.debug(f"Stack trace for error {_error_count}: {''.join(stack_trace)}")
        
        return True
        
    except Exception as e:
        print(f"Failed to report error from {agent_name}: {e}")
        return False

def cleanup_error_reporting(agent_name: str = "Unknown") -> bool:
    """
    Cleanup error reporting resources for an agent
    
    Args:
        agent_name: Name of the agent cleaning up
        
    Returns:
        bool: True if cleanup successful, False otherwise
    """
    try:
        logger.info(f"Error reporting cleanup completed for agent: {agent_name}")
        return True
        
    except Exception as e:
        print(f"Failed to cleanup error reporting for {agent_name}: {e}")
        return False

# Compatibility aliases for different naming conventions
setup_error_bus = setup_error_reporting
report_error_to_bus = report_error
cleanup_error_bus = cleanup_error_reporting

# Module-level initialization
if __name__ == "__main__":
    # Test the module
    print("Testing PC2 Error Bus Template...")
    
    # Test setup
    success = setup_error_reporting("TestAgent")
    print(f"Setup: {'✅' if success else '❌'}")
    
    # Test error reporting
    success = report_error("Test error message", "ERROR", "TestAgent")
    print(f"Error Report: {'✅' if success else '❌'}")
    
    # Test cleanup
    success = cleanup_error_reporting("TestAgent")
    print(f"Cleanup: {'✅' if success else '❌'}")
    
    print("PC2 Error Bus Template test completed!") 