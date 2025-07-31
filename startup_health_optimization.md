# Optimized Startup Sequences & Health Check Strategies
## Docker Production Deployment

**Created**: 2025-07-30  
**Purpose**: Define optimal startup ordering and health check configurations for reliable deployments

---

## 1. MainPC System Startup Optimization

### 1.1 Startup Sequence Strategy

```yaml
# Startup waves with dependency-aware ordering
startup_waves:
  wave_1:  # Critical Infrastructure (0-60s)
    - ServiceRegistry       # Must be first
    - SystemDigitalTwin    # Depends on ServiceRegistry
    - ObservabilityHub     # Depends on SystemDigitalTwin
    - UnifiedSystemAgent   # Depends on SystemDigitalTwin
    
  wave_2:  # AI Engine (60-180s)
    - ModelManagerSuite    # Heavy initialization
    - VRAMOptimizerAgent  # Light, monitors ModelManager
    - ModelOrchestrator   # Depends on ModelManager ready
    - STTService          # Model loading time
    - TTSService          # Model loading time
    - FaceRecognitionAgent # Model loading time
    
  wave_3:  # Request Processing (180-240s)
    - RequestCoordinator
    - NLUAgent
    - IntentionValidatorAgent
    - GoalManager
    - AdvancedCommandHandler
    - Responder
    
  wave_4:  # Memory & Learning (240-300s)
    - MemoryClient
    - SessionMemoryAgent
    - KnowledgeBase
    - LearningOrchestrationService
    - Others (parallel)
    
  wave_5:  # Supporting Services (300-360s)
    - audio_realtime (all agents)
    - personality (all agents)
    - auxiliary (all agents)
```

### 1.2 Group-Specific Health Check Configurations

#### Core Platform Group
```yaml
core_platform:
  ServiceRegistry:
    health_check:
      type: http
      endpoint: /health
      interval: 5s
      timeout: 3s
      retries: 3
      start_period: 10s
      success_threshold: 1
      failure_threshold: 3
      checks:
        - name: registry_accessible
          test: "curl -f http://localhost:8200/health"
        - name: can_register_service
          test: "curl -X POST http://localhost:8200/register/test"
        
  SystemDigitalTwin:
    health_check:
      type: composite
      interval: 10s
      timeout: 5s
      start_period: 30s
      checks:
        - name: api_responsive
          test: "curl -f http://localhost:8220/health"
        - name: database_connected
          test: "curl -f http://localhost:8220/health/db"
        - name: redis_connected
          test: "curl -f http://localhost:8220/health/redis"
        - name: service_registry_connected
          test: "curl -f http://localhost:8220/health/registry"
```

#### AI Engine Group
```yaml
ai_engine:
  ModelManagerSuite:
    health_check:
      type: staged
      stages:
        - name: startup
          start_period: 120s  # Long startup for model loading
          checks:
            - test: "curl -f http://localhost:8211/health/startup"
              interval: 10s
              timeout: 5s
        - name: models_loaded
          checks:
            - test: "curl -f http://localhost:8211/health/models"
              interval: 15s
              timeout: 10s
        - name: ready
          checks:
            - test: "curl -f http://localhost:8211/health/ready"
              interval: 10s
              timeout: 5s
      
  VRAMOptimizerAgent:
    health_check:
      type: http
      endpoint: /health
      interval: 5s
      timeout: 3s
      start_period: 15s
      dependency_checks:
        - service: ModelManagerSuite
          endpoint: http://model-manager:8211/health/ready
```

### 1.3 Progressive Health Check Strategy

```python
# Health check progression for complex services
class ProgressiveHealthCheck:
    stages = [
        {
            "name": "process_started",
            "check": lambda: process_exists(),
            "timeout": 10,
            "critical": True
        },
        {
            "name": "port_listening", 
            "check": lambda: port_is_open(),
            "timeout": 30,
            "critical": True
        },
        {
            "name": "api_responsive",
            "check": lambda: api_responds_200(),
            "timeout": 60,
            "critical": True
        },
        {
            "name": "dependencies_connected",
            "check": lambda: all_deps_healthy(),
            "timeout": 90,
            "critical": True
        },
        {
            "name": "fully_operational",
            "check": lambda: service_fully_ready(),
            "timeout": 120,
            "critical": False  # Can start serving with degraded mode
        }
    ]
```

