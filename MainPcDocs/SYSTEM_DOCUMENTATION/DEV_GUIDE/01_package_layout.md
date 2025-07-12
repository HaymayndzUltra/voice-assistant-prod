# Package Layout and Development Setup

## Overview

This project uses modern Python packaging with `pyproject.toml` to simplify dependency management and imports across the codebase.

## Project Structure

The AI System is organized into several key packages:

- `common`: Shared utilities and base classes
- `main_pc_code`: Code specific to the main PC
- `pc2_code`: Code specific to PC2
- `utils`: General utility functions
- `src`: Core system components

## Development Setup

### Initial Setup

To set up your development environment:

1. Clone the repository
2. Install the project in development mode:

```bash
pip install -e .
```

This performs an "editable install" which makes all packages available throughout your Python environment without needing to modify `sys.path`.

#### Troubleshooting Installation

If you encounter network issues during installation:

```bash
# Try using a different PyPI mirror
pip install -e . --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Or install with the --no-build-isolation flag
pip install -e . --no-build-isolation

# If you're behind a proxy, configure pip accordingly
# pip install -e . --proxy http://your-proxy:port
```

### Benefits of Editable Install

- **Simplified imports**: Import modules directly without path manipulation
- **Live updates**: Changes to code are immediately available without reinstallation
- **Proper namespace resolution**: Avoids import conflicts and path issues

### Example Usage

Before:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main_pc_code.agents.some_agent import SomeAgent
```

After:
```python
from main_pc_code.agents.some_agent import SomeAgent
```

## Best Practices

1. **Never use `sys.path.insert`** for imports within the codebase
2. **Always use relative or absolute imports** based on the package structure
3. **Keep `pyproject.toml` updated** when adding new dependencies

## Migration Strategy

To migrate from `sys.path.insert` to proper imports:

1. Install the package in development mode with `pip install -e .`
2. Use the provided scripts to identify files with `sys.path.insert`:
   ```bash
   python3 scripts/remove_sys_path_inserts.py
   ```
3. Refactor one module or directory at a time:
   ```bash
   python3 scripts/remove_sys_path_example.py path/to/file.py --apply
   ```
4. Run tests after each change to ensure functionality is preserved
5. Commit changes incrementally to make review easier

## CI Checks

Our CI pipeline includes checks to prevent the introduction of new `sys.path.insert` calls. This helps maintain clean import practices across the codebase. 