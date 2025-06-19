# Final Correction Plan

This document outlines the corrective actions needed to address the issues identified in the system audit, with the critical understanding that `pc2_health_checker.py` is outdated and must be treated as non-existent.

## Section 1: Deprecation of Outdated Components

### Action Item 1.1: Rename Outdated Health Checker Script
- Rename `pc2_health_checker.py` to `pc2_health_checker.py.DEPRECATED`
- Command: `mv pc2_health_checker.py pc2_health_checker.py.DEPRECATED`

### Action Item 1.2: Remove Service from Configuration
- The script `pc2_health_checker.py` is not directly referenced in the main `docker-compose.yaml` file
- No action needed for docker-compose.yaml
- However, we should update any references in other configuration files:
  - Remove any references in `config/pc2_connections.py` if they exist
  - Update any documentation that references this script

## Section 2: Correction of Path Inconsistencies

### Action Item 2.1: Fix Docker Compose Path References
- Update the following paths in `docker-compose.yaml`:

```yaml
# Change this:
coordinator:
  command: python -u src/core/coordinator_agent.py
# To this:
coordinator:
  command: python -u agents/coordinator_agent.py

# Change this:
health_monitor:
  command: python -u src/core/health_monitor.py
# To this:
health_monitor:
  command: python -u src/core/health_monitor.py
# (No change needed - file exists in correct location)

# Change this:
system_digital_twin:
  command: python -u src/core/system_digital_twin.py
# To this:
system_digital_twin:
  command: python -u src/core/system_digital_twin.py
# (No change needed - file exists in correct location)

# Change this:
rca_agent:
  command: python -u src/core/rca_agent.py
# To this:
rca_agent:
  command: python -u src/core/rca_agent.py
# (No change needed - file exists in correct location)

# Change this:
proactive_context_monitor:
  command: python -u src/core/proactive_context_monitor.py
# To this:
proactive_context_monitor:
  command: python -u src/core/proactive_context_monitor.py
# (No change needed - file exists in correct location)

# Change this:
task_router:
  command: python -u src/core/task_router.py
# To this:
task_router:
  command: python -u src/core/task_router.py
# (No change needed - file exists in correct location)

# Change this:
vision_capture_agent:
  command: python -u src/vision/vision_capture_agent.py
# To this:
vision_capture_agent:
  command: python -u agents/vision_capture_agent.py
# (Assuming the file exists in the agents directory)

# Change this:
pc2_agent:
  command: python -u pc2_package/pc2_launcher.py
# To this:
pc2_agent:
  command: python -u pc2_launcher.py
# (Since the file exists in the root directory)
```

## Section 3: Resolution of Dead-End Connections

### Action Item 3.1: Refactor Coordinator Agent Connections

In `agents/coordinator_agent.py`, update the following connections:

```python
# Remove or update these dead-end connections:
self.stt_socket = self.context.socket(zmq.REQ)
self.stt_socket.connect(f"tcp://localhost:{STT_PORT}")

self.tts_socket = self.context.socket(zmq.REQ)
self.tts_socket.connect(f"tcp://localhost:{TTS_PORT}")

self.nlu_socket = self.context.socket(zmq.REQ)
self.nlu_socket.connect(f"tcp://localhost:{NLU_PORT}")

self.dialog_socket = self.context.socket(zmq.REQ)
self.dialog_socket.connect(f"tcp://localhost:{DIALOG_PORT}")

self.self_healing_socket = self.context.socket(zmq.REQ)
self.self_healing_socket.connect(f"tcp://localhost:{SELF_HEALING_PORT}")

self.vision_capture_socket = self.context.socket(zmq.REQ)
self.vision_capture_socket.connect(f"tcp://localhost:{VISION_CAPTURE_PORT}")

# Add these connections to active services:
# Connect to health_monitor
self.health_monitor_socket = self.context.socket(zmq.REQ)
self.health_monitor_socket.connect(f"tcp://localhost:{HEALTH_MONITOR_PORT}")

# Connect to task_router
self.task_router_socket = self.context.socket(zmq.REQ)
self.task_router_socket.connect(f"tcp://localhost:{TASK_ROUTER_PORT}")

# Update the stop() method to close these new sockets
def stop(self):
    """Stop the Coordinator Agent."""
    logger.info("Stopping CoordinatorAgent")
    self.running = False
    self.socket.close()
    # Close new sockets
    self.health_monitor_socket.close()
    self.task_router_socket.close()
    # Keep existing sockets that are still valid
    self.pc2_socket.close()
    self.vision_processing_socket.close()
    self.suggestion_socket.close()
    self.context.term()
```

