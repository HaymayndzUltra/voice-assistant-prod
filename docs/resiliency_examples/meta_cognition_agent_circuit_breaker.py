
# WP-07 Circuit Breaker Integration for MetaCognitionAgent
# Add circuit breaker protection for external calls

from common.resiliency.circuit_breaker import (
    get_circuit_breaker, CircuitBreakerConfig, circuit_breaker
)

class MetacognitionagentCircuitBreakers:
    """Circuit breaker management for MetaCognitionAgent"""
    
    def __init__(self):
        # Configure circuit breakers for different services
        self.api_breaker = get_circuit_breaker(
            "MetaCognitionAgent_api",
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout_duration=60.0,
                request_timeout=30.0
            )
        )
        
        self.db_breaker = get_circuit_breaker(
            "MetaCognitionAgent_database",
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_duration=30.0,
                request_timeout=10.0
            )
        )
    
    async def make_api_call(self, endpoint, data=None):
        """Make API call with circuit breaker protection"""
        async def api_call():
            # Your original API call code here
            response = await some_api_client.post(endpoint, json=data)
            return response.json()
        
        return await self.api_breaker.call_async(api_call)
    
    async def query_database(self, query, params=None):
        """Query database with circuit breaker protection"""
        def db_query():
            # Your original database query code here
            with database.connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        
        return await self.db_breaker.call_async(db_query)

# Using decorators for automatic protection
@circuit_breaker(name="MetaCognitionAgent_external_service")
async def call_external_service(data):
    """External service call with automatic circuit breaker"""
    # Your external service call here
    return await external_service.process(data)

# Example usage:
# breakers = MetacognitionagentCircuitBreakers()
# result = await breakers.make_api_call("/process", {"data": "example"})
# status = breakers.api_breaker.get_metrics()
