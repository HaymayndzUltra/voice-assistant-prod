# Unified Agent Design & Migration Plan

## Executive Summary

This document provides detailed designs for each proposed unified agent, including class structures, configuration examples, testing plans, and migration strategies. Each design consolidates overlapping functionality while preserving all original features and improving maintainability.

---

## 1. UnifiedMemoryManagementAgent

### 1.1 Class Design

```python
"""
UnifiedMemoryManagementAgent - Consolidated memory management service
Merges: MemoryClient, SessionMemoryAgent, KnowledgeBase, MemoryOrchestratorService, 
        CacheManager, UnifiedMemoryReasoningAgent, ContextManager, ExperienceTracker
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import threading
import sqlite3
import redis
import zmq
from dataclasses import dataclass
from enum import Enum

class MemoryType(Enum):
    SESSION = "session"
    KNOWLEDGE = "knowledge" 
    EXPERIENCE = "experience"
    CONTEXT = "context"

@dataclass
class MemoryEntry:
    id: str
    type: MemoryType
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    importance: float = 1.0
    ttl: Optional[int] = None

class UnifiedMemoryManagementAgent:
    """
    Unified memory management combining all memory-related agents.
    
    Features:
    - Circuit breaker pattern for resilience (from MemoryClient)
    - Session management with expiry (from SessionMemoryAgent)
    - Fact/knowledge storage (from KnowledgeBase)
    - Hierarchical memory relationships (from MemoryOrchestratorService)
    - Multi-tier caching with Redis (from CacheManager)
    - Context window management (from ContextManager)
    - Experience tracking (from ExperienceTracker)
    - Memory reasoning capabilities (from UnifiedMemoryReasoningAgent)
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Core configuration
        self.port = config.get('port', 5713)
        self.health_check_port = config.get('health_check_port', 6713)
        
        # Storage backends
        self.sqlite_path = config.get('sqlite_path', 'data/unified_memory.db')
        self.redis_config = config.get('redis', {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'prefix': 'umma:'
        })
        
        # Circuit breaker settings (from MemoryClient)
        self.circuit_breaker_threshold = config.get('circuit_breaker_threshold', 5)
        self.circuit_breaker_timeout = config.get('circuit_breaker_timeout', 60)
        
        # Context management (from ContextManager)
        self.max_context_size = config.get('max_context_size', 10000)
        self.context_importance_threshold = config.get('context_importance_threshold', 0.3)
        
        # Session management (from SessionMemoryAgent)
        self.session_ttl = config.get('session_ttl', 3600)
        self.session_cleanup_interval = config.get('session_cleanup_interval', 300)
        
        # Initialize components
        self._init_storage()
        self._init_cache()
        self._init_circuit_breaker()
        self._init_zmq()
        self._start_background_threads()
    
    # --- Core Memory Operations ---
    
    def add_memory(self, entry: MemoryEntry) -> str:
        """Add memory entry with automatic caching and indexing"""
        # Implementation combines logic from:
        # - MemoryClient.add_memory()
        # - MemoryOrchestratorService.add_or_update_memory()
        # - CacheManager.cache_memory()
        pass
    
    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get memory with cache-first strategy"""
        # Implementation combines:
        # - CacheManager.get_cached_memory()
        # - MemoryOrchestratorService.get_memory()
        pass
    
    def search_memory(self, query: str, memory_type: Optional[MemoryType] = None,
                     limit: int = 10) -> List[MemoryEntry]:
        """Search across all memory types with relevance scoring"""
        # Merges search logic from:
        # - MemoryClient.search_memory()
        # - SessionMemoryAgent.search_interactions()
        # - KnowledgeBase.search_facts()
        pass
    
    # --- Session Management (from SessionMemoryAgent) ---
    
    def create_session(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        """Create new session with automatic expiry"""
        pass
    
    def add_interaction(self, session_id: str, interaction: Dict[str, Any]) -> bool:
        """Add interaction to session"""
        pass
    
    def get_session_context(self, session_id: str, max_items: int = 10) -> List[Dict]:
        """Get recent context for session"""
        pass
    
    # --- Knowledge Management (from KnowledgeBase) ---
    
    def add_fact(self, fact_id: str, fact_data: Dict[str, Any]) -> bool:
        """Add persistent fact/knowledge"""
        pass
    
    def update_fact(self, fact_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing fact"""
        pass
    
    # --- Context Management (from ContextManager) ---
    
    def add_to_context(self, content: str, importance: float = 1.0) -> bool:
        """Add to current context with importance scoring"""
        pass
    
    def get_context_text(self, max_tokens: int = 1000) -> str:
        """Get formatted context within token limit"""
        pass
    
    def prune_context(self, target_size: Optional[int] = None) -> int:
        """Prune low-importance context items"""
        pass
    
    # --- Experience Tracking (from ExperienceTracker) ---
    
    def track_experience(self, experience: Dict[str, Any]) -> bool:
        """Track user interaction experience"""
        pass
    
    def get_experiences(self, filters: Dict[str, Any]) -> List[Dict]:
        """Retrieve filtered experiences"""
        pass
    
    # --- Memory Relationships (from MemoryOrchestratorService) ---
    
    def add_memory_relationship(self, parent_id: str, child_id: str, 
                               relationship_type: str) -> bool:
        """Create hierarchical memory relationships"""
        pass
    
    def get_memory_children(self, parent_id: str) -> List[str]:
        """Get child memories"""
        pass
    
    # --- Circuit Breaker (from MemoryClient) ---
    
    def record_success(self):
        """Record successful operation for circuit breaker"""
        pass
    
    def record_failure(self):
        """Record failed operation for circuit breaker"""
        pass
    
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        pass
    
    # --- Health & Monitoring ---
    
    def get_health_status(self) -> Dict[str, Any]:
        """Comprehensive health check combining all components"""
        return {
            'status': 'healthy',
            'components': {
                'sqlite': self._check_sqlite_health(),
                'redis': self._check_redis_health(),
                'circuit_breaker': self.get_circuit_breaker_status(),
                'sessions': self._get_session_stats(),
                'cache': self._get_cache_stats(),
                'context': self._get_context_stats()
            },
            'timestamp': datetime.now().isoformat()
        }
```

