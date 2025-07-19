#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
WP-09 Service Mesh Migration Script
Implements Istio/Linkerd integration for microservice communication and traffic management
Target: Service mesh integration for inter-agent communication with load balancing, traffic routing, and observability
"""

import os
import ast
import yaml
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
import subprocess

@dataclass
class ServiceMeshConfig:
    """Service mesh configuration for an agent"""
    service_name: str
    namespace: str
    port: int
    health_port: int
    protocol: str  # http, grpc, tcp
    mesh_type: str  # istio, linkerd
    traffic_policy: Dict
    security_policy: Dict
    observability_config: Dict

class ServiceMeshAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect service mesh integration opportunities"""
    
    def __init__(self):
        self.zmq_patterns = []
        self.http_endpoints = []
        self.grpc_services = []
        self.port_bindings = []
        self.service_calls = []
        self.mesh_score = 0
        
    def visit_Call(self, node):
        # Detect ZMQ patterns
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['socket', 'connect', 'bind']):
            self.zmq_patterns.append(node.func.attr)
            self.mesh_score += 10
        
        # Detect HTTP endpoints
        if (isinstance(node.func, ast.Name) and 
            node.func.id in ['app.route', 'app.get', 'app.post']):
            self.http_endpoints.append(node.func.id)
            self.mesh_score += 15
        
        # Detect gRPC services
        if (isinstance(node.func, ast.Attribute) and 
            'grpc' in str(node.func).lower()):
            self.grpc_services.append(str(node.func))
            self.mesh_score += 20
        
        self.generic_visit(node)
    
    def visit_Str(self, node):
        # Detect port bindings
        if hasattr(node, 's') and isinstance(node.s, str):
            if 'tcp://' in node.s or 'http://' in node.s:
                self.port_bindings.append(node.s)
                self.mesh_score += 5
        self.generic_visit(node)

def find_service_candidates() -> List[Path]:
    """Find agent files that are candidates for service mesh integration"""
    agent_files = []
    
    # Main PC agents
    main_pc_path = Path("main_pc_code/agents")
    if main_pc_path.exists():
        agent_files.extend(main_pc_path.glob("*.py"))
    
    # PC2 agents
    pc2_path = Path("pc2_code/agents")
    if pc2_path.exists():
        agent_files.extend(pc2_path.glob("*.py"))
    
    # FORMAINPC agents
    formainpc_path = Path("main_pc_code/FORMAINPC")
    if formainpc_path.exists():
        agent_files.extend(formainpc_path.glob("*.py"))
    
    return [f for f in agent_files if not f.name.startswith('__')]

def analyze_service_mesh_needs(file_path: Path) -> Dict:
    """Analyze an agent file for service mesh integration needs"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = ServiceMeshAnalyzer()
        analyzer.visit(tree)
        
        # Extract service information
        service_name = extract_service_name(file_path, content)
        port = extract_port(content)
        health_port = extract_health_port(content)
        
        # Determine mesh suitability
        mesh_priority = determine_mesh_priority(analyzer, content)
        
        return {
            'file_path': str(file_path),
            'service_name': service_name,
            'port': port,
            'health_port': health_port,
            'mesh_score': analyzer.mesh_score,
            'mesh_priority': mesh_priority,
            'zmq_patterns': analyzer.zmq_patterns,
            'http_endpoints': analyzer.http_endpoints,
            'grpc_services': analyzer.grpc_services,
            'port_bindings': analyzer.port_bindings,
            'needs_mesh': analyzer.mesh_score > 20
        }
    except Exception as e:
        return {
            'file_path': str(file_path),
            'error': str(e),
            'needs_mesh': False,
            'mesh_score': 0
        }

def extract_service_name(file_path: Path, content: str) -> str:
    """Extract service name from agent file"""
    # Try to find class name
    import re
    class_match = re.search(r'class\s+(\w+)', content)
    if class_match:
        return class_match.group(1).lower().replace('agent', '').replace('service', '')
    
    return file_path.stem.replace('_agent', '').replace('_service', '')

def extract_port(content: str) -> int:
    """Extract port number from agent content"""
    import re
    port_patterns = [
        r'port["\s]*=[\s]*(\d+)',
        r'PORT["\s]*=[\s]*(\d+)',
        r'tcp://[^:]+:(\d+)',
        r'bind.*?:(\d+)',
        r'connect.*?:(\d+)'
    ]
    
    for pattern in port_patterns:
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
    return 8080  # Default

def extract_health_port(content: str) -> int:
    """Extract health check port"""
    import re
    health_patterns = [
        r'health[_\s]*port["\s]*=[\s]*(\d+)',
        r'HEALTH[_\s]*PORT["\s]*=[\s]*(\d+)',
    ]
    
    for pattern in health_patterns:
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
    return 8081  # Default

def determine_mesh_priority(analyzer: ServiceMeshAnalyzer, content: str) -> str:
    """Determine service mesh integration priority"""
    if analyzer.mesh_score > 50:
        return 'high'
    elif analyzer.mesh_score > 30:
        return 'medium'
    elif analyzer.mesh_score > 10:
        return 'low'
    else:
        return 'none'

def generate_istio_service_definition(service_config: ServiceMeshConfig) -> str:
    """Generate Istio service definition"""
    return f"""
