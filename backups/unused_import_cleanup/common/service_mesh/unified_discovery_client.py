#!/usr/bin/env python3
"""
Unified Service Discovery Client

Combines the modern async HTTP service mesh client with ZMQ compatibility
for seamless migration from legacy service discovery patterns.

Features:
- Async HTTP service mesh integration (primary)
- ZMQ compatibility layer for legacy agents
- Circuit breakers and health checking
- Load balancing and service registry integration
- Automatic protocol detection and fallback
"""

import os
import sys
import time
import logging
import asyncio
import aiohttp
import zmq
import zmq.asyncio as azmq
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import the modern service mesh client
from .client import ServiceMeshClient, ServiceEndpoint, CircuitBreakerState

# Hostname-based service discovery (Blueprint.md Step 6)
try:
    from common.utils.hostname_resolver import get_hostname_resolver, resolve_service_address, DiscoveryMode
    HOSTNAME_RESOLVER_AVAILABLE = True
except ImportError:
    logger.warning("Hostname resolver not available, falling back to IP-based discovery")
    HOSTNAME_RESOLVER_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class UnifiedServiceEndpoint:
    """Unified service endpoint supporting both HTTP and ZMQ protocols"""
    name: str
    host: str
    port: int
    health_port: int
    protocol: str = "http"  # http, zmq, auto
    zmq_port: Optional[int] = None
    mesh_type: str = "local"
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    capabilities: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}
        if self.last_health_check is None:
            self.last_health_check = datetime.now()

