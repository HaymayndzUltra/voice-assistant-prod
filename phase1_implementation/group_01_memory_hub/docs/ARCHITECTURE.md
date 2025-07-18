# 🏗️ MemoryHub Architecture Guide

**System architecture for MemoryHub Unified v2.0.0**

## 🎯 Overview

MemoryHub Unified represents a **true consolidation architecture** that replaces 8+ separate legacy agents with a single, cohesive FastAPI service. This document details the architectural decisions, component design, and consolidation strategy.

## 📊 Architectural Transformation

### Before: Legacy Multi-Agent Architecture

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ MemoryClient    │  │SessionMemoryAgt │  │ KnowledgeBase   │
│ Port: 5713      │  │ Port: 5574      │  │ Port: 5715      │
│ Redis: db0      │  │ SQLite: sess.db │  │ SQLite: kb.db   │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│MemoryOrchestrat │  │UnifiedMemoryRea │  │ ContextManager  │
│ Port: 7140      │  │ Port: 7105      │  │ Port: 7111      │
│ Redis: dbX      │  │ Redis: dbY      │  │ SQLite: ctx.db  │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│ExperienceTracker│  │ CacheManager    │
│ Port: 7112      │  │ Port: 7102      │
│ SQLite: exp.db  │  │ Redis: dbZ      │
└─────────────────┘  └─────────────────┘

Problems:
❌ 8+ separate processes
❌ Individual Redis/SQLite connections
❌ Duplicate logic and schema conflicts
❌ Complex inter-agent communication
❌ Difficult deployment and monitoring
```

### After: Unified Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MemoryHub Unified                         │
│                            Port: 7010                              │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │UnifiedStorageMgr│  │ EmbeddingService│  │  AuthMiddleware │    │
│  │Redis Multi-DB   │  │FAISS + sentence │  │JWT + Trust Score│    │
│  │SQLite Unified   │  │   transformers  │  │  Dynamic Auth   │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │             ProactiveContextMonitor                         │  │
│  │        6 Background Coroutines (Async Tasks)              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Endpoints                       │  │
│  │ /kv  /doc  /embedding  /session  /auth  /verification      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

Benefits:
✅ Single FastAPI process
✅ Shared resource pools (4 Redis DBs, 1 SQLite)
✅ Unified schemas with namespacing
✅ Integrated authentication and monitoring
✅ Simplified deployment and observability
```

---

## 🧩 Core Components

### 1. UnifiedStorageManager

**Purpose**: Centralized storage layer combining Redis (multi-database) and SQLite with automatic namespacing.

**Architecture**:
```
UnifiedStorageManager
├── Redis Connection Pools (4 databases)
│   ├── db0: Cache (key-value storage)
│   ├── db1: Sessions (session management)
│   ├── db2: Knowledge (document metadata)
│   └── db3: Authentication (trust scores, tokens)
├── SQLite Connection
│   ├── documents table (with namespace column)
│   ├── sessions table (with namespace column)
│   └── experiences table (with namespace column)
└── Namespacing Logic
    ├── Key prefixing: {namespace_prefix}:{key}
    ├── Schema isolation
    └── Collision prevention
```

**Key Features**:
- **Multi-database Redis**: Isolates different data types
- **Shared Connection Pooling**: Efficient resource utilization
- **Automatic Namespacing**: Prevents schema collisions
- **Background Cleanup**: Automated session expiry and cache maintenance
- **Transaction Support**: Atomic operations across Redis/SQLite

**Example Implementation**:
```python
# Namespaced key generation
def _get_namespaced_key(self, namespace: str, key: str) -> str:
    prefix = self.namespaces.get(namespace, namespace)
    return f"{prefix}:{key}"

# Redis operation with namespacing
async def redis_get(self, db_name: str, namespace: str, key: str):
    namespaced_key = self._get_namespaced_key(namespace, key)
    return await self._redis_pools[db_name].get(namespaced_key)
```

### 2. EmbeddingService

**Purpose**: Unified semantic search using vector embeddings with FAISS and sentence-transformers.

**Architecture**:
```
EmbeddingService
├── SentenceTransformer Model
│   ├── Model: all-MiniLM-L6-v2 (384 dimensions)
│   ├── Text → Vector encoding
│   └── Batch processing support
├── FAISS Index
│   ├── IndexFlatIP (cosine similarity)
│   ├── Vector storage and retrieval
│   └── Fast similarity search
├── Metadata Management
│   ├── Embedding metadata storage
│   ├── Namespace organization
│   └── Index persistence (save/load)
└── Search Operations
    ├── Semantic similarity search
    ├── Namespace filtering
    └── Threshold-based results
```

