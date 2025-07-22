#!/usr/bin/env python3
"""
PHASE 1 WEEK 2 DAY 5: Advanced Service Discovery System
Enhanced inter-agent communication and capability registration
"""

import json
import time
import threading
import zmq
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentCapability:
    """Define agent capability for service discovery"""
    capability_id: str
    capability_type: str  # 'processing', 'data', 'communication', 'monitoring'
    description: str
    input_formats: List[str]
    output_formats: List[str]
    performance_metrics: Dict[str, Any]
    availability: bool = True
    last_heartbeat: float = 0.0

@dataclass
class ServiceEndpoint:
    """Service endpoint information"""
    agent_name: str
    endpoint_url: str
    port: int
    protocol: str  # 'zmq', 'http', 'websocket'
    capabilities: List[str]
    health_status: str = 'healthy'
    last_seen: float = 0.0

@dataclass
class ServiceDependency:
    """Service dependency definition"""
    dependent_agent: str
    required_capability: str
    dependency_type: str  # 'required', 'optional', 'fallback'
    timeout_seconds: int = 30

class AdvancedServiceDiscovery:
    """
    Advanced Service Discovery System for Enhanced BaseAgent
    - Automatic capability registration and discovery
    - Real-time health monitoring and failover
    - Performance-based service selection
    - Dynamic load balancing
    """
    
    def __init__(self, registry_port: int = 8900):
        self.registry_port = registry_port
        self.running = False
        
        # Service registry storage
        self.registered_agents: Dict[str, ServiceEndpoint] = {}
        self.agent_capabilities: Dict[str, List[AgentCapability]] = {}
        self.service_dependencies: Dict[str, List[ServiceDependency]] = {}
        
        # Performance tracking
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.load_balancing_stats: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self.registry_lock = threading.RLock()
        self.discovery_thread = None
        self.health_monitor_thread = None
        
        # ZMQ setup for service communication
        self.context = zmq.Context()
        self.registry_socket = None
        
        # Event callbacks
        self.event_callbacks: Dict[str, List[Callable]] = {
            'agent_registered': [],
            'agent_deregistered': [],
            'capability_added': [],
            'health_changed': [],
            'dependency_resolved': []
        }
    
    def start(self):
        """Start the advanced service discovery system"""
        if self.running:
            return
        
        self.running = True
        
        # Setup ZMQ registry socket
        self.registry_socket = self.context.socket(zmq.REP)
        self.registry_socket.bind(f"tcp://*:{self.registry_port}")
        
        # Start discovery and health monitoring threads
        self.discovery_thread = threading.Thread(target=self._run_discovery_server, daemon=True)
        self.health_monitor_thread = threading.Thread(target=self._run_health_monitor, daemon=True)
        
        self.discovery_thread.start()
        self.health_monitor_thread.start()
        
        logger.info(f"Advanced Service Discovery started on port {self.registry_port}")
    
    def stop(self):
        """Stop the service discovery system"""
        self.running = False
        
        if self.registry_socket:
            self.registry_socket.close()
        
        if self.discovery_thread:
            self.discovery_thread.join(timeout=1.0)
        
        if self.health_monitor_thread:
            self.health_monitor_thread.join(timeout=1.0)
        
        logger.info("Advanced Service Discovery stopped")
    
    def register_agent(self, agent_name: str, endpoint_url: str, port: int, 
                      capabilities: List[AgentCapability], protocol: str = 'zmq') -> bool:
        """Register agent with advanced capabilities"""
        with self.registry_lock:
            try:
                # Create service endpoint
                endpoint = ServiceEndpoint(
                    agent_name=agent_name,
                    endpoint_url=endpoint_url,
                    port=port,
                    protocol=protocol,
                    capabilities=[cap.capability_id for cap in capabilities],
                    health_status='healthy',
                    last_seen=time.time()
                )
                
                # Register agent and capabilities
                self.registered_agents[agent_name] = endpoint
                self.agent_capabilities[agent_name] = capabilities
                
                # Initialize performance tracking
                self.performance_history[agent_name] = []
                self.load_balancing_stats[agent_name] = {
                    'request_count': 0,
                    'average_response_time': 0.0,
                    'success_rate': 1.0,
                    'load_score': 0.0
                }
                
                # Trigger event callbacks
                self._trigger_event('agent_registered', {
                    'agent_name': agent_name,
                    'capabilities': [cap.capability_id for cap in capabilities],
                    'timestamp': time.time()
                })
                
                logger.info(f"Agent {agent_name} registered with {len(capabilities)} capabilities")
                return True
                
            except Exception as e:
                logger.error(f"Failed to register agent {agent_name}: {e}")
                return False
    
    def discover_service(self, required_capability: str, 
                        performance_requirements: Optional[Dict[str, Any]] = None) -> Optional[ServiceEndpoint]:
        """Discover best service for required capability"""
        with self.registry_lock:
            candidate_agents = []
            
            # Find agents with required capability
            for agent_name, capabilities in self.agent_capabilities.items():
                for capability in capabilities:
                    if capability.capability_id == required_capability and capability.availability:
                        # Check if agent is healthy and reachable
                        endpoint = self.registered_agents.get(agent_name)
                        if endpoint and endpoint.health_status == 'healthy':
                            candidate_agents.append((agent_name, capability, endpoint))
            
            if not candidate_agents:
                logger.warning(f"No available agents found for capability: {required_capability}")
                return None
            
            # Performance-based selection
            best_agent = self._select_best_agent(candidate_agents, performance_requirements)
            
            if best_agent:
                agent_name, capability, endpoint = best_agent
                logger.info(f"Selected agent {agent_name} for capability {required_capability}")
                return endpoint
            
            return None
    
    def _select_best_agent(self, candidates: List[tuple], 
                          performance_requirements: Optional[Dict[str, Any]] = None) -> Optional[tuple]:
        """Select best agent based on performance and load"""
        if not candidates:
            return None
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Score each candidate
        scored_candidates = []
        
        for agent_name, capability, endpoint in candidates:
            score = self._calculate_agent_score(agent_name, capability, performance_requirements)
            scored_candidates.append((score, agent_name, capability, endpoint))
        
        # Return highest scoring agent
        scored_candidates.sort(reverse=True, key=lambda x: x[0])
        best_score, agent_name, capability, endpoint = scored_candidates[0]
        
        return (agent_name, capability, endpoint)
    
    def _calculate_agent_score(self, agent_name: str, capability: AgentCapability,
                              performance_requirements: Optional[Dict[str, Any]] = None) -> float:
        """Calculate agent selection score based on performance metrics"""
        base_score = 1.0
        
        # Load balancing factor
        load_stats = self.load_balancing_stats.get(agent_name, {})
        load_factor = max(0.1, 1.0 - load_stats.get('load_score', 0.0))
        
        # Success rate factor
        success_rate = load_stats.get('success_rate', 1.0)
        
        # Response time factor (lower is better)
        avg_response_time = load_stats.get('average_response_time', 0.1)
        response_time_factor = max(0.1, 1.0 / (1.0 + avg_response_time))
        
        # Capability performance metrics
        capability_score = 1.0
        if hasattr(capability, 'performance_metrics'):
            perf_metrics = capability.performance_metrics
            if 'efficiency_score' in perf_metrics:
                capability_score = perf_metrics['efficiency_score']
        
        # Calculate final score
        final_score = base_score * load_factor * success_rate * response_time_factor * capability_score
        
        # Apply performance requirements if specified
        if performance_requirements:
            req_factor = self._evaluate_performance_requirements(capability, performance_requirements)
            final_score *= req_factor
        
        return final_score
    
    def _evaluate_performance_requirements(self, capability: AgentCapability,
                                         requirements: Dict[str, Any]) -> float:
        """Evaluate how well capability meets performance requirements"""
        if not hasattr(capability, 'performance_metrics'):
            return 0.5  # Unknown performance, moderate score
        
        metrics = capability.performance_metrics
        requirement_score = 1.0
        
        # Check specific requirements
        for req_key, req_value in requirements.items():
            if req_key in metrics:
                metric_value = metrics[req_key]
                if isinstance(req_value, (int, float)) and isinstance(metric_value, (int, float)):
                    # For numeric requirements, calculate satisfaction ratio
                    if req_key in ['max_latency', 'max_response_time']:
                        # Lower is better
                        if metric_value <= req_value:
                            requirement_score *= 1.0
                        else:
                            requirement_score *= max(0.1, req_value / metric_value)
                    else:
                        # Higher is better (throughput, accuracy, etc.)
                        if metric_value >= req_value:
                            requirement_score *= 1.0
                        else:
                            requirement_score *= max(0.1, metric_value / req_value)
        
        return requirement_score
    
    def add_dependency(self, dependent_agent: str, required_capability: str,
                      dependency_type: str = 'required', timeout_seconds: int = 30):
        """Add service dependency for automatic resolution"""
        with self.registry_lock:
            if dependent_agent not in self.service_dependencies:
                self.service_dependencies[dependent_agent] = []
            
            dependency = ServiceDependency(
                dependent_agent=dependent_agent,
                required_capability=required_capability,
                dependency_type=dependency_type,
                timeout_seconds=timeout_seconds
            )
            
            self.service_dependencies[dependent_agent].append(dependency)
            logger.info(f"Added {dependency_type} dependency for {dependent_agent}: {required_capability}")
    
    def resolve_dependencies(self, agent_name: str) -> Dict[str, Optional[ServiceEndpoint]]:
        """Resolve all dependencies for an agent"""
        resolved_dependencies = {}
        
        dependencies = self.service_dependencies.get(agent_name, [])
        
        for dependency in dependencies:
            endpoint = self.discover_service(dependency.required_capability)
            resolved_dependencies[dependency.required_capability] = endpoint
            
            if endpoint:
                self._trigger_event('dependency_resolved', {
                    'dependent_agent': agent_name,
                    'capability': dependency.required_capability,
                    'resolved_to': endpoint.agent_name,
                    'timestamp': time.time()
                })
            elif dependency.dependency_type == 'required':
                logger.warning(f"Failed to resolve required dependency {dependency.required_capability} for {agent_name}")
        
        return resolved_dependencies
    
    def update_performance_metrics(self, agent_name: str, capability_id: str,
                                 metrics: Dict[str, Any]):
        """Update performance metrics for agent capability"""
        with self.registry_lock:
            if agent_name in self.agent_capabilities:
                for capability in self.agent_capabilities[agent_name]:
                    if capability.capability_id == capability_id:
                        capability.performance_metrics.update(metrics)
                        
                        # Update load balancing stats
                        if agent_name not in self.performance_history:
                            self.performance_history[agent_name] = []
                        
                        self.performance_history[agent_name].append({
                            'timestamp': time.time(),
                            'capability_id': capability_id,
                            'metrics': metrics.copy()
                        })
                        
                        # Keep only recent history (last 100 entries)
                        if len(self.performance_history[agent_name]) > 100:
                            self.performance_history[agent_name] = self.performance_history[agent_name][-100:]
                        
                        break
    
    def get_system_topology(self) -> Dict[str, Any]:
        """Get complete system topology and service map"""
        with self.registry_lock:
            topology = {
                'timestamp': time.time(),
                'total_agents': len(self.registered_agents),
                'total_capabilities': sum(len(caps) for caps in self.agent_capabilities.values()),
                'agents': {},
                'capability_map': {},
                'dependency_graph': self.service_dependencies.copy()
            }
            
            # Agent details
            for agent_name, endpoint in self.registered_agents.items():
                capabilities = self.agent_capabilities.get(agent_name, [])
                topology['agents'][agent_name] = {
                    'endpoint': asdict(endpoint),
                    'capabilities': [asdict(cap) for cap in capabilities],
                    'performance_stats': self.load_balancing_stats.get(agent_name, {}),
                    'recent_performance': self.performance_history.get(agent_name, [])[-10:]  # Last 10 entries
                }
            
            # Capability map (which agents provide which capabilities)
            for agent_name, capabilities in self.agent_capabilities.items():
                for capability in capabilities:
                    cap_id = capability.capability_id
                    if cap_id not in topology['capability_map']:
                        topology['capability_map'][cap_id] = []
                    topology['capability_map'][cap_id].append({
                        'agent_name': agent_name,
                        'capability_type': capability.capability_type,
                        'availability': capability.availability,
                        'performance_score': self._calculate_agent_score(agent_name, capability)
                    })
            
            return topology
    
    def _run_discovery_server(self):
        """Run the discovery server to handle registration requests"""
        while self.running:
            try:
                if self.registry_socket.poll(timeout=1000):  # 1 second timeout
                    message = self.registry_socket.recv_json(zmq.NOBLOCK)
                    response = self._handle_discovery_request(message)
                    self.registry_socket.send_json(response)
            except zmq.Again:
                continue
            except Exception as e:
                logger.error(f"Discovery server error: {e}")
                time.sleep(0.1)
    
    def _handle_discovery_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle discovery protocol requests"""
        try:
            request_type = request.get('type', '')
            
            if request_type == 'register':
                # Handle agent registration
                agent_name = request['agent_name']
                capabilities_data = request['capabilities']
                
                capabilities = [AgentCapability(**cap_data) for cap_data in capabilities_data]
                success = self.register_agent(
                    agent_name=agent_name,
                    endpoint_url=request['endpoint_url'],
                    port=request['port'],
                    capabilities=capabilities,
                    protocol=request.get('protocol', 'zmq')
                )
                
                return {'status': 'success' if success else 'error', 'registered': success}
            
            elif request_type == 'discover':
                # Handle service discovery
                capability = request['capability']
                requirements = request.get('performance_requirements')
                
                endpoint = self.discover_service(capability, requirements)
                
                if endpoint:
                    return {'status': 'success', 'endpoint': asdict(endpoint)}
                else:
                    return {'status': 'not_found', 'endpoint': None}
            
            elif request_type == 'topology':
                # Handle topology request
                topology = self.get_system_topology()
                return {'status': 'success', 'topology': topology}
            
            else:
                return {'status': 'error', 'message': f'Unknown request type: {request_type}'}
        
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _run_health_monitor(self):
        """Monitor agent health and update availability"""
        while self.running:
            try:
                current_time = time.time()
                stale_threshold = 60.0  # 60 seconds
                
                with self.registry_lock:
                    for agent_name, endpoint in list(self.registered_agents.items()):
                        # Check if agent is stale
                        if current_time - endpoint.last_seen > stale_threshold:
                            old_status = endpoint.health_status
                            endpoint.health_status = 'stale'
                            
                            if old_status != 'stale':
                                logger.warning(f"Agent {agent_name} marked as stale")
                                self._trigger_event('health_changed', {
                                    'agent_name': agent_name,
                                    'old_status': old_status,
                                    'new_status': 'stale',
                                    'timestamp': current_time
                                })
                        
                        # Update capability availability based on health
                        if agent_name in self.agent_capabilities:
                            for capability in self.agent_capabilities[agent_name]:
                                capability.availability = (endpoint.health_status == 'healthy')
                
                time.sleep(30.0)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                time.sleep(5.0)
    
    def _trigger_event(self, event_type: str, event_data: Dict[str, Any]):
        """Trigger event callbacks"""
        callbacks = self.event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Event callback error for {event_type}: {e}")
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """Add event callback for service discovery events"""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    def remove_event_callback(self, event_type: str, callback: Callable):
        """Remove event callback"""
        if event_type in self.event_callbacks and callback in self.event_callbacks[event_type]:
            self.event_callbacks[event_type].remove(callback)


class ServiceDiscoveryClient:
    """Client for connecting to Advanced Service Discovery"""
    
    def __init__(self, registry_host: str = 'localhost', registry_port: int = 8900):
        self.registry_host = registry_host
        self.registry_port = registry_port
        self.context = zmq.Context()
        self.socket = None
    
    def connect(self):
        """Connect to service discovery registry"""
        if not self.socket:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(f"tcp://{self.registry_host}:{self.registry_port}")
    
    def disconnect(self):
        """Disconnect from service discovery registry"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def register_agent(self, agent_name: str, endpoint_url: str, port: int,
                      capabilities: List[AgentCapability], protocol: str = 'zmq') -> bool:
        """Register agent with service discovery"""
        self.connect()
        
        request = {
            'type': 'register',
            'agent_name': agent_name,
            'endpoint_url': endpoint_url,
            'port': port,
            'protocol': protocol,
            'capabilities': [asdict(cap) for cap in capabilities]
        }
        
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            return response.get('status') == 'success'
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False
    
    def discover_service(self, capability: str, 
                        performance_requirements: Optional[Dict[str, Any]] = None) -> Optional[ServiceEndpoint]:
        """Discover service for capability"""
        self.connect()
        
        request = {
            'type': 'discover',
            'capability': capability,
            'performance_requirements': performance_requirements
        }
        
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            
            if response.get('status') == 'success' and response.get('endpoint'):
                endpoint_data = response['endpoint']
                return ServiceEndpoint(**endpoint_data)
            
            return None
        except Exception as e:
            logger.error(f"Failed to discover service: {e}")
            return None
    
    def get_system_topology(self) -> Optional[Dict[str, Any]]:
        """Get system topology"""
        self.connect()
        
        request = {'type': 'topology'}
        
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            
            if response.get('status') == 'success':
                return response.get('topology')
            
            return None
        except Exception as e:
            logger.error(f"Failed to get topology: {e}")
            return None


# Global service discovery instance
_global_service_discovery = None

def get_service_discovery(registry_port: int = 8900) -> AdvancedServiceDiscovery:
    """Get global service discovery instance"""
    global _global_service_discovery
    if _global_service_discovery is None:
        _global_service_discovery = AdvancedServiceDiscovery(registry_port)
    return _global_service_discovery

def get_service_discovery_client(registry_host: str = 'localhost', 
                                registry_port: int = 8900) -> ServiceDiscoveryClient:
    """Get service discovery client"""
    return ServiceDiscoveryClient(registry_host, registry_port) 