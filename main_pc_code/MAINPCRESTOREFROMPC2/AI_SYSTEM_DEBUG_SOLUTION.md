# AI System Debug Solution

## Identified Issues

1. **Module Import Errors**
   - `ModuleNotFoundError: No module named 'src'` or `'utils'`
   - Path patch not applied consistently across agents
   - Python path not properly set up

2. **Port Conflicts**
   - Multiple ports already in use (8570, 5570, 5624, 5703, etc.)
   - Previous agent processes still running

3. **Missing Configuration Files**
   - Missing `config/system_config.json` (partially exists but may have path issues)
   - Missing `config/model_configs.json`
   - Missing `data/personas.json`

4. **Syntax Errors**
   - In `unified_planning_agent.py`: mismatched parentheses in endpoint string

5. **Command Line Argument Handling**
   - `IntentionValidatorAgent` doesn't recognize `--TaskRouter_host` (case sensitivity)
   - Inconsistent argument naming across agents

## Solution Implementation

### 1. Fix Path Patch in All Agents

A consistent path patch has been applied to ensure all agents can import from `src` and `utils`:

```python
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MAIN_PC_CODE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)
```

### 2. Fix File Paths

- Updated file paths in `DynamicIdentityAgent.py` to use `os.path.join(MAIN_PC_CODE, ...)` for consistent path resolution
- Created missing config files:
  - `config/model_configs.json` with basic model configurations
  - Ensured `data/personas.json` will be created if missing

### 3. Fix Syntax Errors

- Fixed the syntax error in `unified_planning_agent.py`:
  - Changed `f"tcp://{_agent_args.host}:"){PLANNING_AGENT_PORT}"` to `f"tcp://{_agent_args.host}:{PLANNING_AGENT_PORT}"`

### 4. Fix Command Line Argument Handling

- Updated `IntentionValidatorAgent.py` to handle both lowercase and uppercase argument names
- Added normalization function to `utils/config_parser.py` to standardize argument handling

### 5. Process Management

- Created a script to kill all existing Python processes to free up ports
- Added proper logging configuration to all agents

## Diagnostic and Fix Tools

### 1. `fix_system.py`

This script automates the fixing process:
- Kills all existing Python processes
- Applies the path patch to all agent files
- Creates missing config files
- Fixes syntax errors
- Standardizes argument handling

### 2. `check_system_health.py`

This script helps diagnose the system:
- Tests port connections for key agents
- Checks if required config files exist
- Reports the overall system health status

## Usage Instructions

1. **Kill all existing Python processes**:
   ```bash
   python main_pc_code/fix_system.py
   ```

2. **Check system health**:
   ```bash
   python main_pc_code/check_system_health.py
   ```

3. **Start the system**:
   ```bash
   python main_pc_code/start_ai_system.py
   ```

## Additional Recommendations

1. **Standardize Path Handling**
   - Use absolute paths consistently across all agents
   - Always use `os.path.join()` for path construction
   - Create directories if they don't exist before accessing files

2. **Process Management**
   - Implement proper process cleanup on system shutdown
   - Store PIDs of running processes for controlled termination
   - Add health check endpoints to all agents

3. **Error Handling**
   - Add better error reporting for missing dependencies
   - Implement graceful fallbacks for configuration errors
   - Add retry mechanisms for transient failures

4. **Logging Improvements**
   - Standardize logging format across all agents
   - Implement log rotation to prevent large log files
   - Add structured logging for better analysis

5. **Configuration Management**
   - Centralize configuration in one place
   - Implement configuration validation
   - Add environment-specific configuration overrides 