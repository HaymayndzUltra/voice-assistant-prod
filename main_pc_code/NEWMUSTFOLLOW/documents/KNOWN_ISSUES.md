# Known Issues with MVS

## StreamingAudioCapture

1. **Health Check Loop Errors**

   - Error: `'NoneType' object has no attribute 'poll'`
   - This occurs in the BaseAgent health check loop
   - The agent still initializes correctly in dummy mode
   - Likely cause: The health check mechanism is trying to access a process that isn't properly initialized in dummy mode
   - **Resolution**: This needs to be fixed in the BaseAgent class or handled in the StreamingAudioCapture agent

2. **No Messages in Dummy Mode**
   - When running in dummy mode, no audio messages are sent
   - This is expected behavior as dummy mode is designed to skip actual audio capture
   - **Resolution**: No action needed, but this should be documented for testing purposes

## General MVS Issues

1. **Path Resolution**

   - Some scripts may have issues finding the correct paths to agent files or configuration files
   - **Resolution**: Use absolute paths or the path resolution mechanisms implemented in the improved launcher scripts

2. **Dependencies**

   - Some agents may have dependencies that aren't installed
   - For example, StreamingAudioCapture requires PyAudio, NumPy, ZeroMQ, Whisper, and PyTorch
   - **Resolution**: Document all dependencies and add installation instructions

3. **Port Conflicts**
   - Agents use hardcoded ports which may conflict with other processes
   - **Resolution**: Implement dynamic port allocation and service discovery

## Testing Recommendations

1. **Test Individual Agents First**

   - Test each agent in isolation before testing the full MVS
   - Use the `--agent` flag with the launcher: `./launch_mvs_local.py --agent AgentName`

2. **Use Dummy Mode for Initial Testing**

   - For agents that support it, use dummy mode for initial testing
   - This avoids issues with hardware dependencies (e.g., microphones)

3. **Incremental Integration**
   - Start with core agents only, then gradually add dependencies
   - This makes it easier to identify and fix integration issues

## Next Steps

1. **Fix Health Check Loop Errors**

   - Investigate and fix the health check loop errors in the BaseAgent class
   - Ensure proper error handling in all agents

2. **Complete Dependency Documentation**

   - Create a comprehensive list of all dependencies required by the MVS
   - Add installation instructions for each dependency

3. **Implement Better Error Handling**

   - Add more robust error handling to all agents
   - Ensure that errors are properly logged and don't crash the system

4. **Enhance Testing Scripts**
   - Create more comprehensive test scripts for each agent
   - Add integration tests for groups of related agents
