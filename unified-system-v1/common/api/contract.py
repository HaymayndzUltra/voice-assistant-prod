"""
WP-06 API Contract System
Standardized API contracts and communication patterns for all agents
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import logging

logger = logging.getLogger(__name__)

class APIVersion(Enum):
    """Supported API versions"""
    V1 = "v1"
    V2 = "v2"

class MessageType(Enum):
    """Standard message types"""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"
    HEARTBEAT = "heartbeat"

class Priority(Enum):
    """Request priority levels"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    CRITICAL = "critical"

class Status(Enum):
    """Standard response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"

@dataclass
class APIHeader:
    """Standard API message header"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    version: APIVersion = APIVersion.V1
    message_type: MessageType = MessageType.REQUEST
    source_agent: str = ""
    target_agent: str = ""
    correlation_id: Optional[str] = None
    priority: Priority = Priority.NORMAL
    timeout: float = 30.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert header to dictionary"""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "version": self.version.value,
            "message_type": self.message_type.value,
            "source_agent": self.source_agent,
            "target_agent": self.target_agent,
            "correlation_id": self.correlation_id,
            "priority": self.priority.value,
            "timeout": self.timeout
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIHeader':
        """Create header from dictionary"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            version=APIVersion(data.get("version", "v1")),
            message_type=MessageType(data.get("message_type", "request")),
            source_agent=data.get("source_agent", ""),
            target_agent=data.get("target_agent", ""),
            correlation_id=data.get("correlation_id"),
            priority=Priority(data.get("priority", "normal")),
            timeout=data.get("timeout", 30.0)
        )

