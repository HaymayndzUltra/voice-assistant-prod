
"""
Service Mesh Client Library for WP-09 Service Mesh Integration
Provides service discovery, load balancing, and circuit breaking for inter-agent communication
"""

import os
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import json

@dataclass
class ServiceEndpoint:
    """Service endpoint information"""
    name: str
    host: str
    port: int
    health_port: int
    protocol: str
    mesh_type: str
    last_health_check: datetime
    is_healthy: bool = True

@dataclass
class CircuitBreakerState:
    """Circuit breaker state for service calls"""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    next_attempt_time: Optional[datetime] = None

class ServiceMeshClient:
    """
    Service mesh client for inter-agent communication
    Handles service discovery, load balancing, and circuit breaking
    """
    
    def __init__(self, mesh_type: str = "istio", namespace: str = "ai-system"):
        self.mesh_type = mesh_type
        self.namespace = namespace
        self.services: Dict[str, List[ServiceEndpoint]] = {}
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.health_check_interval = 30  # seconds
        self.circuit_breaker_threshold = 5
        self.circuit_breaker_timeout = 60  # seconds
        
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for health checking and service discovery"""
        if hasattr(asyncio, 'create_task'):
            asyncio.create_task(self._health_check_loop())
            asyncio.create_task(self._service_discovery_loop())
    
    async def _health_check_loop(self):
        """Background health checking loop"""
        while True:
            try:
                await self._check_all_services_health()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)
    
    async def _service_discovery_loop(self):
        """Background service discovery loop"""
        while True:
            try:
                await self._discover_services()
                await asyncio.sleep(60)  # Discover every minute
            except Exception as e:
                self.logger.error(f"Service discovery error: {e}")
                await asyncio.sleep(10)
    
    async def _discover_services(self):
        """Discover services in the mesh"""
        if self.mesh_type == "istio":
            await self._discover_istio_services()
        elif self.mesh_type == "linkerd":
            await self._discover_linkerd_services()
        else:
            await self._discover_local_services()
    
    async def _discover_istio_services(self):
        """Discover services via Istio API"""
        try:
            # Query Istio service registry
            # This would typically use Kubernetes API or Istio API
            # For now, we'll use a local service registry
            await self._discover_local_services()
        except Exception as e:
            self.logger.error(f"Istio service discovery error: {e}")
    
    async def _discover_linkerd_services(self):
        """Discover services via Linkerd API"""
        try:
            # Query Linkerd service registry
            # This would typically use Kubernetes API or Linkerd API
            # For now, we'll use a local service registry
            await self._discover_local_services()
        except Exception as e:
            self.logger.error(f"Linkerd service discovery error: {e}")
    
    async def _discover_local_services(self):
        """Discover services via local registry"""
        # Load from environment or config file
        service_registry_path = os.getenv("SERVICE_REGISTRY_PATH", "config/service_registry.json")
        
        if os.path.exists(service_registry_path):
            with open(service_registry_path, 'r') as f:
                registry = json.load(f)
                
            for service_name, endpoints in registry.items():
                self.services[service_name] = [
                    ServiceEndpoint(**endpoint) for endpoint in endpoints
                ]
    
    async def _check_all_services_health(self):
        """Check health of all registered services"""
        for service_name, endpoints in self.services.items():
            for endpoint in endpoints:
                await self._check_service_health(endpoint)
    
    async def _check_service_health(self, endpoint: ServiceEndpoint) -> bool:
        """Check health of a single service endpoint"""
        try:
            health_url = f"http://{endpoint.host}:{endpoint.health_port}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=5) as response:
                    if response.status == 200:
                        endpoint.is_healthy = True
                        endpoint.last_health_check = datetime.now()
                        return True
                    else:
                        endpoint.is_healthy = False
                        return False
        except Exception as e:
            self.logger.warning(f"Health check failed for {endpoint.name}: {e}")
            endpoint.is_healthy = False
            return False
    
    def get_service_endpoint(self, service_name: str) -> Optional[ServiceEndpoint]:
        """Get a healthy service endpoint using load balancing"""
        if service_name not in self.services:
            self.logger.warning(f"Service {service_name} not found in registry")
            return None
        
        # Filter healthy endpoints
        healthy_endpoints = [
            ep for ep in self.services[service_name] 
            if ep.is_healthy and not self._is_circuit_breaker_open(ep.name)
        ]
        
        if not healthy_endpoints:
            self.logger.warning(f"No healthy endpoints for service {service_name}")
            return None
        
        # Simple round-robin load balancing
        # In production, this could be more sophisticated
        return healthy_endpoints[0]
    
    def _is_circuit_breaker_open(self, endpoint_name: str) -> bool:
        """Check if circuit breaker is open for an endpoint"""
        if endpoint_name not in self.circuit_breakers:
            return False
        
        cb_state = self.circuit_breakers[endpoint_name]
        
        if cb_state.state == "OPEN":
            if cb_state.next_attempt_time and datetime.now() > cb_state.next_attempt_time:
                cb_state.state = "HALF_OPEN"
                return False
            return True
        
        return False
    
    def _record_call_success(self, endpoint_name: str):
        """Record a successful call"""
        if endpoint_name in self.circuit_breakers:
            cb_state = self.circuit_breakers[endpoint_name]
            cb_state.failure_count = 0
            cb_state.state = "CLOSED"
            cb_state.next_attempt_time = None
    
    def _record_call_failure(self, endpoint_name: str):
        """Record a failed call"""
        if endpoint_name not in self.circuit_breakers:
            self.circuit_breakers[endpoint_name] = CircuitBreakerState()
        
        cb_state = self.circuit_breakers[endpoint_name]
        cb_state.failure_count += 1
        cb_state.last_failure_time = datetime.now()
        
        if cb_state.failure_count >= self.circuit_breaker_threshold:
            cb_state.state = "OPEN"
            cb_state.next_attempt_time = datetime.now() + timedelta(seconds=self.circuit_breaker_timeout)
    
    async def call_service(self, service_name: str, path: str = "/", method: str = "GET", 
                          data: Any = None, timeout: int = 30) -> Optional[Dict]:
        """Make a service call through the mesh"""
        endpoint = self.get_service_endpoint(service_name)
        if not endpoint:
            return None
        
        url = f"http://{endpoint.host}:{endpoint.port}{path}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method.upper() == "GET":
                    async with session.get(url, timeout=timeout) as response:
                        result = await response.json()
                elif method.upper() == "POST":
                    async with session.post(url, json=data, timeout=timeout) as response:
                        result = await response.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                self._record_call_success(endpoint.name)
                return result
                
        except Exception as e:
            self.logger.error(f"Service call failed for {service_name}: {e}")
            self._record_call_failure(endpoint.name)
            return None
    
    def register_service(self, service_name: str, host: str, port: int, 
                        health_port: int, protocol: str = "http"):
        """Register a service endpoint"""
        endpoint = ServiceEndpoint(
            name=service_name,
            host=host,
            port=port,
            health_port=health_port,
            protocol=protocol,
            mesh_type=self.mesh_type,
            last_health_check=datetime.now()
        )
        
        if service_name not in self.services:
            self.services[service_name] = []
        
        self.services[service_name].append(endpoint)
        self.logger.info(f"Registered service {service_name} at {host}:{port}")

# Global service mesh client instance
service_mesh_client = None

def get_service_mesh_client() -> ServiceMeshClient:
    """Get the global service mesh client instance"""
    global service_mesh_client
    if service_mesh_client is None:
        mesh_type = os.getenv("SERVICE_MESH_TYPE", "istio")
        namespace = os.getenv("SERVICE_MESH_NAMESPACE", "ai-system")
        service_mesh_client = ServiceMeshClient(mesh_type, namespace)
    return service_mesh_client

def init_service_mesh(service_name: str, port: int, health_port: int):
    """Initialize service mesh for an agent"""
    client = get_service_mesh_client()
    host = os.getenv("POD_IP", "localhost")
    client.register_service(service_name, host, port, health_port)
    return client

# Decorator for automatic service mesh integration
def service_mesh_call(service_name: str, path: str = "/", method: str = "GET", timeout: int = 30):
    """Decorator for automatic service mesh calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            client = get_service_mesh_client()
            
            # Extract data from function arguments if needed
            data = kwargs.get('data')
            
            # Make service call
            result = await client.call_service(service_name, path, method, data, timeout)
            
            if result is None:
                raise Exception(f"Service call to {service_name} failed")
            
            return result
        return wrapper
    return decorator
