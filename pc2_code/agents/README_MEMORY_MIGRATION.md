# Memory Agent Migration Guide

## Overview

This document outlines the migration from legacy memory/context/reasoning agents to the new unified memory/reasoning agent for PC2.

## Migrated Components

The following legacy agents have been merged into the unified agent:

1. `contextual_memory_agent.py`

   - Session history management
   - Context summarization
   - Token budget management

2. `memory_agent.py`

   - Short-term and long-term memory
   - Memory storage and retrieval
   - Memory cleanup

3. `context_manager.py`

   - Dynamic context window sizing
   - Importance scoring
   - Speaker-specific context
   - Bilingual keyword support
   - Command pattern detection

4. `error_pattern_memory.py`
   - Error pattern tracking
   - Solution retrieval
   - Error history

## New Unified Agent

The new `unified_memory_reasoning_agent.py` combines all features with improvements:

- Single ZMQ endpoint (port 5596)
- Dedicated health check endpoint (port 5597)
- Improved error handling and logging
- Persistent storage in JSON files
- Thread-safe operations
- Advanced context management
- Error pattern history tracking
- Token budget management
- Bilingual support (English/Tagalog)

## Configuration

The agent uses the following configuration:

```python
# Ports
ZMQ_PORT = 5596
HEALTH_CHECK_PORT = 5597

# Storage paths
CONTEXT_STORE_PATH = "memory_store.json"
ERROR_PATTERNS_PATH = "error_patterns.json"
LOG_PATH = "logs/unified_memory_reasoning_agent.log"

# Memory settings
MAX_SESSION_HISTORY = 50
${SECRET_PLACEHOLDER} 2000
${SECRET_PLACEHOLDER} 0.8
```

## Running the Agent

1. Using the launcher script:

   ```batch
   start_unified_memory_reasoning_agent.bat
   ```

2. Direct Python execution:
   ```bash
   python unified_memory_reasoning_agent.py
   ```

## Testing

A comprehensive test suite is provided in `test_unified_memory_reasoning.py`. Run the tests using:

```batch
run_memory_tests.bat
```

The test suite verifies:

- Context management
- Error pattern handling
- Health monitoring
- Session management
- Token budget compliance

## Data Migration

The agent automatically migrates data from legacy storage:

- Context store: `memory_store.json`
- Error patterns: `error_patterns.json`

## API Changes

The unified agent provides these main actions:

1. `add_interaction`

   - Add new interaction to session
   - Supports metadata

2. `get_context`

   - Retrieve context summary
   - Supports token limits

3. `add_error_pattern`

   - Add new error pattern
   - Includes solution

4. `get_error_solution`

   - Retrieve solution for error

5. `health_check`
   - Get agent status
   - Monitor metrics

## Health Monitoring

The agent provides these metrics:

- Uptime
- Request counts
- Session counts
- Error pattern counts
- Error history size

## Troubleshooting

1. Check logs in `logs/unified_memory_reasoning_agent.log`
2. Verify ZMQ ports are available
3. Ensure storage paths are writable
4. Check Python dependencies:
   - zmq
   - numpy
   - logging

## Future Improvements

Planned enhancements:

1. Distributed storage support
2. Advanced compression
3. Machine learning for pattern detection
4. Real-time metrics dashboard
5. Automated backup system

## Support

For issues or questions:

1. Check the logs
2. Review test results
3. Contact system administrator
4. Submit bug report with logs
