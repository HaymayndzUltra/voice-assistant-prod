# Distributed Agent System Architecture

*Last Updated: 2025-05-24*

## 1. System Overview

The Distributed Agent system represents an advanced multi-agent architecture that operates across multiple machines for complex AI processing tasks. This system is fully integrated with the Modular Streaming System to provide a complete voice assistant solution. The agents work together to handle sophisticated tasks like code generation, memory management, and advanced reasoning. The system has been recently restructured with development/execution agents relocated from PC2 to the Main PC, and the new Human Awareness Agent implemented on the Main PC.

## 2. Agent Inventory & Capabilities

### Main PC (192.168.1.27) - Ryzen 9 7900, RTX 4090, 32GB RAM

#### Core System Agents

| Agent Name | Port | Key Features & Logic |
|------------|------|----------------------|
| Orchestrator | 5600 | Central controller for all agents, Health monitoring, Agent discovery |
| Listener | 5555 | Audio capture with VAD, Wake word detection, Adaptive silence detection |
| Face Recognition | 5560 | InsightFace-based recognition, Multi-user tracking, Emotion detection |
| TTS / Bark TTS | 5562 | Multi-tier speech synthesis, Voice customization, Audio caching |
| Human Awareness Agent | - | Monitors user environment, windows, tone, and physical poses for proactive assistance, Consists of Window Watcher, Tone Detector, Media Pose Detector, TagaBERTa Analyzer, and Reactive Prompt Agent components |

#### Task Processing Agents

| Agent Name | Port | Key Features & Logic |
|------------|------|----------------------|
| Interpreter | - | Intent/entity extraction, Context-aware understanding |
| Responder | - | Response generation, Conversation context maintenance |
| Remote Connector | 5557 | Secure PC1-PC2 communication, Auto-reconnect, Heartbeat monitoring |
| Task Router | 5558 | Task-based routing, Load balancing, Fallback logic |

### PC2 (192.168.1.2) - RTX 3060

#### DISTRIBUTED AGENTS ARCHITECTURE

### 2025-05-24: Voice Pipeline Validation
- XTTS Agent (tetey.wav) and translation adapter are now validated in production.
- Distributed agent integration (ZMQ Bridge, Human Awareness, etc.) can proceed.

### 2025-05-24 19:49: Distributed ZMQ Bridge Test
- ZMQ Bridge (port 5600) validated with successful cross-machine and loopback tests.
- Distributed agent integration is now production-ready.

### 2025-05-24 19:50: Next Phase Initiated
- PHI-3 translation agent (PC2) retained and enhanced for Tagalog/Taglish; NLLB migration cancelled.
- TagaBERTa integration for Human Awareness Agent (Main PC) started.
- Security/Audit Agent implementation in progress.
- Ready for advanced distributed workflows.

#### Advanced AI Agents

| Agent Name | Port | Key Features & Logic |
|------------|------|----------------------|
| Model Manager | 5556 | **DEPRECATED on PC2** - Functionality centralized to Main PC MMA. (Formerly: Dynamic model loading/unloading, VRAM optimization, Model selection) |
| Enhanced Model Router | 5601 | Advanced routing with context awareness, Chain-of-thought integration |
| Chain of Thought | 5612 | Multi-step reasoning for complex tasks |

#### Code Generation & Execution

| Agent Name | Port | Location | Key Features & Logic |
|------------|------|----------|----------------------|
| Code Generator | 6000 | Main PC | Code generation from natural language, Multi-model voting |
| Progressive Code Generator | 6002 | Main PC | Iterative code improvement, Complex software design |
| Auto-Fixer | 6003 | Main PC | Automated code repair, Error pattern recognition |
| Executor | 6001 | Main PC | Safe code execution, Test running, Result validation |
| Test Generator | 6004 | Main PC | Auto test creation, Sandbox validation, Test-driven fixes |

#### Knowledge & Memory

| Agent Name | Port | Key Features & Logic |
|------------|------|----------------------|
| Contextual Memory Agent | 5596 | Advanced context management, Long-term memory storage, Intelligent summarization, Token optimization, Code domain detection, User preferences, Previous interactions |
| Digital Twin | 5597 | User modeling, Personalized responses |
| Jarvis Memory | 5598 | Personal assistant context awareness |
| Learning Mode | 5599 | Adaptation to user patterns, System improvement |

