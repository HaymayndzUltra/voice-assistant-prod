"""
Repository abstractions and implementations for Memory Fusion Hub.

This module provides:
- AbstractRepository: Interface defining repository operations
- SQLiteRepository: SQLite implementation with async support
- PostgresRepository: PostgreSQL implementation with async support
- Circuit breaker and retry decorators for resilience
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import text, MetaData, Table, Column, String, Text, DateTime, JSON
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent, FusionConfig
from ..resiliency.circuit_breaker import CircuitBreakerException

logger = logging.getLogger(__name__)


def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_delay, min=1, max=10),
        reraise=True
    )


class RepositoryException(Exception):
    """Base exception for repository operations."""
    pass


class AbstractRepository(ABC):
    """
    Abstract repository interface defining the contract for data persistence.
    
    All repository implementations must support async operations and handle
    the core data models: MemoryItem, SessionData, KnowledgeRecord, MemoryEvent.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the repository (create tables, connections, etc.)."""
        pass
    
    @abstractmethod
    async def get(self, key: str) -> Optional[BaseModel]:
        """
        Retrieve a data object by its key.
        
        Args:
            key: Unique identifier for the data object
            
        Returns:
            The data object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def put(self, key: str, value: BaseModel) -> None:
        """
        Store a data object with the given key.
        
        Args:
            key: Unique identifier for the data object
            value: Data object to store
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete a data object by its key.
        
        Args:
            key: Unique identifier for the data object to delete
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a data object exists for the given key.
        
        Args:
            key: Unique identifier to check
            
        Returns:
            True if object exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def list_keys(self, prefix: str = "", limit: int = 100) -> List[str]:
        """
        List keys matching the given prefix.
        
        Args:
            prefix: Key prefix to filter by
            limit: Maximum number of keys to return
            
        Returns:
            List of matching keys
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the repository and clean up resources."""
        pass


class SQLiteRepository(AbstractRepository):
    """
    SQLite implementation of the repository using aiosqlite for async operations.
    
    Stores different model types in separate tables with JSON serialization.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize SQLite repository.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
        
    async def initialize(self) -> None:
        """Initialize SQLite database and create tables."""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            await self.connection.execute("PRAGMA journal_mode=WAL")
            await self.connection.execute("PRAGMA synchronous=NORMAL")
            await self.connection.execute("PRAGMA temp_store=MEMORY")
            await self.connection.execute("PRAGMA mmap_size=134217728")  # 128MB
            
            # Create tables for different model types
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS session_data (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_records (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    key TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_memory_items_updated ON memory_items(updated_at)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_session_data_updated ON session_data(updated_at)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_updated ON knowledge_records(updated_at)")
            await self.connection.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON memory_events(created_at)")
            
            await self.connection.commit()
            logger.info(f"SQLite repository initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite repository: {e}")
            raise RepositoryException(f"SQLite initialization failed: {e}")
    
    def _get_table_name(self, value: BaseModel) -> str:
        """Determine the appropriate table name based on model type."""
        if isinstance(value, MemoryItem):
            return "memory_items"
        elif isinstance(value, SessionData):
            return "session_data"
        elif isinstance(value, KnowledgeRecord):
            return "knowledge_records"
        elif isinstance(value, MemoryEvent):
            return "memory_events"
        else:
            raise RepositoryException(f"Unsupported model type: {type(value)}")
    
    def _get_model_class(self, table_name: str) -> type:
        """Get the Pydantic model class for a table."""
        table_to_model = {
            "memory_items": MemoryItem,
            "session_data": SessionData,
            "knowledge_records": KnowledgeRecord,
            "memory_events": MemoryEvent
        }
        return table_to_model.get(table_name)
    
    @retry_with_backoff(max_attempts=3)
    async def get(self, key: str) -> Optional[BaseModel]:
        """Retrieve a data object by its key from any table."""
        if not self.connection:
            raise RepositoryException("Repository not initialized")
        
        # Search across all tables
        for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
            try:
                cursor = await self.connection.execute(
                    f"SELECT data FROM {table_name} WHERE key = ?", (key,)
                )
                row = await cursor.fetchone()
                await cursor.close()
                
                if row:
                    model_class = self._get_model_class(table_name)
                    if model_class:
                        data = json.loads(row[0])
                        return model_class(**data)
                        
            except Exception as e:
                logger.warning(f"Error searching table {table_name} for key {key}: {e}")
                continue
        
        return None
    
    @retry_with_backoff(max_attempts=3)
    async def put(self, key: str, value: BaseModel) -> None:
        """Store a data object with the given key."""
        if not self.connection:
            raise RepositoryException("Repository not initialized")
        
        try:
            table_name = self._get_table_name(value)
            data_json = value.json()
            
            await self.connection.execute(f"""
                INSERT OR REPLACE INTO {table_name} (key, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, data_json))
            
            await self.connection.commit()
            logger.debug(f"Stored object in {table_name}: {key}")
            
        except Exception as e:
            logger.error(f"Failed to store object {key}: {e}")
            raise RepositoryException(f"Put operation failed: {e}")
    
    @retry_with_backoff(max_attempts=3)
    async def delete(self, key: str) -> None:
        """Delete a data object by its key from all tables."""
        if not self.connection:
            raise RepositoryException("Repository not initialized")
        
        try:
            deleted = False
            for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
                cursor = await self.connection.execute(
                    f"DELETE FROM {table_name} WHERE key = ?", (key,)
                )
                if cursor.rowcount > 0:
                    deleted = True
                await cursor.close()
            
            await self.connection.commit()
            
            if deleted:
                logger.debug(f"Deleted object: {key}")
            else:
                logger.warning(f"Object not found for deletion: {key}")
                
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise RepositoryException(f"Delete operation failed: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if a data object exists for the given key."""
        if not self.connection:
            raise RepositoryException("Repository not initialized")
        
        # Check across all tables
        for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
            try:
                cursor = await self.connection.execute(
                    f"SELECT 1 FROM {table_name} WHERE key = ? LIMIT 1", (key,)
                )
                row = await cursor.fetchone()
                await cursor.close()
                
                if row:
                    return True
                    
            except Exception as e:
                logger.warning(f"Error checking existence in {table_name}: {e}")
                continue
        
        return False
    
    async def list_keys(self, prefix: str = "", limit: int = 100) -> List[str]:
        """List keys matching the given prefix."""
        if not self.connection:
            raise RepositoryException("Repository not initialized")
        
        keys = []
        for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
            try:
                if prefix:
                    cursor = await self.connection.execute(
                        f"SELECT key FROM {table_name} WHERE key LIKE ? ORDER BY key LIMIT ?",
                        (f"{prefix}%", limit - len(keys))
                    )
                else:
                    cursor = await self.connection.execute(
                        f"SELECT key FROM {table_name} ORDER BY key LIMIT ?",
                        (limit - len(keys),)
                    )
                
                rows = await cursor.fetchall()
                keys.extend([row[0] for row in rows])
                await cursor.close()
                
                if len(keys) >= limit:
                    break
                    
            except Exception as e:
                logger.warning(f"Error listing keys from {table_name}: {e}")
                continue
        
        return keys[:limit]
    
    async def close(self) -> None:
        """Close the SQLite connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("SQLite repository connection closed")


class PostgresRepository(AbstractRepository):
    """
    PostgreSQL implementation of the repository using SQLAlchemy async.
    
    Provides better performance and concurrent access for production environments.
    """
    
    def __init__(self, connection_url: str):
        """
        Initialize PostgreSQL repository.
        
        Args:
            connection_url: PostgreSQL connection URL
        """
        self.connection_url = connection_url
        self.engine = None
        self.session_factory = None
        
    async def initialize(self) -> None:
        """Initialize PostgreSQL database and create tables."""
        try:
            self.engine = create_async_engine(
                self.connection_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables using raw SQL for simplicity
            async with self.engine.begin() as conn:
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS memory_items (
                        key VARCHAR(255) PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS session_data (
                        key VARCHAR(255) PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS knowledge_records (
                        key VARCHAR(255) PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS memory_events (
                        key VARCHAR(255) PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create indexes
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_memory_items_updated ON memory_items(updated_at)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_session_data_updated ON session_data(updated_at)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_knowledge_updated ON knowledge_records(updated_at)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_events_created ON memory_events(created_at)"))
            
            logger.info("PostgreSQL repository initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL repository: {e}")
            raise RepositoryException(f"PostgreSQL initialization failed: {e}")
    
    def _get_table_name(self, value: BaseModel) -> str:
        """Determine the appropriate table name based on model type."""
        if isinstance(value, MemoryItem):
            return "memory_items"
        elif isinstance(value, SessionData):
            return "session_data"
        elif isinstance(value, KnowledgeRecord):
            return "knowledge_records"
        elif isinstance(value, MemoryEvent):
            return "memory_events"
        else:
            raise RepositoryException(f"Unsupported model type: {type(value)}")
    
    def _get_model_class(self, table_name: str) -> type:
        """Get the Pydantic model class for a table."""
        table_to_model = {
            "memory_items": MemoryItem,
            "session_data": SessionData,
            "knowledge_records": KnowledgeRecord,
            "memory_events": MemoryEvent
        }
        return table_to_model.get(table_name)
    
    @retry_with_backoff(max_attempts=3)
    async def get(self, key: str) -> Optional[BaseModel]:
        """Retrieve a data object by its key from any table."""
        if not self.session_factory:
            raise RepositoryException("Repository not initialized")
        
        async with self.session_factory() as session:
            # Search across all tables
            for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
                try:
                    result = await session.execute(
                        text(f"SELECT data FROM {table_name} WHERE key = :key"),
                        {"key": key}
                    )
                    row = result.fetchone()
                    
                    if row:
                        model_class = self._get_model_class(table_name)
                        if model_class:
                            return model_class(**row[0])
                            
                except Exception as e:
                    logger.warning(f"Error searching table {table_name} for key {key}: {e}")
                    continue
        
        return None
    
    @retry_with_backoff(max_attempts=3)
    async def put(self, key: str, value: BaseModel) -> None:
        """Store a data object with the given key."""
        if not self.session_factory:
            raise RepositoryException("Repository not initialized")
        
        try:
            table_name = self._get_table_name(value)
            data_dict = value.dict()
            
            async with self.session_factory() as session:
                await session.execute(
                    text(f"""
                        INSERT INTO {table_name} (key, data, updated_at)
                        VALUES (:key, :data, CURRENT_TIMESTAMP)
                        ON CONFLICT (key) DO UPDATE SET
                            data = EXCLUDED.data,
                            updated_at = EXCLUDED.updated_at
                    """),
                    {"key": key, "data": data_dict}
                )
                await session.commit()
            
            logger.debug(f"Stored object in {table_name}: {key}")
            
        except Exception as e:
            logger.error(f"Failed to store object {key}: {e}")
            raise RepositoryException(f"Put operation failed: {e}")
    
    @retry_with_backoff(max_attempts=3)
    async def delete(self, key: str) -> None:
        """Delete a data object by its key from all tables."""
        if not self.session_factory:
            raise RepositoryException("Repository not initialized")
        
        try:
            deleted = False
            async with self.session_factory() as session:
                for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
                    result = await session.execute(
                        text(f"DELETE FROM {table_name} WHERE key = :key"),
                        {"key": key}
                    )
                    if result.rowcount > 0:
                        deleted = True
                
                await session.commit()
            
            if deleted:
                logger.debug(f"Deleted object: {key}")
            else:
                logger.warning(f"Object not found for deletion: {key}")
                
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            raise RepositoryException(f"Delete operation failed: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if a data object exists for the given key."""
        if not self.session_factory:
            raise RepositoryException("Repository not initialized")
        
        async with self.session_factory() as session:
            # Check across all tables
            for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
                try:
                    result = await session.execute(
                        text(f"SELECT 1 FROM {table_name} WHERE key = :key LIMIT 1"),
                        {"key": key}
                    )
                    row = result.fetchone()
                    
                    if row:
                        return True
                        
                except Exception as e:
                    logger.warning(f"Error checking existence in {table_name}: {e}")
                    continue
        
        return False
    
    async def list_keys(self, prefix: str = "", limit: int = 100) -> List[str]:
        """List keys matching the given prefix."""
        if not self.session_factory:
            raise RepositoryException("Repository not initialized")
        
        keys = []
        async with self.session_factory() as session:
            for table_name in ["memory_items", "session_data", "knowledge_records", "memory_events"]:
                try:
                    if prefix:
                        result = await session.execute(
                            text(f"SELECT key FROM {table_name} WHERE key LIKE :prefix ORDER BY key LIMIT :limit"),
                            {"prefix": f"{prefix}%", "limit": limit - len(keys)}
                        )
                    else:
                        result = await session.execute(
                            text(f"SELECT key FROM {table_name} ORDER BY key LIMIT :limit"),
                            {"limit": limit - len(keys)}
                        )
                    
                    rows = result.fetchall()
                    keys.extend([row[0] for row in rows])
                    
                    if len(keys) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error listing keys from {table_name}: {e}")
                    continue
        
        return keys[:limit]
    
    async def close(self) -> None:
        """Close the PostgreSQL engine."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            logger.info("PostgreSQL repository connection closed")


def build_repo(storage_config) -> AbstractRepository:
    """
    Factory function to build the appropriate repository based on configuration.
    
    Args:
        storage_config: Storage configuration object
        
    Returns:
        Configured repository instance
    """
    if storage_config.postgres_url:
        logger.info("Building PostgreSQL repository")
        return PostgresRepository(storage_config.postgres_url)
    else:
        logger.info(f"Building SQLite repository: {storage_config.sqlite_path}")
        return SQLiteRepository(storage_config.sqlite_path)