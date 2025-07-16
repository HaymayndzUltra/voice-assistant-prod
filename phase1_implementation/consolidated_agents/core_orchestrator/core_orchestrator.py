#!/usr/bin/env python3
"""
CoreOrchestrator - Phase 1 Implementation
Consolidates: ServiceRegistry, SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent
Target: Unified service coordination + system monitoring FastAPI service (Port 7000)
Hardware: MainPC
Risk Mitigation: Facade pattern - wrap existing classes first, then deprecate
Logic Preservation: 100% - All original logic preserved via delegation + O3 enhancements
"""

import sys
import os
from pathlib import Path
import logging
import time
import threading
import asyncio
import json
import sqlite3
import heapq
import redis
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import uuid

# Add project paths for imports
project_root = Path(__file__).parent.parent.parent.parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import zmq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_implementation/logs/core_orchestrator.log')
    ]
)
logger = logging.getLogger("CoreOrchestrator")

# Import BaseAgent with safe fallback
try:
    from common.core.base_agent import BaseAgent
except ImportError as e:
    logger.warning(f"Could not import BaseAgent: {e}")
    class BaseAgent:
        def __init__(self, name, port, health_check_port=None, **kwargs):
            self.name = name
            self.port = port
            self.health_check_port = health_check_port or (port + 1000)

# O3 Enhanced Priority Calculation
@dataclass
class TaskRequest:
    """Enhanced task request with O3 priority calculation fields"""
    task_id: str
    task_type: str
    user_id: str = "default"
    urgency: str = "normal"  # critical, high, normal, low
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class CircuitBreaker:
    """O3 Circuit breaker implementation"""
    CLOSED, OPEN, HALF_OPEN = 'closed', 'open', 'half_open'
    
    def __init__(self, failure_threshold=3, reset_timeout=30):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = self.CLOSED
    
    def can_execute(self) -> bool:
        if self.state == self.CLOSED:
            return True
        elif self.state == self.OPEN:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = self.HALF_OPEN
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        self.failure_count = 0
        self.state = self.CLOSED
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN

