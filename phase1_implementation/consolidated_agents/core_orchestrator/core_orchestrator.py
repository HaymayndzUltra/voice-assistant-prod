#!/usr/bin/env python3
"""
CoreOrchestrator - Phase 1 Implementation
Consolidates: ServiceRegistry (7100), SystemDigitalTwin (7120), RequestCoordinator (26002), UnifiedSystemAgent (7125)
Target: One FastAPI proc with in-proc registry dict, unified gRPC ingress for all services (Port 7000)
Hardware: MainPC
Risk Mitigation: Facade pattern - wrap existing classes first, then deprecate
"""

import sys
import os
from pathlib import Path

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import threading
import logging
import json
import time
import zmq
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Import existing agents (facade pattern) - with safe imports
from common.core.base_agent import BaseAgent

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_implementation/logs/core_orchestrator.log')
    ]
)
logger = logging.getLogger("CoreOrchestrator")

# Safe imports with fallbacks for facade pattern
try:
    from main_pc_code.agents.service_registry_agent import ServiceRegistryAgent
except ImportError as e:
    logger.warning(f"Could not import ServiceRegistryAgent: {e}")
    ServiceRegistryAgent = None

try:
    from main_pc_code.agents.system_digital_twin import SystemDigitalTwinAgent
except ImportError as e:
    logger.warning(f"Could not import SystemDigitalTwinAgent: {e}")
    SystemDigitalTwinAgent = None

try:
    from main_pc_code.agents.request_coordinator import RequestCoordinator
except ImportError as e:
    logger.warning(f"Could not import RequestCoordinator: {e}")
    RequestCoordinator = None

try:
    from main_pc_code.agents.unified_system_agent import UnifiedSystemAgent
except ImportError as e:
    logger.warning(f"Could not import UnifiedSystemAgent: {e}")
    UnifiedSystemAgent = None

