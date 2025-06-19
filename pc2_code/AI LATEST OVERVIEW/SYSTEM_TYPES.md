# Voice Assistant System Types

## Overview of Available System Architectures

Your voice assistant project has two main system architectures that can be used depending on your needs:

### 1. Modular Streaming System (Primary)
- **Location**: `modular_system/` directory
- **Launch Script**: `run_all_streaming.py`
- **Architecture**: Pipeline-based streaming components with real-time processing
- **Main Features**:
  - Low-latency streaming pipeline
  - Real-time partial transcription
  - Interrupt detection and handling
  - Optimized for conversational flow
- **When to Use**: For day-to-day voice assistant usage with focus on responsiveness and natural conversation

### 2. Distributed Agent System (Advanced)
- **Location**: `agents/` directory
- **Launch Scripts**: `run_all_agents.py` or `distributed_launcher.py`
- **Architecture**: Multi-agent system with specialized AI capabilities distributed across machines
- **Main Features**:
  - Advanced code generation and execution
  - Memory and learning capabilities
  - Multiple machine distribution
  - Enhanced model routing with chain-of-thought
- **When to Use**: For advanced tasks requiring specialized agents like code generation, web scraping, etc.

## Using Both Systems Together

The two systems can work together, with the Modular Streaming System handling the conversational interface and the Distributed Agent System providing specialized capabilities. This integration enables:

1. **Front-end / Back-end Split**: Streaming system handles user interaction while agent system processes complex tasks
2. **Specialized Task Handling**: Voice commands captured by streaming system can trigger distributed agents for advanced processing
3. **Mixed Architecture**: Use streaming for time-sensitive tasks and agents for compute-intensive operations

## Current Documentation Status

Each system has its own complete documentation:

1. **Modular Streaming System**: 
   - FULL_SYSTEM_OVERVIEW.txt (Current implementation)
   - ROUTING.md (Streaming pipeline routing)
   - WORKFLOW.md (Streaming component workflow)

2. **Distributed Agent System**:
   - DISTRIBUTED_AGENTS.md (Soon to be created)

## System Switching

To switch between systems:

```
# Run the Modular Streaming System
cd modular_system
python run_all_streaming.py

# Run the Distributed Agent System
cd agents
python run_all_agents.py  # For single machine
python distributed_launcher.py  # For multi-machine
```
