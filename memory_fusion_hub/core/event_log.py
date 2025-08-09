"""
Event log implementation for Memory Fusion Hub.

This module provides:
- EventLog: Append-only log writer for MemoryEvent objects
- Redis Streams for high-performance event publishing
- Event replay functionality for recovery
- NATS JetStream support for cross-machine replication
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime

import redis.asyncio as aioredis
from pydantic import BaseModel

from .models import MemoryEvent, EventType, ReplicationConfig

logger = logging.getLogger(__name__)


class EventLogException(Exception):
    """Base exception for event log operations."""
    pass


class EventLog:
    """
    Append-only event log writer using Redis Streams.
    
    Provides high-performance event publishing with ordering guarantees,
    event replay functionality, and optional NATS integration for 
    cross-machine replication.
    """
    
    def __init__(self, replication_config: ReplicationConfig):
        """
        Initialize event log.
        
        Args:
            replication_config: Configuration for replication settings
        """
        self.config = replication_config
        self.redis_client: Optional[aioredis.Redis] = None
        self.nats_client = None  # TODO: NATS client for cross-machine replication
        self.stream_name = f"mfh:{self.config.event_topic}"
        self.consumer_group = "mfh_processors"
        self._sequence_counter = 0
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the event log and create necessary streams."""
        try:
            # Initialize Redis connection for streams
            # Extract Redis URL from NATS URL for now (simplified)
            redis_url = "redis://localhost:6379/1"  # Use DB 1 for events
            
            self.redis_client = aioredis.Redis.from_url(
                redis_url,
                decode_responses=True,
                encoding='utf-8'
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Create stream and consumer group if they don't exist
            try:
                # Try to create consumer group (will fail if stream doesn't exist)
                await self.redis_client.xgroup_create(
                    self.stream_name, 
                    self.consumer_group, 
                    id='0', 
                    mkstream=True
                )
                logger.info(f"Created consumer group: {self.consumer_group}")
            except Exception as e:
                # Group might already exist, that's fine
                logger.debug(f"Consumer group creation result: {e}")
            
            # Initialize sequence counter
            await self._initialize_sequence_counter()
            
            logger.info(f"Event log initialized: {self.stream_name}")
            
        except Exception as e:
            # Degrade gracefully in environments without Redis/NATS
            logger.warning(f"Event log initialization degraded: {e}")
            self.redis_client = None
            # Continue without raising to allow service startup
    
    async def _initialize_sequence_counter(self) -> None:
        """Initialize the sequence counter based on existing events."""
        try:
            # Get the latest event to determine the next sequence number
            latest_events = await self.redis_client.xrevrange(
                self.stream_name, count=1
            )
            
            if latest_events:
                # Extract sequence number from the latest event
                latest_event = latest_events[0]
                event_data = latest_event[1]
                sequence_str = event_data.get('sequence_number', '0')
                self._sequence_counter = int(sequence_str) + 1
            else:
                self._sequence_counter = 1
                
            logger.debug(f"Initialized sequence counter: {self._sequence_counter}")
            
        except Exception as e:
            logger.warning(f"Failed to initialize sequence counter: {e}")
            self._sequence_counter = 1
    
    async def publish(self, event_type: str, target_key: str, payload: Optional[Dict[str, Any]] = None, 
                     agent_id: Optional[str] = None, correlation_id: Optional[str] = None,
                     previous_value: Optional[Dict[str, Any]] = None) -> str:
        """
        Publish an event to the log.
        
        Args:
            event_type: Type of event (CREATE, UPDATE, DELETE, READ)
            target_key: Key of the memory item affected
            payload: Event-specific data
            agent_id: ID of the agent performing the operation
            correlation_id: ID for correlating related events
            previous_value: Previous value before the change
            
        Returns:
            Event ID of the published event
        """
        try:
            if not self.redis_client:
                # Degraded mode: synthesize an ID and return without raising
                synthetic_id = f"evt_degraded_{uuid.uuid4().hex[:8]}"
                logger.debug("EventLog degraded mode: skipping publish")
                return synthetic_id
            
            async with self._lock:
                # Generate unique event ID
                event_id = f"evt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                # Get next sequence number
                sequence_number = self._sequence_counter
                self._sequence_counter += 1
                
                # Create MemoryEvent object
                memory_event = MemoryEvent(
                    event_id=event_id,
                    event_type=EventType(event_type),
                    target_key=target_key,
                    timestamp=datetime.utcnow(),
                    agent_id=agent_id,
                    payload=payload,
                    previous_value=previous_value,
                    sequence_number=sequence_number,
                    correlation_id=correlation_id
                )
                
                # Prepare event data for Redis Stream
                event_data = {
                    'event_id': memory_event.event_id,
                    'event_type': memory_event.event_type.value,
                    'target_key': memory_event.target_key,
                    'timestamp': memory_event.timestamp.isoformat(),
                    'sequence_number': str(memory_event.sequence_number),
                    'agent_id': memory_event.agent_id or '',
                    'correlation_id': memory_event.correlation_id or '',
                    'payload': json.dumps(memory_event.payload or {}),
                    'previous_value': json.dumps(memory_event.previous_value or {})
                }
                
                # Publish to Redis Stream
                stream_id = await self.redis_client.xadd(
                    self.stream_name,
                    event_data,
                    maxlen=100000,  # Keep last 100k events
                    approximate=True
                )
                
                logger.debug(f"Published event {event_id} to stream {self.stream_name}")
                
                # TODO: Publish to NATS for cross-machine replication if enabled
                if self.config.enabled and self.nats_client:
                    await self._publish_to_nats(memory_event)
                
                return event_id
                
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            raise EventLogException(f"Event publish failed: {e}")
    
    async def _publish_to_nats(self, event: MemoryEvent) -> None:
        """
        Publish event to NATS for cross-machine replication.
        
        Args:
            event: MemoryEvent to replicate
        """
        # TODO: Implement NATS JetStream publishing
        # This would be implemented when NATS is available
        logger.debug(f"NATS publishing not yet implemented for event: {event.event_id}")
    
    async def get_events(self, start_id: str = '0', count: int = 100, 
                        target_key: Optional[str] = None) -> List[MemoryEvent]:
        """
        Retrieve events from the log.
        
        Args:
            start_id: Stream ID to start from ('0' for beginning)
            count: Maximum number of events to retrieve
            target_key: Filter by target key if specified
            
        Returns:
            List of MemoryEvent objects
        """
        try:
            if not self.redis_client:
                raise EventLogException("Event log not initialized")
            
            # Read events from the stream
            events_data = await self.redis_client.xrange(
                self.stream_name,
                min=start_id,
                max='+',
                count=count
            )
            
            events = []
            for stream_id, event_data in events_data:
                try:
                    # Reconstruct MemoryEvent from stream data
                    memory_event = self._deserialize_event(event_data)
                    
                    # Filter by target key if specified
                    if target_key is None or memory_event.target_key == target_key:
                        events.append(memory_event)
                        
                except Exception as e:
                    logger.warning(f"Failed to deserialize event {stream_id}: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            raise EventLogException(f"Event retrieval failed: {e}")
    
    async def get_events_since(self, since_timestamp: datetime, 
                              target_key: Optional[str] = None) -> List[MemoryEvent]:
        """
        Get events since a specific timestamp.
        
        Args:
            since_timestamp: Timestamp to start from
            target_key: Filter by target key if specified
            
        Returns:
            List of MemoryEvent objects
        """
        try:
            if not self.redis_client:
                raise EventLogException("Event log not initialized")
            
            # Convert timestamp to Redis stream time format
            timestamp_ms = int(since_timestamp.timestamp() * 1000)
            start_id = f"{timestamp_ms}-0"
            
            # Get all events since the timestamp
            events = await self.get_events(start_id=start_id, count=10000, target_key=target_key)
            
            # Additional filtering by timestamp (Redis stream time is not exact)
            filtered_events = [
                event for event in events 
                if event.timestamp >= since_timestamp
            ]
            
            return filtered_events
            
        except Exception as e:
            logger.error(f"Failed to get events since {since_timestamp}: {e}")
            raise EventLogException(f"Event retrieval failed: {e}")
    
    async def replay_events(self, target_key: Optional[str] = None, 
                           since_sequence: Optional[int] = None) -> AsyncGenerator[MemoryEvent, None]:
        """
        Replay events from the log as an async generator.
        
        Args:
            target_key: Filter by target key if specified
            since_sequence: Start from sequence number if specified
            
        Yields:
            MemoryEvent objects in chronological order
        """
        try:
            if not self.redis_client:
                raise EventLogException("Event log not initialized")
            
            start_id = '0'
            batch_size = 1000
            
            while True:
                # Get batch of events
                events_data = await self.redis_client.xrange(
                    self.stream_name,
                    min=start_id,
                    max='+',
                    count=batch_size
                )
                
                if not events_data:
                    break
                
                for stream_id, event_data in events_data:
                    try:
                        memory_event = self._deserialize_event(event_data)
                        
                        # Apply filters
                        if target_key and memory_event.target_key != target_key:
                            continue
                            
                        if since_sequence and memory_event.sequence_number < since_sequence:
                            continue
                        
                        yield memory_event
                        
                    except Exception as e:
                        logger.warning(f"Failed to deserialize event {stream_id}: {e}")
                        continue
                
                # Update start_id for next batch
                last_stream_id = events_data[-1][0]
                start_id = f"({last_stream_id}"  # Exclusive start
                
        except Exception as e:
            logger.error(f"Failed to replay events: {e}")
            raise EventLogException(f"Event replay failed: {e}")
    
    def _deserialize_event(self, event_data: Dict[str, str]) -> MemoryEvent:
        """
        Deserialize event data from Redis stream format to MemoryEvent.
        
        Args:
            event_data: Raw event data from Redis stream
            
        Returns:
            MemoryEvent object
        """
        try:
            # Parse JSON fields
            payload = json.loads(event_data.get('payload', '{}'))
            previous_value = json.loads(event_data.get('previous_value', '{}'))
            
            # Parse timestamp
            timestamp = datetime.fromisoformat(event_data['timestamp'])
            
            # Create MemoryEvent
            return MemoryEvent(
                event_id=event_data['event_id'],
                event_type=EventType(event_data['event_type']),
                target_key=event_data['target_key'],
                timestamp=timestamp,
                agent_id=event_data['agent_id'] if event_data['agent_id'] else None,
                payload=payload if payload else None,
                previous_value=previous_value if previous_value else None,
                sequence_number=int(event_data['sequence_number']),
                correlation_id=event_data['correlation_id'] if event_data['correlation_id'] else None
            )
            
        except Exception as e:
            raise ValueError(f"Failed to deserialize event data: {e}")
    
    async def get_latest_sequence(self) -> int:
        """
        Get the latest sequence number from the event log.
        
        Returns:
            Latest sequence number
        """
        try:
            if not self.redis_client:
                raise EventLogException("Event log not initialized")
            
            # Get the latest event
            latest_events = await self.redis_client.xrevrange(
                self.stream_name, count=1
            )
            
            if latest_events:
                event_data = latest_events[0][1]
                return int(event_data.get('sequence_number', 0))
            else:
                return 0
                
        except Exception as e:
            logger.error(f"Failed to get latest sequence: {e}")
            return 0
    
    async def get_stream_info(self) -> Dict[str, Any]:
        """
        Get information about the event stream.
        
        Returns:
            Dictionary with stream statistics
        """
        try:
            if not self.redis_client:
                return {}
            
            stream_info = await self.redis_client.xinfo_stream(self.stream_name)
            
            return {
                'length': stream_info.get('length', 0),
                'first_entry_id': stream_info.get('first-entry', ['0-0'])[0],
                'last_entry_id': stream_info.get('last-entry', ['0-0'])[0],
                'consumer_groups': stream_info.get('groups', 0),
                'max_deleted_entry_id': stream_info.get('max-deleted-entry-id', '0-0'),
                'entries_added': stream_info.get('entries-added', 0),
            }
            
        except Exception as e:
            logger.error(f"Failed to get stream info: {e}")
            return {}
    
    async def compact_log(self, keep_recent_count: int = 50000) -> int:
        """
        Compact the event log by removing old entries.
        
        Args:
            keep_recent_count: Number of recent events to keep
            
        Returns:
            Number of entries removed
        """
        try:
            if not self.redis_client:
                raise EventLogException("Event log not initialized")
            
            # Get current stream length
            stream_info = await self.get_stream_info()
            current_length = stream_info.get('length', 0)
            
            if current_length <= keep_recent_count:
                return 0
            
            # Trim the stream to keep only recent entries
            await self.redis_client.xtrim(
                self.stream_name,
                maxlen=keep_recent_count,
                approximate=True
            )
            
            # Calculate how many were removed
            new_info = await self.get_stream_info()
            new_length = new_info.get('length', 0)
            removed_count = current_length - new_length
            
            logger.info(f"Compacted event log: removed {removed_count} entries")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to compact log: {e}")
            return 0
    
    async def close(self) -> None:
        """Close the event log and clean up resources."""
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None
                
            if self.nats_client:
                await self.nats_client.close()
                self.nats_client = None
                
            logger.info("Event log connection closed")
            
        except Exception as e:
            logger.error(f"Error closing event log: {e}")