#!/usr/bin/env python3
"""
Hostname Resolver Utility

Implements hostname-based service discovery for Docker deployment.
Part of Blueprint.md Step 6: Network Fixes.

This utility:
1. Resolves service names to IP addresses or hostnames
2. Provides Docker/Kubernetes service name resolution
3. Falls back to IP-based discovery for legacy support
4. Handles cross-machine communication patterns

Features:
- Docker service name resolution (e.g., "mainpc-service" → container IP)
- Kubernetes DNS resolution (e.g., "service.namespace.svc.cluster.local")
- Legacy IP fallback for non-containerized environments
- Environment-aware hostname resolution
- Caching for performance
"""

import os
import socket
import logging
import warnings
from typing import Dict, Optional, Tuple, List
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DiscoveryMode(Enum):
    """Service discovery mode"""
    DOCKER = "docker"
    KUBERNETES = "kubernetes" 
    LEGACY_IP = "legacy_ip"
    HYBRID = "hybrid"

@dataclass
class ServiceEndpoint:
    """Represents a service endpoint"""
    name: str
    hostname: str
    port: int
    ip: Optional[str] = None
    protocol: str = "tcp"
    machine: Optional[str] = None
    
    @property
    def address(self) -> str:
        """Get full service address"""
        host = self.ip if self.ip else self.hostname
        return f"{self.protocol}://{host}:{self.port}"
    
    @property
    def host_port(self) -> str:
        """Get host:port format"""
        host = self.ip if self.ip else self.hostname
        return f"{host}:{self.port}"

