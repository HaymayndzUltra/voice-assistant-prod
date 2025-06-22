# Advanced AI Agents

## Overview
This directory contains advanced AI agents designed to enhance the voice assistant with cascade-level capabilities. These agents work together to provide more intelligent, context-aware, and reliable code generation and problem solving.

# AI LATEST OVERVIEW

## Session and Deduplication Pipeline (2025-05-18)

All major modules in the modular voice assistant system implement robust session and deduplication logic:

- **Session ID Propagation:** Every command/audio chunk is tagged with a unique session_id, propagated through all modules (audio_capture, speech_recognition, language_analyzer, translation, text_processor, coordinator, etc.), ensuring every message/response/log is traceable to its originating session.
- **Chunk Hash Deduplication:** Each audio chunk is hashed (chunk_hash). Before processing, each module checks if the chunk_hash was already processed (using a TTL cache). Duplicates are skipped, preventing double-processing and duplicate responses.
- **Context Tracking:** Downstream modules always propagate session_id and chunk_hash in all outgoing messages, maintaining full context and traceability pipeline-wide.
- **Async/Parallel Ready:** Architecture enables safe parallel and asynchronous processing. Multiple commands, interruptions, and overlapping chunks are handled without race conditions or context mix-ups.
- **Race Condition Protection:** Deduplication and session tracking guarantee only one response per chunk/session, even if jobs overlap or are retried.

### Module Roles and Session/Deduplication Handling

| Module             | Role                                   | Session ID Handling    | Chunk Hash Handling     |
|--------------------|----------------------------------------|-----------------------|------------------------|
| audio_capture      | Captures audio, assigns session_id     | Generates & attaches  | Hashes chunk, checks & attaches |
| speech_recognition | Transcribes audio                      | Propagates            | Checks, propagates     |
| language_analyzer  | Detects language                       | Propagates            | Checks, propagates     |
| translation        | Translates non-English to English      | Propagates            | Checks, propagates     |
| text_processor     | Intent detection, response generation  | Propagates            | Checks, propagates     |
| coordinator        | Orchestrates modules, manages sessions | Tracks, propagates    | Monitors, propagates   |

- **See also:** system_architecture.md for pipeline diagrams and further details.
- **For implementation details:** Check each module's README or docstring for session/chunk_hash usage examples.
- **For troubleshooting:** All logs now include session_id and chunk_hash for easy tracing.

### Benefits
- No duplicate or mixed-up outputs, even under heavy load or rapid-fire commands.
- Debugging and monitoring is session-aware.
- Foundation for advanced features: streaming, barge-in, and full-duplex interaction.

**Last updated:** 2025-05-18

## Starting the Advanced Agents
To start all advanced agents:
```
python start_advanced_agents.py
```

Alternatively, you can include them in your regular startup by using the updated `run_all_agents.py`.

### Available Agents

### Context Summarizer Agent (Port: 5610)
- Maintains a running summary of user interactions, code, errors, and key decisions
- Maximizes context window efficiency when working with LLMs
- Tracks interactions by user and project

### Error Pattern Memory (Port: 5611)
- Maintains a database of encountered errors and their successful fixes
- Enables more intelligent debugging and auto-fix workflows
- Learns from past errors to suggest solutions

### Chain of Thought Agent (Port: 5612)
- Transforms a single user request into a sequence of reasoning steps
- Helps models break down complex coding problems into manageable pieces
- Provides more reliable code generation through step-wise reasoning

### Test Generator Agent (Port: 5613)
- Automatically creates tests for generated code
- Validates functionality and helps identify issues before execution
- Suggests fixes for failing tests

### Auto-Fixer Agent (Port: 5605)
- Orchestrates auto-code correction and debugging loop
- Automatically detects and fixes common code errors
- Provides detailed error analysis and correction suggestions
- Leverages Error Pattern Memory for learned fixes

### Enhanced Model Router (Port: 5601)
- Routes requests to the most appropriate advanced agent or LLM
- Adds relevant context from the Context Summarizer
- Uses Chain of Thought for complex reasoning tasks

## Integration
These agents integrate with your existing voice assistant framework via ZMQ messaging. The Enhanced Model Router serves as the primary interface between your existing system and the advanced agents.

## Usage
To use these agents in your code:

```python
# For context-aware code generation
from agents.chain_of_thought_agent import generate_code_with_cot

# Generate code with context awareness and step-by-step reasoning
solution = generate_code_with_cot("Create a function to download and resize images", code_context)

# For automatic test generation
from agents.test_generator_agent import test_code

# Test the generated code
test_results = test_code(solution, "Function to download and resize images")

# Check if tests passed
if test_results["test_results"]["success"]:
    print("All tests passed!")
else:
    print(f"Tests failed. Suggested fix: {test_results['suggested_fixes']}")
```

## Configuration
Each agent uses a standard ZMQ port for communication. If you need to change these ports, edit the respective agent file.

### Advanced Agent Port Assignments

| Agent Name                | Port   | Description                          |
|--------------------------|--------|--------------------------------------|
| Enhanced Model Router     | 5601   | Central router for advanced agents   |
| Context Summarizer Agent  | 5610   | Maintains context summaries          |
| Error Pattern Memory      | 5611   | Stores error/fix patterns            |
| Chain of Thought Agent    | 5612   | Stepwise reasoning                   |
| Test Generator Agent      | 5613   | Generates and validates tests        |
| Auto-Fixer Agent          | 5605   | Code correction/fix loop             |

## Integration with Existing Agents

### For Code Generation
The advanced agents enhance your existing code generation pipeline:
1. **User Request** → Task Router Agent
2. **Task Router** → Enhanced Model Router Agent (Port: 5601)
3. **Enhanced Model Router Agent** →
   - **Chain of Thought Agent** (Port: 5612) for complex tasks
   - **Test Generator Agent** (Port: 5613) for automatic test creation
   - **Error Pattern Memory** (Port: 5611) for learned error/fix suggestions
   - **Context Summarizer Agent** (Port: 5610) for context compression
4. **Chain of Thought Agent** → Test Generator Agent (for stepwise code validation)
5. **Test Generator Agent** → Auto-Fixer Agent (if tests fail)
6. **Auto-Fixer Agent** (Port: 5605) → Enhanced Model Router Agent (for fix loop)

### For Memory Management
The Context Summarizer and Error Pattern Memory enhance your existing memory system:
1. **Context Summarizer** works with Contextual Memory Agent
2. **Error Pattern Memory** works with Auto-Fixer Agent
3. **Both** provide enhanced context to LLMs via Enhanced Model Router

## Cascade-Level Features
These agents implement several key features found in advanced AI coding assistants:
- **Extended Memory**: Maintain continuity across long coding sessions
- **Error Learning**: System improves over time as it encounters and resolves more errors
- **Consistency**: Code generation remains aligned with earlier design decisions
- **Efficiency**: Compressing context into summaries allows more tokens for actual generation
- **Auto-Healing**: Automatically suggest fixes based on past successes
