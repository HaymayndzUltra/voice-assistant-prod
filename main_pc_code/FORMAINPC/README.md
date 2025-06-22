# Voice Assistant PC2 Core Services

This directory contains the core services for PC2 that will be moved to the Main PC. These services handle advanced language processing, learning, and cognitive functions.

## Services Overview

### 1. Enhanced Model Router (EMR)
- **Purpose**: Master EMR for model routing
- **Port**: 5598
- **Features**:
  - Model selection and routing
  - Load balancing
  - Error handling
  - Performance monitoring

### 2. TinyLlama Service Enhanced
- **Purpose**: Enhanced language model service
- **Port**: 5615
- **Model**: TinyLlama-1.1B-Chat-v1.0
- **Features**:
  - Chat model optimized for PC2
  - ZMQ service interface
  - Auto device selection
  - Memory management

### 3. NLLB Adapter
- **Purpose**: Neural machine translation service
- **Port**: 5581
- **Model**: facebook/nllb-200-1.3B
- **Features**:
  - Multi-language translation
  - Confidence scoring
  - Error handling
  - Resource management

### 4. Learning Adjuster Agent
- **Purpose**: Learning rate and parameter adjustment
- **Port**: 5643
- **Features**:
  - Dynamic learning rate adjustment
  - Batch size optimization
  - Performance monitoring
  - Error recovery

### 5. Local Fine Tuner Agent
- **Purpose**: Local model fine-tuning
- **Port**: 5645
- **Features**:
  - Model parameter adjustment
  - Training management
  - Performance tracking
  - Resource optimization

### 6. Self Training Orchestrator
- **Purpose**: Self-training and reinforcement
- **Port**: 5644
- **Features**:
  - Training pipeline management
  - Progress tracking
  - Resource allocation
  - Quality assurance

### 7. Chain of Thought Agent
- **Purpose**: Advanced reasoning and problem-solving
- **Port**: 5646
- **Dependencies**:
  - Remote Connector Agent (port 5557)
  - LLM services
- **Features**:
  - Step-by-step reasoning
  - Context preservation
  - Error handling
  - Solution refinement

### 8. G.O.T. / T.O.T. Agent
- **Purpose**: Goal-Oriented Thinking / Tree of Thoughts
- **Port**: 5646
- **Features**:
  - Goal planning
  - Thought branching
  - Decision trees
  - Outcome prediction

### 9. Cognitive Model Agent
- **Purpose**: Advanced cognitive processing
- **Port**: 5641
- **Features**:
  - Reasoning capabilities
  - Context inference
  - Pattern recognition
  - Decision making

### 10. Consolidated Translator
- **Purpose**: Multi-engine translation service
- **Port**: 5563
- **Dependencies**:
  - NLLB Adapter (port 5581)
  - Phi LLM Service (port 11434)
  - Google Translate via RCA (port 5557)
- **Features**:
  - Multi-engine translation pipeline
  - Advanced caching
  - Session management
  - Comprehensive error handling
  - Translation quality metrics

## Configuration Requirements

### System Configuration
- Update `system_config.py` with Main PC IPs:
  ```python
  "main_pc_ip": "192.168.100.16",
  "pc2_ip": "192.168.100.17"
  ```

### Service Ports
- **Enhanced Model Router**: 5598
- **TinyLlama Service**: 5615
- **NLLB Adapter**: 5581
- **Learning Adjuster**: 5643
- **Local Fine Tuner**: 5645
- **Self Training Orchestrator**: 5644
- **Chain of Thought**: 5646
- **G.O.T. / T.O.T.**: 5646
- **Cognitive Model**: 5641
- **Consolidated Translator**: 5563
- **Phi LLM**: 11434
- **Remote Connector**: 5557

## Dependencies

### Required Python Packages
- `zmq` - For service communication
- `langdetect` - For language detection
- `nltk` - For text processing
- `numpy` - For numerical operations
- `torch` - For model operations

### Required Services
1. NLLB Adapter Service (port 5581)
2. Phi LLM Service (port 11434)
3. Remote Connector Agent (port 5557)
4. System Config Service

## Integration Steps

1. Update `system_config.py` with Main PC settings
2. Verify all required ports are available
3. Ensure all dependencies are installed
4. Update service configurations
5. Test each service individually
6. Verify inter-service communication

## Service Startup Sequence

1. Remote Connector Agent (port 5557)
2. NLLB Adapter (port 5581)
3. Phi LLM Service (port 11434)
4. TinyLlama Service (port 5615)
5. Cognitive Model Agent (port 5641)
6. Learning Adjuster Agent (port 5643)
7. Local Fine Tuner Agent (port 5645)
8. Self Training Orchestrator (port 5644)
9. Chain of Thought Agent (port 5646)
10. G.O.T. / T.O.T. Agent (port 5646)
11. Enhanced Model Router (port 5598)
12. Consolidated Translator (port 5563)

## Health Check Protocol

All services support health check via ZMQ:
```python
{
    "action": "health_check"
}
```

## Error Handling

Each service implements:
- Connection error recovery
- Rate limiting
- Timeout handling
- Resource monitoring
- Error logging

## Logging

Logs are stored in:
- `logs/consolidated_translator.log`
- `logs/tinyllama_service.log`
- `logs/learning_adjuster.log`
- `logs/cognitive_model.log`

## Resource Requirements

### Memory
- TinyLlama: ~2.8GB VRAM
- Phi LLM: ~2.0GB VRAM
- NLLB: ~2.4GB VRAM
- Other services: ~1GB RAM each

### CPU
- Multi-core CPU recommended
- At least 8GB system RAM
- SSD storage for models

## Security Considerations

- All services bind to `0.0.0.0`
- Firewall rules needed for ports
- Environment variable overrides
- Secure configuration management
