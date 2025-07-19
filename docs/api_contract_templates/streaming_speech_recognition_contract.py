
# Custom API Contract for streaming_speech_recognition
from common.api.contract import APIContract, APIMessage, APIResponse, APIVersion, Status
from typing import Dict, Any

class StreamingSpeechRecognitionContract(APIContract):
    """Custom API contract for streaming_speech_recognition operations"""
    
    @property
    def name(self) -> str:
        return "streaming_speech_recognition"
    
    @property
    def version(self) -> APIVersion:
        return APIVersion.V1
    
    def validate_request(self, payload: Dict[str, Any]) -> bool:
        """Validate streaming_speech_recognition request"""
        # Add your validation logic here
        required_fields = ["action"]  # Customize as needed
        return all(field in payload for field in required_fields)
    
    def validate_response(self, payload: Dict[str, Any]) -> bool:
        """Validate streaming_speech_recognition response"""
        return "status" in payload
    
    async def process_request(self, message: APIMessage) -> APIResponse:
        """Process streaming_speech_recognition request"""
        action = message.payload.get("action")
        
        if action == "status":
            return APIResponse.success({
                "agent": "streaming_speech_recognition",
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
def register_streaming_speech_recognition_contract(processor):
    """Register streaming_speech_recognition contract with API processor"""
    contract = StreamingSpeechRecognitionContract()
    endpoints = ["/streaming_speech_recognition", "/api/v1/streaming_speech_recognition"]
    processor.register_contract(contract, endpoints)
