Memory Fusion Hub – Implementation Blueprint
Author: O3-Pro Architecture Group | Revision: 2025-08-07
Target Environment: dual-machine cluster (main_pc, pc2) running Python 3.10+
1. High-Level Overview
Memory Fusion Hub (MFH) replaces seven legacy agents that handle episodic, semantic, and session memory.
Primary responsibilities:
Unified CRUD API for memory objects (ZMQ + gRPC façade).
Adaptive caching (Redis) and persistence (SQLite / Postgres).
Cross-host replication & event-sourcing for replay / audit.
MFH is designed as a stateless micro-service; horizontal replicas share state via Redis and an append-only event log.
2. Directory & File Layout


memory_fusion_hub/
├── __init__.py
├── app.py                   # bootstrap & CLI entry-point
├── config/
│   ├── default.yaml         # base config (machine-agnostic)
│   ├── main_pc.yaml         # host-specific overrides
│   └── pc2.yaml
├── adapters/
│   ├── sqlite_adapter.py    # persistent store
│   ├── postgres_adapter.py  # optional prod store
│   └── redis_cache.py
├── core/
│   ├── models.py            # Pydantic data models
│   ├── repository.py        # storage abstractions
│   ├── fusion_service.py    # main business logic
│   ├── event_log.py         # event-sourcing writer/reader
│   └── telemetry.py         # Prometheus/Grafana metrics
├── transport/
│   ├── zmq_server.py        # REQ/REP façade
│   └── grpc_server.py       # gRPC façade (proto compiled)
├── resiliency/
│   ├── circuit_breaker.py   # extracted canonical copy
│   └── bulkhead.py          # import from `common/resiliency`
├── requirements.txt
└── README.md

3. Dependencies & Best-Practice Hooks
Add these to requirements.txt:

pydantic==1.10.13
pyzmq==26.0.3
grpcio==1.63.0
grpcio-tools==1.63.0
redis==5.0.1
sqlalchemy==2.0.30
aiosqlite==0.19.0
prometheus-client==0.20.0
tenacity==8.2.3             # for retry decorator

Best-practice integration:
@retry_with_backoff → import from common/utils/network_util.py.
CircuitBreaker canonicalised into resiliency/circuit_breaker.py.
PathManager, env_helpers, Bulkhead, UnifiedConfigLoader all imported directly.
4. Configuration Schema (config/default.yaml)

title: MemoryFusionHubConfig
version: 1.0

server:
  zmq_port: 5713
  grpc_port: 5714
  max_workers: 8

storage:
  write_strategy: "event_sourcing"   # options: direct, event_sourcing
  sqlite_path: "${MFH_SQLITE:/workspace/memory.db}"
  postgres_url: "${POSTGRES_URL:}"
  redis_url: "${REDIS_URL:redis://localhost:6379/0}"
  cache_ttl_seconds: 900

replication:
  enabled: true
  event_topic: "memory_events"
  nats_url: "${NATS_URL:nats://localhost:4222}"

resilience:
  circuit_breaker:
    failure_threshold: 5
    reset_timeout: 30
  bulkhead:
    max_concurrent: 32
    max_queue_size: 128


Host overrides (main_pc.yaml, pc2.yaml) simply change ports or paths.
5. Class-Level Design
5.1 core/models.py
Define Pydantic objects: MemoryItem, SessionData, KnowledgeRecord, MemoryEvent, with JSON-schema generation.
5.2 core/repository.py
Interface AbstractRepository with async methods:


