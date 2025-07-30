"""
WP-06 Standard API Contracts
Pre-defined contracts for common agent operations
"""

from typing import Dict, Any, List
from common.api.contract import (
    APIContract, APIMessage, APIResponse, APIVersion
)
import logging

logger = logging.getLogger(__name__)

class HealthCheckContract(APIContract):
    """Standard health check contract"""
    
    @property
    def name(self) -> str:
        return "health_check"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Health check requires no specific fields"""
        return True
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate health check response"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process health check request"""
        return APIResponse.success({
            "status": "healthy",
            "timestamp": message.header.timestamp,
            "agent": message.header.target_agent
        })

class StatusContract(APIContract):
    """Agent status reporting contract"""
    
    @property
    def name(self) -> str:
        return "status"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Status request validation"""
        return True
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Status response validation"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process status request"""
        return APIResponse.success({
            "agent_id": message.header.target_agent,
            "status": "active",
            "uptime": 0,  # Should be implemented by specific agent
            "load": {"cpu": 0, "memory": 0},
            "connections": {"active": 0, "total": 0}
        })

class ConfigContract(APIContract):
    """Configuration management contract"""
    
    @property
    def name(self) -> str:
        return "config"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Config request validation"""
        action = payload.get("action")
        return action in ["get", "set", "list"]
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Config response validation"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process configuration request"""
        action = message.payload.get("action")
        
        if action == "get":
            key = message.payload.get("key")
            if not key:
                return APIResponse.error("Missing config key")
            
            return APIResponse.success({
                "key": key,
                "value": None,  # Should be implemented by specific agent
                "type": "string"
            })
        
        elif action == "set":
            key = message.payload.get("key")
            value = message.payload.get("value")
            
            if not key:
                return APIResponse.error("Missing config key")
            
            return APIResponse.success({
                "key": key,
                "previous_value": None,
                "new_value": value,
                "updated": True
            })
        
        elif action == "list":
            return APIResponse.success({
                "config_keys": [],  # Should be implemented by specific agent
                "total": 0
            })
        
        return APIResponse.error(f"Unknown action: {action}")

class DataProcessingContract(APIContract):
    """Data processing contract for ML/AI operations"""
    
    @property
    def name(self) -> str:
        return "data_processing"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Data processing request validation"""
        required_fields = ["operation", "data"]
        return all(field in payload for field in required_fields)
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Data processing response validation"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process data processing request"""
        operation = message.payload.get("operation")
        data = message.payload.get("data")
        
        if operation == "analyze":
            return APIResponse.success({
                "analysis_id": "analysis_001",
                "status": "completed",
                "results": {
                    "summary": "Data analysis complete",
                    "metrics": {}
                }
            })
        
        elif operation == "transform":
            return APIResponse.success({
                "transform_id": "transform_001", 
                "status": "completed",
                "output_data": data,  # Echo for now
                "transformations_applied": []
            })
        
        elif operation == "validate":
            return APIResponse.success({
                "validation_id": "validation_001",
                "status": "completed",
                "is_valid": True,
                "errors": [],
                "warnings": []
            })
        
        return APIResponse.error(f"Unknown operation: {operation}")

class ModelContract(APIContract):
    """AI Model management contract"""
    
    @property
    def name(self) -> str:
        return "model"
    
    @property 
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Model request validation"""
        action = payload.get("action")
        return action in ["load", "unload", "predict", "train", "list"]
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Model response validation"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process model management request"""
        action = message.payload.get("action")
        model_id = message.payload.get("model_id")
        
        if action == "load":
            if not model_id:
                return APIResponse.error("Missing model_id")
            
            return APIResponse.success({
                "model_id": model_id,
                "status": "loaded",
                "model_info": {
                    "type": "unknown",
                    "version": "1.0",
                    "parameters": 0
                }
            })
        
        elif action == "unload":
            if not model_id:
                return APIResponse.error("Missing model_id")
            
            return APIResponse.success({
                "model_id": model_id,
                "status": "unloaded"
            })
        
        elif action == "predict":
            input_data = message.payload.get("input_data")
            if not input_data:
                return APIResponse.error("Missing input_data")
            
            return APIResponse.success({
                "prediction_id": "pred_001",
                "model_id": model_id,
                "predictions": [],  # Should be implemented by specific model
                "confidence": 0.0
            })
        
        elif action == "list":
            return APIResponse.success({
                "models": [],  # Should be implemented by model manager
                "total": 0
            })
        
        return APIResponse.error(f"Unknown action: {action}")