@dataclass
class APIResponse:
    """Standard API response format"""
    status: Status
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "processing_time": self.processing_time
        }
    
    @classmethod
    def success(cls, data: Any = None, metadata: Dict[str, Any] = None) -> 'APIResponse':
        """Create success response"""
        return cls(
            status=Status.SUCCESS,
            data=data,
            metadata=metadata or {}
        )
    
    @classmethod
    def error(cls, error_msg: str, error_code: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> 'APIResponse':
        """Create error response"""
        return cls(
            status=Status.ERROR,
            error=error_msg,
            error_code=error_code,
            metadata=metadata or {}
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIResponse':
        """Create response from dictionary"""
        return cls(
            status=Status(data.get("status", "error")),
            data=data.get("data"),
            error=data.get("error"),
            error_code=data.get("error_code"),
            metadata=data.get("metadata", {}),
            processing_time=data.get("processing_time")
        )

@dataclass
class APIMessage:
    """Complete API message with header and payload"""
    header: APIHeader
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "header": self.header.to_dict(),
            "payload": self.payload
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'APIMessage':
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls(
            header=APIHeader.from_dict(data.get("header", {})),
            payload=data.get("payload", {})
        )
    
    def create_response(self, response: APIResponse) -> 'APIMessage':
        """Create response message from this request"""
        response_header = APIHeader(
            message_id=str(uuid.uuid4()),
            timestamp=time.time(),
            version=self.header.version,
            message_type=MessageType.RESPONSE,
            source_agent=self.header.target_agent,
            target_agent=self.header.source_agent,
            correlation_id=self.header.message_id,
            priority=self.header.priority
        )
        
        return APIMessage(
            header=response_header,
            payload=response.to_dict()
        )

class APIContract(ABC):
    """Abstract base class for API contracts"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Contract name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> APIVersion:
        """Contract version"""
        pass
    
    @abstractmethod
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate request payload"""
        pass
    
    @abstractmethod
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate response payload"""
        pass
    
    @abstractmethod
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process API request"""
        pass

class StandardAPIContract(APIContract):
    """Standard API contract implementation"""
    
    def __init__(self, 
                 contract_name: str,
                 required_fields: Optional[List[str]] = None,
                 optional_fields: Optional[List[str]] = None,
                 response_schema: Optional[Dict[str, Type]] = None):
        self._name = contract_name
        self._version = APIVersion.V1
        self.required_fields = required_fields or []
        self.optional_fields = optional_fields or []
        self.response_schema = response_schema or {}
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def version(self) -> APIVersion:
        return self._version
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate request has required fields"""
        for field in self.required_fields:
            if field not in payload:
                logger.warning(f"Missing required field: {field}")
                return False
        return True
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate response structure"""
        if "status" not in payload:
            return False
        
        try:
            Status(payload["status"])
            return True
        except ValueError:
            return False
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Default processing - override in subclasses"""
        return APIResponse.error("Contract not implemented")

class APIRegistry:
    """Registry for API contracts and routing"""
    
    def __init__(self):
        self.contracts: Dict[str, APIContract] = {}
        self.routes: Dict[str, str] = {}  # endpoint -> contract_name
        
    def register_contract(self, contract: APIContract, endpoints: List[str] = None):
        """Register an API contract"""
        self.contracts[contract.name] = contract
        
        if endpoints:
            for endpoint in endpoints:
                self.routes[endpoint] = contract.name
        
        logger.info(f"Registered API contract: {contract.name} v{contract.version.value}")
    
    def get_contract(self, name: str) -> Optional[APIContract]:
        """Get contract by name"""
        return self.contracts.get(name)
    
    def get_contract_for_endpoint(self, endpoint: str) -> Optional[APIContract]:
        """Get contract for specific endpoint"""
        contract_name = self.routes.get(endpoint)
        if contract_name:
            return self.contracts.get(contract_name)
        return None
    
    def list_contracts(self) -> List[str]:
        """List all registered contracts"""
        return list(self.contracts.keys())
    
    def get_contract_info(self, name: str) -> Dict[str, Any]:
        """Get contract information"""
        contract = self.contracts.get(name)
        if not contract:
            return {}
        
        return {
            "name": contract.name,
            "version": contract.version.value,
            "endpoints": [ep for ep, cn in self.routes.items() if cn == name]
        }

class APIValidation:
    """API message validation utilities"""
    
    @staticmethod
    def validate_message_structure(message: APIMessage) -> List[str]:
        """Validate basic message structure"""
        errors = []
        
        # Validate header
        if not message.header.source_agent:
            errors.append("Missing source_agent in header")
        
        if not message.header.target_agent:
            errors.append("Missing target_agent in header")
        
        if message.header.timeout <= 0:
            errors.append("Invalid timeout value")
        
        # Validate payload exists
        if message.payload is None:
            errors.append("Missing payload")
        
        return errors
    
    @staticmethod
    def validate_response_format(response: APIResponse) -> List[str]:
        """Validate response format"""
        errors = []
        
        if response.status == Status.ERROR and not response.error:
            errors.append("Error status requires error message")
        
        if response.status == Status.SUCCESS and response.error:
            errors.append("Success status should not have error message")
        
        return errors

class APIMiddleware(ABC):
    """Abstract middleware for API processing"""
    
    @abstractmethod
    async def process_request(self, message: APIMessage) -> Optional[APIMessage]:
        """Process incoming request. Return None to continue, modified message to override"""
        pass
    
    @abstractmethod
    async def process_response(self, message: APIMessage, response: APIResponse) -> Optional[APIResponse]:
        """Process outgoing response. Return None to continue, modified response to override"""
        pass

class LoggingMiddleware(APIMiddleware):
    """Logging middleware for API calls"""
    
    def __init__(self, log_level: str = "INFO"):
        self.logger = logging.getLogger("api.middleware.logging")
        self.logger.setLevel(getattr(logging, log_level))
    
    async def process_request(self, message: APIMessage) -> Optional[APIMessage]:
        """Log incoming request"""
        self.logger.info(f"API Request: {message.header.source_agent} -> {message.header.target_agent} "
                        f"[{message.header.message_id}] {message.header.message_type.value}")
        return None
    
    async def process_response(self, message: APIMessage, response: APIResponse) -> Optional[APIResponse]:
        """Log outgoing response"""
        self.logger.info(f"API Response: {response.status.value} "
                        f"[{message.header.correlation_id}] "
                        f"time: {response.processing_time:.4f}s" if response.processing_time else "")
        return None

class RateLimitMiddleware(APIMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts: Dict[str, List[float]] = {}
    
    async def process_request(self, message: APIMessage) -> Optional[APIMessage]:
        """Check rate limits"""
        agent_id = message.header.source_agent
        current_time = time.time()
        
        # Initialize if not exists
        if agent_id not in self.request_counts:
            self.request_counts[agent_id] = []
        
        # Clean old requests
        cutoff_time = current_time - self.window_seconds
        self.request_counts[agent_id] = [
            req_time for req_time in self.request_counts[agent_id] 
            if req_time > cutoff_time
        ]
        
        # Check limit
        if len(self.request_counts[agent_id]) >= self.max_requests:
            # Create rate limit response
            response = APIResponse.error(
                "Rate limit exceeded", 
                "RATE_LIMIT_ERROR",
                {"retry_after": self.window_seconds}
            )
            response.status = Status.RATE_LIMITED
            
            # Create error message
            error_message = message.create_response(response)
            return error_message
        
        # Add current request
        self.request_counts[agent_id].append(current_time)
        return None
    
    async def process_response(self, message: APIMessage, response: APIResponse) -> Optional[APIResponse]:
        """No response processing needed"""
        return None

class APIProcessor:
    """Main API processor with middleware support"""
    
    def __init__(self):
        self.registry = APIRegistry()
        self.middleware: List[APIMiddleware] = []
        
    def add_middleware(self, middleware: APIMiddleware):
        """Add middleware to processing chain"""
        self.middleware.append(middleware)
        logger.info(f"Added middleware: {middleware.__class__.__name__}")
    
    def register_contract(self, contract: APIContract, endpoints: List[str] = None):
        """Register API contract"""
        self.registry.register_contract(contract, endpoints)
    
    async def process_message(self, message: APIMessage) -> APIMessage:
        """Process API message through middleware and contracts"""
        start_time = time.time()
        
        try:
            # Validate basic structure
            errors = APIValidation.validate_message_structure(message)
            if errors:
                response = APIResponse.error(f"Validation errors: {', '.join(errors)}")
                return message.create_response(response)
            
            # Process through middleware (request phase)
            for middleware in self.middleware:
                result = await middleware.process_request(message)
                if result is not None:
                    # Middleware returned a response, short-circuit
                    return result
            
            # Find and execute contract
            endpoint = message.payload.get("endpoint", "")
            contract = self.registry.get_contract_for_endpoint(endpoint)
            
            if not contract:
                response = APIResponse.error(f"No contract found for endpoint: {endpoint}")
            else:
                # Validate request
                if not contract.validate_request(message.payload):
                    response = APIResponse.error("Request validation failed")
                else:
                    # Process request
                    response = await contract.process_request(message)
            
            # Set processing time
            response.processing_time = time.time() - start_time
            
            # Process through middleware (response phase)
            for middleware in self.middleware:
                result = await middleware.process_response(message, response)
                if result is not None:
                    response = result
            
            return message.create_response(response)
            
        except Exception as e:
            logger.error(f"Error processing API message: {e}")
            response = APIResponse.error(f"Processing error: {str(e)}")
            response.processing_time = time.time() - start_time
            return message.create_response(response)

# Global API processor instance
_api_processor: Optional[APIProcessor] = None

def get_api_processor() -> APIProcessor:
    """Get global API processor instance"""
    global _api_processor
    if _api_processor is None:
        _api_processor = APIProcessor()
        
        # Add default middleware
        _api_processor.add_middleware(LoggingMiddleware())
        _api_processor.add_middleware(RateLimitMiddleware())
        
    return _api_processor

# Convenience functions for common operations
def create_request(source_agent: str, 
                  target_agent: str, 
                  endpoint: str,
                  data: Dict[str, Any] = None,
                  priority: Priority = Priority.NORMAL,
                  timeout: float = 30.0) -> APIMessage:
    """Create standard API request message"""
    
    header = APIHeader(
        source_agent=source_agent,
        target_agent=target_agent,
        message_type=MessageType.REQUEST,
        priority=priority,
        timeout=timeout
    )
    
    payload = {"endpoint": endpoint}
    if data:
        payload.update(data)
    
    return APIMessage(header=header, payload=payload)

def create_event(source_agent: str,
                event_type: str,
                data: Dict[str, Any] = None,
                priority: Priority = Priority.NORMAL) -> APIMessage:
    """Create event message"""
    
    header = APIHeader(
        source_agent=source_agent,
        target_agent="*",  # Broadcast
        message_type=MessageType.EVENT,
        priority=priority
    )
    
    payload = {"event_type": event_type}
    if data:
        payload.update(data)
    
    return APIMessage(header=header, payload=payload)