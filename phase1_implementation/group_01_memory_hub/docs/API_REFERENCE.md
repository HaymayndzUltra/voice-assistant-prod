# 📚 MemoryHub API Reference

**Complete API documentation for MemoryHub Unified v2.0.0**

## 🌐 Base URL

```
http://localhost:7010
```

## 🔐 Authentication

MemoryHub uses **JWT Bearer Token** authentication with dynamic trust scoring.

### Get Authentication Token

```http
POST /auth/token
Content-Type: application/json

{
  "username": "user1",
  "password": "password123",
  "agent_name": "optional_agent_name"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "user_id": "user1",
    "trust_score": 0.75
  }
}
```

### Use Token

Include in request headers:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

---

## 🏠 Core Endpoints

### Root Status

```http
GET /
```

**Response:**
```
MemoryHub Unified v2.0 - TRUE CONSOLIDATION COMPLETE ✅🚀
```

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "memory_hub_unified",
  "version": "2.0.0",
  "consolidation_complete": true,
  "legacy_routers": "removed",
  "timestamp": "2024-01-15T10:30:00Z",
  "unified_storage": "healthy",
  "redis_databases": {
    "cache_db0": "active",
    "sessions_db1": "active",
    "knowledge_db2": "active",
    "auth_db3": "active"
  },
  "semantic_search": "healthy",
  "background_monitor": "healthy"
}
```

### Metrics

```http
GET /metrics
```

**Response:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "memory_hub_unified",
  "consolidation_status": "complete",
  "redis": {
    "connected_clients": 5,
    "used_memory": "150MB",
    "keyspace_hits": 1250
  },
  "sqlite": {
    "documents": 150,
    "sessions": 25
  },
  "embeddings": {
    "total_embeddings": 150,
    "active_embeddings": 150,
    "model_name": "all-MiniLM-L6-v2"
  }
}
```

---

## 🗂️ Key-Value Storage

### Store Key-Value

```http
POST /kv
Authorization: Bearer <token>
Content-Type: application/json

{
  "key": "user_preference",
  "value": "dark_mode",
  "namespace": "app_settings",
  "expire": 3600
}
```

**Parameters:**
- `key` (string, required): Storage key
- `value` (string, required): Storage value
- `namespace` (string, optional): Namespace for isolation (default: "memory_client")
- `expire` (integer, optional): TTL in seconds

**Response:**
```json
{
  "status": "success",
  "key": "user_preference",
  "namespace": "app_settings"
}
```

### Get Key-Value

```http
GET /kv/{namespace}/{key}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "key": "user_preference",
  "value": "dark_mode",
  "namespace": "app_settings",
  "exists": true
}
```

### List Keys

```http
GET /kv/{namespace}?pattern=user_*
Authorization: Bearer <token>
```

**Query Parameters:**
- `pattern` (string, optional): Key pattern (default: "*")

**Response:**
```json
{
  "namespace": "app_settings",
  "pattern": "user_*",
  "keys": ["user_preference", "user_theme", "user_language"],
  "count": 3
}
```

---

## 📄 Document Storage

### Store Document

```http
POST /doc
Authorization: Bearer <token>
Content-Type: application/json

{
  "doc_id": "user_manual_v1",
  "title": "User Manual",
  "content": "This is a comprehensive guide for using the system...",
  "namespace": "documentation",
  "metadata": {
    "version": "1.0",
    "author": "team",
    "category": "manual"
  }
}
```

**Parameters:**
- `doc_id` (string, required): Unique document identifier
- `title` (string, required): Document title
- `content` (string, required): Document content
- `namespace` (string, optional): Namespace for isolation (default: "knowledge_base")
- `metadata` (object, optional): Additional metadata

**Response:**
```json
{
  "status": "success",
  "doc_id": "user_manual_v1",
  "namespace": "documentation",
  "embedding_id": "documentation:a1b2c3d4e5f6",
  "storage_id": 15
}
```

### Get Document

```http
GET /doc/{namespace}/{doc_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "doc_id": "user_manual_v1",
  "title": "User Manual",
  "content": "This is a comprehensive guide for using the system...",
  "namespace": "documentation",
  "metadata": {
    "version": "1.0",
    "author": "team",
    "category": "manual"
  },
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:00:00Z"
}
```

