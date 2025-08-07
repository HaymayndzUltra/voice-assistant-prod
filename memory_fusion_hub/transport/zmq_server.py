"""
ZMQ REQ/REP server implementation for Memory Fusion Hub.

This module provides:
- ZMQServer: REQ/REP server with JSON serialization
- Request parsing and routing to FusionService methods
- Error handling and response formatting
- Async/await interface with proper resource management
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import zmq
import zmq.asyncio
from pydantic import BaseModel, ValidationError

from ..core.fusion_service import FusionService
from ..core.models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent

logger = logging.getLogger(__name__)


class ZMQServerException(Exception):
    """Base exception for ZMQ server operations."""
    pass


class ZMQServer:
    """
    ZMQ REQ/REP server for Memory Fusion Hub.
    
    Provides JSON-based API for memory operations with proper error handling,
    request validation, and response formatting.
    """
    
    def __init__(self, fusion_service: FusionService, port: int = 5713):
        """
        Initialize ZMQ server.
        
        Args:
            fusion_service: FusionService instance to handle requests
            port: Port to bind the ZMQ socket to
        """
        self.fusion_service = fusion_service
        self.port = port
        self.context = None
        self.socket = None
        self.running = False
        
        # Request handlers mapping
        self.handlers = {
            'get': self._handle_get,
            'put': self._handle_put,
            'delete': self._handle_delete,
            'exists': self._handle_exists,
            'list_keys': self._handle_list_keys,
            'batch_get': self._handle_batch_get,
            'health': self._handle_health,
            'ping': self._handle_ping
        }
        
        logger.info(f"ZMQ server initialized on port {port}")
    
    async def start(self) -> None:
        """Start the ZMQ server and begin processing requests."""
        try:
            # Create ZMQ context and socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            
            self.running = True
            logger.info(f"ZMQ server started on port {self.port}")
            
            # Start processing requests
            await self._process_requests()
            
        except Exception as e:
            logger.error(f"Failed to start ZMQ server: {e}")
            raise ZMQServerException(f"Server startup failed: {e}")
    
    async def stop(self) -> None:
        """Stop the ZMQ server and clean up resources."""
        try:
            self.running = False
            
            if self.socket:
                self.socket.close()
                self.socket = None
                
            if self.context:
                self.context.term()
                self.context = None
                
            logger.info("ZMQ server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping ZMQ server: {e}")
    
    async def _process_requests(self) -> None:
        """Main request processing loop."""
        while self.running:
            try:
                # Wait for request with timeout
                if await self._wait_for_request(timeout_ms=1000):
                    # Receive request
                    request_data = await self.socket.recv_string(zmq.NOBLOCK)
                    logger.debug(f"Received request: {request_data[:200]}...")
                    
                    # Process request and send response
                    response = await self._handle_request(request_data)
                    await self.socket.send_string(response)
                    
            except zmq.Again:
                # Timeout - continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                # Send error response if possible
                try:
                    error_response = self._format_error_response(str(e))
                    await self.socket.send_string(error_response)
                except Exception:
                    logger.error("Failed to send error response")
                    break
    
    async def _wait_for_request(self, timeout_ms: int) -> bool:
        """
        Wait for a request with timeout.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if request is available, False on timeout
        """
        try:
            poller = zmq.asyncio.Poller()
            poller.register(self.socket, zmq.POLLIN)
            
            events = await poller.poll(timeout_ms)
            return len(events) > 0
        except Exception:
            return False
    
    async def _handle_request(self, request_data: str) -> str:
        """
        Handle incoming request and return formatted response.
        
        Args:
            request_data: JSON request string
            
        Returns:
            JSON response string
        """
        try:
            # Parse JSON request
            request = json.loads(request_data)
            
            # Validate request structure
            if not isinstance(request, dict):
                raise ValueError("Request must be a JSON object")
            
            action = request.get('action')
            if not action:
                raise ValueError("Request must include 'action' field")
            
            # Get handler for action
            handler = self.handlers.get(action)
            if not handler:
                raise ValueError(f"Unknown action: {action}")
            
            # Execute handler
            result = await handler(request)
            
            # Format success response
            response = {
                'success': True,
                'action': action,
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return json.dumps(response, default=self._json_serializer)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request: {e}")
            return self._format_error_response("Invalid JSON format")
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return self._format_error_response(str(e))
    
    async def _handle_get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get request."""
        key = request.get('key')
        if not key:
            raise ValueError("Get request requires 'key' field")
        
        agent_id = request.get('agent_id')
        
        item = await self.fusion_service.get(key, agent_id)
        
        return {
            'found': item is not None,
            'item': item.dict() if item else None
        }
    
    async def _handle_put(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle put request."""
        key = request.get('key')
        item_data = request.get('item')
        
        if not key:
            raise ValueError("Put request requires 'key' field")
        if not item_data:
            raise ValueError("Put request requires 'item' field")
        
        agent_id = request.get('agent_id')
        
        # Determine item type and create appropriate model
        item = self._deserialize_item(item_data)
        
        await self.fusion_service.put(key, item, agent_id)
        
        return {'stored': True}
    
    async def _handle_delete(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete request."""
        key = request.get('key')
        if not key:
            raise ValueError("Delete request requires 'key' field")
        
        agent_id = request.get('agent_id')
        
        deleted = await self.fusion_service.delete(key, agent_id)
        
        return {
            'deleted': deleted,
            'found': deleted
        }
    
    async def _handle_exists(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle exists request."""
        key = request.get('key')
        if not key:
            raise ValueError("Exists request requires 'key' field")
        
        exists = await self.fusion_service.exists(key)
        
        return {'exists': exists}
    
    async def _handle_list_keys(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list_keys request."""
        prefix = request.get('prefix', '')
        limit = request.get('limit', 100)
        
        if not isinstance(limit, int) or limit <= 0:
            limit = 100
        
        keys = await self.fusion_service.list_keys(prefix, limit)
        
        return {
            'keys': keys,
            'count': len(keys)
        }
    
    async def _handle_batch_get(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch_get request."""
        keys = request.get('keys')
        if not keys or not isinstance(keys, list):
            raise ValueError("Batch get request requires 'keys' field with list of keys")
        
        agent_id = request.get('agent_id')
        
        results = await self.fusion_service.batch_get(keys, agent_id)
        
        # Separate found and missing items
        found_items = {}
        missing_keys = []
        
        for key, item in results.items():
            if item is not None:
                found_items[key] = item.dict()
            else:
                missing_keys.append(key)
        
        return {
            'items': found_items,
            'missing_keys': missing_keys,
            'total_requested': len(keys),
            'found_count': len(found_items)
        }
    
    async def _handle_health(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check request."""
        health_status = await self.fusion_service.get_health_status()
        return health_status
    
    async def _handle_ping(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping request."""
        return {
            'pong': True,
            'server': 'Memory Fusion Hub ZMQ Server',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _deserialize_item(self, item_data: Dict[str, Any]) -> BaseModel:
        """
        Deserialize item data to appropriate Pydantic model.
        
        Args:
            item_data: Dictionary with item data
            
        Returns:
            Appropriate Pydantic model instance
        """
        try:
            # Determine model type from item_type field or data structure
            item_type = item_data.get('item_type') or item_data.get('memory_type', 'memory_item')
            
            if item_type == 'session' or 'session_id' in item_data:
                return SessionData(**item_data)
            elif item_type == 'knowledge' or 'knowledge_id' in item_data:
                return KnowledgeRecord(**item_data)
            elif item_type == 'event' or 'event_id' in item_data:
                return MemoryEvent(**item_data)
            else:
                # Default to MemoryItem
                return MemoryItem(**item_data)
                
        except ValidationError as e:
            raise ValueError(f"Invalid item data: {e}")
    
    def _format_error_response(self, error_message: str) -> str:
        """Format error response as JSON."""
        response = {
            'success': False,
            'error': error_message,
            'timestamp': datetime.utcnow().isoformat()
        }
        return json.dumps(response)
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


async def run_zmq_server(fusion_service: FusionService, port: int = 5713) -> None:
    """
    Run ZMQ server with the given FusionService.
    
    Args:
        fusion_service: FusionService instance
        port: Port to bind to
    """
    server = ZMQServer(fusion_service, port)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("ZMQ server interrupted by user")
    except Exception as e:
        logger.error(f"ZMQ server error: {e}")
    finally:
        await server.stop()