---

## 2. PC2 System Startup Optimization

### 2.1 PC2 Startup Sequence

```yaml
startup_sequence:
  phase_1:  # Core Services (0-60s)
    parallel:
      - ObservabilityHub      # No dependencies
      - MemoryOrchestratorService  # No dependencies
    sequential:
      - ResourceManager       # Depends on ObservabilityHub
      - AsyncProcessor        # Depends on ResourceManager
      - CacheManager         # Depends on MemoryOrchestratorService
      - UnifiedUtilsAgent    # Depends on ObservabilityHub
      
  phase_2:  # Application Services (60-120s)
    parallel:  # All can start together
      - TieredResponder
      - DreamWorldAgent
      - UnifiedMemoryReasoningAgent
      - TutorAgent
      - ContextManager
      - ExperienceTracker
      - TaskScheduler
      - AuthenticationAgent
      - AgentTrustScorer
      - FileSystemAssistantAgent
      - VisionProcessingAgent
    sequential:  # These have dependencies
      - ProactiveContextMonitor  # After ContextManager
      - DreamingModeAgent       # After DreamWorldAgent
      - AdvancedRouter          # After TaskScheduler
      - RemoteConnectorAgent    # After AdvancedRouter
      - UnifiedWebAgent         # After FileSystemAssistant
```

### 2.2 PC2 Health Check Strategy

```yaml
pc2_health_checks:
  lightweight_check:  # For most PC2 agents
    interval: 10s
    timeout: 5s
    retries: 3
    test: "curl -f http://localhost:{HEALTH_PORT}/health"
    
  dependency_aware_check:  # For agents with dependencies
    pre_checks:
      - dependency: "{DEPENDENCY_NAME}"
        endpoint: "http://{DEPENDENCY_HOST}:{DEPENDENCY_HEALTH_PORT}/health"
        required: true
    main_check:
      test: "curl -f http://localhost:{HEALTH_PORT}/health"
```

---

## 3. Optimized Health Check Endpoints

### 3.1 Standard Health Check Response Format

```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2025-07-30T12:00:00Z",
  "service": {
    "name": "ServiceName",
    "version": "1.0.0",
    "uptime_seconds": 3600
  },
  "checks": {
    "self": {
      "status": "healthy",
      "latency_ms": 5
    },
    "dependencies": {
      "ServiceRegistry": {
        "status": "healthy",
        "latency_ms": 12
      },
      "SystemDigitalTwin": {
        "status": "healthy", 
        "latency_ms": 8
      }
    },
    "resources": {
      "memory_mb": 512,
      "cpu_percent": 15.5,
      "gpu_memory_mb": 2048,
      "threads": 8
    }
  },
  "metrics": {
    "requests_per_second": 145,
    "error_rate": 0.001,
    "average_latency_ms": 23
  }
}
```

### 3.2 Health Check Implementation Template

```python
# Standard health check implementation for agents
class AgentHealthCheck:
    def __init__(self, agent_name, dependencies):
        self.agent_name = agent_name
        self.dependencies = dependencies
        self.start_time = time.time()
        
    async def check_health(self) -> dict:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": {
                "name": self.agent_name,
                "version": self.get_version(),
                "uptime_seconds": time.time() - self.start_time
            },
            "checks": {}
        }
        
        # Self check
        self_check = await self._check_self()
        health_status["checks"]["self"] = self_check
        
        # Dependency checks
        dep_checks = await self._check_dependencies()
        health_status["checks"]["dependencies"] = dep_checks
        
        # Resource checks
        resource_check = await self._check_resources()
        health_status["checks"]["resources"] = resource_check
        
        # Determine overall status
        if any(check["status"] == "unhealthy" for check in 
               [self_check] + list(dep_checks.values())):
            health_status["status"] = "unhealthy"
        elif any(check["status"] == "degraded" for check in 
                 [self_check] + list(dep_checks.values())):
            health_status["status"] = "degraded"
            
        return health_status
```

---

## 4. Docker Compose Health Check Configuration

