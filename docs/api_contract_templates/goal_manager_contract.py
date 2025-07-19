
# Custom API Contract for goal_manager
from common.api.contract import APIContract, APIMessage, APIResponse, APIVersion, Status
from typing import Dict, Any

class GoalManagerContract(APIContract):
    """Custom API contract for goal_manager operations"""
    
    @property
    def name(self) -> str:
        return "goal_manager"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate goal_manager request"""
        # Add your validation logic here
        required_fields = ["action"]  # Customize as needed
        return all(field in payload for field in required_fields)
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate goal_manager response"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process goal_manager request"""
        action = message.payload.get("action")
        
        if action == "status":
            return APIResponse.success({
                "agent": "goal_manager",
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
def register_goal_manager_contract(processor):
    """Register goal_manager contract with API processor"""
    contract = GoalManagerContract()
    endpoints = ["/goal_manager", "/api/v1/goal_manager"]
    processor.register_contract(contract, endpoints)
