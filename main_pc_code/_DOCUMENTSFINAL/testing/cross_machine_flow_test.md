# Cross-Machine Registration and Communication Test

## Overview

The Cross-Machine Registration and Communication Test verifies the fundamental capability of agents to register with the SystemDigitalTwin (SDT) on MainPC and communicate across the distributed system. This test is essential for validating the core network integration between MainPC and PC2.

## Test Components

### 1. Test Script
The main test script is located at:
```
/home/haymayndz/AI_System_Monorepo/main_pc_code/tests/test_cross_machine_registration.py
```

This script performs the following steps:
1. Verifies that SystemDigitalTwin is running and healthy on MainPC
2. Discovers UnifiedMemoryReasoningAgent on PC2 through the SystemDigitalTwin
3. Establishes direct communication with UnifiedMemoryReasoningAgent
4. Sends a test message and validates the response

### 2. PC2 Agent Implementation
The test relies on the UnifiedMemoryReasoningAgent on PC2 to handle TEST_PING commands. The implementation is located at:
```
/home/haymayndz/AI_System_Monorepo/pc2_code/agents/UnifiedMemoryReasoningAgent.py
```

The agent's `process_message` method has been updated to respond to TEST_PING commands with an echo of the received data.

## Prerequisites

Before running the test, ensure that:

1. The network configuration is properly set up in `config/network_config.yaml` with the correct:
   - PC2 IP address
   - MainPC IP address
   - Port configurations

2. The following agents are running:
   - SystemDigitalTwin on MainPC (port 7120)
   - UnifiedMemoryReasoningAgent on PC2 (port defined in configuration, typically 7105)

3. Secure ZMQ Environment Variable is set correctly:
   - If using secure ZMQ, set `SECURE_ZMQ=1`
   - If not using secure ZMQ, set `SECURE_ZMQ=0` or leave it unset

4. If using secure ZMQ, the certificates are properly installed in the `certificates/` directory

## Running the Test

To run the test from MainPC:

1. Start the SystemDigitalTwin on MainPC:
   ```bash
   cd /home/haymayndz/AI_System_Monorepo
   python -m main_pc_code.agents.system_digital_twin
   ```

2. Start the UnifiedMemoryReasoningAgent on PC2:
   ```bash
   cd /home/haymayndz/AI_System_Monorepo
   python -m pc2_code.agents.UnifiedMemoryReasoningAgent
   ```

3. In a third terminal, run the test script:
   ```bash
   cd /home/haymayndz/AI_System_Monorepo
   python -m main_pc_code.tests.test_cross_machine_registration
   ```

## Test Flow Details

### 1. SystemDigitalTwin Health Check
The test first verifies that the SystemDigitalTwin is running and accessible by sending a health check request to its endpoint. This step is crucial as SDT is the central registry for all agents in the system.

### 2. Agent Discovery
The test then uses the service_discovery_client to discover the UnifiedMemoryReasoningAgent that should be registered with the SDT. This verifies that the registration process works correctly across machines.

### 3. Direct Communication
Using the information obtained from the discovery step, the test establishes direct communication with the PC2 agent and sends a TEST_PING command. This verifies that:
- The network path between MainPC and PC2 is open
- The ZMQ socket connections are working properly 
- Encryption (if enabled) is functioning correctly

### 4. Message Exchange
The test sends a simple message containing "Hello from MainPC Cross-Machine Test!" and expects the PC2 agent to echo this data back, confirming a full roundtrip message flow.

## Troubleshooting

### Connection Issues
- **Error: "Failed to discover UnifiedMemoryReasoningAgent"**
  - Verify that UnifiedMemoryReasoningAgent is running on PC2
  - Check that the agent has successfully registered with SDT
  - Inspect logs to ensure registration was attempted

- **Error: "Communication with UnifiedMemoryReasoningAgent timed out"**
  - Verify network connectivity between MainPC and PC2
  - Check firewall settings on both machines
  - Verify the PC2 agent is listening on the expected port
  - Check the message format compatibility

### Security Issues
- **Error: "ZMQ security error"**
  - Ensure the SECURE_ZMQ environment variable is consistently set across all components
  - Verify that certificates are generated and placed in the correct directory
  - Check that both client and server have access to the certificate files

## Future Enhancements

1. **More Extensive Testing**: Add tests for high-volume message exchange and stress testing
2. **Performance Measurements**: Add latency and throughput measurements
3. **Multiple Agents**: Test communication paths between multiple PC2 agents
4. **Error Case Testing**: Add tests for network failures, agent crashes, and recovery

## Related Files

- **SystemDigitalTwin**: `/main_pc_code/agents/system_digital_twin.py`
- **UnifiedMemoryReasoningAgent**: `/pc2_code/agents/UnifiedMemoryReasoningAgent.py`
- **Service Discovery Client**: `/main_pc_code/utils/service_discovery_client.py`
- **Network Config**: `/config/network_config.yaml`
- **Secure ZMQ**: `/main_pc_code/src/network/secure_zmq.py` 