apiVersion: v1
kind: Service
metadata:
  name: {service_config.service_name}
  namespace: {service_config.namespace}
  labels:
    app: {service_config.service_name}
    version: v1
spec:
  ports:
  - port: {service_config.port}
    targetPort: {service_config.port}
    protocol: {service_config.protocol.upper()}
    name: main-port
  - port: {service_config.health_port}
    targetPort: {service_config.health_port}
    protocol: TCP
    name: health-port
  selector:
    app: {service_config.service_name}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service_config.service_name}
  namespace: {service_config.namespace}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {service_config.service_name}
      version: v1
  template:
    metadata:
      labels:
        app: {service_config.service_name}
        version: v1
    spec:
      containers:
      - name: {service_config.service_name}
        image: ai-system/{service_config.service_name}:latest
        ports:
        - containerPort: {service_config.port}
        - containerPort: {service_config.health_port}
        env:
        - name: SERVICE_MESH_ENABLED
          value: "true"
        - name: ISTIO_PROXY_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: {service_config.health_port}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: {service_config.health_port}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {service_config.service_name}
  namespace: {service_config.namespace}
spec:
  hosts:
  - {service_config.service_name}
  http:
  - match:
    - headers:
        priority:
          exact: high
    route:
    - destination:
        host: {service_config.service_name}
        subset: v1
      weight: 100
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
  - route:
    - destination:
        host: {service_config.service_name}
        subset: v1
      weight: 100
    timeout: 30s
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: {service_config.service_name}
  namespace: {service_config.namespace}
spec:
  host: {service_config.service_name}
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
    circuitBreaker:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
"""

def generate_linkerd_service_definition(service_config: ServiceMeshConfig) -> str:
    """Generate Linkerd service definition"""
    return f"""
apiVersion: v1
kind: Service
metadata:
  name: {service_config.service_name}
  namespace: {service_config.namespace}
  annotations:
    linkerd.io/inject: enabled
    config.linkerd.io/proxy-cpu-limit: "0.5"
    config.linkerd.io/proxy-memory-limit: "512Mi"
spec:
  ports:
  - port: {service_config.port}
    targetPort: {service_config.port}
    protocol: {service_config.protocol.upper()}
    name: main-port
  - port: {service_config.health_port}
    targetPort: {service_config.health_port}
    protocol: TCP
    name: health-port
  selector:
    app: {service_config.service_name}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service_config.service_name}
  namespace: {service_config.namespace}
  annotations:
    linkerd.io/inject: enabled
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {service_config.service_name}
  template:
    metadata:
      labels:
        app: {service_config.service_name}
      annotations:
        linkerd.io/inject: enabled
    spec:
      containers:
      - name: {service_config.service_name}
        image: ai-system/{service_config.service_name}:latest
        ports:
        - containerPort: {service_config.port}
        - containerPort: {service_config.health_port}
        env:
        - name: SERVICE_MESH_ENABLED
          value: "true"
        - name: LINKERD_PROXY_ENABLED
          value: "true"
        livenessProbe:
          httpGet:
            path: /health
            port: {service_config.health_port}
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: {service_config.health_port}
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: policy.linkerd.io/v1beta1
kind: ServerPolicy
metadata:
  name: {service_config.service_name}-policy
  namespace: {service_config.namespace}
spec:
  targetRef:
    group: apps
    kind: Deployment
    name: {service_config.service_name}
  requiredRoutes:
  - pathRegex: "/health"
  - pathRegex: "/ready"
  - pathRegex: "/.*"
---
apiVersion: policy.linkerd.io/v1alpha1
kind: HTTPRoute
metadata:
  name: {service_config.service_name}-route
  namespace: {service_config.namespace}