class CommunicationContract(APIContract):
    """Inter-agent communication contract"""
    
    @property
    def name(self) -> str:
        return "communication"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Communication request validation"""
        action = payload.get("action")
        return action in ["send", "broadcast", "subscribe", "unsubscribe"]
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Communication response validation"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process communication request"""
        action = message.payload.get("action")
        
        if action == "send":
            target = message.payload.get("target_agent")
            msg_data = message.payload.get("message")
            
            if not target or not msg_data:
                return APIResponse.error("Missing target_agent or message")
            
            return APIResponse.success({
                "message_id": "msg_001",
                "target_agent": target,
                "status": "sent",
                "delivery_status": "pending"
            })
        
        elif action == "broadcast":
            msg_data = message.payload.get("message")
            topic = message.payload.get("topic", "general")
            
            if not msg_data:
                return APIResponse.error("Missing message")
            
            return APIResponse.success({
                "broadcast_id": "broadcast_001",
                "topic": topic,
                "status": "sent",
                "recipients": 0
            })
        
        elif action == "subscribe":
            topic = message.payload.get("topic")
            if not topic:
                return APIResponse.error("Missing topic")
            
            return APIResponse.success({
                "topic": topic,
                "status": "subscribed",
                "subscription_id": "sub_001"
            })
        
        elif action == "unsubscribe":
            topic = message.payload.get("topic")
            if not topic:
                return APIResponse.error("Missing topic")
            
            return APIResponse.success({
                "topic": topic,
                "status": "unsubscribed"
            })
        
        return APIResponse.error(f"Unknown action: {action}")

class FileSystemContract(APIContract):
    """File system operations contract"""
    
    @property
    def name(self) -> str:
        return "filesystem"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """File system request validation"""
        action = payload.get("action")
        return action in ["read", "write", "list", "delete", "exists"]
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """File system response validation"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process file system request"""
        action = message.payload.get("action")
        path = message.payload.get("path")
        
        if not path:
            return APIResponse.error("Missing file path")
        
        if action == "read":
            return APIResponse.success({
                "path": path,
                "content": "",  # Should be implemented by file handler
                "size": 0,
                "last_modified": None
            })
        
        elif action == "write":
            content = message.payload.get("content", "")
            return APIResponse.success({
                "path": path,
                "bytes_written": len(content),
                "status": "written"
            })
        
        elif action == "list":
            return APIResponse.success({
                "path": path,
                "files": [],  # Should be implemented by file handler
                "directories": [],
                "total": 0
            })
        
        elif action == "delete":
            return APIResponse.success({
                "path": path,
                "status": "deleted"
            })
        
        elif action == "exists":
            return APIResponse.success({
                "path": path,
                "exists": False,  # Should be implemented by file handler
                "is_file": False,
                "is_directory": False
            })
        
        return APIResponse.error(f"Unknown action: {action}")

# Standard contract instances
STANDARD_CONTRACTS = {
    "health_check": HealthCheckContract(),
    "status": StatusContract(),
    "config": ConfigContract(),
    "data_processing": DataProcessingContract(),
    "model": ModelContract(),
    "communication": CommunicationContract(),
    "filesystem": FileSystemContract()
}

def get_standard_contract(name: str) -> APIContract:
    """Get a standard contract by name"""
    contract = STANDARD_CONTRACTS.get(name)
    if contract is None:
        raise ValueError(f"Standard contract not found: {name}")
    return contract

def list_standard_contracts() -> List[str]:
    """List all available standard contracts"""
    return list(STANDARD_CONTRACTS.keys())

def register_all_standard_contracts(processor):
    """Register all standard contracts with an API processor"""
    for name, contract in STANDARD_CONTRACTS.items():
        # Define default endpoints for each contract
        endpoints = [f"/{name}", f"/api/v1/{name}"]
        processor.register_contract(contract, endpoints)
        logger.info(f"Registered standard contract: {name}")
    
    logger.info(f"Registered {len(STANDARD_CONTRACTS)} standard contracts") 