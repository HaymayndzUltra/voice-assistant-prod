# Minimal Viable System (MVS)

## Overview

This directory contains a self-contained implementation of the Minimal Viable System (MVS) - a stable core system with 9 essential agents and their direct dependencies. The MVS serves as a foundation for the larger AI system, ensuring that the core functionality works reliably before expanding to include more agents.

## Directory Structure

```
NEWMUSTFOLLOW/
├── agents/                  # Local copies of all agent files
│   ├── model_manager_agent.py
│   ├── coordinator_agent.py
│   ├── streaming_audio_capture.py
│   └── ...
├── cache/                   # Cache directory for agents
├── certificates/            # Security certificates
├── data/                    # Data files
├── logs/                    # Log files
├── models/                  # Model files
├── check_mvs_health.py      # Health check script
├── copy_agent_files.py      # Script to copy agent files
├── find_agent_files.py      # Script to find agent files in the repo
├── launch_mvs.py            # Basic launcher script
├── launch_mvs_improved.py   # Improved launcher with better error handling
├── launch_mvs_local.py      # Launcher using local agent files
├── minimal_system_config.yaml       # Original configuration
├── minimal_system_config_updated.yaml # Configuration with absolute paths
├── minimal_system_config_local.yaml # Configuration with local paths
├── mvs_installation.md      # Installation instructions
├── mvs_status_report.md     # Status report
├── mvs_summary.md           # System summary
├── mvs_troubleshooting.md   # Troubleshooting guide
├── PROJECT_CONTINUATION_GUIDE.md    # Plan for future development
└── README_MVS.md            # This file
```

## Core Agents

1. **ModelManagerAgent**: Manages model loading, unloading, and VRAM allocation
2. **CoordinatorAgent**: Coordinates communication between agents and manages system state
3. **SystemDigitalTwin**: Maintains a digital representation of the system state
4. **ChainOfThoughtAgent**: Implements chain-of-thought reasoning for complex tasks
5. **GOT_TOTAgent**: Graph of Thoughts implementation for reasoning
6. **SelfTrainingOrchestrator**: Manages the self-training process for agents
7. **TinyLlamaService**: Provides access to the TinyLlama model for lightweight inference
8. **LearningAdjusterAgent**: Adjusts learning parameters based on performance metrics
9. **MemoryOrchestrator**: Manages memory storage and retrieval

## Dependencies

1. **StreamingSpeechRecognition**: Provides real-time speech recognition
2. **StreamingInterruptHandler**: Handles interruptions in streaming processes
3. **FusedAudioPreprocessor**: Preprocesses audio for improved recognition quality
4. **AudioCapture**: Captures audio from input devices
5. **TaskRouter**: Routes tasks to appropriate agents based on capabilities
6. **StreamingTTSAgent**: Provides streaming text-to-speech capabilities
7. **StreamingAudioCapture**: Streams audio chunks in real-time with wake word detection

## Audio Processing Pipeline

The MVS includes an enhanced audio processing pipeline with the StreamingAudioCapture agent, which provides:

- **Wake Word Detection**: Uses Whisper model to detect wake words (e.g., "highminds")
- **Energy-Based Detection**: Fallback mechanism for activating based on audio energy levels
- **Real-time Streaming**: Low-latency audio streaming via ZMQ
- **Robust Error Handling**: Error propagation with rate limiting

This allows the system to intelligently activate only when needed, improving efficiency and user experience.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required Python packages (see installation instructions)
- ZeroMQ library

### Installation

See `mvs_installation.md` for detailed installation instructions.

### Running the MVS

1. **Check agent files**:

   ```bash
   ./launch_mvs_local.py --check-only
   ```

2. **Launch a single agent**:

   ```bash
   ./launch_mvs_local.py --agent ModelManagerAgent
   ```

3. **Launch all agents**:

   ```bash
   ./launch_mvs_local.py
   ```

4. **Check health status**:
   ```bash
   ./check_mvs_health.py
   ```

## Troubleshooting

See `mvs_troubleshooting.md` for common issues and their solutions.

## Development

### Adding a New Agent

1. Add the agent file to the `agents` directory
2. Update the configuration in `minimal_system_config_local.yaml`
3. Test the agent individually before integrating with the full system

### Modifying an Existing Agent

1. Make changes to the agent file in the `agents` directory
2. Test the agent individually
3. Test the agent with the full system

## Future Development

See `PROJECT_CONTINUATION_GUIDE.md` for the plan to expand beyond the MVS.

## Status

See `mvs_status_report.md` for the current status of the MVS implementation.

## Scripts

- **check_mvs_health.py**: Checks the health status of all MVS agents
- **copy_agent_files.py**: Copies agent files from the repository to the local directory
- **find_agent_files.py**: Helps locate agent files in the repository
- **launch_mvs.py**: Basic script to launch the MVS
- **launch_mvs_improved.py**: Enhanced launcher with better error handling
- **launch_mvs_local.py**: Launcher that uses local agent files

## Configuration Files

- **minimal_system_config.yaml**: Original configuration file
- **minimal_system_config_updated.yaml**: Configuration with absolute file paths
- **minimal_system_config_local.yaml**: Configuration with local file paths for the copied agents