**Note**: The Context Summarizer Agent has been consolidated into the Contextual Memory Agent, which now provides both context management and advanced summarization functions in a single integrated service.

#### Support Agents

| Agent Name | Port | Location | Key Features & Logic |
|------------|------|----------|----------------------|
| Enhanced Web Scraper | 5602 | PC2 | Advanced web scraping, Content extraction |
| Filesystem Assistant | 5594 | PC2 | File operations, Directory management |
| Self-Healing | 5601 | PC2 | System repair, Crash recovery |
| NLLB Translation Adapter | 5581 | PC2 | Filipino-English translation using NLLB (No Language Left Behind) model, Replaced Phi-3 for improved accuracy, **Taglish detection and Filipino/English ratio logging before translation** |
| Translator Agent | 5563/5561/5559 | PC2 | **Enhanced**: Advanced translation with dual socket architecture: REP socket (5563) for direct communication with Main PC, SUB socket (5561) for PUB-SUB interactions, and health check endpoint (5559). Implements tiered fallback translation system. |

## 3. Communication & Routing

### Message Flow Patterns

#### Voice Command Processing Flow (Integrated Voice Pipeline)
```
# Modular Streaming System (Voice Pipeline)
User → streaming_audio_capture (→5570) → streaming_speech_recognition (5570→5571) 
  → streaming_partial_transcripts (5571→5575) → streaming_interrupt_handler (5575→5576)
  → streaming_language_analyzer (5571→5572) → fixed_streaming_translation (5572→5573)
  → streaming_text_processor (5573→5574) → tts_connector (5574→5562)

# Integration Point with Distributed Agent System
streaming_text_processor → Orchestrator (5600) → [Distributed Agents] → TTS (5562) → User

# Translation Integration
fixed_streaming_translation → Translator Agent on PC2 (REP socket: 5563) → Tiered translation with fallbacks:
  → Primary: Google Translate API
  → Fallback 1: NLLB Translation Adapter (5581)
  → Fallback 2: Pattern matching dictionary
  → back to fixed_streaming_translation

# Human Awareness Integration
Human Awareness Agent (watcher.py, tone_detector.py, event_trigger.py) → Orchestrator (5600) → [Response Generation]
```
> **NOTE:** All translation components use the Taglish detection utility for consistent bilingual processing and logging. The streaming components are optimized for low latency and can be interrupted mid-response.

#### Advanced Code Generation Flow
```
# PC2 to Main PC Flow
Orchestrator (5600) → Remote Connector (5557) → Task Router (5558)
  → Enhanced Model Router (5601) → Chain of Thought (5612)
  → Code Generator (6000) on Main PC
  → Executor (6001) on Main PC for testing
  → [If errors: Auto-Fixer (6003) → Progressive Generator (6002) on Main PC]
  → Remote Connector → Orchestrator → Responder → User

# Human Awareness Integration
Human Awareness Agent → Orchestrator (5600) → [Appropriate workflow based on detected context]
```

### Cross-Machine Communication

1. **Direct Communication**: Agent-to-agent connections across machines
   ```
   Main PC Agent → PC2 Agent (direct ZMQ connection)
   ```

2. **Orchestrated Routing**: Centralized control through Orchestrator
   ```
   Main PC Agent → Orchestrator → Remote Connector → PC2 Agent
   ```

## 4. Distributed System Features

### Machine Discovery & Management
- Automatic discovery of available machines
- Dynamic agent allocation based on resource availability
- Health monitoring across all machines
- Graceful handling of machine disconnection

### Cross-Machine Resource Optimization
- Load balancing of compute-intensive tasks
- Model sharing between machines
- Memory optimization for AI models
- Automatic failover to backup machines

### Security Features
- Encrypted communication between machines
- Authentication for machine discovery
- Privilege separation between agents
- Secure code execution sandboxing

## 5. Running the Distributed System

### Launching the Modular Streaming System (Primary Method)
```
cd modular_system
python run_all_streaming.py
```

### Launching the Distributed Agent System
```
# On Main PC
cd agents
python distributed_launcher.py

# On PC2
cd pc2_package
python distributed_launcher.py --machine pc2
```

### Configuration
The system uses `config/distributed_config.json` to determine:
- Which agents run on which machines
- Port assignments for all agents
- Network configuration and security settings
- System resources and limitations
