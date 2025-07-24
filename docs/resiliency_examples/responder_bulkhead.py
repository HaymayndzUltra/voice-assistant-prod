
# WP-07 Bulkhead Integration for responder
# Add resource isolation to prevent cascading failures

from common.resiliency.bulkhead import (
    get_bulkhead, BulkheadConfig, IsolationStrategy, bulkhead
)

class ResponderBulkheads:
    """Bulkhead isolation for responder"""
    
    def __init__(self):
        # Critical operations bulkhead
        self.critical_bulkhead = get_bulkhead(
            "responder_critical",
            max_concurrent=5,
            timeout=60.0,
            isolation_strategy=IsolationStrategy.SEMAPHORE
        )
        
        # Background tasks bulkhead
        self.background_bulkhead = get_bulkhead(
            "responder_background",
            max_concurrent=20,
            max_queue_size=100,
            timeout=30.0,
            isolation_strategy=IsolationStrategy.THREAD_POOL
        )
        
        # External API bulkhead
        self.api_bulkhead = get_bulkhead(
            "responder_api",
            max_concurrent=10,
            timeout=45.0,
            isolation_strategy=IsolationStrategy.ASYNC_SEMAPHORE
        )
    
    async def critical_processing(self, data):
        """Critical processing with resource isolation"""
        async def process():
            # Your critical processing logic here
            result = await process_important_data(data)
            return result
        
        return await self.critical_bulkhead.execute_async(process)
    
    async def background_task(self, task_data):
        """Background task with isolation"""
        def task():
            # Your background task logic here
            return perform_background_work(task_data)
        
        return await self.background_bulkhead.execute_async(task)
    
    async def api_call(self, endpoint, data):
        """API call with isolation"""
        async def call():
            response = await api_client.post(endpoint, json=data)
            return response.json()
        
        return await self.api_bulkhead.execute_async(call)

# Using decorators for automatic isolation
@bulkhead(
    name="responder_heavy_computation",
    max_concurrent=3,
    timeout=120.0,
    isolation_strategy=IsolationStrategy.THREAD_POOL
)
async def heavy_computation(data):
    """Heavy computation with automatic isolation"""
    return await compute_intensive_operation(data)

@bulkhead(
    name="responder_external_calls",
    max_concurrent=15,
    timeout=30.0
)
async def external_service_call(service_url, payload):
    """External service call with isolation"""
    return await external_service.request(service_url, payload)

# Example usage:
# bulkheads = ResponderBulkheads()
# result = await bulkheads.critical_processing(important_data)
# metrics = bulkheads.critical_bulkhead.get_metrics()
