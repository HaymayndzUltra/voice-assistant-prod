# PC2 Non-GPU & System Services

This directory contains the non-GPU, system management, and data services designated to run on PC2. These services handle system health, task routing, monitoring, and other essential background processes.

## Services Overview

### 1. HealthMonitor
- **Purpose**: Monitors the health of all system agents and services, reports health status, performs parallel health checks, and manages agent lifecycle.
- **Main Port**: 5584
- **Health Check Port**: 5585
- **Dependencies (Internal)**: TaskRouter, ModelManagerAgent, EnhancedModelRouter, ConsolidatedTranslator
- **Dependencies (External)**: zmq, json, logging, threading, requests, subprocess
- **Key Features**:
  - Parallel health checks
  - Agent lifecycle management
  - Automatic recovery
  - Health status reporting
  - System metrics monitoring

### 2. Task_Router
- **Purpose**: Routes tasks to appropriate models and services, implements Circuit Breaker pattern for resilient connections.
- **Main Port**: 5571
- **Health Check Port**: 5572
- **Dependencies (Internal)**: HealthMonitor, ModelManagerAgent
- **Dependencies (External)**: zmq, json, logging, threading, msgpack
- **Key Features**:
  - Task routing
  - Circuit breaker implementation
  - Service communication management
  - Health check integration

### 3. ProactiveContextMonitor
- **Purpose**: Monitors and analyzes context for proactive actions, maintains context history, triggers proactive responses.
- **Main Port**: 5585
- **Health Check Port**: 5586
- **Dependencies (Internal)**: HealthMonitor
- **Dependencies (External)**: zmq, json, logging, threading
- **Key Features**:
  - Context monitoring
  - History maintenance
  - Proactive response triggering
  - Health check integration

### 4. RCAAgent
- **Purpose**: Analyzes log files for error patterns and provides proactive recommendations for system healing.
- **Main Port**: 5586
- **Health Check Port**: 5587
- **Dependencies (Internal)**: HealthMonitor, Self-Healing Agent (on PC2)
- **Dependencies (External)**: zmq, json, logging, threading, re
- **Key Features**:
  - Log file analysis
  - Error pattern detection
  - Proactive recommendations
  - Health status reporting

### 5. SystemDigitalTwin
- **Purpose**: Creates and maintains a digital representation of the system state and behavior.
- **Main Port**: 5587
- **Health Check Port**: 5588
- **Dependencies (Internal)**: HealthMonitor
- **Dependencies (External)**: zmq, json, logging, threading, psutil
- **Key Features**:
  - System state monitoring
  - Metrics collection
  - Health status reporting
  - Prometheus integration

### 6. UnifiedMonitoring
- **Purpose**: Provides unified system monitoring capabilities across all components.
- **Main Port**: 5614
- **Health Check Port**: 5615
- **Dependencies (Internal)**: BaseAgent
- **Dependencies (External)**: zmq, json, psutil, logging
- **Key Features**:
  - System metrics monitoring
  - Component status tracking
  - Resource usage monitoring
  - Health check integration

### 7. UnifiedUtilsAgent
- **Purpose**: Provides utility functions for system maintenance and cleanup.
- **Main Port**: 7015
- **Health Check Port**: 7016
- **Dependencies (Internal)**: BaseAgent
- **Dependencies (External)**: os, platform, shutil, logging, subprocess
- **Key Features**:
  - Temp file cleanup
  - Log file management
  - Cache management
  - Browser cache cleanup
  - System maintenance

### 8. UnifiedErrorAgent
- **Purpose**: Handles and manages system-wide error reporting and analysis.
- **Main Port**: 7041
- **Health Check Port**: 7042
- **Dependencies (Internal)**: BaseAgent
- **Dependencies (External)**: zmq, json, logging, threading
- **Key Features**:
  - Error tracking
  - Error analysis
  - Error reporting
  - Health check integration

### 9. AuthenticationAgent
- **Purpose**: Manages system authentication and authorization.
- **Main Port**: 7043
- **Health Check Port**: 7044
- **Dependencies (Internal)**: BaseAgent
- **Dependencies (External)**: zmq, json, logging, threading
- **Key Features**:
  - Authentication management
  - Authorization control
  - Security monitoring
  - Health check integration

## General Protocols & Standards

- **Communication**: All agents utilize ZMQ for robust, asynchronous inter-service communication.
- **Base Class**: All agents inherit from a common `BaseAgent` class, ensuring standardized functionality.
- **Health Checks**: All agents implement a health check endpoint, typically on `main_port + 1`, to allow for system-wide monitoring by the HealthMonitor.
- **Logging**: Standardized logging is implemented across all agents for effective monitoring and debugging. 