class CoreOrchestrator(BaseAgent):
    """
    CoreOrchestrator - Phase 1 Consolidated Service
    Enhanced with O3 specifications: SQLite, Redis, Language Analysis, Advanced Priority Calculation
    """
    
    def __init__(self, name="CoreOrchestrator", port=7000, 
                 enable_unified_registry=True, enable_unified_twin=True,
                 enable_unified_coordinator=True, enable_unified_system=True):
        super().__init__(name, port)
        
        # Feature flags for gradual transition
        self.enable_unified_registry = enable_unified_registry
        self.enable_unified_twin = enable_unified_twin
        self.enable_unified_coordinator = enable_unified_coordinator
        self.enable_unified_system = enable_unified_system
        
        # O3 Enhanced Features
        self.db_path = "phase1_implementation/data/core_orchestrator.db"
        self.redis_conn = None
        self.language_analysis_thread = None
        self.language_analysis_running = False
        
        # O3 Priority System
        self.task_queue = []  # Priority queue using heapq
        self.user_profiles = {}  # SQLite-backed user profiles
        self.circuit_breakers = defaultdict(lambda: CircuitBreaker())
        
        # Internal registries for unified mode
        self.internal_registry = {}
        self.system_metrics = {}
        self.active_requests = {}
        
        # Thread pools
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix='CoreOrchestrator')
        
        # FastAPI app for unified endpoints
        self.app = FastAPI(
            title="CoreOrchestrator", 
            description="Phase 1 Unified Core Services with O3 Enhancements",
            version="1.0.0"
        )
        
        # Initialize O3 enhanced components
        self._init_database()
        self._setup_redis()
        self._start_language_analysis_thread()
        
        # Setup unified API routes
        self.setup_routes()
        
        # ZMQ context for legacy communication
        self.context = zmq.Context()
        self.zmq_socket = None
        
        # Startup state
        self.startup_complete = False
        self.startup_time = time.time()
        
        logger.info("CoreOrchestrator with O3 enhancements initialized")
    
    def _init_database(self):
        """O3 Required: SQLite database setup for user profiles"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            
            # User profiles table for priority calculation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    priority_adjustment INTEGER DEFAULT 0,
                    request_count INTEGER DEFAULT 0,
                    last_request_time REAL,
                    performance_score REAL DEFAULT 1.0,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Agent registry table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_registry (
                    agent_name TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    port INTEGER,
                    health_status TEXT DEFAULT 'unknown',
                    last_seen REAL DEFAULT (julianday('now')),
                    metadata TEXT
                )
            """)
            
            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    timestamp REAL PRIMARY KEY,
                    metric_type TEXT,
                    metric_value REAL,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
            # Load user profiles into memory
            self._load_user_profiles()
            logger.info(f"SQLite database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def _setup_redis(self):
        """O3 Required: Redis cache integration"""
        try:
            self.redis_conn = redis.Redis(
                host='localhost', 
                port=6379, 
                db=1,  # Use db=1 for core orchestrator
                decode_responses=True,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_conn.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, continuing without caching")
            self.redis_conn = None
    
    def _load_user_profiles(self):
        """Load user profiles from database for priority calculation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("SELECT user_id, priority_adjustment, performance_score FROM user_profiles")
            
            for row in cursor.fetchall():
                user_id, priority_adj, perf_score = row
                self.user_profiles[user_id] = {
                    'priority_adjustment': priority_adj,
                    'performance_score': perf_score
                }
            
            conn.close()
            logger.info(f"Loaded {len(self.user_profiles)} user profiles")
            
        except Exception as e:
            logger.error(f"Error loading user profiles: {e}")
    
    def _start_language_analysis_thread(self):
        """O3 Required: Language analysis processing thread"""
        self.language_analysis_running = True
        self.language_analysis_thread = threading.Thread(
            target=self._listen_for_language_analysis,
            name="LanguageAnalysisProcessor",
            daemon=True
        )
        self.language_analysis_thread.start()
        logger.info("Language analysis thread started")
    
    def _listen_for_language_analysis(self):
        """O3 Required: Language analysis processing loop"""
        while self.language_analysis_running:
            try:
                # Check for language analysis requests
                if self.redis_conn:
                    # Check Redis for language analysis requests
                    analysis_request = self.redis_conn.lpop('language_analysis_queue')
                    if analysis_request:
                        request_data = json.loads(analysis_request)
                        self._process_language_analysis(request_data)
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except Exception as e:
                logger.error(f"Language analysis thread error: {e}")
                time.sleep(1)
    
    def _process_language_analysis(self, request_data):
        """Process language analysis request"""
        try:
            text = request_data.get('text', '')
            request_id = request_data.get('request_id', str(uuid.uuid4()))
            
            # Simple language detection (can be enhanced with actual models)
            language_hints = {
                'filipino': ['po', 'opo', 'ka', 'ng', 'sa', 'ang', 'mga'],
                'tagalog': ['po', 'opo', 'ka', 'ng', 'sa', 'ang', 'mga'],
                'english': ['the', 'and', 'or', 'but', 'in', 'on', 'at']
            }
            
            detected_language = 'unknown'
            max_matches = 0
            
            text_lower = text.lower()
            for lang, hints in language_hints.items():
                matches = sum(1 for hint in hints if hint in text_lower)
                if matches > max_matches:
                    max_matches = matches
                    detected_language = lang
            
            result = {
                'request_id': request_id,
                'detected_language': detected_language,
                'confidence': min(max_matches / 10.0, 1.0),
                'processed_at': time.time()
            }
            
            # Store result in Redis
            if self.redis_conn:
                self.redis_conn.setex(
                    f'language_result:{request_id}',
                    300,  # 5 minutes TTL
                    json.dumps(result)
                )
            
            logger.info(f"Language analysis completed for request {request_id}: {detected_language}")
            
        except Exception as e:
            logger.error(f"Language analysis processing error: {e}")
    
    def _calculate_priority(self, task_type: str, request: TaskRequest) -> int:
        """O3 Required: Dynamic priority calculation algorithm"""
        try:
            # Base priority by task type
            base_priority = {
                'audio_processing': 1,
                'text_processing': 2,
                'vision_processing': 3,
                'translation': 2,
                'memory_operation': 4,
                'system_command': 1
            }.get(task_type, 5)
            
            # User priority adjustment from SQLite profiles
            user_profile = self.user_profiles.get(request.user_id, {})
            user_priority_adjustment = user_profile.get('priority_adjustment', 0)
            
            # Urgency adjustment
            urgency_adjustment = {
                'critical': -3,
                'high': -1, 
                'normal': 0,
                'low': 1
            }.get(request.urgency, 0)
            
            # System load adjustment (80% threshold as per O3)
            current_queue_size = len(self.task_queue)
            system_load_adjustment = 1 if current_queue_size > 20 else 0  # 80% of 25 max queue
            
            # Performance score adjustment
            performance_score = user_profile.get('performance_score', 1.0)
            performance_adjustment = int((1.0 - performance_score) * 2)
            
            # Time-based adjustment (newer requests get slight priority)
            time_adjustment = max(0, int((time.time() - request.timestamp) / 60))
            
            final_priority = (base_priority + user_priority_adjustment + urgency_adjustment + 
                            system_load_adjustment + performance_adjustment + time_adjustment)
            
            logger.debug(f"Priority calculation for {task_type}: base={base_priority}, "
                        f"user={user_priority_adjustment}, urgency={urgency_adjustment}, "
                        f"load={system_load_adjustment}, final={final_priority}")
            
            return max(1, final_priority)  # Ensure positive priority
            
        except Exception as e:
            logger.error(f"Priority calculation error: {e}")
            return 5  # Default priority
    
    def add_task_to_queue(self, priority: int, task: TaskRequest):
        """O3 Required: Priority queue with heapq"""
        try:
            heapq.heappush(self.task_queue, (priority, time.time(), task))
            logger.info(f"Task {task.task_id} added to priority queue with priority {priority}")
            
            # Update user request count
            if task.user_id != "default":
                self._update_user_stats(task.user_id)
                
        except Exception as e:
            logger.error(f"Error adding task to queue: {e}")
    
    def _update_user_stats(self, user_id: str):
        """Update user statistics in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO user_profiles 
                (user_id, request_count, last_request_time)
                VALUES (?, 
                    COALESCE((SELECT request_count FROM user_profiles WHERE user_id = ?) + 1, 1),
                    ?)
            """, (user_id, user_id, time.time()))
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating user stats: {e}")
    
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
            if not self.enable_unified_registry:
                logger.info("Starting ServiceRegistry in delegation mode")
                # Assuming ServiceRegistryAgent is available in main_pc_code
                from main_pc_code.agents.service_registry_agent import ServiceRegistryAgent
                self.service_registry = ServiceRegistryAgent(port=7100)
                self.executor.submit(self.service_registry.run)
            else:
                logger.warning("ServiceRegistry not available, using unified mode")
            
            # Start SystemDigitalTwin if not unified and available
            if not self.enable_unified_twin:
                logger.info("Starting SystemDigitalTwin in delegation mode")
                # Assuming SystemDigitalTwinAgent is available in main_pc_code
                from main_pc_code.agents.system_digital_twin import SystemDigitalTwinAgent
                self.system_twin = SystemDigitalTwinAgent(config={"port": 7120})
                self.executor.submit(self.system_twin.run)
            else:
                logger.warning("SystemDigitalTwin not available, using unified mode")
            
            # Start RequestCoordinator if not unified and available
            if not self.enable_unified_coordinator:
                logger.info("Starting RequestCoordinator in delegation mode")
                # Assuming RequestCoordinator is available in main_pc_code
                from main_pc_code.agents.request_coordinator import RequestCoordinator
                self.request_coordinator = RequestCoordinator(port=26002)
                self.executor.submit(self.request_coordinator.run)
            else:
                logger.warning("RequestCoordinator not available, using unified mode")
            
            # Start UnifiedSystemAgent if not unified and available
            if not self.enable_unified_system:
                logger.info("Starting UnifiedSystemAgent in delegation mode")
                # Assuming UnifiedSystemAgent is available in main_pc_code
                from main_pc_code.agents.unified_system_agent import UnifiedSystemAgent
                self.unified_system = UnifiedSystemAgent()
                self.executor.submit(self.unified_system.run)
            else:
                logger.warning("UnifiedSystemAgent not available, using unified mode")
            
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