class UnifiedDiscoveryClient:
    """
    Unified service discovery client with dual protocol support.
    
    This client provides a seamless interface that works with both:
    - Modern HTTP-based service mesh (primary)
    - Legacy ZMQ-based service discovery (compatibility)
    """
    
    def __init__(self, 
                 mesh_type: str = "local", 
                 namespace: str = "ai-system",
                 enable_zmq_compat: bool = True,
                 service_registry_host: str = "localhost",
                 service_registry_port: int = 7100,
                 sdt_host: str = "localhost", 
                 sdt_port: int = 7120):
        
        # Initialize core service mesh client
        self.mesh_client = ServiceMeshClient(mesh_type=mesh_type, namespace=namespace)
        
        # ZMQ compatibility settings
        self.enable_zmq_compat = enable_zmq_compat
        self.service_registry_host = service_registry_host
        self.service_registry_port = service_registry_port
        self.sdt_host = sdt_host
        self.sdt_port = sdt_port
        
        # Protocol priority: http first, then zmq fallback
        self.protocol_priority = ["http", "zmq"]
        
        # Internal service cache
        self.unified_services: Dict[str, UnifiedServiceEndpoint] = {}
        
        # ZMQ context for compatibility layer
        self.zmq_context = None
        if self.enable_zmq_compat:
            self.zmq_context = zmq.Context()
        
        logger.info(f"Unified discovery client initialized: mesh={mesh_type}, zmq_compat={enable_zmq_compat}")
    
    async def discover_service_async(self, service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Async service discovery with multi-protocol support.
        
        Args:
            service_name: Name of the service to discover
            machine: Machine filter (optional)
            
        Returns:
            Tuple of (success, service_info)
        """
        logger.debug(f"Discovering service {service_name} (machine: {machine})")
        
        # Try hostname-based discovery first (Blueprint.md Step 6)
        if HOSTNAME_RESOLVER_AVAILABLE:
            try:
                resolver = get_hostname_resolver()
                endpoint = resolver.resolve_service(service_name, machine)
                
                if endpoint:
                    # Create unified endpoint from hostname resolution
                    unified_endpoint = UnifiedServiceEndpoint(
                        name=service_name,
                        host=endpoint.hostname,
                        port=endpoint.port,
                        protocol=endpoint.protocol,
                        machine=endpoint.machine,
                        ip=endpoint.ip,
                        health_port=endpoint.port + 1000,  # Convention: health port = service port + 1000
                        capabilities=[],
                        metadata={"resolution_mode": resolver.discovery_mode.value, "ip": endpoint.ip},
                        last_health_check=datetime.now()
                    )
                    
                    self.unified_services[service_name] = unified_endpoint
                    
                    return True, {
                        "status": "SUCCESS",
                        "payload": {
                            "name": service_name,
                            "ip": endpoint.ip or endpoint.hostname,
                            "hostname": endpoint.hostname,
                            "port": endpoint.port,
                            "health_check_port": unified_endpoint.health_port,
                            "protocol": endpoint.protocol,
                            "machine": endpoint.machine,
                            "resolution_mode": resolver.discovery_mode.value,
                            "address": endpoint.address,
                            "last_registered": datetime.now().isoformat()
                        }
                    }
            except Exception as e:
                logger.debug(f"Hostname discovery failed for {service_name}: {e}")
        
        # Try HTTP-based discovery second
        try:
            endpoint = self.mesh_client.get_service_endpoint(service_name)
            if endpoint and endpoint.is_healthy:
                unified_endpoint = self._convert_to_unified(endpoint)
                self.unified_services[service_name] = unified_endpoint
                
                return True, {
                    "status": "SUCCESS",
                    "payload": {
                        "name": service_name,
                        "ip": unified_endpoint.host,
                        "port": unified_endpoint.port,
                        "health_check_port": unified_endpoint.health_port,
                        "protocol": unified_endpoint.protocol,
                        "capabilities": unified_endpoint.capabilities,
                        "metadata": unified_endpoint.metadata,
                        "last_registered": unified_endpoint.last_health_check.isoformat()
                    }
                }
        except Exception as e:
            logger.debug(f"HTTP discovery failed for {service_name}: {e}")
        
        # Fallback to ZMQ-based discovery if enabled
        if self.enable_zmq_compat:
            return await self._discover_via_zmq_async(service_name, machine)
        
        return False, {"status": "NOT_FOUND", "message": f"Service {service_name} not found"}
    
    def discover_service(self, service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Synchronous service discovery (compatibility wrapper).
        
        Args:
            service_name: Name of the service to discover
            machine: Machine filter (optional)
            
        Returns:
            Tuple of (success, service_info)
        """
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, but this is a sync call
            # Create a task and run it
            task = asyncio.create_task(self.discover_service_async(service_name, machine))
            return asyncio.run_coroutine_threadsafe(task, loop).result(timeout=10.0)
        except RuntimeError:
            # No event loop running, we can use asyncio.run
            return asyncio.run(self.discover_service_async(service_name, machine))
        except Exception as e:
            logger.error(f"Sync discovery failed for {service_name}: {e}")
            return False, {"status": "ERROR", "message": str(e)}
    
    async def _discover_via_zmq_async(self, service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
        """ZMQ-based discovery fallback using async ZMQ."""
        logger.debug(f"Trying ZMQ discovery for {service_name}")
        
        # Try Service Registry first (modern)
        success, result = await self._query_service_registry(service_name)
        if success:
            return success, result
        
        # Fallback to SystemDigitalTwin (legacy)
        return await self._query_system_digital_twin(service_name, machine)
    
    async def _query_service_registry(self, service_name: str) -> Tuple[bool, Dict[str, Any]]:
        """Query the dedicated Service Registry agent."""
        try:
            context = azmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            address = f"tcp://{self.service_registry_host}:{self.service_registry_port}"
            socket.connect(address)
            
            request = {
                "action": "get_agent_endpoint",
                "agent_name": service_name
            }
            
            await socket.send_json(request)
            response = await socket.recv_json()
            
            socket.close()
            context.term()
            
            if response.get("status") == "success":
                # Convert ServiceRegistry format to unified format
                return True, {
                    "status": "SUCCESS",
                    "payload": {
                        "name": service_name,
                        "ip": response.get("host", "localhost"),
                        "port": response.get("port"),
                        "health_check_port": response.get("health_check_port"),
                        "protocol": "zmq",
                        "capabilities": response.get("capabilities", []),
                        "metadata": response.get("metadata", {}),
                        "last_registered": response.get("last_registered", datetime.now().isoformat())
                    }
                }
            
        except Exception as e:
            logger.debug(f"Service Registry query failed: {e}")
        
        return False, {"status": "ERROR", "message": "Service Registry query failed"}
    
    async def _query_system_digital_twin(self, service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Query SystemDigitalTwin for service discovery (legacy fallback)."""
        try:
            context = azmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            address = f"tcp://{self.sdt_host}:{self.sdt_port}"
            socket.connect(address)
            
            request = {
                "command": "DISCOVER",
                "payload": {"name": service_name}
            }
            if machine:
                request["payload"]["machine"] = machine
            
            await socket.send_json(request)
            response = await socket.recv_json()
            
            socket.close()
            context.term()
            
            return response.get("status") == "SUCCESS", response
            
        except Exception as e:
            logger.debug(f"SystemDigitalTwin query failed: {e}")
            return False, {"status": "ERROR", "message": str(e)}
    
    def get_service_address(self, service_name: str, machine: str = None) -> Optional[str]:
        """
        Get service address with hostname-aware protocol auto-detection.
        
        Args:
            service_name: Name of the service
            machine: Machine filter (optional)
            
        Returns:
            Service address string or None
        """
        success, response = self.discover_service(service_name, machine)
        
        if success and "payload" in response:
            payload = response["payload"]
            
            # Prefer hostname over IP for Docker compatibility (Blueprint.md Step 6)
            host = payload.get("hostname") or payload.get("ip", "localhost")
            port = payload.get("port")
            protocol = payload.get("protocol", "tcp")
            
            if host and port:
                # Convert 0.0.0.0 to localhost for client connections
                if host == "0.0.0.0":
                    host = "localhost"
                
                # Use hostname-aware addressing
                if protocol in ("http", "https"):
                    return f"{protocol}://{host}:{port}"
                else:
                    return f"tcp://{host}:{port}"
        
        return None
    
    def register_service(self, 
                        service_name: str, 
                        host: str, 
                        port: int, 
                        health_port: int,
                        protocol: str = "auto",
                        capabilities: List[str] = None,
                        metadata: Dict[str, Any] = None) -> bool:
        """
        Register a service with both HTTP and ZMQ registries.
        
        Args:
            service_name: Service name
            host: Service host
            port: Service port  
            health_port: Health check port
            protocol: Protocol type (http, zmq, auto)
            capabilities: Service capabilities
            metadata: Additional metadata
            
        Returns:
            Registration success
        """
        if capabilities is None:
            capabilities = []
        if metadata is None:
            metadata = {}
        
        # Register with HTTP service mesh
        try:
            self.mesh_client.register_service(service_name, host, port, health_port, protocol)
            logger.debug(f"Registered {service_name} with service mesh")
        except Exception as e:
            logger.warning(f"Failed to register {service_name} with service mesh: {e}")
        
        # Register with ZMQ registries if enabled
        if self.enable_zmq_compat:
            self._register_with_zmq_registries(service_name, host, port, health_port, capabilities, metadata)
        
        # Store in local cache
        unified_endpoint = UnifiedServiceEndpoint(
            name=service_name,
            host=host,
            port=port,
            health_port=health_port,
            protocol=protocol if protocol != "auto" else "http",
            capabilities=capabilities,
            metadata=metadata,
            last_health_check=datetime.now()
        )
        self.unified_services[service_name] = unified_endpoint
        
        return True
    
    def _register_with_zmq_registries(self, service_name: str, host: str, port: int, 
                                    health_port: int, capabilities: List[str], metadata: Dict[str, Any]):
        """Register with ZMQ-based registries."""
        # Try Service Registry first
        try:
            self._register_with_service_registry(service_name, host, port, health_port, capabilities, metadata)
        except Exception as e:
            logger.debug(f"Service Registry registration failed: {e}")
        
        # Try SystemDigitalTwin fallback  
        try:
            self._register_with_system_digital_twin(service_name, host, port, health_port, capabilities, metadata)
        except Exception as e:
            logger.debug(f"SystemDigitalTwin registration failed: {e}")
    
    def _register_with_service_registry(self, service_name: str, host: str, port: int,
                                      health_port: int, capabilities: List[str], metadata: Dict[str, Any]):
        """Register with ServiceRegistry agent."""
        if not self.zmq_context:
            return
        
        socket = self.zmq_context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        
        try:
            address = f"tcp://{self.service_registry_host}:{self.service_registry_port}"
            socket.connect(address)
            
            request = {
                "action": "register_agent",
                "agent_id": service_name,
                "host": host,
                "port": port,
                "health_check_port": health_port,
                "capabilities": capabilities,
                "metadata": metadata
            }
            
            socket.send_json(request)
            response = socket.recv_json()
            
            if response.get("status") == "success":
                logger.debug(f"Successfully registered {service_name} with Service Registry")
            else:
                logger.warning(f"Service Registry registration failed: {response}")
                
        except Exception as e:
            logger.debug(f"Service Registry registration error: {e}")
        finally:
            socket.close()
    
    def _register_with_system_digital_twin(self, service_name: str, host: str, port: int,
                                         health_port: int, capabilities: List[str], metadata: Dict[str, Any]):
        """Register with SystemDigitalTwin (legacy fallback)."""
        if not self.zmq_context:
            return
        
        socket = self.zmq_context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, 5000)
        
        try:
            address = f"tcp://{self.sdt_host}:{self.sdt_port}"
            socket.connect(address)
            
            request = {
                "command": "REGISTER",
                "payload": {
                    "name": service_name,
                    "ip": host,
                    "port": port,
                    "health_check_port": health_port,
                    "capabilities": capabilities,
                    "metadata": metadata
                }
            }
            
            socket.send_json(request)
            response = socket.recv_json()
            
            if response.get("status") == "SUCCESS":
                logger.debug(f"Successfully registered {service_name} with SystemDigitalTwin")
            else:
                logger.warning(f"SystemDigitalTwin registration failed: {response}")
                
        except Exception as e:
            logger.debug(f"SystemDigitalTwin registration error: {e}")
        finally:
            socket.close()
    
    def _convert_to_unified(self, endpoint: ServiceEndpoint) -> UnifiedServiceEndpoint:
        """Convert ServiceMeshClient endpoint to unified endpoint."""
        return UnifiedServiceEndpoint(
            name=endpoint.name,
            host=endpoint.host,
            port=endpoint.port,
            health_port=endpoint.health_port,
            protocol=endpoint.protocol,
            mesh_type=endpoint.mesh_type,
            last_health_check=endpoint.last_health_check,
            is_healthy=endpoint.is_healthy,
            capabilities=[],  # ServiceEndpoint doesn't have capabilities
            metadata={}  # ServiceEndpoint doesn't have metadata
        )
    
    def close(self):
        """Clean up resources."""
        if self.zmq_context:
            self.zmq_context.term()
        logger.debug("Unified discovery client closed")

# Global singleton instance
_unified_client: Optional[UnifiedDiscoveryClient] = None

def get_unified_discovery_client() -> UnifiedDiscoveryClient:
    """Get the global unified discovery client instance."""
    global _unified_client
    if _unified_client is None:
        mesh_type = os.getenv("SERVICE_MESH_TYPE", "local")
        namespace = os.getenv("SERVICE_MESH_NAMESPACE", "ai-system")
        enable_zmq = os.getenv("ENABLE_ZMQ_COMPAT", "true").lower() == "true"
        
        _unified_client = UnifiedDiscoveryClient(
            mesh_type=mesh_type,
            namespace=namespace,
            enable_zmq_compat=enable_zmq
        )
    return _unified_client

# Compatibility functions for legacy ZMQ interface
def discover_service(service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
    """Legacy compatibility function for ZMQ-based discovery."""
    client = get_unified_discovery_client()
    return client.discover_service(service_name, machine)

def get_service_address(service_name: str, machine: str = None) -> Optional[str]:
    """Legacy compatibility function for getting service addresses."""
    client = get_unified_discovery_client()
    return client.get_service_address(service_name, machine)

def get_service_discovery_client() -> UnifiedDiscoveryClient:
    """Legacy compatibility function - returns unified client."""
    return get_unified_discovery_client()

# Modern async interface
async def discover_service_async(service_name: str, machine: str = None) -> Tuple[bool, Dict[str, Any]]:
    """Modern async service discovery."""
    client = get_unified_discovery_client()
    return await client.discover_service_async(service_name, machine)

def register_service(service_name: str, host: str, port: int, health_port: int,
                    protocol: str = "auto", capabilities: List[str] = None,
                    metadata: Dict[str, Any] = None) -> bool:
    """Register a service with the unified discovery system."""
    client = get_unified_discovery_client()
    return client.register_service(service_name, host, port, health_port, protocol, capabilities, metadata) 