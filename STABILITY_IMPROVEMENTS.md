# AI System Stability Improvements

This document outlines the stability improvements made to the AI System to address systemic instability issues.

## Key Components

### 1. Centralized Path Management (`main_pc_code/utils/path_manager.py`)

A utility class that provides consistent path resolution across the codebase:

```python
from main_pc_code.utils.path_manager import PathManager

# Get project root
project_root = PathManager.get_project_root()

# Resolve a path relative to project root
config_path = PathManager.resolve_path("config/network_config.yaml")

# Get logs directory
logs_dir = PathManager.get_logs_dir()
```

### 2. Robust Process Cleanup (`cleanup_agents.py`)

A script that thoroughly cleans up all agent-related processes and resources:

```bash
# Clean up with SIGTERM first, then SIGKILL if necessary
python3 cleanup_agents.py

# Force immediate cleanup with SIGKILL
python3 cleanup_agents.py --force

# Customize wait time before SIGKILL
python3 cleanup_agents.py --wait 10
```

### 3. Improved Layer 0 Startup (`improved_layer0_startup.py`)

An enhanced startup script with better error handling and resource management:

```bash
# Start Layer 0 agents
python3 improved_layer0_startup.py

# Use a specific configuration file
python3 improved_layer0_startup.py --config path/to/config.yaml

# Only clean up resources without starting agents
python3 improved_layer0_startup.py --cleanup-only
```

### 4. Run Script (`run_improved_layer0.sh`)

A shell script that sets up the environment and runs the improved startup script:

```bash
# Run the script
./run_improved_layer0.sh
```

### 5. Test Script (`test_improved_layer0.py`)

A script that tests the stability of the improved Layer 0 startup:

```bash
# Run the test
python3 test_improved_layer0.py
```

## Usage

To start the system with the improved stability features:

1. Clean up any lingering processes:
   ```bash
   python3 cleanup_agents.py
   ```

2. Run the improved Layer 0 startup:
   ```bash
   ./run_improved_layer0.sh
   ```

3. Test the stability:
   ```bash
   python3 test_improved_layer0.py
   ```

## Documentation

For more detailed information, see the following documents:

- [Systemic Instability Diagnosis & Remediation Plan](main_pc_code/NEWMUSTFOLLOW/documents/systemic_instability_diagnosis.md)
- [Systemic Instability Investigation Summary](systemic_instability_summary.md)
- [Task & Report](main_pc_code/NEWMUSTFOLLOW/documents/task&report.md) 