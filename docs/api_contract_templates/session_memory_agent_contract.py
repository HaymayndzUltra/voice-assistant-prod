
# Custom API Contract for session_memory_agent
from common.api.contract import APIContract, APIMessage, APIResponse, APIVersion, Status
from typing import Dict, Any

class SessionMemoryAgentContract(APIContract):
    """Custom API contract for session_memory_agent operations"""
    
    @property
    def name(self) -> str:
        return "session_memory_agent"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate session_memory_agent request"""
        # Add your validation logic here
        required_fields = ["action"]  # Customize as needed
        return all(field in payload for field in required_fields)
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate session_memory_agent response"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process session_memory_agent request"""
        action = message.payload.get("action")
        
        if action == "status":
            return APIResponse.success({
                "agent": "session_memory_agent",
                "status": "active",
                "capabilities": []  # Add your capabilities
            })
        
        elif action == "process":
            # Add your processing logic here
            data = message.payload.get("data")
            return APIResponse.success({
                "processed": True,
                "result": data  # Replace with actual processing
            })
        
        return APIResponse.error(f"Unknown action: {action}")

# Register the contract
def register_session_memory_agent_contract(processor):
    """Register session_memory_agent contract with API processor"""
    contract = SessionMemoryAgentContract()
    endpoints = ["/session_memory_agent", "/api/v1/session_memory_agent"]
    processor.register_contract(contract, endpoints)
