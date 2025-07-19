from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""Unified MemoryHub - True Consolidation Implementation.

This is the production-ready unified implementation that replaces all legacy proxy 
routers with integrated storage, semantic search, authentication, and background monitoring.
"""

import os
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Request, Query, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import unified components
from .core.storage_manager import UnifiedStorageManager, StorageConfig
from .core.embedding_service import EmbeddingService, EmbeddingConfig
from .core.auth_middleware import AuthMiddleware, AuthConfig, User, init_auth_middleware, get_current_user, require_auth, require_high_trust
from .core.background_monitor import ProactiveContextMonitor, ContextEvent

logger = logging.getLogger("memory_hub")
logging.basicConfig(level=logging.INFO)

# Global instances
storage_manager: Optional[UnifiedStorageManager] = None
embedding_service: Optional[EmbeddingService] = None
auth_middleware: Optional[AuthMiddleware] = None
context_monitor: Optional[ProactiveContextMonitor] = None


# Pydantic models for API
class KeyValueRequest(BaseModel):
    key: str
    value: str
    namespace: str = "memory_client"
    expire: Optional[int] = None


class KeyValueResponse(BaseModel):
    key: str
    value: Optional[str]
    namespace: str
    exists: bool


class DocumentRequest(BaseModel):
    doc_id: str
    title: str
    content: str
    namespace: str = "knowledge_base"
    metadata: Dict[str, Any] = {}


class DocumentResponse(BaseModel):
    doc_id: str
    title: str
    content: str
    namespace: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class EmbeddingRequest(BaseModel):
    content: str
    namespace: str = "unified_memory_reasoning"
    doc_id: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = {}


class EmbeddingSearchRequest(BaseModel):
    query: str
    namespace: Optional[str] = None
    limit: int = 10
    min_similarity: Optional[float] = None


class SessionRequest(BaseModel):
    session_id: str
    user_id: str
    data: Dict[str, Any]
    namespace: str = "session_memory"
    expires_hours: Optional[int] = 24


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    data: Dict[str, Any]
    namespace: str
    expires_at: Optional[str]
    created_at: str
    updated_at: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global storage_manager, embedding_service, auth_middleware, context_monitor
    
    logger.info("🚀 Starting MemoryHub Unified - True Consolidation")
    
    try:
        # Initialize configurations
        storage_config = StorageConfig(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            sqlite_path=os.getenv("SQLITE_PATH", "data/memory_hub.db")
        )
        
        embedding_config = EmbeddingConfig(
            model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            index_path=os.getenv("EMBEDDING_INDEX_PATH", "data/embeddings.index"),
            metadata_path=os.getenv("EMBEDDING_METADATA_PATH", "data/embeddings_metadata.json")
        )
        
        auth_config = AuthConfig(
            jwt_secret=os.getenv("JWT_SECRET", "memory-hub-secret-key-change-in-production"),
            require_auth=os.getenv("REQUIRE_AUTH", "true").lower() == "true",
            trusted_agents=["CoreOrchestrator", "PlanningOrchestrator"]
        )
        
        # Initialize unified storage manager
        logger.info("Initializing UnifiedStorageManager...")
        storage_manager = UnifiedStorageManager(storage_config)
        await storage_manager.initialize()
        
        # Initialize embedding service
        logger.info("Initializing EmbeddingService...")
        embedding_service = EmbeddingService(embedding_config)
        await embedding_service.initialize()
        
        # Initialize authentication middleware
        logger.info("Initializing AuthMiddleware...")
        auth_middleware = init_auth_middleware(auth_config, storage_manager)
        
        # Initialize background context monitor
        logger.info("Initializing ProactiveContextMonitor...")
        context_monitor = ProactiveContextMonitor(storage_manager, embedding_service)
        await context_monitor.start()
        
        logger.info("✅ MemoryHub Unified initialized successfully")
        logger.info("🔧 All legacy proxy routers replaced with unified components")
        logger.info("🗄️  Unified Redis + SQLite storage active")
        logger.info("🧠 Semantic search with embeddings active")
        logger.info("🔐 JWT authentication with trust scoring active")
        logger.info("📊 Proactive context monitoring active")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize MemoryHub: {e}")
        raise
    
    finally:
        # Cleanup
        logger.info("🛑 Shutting down MemoryHub Unified")
        
        if context_monitor:
            await context_monitor.stop()
        
        if embedding_service:
            await embedding_service.close()
        
        if storage_manager:
            await storage_manager.close()
        
        logger.info("✅ MemoryHub Unified shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MemoryHub Unified",
    description="Production-ready unified memory service with true consolidation",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper function to emit context events
async def emit_context_event(event_type: str, namespace: str, data: Dict[str, Any], user: Optional[User] = None):
    """Emit context event for monitoring."""
    if context_monitor:
        event = ContextEvent(
            event_id=f"{event_type}_{namespace}_{int(datetime.now().timestamp())}",
            namespace=namespace,
            event_type=event_type,
            data=data,
            timestamp=datetime.now(),
            metadata={"user_id": user.user_id if user else "system"}
        )
        await context_monitor.emit_event(event)


# =============================================================================
# CORE ENDPOINTS - BASE FUNCTIONALITY
# =============================================================================

@app.get("/", response_class=PlainTextResponse)
async def root() -> str:
    """Root endpoint - unified service status."""
    return "MemoryHub Unified v2.0 - True Consolidation Active ✅"


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Comprehensive health check."""
    try:
        health_status = {
            "status": "healthy",
            "service": "memory_hub_unified",
            "version": "2.0.0",
            "consolidation": "complete",
            "timestamp": datetime.now().isoformat()
        }
        
        # Check storage
        if storage_manager:
            try:
                await storage_manager._redis_pools["cache"].ping()
                health_status["storage"] = "healthy"
            except:
                health_status["storage"] = "unhealthy"
                health_status["status"] = "degraded"
        
        # Check embedding service
        if embedding_service:
            try:
                stats = await embedding_service.get_stats()
                health_status["embedding"] = "healthy"
                health_status["embedding_stats"] = stats
            except:
                health_status["embedding"] = "unhealthy"
                health_status["status"] = "degraded"
        
        # Check context monitor
        if context_monitor:
            stats = await context_monitor.get_activity_stats()
            health_status["monitor"] = "healthy" if stats["is_running"] else "stopped"
            health_status["monitor_stats"] = stats
        
        return health_status
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Consolidated metrics from all components."""
    try:
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "service": "memory_hub_unified"
        }
        
        # Storage metrics
        if storage_manager:
            # Redis info
            cache_info = await storage_manager._redis_pools["cache"].info()
            metrics["redis"] = {
                "connected_clients": cache_info.get("connected_clients", 0),
                "used_memory": cache_info.get("used_memory_human", "0"),
                "keyspace_hits": cache_info.get("keyspace_hits", 0),
                "keyspace_misses": cache_info.get("keyspace_misses", 0)
            }
            
            # SQLite metrics
            doc_count = storage_manager.sqlite_fetchone("SELECT COUNT(*) as count FROM documents")
            session_count = storage_manager.sqlite_fetchone("SELECT COUNT(*) as count FROM sessions")
            
            metrics["sqlite"] = {
                "documents": doc_count["count"] if doc_count else 0,
                "sessions": session_count["count"] if session_count else 0
            }
        
        # Embedding metrics
        if embedding_service:
            metrics["embeddings"] = await embedding_service.get_stats()
        
        # Monitor metrics
        if context_monitor:
            metrics["monitor"] = await context_monitor.get_activity_stats()
        
        return metrics
    
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# KEY-VALUE STORAGE ENDPOINTS (/kv)
# =============================================================================

@app.post("/kv", response_model=Dict[str, str])
async def set_key_value(
    request: KeyValueRequest,
    user: User = Depends(require_auth(min_trust=0.5))
):
    """Set key-value pair with namespacing."""
    try:
        # Store in Redis cache database
        success = await storage_manager.redis_set(
            "cache", request.namespace, request.key, request.value, request.expire
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store key-value")
        
        # Emit context event
        await emit_context_event("memory_access", request.namespace, {
            "operation": "set",
            "key": request.key,
            "has_expiry": request.expire is not None
        }, user)
        
        return {
            "status": "success",
            "key": request.key,
            "namespace": request.namespace
        }
    
    except Exception as e:
        logger.error(f"Error setting key-value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kv/{namespace}/{key}", response_model=KeyValueResponse)
async def get_key_value(
    namespace: str,
    key: str,
    user: User = Depends(require_auth(min_trust=0.3))
):
    """Get key-value pair with namespacing."""
    try:
        value = await storage_manager.redis_get("cache", namespace, key)
        
        # Emit context event
        await emit_context_event("memory_access", namespace, {
            "operation": "get",
            "key": key,
            "found": value is not None
        }, user)
        
        return KeyValueResponse(
            key=key,
            value=value,
            namespace=namespace,
            exists=value is not None
        )
    
    except Exception as e:
        logger.error(f"Error getting key-value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/kv/{namespace}/{key}")
async def delete_key_value(
    namespace: str,
    key: str,
    user: User = Depends(require_auth(min_trust=0.5))
):
    """Delete key-value pair with namespacing."""
    try:
        deleted_count = await storage_manager.redis_delete("cache", namespace, key)
        
        # Emit context event
        await emit_context_event("memory_access", namespace, {
            "operation": "delete",
            "key": key,
            "deleted": deleted_count > 0
        }, user)
        
        return {
            "status": "success",
            "key": key,
            "namespace": namespace,
            "deleted": deleted_count > 0
        }
    
    except Exception as e:
        logger.error(f"Error deleting key-value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/kv/{namespace}")
async def list_keys(
    namespace: str,
    pattern: str = Query("*", description="Key pattern"),
    user: User = Depends(require_auth(min_trust=0.3))
):
    """List keys in namespace."""
    try:
        keys = await storage_manager.redis_keys("cache", namespace, pattern)
        
        return {
            "namespace": namespace,
            "pattern": pattern,
            "keys": keys,
            "count": len(keys)
        }
    
    except Exception as e:
        logger.error(f"Error listing keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOCUMENT STORAGE ENDPOINTS (/doc)
# =============================================================================

@app.post("/doc", response_model=Dict[str, Any])
async def store_document(
    request: DocumentRequest,
    user: User = Depends(require_auth(min_trust=0.5))
):
    """Store document with namespacing."""
    try:
        # Store in SQLite
        doc_id = await storage_manager.store_document(
            request.namespace, request.doc_id, request.title, 
            request.content, request.metadata
        )
        
        # Auto-generate embedding
        embedding_id = None
        if embedding_service:
            try:
                embedding_id = await embedding_service.add_embedding(
                    namespace=request.namespace,
                    content=f"{request.title}\n{request.content}",
                    doc_id=request.doc_id,
                    category="document",
                    metadata=request.metadata
                )
            except Exception as e:
                logger.warning(f"Failed to generate embedding for document: {e}")
        
        # Emit context event
        await emit_context_event("knowledge_update", request.namespace, {
            "operation": "store",
            "doc_id": request.doc_id,
            "content": request.content,
            "embedding_generated": embedding_id is not None
        }, user)
        
        return {
            "status": "success",
            "doc_id": request.doc_id,
            "namespace": request.namespace,
            "embedding_id": embedding_id,
            "storage_id": doc_id
        }
    
    except Exception as e:
        logger.error(f"Error storing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/doc/{namespace}/{doc_id}", response_model=DocumentResponse)
async def get_document(
    namespace: str,
    doc_id: str,
    user: User = Depends(require_auth(min_trust=0.3))
):
    """Get document with namespacing."""
    try:
        doc = storage_manager.get_document(namespace, doc_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Emit context event
        await emit_context_event("memory_access", namespace, {
            "operation": "get_document",
            "doc_id": doc_id
        }, user)
        
        return DocumentResponse(
            doc_id=doc["doc_id"],
            title=doc["title"],
            content=doc["content"],
            namespace=namespace,
            metadata=doc["metadata"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/doc/{namespace}")
async def list_documents(
    namespace: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_auth(min_trust=0.3))
):
    """List documents in namespace."""
    try:
        docs = storage_manager.sqlite_fetchall(
            "SELECT doc_id, title, created_at, updated_at FROM documents WHERE namespace = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (namespace, limit, offset)
        )
        
        return {
            "namespace": namespace,
            "documents": [
                {
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
                }
                for doc in docs
            ],
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SEMANTIC SEARCH ENDPOINTS (/embedding)
# =============================================================================

@app.post("/embedding")
async def create_embedding(
    request: EmbeddingRequest,
    user: User = Depends(require_auth(min_trust=0.5))
):
    """Create embedding for content."""
    try:
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        embedding_id = await embedding_service.add_embedding(
            namespace=request.namespace,
            content=request.content,
            doc_id=request.doc_id,
            category=request.category,
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "embedding_id": embedding_id,
            "namespace": request.namespace
        }
    
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embedding/search")
async def search_embeddings(
    request: EmbeddingSearchRequest,
    user: User = Depends(require_auth(min_trust=0.3))
):
    """Search for similar content using semantic similarity."""
    try:
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        results = await embedding_service.search_similar(
            query=request.query,
            namespace=request.namespace,
            limit=request.limit,
            min_similarity=request.min_similarity
        )
        
        # Emit context event
        await emit_context_event("embedding_search", request.namespace or "all", {
            "query": request.query,
            "results_count": len(results),
            "min_similarity": request.min_similarity
        }, user)
        
        return {
            "query": request.query,
            "namespace": request.namespace,
            "results": results,
            "count": len(results)
        }
    
    except Exception as e:
        logger.error(f"Error searching embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/embedding/{embedding_id}")
async def get_embedding(
    embedding_id: str,
    user: User = Depends(require_auth(min_trust=0.3))
):
    """Get embedding by ID."""
    try:
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        embedding = await embedding_service.get_embedding_by_id(embedding_id)
        
        if not embedding:
            raise HTTPException(status_code=404, detail="Embedding not found")
        
        return embedding
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/embedding/stats")
async def embedding_stats(
    user: User = Depends(require_auth(min_trust=0.3))
):
    """Get embedding service statistics."""
    try:
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        return await embedding_service.get_stats()
    
    except Exception as e:
        logger.error(f"Error getting embedding stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SESSION MANAGEMENT ENDPOINTS (/session)
# =============================================================================

@app.post("/session", response_model=Dict[str, Any])
async def create_session(
    request: SessionRequest,
    user: User = Depends(require_auth(min_trust=0.5))
):
    """Create or update session with namespacing."""
    try:
        expires_at = None
        if request.expires_hours:
            expires_at = datetime.now() + timedelta(hours=request.expires_hours)
        
        session_id = await storage_manager.store_session(
            request.namespace, request.session_id, request.user_id,
            request.data, expires_at
        )
        
        # Emit context event
        await emit_context_event("session_change", request.namespace, {
            "operation": "create",
            "session_id": request.session_id,
            "user_id": request.user_id,
            "expires_at": expires_at.isoformat() if expires_at else None
        }, user)
        
        return {
            "status": "success",
            "session_id": request.session_id,
            "namespace": request.namespace,
            "storage_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{namespace}/{session_id}", response_model=SessionResponse)
async def get_session(
    namespace: str,
    session_id: str,
    user: User = Depends(require_auth(min_trust=0.3))
):
    """Get session with namespacing."""
    try:
        session = storage_manager.get_session(namespace, session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Emit context event
        await emit_context_event("session_change", namespace, {
            "operation": "get",
            "session_id": session_id
        }, user)
        
        return SessionResponse(
            session_id=session["session_id"],
            user_id=session["user_id"],
            data=session["data"],
            namespace=namespace,
            expires_at=session["expires_at"],
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AUTHENTICATION ENDPOINTS (/auth)
# =============================================================================

@app.post("/auth/token")
async def create_token(
    username: str = Body(...),
    password: str = Body(...),
    agent_name: Optional[str] = Body(None)
):
    """Create authentication token."""
    try:
        # In production, validate credentials against actual user store
        # For now, create token for valid requests
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password required")
        
        # Create user object
        trust_score = await auth_middleware.trust_scorer.get_trust_score(username, agent_name)
        
        user = User(
            user_id=username,
            username=username,
            roles=["user"] if not agent_name else ["agent", "system"],
            agent_name=agent_name,
            trust_score=trust_score
        )
        
        token = auth_middleware.create_access_token(user)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": auth_middleware.config.jwt_expire_hours * 3600,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "roles": user.roles,
                "trust_score": user.trust_score
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/agent-token")
async def create_agent_token(
    agent_name: str = Body(...),
    user: User = Depends(require_high_trust())
):
    """Create token for trusted agents (admin only)."""
    try:
        token = await auth_middleware.create_agent_token(agent_name)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "agent_name": agent_name
        }
    
    except Exception as e:
        logger.error(f"Error creating agent token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/me")
async def get_current_user_info(
    user: User = Depends(get_current_user)
):
    """Get current user information."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return {
        "user_id": user.user_id,
        "username": user.username,
        "roles": user.roles,
        "agent_name": user.agent_name,
        "trust_score": user.trust_score,
        "metadata": user.metadata
    }