**Key Features**:
- **Production-Ready Models**: sentence-transformers with 384-dimensional vectors
- **Fast Similarity Search**: FAISS IndexFlatIP for cosine similarity
- **Persistent Storage**: Index and metadata saved to disk
- **Namespace Support**: Search within specific namespaces
- **Auto-Embedding**: Documents automatically generate embeddings
- **Index Maintenance**: Background rebuilding and cleanup

**Search Flow**:
```
Query Text → sentence-transformers → Normalized Vector → FAISS Search → 
Similarity Scores → Namespace Filtering → Results with Metadata
```

### 3. AuthMiddleware

**Purpose**: JWT authentication with dynamic trust scoring and role-based access control.

**Architecture**:
```
AuthMiddleware
├── JWT Management
│   ├── Token generation (HS256)
│   ├── Token validation
│   └── Expiry handling
├── Trust Scoring System
│   ├── Base scores by role/agent
│   ├── Dynamic calculation from interaction history
│   ├── Redis caching (1-hour TTL)
│   └── Violation tracking
├── FastAPI Integration
│   ├── Dependency injection
│   ├── Route-level security
│   └── Trust threshold enforcement
└── Interaction Tracking
    ├── Success/failure recording
    ├── Trust score updates
    └── Security violation detection
```

**Trust Score Calculation**:
```python
# Dynamic trust scoring algorithm
def _calculate_trust_score(self, base_score: float, interaction_data: Dict):
    successful = interaction_data.get("successful_requests", 0)
    failed = interaction_data.get("failed_requests", 0)
    violations = interaction_data.get("violations", 0)
    
    total_requests = successful + failed
    if total_requests == 0:
        return base_score
    
    # Success ratio factor
    success_ratio = successful / total_requests
    success_factor = min(success_ratio * 1.2, 1.0)
    
    # Violation penalty
    violation_penalty = min(violations * 0.1, 0.5)
    
    # Activity bonus
    activity_bonus = min(total_requests / 1000, 0.1)
    
    # Calculate final score
    final_score = base_score * success_factor - violation_penalty + activity_bonus
    return max(0.0, min(1.0, final_score))
```

### 4. ProactiveContextMonitor

**Purpose**: Background monitoring system with 6 async coroutines for proactive context management.

**Architecture**:
```
ProactiveContextMonitor
├── Background Coroutines (6 tasks)
│   ├── Session Monitor (5min intervals)
│   ├── Memory Cleanup (1hr intervals)
│   ├── Embedding Maintenance (24hr intervals)
│   ├── Context Analysis (1min intervals)
│   ├── Health Check (2min intervals)
│   └── Event Processor (real-time)
├── Event Processing
│   ├── Async event queue
│   ├── Event handlers registration
│   └── Context change detection
├── Analytics & Insights
│   ├── Activity pattern analysis
│   ├── Performance metrics collection
│   └── Predictive maintenance
└── Lifecycle Management
    ├── FastAPI lifespan integration
    ├── Graceful startup/shutdown
    └── Task health monitoring
```

**Background Tasks**:
1. **Session Monitor**: Tracks session activity, cleans expired sessions
2. **Memory Cleanup**: Removes old cache entries and temporary data
3. **Embedding Maintenance**: Rebuilds FAISS index when needed
4. **Context Analysis**: Analyzes usage patterns and generates insights
5. **Health Check**: Monitors component health and system status
6. **Event Processor**: Processes real-time context events

---

## 🔗 Integration Architecture

### FastAPI Application Structure

```python
# Application initialization with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize unified components
    global storage_manager, embedding_service, auth_middleware, context_monitor
    
    # Storage layer initialization
    storage_manager = UnifiedStorageManager(storage_config)
    await storage_manager.initialize()
    
    # Semantic search initialization  
    embedding_service = EmbeddingService(embedding_config)
    await embedding_service.initialize()
    
    # Authentication middleware
    auth_middleware = init_auth_middleware(auth_config, storage_manager)
    
    # Background monitoring
    context_monitor = ProactiveContextMonitor(storage_manager, embedding_service)
    await context_monitor.start()
    
    yield  # Application runs
    
    # Cleanup
    await context_monitor.stop()
    await embedding_service.close()
    await storage_manager.close()
```

### Endpoint Integration Pattern

```python
# Example: Document storage with integrated features
@app.post("/doc")
async def store_document(
    request: DocumentRequest,
    user: User = Depends(require_auth(min_trust=0.5))  # JWT + Trust auth
):
    # Store in unified SQLite (with namespacing)
    doc_id = await storage_manager.store_document(
        request.namespace, request.doc_id, request.title, 
        request.content, request.metadata
    )
    
    # Auto-generate embedding (semantic search)
    embedding_id = await embedding_service.add_embedding(
        namespace=request.namespace,
        content=f"{request.title}\n{request.content}",
        doc_id=request.doc_id
    )
    
    # Emit context event (background monitoring)
    await emit_context_event("knowledge_update", request.namespace, {
        "operation": "store", 
        "doc_id": request.doc_id,
        "embedding_generated": embedding_id is not None
    }, user)
    
    return {"status": "success", "doc_id": request.doc_id, "embedding_id": embedding_id}
```

