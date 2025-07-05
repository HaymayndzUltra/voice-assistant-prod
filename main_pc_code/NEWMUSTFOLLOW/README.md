# Minimal Viable System (MVS)

## Overview

This folder contains the configuration, scripts, and documentation for the Minimal Viable System (MVS) - a small, stable, and fully functional core system focused on the 9 healthy agents and their direct dependencies.

## Files and Their Purpose

| File | Description |
|------|-------------|
| `minimal_system_config.yaml` | Configuration file defining the MVS agents and their dependencies |
| `run_mvs.sh` | Shell script to set up the environment and launch the MVS |
| `start_mvs.py` | Python script with improved error handling for starting the MVS |
| `check_mvs_health.py` | Script to check the health status of all MVS agents |
| `mvs_summary.md` | Summary of the MVS components and architecture |
| `mvs_troubleshooting.md` | Guide for troubleshooting common issues |
| `mvs_installation.md` | Installation instructions for the MVS |
| `PROJECT_CONTINUATION_GUIDE.md` | Guide for continuing development in future sessions |
| `README.md` | This file - overview of the MVS folder |

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install zmq pyyaml psutil torch
   ```

2. **Run the MVS**:
   ```bash
   # Option 1: Using the shell script
   chmod +x run_mvs.sh
   ./run_mvs.sh
   
   # Option 2: Using the Python script (recommended)
   python start_mvs.py
   ```

3. **Check agent health**:
   ```bash
   python check_mvs_health.py
   ```

## MVS Components

The MVS consists of:
- 9 healthy core agents
- 6 direct dependencies required by the core agents

### Core Agents:
1. ModelManagerAgent
2. ChainOfThoughtAgent
3. GOT_TOTAgent
4. CoordinatorAgent
5. SystemDigitalTwin
6. TinyLlamaService
7. LearningAdjusterAgent
8. StreamingInterruptHandler
9. MemoryOrchestrator

See `mvs_summary.md` for detailed information about each agent.

## Documentation

- For installation instructions, see `mvs_installation.md`
- For troubleshooting help, see `mvs_troubleshooting.md`
- For project continuation plans, see `PROJECT_CONTINUATION_GUIDE.md`

## Next Steps

After successfully running the MVS:
1. Test each agent's functionality
2. Gradually add more agents to the system
3. Standardize health check responses
4. Improve error handling and logging

## Support

For questions or issues, refer to the troubleshooting guide or contact the development team. 