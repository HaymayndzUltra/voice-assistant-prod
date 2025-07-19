
# WP-06 API Standardization Integration for translation_service
# Add these imports and patterns to standardize your API

from common.api.contract import (
    get_api_processor, create_request, create_event,
    APIMessage, APIResponse, APIHeader, Status, Priority
)
from common.api.standard_contracts import register_all_standard_contracts

class TranslationServiceAPIIntegration:
    """API standardization for translation_service"""
    
    def __init__(self):
        self.api_processor = get_api_processor()
        register_all_standard_contracts(self.api_processor)
    
    def create_standard_response(self, data=None, error=None):
        """Create standardized API response"""
        if error:
            return APIResponse.error(error)
        return APIResponse.success(data)
    
    def send_standard_request(self, target_agent: str, endpoint: str, data: dict = None):
        """Send standardized API request"""
        message = create_request(
            source_agent="translation_service",
            target_agent=target_agent,
            endpoint=endpoint,
            data=data,
            priority=Priority.NORMAL
        )
        return message
    
    def broadcast_event(self, event_type: str, data: dict = None):
        """Broadcast standardized event"""
        message = create_event(
            source_agent="translation_service",
            event_type=event_type,
            data=data
        )
        return message
    
    async def process_api_message(self, message: APIMessage) -> APIMessage:
        """Process incoming API message with standardization"""
        return await self.api_processor.process_message(message)

# Example usage:
# api_integration = TranslationServiceAPIIntegration()
# response = api_integration.create_standard_response({"status": "ready"})
# request = api_integration.send_standard_request("target_agent", "/health_check")