---

## 📊 Data Flow Architecture

### 1. Storage Operations Flow

```
Client Request → JWT Validation → Trust Score Check → 
Namespace Resolution → Storage Operation → Context Event → Response
```

**Example: Key-Value Storage**
1. **Request**: `POST /kv` with authentication token
2. **Authentication**: JWT validation + trust score check (≥0.5 required)
3. **Namespacing**: Key prefixed with namespace (`app_settings:user_pref`)
4. **Storage**: Redis operation on appropriate database (db0 for cache)
5. **Monitoring**: Context event emitted for background analysis
6. **Response**: Success confirmation with namespace info

### 2. Semantic Search Flow

```
Search Query → Authentication → Embedding Generation → 
FAISS Search → Namespace Filtering → Context Tracking → Results
```

**Example: Document Search**
1. **Query**: `POST /embedding/search` with semantic query
2. **Authentication**: JWT validation + trust score check (≥0.3 required)
3. **Embedding**: Query converted to 384-dimensional vector
4. **Search**: FAISS similarity search with cosine distance
5. **Filtering**: Results filtered by namespace and similarity threshold
6. **Tracking**: Search patterns recorded for analytics
7. **Results**: Ranked results with similarity scores and metadata

### 3. Session Management Flow

```
Session Request → Authentication → Expiry Calculation → 
Storage with Namespacing → Background Cleanup → Response
```

**Example: Session Creation**
1. **Request**: `POST /session` with session data
2. **Authentication**: JWT validation + trust score check (≥0.5 required)
3. **Expiry**: TTL calculated from `expires_hours` parameter
4. **Storage**: SQLite insertion with namespace and expiry
5. **Cleanup**: Background coroutine schedules cleanup
6. **Response**: Session confirmation with storage ID

---

## 🔒 Security Architecture

### Authentication Layer

```
Request → JWT Token → Signature Validation → 
Trust Score Lookup → Role Verification → Access Granted/Denied
```

**Security Features**:
- **JWT Tokens**: HS256 signed tokens with configurable expiry
- **Dynamic Trust Scoring**: Based on interaction history and violations
- **Role-Based Access**: User, agent, and system roles with different permissions
- **Rate Limiting**: Trust-based rate limiting (high trust = higher limits)
- **Interaction Tracking**: Success/failure/violation recording for trust updates

### Trust Score Levels

| **Trust Score** | **Access Level** | **Rate Limit** | **Typical Users** |
|-----------------|------------------|----------------|-------------------|
| **0.9-1.0** | Full access | 1000 req/min | System agents, admins |
| **0.7-0.8** | High access | 500 req/min | Trusted applications |
| **0.5-0.6** | Standard access | 300 req/min | Regular users |
| **0.3-0.4** | Limited access | 100 req/min | New users |
| **0.0-0.2** | Restricted | 50 req/min | Flagged users |

### Namespacing Security

```
Storage Key: {namespace_prefix}:{actual_key}
SQLite Row: namespace='user_app', doc_id='document_1'
```

**Isolation Benefits**:
- **Cross-tenant Security**: Prevents data leakage between namespaces
- **Schema Protection**: Each namespace maintains independent schema
- **Access Control**: Namespace-based permission checking
- **Legacy Compatibility**: Maintains original agent data boundaries

---

## 📈 Performance Architecture

### Connection Pooling

```
┌─────────────────────────────────────────────────────────────┐
│                 Connection Management                       │
├─────────────────────────────────────────────────────────────┤
│ Redis Connection Pools (Async)                             │
│ ├── Cache Pool (db0): 10 connections                       │
│ ├── Sessions Pool (db1): 5 connections                     │
│ ├── Knowledge Pool (db2): 5 connections                    │
│ └── Auth Pool (db3): 5 connections                         │
├─────────────────────────────────────────────────────────────┤
│ SQLite Connection                                           │
│ └── Single connection with connection pooling              │
├─────────────────────────────────────────────────────────────┤
│ FAISS Index                                                 │
│ └── In-memory index with disk persistence                  │
└─────────────────────────────────────────────────────────────┘
```

### Memory Management

**Component Memory Usage**:
- **FastAPI Application**: ~50MB base
- **UnifiedStorageManager**: ~30MB (connection pools)
- **EmbeddingService**: ~300MB (sentence-transformer model + FAISS index)
- **AuthMiddleware**: ~10MB (JWT libraries, trust data)
- **ProactiveContextMonitor**: ~20MB (background tasks, event queue)
- **Total Estimated**: ~410MB (vs. 2GB+ for legacy multi-agent)

