# File System Roles & Responsibilities

## JSON State Files (Authoritative Data)
- **todo-tasks.json**: MASTER TASK STORAGE - Source of truth for all tasks and TODOs
- **cursor_state.json**: CURSOR SESSION STATE - Current file, line, task context
- **task-state.json**: TASK EXECUTION STATE - Current task progress and status
- **task_interruption_state.json**: INTERRUPTION HANDLING - Resume logic and recovery

## Memory Files (Data Persistence)
- **memory.json**: MCP SERVER CONFIG - External service configurations
- **memory_store.json**: SIMPLE MEMORY STORE - Basic key-value memory storage
- **memory-bank/memory.db**: PERSISTENT MEMORY DB - SQLite database for complex memory
- **memory-bank/current-session.md**: SESSION SUMMARY - Human-readable current state
- **memory-bank/plan.md**: PROJECT PLANNING - High-level goals and strategies
- **memory-bank/evolution_blueprint.md**: SYSTEM EVOLUTION - Architecture roadmap
- **memory-bank/cli_dependency_architecture_map.md**: TECHNICAL DOCS - System architecture
- **cursor_memory_bridge.py**: JSON-TO-MARKDOWN BRIDGE - Converts state to human format
- **workflow_memory_intelligence_fixed.py**: TASK INTELLIGENCE - Smart task processing
- **memory_system/cli.py**: CLI INTERFACE - Command-line entry point

## Markdown Files (Human Documentation)
- **memory-bank/current-session.md**: SESSION SUMMARY - Human-readable current state
- **memory-bank/plan.md**: PROJECT PLANNING - High-level goals and strategies
- **memory-bank/evolution_blueprint.md**: SYSTEM EVOLUTION - Architecture roadmap
- **memory-bank/cli_dependency_architecture_map.md**: TECHNICAL DOCS - System architecture

## Integration Modules (System Bridges)
- **auto_sync_manager.py**: STATE SYNCHRONIZATION - Keeps all state files in sync
- **cursor_memory_bridge.py**: JSON-TO-MARKDOWN BRIDGE - Converts state to human format
- **todo_manager.py**: TASK CRUD OPERATIONS - Create, read, update, delete tasks
- **workflow_memory_intelligence_fixed.py**: TASK INTELLIGENCE - Smart task processing
- **memory_system/cli.py**: CLI INTERFACE - Command-line entry point

## Data Flow Rules
1. **todo-tasks.json** is the single source of truth for tasks
2. All other JSON files sync FROM todo-tasks.json
3. Markdown files are generated FROM JSON state
4. Integration modules maintain consistency
5. CLI operates through integration modules
