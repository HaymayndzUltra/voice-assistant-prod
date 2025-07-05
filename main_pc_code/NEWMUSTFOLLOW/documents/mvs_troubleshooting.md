# MVS Troubleshooting Guide

## Common Issues and Solutions

### 1. Agent Fails to Start

**Symptoms:**
- Agent process terminates immediately after starting
- Error messages about missing modules or imports
- "Script not found" errors

**Solutions:**
- Check that the script path in `minimal_system_config.yaml` is correct
- Ensure all required Python packages are installed
- Verify the PYTHONPATH environment variable includes the project root
- Check for syntax errors in the agent code

### 2. ZMQ Connection Issues

**Symptoms:**
- "Address already in use" errors
- Agents can't communicate with each other
- Timeout errors when checking agent health

**Solutions:**
- Ensure no other processes are using the same ports
- Kill any zombie agent processes: `pkill -f "python.*agent"`
- Check that the bind address is correct (usually 0.0.0.0 for all interfaces)
- Verify firewall settings aren't blocking ZMQ communication

### 3. Health Check Failures

**Symptoms:**
- Agent reports as "TIMEOUT" or "ERROR" in health checks
- Agent is running but not responding to health check requests

**Solutions:**
- Check that the agent's health check port is correct (usually main port + 1)
- Verify the agent has implemented the health check protocol correctly
- Ensure the agent is binding to the correct interface
- Look for error messages in the agent's logs

### 4. Dependency Issues

**Symptoms:**
- Dependent agents fail to start or connect to their dependencies
- Error messages about missing services

**Solutions:**
- Ensure all dependency agents are started first and are healthy
- Check that service discovery is working correctly
- Verify port numbers match between agent and its dependencies
- Increase the startup delay between agents

### 5. Environment Variable Problems

**Symptoms:**
- Agents fail with "KeyError" or "ValueError" exceptions
- Configuration issues reported in logs

**Solutions:**
- Check that all required environment variables are set in `run_mvs.sh`
- Verify the values are correct for your environment
- Ensure directory paths exist and are accessible

### 6. Resource Constraints

**Symptoms:**
- Agents crash with out-of-memory errors
- System becomes unresponsive when running multiple agents

**Solutions:**
- Adjust MAX_MEMORY_MB and MAX_VRAM_MB environment variables
- Start fewer agents simultaneously
- Close other applications to free up resources

## Debugging Techniques

### 1. Check Agent Logs

```bash
# View the last 50 lines of an agent's log
tail -n 50 logs/agent_name.log

# Follow log output in real-time
tail -f logs/agent_name.log
```

### 2. Test Individual Agents

```bash
# Start a single agent with debug logging
LOG_LEVEL=DEBUG python main_pc_code/agents/agent_name.py

# Test agent health check directly
python -c "import zmq; ctx=zmq.Context(); s=ctx.socket(zmq.REQ); s.connect('tcp://localhost:PORT'); s.send_json({'action':'health_check'}); print(s.recv_json())"
```

### 3. Check Port Usage

```bash
# See which processes are using which ports
sudo netstat -tulpn | grep LISTEN

# Check if a specific port is in use
sudo lsof -i :PORT_NUMBER
```

### 4. Monitor System Resources

```bash
# Monitor CPU, memory, and process stats
htop

# Monitor network connections
sudo netstat -tulpn
```

### 5. Debug ZMQ Communication

```bash
# Install zmqtool for debugging
pip install zmqtool

# Monitor ZMQ traffic (replace PORT with the agent's port)
zmqtool sub tcp://localhost:PORT
```

## Agent-Specific Troubleshooting

### ModelManagerAgent

- Ensure CUDA is available if using GPU models
- Check model paths in configuration
- Verify VRAM settings are appropriate for your GPU

### SystemDigitalTwin

- Check if Prometheus is running (if used)
- Verify the health check port (8120) is accessible

### SelfTrainingOrchestrator

- Ensure the database directory exists and is writable
- Check for the correct attribute name (`is_running` vs `running`)

### StreamingSpeechRecognition

- Verify audio preprocessing is working
- Check if USE_DUMMY_AUDIO is set correctly for testing

### MemoryOrchestrator

- Ensure database connections are configured correctly
- Check for proper encoding/decoding of messages

## Getting Help

If you continue to experience issues:

1. Collect all relevant logs
2. Note the exact error messages
3. Document the steps to reproduce the issue
4. Check for similar issues in the project documentation
5. Contact the development team with complete information 