### Performance Optimizations

1. **Async Operations**: All I/O operations are async/await
2. **Connection Reuse**: Pooled connections across requests
3. **Batch Processing**: Embedding generation supports batching
4. **Index Caching**: FAISS index kept in memory with periodic saves
5. **Trust Score Caching**: Redis cache for calculated trust scores
6. **Background Processing**: Non-critical tasks moved to background coroutines

---

## 🚀 Deployment Architecture

### Single Process Deployment

```bash
# Development
python -m memory_hub.memory_hub

# Production with Uvicorn
uvicorn memory_hub.memory_hub:app --host 0.0.0.0 --port 7010 --workers 4

# Production with Gunicorn
gunicorn memory_hub.memory_hub:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Container Architecture

```dockerfile
FROM python:3.9-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Download embedding model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 7010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD curl -f http://localhost:7010/health || exit 1

# Run application
CMD ["uvicorn", "memory_hub.memory_hub:app", "--host", "0.0.0.0", "--port", "7010"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memoryhub-unified
spec:
  replicas: 3
  selector:
    matchLabels:
      app: memoryhub-unified
  template:
    metadata:
      labels:
        app: memoryhub-unified
    spec:
      containers:
      - name: memoryhub
        image: memoryhub:v2.0.0
        ports:
        - containerPort: 7010
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: memoryhub-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 7010
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 7010
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 📊 Monitoring Architecture

### Health Check System

```python
async def health():
    health_status = {
        "status": "healthy",
        "service": "memory_hub_unified",
        "timestamp": datetime.now().isoformat()
    }
    
    # Check storage
    try:
        await storage_manager._redis_pools["cache"].ping()
        health_status["unified_storage"] = "healthy"
    except:
        health_status["unified_storage"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check embedding service
    try:
        stats = await embedding_service.get_stats()
        health_status["semantic_search"] = "healthy"
    except:
        health_status["semantic_search"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status
```

### Metrics Collection

**System Metrics**:
- Request throughput (req/s)
- Response times (P50, P95, P99)
- Error rates by endpoint
- Memory usage and garbage collection
- Connection pool utilization

**Business Metrics**:
- Documents stored per namespace
- Embedding search performance
- Session activity patterns
- Trust score distributions
- Authentication success rates

**Infrastructure Metrics**:
- Redis connection health
- SQLite query performance
- FAISS index size and search times
- Background task execution times

---

## 🔄 Migration Strategy

### Legacy Agent Replacement

| **Legacy Component** | **Migration Strategy** | **Data Migration** |
|----------------------|------------------------|-------------------|
| MemoryClient | Direct API mapping to `/kv` | Redis key migration with namespacing |
| SessionMemoryAgent | Session data to unified SQLite | SQLite → SQLite with namespace column |
| KnowledgeBase | Document storage + auto-embedding | Documents + embedding generation |
| UnifiedMemoryReasoningAgent | FAISS-based semantic search | Rebuild embeddings from documents |
| AuthenticationAgent | JWT middleware integration | User data + trust score calculation |
| TrustScorer | Integrated trust scoring | Interaction history migration |
| ProactiveContextMonitor | Background coroutines | Event logs → unified format |
| CacheManager | UnifiedStorageManager | Cache data with namespacing |

### Data Migration Process

1. **Pre-migration Analysis**: Audit existing data schemas and volumes
2. **Namespace Planning**: Define namespace mapping for each legacy agent
3. **Schema Migration**: Create unified schemas with namespace support
4. **Data Export**: Extract data from legacy agents with proper formatting
5. **Data Import**: Import to unified storage with namespace assignment
6. **Embedding Generation**: Generate embeddings for existing documents
7. **Validation**: Verify data integrity and completeness
8. **Cutover**: Switch traffic from legacy agents to unified service

---

## 🎯 Future Architecture Considerations

### Scalability Enhancements

- **Horizontal Scaling**: Multiple MemoryHub instances with shared Redis/SQLite
- **Database Sharding**: Distribute namespaces across multiple databases
- **Embedding Clustering**: Distributed FAISS index for large-scale search
- **Caching Layers**: Additional caching for frequently accessed data

### Advanced Features

- **Multi-tenant Support**: Enhanced namespacing for true multi-tenancy
- **Advanced Analytics**: ML-powered insights from context monitoring
- **Stream Processing**: Real-time event processing with Apache Kafka
- **Graph Database**: Knowledge graph capabilities for complex relationships

---

**MemoryHub Architecture v2.0.0** - True consolidation architecture achieved ✅🏗️ 