### 1.2 Configuration Example

```yaml
UnifiedMemoryManagementAgent:
  port: 5713
  health_check_port: 6713
  
  # Storage configuration
  sqlite_path: data/unified_memory.db
  redis:
    host: localhost
    port: 6379
    db: 0
    prefix: "umma:"
    
  # Circuit breaker settings
  circuit_breaker_threshold: 5
  circuit_breaker_timeout: 60
  
  # Context management
  max_context_size: 10000
  context_importance_threshold: 0.3
  
  # Session management  
  session_ttl: 3600
  session_cleanup_interval: 300
  
  # Cache settings
  cache_ttl_default: 300
  cache_max_size_mb: 512
  
  # Performance tuning
  worker_threads: 4
  batch_size: 100
```

### 1.3 Testing & Validation Plan

#### Unit Tests
1. **Memory Operations**
   - Test add_memory with all memory types
   - Test get_memory with cache hit/miss scenarios
   - Test search_memory with various query patterns
   
2. **Session Management**
   - Test session creation and expiry
   - Test concurrent session access
   - Test session cleanup thread
   
3. **Circuit Breaker**
   - Test threshold triggering
   - Test automatic recovery
   - Test state transitions
   
4. **Context Management**
   - Test importance-based pruning
   - Test token limit enforcement
   - Test context serialization

#### Integration Tests
1. **End-to-End Memory Flow**
   - Create session → Add interactions → Search → Expire
   - Add fact → Update → Create relationships → Query graph
   
2. **Cache Coherency**
   - Verify cache invalidation on updates
   - Test multi-tier cache performance
   
3. **Failure Scenarios**
   - Redis down → SQLite fallback
   - Circuit breaker activation
   - Recovery procedures

#### Performance Tests
1. **Load Testing**
   - 10K concurrent sessions
   - 1M memory entries
   - Search latency < 100ms p99
   
2. **Memory Usage**
   - Monitor heap growth
   - Cache eviction effectiveness
   - Context pruning efficiency

### 1.4 Migration Plan

#### Phase 1: Parallel Deployment (Week 1-2)
1. Deploy UnifiedMemoryManagementAgent alongside existing agents
2. Configure with same Redis/SQLite backends (read-only mode)
3. Shadow traffic from existing agents to unified agent
4. Compare responses for consistency

#### Phase 2: Gradual Migration (Week 3-4)
1. Update clients to use unified agent for read operations (10% → 50% → 100%)
2. Monitor error rates and latencies
3. Enable write operations for new sessions only
4. Migrate existing sessions during low-traffic hours

#### Phase 3: Cutover (Week 5)
1. Update all client configurations
2. Redirect all traffic to unified agent
3. Keep old agents running in standby mode
4. Monitor for 48 hours

