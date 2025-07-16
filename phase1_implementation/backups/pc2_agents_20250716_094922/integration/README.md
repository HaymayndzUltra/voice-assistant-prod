# AI Voice Assistant Integration Layer

This integration layer provides system-wide performance optimization, caching, and intelligent response handling for the AI Voice Assistant. It consists of several complementary agents that work together to enhance system efficiency and user experience.

## Components

### 1. Performance Monitor (`performance_monitor.py`)
- **Purpose**: System-wide performance monitoring and metrics collection
- **Features**:
  - Tracks response times for all ZMQ calls
  - Calculates throughput metrics
  - Monitors error rates
  - Broadcasts metrics to subscribers
  - Uses PUB/SUB pattern for real-time monitoring
- **Ports**: 5614 (PUB)

### 2. Async Processor (`async_processor.py`)
- **Purpose**: Non-blocking task processing and background operations
- **Features**:
  - Implements PUSH/PULL pattern for fire-and-forget tasks
  - Handles logging, analysis, and memory tasks asynchronously
  - Background processing of non-critical operations
  - Prevents system blocking during long operations
- **Ports**: 5615 (PUSH), 5616 (PULL)

### 3. Cache Manager (`cache_manager.py`)
- **Purpose**: Intelligent caching of intermediate results
- **Features**:
  - Redis-based shared cache
  - Caches NLU results, model decisions, context summaries
  - Time-based cache invalidation
  - Reference-based caching for large objects
  - Automatic cleanup of expired entries
- **Redis**: localhost:6379 (default)

### 4. Data Optimizer (`data_optimizer.py`)
- **Purpose**: Optimizes data payloads for ZMQ communication
- **Features**:
  - Multiple serialization methods (JSON, MessagePack)
  - Compression support
  - Reference-based optimization
  - Size monitoring and compression ratios
  - Automatic payload optimization

### 5. Predictive Loader (`predictive_loader.py`)
- **Purpose**: Pre-loading resources based on context
- **Features**:
  - Context-aware pre-loading
  - Automatic model warming
  - Background information fetching
  - Confidence-based triggering
  - Manual pre-loading support
- **Ports**: 5617 (PULL), 5618 (PUSH)

### 6. Tiered Responder (`tiered_responder.py`)
- **Purpose**: Intelligent response tiering based on query type
- **Features**:
  - Three-tier response system:
    - Instant (100ms): Simple greetings and common phrases
    - Fast (1s): General knowledge questions
    - Deep (5s): Complex analysis and planning
  - Thinking message support for deep queries
  - Pattern-based query classification
  - Canned responses for instant queries
- **Ports**: 5619 (PULL), 5620 (PUSH)

## Integration Flow

1. **Performance Monitoring**:
   - All ZMQ calls are monitored
   - Metrics are broadcast to subscribers
   - Bottlenecks are identified

2. **Async Processing**:
   - Non-critical tasks are offloaded
   - Background processing prevents blocking
   - Logging and analysis happen in parallel

3. **Caching**:
   - NLU results are cached
   - Model decisions are cached
   - Context summaries are cached
   - Reduces redundant processing

4. **Data Optimization**:
   - Large payloads are optimized
   - References replace large objects
   - Compression is applied where needed
   - Network overhead is minimized

5. **Predictive Loading**:
   - Context is monitored
   - Resources are pre-loaded
   - Models are warmed up
   - Information is pre-fetched

6. **Tiered Response**:
   - Queries are classified
   - Appropriate tier is selected
   - Response time is optimized
   - User experience is maintained

## Usage Examples

### Performance Monitoring
```python
from integration.performance_monitor import PerformanceMonitor

# Start the monitor
monitor = PerformanceMonitor()
monitor.run()

# Log a metric
monitor.log_metric(
    agent_name="my_agent",
    operation="process_request",
    duration=0.123,
    success=True
)
```

### Async Processing
```python
from integration.async_processor import AsyncProcessor, async_task

# Start the processor
processor = AsyncProcessor()
processor.run()

# Use async decorator
@async_task("logging")
def log_data(data):
    # Your logging code here
    pass
```

### Caching
```python
from integration.cache_manager import CacheManager

# Initialize cache
cache = CacheManager()

# Cache NLU results
cache.cache_nlu_result(
    user_input="Sino ang presidente ng Pilipinas?",
    intent="ask_person_role",
    entities={"role": "presidente", "country": "Pilipinas"}
)
```

### Data Optimization
```python
from integration.data_optimizer import optimize_zmq_message

# Optimize a message
message = {
    'session_id': '1234567890',
    'conversation_history': [
        {'user': 'Hello', 'assistant': 'Hi there!'} for _ in range(1000)
    ]
}

optimized = optimize_zmq_message(message)
```

### Predictive Loading
```python
from integration.predictive_loader import PredictiveLoader

# Initialize loader
loader = PredictiveLoader()

# Start the loader
loader.run()

# Pre-load resources
loader.preload_topic('coding')
```

### Tiered Response
```python
from integration.tiered_responder import TieredResponder

# Initialize responder
responder = TieredResponder()

# Start the responder
responder.run()

# Send a query
query = {
    'text': 'Hello',
    'session_id': '12345'
}
```

## System Requirements
- Python 3.8+
- Redis server (for caching)
- ZMQ (for inter-process communication)
- MessagePack (for optimized serialization)

## Configuration
All components use default ports but can be configured via environment variables:
- PERFORMANCE_PUB_PORT=5614
- ASYNC_PULL_PORT=5615
- ASYNC_PUSH_PORT=5616
- CACHE_REDIS_PORT=6379
- PREDICTIVE_PULL_PORT=5617
- PREDICTIVE_PUSH_PORT=5618
- TIERED_PULL_PORT=5619
- TIERED_PUSH_PORT=5620

## Monitoring
All components log to both console and files:
- logs/performance_metrics.log
- logs/async_processor.log
- logs/cache_manager.log
- logs/data_optimizer.log
- logs/predictive_loader.log
- logs/tiered_responder.log

## Best Practices
1. Use async processing for non-critical tasks
2. Cache intermediate results
3. Optimize large data payloads
4. Pre-load resources based on context
5. Use tiered responses for better UX
6. Monitor system performance

## Contributing
To add new features or modify existing ones, follow these steps:
1. Update the relevant component
2. Add appropriate logging
3. Update the README
4. Test thoroughly
5. Submit for review

## License
MIT License - feel free to modify and use as needed
