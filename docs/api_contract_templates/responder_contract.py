
# Custom API Contract for responder
from common.api.contract import APIContract, APIMessage, APIResponse, APIVersion, Status
from typing import Dict, Any

class ResponderContract(APIContract):
    """Custom API contract for responder operations"""
    
    @property
    def name(self) -> str:
        return "responder"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate responder request"""
        # Add your validation logic here
        required_fields = ["action"]  # Customize as needed
        return all(field in payload for field in required_fields)
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate responder response"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process responder request"""
        action = message.payload.get("action")
        
        if action == "status":
            return APIResponse.success({
                "agent": "responder",
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
def register_responder_contract(processor):
    """Register responder contract with API processor"""
    contract = ResponderContract()
    endpoints = ["/responder", "/api/v1/responder"]
    processor.register_contract(contract, endpoints)