class HostnameResolver:
    """
    Hostname-based service resolver for Docker and Kubernetes deployments.
    """
    
    def __init__(self, discovery_mode: DiscoveryMode = None):
        """
        Initialize hostname resolver.
        
        Args:
            discovery_mode: Override discovery mode (auto-detected if None)
        """
        self.discovery_mode = discovery_mode or self._detect_discovery_mode()
        self._cache: Dict[str, ServiceEndpoint] = {}
        
        logger.info(f"HostnameResolver initialized with mode: {self.discovery_mode.value}")
    
    @staticmethod
    def _detect_discovery_mode() -> DiscoveryMode:
        """Auto-detect the appropriate discovery mode based on environment."""
        # Check for Kubernetes environment
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount'):
            return DiscoveryMode.KUBERNETES
        
        # Check for Docker environment
        if (os.path.exists('/.dockerenv') or 
            os.environ.get('CONTAINER_MODE', '').lower() in ('true', '1') or
            os.environ.get('DOCKER_MODE', '').lower() in ('true', '1')):
            return DiscoveryMode.DOCKER
        
        # Check for hybrid mode (Docker with external machines)
        mainpc_ip = os.environ.get('MAINPC_IP', '')
        pc2_ip = os.environ.get('PC2_IP', '')
        
        if (mainpc_ip not in ('localhost', '127.0.0.1') or 
            pc2_ip not in ('localhost', '127.0.0.1')):
            return DiscoveryMode.HYBRID
        
        # Default to legacy IP mode
        return DiscoveryMode.LEGACY_IP
    
    @lru_cache(maxsize=128)
    def resolve_service(self, service_name: str, machine: str = None, port: int = None) -> Optional[ServiceEndpoint]:
        """
        Resolve a service name to its endpoint.
        
        Args:
            service_name: Name of the service to resolve
            machine: Target machine (mainpc, pc2, or None for current)
            port: Service port (if not using default)
            
        Returns:
            ServiceEndpoint if resolved, None otherwise
        """
        cache_key = f"{service_name}:{machine}:{port}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try resolution based on discovery mode
        endpoint = None
        
        if self.discovery_mode == DiscoveryMode.DOCKER:
            endpoint = self._resolve_docker_service(service_name, machine, port)
        elif self.discovery_mode == DiscoveryMode.KUBERNETES:
            endpoint = self._resolve_k8s_service(service_name, machine, port)
        elif self.discovery_mode == DiscoveryMode.HYBRID:
            endpoint = self._resolve_hybrid_service(service_name, machine, port)
        else:  # LEGACY_IP
            endpoint = self._resolve_legacy_service(service_name, machine, port)
        
        # Cache successful resolution
        if endpoint:
            self._cache[cache_key] = endpoint
            logger.debug(f"Resolved {service_name} → {endpoint.address}")
        else:
            logger.warning(f"Failed to resolve service: {service_name}")
        
        return endpoint
    
    def _resolve_docker_service(self, service_name: str, machine: str = None, port: int = None) -> Optional[ServiceEndpoint]:
        """Resolve service in Docker environment."""
        # Docker service naming patterns
        hostname = self._get_docker_hostname(service_name, machine)
        
        # Try to resolve hostname
        try:
            ip = socket.gethostbyname(hostname)
            return ServiceEndpoint(
                name=service_name,
                hostname=hostname,
                port=port or self._get_default_port(service_name),
                ip=ip,
                machine=machine
            )
        except socket.gaierror:
            logger.debug(f"Failed to resolve Docker hostname: {hostname}")
            return None
    
    def _resolve_k8s_service(self, service_name: str, machine: str = None, port: int = None) -> Optional[ServiceEndpoint]:
        """Resolve service in Kubernetes environment."""
        # Kubernetes service naming patterns
        namespace = os.environ.get('K8S_NAMESPACE', 'default')
        cluster_domain = os.environ.get('K8S_CLUSTER_DOMAIN', 'cluster.local')
        
        # Try different hostname patterns
        hostnames = [
            f"{service_name}.{namespace}.svc.{cluster_domain}",
            f"{service_name}.{namespace}",
            f"{service_name}",
            self._get_docker_hostname(service_name, machine)  # Fallback to Docker pattern
        ]
        
        for hostname in hostnames:
            try:
                ip = socket.gethostbyname(hostname)
                return ServiceEndpoint(
                    name=service_name,
                    hostname=hostname,
                    port=port or self._get_default_port(service_name),
                    ip=ip,
                    machine=machine
                )
            except socket.gaierror:
                continue
        
        logger.debug(f"Failed to resolve K8s service: {service_name}")
        return None
    
    def _resolve_hybrid_service(self, service_name: str, machine: str = None, port: int = None) -> Optional[ServiceEndpoint]:
        """Resolve service in hybrid environment (Docker + external machines)."""
        # If machine is specified and it's external, use IP-based resolution
        if machine:
            machine_lower = machine.lower()
            if machine_lower == "mainpc":
                mainpc_ip = os.environ.get('MAINPC_IP', 'localhost')
                if mainpc_ip not in ('localhost', '127.0.0.1'):
                    return ServiceEndpoint(
                        name=service_name,
                        hostname=mainpc_ip,
                        port=port or self._get_default_port(service_name),
                        ip=mainpc_ip,
                        machine=machine
                    )
            elif machine_lower == "pc2":
                pc2_ip = os.environ.get('PC2_IP', 'localhost')
                if pc2_ip not in ('localhost', '127.0.0.1'):
                    return ServiceEndpoint(
                        name=service_name,
                        hostname=pc2_ip,
                        port=port or self._get_default_port(service_name),
                        ip=pc2_ip,
                        machine=machine
                    )
        
        # Otherwise, try Docker resolution first
        docker_endpoint = self._resolve_docker_service(service_name, machine, port)
        if docker_endpoint:
            return docker_endpoint
        
        # Fall back to legacy IP resolution
        return self._resolve_legacy_service(service_name, machine, port)
    
    def _resolve_legacy_service(self, service_name: str, machine: str = None, port: int = None) -> Optional[ServiceEndpoint]:
        """Resolve service using legacy IP-based approach."""
        hostname = "localhost"
        ip = "127.0.0.1"
        
        # Use machine-specific IPs if available
        if machine:
            machine_lower = machine.lower()
            if machine_lower == "mainpc":
                mainpc_ip = os.environ.get('MAINPC_IP', 'localhost')
                hostname = mainpc_ip
                ip = mainpc_ip if mainpc_ip != 'localhost' else '127.0.0.1'
            elif machine_lower == "pc2":
                pc2_ip = os.environ.get('PC2_IP', 'localhost')
                hostname = pc2_ip
                ip = pc2_ip if pc2_ip != 'localhost' else '127.0.0.1'
        
        return ServiceEndpoint(
            name=service_name,
            hostname=hostname,
            port=port or self._get_default_port(service_name),
            ip=ip,
            machine=machine
        )
    
    def _get_docker_hostname(self, service_name: str, machine: str = None) -> str:
        """Generate Docker hostname for a service."""
        # Docker service naming conventions
        service_base = service_name.lower().replace('_', '-').replace(' ', '-')
        
        if machine:
            machine_lower = machine.lower()
            if machine_lower == "mainpc":
                return f"mainpc-{service_base}"
            elif machine_lower == "pc2":
                return f"pc2-{service_base}"
        
        # Default Docker service names
        return service_base
    
    def _get_default_port(self, service_name: str) -> int:
        """Get default port for a service."""
        # Common service port mappings
        default_ports = {
            'systemdigitaltwin': 7120,
            'serviceregistry': 7100,
            'modelmanager': 5570,
            'taskrouter': 8571,
            'streamingttts': 5562,
            'coordinator': 8000,
            'memoryorchestrator': 5575,
            'translator': 5559,
            'authentication': 6120,
            'healthmonitor': 7200,
        }
        
        service_key = service_name.lower().replace('_', '').replace('-', '')
        return default_ports.get(service_key, 8080)  # Default fallback port
    
    def get_service_address(self, service_name: str, machine: str = None, port: int = None) -> Optional[str]:
        """
        Get full service address (tcp://host:port).
        
        Args:
            service_name: Name of the service
            machine: Target machine (mainpc, pc2, or None)
            port: Service port override
            
        Returns:
            Full service address or None if not resolved
        """
        endpoint = self.resolve_service(service_name, machine, port)
        return endpoint.address if endpoint else None
    
    def get_service_hostname(self, service_name: str, machine: str = None) -> Optional[str]:
        """
        Get service hostname (without port).
        
        Args:
            service_name: Name of the service
            machine: Target machine (mainpc, pc2, or None)
            
        Returns:
            Service hostname or None if not resolved
        """
        endpoint = self.resolve_service(service_name, machine)
        return endpoint.hostname if endpoint else None
    
    def validate_service_connectivity(self, service_name: str, machine: str = None, timeout: float = 5.0) -> bool:
        """
        Test connectivity to a service.
        
        Args:
            service_name: Name of the service to test
            machine: Target machine (mainpc, pc2, or None)
            timeout: Connection timeout in seconds
            
        Returns:
            True if service is reachable, False otherwise
        """
        endpoint = self.resolve_service(service_name, machine)
        if not endpoint:
            return False
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            host = endpoint.ip if endpoint.ip else endpoint.hostname
            result = sock.connect_ex((host, endpoint.port))
            sock.close()
            
            is_reachable = result == 0
            if is_reachable:
                logger.debug(f"Service {service_name} is reachable at {endpoint.address}")
            else:
                logger.debug(f"Service {service_name} is NOT reachable at {endpoint.address}")
            
            return is_reachable
        except Exception as e:
            logger.debug(f"Connectivity test failed for {service_name}: {e}")
            return False
    
    def list_resolvable_services(self) -> List[str]:
        """Get list of all services that can be resolved."""
        # This would typically query a service registry
        # For now, return common service names
        return [
            'SystemDigitalTwin',
            'ServiceRegistry', 
            'ModelManager',
            'TaskRouter',
            'StreamingTTS',
            'Coordinator',
            'MemoryOrchestrator',
            'Translator',
            'Authentication',
            'HealthMonitor'
        ]
    
    def clear_cache(self):
        """Clear the resolution cache."""
        self._cache.clear()
        # Clear the LRU cache as well
        self.resolve_service.cache_clear()
        logger.debug("Hostname resolution cache cleared")