### List Documents

```http
GET /doc/{namespace}?limit=50&offset=0
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (integer, optional): Max results (1-1000, default: 50)
- `offset` (integer, optional): Results offset (default: 0)

**Response:**
```json
{
  "namespace": "documentation",
  "documents": [
    {
      "doc_id": "user_manual_v1",
      "title": "User Manual",
      "created_at": "2024-01-15T09:00:00Z",
      "updated_at": "2024-01-15T09:00:00Z"
    }
  ],
  "limit": 50,
  "offset": 0
}
```

---

## 🔍 Semantic Search

### Search Embeddings

```http
POST /embedding/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "how to configure the system",
  "namespace": "documentation",
  "limit": 10,
  "min_similarity": 0.7
}
```

**Parameters:**
- `query` (string, required): Search query
- `namespace` (string, optional): Limit search to namespace
- `limit` (integer, optional): Max results (default: 10)
- `min_similarity` (float, optional): Minimum similarity threshold (0.0-1.0)

**Response:**
```json
{
  "query": "how to configure the system",
  "namespace": "documentation",
  "results": [
    {
      "id": "documentation:a1b2c3d4e5f6",
      "namespace": "documentation",
      "content": "Configuration Guide: To configure the system...",
      "doc_id": "config_guide_v1",
      "category": "document",
      "similarity": 0.92,
      "metadata": {
        "version": "1.0",
        "author": "team"
      },
      "created_at": "2024-01-15T08:00:00Z"
    }
  ],
  "count": 1
}
```

### Create Embedding

```http
POST /embedding
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "This is content to embed",
  "namespace": "custom_embeddings",
  "doc_id": "custom_doc_1",
  "category": "custom",
  "metadata": {
    "source": "user_input"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "embedding_id": "custom_embeddings:x1y2z3a4b5c6",
  "namespace": "custom_embeddings"
}
```

### Get Embedding

```http
GET /embedding/{embedding_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "custom_embeddings:x1y2z3a4b5c6",
  "namespace": "custom_embeddings",
  "content": "This is content to embed",
  "doc_id": "custom_doc_1",
  "category": "custom",
  "metadata": {
    "source": "user_input"
  },
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Embedding Statistics

```http
GET /embedding/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total_embeddings": 150,
  "active_embeddings": 150,
  "deleted_embeddings": 0,
  "namespace_counts": {
    "documentation": 50,
    "knowledge_base": 75,
    "custom_embeddings": 25
  },
  "model_name": "all-MiniLM-L6-v2",
  "dimension": 384
}
```

---

## 👥 Session Management

### Create Session

```http
POST /session
Authorization: Bearer <token>
Content-Type: application/json

{
  "session_id": "user1_session_20240115",
  "user_id": "user1",
  "data": {
    "preferences": {
      "theme": "dark",
      "language": "en"
    },
    "last_activity": "2024-01-15T10:00:00Z",
    "login_time": "2024-01-15T09:00:00Z"
  },
  "namespace": "user_sessions",
  "expires_hours": 24
}
```

**Parameters:**
- `session_id` (string, required): Unique session identifier
- `user_id` (string, required): User identifier
- `data` (object, required): Session data
- `namespace` (string, optional): Namespace for isolation (default: "session_memory")
- `expires_hours` (integer, optional): Session TTL in hours

**Response:**
```json
{
  "status": "success",
  "session_id": "user1_session_20240115",
  "namespace": "user_sessions",
  "storage_id": 25
}
```

### Get Session

```http
GET /session/{namespace}/{session_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "session_id": "user1_session_20240115",
  "user_id": "user1",
  "data": {
    "preferences": {
      "theme": "dark",
      "language": "en"
    },
    "last_activity": "2024-01-15T10:00:00Z",
    "login_time": "2024-01-15T09:00:00Z"
  },
  "namespace": "user_sessions",
  "expires_at": "2024-01-16T09:00:00Z",
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

---

## 🔐 Authentication

### Get Current User

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user_id": "user1",
  "username": "user1",
  "roles": ["user"],
  "agent_name": null,
  "trust_score": 0.75,
  "metadata": {}
}
```

### Create Agent Token

```http
POST /auth/agent-token
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "agent_name": "CoreOrchestrator"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "agent_name": "CoreOrchestrator"
}
```

---

## 🔍 Verification

### Consolidation Status

```http
GET /verification/consolidation-status
```

**Response:**
```json
{
  "consolidation_complete": true,
  "implementation_approach": "TRUE_CONSOLIDATION",
  "legacy_proxy_pattern": "COMPLETELY_REMOVED",
  "unified_components_active": {
    "unified_storage_manager": true,
    "embedding_service": true,
    "auth_middleware": true,
    "proactive_monitor": true
  },
  "critical_features_implemented": {
    "unified_redis_sqlite_layer": "✅ Multi-database Redis + SQLite",
    "neuro_symbolic_search": "✅ FAISS + sentence-transformers",
    "jwt_auth_trust_scoring": "✅ Dynamic trust scoring",
    "proactive_context_monitoring": "✅ Background coroutines",
    "namespacing_prevention": "✅ Schema collision prevention",
    "single_process": "✅ No subprocess agents"
  },
  "endpoints_replace_legacy_routers": {
    "/kv": "MemoryClient router → Unified storage",
    "/doc": "KnowledgeBase router → Unified SQLite + auto-embedding",
    "/embedding": "UnifiedMemoryReasoningAgent router → Vector search",
    "/session": "SessionMemoryAgent router → Unified sessions",
    "/auth": "AuthenticationAgent + TrustScorer routers → JWT + trust"
  },
  "production_readiness": "COMPLETE"
}
```

---

## ⚠️ Error Responses

### Standard Error Format

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

### Common Status Codes

- **200**: Success
- **201**: Created
- **400**: Bad Request
- **401**: Unauthorized (missing/invalid token)
- **403**: Forbidden (insufficient trust score/permissions)
- **404**: Not Found
- **422**: Validation Error
- **500**: Internal Server Error
- **503**: Service Unavailable

### Authentication Errors

```json
{
  "detail": "Authentication required",
  "status_code": 401
}
```

```json
{
  "detail": "Insufficient trust score: 0.65 < 0.70",
  "status_code": 403
}
```

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "key"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "status_code": 422
}
```

---

## 📈 Rate Limiting

MemoryHub implements intelligent rate limiting based on trust scores:

- **High Trust (>0.8)**: 1000 req/min
- **Medium Trust (0.5-0.8)**: 500 req/min  
- **Low Trust (<0.5)**: 100 req/min

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642248000
```

