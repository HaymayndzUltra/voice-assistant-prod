/agent
COMPREHENSIVE DOCKER INFRASTRUCTURE FIX - AI SYSTEM MONOREPO (Dual-Machine: MainPC RTX 4090 + PC2 RTX 3060):

CRITICAL ISSUE ANALYSIS:
1. CONTAINER NETWORKING BREAKDOWN:
   - Agents connecting to localhost instead of container hostnames
   - Redis connection failures: "Error 111 connecting to localhost:6379"
   - NATS connection failures: "Connect call failed ('127.0.0.1', 4222)"
   - BaseAgent StandardizedHealthChecker hardcoded to localhost
   - Environment variables not properly passed to Python agents

2. PORT CONFLICT RESOLUTION:
   - SystemDigitalTwin port 8220 "Address already in use"
   - ServiceRegistry health port 8200 not responding
   - Container port mapping conflicts between services
   - Host port conflicts with existing processes

3. CONFIGURATION SYNCHRONIZATION:
   - startup_config.yaml ports don't match container port mappings
   - Environment variables inconsistent between docker-compose and agent startup
   - Missing container-specific configuration overrides

AUTOMATED FIXES REQUIRED:

PHASE 1: CONTAINER NETWORKING FIXES
- Update all agent code to use environment variables for Redis/NATS connections
- Fix BaseAgent StandardizedHealthChecker to accept redis_host/redis_port parameters
- Update ServiceRegistry, SystemDigitalTwin, RequestCoordinator argument parsing
- Ensure all agents pass redis_host/redis_port to BaseAgent constructor
- Fix NATS connection configuration in unified error handler

PHASE 2: DOCKER COMPOSE OPTIMIZATION
- Update docker-compose.yml to use proper container networking
- Add health checks for Redis and NATS services
- Configure proper environment variable passing to all containers
- Fix port mappings to match startup_config.yaml
- Add container restart policies and resource limits

PHASE 3: AGENT STARTUP SCRIPT ENHANCEMENT
- Create robust startup script that handles all edge cases
- Add proper error handling and retry logic
- Implement graceful shutdown procedures
- Add comprehensive logging and monitoring
- Ensure proper Python path and module imports

PHASE 4: DUAL-MACHINE DEPLOYMENT VALIDATION
- Test container deployment on both MainPC (RTX 4090) and PC2 (RTX 3060)
- Validate cross-machine communication via Docker networks
- Ensure GPU access works correctly for both machines
- Test service discovery across dual-machine setup

COMPREHENSIVE TESTING PROTOCOL:
1. Build all containers and verify no build failures
2. Start infrastructure services (Redis, NATS) and validate connectivity
3. Start core agents individually and capture detailed logs
4. Test inter-agent communication via ZMQ and NATS
5. Validate health check endpoints respond correctly
6. Test graceful shutdown and restart procedures
7. Verify resource cleanup and memory management
8. Test cross-machine communication scenarios

SUCCESS CRITERIA:
- All 77 agents (54 MainPC + 23 PC2) start successfully in containers
- Zero connection failures to Redis and NATS
- All health check endpoints respond within 5 seconds
- No port conflicts across dual-machine setup
- Proper GPU utilization on both RTX 4090 and RTX 3060
- Automated container restart and recovery working
- Complete logging and monitoring operational

DELIVERABLE: Fully operational Docker infrastructure with comprehensive error handling, dual-machine support, automated recovery, and production-ready deployment scripts.

COMMIT MESSAGE: "DOCKER INFRASTRUCTURE: Complete container networking fix - all 77 agents operational, dual-machine support, automated recovery, production-ready deployment"
