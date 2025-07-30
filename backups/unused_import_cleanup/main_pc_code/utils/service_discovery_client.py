#!/usr/bin/env python3
"""
Service Discovery Client Compatibility Shim

This module redirects legacy ZMQ-based service discovery imports to the 
unified discovery client while maintaining backward compatibility.

IMPORTANT: This is a temporary shim during the service discovery unification phase.
All new code should import directly from common.service_mesh.unified_discovery_client.

Usage:
    # Old way (still works via this shim)
    from main_pc_code.utils.service_discovery_client import discover_service
    
    # New way (preferred)
    from common.service_mesh.unified_discovery_client import discover_service_async
"""

import warnings
import logging
from typing import Dict, Any, Optional, Tuple

# Show deprecation warning for legacy service discovery usage
warnings.warn(
    "Importing from main_pc_code.utils.service_discovery_client is deprecated. "
    "Use 'from common.service_mesh.unified_discovery_client import discover_service_async' for new code.",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)
logger.info("ServiceDiscovery: Redirecting legacy import to unified discovery client")

# Import and re-export the unified discovery functions
try:
    from common.service_mesh.unified_discovery_client import (
        discover_service,
        get_service_address,
        get_service_discovery_client,
        discover_service_async,
        register_service,
        get_unified_discovery_client
    )
    
    # Legacy class compatibility
    class ServiceDiscoveryClient:
        """Legacy compatibility wrapper for ServiceDiscoveryClient."""
        
        def __init__(self, sdt_port: int = 7120):
            """Initialize with unified client backend."""
            self._unified_client = get_unified_discovery_client()
            logger.debug("Legacy ServiceDiscoveryClient using unified backend")
        
        def discover_service(self, service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
            """Legacy discover_service method."""
            return discover_service(service_name, machine)
        
        def get_service_address(self, service_name: str, machine: str = None) -> Optional[str]:
            """Legacy get_service_address method."""
            return get_service_address(service_name, machine)
        
        def connect_to_service(self, service_name: str, machine: str = None, socket_type: int = None):
            """Legacy connect_to_service method - deprecated in favor of direct connection."""
            warnings.warn(
                "connect_to_service is deprecated. Use get_service_address() and create connections directly.",
                DeprecationWarning,
                stacklevel=2
            )
            address = get_service_address(service_name, machine)
            if address:
                logger.info(f"Service {service_name} available at {address} - create connection manually")
                return address
            return None
    
    # Re-export for backward compatibility
    __all__ = [
        'ServiceDiscoveryClient',
        'discover_service', 
        'get_service_address',
        'get_service_discovery_client',
        'discover_service_async',
        'register_service'
    ]
    
    logger.debug("Service discovery shim: Successfully imported unified version")
    
except ImportError as e:
    logger.error(f"Service discovery shim: Failed to import unified version: {e}")
    raise ImportError(
        "Could not import unified discovery client from common.service_mesh.unified_discovery_client. "
        "Ensure the unified_discovery_client.py file exists and is properly configured."
    ) from e 