---

## 🔗 SDKs and Client Libraries

### Python SDK

```python
from memoryhub_client import MemoryHubClient

# Initialize client
client = MemoryHubClient(
    base_url="http://localhost:7010",
    username="user1",
    password="password123"
)

# Store key-value
client.kv.set("user_pref", "dark_mode", namespace="app_settings")

# Get key-value
value = client.kv.get("user_pref", namespace="app_settings")

# Store document
doc_id = client.docs.store(
    doc_id="manual_v1",
    title="User Manual",
    content="Guide content...",
    namespace="docs"
)

# Semantic search
results = client.embeddings.search(
    query="configuration guide",
    namespace="docs",
    limit=5
)
```

### JavaScript SDK

```javascript
import { MemoryHubClient } from '@memoryhub/client';

const client = new MemoryHubClient({
  baseUrl: 'http://localhost:7010',
  username: 'user1',
  password: 'password123'
});

// Store key-value
await client.kv.set('user_pref', 'dark_mode', { namespace: 'app_settings' });

// Semantic search
const results = await client.embeddings.search({
  query: 'configuration guide',
  namespace: 'docs',
  limit: 5
});
```

---

## 📝 OpenAPI Schema

Full OpenAPI 3.0 schema available at:
```
GET /openapi.json
```

Interactive API documentation:
```
GET /docs
```

Alternative documentation:
```
GET /redoc
```

---

**MemoryHub API Reference v2.0.0** - Complete API documentation ✅ 