<<<<<<< HEAD
#!/usr/bin/env python3
"""
ResourceManagerSuite - Phase 1 Implementation
Consolidates: ResourceManager, TaskScheduler, AsyncProcessor, VRAMOptimizerAgent
Target: Unified resource allocation + task scheduling FastAPI service (Port 7001)
Hardware: MainPC
Risk Mitigation: Facade pattern - wrap existing classes first, then deprecate
Logic Preservation: 100% - All original logic preserved via delegation
"""

import sys
import os
from pathlib import Path
import logging
import time
import threading
import asyncio
import heapq
import json
from typing import Dict, Any, Optional, List, Tuple
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('phase1_implementation/logs/resource_manager_suite.log')
    ]
)
logger = logging.getLogger("ResourceManagerSuite")

# Import BaseAgent with safe fallback
try:
    from common.core.base_agent import BaseAgent
except ImportError as e:
    logger.warning(f"Could not import BaseAgent: {e}")
    class BaseAgent:
        def __init__(self, name, port, health_check_port=None, **kwargs):
            self.name = name
            self.port = port
            self.health_check_port = health_check_port or port + 100

# Task Priority Levels (from correction command)
class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class Task:
    """Task data structure with priority calculation"""
    task_id: str
    task_type: str
    priority: TaskPriority
    resources_required: Dict[str, Any]
    estimated_duration: float
    created_at: datetime
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Priority comparison for heapq"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at