### Action Item 3.2: Update PC2 Agent References
Ensure that all PC2 agent references in the codebase are updated to use the latest agents from `_PC2 SOURCE OF TRUTH LATEST`, such as:
- Unified Memory Reasoning Agent (port 5596)
- DreamWorld Agent (port 5598-PUB)
- Other PC2 memory services

## Section 4: Integration of Orphan Agents

### Action Item 4.1: Connect to System Digital Twin

Create or update `vram_manager.py` to connect to the `system_digital_twin`:

```python
# Add to vram_manager.py
import zmq
import logging

# Constants
SYSTEM_DIGITAL_TWIN_PORT = 5585

class VRAMManager:
    def __init__(self):
        # Initialize ZMQ context and socket
        self.context = zmq.Context()
        self.sdt_socket = self.context.socket(zmq.REQ)
        self.sdt_socket.connect(f"tcp://localhost:{SYSTEM_DIGITAL_TWIN_PORT}")
        logger.info(f"Connected to System Digital Twin on port {SYSTEM_DIGITAL_TWIN_PORT}")
        
    def check_vram_availability(self, required_vram_mb):
        """
        Check if there's enough VRAM available for a requested operation
        
        Args:
            required_vram_mb: Amount of VRAM required in MB
            
        Returns:
            bool: True if enough VRAM is available, False otherwise
        """
        try:
            # Send request to System Digital Twin
            self.sdt_socket.send_json({
                "action": "simulate_load",
                "load_type": "vram",
                "value": required_vram_mb
            })
            
            # Get response
            response = self.sdt_socket.recv_json()
            
            # Check recommendation
            if response.get("recommendation") == "proceed":
                logger.info(f"VRAM check passed: {required_vram_mb}MB requested, {response.get('projected_vram_mb')}MB projected")
                return True
            else:
                logger.warning(f"VRAM check failed: {response.get('reason')}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking VRAM availability: {e}")
            # Default to allowing the operation if we can't check
            return True
    
    def cleanup(self):
        """Close connections and clean up resources"""
        if hasattr(self, 'sdt_socket'):
            self.sdt_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
```

## Section 5: Resolution of Port Conflicts

### Action Item 5.1: Resolve Port 5556 Conflict

The port 5556 is referenced as both STT_PORT in coordinator_agent.py and MODEL_MANAGER_PORT in health_monitor.py and task_router.py.

```python
# In agents/coordinator_agent.py:
# Change this:
STT_PORT = 5556
# To this:
STT_PORT = 5566  # New port to avoid conflict

# In src/core/health_monitor.py and src/core/task_router.py:
# Keep MODEL_MANAGER_PORT = 5556 as is, since this is the actual service running on that port

# Update any connection code in coordinator_agent.py:
self.stt_socket = self.context.socket(zmq.REQ)
self.stt_socket.connect(f"tcp://localhost:{STT_PORT}")  # Now connects to port 5566
```

## Implementation Priority

1. **High Priority**:
   - Section 1: Deprecation of outdated components
   - Section 5: Resolution of port conflicts

2. **Medium Priority**:
   - Section 2: Correction of path inconsistencies
   - Section 3: Resolution of dead-end connections

3. **Low Priority**:
   - Section 4: Integration of orphan agents

## Verification Steps

After implementing each section, perform the following verification:

1. Run `docker-compose config` to validate the docker-compose.yaml syntax
2. Start the system with `docker-compose up -d`
3. Check logs for each modified service
4. Verify connections between services using the health monitor

This plan addresses all the issues identified in the audit report while taking into account that pc2_health_checker.py is deprecated and should not be used. 