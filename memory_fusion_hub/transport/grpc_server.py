"""
gRPC server implementation for Memory Fusion Hub.

This module provides:
- MemoryFusionServicer: gRPC service implementation
- Protocol buffer conversion utilities
- Error handling and status codes
- Async/await interface with proper resource management
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import grpc
from grpc import aio
from pydantic import ValidationError, BaseModel

from ..core.fusion_service import FusionService
from ..core.models import MemoryItem, SessionData, KnowledgeRecord, MemoryEvent
# Prefer relative generated modules for typing consistency
from ..memory_fusion_pb2 import (
    GetResponse, PutResponse, DeleteResponse, BatchGetResponse,
    ExistsResponse, ListKeysResponse, HealthResponse,
    MemoryItem as ProtoMemoryItem, ComponentHealth,
)
from ..memory_fusion_pb2_grpc import (
    MemoryFusionServiceServicer,
    add_MemoryFusionServiceServicer_to_server,
)

logger = logging.getLogger(__name__)


class GRPCServerException(Exception):
    """Base exception for gRPC server operations."""
    pass


class MemoryFusionServicer(MemoryFusionServiceServicer):
    """
    gRPC service implementation for Memory Fusion Hub.
    
    Implements all MemoryFusionService RPCs defined in the protocol buffer,
    delegating to the FusionService for actual operations.
    """
    
    def __init__(self, fusion_service: FusionService):
        """
        Initialize gRPC servicer.
        
        Args:
            fusion_service: FusionService instance to handle requests
        """
        self.fusion_service = fusion_service
        logger.info("gRPC servicer initialized")
    
    async def Get(self, request, context) -> GetResponse:  # type: ignore[override]
        """Handle Get RPC."""
        try:
            logger.debug(f"gRPC Get request: key={request.key}")
            
            # Get item from FusionService
            agent_id = request.agent_id if request.agent_id else None
            item = await self.fusion_service.get(request.key, agent_id)
            
            # Create response
            response = GetResponse()
            response.found = item is not None
            
            if item:
                response.item.CopyFrom(self._pydantic_to_proto_memory_item(item))
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC Get error: {e}")
            response = GetResponse()
            response.found = False
            response.error = str(e)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    async def Put(self, request, context) -> PutResponse:  # type: ignore[override]
        """Handle Put RPC."""
        try:
            logger.debug(f"gRPC Put request: key={request.key}")
            
            # Convert proto item to Pydantic model
            item = self._proto_to_pydantic_memory_item(request.item)
            
            # Store item using FusionService
            agent_id = request.agent_id if request.agent_id else None
            await self.fusion_service.put(request.key, item, agent_id)
            
            # Create response
            response = PutResponse()
            response.success = True
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC Put error: {e}")
            response = PutResponse()
            response.success = False
            response.error = str(e)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    async def Delete(self, request, context) -> DeleteResponse:  # type: ignore[override]
        """Handle Delete RPC."""
        try:
            logger.debug(f"gRPC Delete request: key={request.key}")
            
            # Delete item using FusionService
            agent_id = request.agent_id if request.agent_id else None
            deleted = await self.fusion_service.delete(request.key, agent_id)
            
            # Create response
            response = DeleteResponse()
            response.success = True
            response.found = deleted
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC Delete error: {e}")
            response = DeleteResponse()
            response.success = False
            response.found = False
            response.error = str(e)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    async def BatchGet(self, request, context) -> BatchGetResponse:  # type: ignore[override]
        """Handle BatchGet RPC."""
        try:
            logger.debug(f"gRPC BatchGet request: {len(request.keys)} keys")
            
            # Get items using FusionService
            agent_id = request.agent_id if request.agent_id else None
            results = await self.fusion_service.batch_get(list(request.keys), agent_id)
            
            # Create response
            response = BatchGetResponse()
            
            for key, item in results.items():
                if item is not None:
                    proto_item = self._pydantic_to_proto_memory_item(item)
                    response.items[key].CopyFrom(proto_item)
                else:
                    response.missing_keys.append(key)
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC BatchGet error: {e}")
            response = BatchGetResponse()
            response.error = str(e)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    async def Exists(self, request, context) -> ExistsResponse:  # type: ignore[override]
        """Handle Exists RPC."""
        try:
            logger.debug(f"gRPC Exists request: key={request.key}")
            
            # Check existence using FusionService
            exists = await self.fusion_service.exists(request.key)
            
            # Create response
            response = ExistsResponse()
            response.exists = exists
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC Exists error: {e}")
            response = ExistsResponse()
            response.exists = False
            response.error = str(e)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    async def ListKeys(self, request, context) -> ListKeysResponse:  # type: ignore[override]
        """Handle ListKeys RPC."""
        try:
            logger.debug(f"gRPC ListKeys request: prefix={request.prefix}, limit={request.limit}")
            
            # Get keys using FusionService
            limit = request.limit if request.limit > 0 else 100
            keys = await self.fusion_service.list_keys(request.prefix, limit)
            
            # Create response
            response = ListKeysResponse()
            response.keys.extend(keys)
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC ListKeys error: {e}")
            response = ListKeysResponse()
            response.error = str(e)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    async def GetHealth(self, request, context) -> HealthResponse:  # type: ignore[override]
        """Handle GetHealth RPC."""
        try:
            logger.debug("gRPC GetHealth request")
            
            # Get health status using FusionService
            health_data = await self.fusion_service.get_health_status()
            
            # Create response
            response = HealthResponse()
            response.service = health_data.get('service', 'Memory Fusion Hub')
            response.status = health_data.get('status', 'unknown')
            response.timestamp = health_data.get('timestamp', datetime.utcnow().isoformat())
            
            # Add component health information
            components = health_data.get('components', {})
            for comp_name, comp_data in components.items():
                component_health = ComponentHealth()
                component_health.healthy = comp_data.get('healthy', False)
                
                # Add component info
                comp_info = comp_data.get('info', {})
                for key, value in comp_info.items():
                    component_health.info[key] = str(value)
                
                response.components[comp_name].CopyFrom(component_health)
            
            return response
            
        except Exception as e:
            logger.error(f"gRPC GetHealth error: {e}")
            response = HealthResponse()
            response.service = "Memory Fusion Hub"
            response.status = "unhealthy"
            response.error = str(e)
            response.timestamp = datetime.utcnow().isoformat()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return response
    
    def _pydantic_to_proto_memory_item(self, item: BaseModel) -> ProtoMemoryItem:
        """
        Convert Pydantic model to protobuf MemoryItem.
        
        Args:
            item: Pydantic model (MemoryItem, SessionData, etc.)
            
        Returns:
            Protobuf MemoryItem
        """
        proto_item = ProtoMemoryItem()
        
        if isinstance(item, MemoryItem):
            proto_item.key = item.key
            
            # Handle content based on type
            if isinstance(item.content, str):
                proto_item.text_content = item.content
            else:
                proto_item.json_content = json.dumps(item.content)
            
            proto_item.memory_type = item.memory_type.value if hasattr(item.memory_type, 'value') else str(item.memory_type)
            proto_item.timestamp = item.timestamp.isoformat()
            
            if item.updated_at:
                proto_item.updated_at = item.updated_at.isoformat()
            
            # Add metadata
            for key, value in item.metadata.items():
                proto_item.metadata[key] = str(value)
            
            # Add tags
            proto_item.tags.extend(item.tags)
            
            if item.source_agent:
                proto_item.source_agent = item.source_agent
            
            if item.expiry_timestamp:
                proto_item.expiry_timestamp = item.expiry_timestamp.isoformat()
        
        else:
            # For other types (SessionData, KnowledgeRecord), serialize as JSON
            proto_item.key = getattr(item, 'key', '') or getattr(item, 'session_id', '') or getattr(item, 'knowledge_id', '')
            proto_item.json_content = item.json()
            proto_item.memory_type = type(item).__name__.lower()
            proto_item.timestamp = datetime.utcnow().isoformat()
        
        return proto_item
    
    def _proto_to_pydantic_memory_item(self, proto_item: ProtoMemoryItem) -> MemoryItem:
        """
        Convert protobuf MemoryItem to Pydantic MemoryItem.
        
        Args:
            proto_item: Protobuf MemoryItem
            
        Returns:
            Pydantic MemoryItem
        """
        try:
            # Determine content
            if proto_item.HasField('text_content'):
                content: Any = proto_item.text_content
            elif proto_item.HasField('json_content'):
                try:
                    content = json.loads(proto_item.json_content)
                except json.JSONDecodeError:
                    content = proto_item.json_content  # Fallback to string
            else:
                content = ""
            
            # Convert timestamp
            timestamp = datetime.fromisoformat(proto_item.timestamp) if proto_item.timestamp else datetime.utcnow()
            
            # Convert updated_at if present
            updated_at = None
            if proto_item.updated_at:
                try:
                    updated_at = datetime.fromisoformat(proto_item.updated_at)
                except ValueError:
                    updated_at = None
            
            # Convert expiry_timestamp if present
            expiry_timestamp = None
            if proto_item.expiry_timestamp:
                try:
                    expiry_timestamp = datetime.fromisoformat(proto_item.expiry_timestamp)
                except ValueError:
                    expiry_timestamp = None
            
            # Create MemoryItem
            return MemoryItem(
                key=proto_item.key,
                content=content,
                memory_type=proto_item.memory_type or 'conversation',
                timestamp=timestamp,
                updated_at=updated_at,
                metadata=dict(proto_item.metadata),
                tags=list(proto_item.tags),
                source_agent=proto_item.source_agent if proto_item.source_agent else None,
                expiry_timestamp=expiry_timestamp
            )
            
        except Exception as e:
            logger.error(f"Error converting proto to Pydantic: {e}")
            # Fallback minimal item
            return MemoryItem(
                key=proto_item.key or 'unknown',
                content=proto_item.text_content or proto_item.json_content or ""
            )


class GRPCServer:
    """
    gRPC server wrapper for Memory Fusion Hub.
    
    Handles server lifecycle, configuration, and graceful shutdown.
    """
    
    def __init__(self, fusion_service: FusionService, port: int = 5714, max_workers: int = 8):
        """
        Initialize gRPC server.
        
        Args:
            fusion_service: FusionService instance
            port: Port to bind to
            max_workers: Maximum number of worker threads
        """
        self.fusion_service = fusion_service
        self.port = port
        self.max_workers = max_workers
        self.server: Optional[aio.Server] = None
        
        logger.info(f"gRPC server initialized on port {port}")
    
    async def start(self) -> None:
        """Start the gRPC server."""
        try:
            # Create server
            self.server = aio.server()
            
            # Add servicer
            servicer = MemoryFusionServicer(self.fusion_service)
            add_MemoryFusionServiceServicer_to_server(servicer, self.server)
            
            # Add port
            listen_addr = f'[::]:{self.port}'
            self.server.add_insecure_port(listen_addr)
            
            # Start server
            await self.server.start()
            logger.info(f"gRPC server started on {listen_addr}")
            
        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            raise GRPCServerException(f"Server startup failed: {e}")
    
    async def serve(self) -> None:
        """Start server and wait for termination."""
        await self.start()
        assert self.server is not None
        await self.server.wait_for_termination()
    
    async def stop(self, grace_period: int = 5) -> None:
        """Stop the gRPC server gracefully."""
        if self.server:
            logger.info("Stopping gRPC server...")
            await self.server.stop(grace_period)
            logger.info("gRPC server stopped")
    
    # Context manager support
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


async def run_grpc_server(fusion_service: FusionService, port: int = 5714, max_workers: int = 8) -> None:
    """
    Run gRPC server with the given FusionService.
    
    Args:
        fusion_service: FusionService instance
        port: Port to bind to
        max_workers: Maximum worker threads
    """
    server = GRPCServer(fusion_service, port, max_workers)
    
    try:
        await server.serve()
    except KeyboardInterrupt:  # pragma: no cover
        logger.info("gRPC server interrupted by user")
    except Exception as e:
        logger.error(f"gRPC server error: {e}")
    finally:
        await server.stop()