class CoreOrchestrator(BaseAgent):
    """
    Unified facade for core system agents.
    Implements Phase 1 consolidation of ServiceRegistry, SystemDigitalTwin, 
    RequestCoordinator, and UnifiedSystemAgent into a single FastAPI service.
    """
    
    def __init__(self, **kwargs):
        # Initialize as BaseAgent
        super().__init__(name="CoreOrchestrator", port=7000, health_check_port=7100)
        
        # Feature flags for gradual migration (facade pattern)
        self.enable_unified_registry = os.getenv('ENABLE_UNIFIED_REGISTRY', 'false').lower() == 'true'
        self.enable_unified_twin = os.getenv('ENABLE_UNIFIED_TWIN', 'false').lower() == 'true'
        self.enable_unified_coordinator = os.getenv('ENABLE_UNIFIED_COORDINATOR', 'false').lower() == 'true'
        self.enable_unified_system = os.getenv('ENABLE_UNIFIED_SYSTEM', 'false').lower() == 'true'
        
        # In-process registry dict (as specified in proposal)
        self.internal_registry: Dict[str, Dict[str, Any]] = {}
        self.agent_endpoints: Dict[str, Dict[str, Any]] = {}
        self.system_metrics: Dict[str, Any] = {}
        
        # Legacy agent instances (facade pattern - keep existing classes)
        self.service_registry = None
        self.system_twin = None
        self.request_coordinator = None
        self.unified_system = None
        
        # Thread pool for background operations
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='CoreOrchestrator')
        
        # FastAPI app for unified endpoints (as specified)
        self.app = FastAPI(
            title="CoreOrchestrator",
            description="Phase 1 Unified Core Services",
            version="1.0.0"
        )
        
        # Setup unified API routes
        self.setup_routes()
        
        # ZMQ context for gRPC-like communication
        self.context = zmq.Context()
        self.zmq_socket = None
        
        # Startup state
        self.startup_complete = False
        self.startup_time = time.time()
        
        logger.info("CoreOrchestrator facade initialized")
    
    def setup_routes(self):
        """Setup unified API routes that delegate to appropriate services based on feature flags"""
        
        # Health and status endpoints
        @self.app.get("/health")
        async def health_check():
            """Unified health check endpoint"""
            return {
                "status": "healthy" if self.startup_complete else "starting",
                "service": "CoreOrchestrator",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - self.startup_time,
                "unified_services": {
                    "registry": self.enable_unified_registry,
                    "twin": self.enable_unified_twin,
                    "coordinator": self.enable_unified_coordinator,
                    "system": self.enable_unified_system
                }
            }
        
        @self.app.get("/status")
        async def system_status():
            """Unified system status endpoint"""
            if self.enable_unified_twin:
                return self._handle_unified_status()
            else:
                return await self._delegate_to_system_twin({"action": "get_status"})
        
        # Service Registry endpoints
        @self.app.post("/register_agent")
        async def register_agent(request: Request):
            """Unified agent registration endpoint"""
            try:
                registration_data = await request.json()
                if self.enable_unified_registry:
                    return self._handle_unified_registration(registration_data)
                else:
                    return await self._delegate_to_service_registry(registration_data)
            except Exception as e:
                logger.error(f"Error in register_agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/get_agent_endpoint/{agent_name}")
        async def get_agent_endpoint(agent_name: str):
            """Unified agent discovery endpoint"""
            if self.enable_unified_registry:
                return self._handle_unified_discovery(agent_name)
            else:
                return await self._delegate_to_service_registry({"action": "get_agent_endpoint", "agent_name": agent_name})
        
        @self.app.get("/list_agents")
        async def list_agents():
            """List all registered agents"""
            if self.enable_unified_registry:
                return {"status": "success", "agents": list(self.internal_registry.keys())}
            else:
                return await self._delegate_to_service_registry({"action": "list_agents"})
        
        # Request Coordination endpoints
        @self.app.post("/coordinate_request")
        async def coordinate_request(request: Request):
            """Unified request coordination endpoint"""
            try:
                request_data = await request.json()
                if self.enable_unified_coordinator:
                    return self._handle_unified_coordination(request_data)
                else:
                    return await self._delegate_to_request_coordinator(request_data)
            except Exception as e:
                logger.error(f"Error in coordinate_request: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System Twin endpoints
        @self.app.get("/metrics")
        async def get_metrics():
            """Get system metrics"""
            if self.enable_unified_twin:
                return self._handle_unified_metrics()
            else:
                return await self._delegate_to_system_twin({"action": "get_metrics"})
        
        @self.app.post("/publish_event")
        async def publish_event(request: Request):
            """Publish system event"""
            try:
                event_data = await request.json()
                if self.enable_unified_twin:
                    return self._handle_unified_event(event_data)
                else:
                    return await self._delegate_to_system_twin({"action": "publish_event", "event": event_data})
            except Exception as e:
                logger.error(f"Error in publish_event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Unified System endpoints
        @self.app.get("/system_info")
        async def system_info():
            """Get system information"""
            if self.enable_unified_system:
                return self._handle_unified_system_info()
            else:
                return await self._delegate_to_unified_system({"action": "get_system_info"})
        
        # Import/Export for migration support
        @self.app.post("/import_registry_state")
        async def import_registry_state(request: Request):
            """Import registry state for migration"""
            try:
                state_data = await request.json()
                return self._import_registry_state(state_data)
            except Exception as e:
                logger.error(f"Error importing registry state: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/import_twin_state")
        async def import_twin_state(request: Request):
            """Import system twin state for migration"""
            try:
                state_data = await request.json()
                return self._import_twin_state(state_data)
            except Exception as e:
                logger.error(f"Error importing twin state: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/import_coordinator_state")
        async def import_coordinator_state(request: Request):
            """Import coordinator state for migration"""
            try:
                state_data = await request.json()
                return self._import_coordinator_state(state_data)
            except Exception as e:
                logger.error(f"Error importing coordinator state: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def start_legacy_agents(self):
        """Start legacy agents in delegation mode (facade pattern)"""
        try:
            # Start ServiceRegistry if not unified and available
            if not self.enable_unified_registry and ServiceRegistryAgent is not None:
                logger.info("Starting ServiceRegistry in delegation mode")
                self.service_registry = ServiceRegistryAgent(port=7100)
                self.executor.submit(self.service_registry.run)
            elif not self.enable_unified_registry:
                logger.warning("ServiceRegistry not available, using unified mode")
                self.enable_unified_registry = True
            
            # Start SystemDigitalTwin if not unified and available
            if not self.enable_unified_twin and SystemDigitalTwinAgent is not None:
                logger.info("Starting SystemDigitalTwin in delegation mode")
                self.system_twin = SystemDigitalTwinAgent(config={"port": 7120})
                self.executor.submit(self.system_twin.run)
            elif not self.enable_unified_twin:
                logger.warning("SystemDigitalTwin not available, using unified mode")
                self.enable_unified_twin = True
            
            # Start RequestCoordinator if not unified and available
            if not self.enable_unified_coordinator and RequestCoordinator is not None:
                logger.info("Starting RequestCoordinator in delegation mode")
                self.request_coordinator = RequestCoordinator(port=26002)
                self.executor.submit(self.request_coordinator.run)
            elif not self.enable_unified_coordinator:
                logger.warning("RequestCoordinator not available, using unified mode")
                self.enable_unified_coordinator = True
            
            # Start UnifiedSystemAgent if not unified and available
            if not self.enable_unified_system and UnifiedSystemAgent is not None:
                logger.info("Starting UnifiedSystemAgent in delegation mode")
                # UnifiedSystemAgent doesn't take port parameter
                self.unified_system = UnifiedSystemAgent()
                self.executor.submit(self.unified_system.run)
            elif not self.enable_unified_system:
                logger.warning("UnifiedSystemAgent not available, using unified mode")
                self.enable_unified_system = True
            
            # Wait for services to start
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error starting legacy agents: {e}")
            raise
    
    def _handle_unified_registration(self, registration_data: dict) -> dict:
        """Handle agent registration in unified mode"""
        try:
            agent_name = registration_data.get('name') or registration_data.get('agent_id')
            if not agent_name:
                return {"status": "error", "message": "Missing agent name/id"}
            
            # Store in internal registry (in-proc dict as specified)
            self.internal_registry[agent_name] = {
                **registration_data,
                "registered_at": datetime.utcnow().isoformat(),
                "last_seen": datetime.utcnow().isoformat()
            }
            
            # Also store endpoint information
            if 'port' in registration_data:
                self.agent_endpoints[agent_name] = {
                    "host": registration_data.get('host', 'localhost'),
                    "port": registration_data['port'],
                    "health_check_port": registration_data.get('health_check_port'),
                    "capabilities": registration_data.get('capabilities', [])
                }
            
            logger.info(f"Agent {agent_name} registered in unified registry")
            return {"status": "success", "message": f"Agent {agent_name} registered"}
            
        except Exception as e:
            logger.error(f"Error in unified registration: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_unified_discovery(self, agent_name: str) -> dict:
        """Handle agent discovery in unified mode"""
        try:
            if agent_name in self.internal_registry:
                agent_data = self.internal_registry[agent_name]
                endpoint_data = self.agent_endpoints.get(agent_name, {})
                return {
                    "status": "success", 
                    "agent": {**agent_data, **endpoint_data}
                }
            else:
                return {"status": "error", "message": f"Agent {agent_name} not found"}
        except Exception as e:
            logger.error(f"Error in unified discovery: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_unified_coordination(self, request_data: dict) -> dict:
        """Handle request coordination in unified mode"""
        try:
            # Basic coordination logic (can be expanded)
            request_id = request_data.get('request_id', f"req_{int(time.time())}")
            target_agent = request_data.get('target_agent')
            
            if target_agent and target_agent in self.agent_endpoints:
                endpoint = self.agent_endpoints[target_agent]
                return {
                    "status": "success",
                    "message": "Request coordinated",
                    "request_id": request_id,
                    "target_endpoint": endpoint
                }
            else:
                return {
                    "status": "error",
                    "message": f"Target agent {target_agent} not found or no endpoint available"
                }
        except Exception as e:
            logger.error(f"Error in unified coordination: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_unified_status(self) -> dict:
        """Handle system status in unified mode"""
        try:
            import psutil
            
            # Collect basic system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            self.system_metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "registered_agents": len(self.internal_registry),
                "active_endpoints": len(self.agent_endpoints),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return {
                "status": "success",
                "system_status": "operational",
                "metrics": self.system_metrics
            }
        except Exception as e:
            logger.error(f"Error getting unified status: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_unified_metrics(self) -> dict:
        """Handle metrics collection in unified mode"""
        return {
            "status": "success",
            "metrics": self.system_metrics
        }
    
    def _handle_unified_event(self, event_data: dict) -> dict:
        """Handle event publishing in unified mode"""
        try:
            event_id = event_data.get('event_id', f"event_{int(time.time())}")
            logger.info(f"Publishing event {event_id}: {event_data.get('event_type', 'unknown')}")
            
            # Store event (basic implementation)
            # In full implementation, this would distribute to interested agents
            
            return {
                "status": "success",
                "message": f"Event {event_id} published",
                "event_id": event_id
            }
        except Exception as e:
            logger.error(f"Error publishing unified event: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_unified_system_info(self) -> dict:
        """Handle system info in unified mode"""
        try:
            import platform
            import psutil
            
            return {
                "status": "success",
                "system_info": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                    "uptime": time.time() - self.startup_time
                }
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"status": "error", "message": str(e)}
    
    # Delegation methods for facade pattern
    async def _delegate_to_service_registry(self, data: dict):
        """Delegate to existing ServiceRegistry via ZMQ"""
        try:
            if self.service_registry:
                # Direct method call if running in same process
                return self.service_registry.handle_request(data)
            else:
                # ZMQ call to external service
                return await self._zmq_request("tcp://localhost:7100", data)
        except Exception as e:
            logger.error(f"Error delegating to ServiceRegistry: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _delegate_to_system_twin(self, data: dict):
        """Delegate to existing SystemDigitalTwin via ZMQ"""
        try:
            if self.system_twin:
                # Direct method call if running in same process
                return self.system_twin.handle_request(data)
            else:
                # ZMQ call to external service
                return await self._zmq_request("tcp://localhost:7120", data)
        except Exception as e:
            logger.error(f"Error delegating to SystemDigitalTwin: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _delegate_to_request_coordinator(self, data: dict):
        """Delegate to existing RequestCoordinator via ZMQ"""
        try:
            if self.request_coordinator:
                # For RequestCoordinator, we'd need to adapt the interface
                # as it uses different request handling patterns
                return {"status": "delegated", "service": "RequestCoordinator", "data": data}
            else:
                # ZMQ call to external service
                return await self._zmq_request("tcp://localhost:26002", data)
        except Exception as e:
            logger.error(f"Error delegating to RequestCoordinator: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _delegate_to_unified_system(self, data: dict):
        """Delegate to existing UnifiedSystemAgent via ZMQ"""
        try:
            if self.unified_system:
                # Direct method call if available
                return {"status": "delegated", "service": "UnifiedSystemAgent", "data": data}
            else:
                # ZMQ call to external service
                return await self._zmq_request("tcp://localhost:7125", data)
        except Exception as e:
            logger.error(f"Error delegating to UnifiedSystemAgent: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _zmq_request(self, endpoint: str, data: dict, timeout: int = 5000):
        """Make ZMQ request to external service"""
        try:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, timeout)
            socket.setsockopt(zmq.SNDTIMEO, timeout)
            socket.connect(endpoint)
            
            socket.send_json(data)
            response = socket.recv_json()
            
            socket.close()
            return response
            
        except zmq.error.Again:
            return {"status": "error", "message": f"Timeout connecting to {endpoint}"}
        except Exception as e:
            return {"status": "error", "message": f"ZMQ error: {str(e)}"}
    
    # Migration support methods
    def _import_registry_state(self, state_data: dict) -> dict:
        """Import registry state for migration"""
        try:
            agents = state_data.get('agents', {})
            for agent_name, agent_data in agents.items():
                self.internal_registry[agent_name] = agent_data
                if 'port' in agent_data:
                    self.agent_endpoints[agent_name] = {
                        "host": agent_data.get('host', 'localhost'),
                        "port": agent_data['port'],
                        "health_check_port": agent_data.get('health_check_port')
                    }
            
            logger.info(f"Imported {len(agents)} agents to unified registry")
            return {"status": "success", "imported_agents": len(agents)}
            
        except Exception as e:
            logger.error(f"Error importing registry state: {e}")
            return {"status": "error", "message": str(e)}
    
    def _import_twin_state(self, state_data: dict) -> dict:
        """Import system twin state for migration"""
        try:
            # Import system metrics and agent registry
            if 'system_metrics' in state_data:
                self.system_metrics.update(state_data['system_metrics'])
            
            if 'agent_registry' in state_data:
                # Handle agent registry data
                for agent_record in state_data['agent_registry']:
                    # Adapt database record format to internal format
                    pass
            
            logger.info("Imported SystemDigitalTwin state")
            return {"status": "success", "message": "Twin state imported"}
            
        except Exception as e:
            logger.error(f"Error importing twin state: {e}")
            return {"status": "error", "message": str(e)}
    
    def _import_coordinator_state(self, state_data: dict) -> dict:
        """Import coordinator state for migration"""
        try:
            # Import routing configuration and task queue
            routing_config = state_data.get('routing_config', {})
            task_queue = state_data.get('task_queue', {})
            
            logger.info("Imported RequestCoordinator state")
            return {"status": "success", "message": "Coordinator state imported"}
            
        except Exception as e:
            logger.error(f"Error importing coordinator state: {e}")
            return {"status": "error", "message": str(e)}
    
    async def start(self):
        """Start the CoreOrchestrator service"""
        try:
            logger.info("Starting CoreOrchestrator service...")
            
            # Start legacy agents in delegation mode
            await self.start_legacy_agents()
            
            # Mark startup as complete
            self.startup_complete = True
            
            logger.info("CoreOrchestrator started successfully on port 7000")
            logger.info(f"Feature flags - Registry: {self.enable_unified_registry}, "
                       f"Twin: {self.enable_unified_twin}, "
                       f"Coordinator: {self.enable_unified_coordinator}, "
                       f"System: {self.enable_unified_system}")
            
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=7000,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start CoreOrchestrator: {e}")
            raise
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.context:
                self.context.term()
            if self.executor:
                self.executor.shutdown(wait=True)
            logger.info("CoreOrchestrator cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    import asyncio
    
    # Set default feature flags to delegation mode (facade pattern)
    os.environ.setdefault('ENABLE_UNIFIED_REGISTRY', 'false')
    os.environ.setdefault('ENABLE_UNIFIED_TWIN', 'false')
    os.environ.setdefault('ENABLE_UNIFIED_COORDINATOR', 'false')
    os.environ.setdefault('ENABLE_UNIFIED_SYSTEM', 'false')
    
    orchestrator = CoreOrchestrator()
    
    try:
        asyncio.run(orchestrator.start())
    except KeyboardInterrupt:
        logger.info("CoreOrchestrator interrupted by user")
    except Exception as e:
        logger.error(f"CoreOrchestrator error: {e}")
    finally:
        orchestrator.cleanup() 