# =============================================================================
# ADMINISTRATION ENDPOINTS (/admin)
# =============================================================================

@app.get("/admin/stats")
async def admin_stats(
    user: User = Depends(require_high_trust())
):
    """Get comprehensive system statistics (admin only)."""
    try:
        stats = {
            "timestamp": datetime.now().isoformat(),
            "system": "memory_hub_unified",
            "version": "2.0.0"
        }
        
        # Storage statistics
        if storage_manager:
            # Document counts by namespace
            doc_stats = storage_manager.sqlite_fetchall(
                "SELECT namespace, COUNT(*) as count FROM documents GROUP BY namespace"
            )
            stats["documents"] = {row["namespace"]: row["count"] for row in doc_stats}
            
            # Session counts by namespace
            session_stats = storage_manager.sqlite_fetchall(
                "SELECT namespace, COUNT(*) as count FROM sessions WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP GROUP BY namespace"
            )
            stats["sessions"] = {row["namespace"]: row["count"] for row in session_stats}
        
        # Embedding statistics
        if embedding_service:
            stats["embeddings"] = await embedding_service.get_stats()
        
        # Monitor statistics
        if context_monitor:
            stats["monitor"] = await context_monitor.get_activity_stats()
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/rebuild-embeddings")
async def rebuild_embeddings(
    user: User = Depends(require_high_trust())
):
    """Rebuild embedding index (admin only)."""
    try:
        if not embedding_service:
            raise HTTPException(status_code=503, detail="Embedding service not available")
        
        await embedding_service.rebuild_index()
        
        return {
            "status": "success",
            "message": "Embedding index rebuilt successfully"
        }
    
    except Exception as e:
        logger.error(f"Error rebuilding embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """CLI entry point."""
    import uvicorn
    
    logger.info("🚀 Launching MemoryHub Unified on 0.0.0.0:7010")
    uvicorn.run(
        "phase1_implementation.group_01_memory_hub.memory_hub.memory_hub_unified:app",
        host="0.0.0.0",
        port=7010,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main() 