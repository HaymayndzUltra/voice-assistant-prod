# Distributed AI System Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [MainPC Services](#mainpc-services)
4. [PC2 Services](#pc2-services)
5. [Network Configuration](#network-configuration)
6. [Resource Allocation](#resource-allocation)
7. [Health Monitoring](#health-monitoring)
8. [Communication Patterns](#communication-patterns)
9. [Data Persistence](#data-persistence)

## System Overview

The Distributed AI Voice Assistant System is a sophisticated multi-agent architecture that operates across two physical machines (MainPC and PC2) to provide advanced voice interaction capabilities. The system follows a microservices architecture with specialized agents handling specific tasks, all coordinated through centralized management services.

### Key Architectural Principles
1. **Distributed Processing**: Workloads are distributed across MainPC and PC2 based on computational requirements
2. **Centralized Model Management**: All AI models are managed by the ModelManagerSuite on MainPC
3. **Service Discovery**: ServiceRegistry provides dynamic service discovery and health monitoring
4. **Fault Tolerance**: Multiple layers of redundancy and failover mechanisms
5. **Resource Optimization**: Intelligent resource allocation with VRAM optimization and model quantization

### System Components
- **MainPC**: Central orchestrator with core services, model management, and primary processing
- **PC2**: Specialized services for memory, reasoning, translation, and auxiliary processing

## Architecture Diagram

```
┌─────────────────────────── MAINPC ───────────────────────────┐
│                                                               │
│  ┌─────────────────┐    ┌──────────────────┐                │
│  │ ServiceRegistry │◄───┤SystemDigitalTwin  │                │
│  │   (Port 7200)   │    │  (Port 7220)     │                │
│  └────────┬────────┘    └────────┬──────────┘                │
│           │                      │                            │
│  ┌────────▼────────────────────▼─────────┐                  │
│  │      RequestCoordinator (26002)        │                  │
│  └────────┬───────────────────────────────┘                  │
│           │                                                   │
│  ┌────────▼────────┐    ┌─────────────────┐                 │
│  │ModelManagerSuite│    │ObservabilityHub │                 │
│  │   (Port 7211)   │    │  (Port 9000)    │                 │
│  └─────────────────┘    └─────────────────┘                 │
│                                                               │
│  [Core Services] [Memory] [Utilities] [GPU] [Reasoning]      │
│  [Vision] [Learning] [Language] [Speech] [Audio] [Emotion]   │
└───────────────────────────────────────────────────────────────┘
                              │
                    Network Bridge (172.20.0.0/16)
                              │
┌─────────────────────────── PC2 ──────────────────────────────┐
│                                                               │
│  ┌──────────────────────────┐    ┌─────────────────┐        │
│  │MemoryOrchestratorService │    │ObservabilityHub │        │
│  │      (Port 7140)         │    │  (Port 9000)    │        │
│  └────────────┬─────────────┘    └─────────────────┘        │
│               │                                               │
│  ┌────────────▼──────────┐    ┌──────────────────┐          │
│  │   TieredResponder     │    │  AsyncProcessor   │          │
│  │    (Port 7100)        │    │   (Port 7101)     │          │
│  └───────────────────────┘    └──────────────────┘          │
│                                                               │
│  [Integration Layer] [Core Agents] [ForPC2] [Utilities]      │
└───────────────────────────────────────────────────────────────┘
```

## Communication Patterns

### 1. Service Discovery Pattern
- All agents register with ServiceRegistry on startup
- ServiceRegistry maintains active service catalog
- Agents query ServiceRegistry for service endpoints
- Health checks validate service availability

### 2. Request Coordination Pattern
- RequestCoordinator receives all incoming requests
- Routes requests to appropriate agents based on capability
- Manages request lifecycle and response aggregation
- Handles failover and retry logic

### 3. Model Management Pattern
- ModelManagerSuite centralizes all AI model operations
- Agents request model inference through model_client
- VRAM optimization and model loading/unloading
- Quantization and KV-cache management

### 4. Cross-Machine Communication
- ZMQ sockets for high-performance messaging
- Redis for shared state and caching
- Health monitoring across machine boundaries
- Automatic failover for critical services