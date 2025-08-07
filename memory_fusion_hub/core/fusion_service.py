"""
Main FusionService business logic for Memory Fusion Hub.

This module provides:
- FusionService: Central business logic coordinating all components
- Integration with repository, cache, event log, and telemetry
- Circuit breaker and bulkhead resilience patterns
- Async/await interface with proper error handling
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel

from .models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent, FusionConfig, EventType
from .repository import AbstractRepository, build_repo
from .event_log import EventLog
from .telemetry import Telemetry
from ..adapters.redis_cache import RedisCache
from ..resiliency.circuit_breaker import CircuitBreakerException
from ..resiliency.bulkhead import BulkheadException

logger = logging.getLogger(__name__)


class FusionServiceException(Exception):
    """Base exception for FusionService operations."""
    pass


def bulkhead_guard(func):
    """
    Decorator to apply bulkhead pattern for resource isolation.
    
    This is a simplified implementation - in production, this would
    integrate with the actual bulkhead implementation.
    """
    async def wrapper(*args, **kwargs):
        # TODO: Implement actual bulkhead logic
        return await func(*args, **kwargs)
    return wrapper


class FusionService:
    """
    Main business logic service for Memory Fusion Hub.
    
    Coordinates between cache, repository, event log, and telemetry
    to provide a unified memory management interface with resilience
    patterns and observability.
    """
    
    def __init__(self, cfg: FusionConfig):
        """
        Initialize FusionService with configuration.
        
        Args:
            cfg: Complete configuration for the service
        """
        self.config = cfg
        
        # Initialize core components
        self.cache = RedisCache(
            cfg.storage.redis_url, 
            cfg.storage.cache_ttl_seconds
        )
        
        self.repo = build_repo(cfg.storage)
        
        self.event_log = EventLog(cfg.replication)
        
        self.metrics = Telemetry()
        
        # Async lock for write operations to ensure event ordering
        self.lock = asyncio.Lock()
        
        # Component health status
        self._cache_healthy = True
        self._repo_healthy = True
        self._event_log_healthy = True
        
        logger.info("FusionService initialized")
    
    async def initialize(self) -> None:
        """Initialize all service components."""
        try:
            logger.info("Initializing FusionService components...")
            
            # Initialize repository
            await self.repo.initialize()
            self.metrics.update_health_status('repository', True)
            logger.info("Repository initialized")
            
            # Initialize event log
            await self.event_log.initialize()
            self.metrics.update_health_status('event_log', True)
            logger.info("Event log initialized")
            
            # Cache initialization is lazy, but test connectivity
            try:
                async with self.cache:
                    is_healthy = await self.cache.health_check()
                    self._cache_healthy = is_healthy
                    self.metrics.update_health_status('cache', is_healthy)
                    if is_healthy:
                        logger.info("Cache connection verified")
                    else:
                        logger.warning("Cache health check failed")
            except Exception as e:
                logger.warning(f"Cache initialization warning: {e}")
                self._cache_healthy = False
                self.metrics.update_health_status('cache', False)
            
            logger.info("FusionService initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize FusionService: {e}")
            raise FusionServiceException(f"Service initialization failed: {e}")
    
    async def get(self, key: str, agent_id: Optional[str] = None) -> Optional[BaseModel]:
        """
        Retrieve a memory item by key with cache-aside pattern.
        
        Args:
            key: Unique identifier for the memory item
            agent_id: ID of the requesting agent (for audit)
            
        Returns:
            Memory item if found, None otherwise
        """
        async with self.metrics.time_operation('get'):
            try:
                # Try cache first (if healthy)
                if self._cache_healthy:
                    try:
                        cached_item = await self.cache.get(key)
                        if cached_item:
                            self.metrics.record_cache_hit()
                            
                            # Record read event
                            await self._publish_event(
                                EventType.READ, key, agent_id=agent_id
                            )
                            
                            logger.debug(f"Cache hit for key: {key}")
                            return cached_item
                    except Exception as e:
                        logger.warning(f"Cache get failed for {key}: {e}")
                        self._cache_healthy = False
                        self.metrics.update_health_status('cache', False)
                        self.metrics.record_error('CacheException', 'get')
                
                # Cache miss or cache unhealthy - go to repository
                self.metrics.record_cache_miss()
                
                item = await self.repo.get(key)
                if item:
                    # Store in cache for future requests (if cache is healthy)
                    if self._cache_healthy:
                        try:
                            await self.cache.put(key, item)
                            self.metrics.record_cache_put()
                        except Exception as e:
                            logger.warning(f"Failed to cache item {key}: {e}")
                            self._cache_healthy = False
                            self.metrics.update_health_status('cache', False)
                    
                    # Record read event
                    await self._publish_event(
                        EventType.READ, key, agent_id=agent_id
                    )
                    
                    logger.debug(f"Repository hit for key: {key}")
                else:
                    logger.debug(f"Key not found: {key}")
                
                return item
                
            except Exception as e:
                logger.error(f"Failed to get key {key}: {e}")
                self.metrics.record_error(str(type(e).__name__), 'get')
                raise FusionServiceException(f"Get operation failed: {e}")
    
    @bulkhead_guard
    async def put(self, key: str, item: BaseModel, agent_id: Optional[str] = None) -> None:
        """
        Store a memory item with write-through pattern and event sourcing.
        
        Args:
            key: Unique identifier for the memory item
            item: Memory item to store
            agent_id: ID of the agent performing the operation
        """
        async with self.metrics.time_operation('put'):
            # Use lock to ensure event ordering
            async with self.lock:
                try:
                    # Get previous value for event log
                    previous_item = None
                    try:
                        previous_item = await self.repo.get(key)
                    except Exception as e:
                        logger.debug(f"Could not retrieve previous value for {key}: {e}")
                    
                    # Store in repository first (consistency)
                    await self.repo.put(key, item)
                    
                    # Update cache (if healthy)
                    if self._cache_healthy:
                        try:
                            await self.cache.put(key, item)
                            self.metrics.record_cache_put()
                        except Exception as e:
                            logger.warning(f"Failed to update cache for {key}: {e}")
                            self._cache_healthy = False
                            self.metrics.update_health_status('cache', False)
                    
                    # Determine event type
                    event_type = EventType.UPDATE if previous_item else EventType.CREATE
                    
                    # Publish event for replication
                    await self._publish_event(
                        event_type, 
                        key, 
                        payload=item.dict(),
                        agent_id=agent_id,
                        previous_value=previous_item.dict() if previous_item else None
                    )
                    
                    logger.debug(f"Stored item: {key} (type: {event_type.value})")
                    
                except Exception as e:
                    logger.error(f"Failed to put key {key}: {e}")
                    self.metrics.record_error(str(type(e).__name__), 'put')
                    raise FusionServiceException(f"Put operation failed: {e}")
    
    async def delete(self, key: str, agent_id: Optional[str] = None) -> bool:
        """
        Delete a memory item by key.
        
        Args:
            key: Unique identifier for the memory item to delete
            agent_id: ID of the agent performing the operation
            
        Returns:
            True if item was deleted, False if item didn't exist
        """
        async with self.metrics.time_operation('delete'):
            async with self.lock:
                try:
                    # Get item before deletion for event log
                    previous_item = None
                    try:
                        previous_item = await self.repo.get(key)
                    except Exception as e:
                        logger.debug(f"Could not retrieve item before deletion {key}: {e}")
                    
                    if not previous_item:
                        logger.debug(f"Delete attempted on non-existent key: {key}")
                        return False
                    
                    # Delete from repository
                    await self.repo.delete(key)
                    
                    # Remove from cache (if healthy)
                    if self._cache_healthy:
                        try:
                            await self.cache.evict(key)
                            self.metrics.record_cache_evict()
                        except Exception as e:
                            logger.warning(f"Failed to evict from cache {key}: {e}")
                            self._cache_healthy = False
                            self.metrics.update_health_status('cache', False)
                    
                    # Publish delete event
                    await self._publish_event(
                        EventType.DELETE,
                        key,
                        agent_id=agent_id,
                        previous_value=previous_item.dict() if previous_item else None
                    )
                    
                    logger.debug(f"Deleted item: {key}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to delete key {key}: {e}")
                    self.metrics.record_error(str(type(e).__name__), 'delete')
                    raise FusionServiceException(f"Delete operation failed: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if a memory item exists.
        
        Args:
            key: Unique identifier to check
            
        Returns:
            True if item exists, False otherwise
        """
        async with self.metrics.time_operation('exists'):
            try:
                # Check cache first (if healthy)
                if self._cache_healthy:
                    try:
                        if await self.cache.exists(key):
                            self.metrics.record_cache_hit()
                            return True
                    except Exception as e:
                        logger.warning(f"Cache exists check failed for {key}: {e}")
                        self._cache_healthy = False
                        self.metrics.update_health_status('cache', False)
                
                # Check repository
                exists = await self.repo.exists(key)
                if not exists:
                    self.metrics.record_cache_miss()
                
                return exists
                
            except Exception as e:
                logger.error(f"Failed to check existence of key {key}: {e}")
                self.metrics.record_error(str(type(e).__name__), 'exists')
                raise FusionServiceException(f"Exists check failed: {e}")
    
    async def list_keys(self, prefix: str = "", limit: int = 100) -> List[str]:
        """
        List memory item keys matching the given prefix.
        
        Args:
            prefix: Key prefix to filter by
            limit: Maximum number of keys to return
            
        Returns:
            List of matching keys
        """
        async with self.metrics.time_operation('list_keys'):
            try:
                return await self.repo.list_keys(prefix, limit)
            except Exception as e:
                logger.error(f"Failed to list keys with prefix {prefix}: {e}")
                self.metrics.record_error(str(type(e).__name__), 'list_keys')
                raise FusionServiceException(f"List keys operation failed: {e}")
    
    async def batch_get(self, keys: List[str], agent_id: Optional[str] = None) -> Dict[str, Optional[BaseModel]]:
        """
        Retrieve multiple memory items in a single operation.
        
        Args:
            keys: List of keys to retrieve
            agent_id: ID of the requesting agent
            
        Returns:
            Dictionary mapping keys to their values (None if not found)
        """
        async with self.metrics.time_operation('batch_get'):
            try:
                results = {}
                
                # Process keys in parallel for better performance
                async def get_single_key(key: str):
                    try:
                        return key, await self.get(key, agent_id)
                    except Exception as e:
                        logger.warning(f"Failed to get key {key} in batch: {e}")
                        return key, None
                
                # Execute batch retrieval
                tasks = [get_single_key(key) for key in keys]
                key_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in key_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Batch get task failed: {result}")
                        continue
                    key, value = result
                    results[key] = value
                
                return results
                
            except Exception as e:
                logger.error(f"Batch get operation failed: {e}")
                self.metrics.record_error(str(type(e).__name__), 'batch_get')
                raise FusionServiceException(f"Batch get operation failed: {e}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all components.
        
        Returns:
            Dictionary with health status and metrics
        """
        try:
            # Test component health
            cache_healthy = await self._check_cache_health()
            repo_healthy = await self._check_repo_health()
            event_log_healthy = await self._check_event_log_health()
            
            # Get metrics summary
            metrics_summary = self.metrics.get_metrics_summary()
            
            # Get cache info if available
            cache_info = {}
            if cache_healthy:
                try:
                    cache_info = await self.cache.get_cache_info()
                except Exception as e:
                    logger.warning(f"Failed to get cache info: {e}")
            
            return {
                'service': 'Memory Fusion Hub',
                'status': 'healthy' if all([cache_healthy, repo_healthy, event_log_healthy]) else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'components': {
                    'cache': {
                        'healthy': cache_healthy,
                        'info': cache_info
                    },
                    'repository': {
                        'healthy': repo_healthy
                    },
                    'event_log': {
                        'healthy': event_log_healthy
                    }
                },
                'metrics': metrics_summary
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'service': 'Memory Fusion Hub',
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _publish_event(self, event_type: EventType, target_key: str, 
                           payload: Optional[Dict[str, Any]] = None,
                           agent_id: Optional[str] = None,
                           previous_value: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish an event to the event log.
        
        Args:
            event_type: Type of event
            target_key: Key that was affected
            payload: Event payload data
            agent_id: ID of the agent that performed the operation
            previous_value: Previous value before the change
        """
        try:
            await self.event_log.publish(
                event_type.value,
                target_key,
                payload=payload,
                agent_id=agent_id,
                previous_value=previous_value
            )
            self.metrics.record_event_published(event_type.value)
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")
            self._event_log_healthy = False
            self.metrics.update_health_status('event_log', False)
            self.metrics.record_error('EventLogException', 'publish_event')
    
    async def _check_cache_health(self) -> bool:
        """Check cache health status."""
        try:
            if not self._cache_healthy:
                return False
            
            async with self.cache:
                healthy = await self.cache.health_check()
                self._cache_healthy = healthy
                self.metrics.update_health_status('cache', healthy)
                return healthy
        except Exception:
            self._cache_healthy = False
            self.metrics.update_health_status('cache', False)
            return False
    
    async def _check_repo_health(self) -> bool:
        """Check repository health status."""
        try:
            # Simple health check - try to check if a test key exists
            await self.repo.exists('__health_check__')
            self._repo_healthy = True
            self.metrics.update_health_status('repository', True)
            return True
        except Exception:
            self._repo_healthy = False
            self.metrics.update_health_status('repository', False)
            return False
    
    async def _check_event_log_health(self) -> bool:
        """Check event log health status."""
        try:
            # Check if we can get stream info
            await self.event_log.get_stream_info()
            self._event_log_healthy = True
            self.metrics.update_health_status('event_log', True)
            return True
        except Exception:
            self._event_log_healthy = False
            self.metrics.update_health_status('event_log', False)
            return False
    
    async def close(self) -> None:
        """Close the service and clean up all resources."""
        try:
            logger.info("Shutting down FusionService...")
            
            # Close components in reverse order of initialization
            if hasattr(self, 'cache'):
                await self.cache.close()
                
            if hasattr(self, 'event_log'):
                await self.event_log.close()
                
            if hasattr(self, 'repo'):
                await self.repo.close()
            
            logger.info("FusionService shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during FusionService shutdown: {e}")


# Factory function for service creation
def create_fusion_service(config: FusionConfig) -> FusionService:
    """
    Factory function to create a FusionService instance.
    
    Args:
        config: Service configuration
        
    Returns:
        Configured FusionService instance
    """
    return FusionService(config)