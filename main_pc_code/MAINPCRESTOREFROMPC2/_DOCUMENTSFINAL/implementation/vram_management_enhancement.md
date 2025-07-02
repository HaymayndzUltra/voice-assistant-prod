# VRAM Management Enhancement

## Overview

This implementation enhances VRAM management across both MainPC and PC2 GPUs by adding advanced features to the `VRAMOptimizerAgent` and `ModelManagerAgent`. These enhancements include predictive model loading, fine-tuned unloading, and VRAM pressure mitigation.

## Components Modified

1. **VRAMOptimizerAgent**
   - Implemented continuous VRAM monitoring for both MainPC and PC2
   - Added predictive model loading based on usage patterns and TaskRouter queue
   - Implemented fine-tuned model unloading strategies 
   - Added VRAM pressure monitoring with automatic mitigation

2. **ModelManagerAgent**
   - Added new ZMQ commands for VRAM management (LOAD_MODEL, UNLOAD_MODEL, GET_LOADED_MODELS_STATUS)
   - Implemented VRAM reporting to SystemDigitalTwin
   - Enhanced model loading with quantization level support

3. **SystemDigitalTwin**
   - Added VRAM metrics collection and storage
   - Added commands for reporting and retrieving VRAM metrics

## Configuration

VRAM optimization settings are configurable through the `startup_config.yaml` file:

```yaml
# VRAMOptimizerAgent Configuration
vram_thresholds:
  critical: 0.85      # 85% VRAM usage - triggers immediate unloading
  warning: 0.75       # 75% VRAM usage - triggers idle model unloading
  safe: 0.5           # 50% VRAM usage - considered safe

# VRAM budgets per device in MB
mainpc_vram_budget_mb: 20000  # 20GB for RTX 4090
pc2_vram_budget_mb: 10000     # 10GB for RTX 3060

# Idle timeouts and intervals
idle_timeout: 900             # Unload models after 15 minutes of inactivity
idle_check_interval: 60       # Check for idle models every minute

# Memory optimization
defragmentation_threshold: 0.7  # 70% fragmentation triggers defrag
optimization_interval: 300      # Run optimization every 5 minutes

# Predictive loading settings
predictive_loading_enabled: true
lookahead_window: 300           # 5 min lookahead for task prediction
prediction_window: 3600         # Track usage patterns for 1 hour
```

## VRAM Optimization Strategies

### 1. Predictive Model Loading

The VRAMOptimizerAgent uses two approaches for predictive model loading:

1. **TaskRouter Queue Analysis**
   - Examines the pending tasks in the TaskRouter queue
   - Maps task types to likely models that will be needed
   - Preloads models before they're explicitly requested

2. **Historical Usage Pattern Analysis**
   - Tracks model usage over time
   - Identifies patterns in model usage (frequency, time of day, etc.)
   - Predicts which models are likely to be needed soon

### 2. Fine-tuned Model Unloading

The agent implements intelligent model unloading strategies:

1. **Idle Model Detection**
   - Tracks last usage timestamp for each model
   - Unloads models that haven't been used for longer than the configured timeout
   - Prioritizes unloading from the less powerful GPU first

2. **Priority-based Unloading**
   - Assigns priority levels to models based on importance and usage frequency
   - When VRAM pressure occurs, unloads lower priority models first

### 3. VRAM Pressure Mitigation

The agent proactively monitors and manages VRAM pressure:

1. **Threshold-based Monitoring**
   - Continuously monitors VRAM usage on both GPUs
   - Uses configurable warning and critical thresholds

2. **Automatic Mitigation**
   - Warning level: Unloads idle models only
   - Critical level: Aggressively unloads even active models starting with largest memory footprint

3. **Memory Optimization**
   - Implements memory defragmentation when fragmentation exceeds threshold
   - Optimizes batch sizes based on available VRAM

## Communication Flow

1. VRAMOptimizerAgent regularly queries SystemDigitalTwin for VRAM metrics
2. ModelManagerAgent reports VRAM usage and loaded models to SystemDigitalTwin
3. VRAMOptimizerAgent analyzes metrics and sends commands to ModelManagerAgent to load/unload models as needed
4. All communication uses secure ZMQ and service discovery

## Security

All inter-agent communication is secured using CurveZMQ (elliptic curve cryptography):

1. Each agent socket is configured with secure ZMQ options
2. Authentication is handled via the `secure_zmq.py` module
3. ZMQ sockets include proper error handling and timeout settings

## Testing

A test script `test_vram_optimizer.py` is included to verify the VRAM optimization functionality:

```bash
# Run with default settings
python test_vram_optimizer.py

# Run with custom ports
python test_vram_optimizer.py --vra-port 5572 --mma-port 5570 --sdt-port 7120
```

The test script validates:
- Communication between VRAMOptimizerAgent and ModelManagerAgent
- VRAM monitoring capabilities
- Configuration update functionality
- Model tracking and reporting

## Future Enhancements

Potential future enhancements to consider:

1. Machine learning-based prediction of model usage patterns
2. Dynamic adjustment of thresholds based on system load
3. Integration with task priority to make more intelligent loading/unloading decisions
4. Enhanced memory optimization techniques (kernel fusion, model sharding, etc.)
5. Model quantization based on VRAM pressure
