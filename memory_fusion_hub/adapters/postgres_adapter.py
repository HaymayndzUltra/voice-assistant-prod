"""
PostgreSQL adapter for Memory Fusion Hub repository.

This module provides a concrete implementation of the AbstractRepository interface
using PostgreSQL as the storage backend with asyncpg for async operations.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False

from pydantic import BaseModel

from ..core.repository import MemoryRepository, RepositoryError, ConnectionError, NotFoundError
from ..core.models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent


logger = logging.getLogger(__name__)


class PostgresRepository(MemoryRepository):
    """
    PostgreSQL implementation of the repository interface.
    
    Uses asyncpg for async database operations and stores Pydantic models
    as JSONB in PostgreSQL with proper indexing for efficient queries.
    
    Note: Requires asyncpg package to be installed.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL repository.
        
        Args:
            config: Configuration dictionary containing connection parameters
        """
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg is required for PostgreSQL support. Install it with: pip install asyncpg")
            
        self.config = config
        self.connection_pool: Optional[asyncpg.Pool] = None
        self._initialized = False
        
        # Connection parameters
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5432)
        self.database = config.get("database", "memory_fusion_hub")
        self.user = config.get("user", "postgres")
        self.password = config.get("password", "")
        self.ssl = config.get("ssl", "prefer")
        
        # Pool configuration
        self.min_size = config.get("min_pool_size", 5)
        self.max_size = config.get("max_pool_size", 20)
        self.command_timeout = config.get("command_timeout", 60)

    async def _ensure_connection(self) -> asyncpg.Pool:
        """Ensure connection pool is established and initialized."""
        if self.connection_pool is None:
            try:
                self.connection_pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    ssl=self.ssl,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=self.command_timeout
                )
                
                await self._initialize_schema()
                self._initialized = True
                
                logger.info(f"PostgreSQL repository initialized: {self.host}:{self.port}/{self.database}")
                
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL database: {e}")
                raise ConnectionError(f"Database connection failed: {e}")
                
        return self.connection_pool

    async def _initialize_schema(self) -> None:
        """Initialize database schema for storing memory data."""
        if self.connection_pool is None:
            raise ConnectionError("Database connection pool not established")

        async with self.connection_pool.acquire() as conn:
            # Enable required extensions
            await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
            
            # Main storage table for all items
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    key TEXT PRIMARY KEY,
                    model_type TEXT NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    
                    -- Extracted fields for indexing and querying
                    memory_type TEXT,
                    tags TEXT[],
                    session_id UUID,
                    user_id TEXT,
                    relevance_score REAL,
                    access_count INTEGER DEFAULT 0
                )
            """)

            # Indexes for efficient querying
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_type 
                ON memory_items(model_type)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_memory_type 
                ON memory_items(memory_type)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_session 
                ON memory_items(session_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_user 
                ON memory_items(user_id)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_relevance 
                ON memory_items(relevance_score DESC)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_tags 
                ON memory_items USING GIN(tags)
            """)
            
            # JSONB indexes for flexible querying
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_items_data 
                ON memory_items USING GIN(data)
            """)

            # Knowledge-specific table for RDF-like queries
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_triples (
                    id UUID PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object JSONB NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    domain TEXT,
                    verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    valid_from TIMESTAMP WITH TIME ZONE,
                    valid_until TIMESTAMP WITH TIME ZONE
                )
            """)

            # Indexes for knowledge queries
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_subject 
                ON knowledge_triples(subject)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_predicate 
                ON knowledge_triples(predicate)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_domain 
                ON knowledge_triples(domain)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_object 
                ON knowledge_triples USING GIN(object)
            """)

            # Function to update the updated_at timestamp
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)

            # Trigger to automatically update updated_at
            await conn.execute("""
                DROP TRIGGER IF EXISTS update_memory_items_updated_at ON memory_items
            """)
            
            await conn.execute("""
                CREATE TRIGGER update_memory_items_updated_at 
                BEFORE UPDATE ON memory_items 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
            """)

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
                "tags": value.tags if value.tags else None,
                "relevance_score": value.relevance_score,
            })
        elif isinstance(value, SessionData):
            metadata.update({
                "session_id": value.session_id,
                "user_id": value.user_id,
            })
        elif isinstance(value, MemoryEvent):
            metadata.update({
                "session_id": value.session_id,
                "user_id": value.user_id,
            })

        return metadata

    async def get(self, key: str) -> Optional[BaseModel]:
        """Retrieve an item by key."""
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT model_type, data FROM memory_items WHERE key = $1", 
                    key
                )
                
                if row is None:
                    return None
                
                model_type, data = row
                
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
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    model_type = value.__class__.__name__
                    data = json.loads(value.json())
                    metadata = self._extract_metadata(value)
                    
                    await conn.execute("""
                        INSERT INTO memory_items 
                        (key, model_type, data, memory_type, tags, session_id, user_id, relevance_score)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (key) DO UPDATE SET
                            model_type = EXCLUDED.model_type,
                            data = EXCLUDED.data,
                            memory_type = EXCLUDED.memory_type,
                            tags = EXCLUDED.tags,
                            session_id = EXCLUDED.session_id,
                            user_id = EXCLUDED.user_id,
                            relevance_score = EXCLUDED.relevance_score,
                            updated_at = NOW()
                    """, 
                        key,
                        model_type,
                        data,
                        metadata["memory_type"],
                        metadata["tags"],
                        metadata["session_id"],
                        metadata["user_id"],
                        metadata["relevance_score"]
                    )

                    # Special handling for knowledge records
                    if isinstance(value, KnowledgeRecord):
                        await conn.execute("""
                            INSERT INTO knowledge_triples
                            (id, subject, predicate, object, confidence, domain, verified, valid_from, valid_until)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (id) DO UPDATE SET
                                subject = EXCLUDED.subject,
                                predicate = EXCLUDED.predicate,
                                object = EXCLUDED.object,
                                confidence = EXCLUDED.confidence,
                                domain = EXCLUDED.domain,
                                verified = EXCLUDED.verified,
                                valid_from = EXCLUDED.valid_from,
                                valid_until = EXCLUDED.valid_until
                        """,
                            value.id,
                            value.subject,
                            value.predicate,
                            value.object,
                            value.confidence,
                            value.domain,
                            value.verified,
                            value.valid_from,
                            value.valid_until
                        )

                    logger.debug(f"Stored item: {key} (type: {model_type})")
            
        except Exception as e:
            logger.error(f"Error storing item {key}: {e}")
            raise RepositoryError(f"Failed to store item: {e}")

    async def delete(self, key: str) -> None:
        """Delete an item by key."""
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Get the item first to handle knowledge records
                    item = await self.get(key)
                    
                    result = await conn.execute("DELETE FROM memory_items WHERE key = $1", key)
                    
                    if result == "DELETE 0":
                        raise NotFoundError(f"Item with key '{key}' not found")
                    
                    # Clean up knowledge triples if it was a knowledge record
                    if isinstance(item, KnowledgeRecord):
                        await conn.execute("DELETE FROM knowledge_triples WHERE id = $1", item.id)
                    
                    logger.debug(f"Deleted item: {key}")
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting item {key}: {e}")
            raise RepositoryError(f"Failed to delete item: {e}")

    async def exists(self, key: str) -> bool:
        """Check if an item exists."""
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT 1 FROM memory_items WHERE key = $1 LIMIT 1", 
                    key
                )
                return result is not None
                
        except Exception as e:
            logger.error(f"Error checking existence of {key}: {e}")
            raise RepositoryError(f"Failed to check item existence: {e}")

    async def list_keys(self, prefix: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """List keys, optionally filtered by prefix."""
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                query = "SELECT key FROM memory_items"
                params = []
                
                if prefix:
                    query += " WHERE key LIKE $1"
                    params.append(f"{prefix}%")
                
                query += " ORDER BY key"
                
                if limit:
                    query += f" LIMIT ${len(params) + 1}"
                    params.append(limit)
                
                rows = await conn.fetch(query, *params)
                return [row["key"] for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
            raise RepositoryError(f"Failed to list keys: {e}")

    async def search(self, query: Dict[str, Any], model_type: Type[BaseModel]) -> List[BaseModel]:
        """Search for items matching the query criteria."""
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                model_name = model_type.__name__
                
                # Build SQL query based on search criteria
                sql_query = "SELECT data FROM memory_items WHERE model_type = $1"
                params = [model_name]
                param_count = 1
                
                # Add search conditions
                if "memory_type" in query:
                    param_count += 1
                    sql_query += f" AND memory_type = ${param_count}"
                    params.append(query["memory_type"])
                
                if "session_id" in query:
                    param_count += 1
                    sql_query += f" AND session_id = ${param_count}"
                    params.append(query["session_id"])
                
                if "user_id" in query:
                    param_count += 1
                    sql_query += f" AND user_id = ${param_count}"
                    params.append(query["user_id"])
                
                if "tags" in query and query["tags"]:
                    param_count += 1
                    sql_query += f" AND tags @> ${param_count}"
                    params.append(query["tags"])
                
                # Knowledge-specific queries using JOIN
                if model_name == "KnowledgeRecord":
                    knowledge_conditions = []
                    if "subject" in query:
                        param_count += 1
                        knowledge_conditions.append(f"kt.subject = ${param_count}")
                        params.append(query["subject"])
                    if "predicate" in query:
                        param_count += 1
                        knowledge_conditions.append(f"kt.predicate = ${param_count}")
                        params.append(query["predicate"])
                    if "domain" in query:
                        param_count += 1
                        knowledge_conditions.append(f"kt.domain = ${param_count}")
                        params.append(query["domain"])
                    if "verified" in query:
                        param_count += 1
                        knowledge_conditions.append(f"kt.verified = ${param_count}")
                        params.append(query["verified"])
                    
                    if knowledge_conditions:
                        sql_query = """
                            SELECT mi.data FROM memory_items mi
                            JOIN knowledge_triples kt ON (mi.data->>'id')::UUID = kt.id
                            WHERE mi.model_type = $1
                        """
                        sql_query += " AND " + " AND ".join(knowledge_conditions)
                
                # Add ordering and limit
                sql_query += " ORDER BY updated_at DESC"
                
                if "limit" in query:
                    param_count += 1
                    sql_query += f" LIMIT ${param_count}"
                    params.append(query["limit"])
                
                rows = await conn.fetch(sql_query, *params)
                
                results = []
                for row in rows:
                    data = row["data"]
                    results.append(model_type(**data))
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching for {model_type.__name__}: {e}")
            raise RepositoryError(f"Failed to search: {e}")

    async def count(self, model_type: Type[BaseModel]) -> int:
        """Count items of a specific type."""
        pool = await self._ensure_connection()
        
        try:
            async with pool.acquire() as conn:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM memory_items WHERE model_type = $1",
                    model_type.__name__
                )
                return result or 0
                
        except Exception as e:
            logger.error(f"Error counting {model_type.__name__}: {e}")
            raise RepositoryError(f"Failed to count items: {e}")

    async def close(self) -> None:
        """Close database connection pool."""
        if self.connection_pool:
            await self.connection_pool.close()
            self.connection_pool = None
            self._initialized = False
            logger.info("PostgreSQL repository connection pool closed")

    # Additional PostgreSQL-specific methods
    async def vacuum_analyze(self) -> None:
        """Run VACUUM ANALYZE to optimize database performance."""
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            await conn.execute("VACUUM ANALYZE memory_items")
            await conn.execute("VACUUM ANALYZE knowledge_triples")
        logger.info("Database vacuum analyze completed")

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        pool = await self._ensure_connection()
        
        stats = {}
        
        async with pool.acquire() as conn:
            # Get table statistics
            type_counts = await conn.fetch("""
                SELECT model_type, COUNT(*) as count 
                FROM memory_items 
                GROUP BY model_type
            """)
            stats["type_counts"] = {row["model_type"]: row["count"] for row in type_counts}
            
            # Get database size information
            db_size = await conn.fetchval("""
                SELECT pg_database_size(current_database())
            """)
            stats["database_size_bytes"] = db_size
            
            # Get table sizes
            table_sizes = await conn.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_total_relation_size(schemaname||'.'||tablename) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename IN ('memory_items', 'knowledge_triples')
            """)
            stats["table_sizes"] = {
                row["tablename"]: row["size"] for row in table_sizes
            }
            
            # Get connection pool stats
            stats["pool_stats"] = {
                "size": self.connection_pool.get_size(),
                "min_size": self.connection_pool.get_min_size(),
                "max_size": self.connection_pool.get_max_size(),
                "idle_size": self.connection_pool.get_idle_size()
            }
        
        return stats

    async def execute_raw(self, query: str, *params) -> Any:
        """Execute a raw SQL query (for advanced use cases)."""
        pool = await self._ensure_connection()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *params)