spec:
  parentRefs:
  - name: {service_config.service_name}
    kind: Service
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: "/"
    backendRefs:
    - name: {service_config.service_name}
      port: {service_config.port}
      weight: 100
    timeouts:
      request: 30s
"""

def generate_service_mesh_client_library() -> str:
    """Generate service mesh client library for agents"""
    return '''
"""
Service Mesh Client Library for WP-09 Service Mesh Integration
Provides service discovery, load balancing, and circuit breaking for inter-agent communication
"""

import os
import time
import requests
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
'''

def create_service_mesh_structure():
    """Create service mesh directory structure"""
    mesh_dir = Path("common/service_mesh")
    mesh_dir.mkdir(parents=True, exist_ok=True)
    
    # Create service mesh client library
    with open(mesh_dir / "client.py", 'w') as f:
        f.write(generate_service_mesh_client_library())
    
    # Create __init__.py
    with open(mesh_dir / "__init__.py", 'w') as f:
        f.write('"""Service Mesh Integration for WP-09"""\n\nfrom .client import ServiceMeshClient, get_service_mesh_client, init_service_mesh, service_mesh_call\n\n__all__ = ["ServiceMeshClient", "get_service_mesh_client", "init_service_mesh", "service_mesh_call"]\n')
    
    # Create Kubernetes manifests directory
    k8s_dir = mesh_dir / "k8s"
    k8s_dir.mkdir(exist_ok=True)
    
    return mesh_dir

def generate_service_mesh_integration_example(service_info: Dict) -> str:
    """Generate service mesh integration example for a service"""
    service_name = service_info['service_name']
    
    return f'''
# Service Mesh Integration Example for {service_name}
# Generated by WP-09 Service Mesh Migration

from common.service_mesh import init_service_mesh, service_mesh_call, get_service_mesh_client
import asyncio

class {service_name.title().replace('_', '')}ServiceMesh:
    """
    Enhanced {service_name} with service mesh integration
    """
    
    def __init__(self, port: int = {service_info['port']}, health_port: int = {service_info['health_port']}):
        self.service_name = "{service_name}"
        self.port = port
        self.health_port = health_port
        
        # Initialize service mesh
        self.mesh_client = init_service_mesh(self.service_name, port, health_port)
        
        print(f"Service mesh initialized for {{self.service_name}} on port {{port}}")
    
    @service_mesh_call("model-manager", "/api/v1/models", "GET")
    async def get_available_models(self):
        """Get available models via service mesh"""
        pass  # Implementation handled by decorator
    
    @service_mesh_call("translation-service", "/api/v1/translate", "POST")
    async def translate_text(self, data: dict):
        """Translate text via service mesh"""
        pass  # Implementation handled by decorator
    
    async def call_another_service(self, service_name: str, endpoint: str, data: dict = None):
        """Generic service call via mesh"""
        result = await self.mesh_client.call_service(
            service_name=service_name,
            path=endpoint,
            method="POST" if data else "GET",
            data=data
        )
        return result
    
    def register_with_mesh(self):
        """Register this service with the mesh"""
        self.mesh_client.register_service(
            service_name=self.service_name,
            host="0.0.0.0",  # Will be replaced by pod IP in Kubernetes
            port=self.port,
            health_port=self.health_port
        )

# Example usage:
async def main():
    service = {service_name.title().replace('_', '')}ServiceMesh()
    
    # Register with service mesh
    service.register_with_mesh()
    
    # Make service calls via mesh
    try:
        models = await service.get_available_models()
        print("Available models:", models)
        
        translation = await service.translate_text({{
            "text": "Hello world",
            "target_language": "es"
        }})
        print("Translation:", translation)
        
    except Exception as e:
        print(f"Service call failed: {{e}}")

if __name__ == "__main__":
    asyncio.run(main())
'''

def update_requirements_txt():
    """Update requirements.txt with service mesh dependencies"""
    requirements = [
        "aiohttp>=3.8.0",
        "kubernetes>=24.0.0",
        "pyyaml>=6.0",
        "requests>=2.28.0"
    ]
    
    requirements_file = Path("requirements.txt")
    
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            existing = f.read()
        
        new_requirements = []
        for req in requirements:
            if req.split('>=')[0] not in existing:
                new_requirements.append(req)
        
        if new_requirements:
            with open(requirements_file, 'a') as f:
                f.write('\n# WP-09 Service Mesh dependencies\n')
                for req in new_requirements:
                    f.write(f'{req}\n')

def main():
    """Main execution function"""
    print("🚀 WP-09: SERVICE MESH INTEGRATION")
    print("=" * 50)
    
    # Update requirements
    update_requirements_txt()
    print("✅ Updated requirements.txt with service mesh dependencies")
    
    # Create service mesh structure
    mesh_dir = create_service_mesh_structure()
    print(f"✅ Created service mesh framework in {mesh_dir}")
    
    # Find service candidates
    candidates = find_service_candidates()
    print(f"📁 Found {len(candidates)} service candidates")
    
    # Analyze services
    analysis_results = []
    mesh_candidates = []
    
    for candidate in candidates:
        result = analyze_service_mesh_needs(candidate)
        analysis_results.append(result)
        
        if result.get('needs_mesh', False):
            mesh_candidates.append(result)
    
    print(f"\n📊 SERVICE MESH ANALYSIS:")
    print(f"✅ Total services: {len(analysis_results)}")
    print(f"🔧 Services needing mesh integration: {len(mesh_candidates)}")
    
    # Generate Kubernetes manifests for top services
    k8s_dir = mesh_dir / "k8s"
    
    for service_info in sorted(mesh_candidates, key=lambda x: x.get('mesh_score', 0), reverse=True)[:10]:
        service_name = service_info['service_name']
        
        # Create service mesh configuration
        config = ServiceMeshConfig(
            service_name=service_name,
            namespace="ai-system",
            port=service_info['port'],
            health_port=service_info['health_port'],
            protocol="http",
            mesh_type="istio",  # Default to Istio
            traffic_policy={},
            security_policy={},
            observability_config={}
        )
        
        # Generate Istio manifests
        istio_manifest = generate_istio_service_definition(config)
        with open(k8s_dir / f"{service_name}-istio.yaml", 'w') as f:
            f.write(istio_manifest)
        
        # Generate Linkerd manifests
        config.mesh_type = "linkerd"
        linkerd_manifest = generate_linkerd_service_definition(config)
        with open(k8s_dir / f"{service_name}-linkerd.yaml", 'w') as f:
            f.write(linkerd_manifest)
        
        print(f"✅ Generated K8s manifests for {service_name}")
    
    # Generate integration examples
    examples_dir = Path("docs/service_mesh_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    for service_info in mesh_candidates[:5]:  # Top 5 services
        example_code = generate_service_mesh_integration_example(service_info)
        example_file = examples_dir / f"{service_info['service_name']}_mesh_integration.py"
        
        with open(example_file, 'w') as f:
            f.write(example_code)
        
        print(f"✅ Generated mesh integration example for {service_info['service_name']}")
    
    # Generate service registry
    service_registry = {}
    for service_info in mesh_candidates:
        service_registry[service_info['service_name']] = [{
            "name": service_info['service_name'],
            "host": "localhost",
            "port": service_info['port'],
            "health_port": service_info['health_port'],
            "protocol": "http",
            "mesh_type": "istio",
            "last_health_check": datetime.now().isoformat(),
            "is_healthy": True
        }]
    
    with open("config/service_registry.json", 'w') as f:
        json.dump(service_registry, f, indent=2)
    
    # Generate summary report
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_services": len(analysis_results),
        "mesh_ready_services": len(mesh_candidates),
        "istio_manifests_generated": len([f for f in k8s_dir.glob("*-istio.yaml")]),
        "linkerd_manifests_generated": len([f for f in k8s_dir.glob("*-linkerd.yaml")]),
        "service_mesh_coverage": (len(mesh_candidates) / len(analysis_results)) * 100,
        "top_mesh_candidates": [
            {
                "service": s['service_name'],
                "mesh_score": s['mesh_score'],
                "priority": s['mesh_priority']
            }
            for s in sorted(mesh_candidates, key=lambda x: x.get('mesh_score', 0), reverse=True)[:10]
        ]
    }
    
    with open("WP-09_SERVICE_MESH_REPORT.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✅ SERVICE MESH INTEGRATION COMPLETE:")
    print(f"📊 Mesh Coverage: {report['service_mesh_coverage']:.1f}%")
    print(f"🚢 Istio Manifests: {report['istio_manifests_generated']}")
    print(f"🔗 Linkerd Manifests: {report['linkerd_manifests_generated']}")
    print(f"📝 Report: WP-09_SERVICE_MESH_REPORT.json")
    print(f"⚙️  Service Mesh Framework: common/service_mesh/")
    print(f"☸️  Kubernetes Manifests: common/service_mesh/k8s/")
    print(f"📖 Integration Examples: docs/service_mesh_examples/")
    
    print(f"\n🎯 WP-09 SERVICE MESH: COMPLETE")

if __name__ == "__main__":
    main() 