#### Phase 4: Cleanup (Week 6)
1. Decommission old agents
2. Archive old logs
3. Update documentation
4. Post-mortem review

#### Rollback Strategy
- **Instant Rollback**: Update service discovery to route back to old agents
- **Data Consistency**: Redis/SQLite shared, so no data migration needed
- **Monitoring**: Alert on error rate > 1% or latency > 200ms
- **Rollback Window**: Keep old agents for 30 days post-migration

---

## 2. UnifiedTaskCoordinatorAgent

### 2.1 Class Design

```python
"""
UnifiedTaskCoordinatorAgent - Consolidated task coordination and routing
Merges: RequestCoordinator, AsyncProcessor, TaskScheduler, AdvancedRouter, 
        TieredResponder, ResourceManager
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue
import asyncio
import threading
import time

class TaskPriority(Enum):
    CRITICAL = 0  # Voice interrupts
    HIGH = 1      # User requests
    NORMAL = 2    # Background tasks
    LOW = 3       # Maintenance

@dataclass
class Task:
    id: str
    type: str
    payload: Dict[str, Any]
    priority: TaskPriority
    timestamp: float
    timeout: float
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        return (self.priority.value, self.timestamp) < (other.priority.value, other.timestamp)

class UnifiedTaskCoordinatorAgent:
    """
    Unified task coordination combining request routing, async processing,
    scheduling, tiered responses, and resource management.
    
    Features:
    - Priority-based task queue (from RequestCoordinator)
    - Async task processing (from AsyncProcessor)
    - Cron-like scheduling (from TaskScheduler)
    - Model capability routing (from AdvancedRouter)
    - Tiered response system (from TieredResponder)
    - Resource allocation/limits (from ResourceManager)
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Core configuration
        self.port = config.get('port', 26002)
        self.health_check_port = config.get('health_check_port', 27002)
        
        # Queue settings
        self.max_queue_size = config.get('max_queue_size', 10000)
        self.worker_threads = config.get('worker_threads', 8)
        
        # Circuit breakers for downstream services
        self.circuit_breaker_config = config.get('circuit_breakers', {})
        
        # Resource limits
        self.resource_limits = config.get('resource_limits', {
            'cpu_percent': 80,
            'memory_mb': 4096,
            'concurrent_tasks': 100
        })
        
        # Tiered response configuration
        self.response_tiers = config.get('response_tiers', {
            'tier1': {'timeout': 0.1, 'cache': True},
            'tier2': {'timeout': 1.0, 'cache': True},
            'tier3': {'timeout': 10.0, 'cache': False}
        })
        
        # Initialize components
        self._init_queues()
        self._init_workers()
        self._init_circuit_breakers()
        self._init_resource_manager()
        self._init_router()
        self._init_scheduler()
    
    # --- Task Submission (from RequestCoordinator) ---
    
    async def submit_task(self, task: Task) -> str:
        """Submit task with priority and timeout handling"""
        # Check resource availability
        if not self._check_resources(task):
            raise ResourceError("Insufficient resources")
            
        # Add to appropriate queue
        await self._enqueue_task(task)
        
        # Return task ID for tracking
        return task.id
    
    # --- Async Processing (from AsyncProcessor) ---
    
    async def _process_task(self, task: Task) -> Any:
        """Process task asynchronously with timeout and retry logic"""
        # Allocate resources
        resources = await self._allocate_resources(task)
        
        try:
            # Route to appropriate handler
            handler = self._route_task(task)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(task),
                timeout=task.timeout
            )
            
            # Record success
            self._record_task_success(task, result)
            
            return result
            
        except asyncio.TimeoutError:
            self._record_task_timeout(task)
            raise
            
        finally:
            # Release resources
            await self._release_resources(resources)
    
    # --- Scheduling (from TaskScheduler) ---
    
    def schedule_recurring_task(self, cron_expr: str, task_template: Dict) -> str:
        """Schedule recurring task with cron expression"""
        pass
    
    def cancel_scheduled_task(self, schedule_id: str) -> bool:
        """Cancel scheduled task"""
        pass
    
    # --- Routing (from AdvancedRouter) ---
    
    def _route_task(self, task: Task) -> Callable:
        """Route task to appropriate handler based on type and capabilities"""
        # Detect task type
        task_type = self._detect_task_type(task)
        
        # Map to model capabilities
        required_capabilities = self._map_task_to_capabilities(task_type)
        
        # Select best handler
        handler = self._select_handler(required_capabilities)
        
        return handler
    
    # --- Tiered Responses (from TieredResponder) ---
    
    async def get_response(self, query: Dict[str, Any]) -> Any:
        """Get response using tiered approach"""
        # Try tier 1 (cached/fast)
        if result := await self._try_tier1(query):
            return result
            
        # Try tier 2 (moderate complexity)
        if result := await self._try_tier2(query):
            return result
            
        # Fall back to tier 3 (complex/slow)
        return await self._try_tier3(query)
    
    # --- Resource Management (from ResourceManager) ---
    
    def _check_resources(self, task: Task) -> bool:
        """Check if resources available for task"""
        required = self._estimate_resources(task)
        available = self._get_available_resources()
        
        return all(
            available[res] >= required[res]
            for res in required
        )
    
    async def _allocate_resources(self, task: Task) -> Dict[str, Any]:
        """Allocate resources for task execution"""
        pass
    
    async def _release_resources(self, resources: Dict[str, Any]):
        """Release allocated resources"""
        pass
    
    # --- Circuit Breakers ---
    
    def _check_circuit_breaker(self, service: str) -> bool:
        """Check if service circuit breaker is open"""
        pass
    
    def _record_service_success(self, service: str):
        """Record successful service call"""
        pass
    
    def _record_service_failure(self, service: str):
        """Record failed service call"""
        pass
    
    # --- Health & Monitoring ---
    
    def get_health_status(self) -> Dict[str, Any]:
        """Comprehensive health status"""
        return {
            'status': 'healthy',
            'queue_sizes': self._get_queue_stats(),
            'worker_status': self._get_worker_stats(),
            'resource_usage': self._get_resource_stats(),
            'circuit_breakers': self._get_circuit_breaker_stats(),
            'response_times': self._get_response_time_stats()
        }
```