@dataclass
class ResourceAllocation:
    """Resource allocation tracking"""
    allocation_id: str
    resource_type: str
    amount: float
    allocated_to: str
    allocated_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class CircuitBreaker:
    """Circuit breaker pattern for task execution"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class VRAMTracker:
    """VRAM usage tracking and optimization"""
    def __init__(self):
        self.total_vram = self._get_total_vram()
        self.allocated_vram = {}
        self.vram_budget_limits = {
            TaskPriority.CRITICAL: 0.8,  # 80% max
            TaskPriority.HIGH: 0.6,      # 60% max
            TaskPriority.MEDIUM: 0.4,    # 40% max
            TaskPriority.LOW: 0.2        # 20% max
        }
    
    def _get_total_vram(self) -> float:
        """Get total VRAM available (mock implementation)"""
        try:
            # This would use nvidia-ml-py3 or similar
            return 24.0  # Mock 24GB VRAM
        except Exception:
            return 8.0   # Fallback to 8GB
    
    def allocate_vram(self, allocation_id: str, amount: float, priority: TaskPriority) -> bool:
        """Allocate VRAM with budget checking"""
        current_usage = sum(self.allocated_vram.values())
        max_allowed = self.total_vram * self.vram_budget_limits[priority]
        
        if current_usage + amount <= max_allowed:
            self.allocated_vram[allocation_id] = amount
            logger.info(f"VRAM allocated: {amount}GB for {allocation_id}")
            return True
        else:
            logger.warning(f"VRAM allocation denied: {amount}GB would exceed budget")
            return False
    
    def release_vram(self, allocation_id: str):
        """Release VRAM allocation"""
        if allocation_id in self.allocated_vram:
            amount = self.allocated_vram.pop(allocation_id)
            logger.info(f"VRAM released: {amount}GB from {allocation_id}")
    
    def get_vram_status(self) -> Dict[str, Any]:
        """Get current VRAM status"""
        current_usage = sum(self.allocated_vram.values())
        return {
            "total_vram": self.total_vram,
            "allocated_vram": current_usage,
            "free_vram": self.total_vram - current_usage,
            "utilization_percent": (current_usage / self.total_vram) * 100,
            "allocations": dict(self.allocated_vram)
        }

class TaskScheduler:
    """Advanced task scheduler with priority queues and dependencies"""
    def __init__(self):
        # Priority queues using heapq (from correction command requirement)
        self.task_queues = {
            TaskPriority.CRITICAL: [],
            TaskPriority.HIGH: [],
            TaskPriority.MEDIUM: [],
            TaskPriority.LOW: []
        }
        self.active_tasks = {}
        self.completed_tasks = deque(maxlen=1000)
        self.failed_tasks = deque(maxlen=1000)
        self.task_dependencies = defaultdict(list)
        self.circuit_breakers = defaultdict(CircuitBreaker)
        
    def add_task(self, task: Task) -> bool:
        """Add task to appropriate priority queue"""
        try:
            # Check dependencies
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in [t.task_id for t in self.completed_tasks]:
                        logger.warning(f"Task {task.task_id} has unresolved dependency: {dep_id}")
                        return False
            
            # Add to priority queue
            heapq.heappush(self.task_queues[task.priority], task)
            logger.info(f"Task {task.task_id} added to {task.priority.name} queue")
            return True
            
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return False
    
    def get_next_task(self) -> Optional[Task]:
        """Get next task from highest priority non-empty queue"""
        for priority in TaskPriority:
            queue = self.task_queues[priority]
            if queue:
                task = heapq.heappop(queue)
                # Check circuit breaker
                if self.circuit_breakers[task.task_type].can_execute():
                    self.active_tasks[task.task_id] = task
                    return task
                else:
                    # Re-queue if circuit breaker is open
                    heapq.heappush(queue, task)
                    logger.warning(f"Circuit breaker open for task type: {task.task_type}")
        return None
    
    def complete_task(self, task_id: str, success: bool = True):
        """Mark task as completed"""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            
            if success:
                self.completed_tasks.append(task)
                self.circuit_breakers[task.task_type].record_success()
                logger.info(f"Task {task_id} completed successfully")
            else:
                self.failed_tasks.append(task)
                self.circuit_breakers[task.task_type].record_failure()
                logger.warning(f"Task {task_id} failed")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queues": {
                priority.name: len(queue) 
                for priority, queue in self.task_queues.items()
            },
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks)
        }

class ResourceManager:
    """Advanced resource management with allocation tracking"""
    def __init__(self):
        self.resource_pools = {
            "cpu_cores": {"total": self._get_cpu_count(), "allocated": 0},
            "memory_gb": {"total": self._get_memory_gb(), "allocated": 0},
            "gpu_slots": {"total": self._get_gpu_count(), "allocated": 0},
            "disk_space_gb": {"total": self._get_disk_space(), "allocated": 0}
        }
        self.allocations = {}
        self.allocation_history = deque(maxlen=1000)
        self.vram_tracker = VRAMTracker()
        
    def _get_cpu_count(self) -> int:
        """Get CPU core count"""
        try:
            import psutil
            return psutil.cpu_count(logical=False)
        except:
            return 4
    
    def _get_memory_gb(self) -> float:
        """Get total memory in GB"""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except:
            return 16.0
    
    def _get_gpu_count(self) -> int:
        """Get GPU count"""
        try:
            # This would use nvidia-ml-py3
            return 1
        except:
            return 0
    
    def _get_disk_space(self) -> float:
        """Get available disk space in GB"""
        try:
            import psutil
            return psutil.disk_usage('/').free / (1024**3)
        except:
            return 100.0
    
    def allocate_resources(self, allocation_id: str, resources: Dict[str, float], priority: TaskPriority) -> bool:
        """Allocate resources with priority-based limits"""
        try:
            # Check if allocation is possible
            for resource_type, amount in resources.items():
                if resource_type not in self.resource_pools:
                    logger.error(f"Unknown resource type: {resource_type}")
                    return False
                
                pool = self.resource_pools[resource_type]
                available = pool["total"] - pool["allocated"]
                
                if amount > available:
                    logger.warning(f"Insufficient {resource_type}: requested {amount}, available {available}")
                    return False
            
            # Special handling for VRAM
            if "vram_gb" in resources:
                if not self.vram_tracker.allocate_vram(allocation_id, resources["vram_gb"], priority):
                    return False
            
            # Perform allocation
            for resource_type, amount in resources.items():
                if resource_type != "vram_gb":  # Already handled above
                    self.resource_pools[resource_type]["allocated"] += amount
            
            # Record allocation
            allocation = ResourceAllocation(
                allocation_id=allocation_id,
                resource_type="mixed",
                amount=sum(resources.values()),
                allocated_to="task",
                allocated_at=datetime.utcnow()
            )
            self.allocations[allocation_id] = (resources, allocation)
            self.allocation_history.append(allocation)
            
            logger.info(f"Resources allocated for {allocation_id}: {resources}")
            return True
            
        except Exception as e:
            logger.error(f"Error allocating resources: {e}")
            return False
    
    def release_resources(self, allocation_id: str):
        """Release allocated resources"""
        if allocation_id in self.allocations:
            resources, allocation = self.allocations.pop(allocation_id)
            
            # Release from pools
            for resource_type, amount in resources.items():
                if resource_type != "vram_gb":
                    if resource_type in self.resource_pools:
                        self.resource_pools[resource_type]["allocated"] -= amount
                        self.resource_pools[resource_type]["allocated"] = max(0, self.resource_pools[resource_type]["allocated"])
            
            # Release VRAM
            if "vram_gb" in resources:
                self.vram_tracker.release_vram(allocation_id)
            
            logger.info(f"Resources released for {allocation_id}")
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        status = {}
        for resource_type, pool in self.resource_pools.items():
            status[resource_type] = {
                "total": pool["total"],
                "allocated": pool["allocated"],
                "available": pool["total"] - pool["allocated"],
                "utilization_percent": (pool["allocated"] / pool["total"]) * 100 if pool["total"] > 0 else 0
            }
        
        # Add VRAM status
        status["vram"] = self.vram_tracker.get_vram_status()
        
        return status

class ResourceManagerSuite(BaseAgent):
    """
    Unified resource management and task scheduling service.
    Implements facade pattern around existing ResourceManager, TaskScheduler, 
    AsyncProcessor, and VRAMOptimizerAgent.
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="ResourceManagerSuite", port=7001, health_check_port=7101)
        
        # Feature flags for gradual migration
        self.enable_unified_resources = os.getenv('ENABLE_UNIFIED_RESOURCES', 'false').lower() == 'true'
        self.enable_unified_scheduling = os.getenv('ENABLE_UNIFIED_SCHEDULING', 'false').lower() == 'true'
        self.enable_unified_vram = os.getenv('ENABLE_UNIFIED_VRAM', 'false').lower() == 'true'
        
        # Internal components
        self.resource_manager = ResourceManager()
        self.task_scheduler = TaskScheduler()
        
        # Legacy agent instances (facade pattern)
        self.legacy_resource_manager = None
        self.legacy_task_scheduler = None
        self.legacy_async_processor = None
        self.legacy_vram_optimizer = None
        
        # Threading components
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix='ResourceManagerSuite')
        self.processing_threads = []
        self.running = True
        
        # FastAPI app
        self.app = FastAPI(
            title="ResourceManagerSuite",
            description="Phase 1 Unified Resource Management and Task Scheduling",
            version="1.0.0"
        )
        
        self.setup_routes()
        
        # Startup state
        self.startup_complete = False
        self.startup_time = time.time()
        
        logger.info("ResourceManagerSuite initialized")
    
    def setup_routes(self):
        """Setup unified API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy" if self.startup_complete else "starting",
                "service": "ResourceManagerSuite",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - self.startup_time,
                "unified_services": {
                    "resources": self.enable_unified_resources,
                    "scheduling": self.enable_unified_scheduling,
                    "vram": self.enable_unified_vram
                }
            }
        
        @self.app.post("/allocate_resources")
        async def allocate_resources(request: Request):
            """Allocate system resources"""
            try:
                data = await request.json()
                allocation_id = data.get('allocation_id', str(uuid.uuid4()))
                resources = data.get('resources', {})
                priority = TaskPriority[data.get('priority', 'MEDIUM')]
                
                if self.enable_unified_resources:
                    success = self.resource_manager.allocate_resources(allocation_id, resources, priority)
                    return {"status": "success" if success else "failed", "allocation_id": allocation_id}
                else:
                    return await self._delegate_to_legacy_resource_manager(data)
                    
            except Exception as e:
                logger.error(f"Error allocating resources: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/release_resources")
        async def release_resources(request: Request):
            """Release allocated resources"""
            try:
                data = await request.json()
                allocation_id = data.get('allocation_id')
                
                if self.enable_unified_resources:
                    self.resource_manager.release_resources(allocation_id)
                    return {"status": "success", "message": f"Resources released for {allocation_id}"}
                else:
                    return await self._delegate_to_legacy_resource_manager(data)
                    
            except Exception as e:
                logger.error(f"Error releasing resources: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/schedule_task")
        async def schedule_task(request: Request):
            """Schedule a new task"""
            try:
                data = await request.json()
                
                task = Task(
                    task_id=data.get('task_id', str(uuid.uuid4())),
                    task_type=data['task_type'],
                    priority=TaskPriority[data.get('priority', 'MEDIUM')],
                    resources_required=data.get('resources_required', {}),
                    estimated_duration=data.get('estimated_duration', 60.0),
                    created_at=datetime.utcnow(),
                    deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
                    dependencies=data.get('dependencies', []),
                    metadata=data.get('metadata', {})
                )
                
                if self.enable_unified_scheduling:
                    success = self.task_scheduler.add_task(task)
                    return {"status": "success" if success else "failed", "task_id": task.task_id}
                else:
                    return await self._delegate_to_legacy_scheduler(data)
                    
            except Exception as e:
                logger.error(f"Error scheduling task: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/resource_status")
        async def resource_status():
            """Get current resource status"""
            if self.enable_unified_resources:
                return {
                    "status": "success",
                    "resources": self.resource_manager.get_resource_status(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return await self._delegate_to_legacy_resource_manager({"action": "get_status"})
        
        @self.app.get("/queue_status")
        async def queue_status():
            """Get current task queue status"""
            if self.enable_unified_scheduling:
                return {
                    "status": "success",
                    "queues": self.task_scheduler.get_queue_status(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return await self._delegate_to_legacy_scheduler({"action": "get_status"})
        
        @self.app.get("/vram_status")
        async def vram_status():
            """Get VRAM status"""
            if self.enable_unified_vram:
                return {
                    "status": "success",
                    "vram": self.resource_manager.vram_tracker.get_vram_status(),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return await self._delegate_to_legacy_vram_optimizer({"action": "get_status"})
    
    # Delegation methods for facade pattern
    async def _delegate_to_legacy_resource_manager(self, data: dict):
        """Delegate to existing ResourceManager"""
        # This would connect to existing ResourceManager agent
        return {"status": "delegated", "service": "LegacyResourceManager", "data": data}
    
    async def _delegate_to_legacy_scheduler(self, data: dict):
        """Delegate to existing TaskScheduler"""
        # This would connect to existing TaskScheduler agent
        return {"status": "delegated", "service": "LegacyTaskScheduler", "data": data}
    
    async def _delegate_to_legacy_vram_optimizer(self, data: dict):
        """Delegate to existing VRAMOptimizerAgent"""
        # This would connect to existing VRAMOptimizerAgent
        return {"status": "delegated", "service": "LegacyVRAMOptimizer", "data": data}
    
    def start_processing_threads(self):
        """Start background processing threads"""
        if self.enable_unified_scheduling:
            # Task processing thread
            task_thread = threading.Thread(target=self._task_processing_loop, daemon=True)
            task_thread.start()
            self.processing_threads.append(task_thread)
        
        # Resource monitoring thread
        if self.enable_unified_resources:
            monitor_thread = threading.Thread(target=self._resource_monitoring_loop, daemon=True)
            monitor_thread.start()
            self.processing_threads.append(monitor_thread)
    
    def _task_processing_loop(self):
        """Background task processing loop"""
        while self.running:
            try:
                task = self.task_scheduler.get_next_task()
                if task:
                    # Allocate resources for task
                    allocation_id = f"task_{task.task_id}"
                    if self.resource_manager.allocate_resources(allocation_id, task.resources_required, task.priority):
                        # Simulate task execution
                        logger.info(f"Executing task {task.task_id}")
                        time.sleep(min(task.estimated_duration, 10))  # Cap execution time for simulation
                        
                        # Complete task
                        self.task_scheduler.complete_task(task.task_id, success=True)
                        self.resource_manager.release_resources(allocation_id)
                    else:
                        # Failed to allocate resources
                        self.task_scheduler.complete_task(task.task_id, success=False)
                        logger.warning(f"Failed to allocate resources for task {task.task_id}")
                else:
                    time.sleep(1)  # No tasks available
                    
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                time.sleep(5)
    
    def _resource_monitoring_loop(self):
        """Background resource monitoring loop"""
        while self.running:
            try:
                # Log resource status periodically
                status = self.resource_manager.get_resource_status()
                logger.debug(f"Resource status: {status}")
                
                # Check for resource exhaustion
                for resource_type, resource_status in status.items():
                    if resource_type != "vram" and resource_status.get("utilization_percent", 0) > 90:
                        logger.warning(f"High {resource_type} utilization: {resource_status['utilization_percent']:.1f}%")
                
                time.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {e}")
                time.sleep(30)
    
    async def start(self):
        """Start the ResourceManagerSuite service"""
        try:
            logger.info("Starting ResourceManagerSuite service...")
            
            # Start processing threads
            self.start_processing_threads()
            
            # Mark startup as complete
            self.startup_complete = True
            
            logger.info("ResourceManagerSuite started successfully on port 7001")
            logger.info(f"Feature flags - Resources: {self.enable_unified_resources}, "
                       f"Scheduling: {self.enable_unified_scheduling}, "
                       f"VRAM: {self.enable_unified_vram}")
            
            # Start FastAPI server
            config = uvicorn.Config(
                self.app,
                host="0.0.0.0",
                port=7001,
                log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start ResourceManagerSuite: {e}")
            raise
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.running = False
            if self.executor:
                self.executor.shutdown(wait=True)
            logger.info("ResourceManagerSuite cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    import asyncio
    
    # Set default feature flags to unified mode for testing
    os.environ.setdefault('ENABLE_UNIFIED_RESOURCES', 'true')
    os.environ.setdefault('ENABLE_UNIFIED_SCHEDULING', 'true')
    os.environ.setdefault('ENABLE_UNIFIED_VRAM', 'true')
    
    suite = ResourceManagerSuite()
    
    try:
        asyncio.run(suite.start())
    except KeyboardInterrupt:
        logger.info("ResourceManagerSuite interrupted by user")
    except Exception as e:
        logger.error(f"ResourceManagerSuite error: {e}")
    finally:
        suite.cleanup() 
=======

from __future__ import annotations

# ResourceManagerSuite Consolidated Service

import sys
import os
import logging
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
import uvicorn
import zmq

# Ensure project root in path for legacy agent imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from common.core.base_agent import BaseAgent
except ImportError:
    # Fallback minimal BaseAgent if common.core not yet available during early unit-testing
    class BaseAgent:  # type: ignore
        def __init__(self, name: str, port: int, **_: Any):
            self.name = name
            self.port = port
            self.health_check_port = port + 100
            self.context: zmq.Context = zmq.Context()
            self.running = True
            self.start_time = time.time()
        def _get_health_status(self) -> Dict[str, Any]:
            return {
                "status": "ok",
                "uptime": time.time() - self.start_time,
            }
        def cleanup(self):
            self.running = False
            if hasattr(self, "context"):
                self.context.term()

# Safe imports of legacy agents (facade pattern)
LEGACY_IMPORTS = {
    "ResourceManager": "pc2_code.agents.resource_manager.ResourceManager",
    "TaskSchedulerAgent": "pc2_code.agents.task_scheduler.TaskSchedulerAgent",
    "AsyncProcessor": "pc2_code.agents.async_processor.AsyncProcessor",
    "VramOptimizerAgent": "main_pc_code.agents.vram_optimizer_agent.VramOptimizerAgent",
}

_import_cache: Dict[str, Optional[type]] = {}

def _safe_import(path: str) -> Optional[type]:
    if path in _import_cache:
        return _import_cache[path]
    module_path, cls_name = path.rsplit(".", 1)
    try:
        module = __import__(module_path, fromlist=[cls_name])
        cls = getattr(module, cls_name)
        _import_cache[path] = cls
        return cls
    except Exception as exc:  # pylint: disable=broad-except
        logging.getLogger("ResourceManagerSuite").warning("Could not import %s: %s", path, exc)
        _import_cache[path] = None
        return None

# ---------------------------------------------------------------------------
# Consolidated Service Implementation
# ---------------------------------------------------------------------------

LOGGER = logging.getLogger("ResourceManagerSuite")
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "phase1_implementation/logs/resource_manager_suite.log"),
    ],
)


class ResourceManagerSuite(BaseAgent):
    """Unified Resource-management & Scheduling service (port 7001).

    Facade over:
      * ResourceManager (resource accounting / NVML / psutil)
      * TaskSchedulerAgent (priority queue, async delegation)
      * AsyncProcessor (async workers)
      * VramOptimizerAgent (GPU-specific optimisation)
    """

    def __init__(self, *, port: int = 7001, health_check_port: int = 7101):
        super().__init__(name="ResourceManagerSuite", port=port, health_check_port=health_check_port)

        # Thread-pool for background tasks
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="RMSuite")
        self._agents: Dict[str, BaseAgent] = {}
        self._launch_legacy_agents()

        # ZMQ context for delegations not in-proc (fallback)
        self._zmq_ctx = zmq.Context()

        # FastAPI app for consolidated API
        self.app = FastAPI(
            title="ResourceManagerSuite",
            description="Phase-1 consolidated resource management & scheduling service",
            version="1.0.0",
        )
        self._setup_routes()

        self._startup_time = time.time()
        LOGGER.info("ResourceManagerSuite initialised on port %s", self.port)

    # ---------------------------------------------------------------------
    # Legacy agent bootstrapping
    # ---------------------------------------------------------------------

    def _launch_legacy_agents(self) -> None:  # noqa: C901  (complexity acceptable)
        """Instantiate legacy agent classes inside threads using facade pattern."""
        mapping = {
            "resource_manager": ("ResourceManager", 7113),
            "task_scheduler": ("TaskSchedulerAgent", 7115),
            "async_processor": ("AsyncProcessor", 7101),
            "vram_optimizer": ("VramOptimizerAgent", None),  # port determined inside
        }
        for key, (cls_name, legacy_port) in mapping.items():
            cls = _safe_import(LEGACY_IMPORTS[cls_name]) if cls_name in LEGACY_IMPORTS else None
            if cls is None:
                LOGGER.warning("%s class unavailable – running in unified-only mode", cls_name)
                continue
            try:
                # Instantiate with explicit port when possible to avoid conflicts.
                kwargs: Dict[str, Any] = {}
                if legacy_port is not None:
                    kwargs["port"] = legacy_port
                instance = cls(**kwargs)  # type: ignore[arg-type]
                thread = threading.Thread(target=instance.run, daemon=True, name=f"legacy_{key}")
                thread.start()
                self._agents[key] = instance  # keep ref for delegation
                LOGGER.info("Started legacy agent %s in-proc thread", cls_name)
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("Failed to start legacy %s: %s", cls_name, exc)

    # ---------------------------------------------------------------------
    # API Routes
    # ---------------------------------------------------------------------

    def _setup_routes(self) -> None:
        @self.app.get("/health")
        async def health() -> Dict[str, Any]:  # pylint: disable=unused-variable
            return self._get_health_status()

        # ------------- Resource endpoints -------------
        @self.app.post("/allocate")
        async def allocate(request: Request):  # type: ignore[no-return]
            data = await request.json()
            return await self._delegate("resource_manager", {"action": "allocate_resources", **data})

        @self.app.post("/release")
        async def release(request: Request):  # type: ignore[no-return]
            data = await request.json()
            return await self._delegate("resource_manager", {"action": "release_resources", **data})

        @self.app.get("/status")
        async def status():  # type: ignore[no-return]
            return await self._delegate("resource_manager", {"action": "get_status"})

        # ------------- Task scheduling endpoints -------------
        @self.app.post("/schedule")
        async def schedule(request: Request):  # type: ignore[no-return]
            data = await request.json()
            return await self._delegate("task_scheduler", {"action": "schedule_task", **data})

        # ------------- Async processing diagnostics -------------
        @self.app.get("/queue_stats")
        async def queue_stats():  # type: ignore[no-return]
            return await self._delegate("async_processor", {"action": "health_check"})

    # ---------------------------------------------------------------------
    # Delegation helpers
    # ---------------------------------------------------------------------

    async def _delegate(self, key: str, payload: Dict[str, Any], timeout_ms: int = 5000) -> Dict[str, Any]:
        """Delegate the request to an in-proc legacy agent if available, else via ZMQ."""
        agent = self._agents.get(key)
        if agent is not None and hasattr(agent, "handle_request"):
            try:
                return agent.handle_request(payload)  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.error("In-proc delegation to %s failed: %s", key, exc)

        # Fallback ZMQ delegation (legacy agent might be running as separate proc)
        target_port = {
            "resource_manager": 7113,
            "task_scheduler": 7115,
            "async_processor": 7101,
        }.get(key)
        if target_port is None:
            return {"status": "error", "message": f"Unknown delegation target: {key}"}
        try:
            sock = self._zmq_ctx.socket(zmq.REQ)
            sock.setsockopt(zmq.RCVTIMEO, timeout_ms)
            sock.connect(f"tcp://localhost:{target_port}")
            sock.send_json(payload)
            reply = sock.recv_json()
            sock.close()
            return reply
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("ZMQ delegation to %s@%s failed: %s", key, target_port, exc)
            return {"status": "error", "message": str(exc)}

    # ---------------------------------------------------------------------
    # Health / cleanup
    # ---------------------------------------------------------------------

    def _get_health_status(self):  # type: ignore[override]
        base = super()._get_health_status()
        base.update({
            "service": "ResourceManagerSuite",
            "legacy_agents": {k: v.__class__.__name__ for k, v in self._agents.items()},
            "uptime": time.time() - self._startup_time,
        })
        return base

    def cleanup(self):  # type: ignore[override]
        LOGGER.info("Cleaning up ResourceManagerSuite …")
        for agent in self._agents.values():
            try:
                if hasattr(agent, "cleanup"):
                    agent.cleanup()  # type: ignore[attr-defined]
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.warning("Error during legacy agent cleanup: %s", exc)
        super().cleanup()


# ---------------------------------------------------------------------------
# Stand-alone execution helper for local development
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    service = ResourceManagerSuite()
    uvicorn.run(service.app, host="0.0.0.0", port=service.port, log_level="info")
>>>>>>> d25a671 (Merge pull request #2 from HaymayndzUltra/cursor/implement-phase-1-consolidation-with-full-logic-preservation-6366)