# Global singleton instance
_hostname_resolver: Optional[HostnameResolver] = None

def get_hostname_resolver() -> HostnameResolver:
    """Get the global hostname resolver instance."""
    global _hostname_resolver
    if _hostname_resolver is None:
        _hostname_resolver = HostnameResolver()
    return _hostname_resolver

# Convenience functions
def resolve_service_hostname(service_name: str, machine: str = None) -> Optional[str]:
    """Resolve service to hostname."""
    return get_hostname_resolver().get_service_hostname(service_name, machine)

def resolve_service_address(service_name: str, machine: str = None, port: int = None) -> Optional[str]:
    """Resolve service to full address."""
    return get_hostname_resolver().get_service_address(service_name, machine, port)

def validate_service_reachable(service_name: str, machine: str = None, timeout: float = 5.0) -> bool:
    """Test if service is reachable."""
    return get_hostname_resolver().validate_service_connectivity(service_name, machine, timeout)

def is_docker_environment() -> bool:
    """Check if running in Docker environment."""
    resolver = get_hostname_resolver()
    return resolver.discovery_mode in (DiscoveryMode.DOCKER, DiscoveryMode.KUBERNETES)

def get_discovery_mode() -> DiscoveryMode:
    """Get current discovery mode."""
    return get_hostname_resolver().discovery_mode 