### 2.2 Testing & Validation Plan

#### Unit Tests
1. **Queue Management**
   - Test priority ordering
   - Test queue overflow handling
   - Test task timeout

2. **Resource Management**
   - Test allocation/release
   - Test resource limits
   - Test deadlock prevention

3. **Circuit Breakers**
   - Test per-service breakers
   - Test cascade failure prevention

#### Integration Tests
1. **End-to-End Flow**
   - Submit task → Route → Process → Response
   - Scheduled task execution
   - Tiered response fallback

2. **Load Balancing**
   - Verify even distribution
   - Test worker scaling

#### Performance Tests
1. **Throughput**
   - 10K tasks/second
   - <10ms routing overhead
   - Queue saturation handling

### 2.3 Migration Plan

#### Phase 1: Shadow Mode (Week 1-2)
1. Deploy unified agent in shadow mode
2. Duplicate traffic from RequestCoordinator
3. Compare routing decisions
4. Measure performance differences

#### Phase 2: Canary Deployment (Week 3-4)
1. Route 5% traffic to unified agent
2. Gradually increase to 50%
3. Monitor SLIs closely
4. A/B test response quality

#### Phase 3: Full Migration (Week 5)
1. Migrate scheduled tasks
2. Update all client configs
3. Decommission old agents
4. Archive historical data

---

## 3. UnifiedHealthPerformanceMonitor

### 3.1 Class Design