class AbstractRepository(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[BaseModel]: ...
    @abstractmethod
    async def put(self, key: str, value: BaseModel) -> None: ...
    @abstractmethod
    async def delete(self, key: str) -> None: ...

Concrete implementations: SQLiteRepository, PostgresRepository, each wrapped with CircuitBreaker + @retry_with_backoff.
5.3 adapters/redis_cache.py
TTL-aware cache with lazy connection via env_helpers.get_env.
5.4 core/event_log.py
Append-only log writer; uses Redis Streams or NATS JetStream; publishes MemoryEvent protobuf.
5.5 core/fusion_service.py (heart of MFH)


class FusionService:
    def __init__(self, cfg: FusionConfig):
        self.cache = RedisCache(cfg.storage.redis_url, cfg.storage.cache_ttl_seconds)
        self.repo = build_repo(cfg.storage)          # returns appropriate repository
        self.event_log = EventLog(cfg.replication)
        self.metrics = Telemetry()                   # Prometheus counters & histograms
        self.lock = asyncio.Lock()                   # to guard write sequence

    @retry_with_backoff(...)
    async def get(self, key: str) -> MemoryItem:
        cached = await self.cache.get(key)
        if cached:
            self.metrics.cache_hits.inc()
            return cached
        self.metrics.cache_misses.inc()
        item = await self.repo.get(key)
        await self.cache.put(key, item)
        return item

    @bulkhead_guard
    async def put(self, key: str, item: MemoryItem):
        async with self.lock:                       # ensure event order
            await self.repo.put(key, item)
            await self.cache.put(key, item)
            await self.event_log.publish("PUT", item)

    async def delete(self, key: str):
        await self.repo.delete(key)
        await self.cache.evict(key)
        await self.event_log.publish("DELETE", key)

Decorators @bulkhead_guard and @retry_with_backoff wrap external calls.
6. Transport Layer
6.1 ZeroMQ REQ/REP (transport/zmq_server.py)
Use common/net/zmq_client.py pattern for sockets; each request embeds action & payload JSON; marshalled via Pydantic.
6.2 gRPC (transport/grpc_server.py)
Proto file (memory_fusion.proto) generates MemoryFusionService with Get, Put, Delete, BatchGet RPCs; compiled in CI.
Both servers call a shared FusionService instance; start inside a ThreadPoolExecutor (max_workers from config).
7. Bootstrap (app.py)
Load config via UnifiedConfigLoader (default.yaml + host override + env vars).
Initialise FusionService.
Start Prometheus HTTP endpoint on /metrics.
Launch ZMQ + gRPC servers asynchronously.
Graceful shutdown on SIGTERM / SIGINT (flush event log, close DB).
8. Development & Deployment Steps
Clone repo / create memory_fusion_hub/ directory.
Copy canonical utilities:

   cp common/resiliency/bulkhead.py  memory_fusion_hub/resiliency/
   cp main_pc_code/agents/memory_client.py memory_fusion_hub/resiliency/circuit_breaker.py

Keep only class definition & tests.
Install dependencies: pip install -r memory_fusion_hub/requirements.txt.
Compile gRPC stubs:

   python -m grpc_tools.protoc -I. --python_out=memory_fusion_hub/ --grpc_python_out=memory_fusion_hub/ memory_fusion.proto

Unit Tests (pytest) for repository, cache, fusion logic.
Load Test with Locust; verify ≤ 20 ms p95 per single read under 1 k rps.
Deploy two replicas per host behind zmq.ROUTER socket.
Migrate Traffic: switch existing agents’ mem_port to 5713; decommission legacy memory agents.

. Risk Mitigation Checklist ✅
Item	Mitigation
Single-process bottleneck	Stateless replicas + bulkhead isolation
Data loss on crash	Event-sourcing + periodic snapshot to durable DB
Schema drift	Pydantic models versioned; enforce schema_version field
Backwards compatibility	Maintain old message schema for 1 release cycle; provide shim translator
Security	Use env_helpers.get_env("MFH_API_KEY", required=True) for gRPC auth; TLS termination via sidecar
Observability	Prometheus metrics, structured JSON logs via structlog
Resilience	CircuitBreaker around DB/Redis; retry with exponential backoff; graceful degrade to read-only mode
10. Final Verification Gate
Static Analysis: mypy (--strict), flake8 (< 0.9 score).
Integration Tests: Legacy agent (LearningManager) performs 1 k sequential reads/writes without error.
Failover Drill: kill primary MFH process; replica continues serving.
Cross-Machine Consistency: random write on pc2 replica appears on main_pc replica within 200 ms (NATS stream).
Audit Log Review: event_log.replay() rehydrates DB to identical checksum.
When all checks are ✅, Memory Fusion Hub is production-ready and the seven superseded agents can be archived.
