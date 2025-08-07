"""
SQLite adapter for Memory Fusion Hub repository.

This module provides a concrete implementation of the AbstractRepository interface
using SQLite as the storage backend with aiosqlite for async operations.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

import aiosqlite
from pydantic import BaseModel

from ..core.repository import MemoryRepository, RepositoryError, ConnectionError, NotFoundError
from ..core.models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent


logger = logging.getLogger(__name__)


class SQLiteRepository(MemoryRepository):
    """
    SQLite implementation of the repository interface.
    
    Uses aiosqlite for async database operations and stores Pydantic models
    as JSON in the database with proper indexing for efficient queries.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SQLite repository.
        
        Args:
            config: Configuration dictionary containing database path and options
        """
        self.db_path = config.get("sqlite_path", ":memory:")
        self.connection: Optional[aiosqlite.Connection] = None
        self._initialized = False
        
        # Configuration options
        self.enable_wal = config.get("enable_wal", True)
        self.journal_mode = config.get("journal_mode", "WAL" if self.enable_wal else "DELETE")
        self.synchronous = config.get("synchronous", "NORMAL")
        self.cache_size = config.get("cache_size", 10000)

    async def _ensure_connection(self) -> aiosqlite.Connection:
        """Ensure database connection is established and initialized."""
        if self.connection is None:
            try:
                self.connection = await aiosqlite.connect(self.db_path)
                
                # Configure SQLite for optimal performance
                await self.connection.execute(f"PRAGMA journal_mode = {self.journal_mode}")
                await self.connection.execute(f"PRAGMA synchronous = {self.synchronous}")
                await self.connection.execute(f"PRAGMA cache_size = {self.cache_size}")
                await self.connection.execute("PRAGMA foreign_keys = ON")
                
                await self._initialize_schema()
                self._initialized = True
                
                logger.info(f"SQLite repository initialized: {self.db_path}")
                
            except Exception as e:
                logger.error(f"Failed to connect to SQLite database: {e}")
                raise ConnectionError(f"Database connection failed: {e}")
                
        return self.connection

    async def _initialize_schema(self) -> None:
        """Initialize database schema for storing memory data."""
        if self.connection is None:
            raise ConnectionError("Database connection not established")

        # Main storage table for all items
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS memory_items (
                key TEXT PRIMARY KEY,
                model_type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Extracted fields for indexing and querying
                memory_type TEXT,
                tags TEXT,
                session_id TEXT,
                user_id TEXT,
                relevance_score REAL,
                access_count INTEGER DEFAULT 0
            )
        """)

        # Indexes for efficient querying
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_items_type 
            ON memory_items(model_type)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_items_memory_type 
            ON memory_items(memory_type)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_items_session 
            ON memory_items(session_id)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_items_user 
            ON memory_items(user_id)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_items_relevance 
            ON memory_items(relevance_score DESC)
        """)

        # Knowledge-specific table for RDF-like queries
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_triples (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                domain TEXT,
                verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for knowledge queries
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_subject 
            ON knowledge_triples(subject)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_predicate 
            ON knowledge_triples(predicate)
        """)
        
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_domain 
            ON knowledge_triples(domain)
        """)

        await self.connection.commit()

    def _extract_metadata(self, value: BaseModel) -> Dict[str, Any]:
        """Extract metadata from Pydantic model for indexing."""
        metadata = {
            "memory_type": None,
            "tags": None,
            "session_id": None,
            "user_id": None,
            "relevance_score": None,
        }

        if isinstance(value, MemoryItem):
            metadata.update({
                "memory_type": value.memory_type.value if value.memory_type else None,
                "tags": json.dumps(value.tags) if value.tags else None,
                "relevance_score": value.relevance_score,
            })
        elif isinstance(value, SessionData):
            metadata.update({
                "session_id": str(value.session_id),
                "user_id": value.user_id,
            })
        elif isinstance(value, MemoryEvent):
            metadata.update({
                "session_id": str(value.session_id) if value.session_id else None,
                "user_id": value.user_id,
            })

        return metadata

    async def get(self, key: str) -> Optional[BaseModel]:
        """Retrieve an item by key."""
        conn = await self._ensure_connection()
        
        try:
            async with conn.execute(
                "SELECT model_type, data FROM memory_items WHERE key = ?", 
                (key,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row is None:
                    return None
                
                model_type, data_json = row
                data = json.loads(data_json)
                
                # Determine model class and deserialize
                if model_type == "MemoryItem":
                    return MemoryItem(**data)
                elif model_type == "SessionData":
                    return SessionData(**data)
                elif model_type == "KnowledgeRecord":
                    return KnowledgeRecord(**data)
                elif model_type == "MemoryEvent":
                    return MemoryEvent(**data)
                else:
                    logger.warning(f"Unknown model type: {model_type}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error retrieving item {key}: {e}")
            raise RepositoryError(f"Failed to retrieve item: {e}")

    async def put(self, key: str, value: BaseModel) -> None:
        """Store an item with the given key."""
        conn = await self._ensure_connection()
        
        try:
            model_type = value.__class__.__name__
            data_json = value.json()
            metadata = self._extract_metadata(value)
            
            await conn.execute("""
                INSERT OR REPLACE INTO memory_items 
                (key, model_type, data, memory_type, tags, session_id, user_id, relevance_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                key,
                model_type,
                data_json,
                metadata["memory_type"],
                metadata["tags"],
                metadata["session_id"],
                metadata["user_id"],
                metadata["relevance_score"]
            ))

            # Special handling for knowledge records
            if isinstance(value, KnowledgeRecord):
                await conn.execute("""
                    INSERT OR REPLACE INTO knowledge_triples
                    (id, subject, predicate, object, confidence, domain, verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(value.id),
                    value.subject,
                    value.predicate,
                    json.dumps(value.object) if isinstance(value.object, (dict, list)) else str(value.object),
                    value.confidence,
                    value.domain,
                    value.verified
                ))

            await conn.commit()
            logger.debug(f"Stored item: {key} (type: {model_type})")
            
        except Exception as e:
            await conn.rollback()
            logger.error(f"Error storing item {key}: {e}")
            raise RepositoryError(f"Failed to store item: {e}")

    async def delete(self, key: str) -> None:
        """Delete an item by key."""
        conn = await self._ensure_connection()
        
        try:
            # Get the item first to handle knowledge records
            item = await self.get(key)
            
            cursor = await conn.execute("DELETE FROM memory_items WHERE key = ?", (key,))
            
            if cursor.rowcount == 0:
                raise NotFoundError(f"Item with key '{key}' not found")
            
            # Clean up knowledge triples if it was a knowledge record
            if isinstance(item, KnowledgeRecord):
                await conn.execute("DELETE FROM knowledge_triples WHERE id = ?", (str(item.id),))
            
            await conn.commit()
            logger.debug(f"Deleted item: {key}")
            
        except NotFoundError:
            raise
        except Exception as e:
            await conn.rollback()
            logger.error(f"Error deleting item {key}: {e}")
            raise RepositoryError(f"Failed to delete item: {e}")

    async def exists(self, key: str) -> bool:
        """Check if an item exists."""
        conn = await self._ensure_connection()
        
        try:
            async with conn.execute(
                "SELECT 1 FROM memory_items WHERE key = ? LIMIT 1", 
                (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
                
        except Exception as e:
            logger.error(f"Error checking existence of {key}: {e}")
            raise RepositoryError(f"Failed to check item existence: {e}")

    async def list_keys(self, prefix: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """List keys, optionally filtered by prefix."""
        conn = await self._ensure_connection()
        
        try:
            query = "SELECT key FROM memory_items"
            params = []
            
            if prefix:
                query += " WHERE key LIKE ?"
                params.append(f"{prefix}%")
            
            query += " ORDER BY key"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
            raise RepositoryError(f"Failed to list keys: {e}")

    async def search(self, query: Dict[str, Any], model_type: Type[BaseModel]) -> List[BaseModel]:
        """Search for items matching the query criteria."""
        conn = await self._ensure_connection()
        
        try:
            model_name = model_type.__name__
            
            # Build SQL query based on search criteria
            sql_query = "SELECT data FROM memory_items WHERE model_type = ?"
            params = [model_name]
            
            # Add search conditions
            if "memory_type" in query:
                sql_query += " AND memory_type = ?"
                params.append(query["memory_type"])
            
            if "session_id" in query:
                sql_query += " AND session_id = ?"
                params.append(str(query["session_id"]))
            
            if "user_id" in query:
                sql_query += " AND user_id = ?"
                params.append(query["user_id"])
            
            if "tags" in query and query["tags"]:
                # Simple tag matching - could be improved with full-text search
                for tag in query["tags"]:
                    sql_query += " AND tags LIKE ?"
                    params.append(f'%"{tag}"%')
            
            # Knowledge-specific queries
            if model_name == "KnowledgeRecord":
                knowledge_conditions = []
                if "subject" in query:
                    knowledge_conditions.append("subject = ?")
                    params.append(query["subject"])
                if "predicate" in query:
                    knowledge_conditions.append("predicate = ?")
                    params.append(query["predicate"])
                if "domain" in query:
                    knowledge_conditions.append("domain = ?")
                    params.append(query["domain"])
                if "verified" in query:
                    knowledge_conditions.append("verified = ?")
                    params.append(query["verified"])
                
                if knowledge_conditions:
                    sql_query = """
                        SELECT mi.data FROM memory_items mi
                        JOIN knowledge_triples kt ON json_extract(mi.data, '$.id') = kt.id
                        WHERE mi.model_type = ?
                    """
                    sql_query += " AND " + " AND ".join(knowledge_conditions)
            
            # Add ordering and limit
            sql_query += " ORDER BY updated_at DESC"
            
            if "limit" in query:
                sql_query += " LIMIT ?"
                params.append(query["limit"])
            
            async with conn.execute(sql_query, params) as cursor:
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    data = json.loads(row[0])
                    results.append(model_type(**data))
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching for {model_type.__name__}: {e}")
            raise RepositoryError(f"Failed to search: {e}")

    async def count(self, model_type: Type[BaseModel]) -> int:
        """Count items of a specific type."""
        conn = await self._ensure_connection()
        
        try:
            async with conn.execute(
                "SELECT COUNT(*) FROM memory_items WHERE model_type = ?",
                (model_type.__name__,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
                
        except Exception as e:
            logger.error(f"Error counting {model_type.__name__}: {e}")
            raise RepositoryError(f"Failed to count items: {e}")

    async def close(self) -> None:
        """Close database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self._initialized = False
            logger.info("SQLite repository connection closed")

    # Additional SQLite-specific methods
    async def vacuum(self) -> None:
        """Optimize database by running VACUUM."""
        conn = await self._ensure_connection()
        await conn.execute("VACUUM")
        await conn.commit()
        logger.info("Database vacuum completed")

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        conn = await self._ensure_connection()
        
        stats = {}
        
        # Get table statistics
        async with conn.execute("""
            SELECT model_type, COUNT(*) as count 
            FROM memory_items 
            GROUP BY model_type
        """) as cursor:
            type_counts = await cursor.fetchall()
            stats["type_counts"] = {row[0]: row[1] for row in type_counts}
        
        # Get database size
        async with conn.execute("PRAGMA page_count") as cursor:
            page_count = (await cursor.fetchone())[0]
        async with conn.execute("PRAGMA page_size") as cursor:
            page_size = (await cursor.fetchone())[0]
        
        stats["database_size_bytes"] = page_count * page_size
        stats["page_count"] = page_count
        stats["page_size"] = page_size
        
        return stats