```python
"""
UnifiedHealthPerformanceMonitor - Consolidated health and performance monitoring
Merges: PredictiveHealthMonitor, PerformanceMonitor, PerformanceLoggerAgent,
        HealthMonitor, SystemHealthManager, AgentTrustScorer
"""

class UnifiedHealthPerformanceMonitor:
    """
    Unified monitoring combining predictive health, performance metrics,
    logging, trust scoring, and system health management.
    
    Features:
    - Real-time performance metrics (from PerformanceMonitor)
    - Predictive failure detection (from PredictiveHealthMonitor)
    - Centralized metric logging (from PerformanceLoggerAgent)
    - Agent trust scoring (from AgentTrustScorer)
    - System-wide health dashboard (from SystemHealthManager)
    - Adaptive sampling rates
    """
    
    def __init__(self, config: Dict[str, Any]):
        # Metric collection settings
        self.sampling_intervals = config.get('sampling_intervals', {
            'system': 1.0,      # CPU, memory, disk
            'agent': 5.0,       # Agent-specific metrics
            'predictive': 30.0  # ML model inference
        })
        
        # Storage backends
        self.timeseries_db = config.get('timeseries_db', {
            'type': 'prometheus',
            'retention': '30d'
        })
        
        # Trust scoring parameters
        self.trust_decay_rate = config.get('trust_decay_rate', 0.95)
        self.trust_recovery_rate = config.get('trust_recovery_rate', 1.05)
        
        # Initialize components
        self._init_collectors()
        self._init_predictive_models()
        self._init_error_bus()
        self._init_dashboards()
    
    # --- Metric Collection (from PerformanceMonitor) ---
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect all system and agent metrics"""
        return {
            'system': self._collect_system_metrics(),
            'agents': self._collect_agent_metrics(),
            'custom': self._collect_custom_metrics()
        }
    
    # --- Predictive Health (from PredictiveHealthMonitor) ---
    
    def predict_failures(self) -> List[Dict[str, Any]]:
        """Predict potential failures using ML models"""
        # Analyze metric trends
        trends = self._analyze_trends()
        
        # Run prediction models
        predictions = self._run_predictions(trends)
        
        # Generate alerts
        alerts = self._generate_alerts(predictions)
        
        return alerts
    
    def auto_remediate(self, alert: Dict[str, Any]) -> bool:
        """Attempt automatic remediation"""
        remediation_type = self._determine_remediation(alert)
        
        if remediation_type == 'restart':
            return self._restart_agent(alert['agent_id'])
        elif remediation_type == 'scale':
            return self._scale_resources(alert['resource'])
        elif remediation_type == 'throttle':
            return self._apply_throttling(alert['service'])
            
        return False
    
    # --- Performance Logging (from PerformanceLoggerAgent) ---
    
    def log_metric(self, metric_name: str, value: float, 
                   tags: Dict[str, str] = None):
        """Log individual metric with tags"""
        pass
    
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log system event"""
        pass
    
    # --- Trust Scoring (from AgentTrustScorer) ---
    
    def update_trust_score(self, agent_id: str, success: bool):
        """Update agent trust score based on performance"""
        current_score = self._get_trust_score(agent_id)
        
        if success:
            new_score = min(1.0, current_score * self.trust_recovery_rate)
        else:
            new_score = max(0.0, current_score * self.trust_decay_rate)
            
        self._set_trust_score(agent_id, new_score)
    
    def get_trusted_agents(self, min_score: float = 0.8) -> List[str]:
        """Get list of trusted agents above threshold"""
        pass
    
    # --- System Health (from SystemHealthManager) ---
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        return {
            'overall_status': self._calculate_overall_status(),
            'agents': self._get_all_agent_health(),
            'resources': self._get_resource_health(),
            'predictions': self._get_prediction_summary(),
            'alerts': self._get_active_alerts()
        }
    
    # --- Error Bus Integration ---
    
    def publish_error(self, error: ErrorReport):
        """Publish error to distributed error bus"""
        pass
    
    def subscribe_errors(self, callback: Callable):
        """Subscribe to error stream"""
        pass
```

### 3.2 Migration Strategy

1. **Metric Migration**
   - Export historical metrics from old agents
   - Import into unified time-series DB
   - Verify data integrity

2. **Dashboard Migration**
   - Recreate dashboards with new metric names
   - Maintain old dashboards during transition
   - Train team on new interface

3. **Alert Migration**
   - Map old alerts to new format
   - Test alert routing
   - Update on-call playbooks

---

## 4. Additional Unified Agents

### 4.1 UnifiedLearningAgent

Combines learning opportunity detection, orchestration, evaluation, and tuning into a cohesive pipeline.

### 4.2 UnifiedTranslationService

Merges all translation services with shared tokenizers and caches.

### 4.3 UnifiedVisionProcessingAgent

Combines face recognition and general vision processing with shared GPU resources.

---

## General Migration Best Practices

### Pre-Migration Checklist
- [ ] Full backup of all data
- [ ] Load testing completed
- [ ] Rollback procedures documented
- [ ] Team trained on new architecture
- [ ] Monitoring dashboards ready
- [ ] Client libraries updated

### Migration Monitoring
- Error rate threshold: 0.1%
- Latency increase threshold: 10%
- Resource usage threshold: 90%
- Automatic rollback triggers configured

### Post-Migration Validation
- [ ] All features working as expected
- [ ] Performance meets or exceeds baseline
- [ ] No data loss or corruption
- [ ] Successful rollback test
- [ ] Documentation updated

---

## Conclusion

This unified agent architecture reduces operational complexity while maintaining all original functionality. The gradual migration approach minimizes risk, and comprehensive testing ensures reliability. Each unified agent is designed with clear interfaces, making future enhancements straightforward.