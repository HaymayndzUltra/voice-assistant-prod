from common.core.base_agent import BaseAgent
"""Background monitoring for proactive context changes."""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger("memory_hub.monitor")


@dataclass
class ContextEvent:
    """Context change event."""
    event_id: str
    namespace: str
    event_type: str  # 'memory_access', 'session_change', 'knowledge_update', etc.
    data: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any]


class ProactiveContextMonitor:
    """
    Background monitor that tracks context changes and proactively
    manages memory, sessions, and knowledge updates.
    """
    
    def __init__(self, storage_manager, embedding_service):

        super().__init__(*args, **kwargs)        self.storage = storage_manager
        self.embedding = embedding_service
        self.is_running = False
        self.tasks: List[asyncio.Task] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.event_queue = asyncio.Queue()
        
        # Monitoring intervals (seconds)
        self.intervals = {
            "session_monitor": 300,    # 5 minutes
            "memory_cleanup": 3600,    # 1 hour
            "embedding_rebuild": 86400, # 24 hours
            "context_analysis": 60,    # 1 minute
            "health_check": 120        # 2 minutes
        }
        
        # Context tracking
        self.context_cache = {}
        self.activity_counters = {}
        
        logger.info("ProactiveContextMonitor initialized")
    
    async def start(self):
        """Start background monitoring tasks."""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Starting ProactiveContextMonitor...")
        
        # Start all monitoring coroutines
        self.tasks = [
            asyncio.create_task(self._session_monitor()),
            asyncio.create_task(self._memory_cleanup_monitor()),
            asyncio.create_task(self._embedding_maintenance_monitor()),
            asyncio.create_task(self._context_analysis_monitor()),
            asyncio.create_task(self._health_check_monitor()),
            asyncio.create_task(self._event_processor())
        ]
        
        logger.info(f"Started {len(self.tasks)} monitoring tasks")
    
    async def stop(self):
        """Stop all monitoring tasks."""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping ProactiveContextMonitor...")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("ProactiveContextMonitor stopped")
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register handler for specific event types."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type}")
    
    async def emit_event(self, event: ContextEvent):
        """Emit context event for processing."""
        await self.event_queue.put(event)
    
    async def _event_processor(self):
        """Process context events from queue."""
        logger.info("Event processor started")
        
        while self.is_running:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Process event
                await self._process_event(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                await asyncio.sleep(1)
    
    async def _process_event(self, event: ContextEvent):
        """Process individual context event."""
        try:
            # Update activity counters
            self._update_activity_counters(event)
            
            # Store event for analysis
            await self._store_event(event)
            
            # Call registered handlers
            handlers = self.event_handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
            
            # Built-in event processing
            await self._handle_builtin_event(event)
            
        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")
    
    def _update_activity_counters(self, event: ContextEvent):
        """Update activity counters for analytics."""
        namespace = event.namespace
        event_type = event.event_type
        
        if namespace not in self.activity_counters:
            self.activity_counters[namespace] = {}
        
        if event_type not in self.activity_counters[namespace]:
            self.activity_counters[namespace][event_type] = 0
        
        self.activity_counters[namespace][event_type] += 1
    
    async def _store_event(self, event: ContextEvent):
        """Store event in Redis for analysis."""
        try:
            event_data = {
                "event_id": event.event_id,
                "namespace": event.namespace,
                "event_type": event.event_type,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata
            }
            
            # Store in Redis with TTL
            key = f"event:{event.event_id}"
            await self.storage.redis_set(
                "cache", "context_monitor", key,
                json.dumps(event_data),
                expire=86400 * 7  # 7 days
            )
            
            # Add to namespace index
            namespace_key = f"events:namespace:{event.namespace}"
            await self.storage.redis_hset(
                "cache", "context_monitor", namespace_key,
                event.event_id, event.timestamp.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error storing event: {e}")
    
    async def _handle_builtin_event(self, event: ContextEvent):
        """Handle built-in event types."""
        try:
            if event.event_type == "memory_access":
                await self._handle_memory_access(event)
            elif event.event_type == "session_change":
                await self._handle_session_change(event)
            elif event.event_type == "knowledge_update":
                await self._handle_knowledge_update(event)
            elif event.event_type == "embedding_search":
                await self._handle_embedding_search(event)
        
        except Exception as e:
            logger.error(f"Error handling builtin event {event.event_type}: {e}")
    
    async def _handle_memory_access(self, event: ContextEvent):
        """Handle memory access events."""
        # Track frequently accessed items
        key = event.data.get("key", "")
        if key:
            access_key = f"access_count:{event.namespace}:{key}"
            await self.storage.redis_hset(
                "cache", "context_monitor", access_key,
                "count", str(int(await self.storage.redis_hget("cache", "context_monitor", access_key, "count") or "0") + 1)
            )
    
    async def _handle_session_change(self, event: ContextEvent):
        """Handle session change events."""
        session_id = event.data.get("session_id", "")
        if session_id:
            # Update session activity
            activity_key = f"session_activity:{session_id}"
            await self.storage.redis_set(
                "sessions", "session_memory", activity_key,
                datetime.now().isoformat(),
                expire=86400  # 1 day
            )
    
    async def _handle_knowledge_update(self, event: ContextEvent):
        """Handle knowledge update events."""
        # Auto-generate embeddings for new knowledge
        content = event.data.get("content", "")
        doc_id = event.data.get("doc_id", "")
        
        if content and doc_id:
            try:
                embedding_id = await self.embedding.add_embedding(
                    namespace=event.namespace,
                    content=content,
                    doc_id=doc_id,
                    category="auto_generated",
                    metadata={"auto_indexed": True, "source_event": event.event_id}
                )
                logger.debug(f"Auto-generated embedding {embedding_id} for doc {doc_id}")
            except Exception as e:
                logger.error(f"Error auto-generating embedding: {e}")
    
    async def _handle_embedding_search(self, event: ContextEvent):
        """Handle embedding search events."""
        query = event.data.get("query", "")
        if query:
            # Track popular search queries
            query_key = f"popular_queries:{event.namespace}"
            await self.storage.redis_hset(
                "cache", "context_monitor", query_key,
                query, str(int(await self.storage.redis_hget("cache", "context_monitor", query_key, query) or "0") + 1)
            )
    
    async def _session_monitor(self):
        """Monitor and cleanup expired sessions."""
        logger.info("Session monitor started")
        
        while self.is_running:
            try:
                # Run session cleanup
                await self.storage.cleanup_expired_sessions()
                
                # Check for inactive sessions
                await self._check_inactive_sessions()
                
                await asyncio.sleep(self.intervals["session_monitor"])
            
            except Exception as e:
                logger.error(f"Session monitor error: {e}")
                await asyncio.sleep(self.intervals["session_monitor"])
    
    async def _check_inactive_sessions(self):
        """Check for inactive sessions and emit events."""
        try:
            # Get all active sessions
            sessions = self.storage.sqlite_fetchall(
                "SELECT session_id, user_id, updated_at FROM sessions WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP"
            )
            
            inactive_threshold = datetime.now() - timedelta(hours=2)
            
            for session in sessions:
                session_updated = datetime.fromisoformat(session["updated_at"])
                if session_updated < inactive_threshold:
                    # Emit inactive session event
                    event = ContextEvent(
                        event_id=f"inactive_session_{session['session_id']}_{int(datetime.now().timestamp())}",
                        namespace="session_memory",
                        event_type="session_inactive",
                        data={
                            "session_id": session["session_id"],
                            "user_id": session["user_id"],
                            "last_activity": session["updated_at"]
                        },
                        timestamp=datetime.now(),
                        metadata={"monitor": "session_monitor"}
                    )
                    await self.emit_event(event)
        
        except Exception as e:
            logger.error(f"Error checking inactive sessions: {e}")
    
    async def _memory_cleanup_monitor(self):
        """Monitor and cleanup memory caches."""
        logger.info("Memory cleanup monitor started")
        
        while self.is_running:
            try:
                # Cleanup old cache entries
                await self._cleanup_old_cache_entries()
                
                # Cleanup old events
                await self._cleanup_old_events()
                
                await asyncio.sleep(self.intervals["memory_cleanup"])
            
            except Exception as e:
                logger.error(f"Memory cleanup monitor error: {e}")
                await asyncio.sleep(self.intervals["memory_cleanup"])
    
    async def _cleanup_old_cache_entries(self):
        """Cleanup old cache entries."""
        try:
            # Get all cache keys
            cache_keys = await self.storage.redis_keys("cache", "context_monitor", "*")
            
            cleanup_count = 0
            for key in cache_keys:
                if key.startswith("event:"):
                    # Events older than 7 days
                    event_data = await self.storage.redis_get("cache", "context_monitor", key)
                    if event_data:
                        event_info = json.loads(event_data)
                        event_time = datetime.fromisoformat(event_info["timestamp"])
                        if event_time < datetime.now() - timedelta(days=7):
                            await self.storage.redis_delete("cache", "context_monitor", key)
                            cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} old cache entries")
        
        except Exception as e:
            logger.error(f"Error cleaning up cache entries: {e}")
    
    async def _cleanup_old_events(self):
        """Cleanup old events from namespace indexes."""
        try:
            # Get namespace indexes
            namespace_keys = await self.storage.redis_keys("cache", "context_monitor", "events:namespace:*")
            
            for namespace_key in namespace_keys:
                # Get all events for namespace
                events = {}
                cursor = 0
                while True:
                    cursor, items = await self.storage._redis_pools["cache"].hscan(
                        self.storage._get_namespaced_key("context_monitor", namespace_key),
                        cursor=cursor
                    )
                    events.update(items)
                    if cursor == 0:
                        break
                
                # Remove old events
                cutoff_time = datetime.now() - timedelta(days=7)
                old_events = []
                
                for event_id, timestamp_str in events.items():
                    try:
                        event_time = datetime.fromisoformat(timestamp_str)
                        if event_time < cutoff_time:
                            old_events.append(event_id)
                    except:
                        old_events.append(event_id)  # Remove malformed entries
                
                # Remove old events from index
                for event_id in old_events:
                    await self.storage._redis_pools["cache"].hdel(
                        self.storage._get_namespaced_key("context_monitor", namespace_key),
                        event_id
                    )
                
                if old_events:
                    logger.debug(f"Cleaned up {len(old_events)} old events from {namespace_key}")
        
        except Exception as e:
            logger.error(f"Error cleaning up old events: {e}")
    
    async def _embedding_maintenance_monitor(self):
        """Monitor and maintain embedding index."""
        logger.info("Embedding maintenance monitor started")
        
        while self.is_running:
            try:
                # Check if embedding rebuild is needed
                stats = await self.embedding.get_stats()
                deleted_ratio = stats["deleted_embeddings"] / max(stats["total_embeddings"], 1)
                
                if deleted_ratio > 0.2:  # More than 20% deleted
                    logger.info("Rebuilding embedding index due to high deletion ratio")
                    await self.embedding.rebuild_index()
                
                await asyncio.sleep(self.intervals["embedding_rebuild"])
            
            except Exception as e:
                logger.error(f"Embedding maintenance monitor error: {e}")
                await asyncio.sleep(self.intervals["embedding_rebuild"])
    
    async def _context_analysis_monitor(self):
        """Monitor context changes and generate insights."""
        logger.info("Context analysis monitor started")
        
        while self.is_running:
            try:
                # Analyze activity patterns
                await self._analyze_activity_patterns()
                
                await asyncio.sleep(self.intervals["context_analysis"])
            
            except Exception as e:
                logger.error(f"Context analysis monitor error: {e}")
                await asyncio.sleep(self.intervals["context_analysis"])
    
    async def _analyze_activity_patterns(self):
        """Analyze activity patterns and generate insights."""
        try:
            # Get activity stats
            insights = {
                "timestamp": datetime.now().isoformat(),
                "activity_counters": self.activity_counters.copy(),
                "total_events": sum(
                    sum(events.values()) for events in self.activity_counters.values()
                )
            }
            
            # Store insights
            insights_key = f"insights:{int(datetime.now().timestamp() // 3600)}"  # Hourly insights
            await self.storage.redis_set(
                "cache", "context_monitor", insights_key,
                json.dumps(insights),
                expire=86400 * 30  # 30 days
            )
            
            # Reset counters periodically
            if datetime.now().minute == 0:  # Reset every hour
                self.activity_counters.clear()
        
        except Exception as e:
            logger.error(f"Error analyzing activity patterns: {e}")
    
    async def _health_check_monitor(self):
        """Monitor health of all components."""
        logger.info("Health check monitor started")
        
        while self.is_running:
            try:
                health_status = await self._check_component_health()
                
                # Store health status
                health_key = "health_status"
                await self.storage.redis_set(
                    "cache", "context_monitor", health_key,
                    json.dumps(health_status),
                    expire=300  # 5 minutes
                )
                
                await asyncio.sleep(self.intervals["health_check"])
            
            except Exception as e:
                logger.error(f"Health check monitor error: {e}")
                await asyncio.sleep(self.intervals["health_check"])
    
    async def _check_component_health(self) -> Dict[str, Any]:
        """Check health of all MemoryHub components."""
        health = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        try:
            # Check storage
            await self.storage._redis_pools["cache"].ping()
            health["components"]["storage"] = "healthy"
        except:
            health["components"]["storage"] = "unhealthy"
            health["overall_status"] = "degraded"
        
        try:
            # Check embedding service
            stats = await self.embedding.get_stats()
            health["components"]["embedding"] = "healthy"
            health["embedding_stats"] = stats
        except:
            health["components"]["embedding"] = "unhealthy"
            health["overall_status"] = "degraded"
        
        # Check task health
        running_tasks = len([task for task in self.tasks if not task.done()])
        health["components"]["background_tasks"] = f"{running_tasks}/{len(self.tasks)} running"
        
        if running_tasks < len(self.tasks):
            health["overall_status"] = "degraded"
        
        return health
    
    async def get_activity_stats(self) -> Dict[str, Any]:
        """Get current activity statistics."""
        return {
            "activity_counters": self.activity_counters.copy(),
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "running_tasks": len([task for task in self.tasks if not task.done()]),
            "event_queue_size": self.event_queue.qsize()
        } 