### 4.1 MainPC Docker Compose Example

```yaml
version: '3.8'

services:
  cascade-core:
    image: cascade/core:latest
    healthcheck:
      test: ["CMD", "python", "/app/health_check.py", "core"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    deploy:
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 5
        
  cascade-ai-engine:
    image: cascade/ai-engine:latest
    depends_on:
      cascade-core:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "/app/health_check.py", "ai-engine"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 180s  # 3 minutes for model loading
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 4.2 Kubernetes Health Check Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cascade-core
spec:
  template:
    spec:
      containers:
      - name: service-registry
        image: cascade/service-registry:latest
        ports:
        - containerPort: 7200
        - containerPort: 8200
        livenessProbe:
          httpGet:
            path: /health
            port: 8200
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8200
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 3
        startupProbe:
          httpGet:
            path: /health/startup
            port: 8200
          initialDelaySeconds: 0
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 30  # 30 * 5 = 150s max startup
```

---

## 5. Startup Optimization Techniques

### 5.1 Parallel Initialization

```python
# Parallel startup for independent services
async def parallel_startup(services: List[Service]):
    startup_tasks = []
    
    # Group services by wave
    waves = group_by_dependencies(services)
    
    for wave in waves:
        # Start all services in wave simultaneously
        wave_tasks = [
            asyncio.create_task(service.start())
            for service in wave
        ]
        
        # Wait for all in wave to be healthy
        results = await asyncio.gather(*wave_tasks, return_exceptions=True)
        
        # Check for failures
        for service, result in zip(wave, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to start {service.name}: {result}")
                # Implement retry or fallback strategy
```

### 5.2 Lazy Loading Strategy

```yaml
# Configuration for lazy loading
lazy_loading:
  ai_engine:
    models:
      preload:  # Load immediately
        - phi-2  # Small, frequently used
      on_demand:  # Load when first requested
        - whisper-large-v3  # Large, less frequent
        - xtts-v2  # Large, specific use case
    cache_strategy:
      max_models_in_memory: 3
      eviction_policy: lru
      idle_timeout_minutes: 30
```

### 5.3 Circuit Breaker Pattern

```python
# Circuit breaker for dependency failures
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        
    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise CircuitOpenError("Circuit breaker is open")
                
        try:
            result = await func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = "open"
                
            raise e
```

---

## 6. Monitoring & Alerting Strategy

### 6.1 Startup Metrics to Track

```yaml
startup_metrics:
  - metric: startup_time_seconds
    labels: [service, group, wave]
    alert_threshold: 300  # Alert if > 5 minutes
    
  - metric: health_check_duration_ms
    labels: [service, check_type]
    alert_threshold: 5000  # Alert if > 5 seconds
    
  - metric: dependency_check_failures
    labels: [service, dependency]
    alert_threshold: 3  # Alert after 3 consecutive failures
    
  - metric: restart_count
    labels: [service, reason]
    alert_threshold: 5  # Alert after 5 restarts
```

### 6.2 Prometheus Alert Rules

```yaml
groups:
  - name: cascade_startup_alerts
    rules:
      - alert: ServiceStartupTimeout
        expr: startup_time_seconds > 300
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.service }} startup timeout"
          description: "{{ $labels.service }} has taken more than 5 minutes to start"
          
      - alert: CriticalServiceDown
        expr: up{group="core_platform"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Critical service {{ $labels.service }} is down"
          description: "Core platform service {{ $labels.service }} has been down for 30s"
```

---

## 7. Rollback Strategy

### 7.1 Health-Based Rollback

```yaml
rollback_policy:
  health_check_window: 300s  # 5 minutes after deployment
  failure_conditions:
    - condition: health_check_failures > 50%
      action: immediate_rollback
    - condition: critical_service_unhealthy
      action: immediate_rollback
    - condition: error_rate > 10%
      action: gradual_rollback
  rollback_stages:
    - pause_new_deployment
    - route_traffic_to_old
    - terminate_unhealthy_new
    - restore_old_version
```

---

## Next Steps
1. Implement health check endpoints in all agents
2. Create startup orchestration scripts
3. Setup monitoring dashboards
4. Test failure scenarios and recovery
5. Document rollback procedures