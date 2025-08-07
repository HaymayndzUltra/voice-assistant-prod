"""
Repository interfaces and implementations for Memory Fusion Hub.

This module defines the abstract repository pattern and provides concrete
implementations for different storage backends (SQLite, PostgreSQL).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from pydantic import BaseModel

from .models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent


class AbstractRepository(ABC):
    """
    Abstract base class for memory storage repositories.
    
    Defines the interface that all concrete repository implementations must follow.
    This enables the Memory Fusion Hub to work with different storage backends
    transparently.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[BaseModel]:
        """
        Retrieve a memory item by its key.
        
        Args:
            key: The unique key identifying the memory item
            
        Returns:
            The memory item if found, None otherwise
        """
        pass

    @abstractmethod
    async def put(self, key: str, value: BaseModel) -> None:
        """
        Store a memory item with the given key.
        
        Args:
            key: The unique key to identify the memory item
            value: The memory item to store
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete a memory item by its key.
        
        Args:
            key: The unique key identifying the memory item to delete
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a memory item exists with the given key.
        
        Args:
            key: The unique key to check
            
        Returns:
            True if the item exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """
        List all keys in the repository, optionally filtered by prefix.
        
        Args:
            prefix: Optional prefix to filter keys
            limit: Optional limit on number of keys returned
            
        Returns:
            List of keys matching the criteria
        """
        pass

    @abstractmethod
    async def search(self, query: Dict[str, Any], model_type: Type[BaseModel]) -> List[BaseModel]:
        """
        Search for items matching the given query criteria.
        
        Args:
            query: Dictionary containing search criteria
            model_type: The type of model to search for
            
        Returns:
            List of items matching the search criteria
        """
        pass

    @abstractmethod
    async def count(self, model_type: Type[BaseModel]) -> int:
        """
        Count the number of items of a specific model type.
        
        Args:
            model_type: The type of model to count
            
        Returns:
            Number of items of the specified type
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the repository and clean up any resources.
        """
        pass


class MemoryRepository(AbstractRepository):
    """
    Base class for memory-specific repositories with common functionality.
    
    Provides helper methods specifically for working with memory items,
    sessions, knowledge records, and events.
    """

    async def get_memory_item(self, key: str) -> Optional[MemoryItem]:
        """Get a memory item by key."""
        result = await self.get(key)
        return result if isinstance(result, MemoryItem) else None

    async def put_memory_item(self, item: MemoryItem) -> None:
        """Store a memory item."""
        await self.put(item.key, item)

    async def get_session(self, session_id: UUID) -> Optional[SessionData]:
        """Get session data by session ID."""
        result = await self.get(f"session:{session_id}")
        return result if isinstance(result, SessionData) else None

    async def put_session(self, session: SessionData) -> None:
        """Store session data."""
        await self.put(f"session:{session.session_id}", session)

    async def get_knowledge_record(self, record_id: UUID) -> Optional[KnowledgeRecord]:
        """Get a knowledge record by ID."""
        result = await self.get(f"knowledge:{record_id}")
        return result if isinstance(result, KnowledgeRecord) else None

    async def put_knowledge_record(self, record: KnowledgeRecord) -> None:
        """Store a knowledge record."""
        await self.put(f"knowledge:{record.id}", record)

    async def put_event(self, event: MemoryEvent) -> None:
        """Store a memory event."""
        await self.put(f"event:{event.id}", event)

    async def get_recent_events(self, limit: int = 100) -> List[MemoryEvent]:
        """Get recent memory events."""
        events = await self.search({"limit": limit}, MemoryEvent)
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    async def search_memory_items(self, 
                                 memory_type: Optional[str] = None,
                                 tags: Optional[List[str]] = None,
                                 limit: Optional[int] = None) -> List[MemoryItem]:
        """
        Search for memory items by type and tags.
        
        Args:
            memory_type: Filter by memory type
            tags: Filter by tags (items must have all specified tags)
            limit: Maximum number of results
            
        Returns:
            List of matching memory items
        """
        query = {}
        if memory_type:
            query["memory_type"] = memory_type
        if tags:
            query["tags"] = tags
        if limit:
            query["limit"] = limit
            
        return await self.search(query, MemoryItem)

    async def search_knowledge(self, 
                              subject: Optional[str] = None,
                              predicate: Optional[str] = None,
                              domain: Optional[str] = None,
                              verified_only: bool = False) -> List[KnowledgeRecord]:
        """
        Search for knowledge records by various criteria.
        
        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            domain: Filter by domain
            verified_only: Only return verified knowledge
            
        Returns:
            List of matching knowledge records
        """
        query = {}
        if subject:
            query["subject"] = subject
        if predicate:
            query["predicate"] = predicate
        if domain:
            query["domain"] = domain
        if verified_only:
            query["verified"] = True
            
        return await self.search(query, KnowledgeRecord)


class RepositoryError(Exception):
    """Base exception for repository-related errors."""
    pass


class ConnectionError(RepositoryError):
    """Raised when there's a connection issue with the storage backend."""
    pass


class ValidationError(RepositoryError):
    """Raised when data validation fails."""
    pass


class NotFoundError(RepositoryError):
    """Raised when a requested item is not found."""
    pass


class DuplicateKeyError(RepositoryError):
    """Raised when trying to create an item with a key that already exists."""
    pass


# Repository factory function
def create_repository(storage_config: Dict[str, Any]) -> AbstractRepository:
    """
    Factory function to create repository instances based on configuration.
    
    Args:
        storage_config: Configuration dictionary specifying storage type and options
        
    Returns:
        Configured repository instance
        
    Raises:
        ValueError: If storage type is not supported
    """
    storage_type = storage_config.get("type", "sqlite").lower()
    
    if storage_type == "sqlite":
        from ..adapters.sqlite_adapter import SQLiteRepository
        return SQLiteRepository(storage_config)
    elif storage_type == "postgresql":
        from ..adapters.postgres_adapter import PostgresRepository  
        return PostgresRepository(storage_config)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


# Repository utilities
class RepositoryManager:
    """
    Manages multiple repository instances and provides unified access.
    
    This class can be used to coordinate between different storage backends
    or provide failover capabilities.
    """
    
    def __init__(self):
        self._repositories: Dict[str, AbstractRepository] = {}
        self._primary: Optional[str] = None

    def add_repository(self, name: str, repository: AbstractRepository, is_primary: bool = False) -> None:
        """Add a repository instance."""
        self._repositories[name] = repository
        if is_primary or self._primary is None:
            self._primary = name

    def get_repository(self, name: Optional[str] = None) -> AbstractRepository:
        """Get a repository by name, or the primary repository if no name given."""
        if name is None:
            if self._primary is None:
                raise ValueError("No repositories configured")
            name = self._primary
            
        if name not in self._repositories:
            raise ValueError(f"Repository '{name}' not found")
            
        return self._repositories[name]

    async def close_all(self) -> None:
        """Close all repositories."""
        for repo in self._repositories.values():
            await repo.close()
        self._repositories.clear()
        self._primary = None