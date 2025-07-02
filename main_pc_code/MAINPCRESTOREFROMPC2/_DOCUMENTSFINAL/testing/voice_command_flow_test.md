# Voice Command Flow End-to-End Test

## Overview

This document describes the end-to-end test for verifying the voice command flow through the MainPC agent system. The test simulates a voice command input and verifies the successful flow of data through the entire processing chain: `AudioCapture → StreamingSpeechRecognition → TaskRouter → Responder → TTS`.

## Test Components

### Test Files

- **Main Test Script**: `/main_pc_code/tests/test_voice_command_flow.py`
- **Test Runner**: `/main_pc_code/scripts/run_voice_flow_test.py`

### Agents Required

The following agents must be running for the end-to-end test:

1. **SystemDigitalTwin** - Central registry for agent discovery
2. **StreamingSpeechRecognition** - Processes speech audio into text
3. **TaskRouter** - Routes tasks to appropriate handlers
4. **Responder** - Generates responses to user queries
5. **TTSConnector** - Manages TTS requests (Text-to-Speech)
6. **TTSAgent** - (Optional) Actual speech synthesis

## Communication Flow

```
                  ┌────────────────────┐
                  │    Test Script     │
                  └────────┬───────────┘
                           │
                           ▼
            (1) Simulated Transcript
                           │
                           ▼
┌───────────────────────────────────────────┐
│       StreamingSpeechRecognition          │
└───────────────────────┬───────────────────┘
                        │
                        ▼
                  (2) Transcription
                        │
                        ▼
┌───────────────────────────────────────────┐
│             TaskRouter                    │
└───────────────────────┬───────────────────┘
                        │
                        ▼
                  (3) Task Response
                        │
                        ▼
┌───────────────────────────────────────────┐
│             Responder                     │
└───────────────────────┬───────────────────┘
                        │
                        ▼
                  (4) Response Text
                        │
                        ▼
┌───────────────────────────────────────────┐
│           TTS Connector                   │
└───────────────────────┬───────────────────┘
                        │
                        ▼
                  (5) Speech Output
                        │
                        ▼
┌───────────────────────────────────────────┐
│             Test Script                   │
│     (Verifies final speech text output)   │
└───────────────────────────────────────────┘
```

## Message Formats

The test script simulates and monitors the following message formats:

1. **Speech Recognition Output**:
   ```json
   "TRANSCRIPTION: {
     "text": "What is the weather like today?", 
     "confidence": 0.95, 
     "language": "en", 
     "language_confidence": 0.99, 
     "timestamp": 1719348765.23
   }"
   ```

2. **Task Router Request**:
   ```json
   {
     "task_type": "weather_query",
     "content": "What is the weather like today?",
     "language": "en",
     "priority": "normal"
   }
   ```

3. **TTS Output**:
   The test script listens for the final text that would be sent to the TTS engine.

## Running the Test

### Prerequisites

1. Ensure all required agents are properly configured.
2. Make sure all necessary ports are available as per the port registry.

### Automatic Test Execution

The test runner script automatically starts all required agents and runs the test:

```bash
python -m main_pc_code.scripts.run_voice_flow_test [--debug] [--skip-agent-start]
```

Options:
- `--debug`: Enable debug-level logging for detailed diagnostics
- `--skip-agent-start`: Skip starting agents (use if they're already running)

### Manual Test Execution

If you prefer to manually start agents and run the test:

1. Start all required agents in separate terminals
2. Run the test script:
   ```bash
   python -m main_pc_code.tests.test_voice_command_flow [--debug]
   ```

## Test Cases

The test script includes the following test cases:

1. **Basic Voice Command Flow** - Tests the full flow from speech recognition to TTS
2. **Direct Task Routing** - Tests direct interaction with the TaskRouter agent

## Measured Metrics

The test captures and reports:
- Total flow latency (end-to-end)
- Task router latency

## Troubleshooting

If the test fails:

1. Check agent logs in `/logs/` directory
2. Verify all agents are running and reachable
3. Check network connectivity between agents
4. Verify message formats match the expected formats

Common issues:
- Timeout waiting for TTS response: Check if Responder and TTS agents are properly connected
- Service discovery failures: Verify SystemDigitalTwin is running
- Message format errors: Check for changes in message schemas

## Future Improvements

- Add more test cases covering different voice commands
- Add tests for error handling scenarios
- Include voice command intent detection verification
- Add support for testing with actual audio input files 