from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""Unified Storage Manager for Redis + SQLite with namespacing."""

import json
import sqlite3
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger("memory_hub.storage")


class StorageConfig(BaseModel):
    """Storage configuration for MemoryHub."""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    sqlite_path: str = "data/memory_hub.db"
    
    # Multi-database Redis setup
    cache_db: int = 0      # db0=cache (CacheManager)
    sessions_db: int = 1   # db1=sessions (SessionMemoryAgent)
    knowledge_db: int = 2  # db2=knowledge (KnowledgeBase)
    auth_db: int = 3       # db3=auth (AuthenticationAgent)


class UnifiedStorageManager:
    """
    Unified storage layer combining Redis (multi-db) and SQLite.
    Provides namespacing to prevent schema collisions between legacy agents.
    """
    
    def __init__(self, config: StorageConfig):

        super().__init__(*args, **kwargs)        self.config = config
        self._redis_pools: Dict[str, redis.Redis] = {}
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._initialized = False
        
        # Namespace prefixes for legacy agents
        self.namespaces = {
            "memory_client": "mc",
            "session_memory": "sm", 
            "knowledge_base": "kb",
            "memory_orchestrator": "mo",
            "unified_memory_reasoning": "umr",
            "context_manager": "cm",
            "experience_tracker": "et",
            "cache_manager": "cache",
            "auth": "auth",
            "trust": "trust"
        }
    
    async def initialize(self):
        """Initialize all storage connections."""
        if self._initialized:
            return
            
        logger.info("Initializing UnifiedStorageManager...")
        
        # Initialize Redis connections for each database
        redis_configs = {
            "cache": self.config.cache_db,
            "sessions": self.config.sessions_db, 
            "knowledge": self.config.knowledge_db,
            "auth": self.config.auth_db
        }
        
        for db_name, db_num in redis_configs.items():
            pool = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                db=db_num,
                decode_responses=True
            )
            await pool.ping()  # Test connection
            self._redis_pools[db_name] = pool
            logger.info(f"Redis {db_name} (db{db_num}) connected")
        
        # Initialize SQLite
        self._sqlite_conn = sqlite3.connect(self.config.sqlite_path, check_same_thread=False)
        self._sqlite_conn.row_factory = sqlite3.Row
        self._create_tables()
        
        self._initialized = True
        logger.info("UnifiedStorageManager initialized successfully")
    
    def _create_tables(self):
        """Create SQLite tables with namespacing."""
        cursor = self._sqlite_conn.cursor()
        
        # Unified documents table (KnowledgeBase + others)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                metadata TEXT,  -- JSON
                embedding_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(namespace, doc_id)
            )
        """)
        
        # Unified sessions table (SessionMemoryAgent)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL,
                session_id TEXT NOT NULL,
                user_id TEXT,
                data TEXT NOT NULL,  -- JSON
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(namespace, session_id)
            )
        """)
        
        # Unified experiences table (ExperienceTracker)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                namespace TEXT NOT NULL,
                experience_id TEXT NOT NULL,
                category TEXT,
                context TEXT NOT NULL,  -- JSON
                outcome TEXT,
                learning TEXT,
                confidence_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(namespace, experience_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_namespace ON documents(namespace)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_namespace ON sessions(namespace)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiences_namespace ON experiences(namespace)")
        
        self._sqlite_conn.commit()
        logger.info("SQLite tables created/verified")
    
    def _get_namespaced_key(self, namespace: str, key: str) -> str:
        """Generate namespaced key to prevent collisions."""
        prefix = self.namespaces.get(namespace, namespace)
        return f"{prefix}:{key}"
    
    # Redis Operations
    async def redis_get(self, db_name: str, namespace: str, key: str) -> Optional[str]:
        """Get value from Redis with namespacing."""
        namespaced_key = self._get_namespaced_key(namespace, key)
        return await self._redis_pools[db_name].get(namespaced_key)
    
    async def redis_set(self, db_name: str, namespace: str, key: str, value: str, 
                       expire: Optional[int] = None) -> bool:
        """Set value in Redis with namespacing."""
        namespaced_key = self._get_namespaced_key(namespace, key)
        result = await self._redis_pools[db_name].set(namespaced_key, value)
        if expire:
            await self._redis_pools[db_name].expire(namespaced_key, expire)
        return result
    
    async def redis_delete(self, db_name: str, namespace: str, key: str) -> int:
        """Delete key from Redis with namespacing."""
        namespaced_key = self._get_namespaced_key(namespace, key)
        return await self._redis_pools[db_name].delete(namespaced_key)
    
    async def redis_keys(self, db_name: str, namespace: str, pattern: str = "*") -> List[str]:
        """Get keys from Redis with namespacing."""
        prefix = self.namespaces.get(namespace, namespace)
        namespaced_pattern = f"{prefix}:{pattern}"
        keys = await self._redis_pools[db_name].keys(namespaced_pattern)
        # Remove namespace prefix from results
        return [key.replace(f"{prefix}:", "", 1) for key in keys]
    
    async def redis_hget(self, db_name: str, namespace: str, name: str, key: str) -> Optional[str]:
        """Get hash field from Redis with namespacing."""
        namespaced_name = self._get_namespaced_key(namespace, name)
        return await self._redis_pools[db_name].hget(namespaced_name, key)
    
    async def redis_hset(self, db_name: str, namespace: str, name: str, key: str, value: str) -> int:
        """Set hash field in Redis with namespacing."""
        namespaced_name = self._get_namespaced_key(namespace, name)
        return await self._redis_pools[db_name].hset(namespaced_name, key, value)
    
    # SQLite Operations
    def sqlite_execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute SQLite query."""
        cursor = self._sqlite_conn.cursor()
        cursor.execute(query, params)
        self._sqlite_conn.commit()
        return cursor
    
    def sqlite_fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch one result from SQLite."""
        cursor = self._sqlite_conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()
    
    def sqlite_fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all results from SQLite."""
        cursor = self._sqlite_conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    # High-level operations
    async def store_document(self, namespace: str, doc_id: str, title: str, 
                           content: str, metadata: Dict[str, Any] = None) -> int:
        """Store document with namespacing."""
        metadata_json = json.dumps(metadata or {})
        cursor = self.sqlite_execute(
            """INSERT OR REPLACE INTO documents 
               (namespace, doc_id, title, content, metadata, updated_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (namespace, doc_id, title, content, metadata_json)
        )
        return cursor.lastrowid
    
    def get_document(self, namespace: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document with namespacing."""
        row = self.sqlite_fetchone(
            "SELECT * FROM documents WHERE namespace = ? AND doc_id = ?",
            (namespace, doc_id)
        )
        if row:
            return {
                "id": row["id"],
                "doc_id": row["doc_id"],
                "title": row["title"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        return None
    
    async def store_session(self, namespace: str, session_id: str, user_id: str,
                          data: Dict[str, Any], expires_at: Optional[datetime] = None) -> int:
        """Store session with namespacing."""
        data_json = json.dumps(data)
        cursor = self.sqlite_execute(
            """INSERT OR REPLACE INTO sessions 
               (namespace, session_id, user_id, data, expires_at, updated_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (namespace, session_id, user_id, data_json, expires_at)
        )
        return cursor.lastrowid
    
    def get_session(self, namespace: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with namespacing."""
        row = self.sqlite_fetchone(
            "SELECT * FROM sessions WHERE namespace = ? AND session_id = ? AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
            (namespace, session_id)
        )
        if row:
            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "data": json.loads(row["data"]),
                "expires_at": row["expires_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        return None
    
    async def cleanup_expired_sessions(self):
        """Background task to clean up expired sessions."""
        while True:
            try:
                self.sqlite_execute(
                    "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
                )
                logger.debug("Cleaned up expired sessions")
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def close(self):
        """Close all connections."""
        for pool in self._redis_pools.values():
            await pool.close()
        if self._sqlite_conn:
            self._sqlite_conn.close()
        logger.info("UnifiedStorageManager closed") 