# PC2 Agent Health Check Report

## HEALTHY AGENTS
- agents/ForPC2/unified_monitoring.py
- agents/tutoring_agent.py
- agents/advanced_router.py
- agents/auto_fixer_agent.py

## FAILED AGENTS
- agents/ForPC2/rca_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:20:03,267 - RCA_Agent - INFO - Connected to Self-Healing Agent on 192.168.100.17:5614
2025-06-20 00:20:03,270 - RCA_Agent - INFO - RCA_Agent initialized on port 7121
2025-06-20 00:20:03,270 - RCA_Agent - INFO - RCA_Agent starting on port 7121
2025-06-20 00:20:03,270 - RCA_Agent - INFO - Starting log scanning loop
2025-06-20 00:20:03,762 - RCA_Agent - INFO - Sending recommendation for health_monitor: timeout_error (24 occurrences)
2025-06-20 00:20:08,775 - RCA_Agent - WARNING - Timeout waiting for response from Self-Healing Agent
2025-06-20 00:20:08,776 - RCA_Agent - INFO - Sending recommendation for self_healing_agent: zmq_error (7 occurrences)
2025-06-20 00:20:13,780 - RCA_Agent - WARNING - Timeout waiting for response from Self-Healing Agent
2025-06-20 00:20:13,780 - RCA_Agent - INFO - Sending recommendation for unified_web_agent: zmq_error (14 occurrences)
    ```
- agents/ForPC2/system_digital_twin.py: FAILED
  Error Log:
    ```
2025-06-20 00:20:19,449 - SystemDigitalTwinAgent - INFO - Prometheus client initialized successfully
2025-06-20 00:20:19,450 - SystemDigitalTwinAgent - INFO - SystemDigitalTwin initialized on port 7120
2025-06-20 00:20:19,450 - SystemDigitalTwinAgent - INFO - SystemDigitalTwin starting on port 7120
2025-06-20 00:20:21,725 - urllib3.connectionpool - WARNING - Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("<urllib3.connection.HTTPConnection object at 0x0000024F5DCA21D0>: Failed to resolve 'prometheus' ([Errno 11001] getaddrinfo failed)")': /api/v1/query?query=node_cpu_utilization
2025-06-20 00:20:25,998 - urllib3.connectionpool - WARNING - Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("<urllib3.connection.HTTPConnection object at 0x0000024F5DCA23E0>: Failed to resolve 'prometheus' ([Errno 11001] getaddrinfo failed)")': /api/v1/query?query=node_cpu_utilization
2025-06-20 00:20:32,283 - urllib3.connectionpool - WARNING - Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NameResolutionError("<urllib3.connection.HTTPConnection object at 0x0000024F5DCA2590>: Failed to resolve 'prometheus' ([Errno 11001] getaddrinfo failed)")': /api/v1/query?query=node_cpu_utilization
    ```
- agents/ForPC2/proactive_context_monitor.py: FAILED
  Error Log:
    ```
2025-06-20 00:20:33,548 - ProactiveContextMonitor - INFO - Main socket bound to port 7119
2025-06-20 00:20:33,640 - ProactiveContextMonitor - INFO - Health check server started on port 7120
2025-06-20 00:20:33,640 - ProactiveContextMonitor - INFO - Context processing thread started
2025-06-20 00:20:33,641 - ProactiveContextMonitor - INFO - Proactive Context Monitor initialized on port 7119
2025-06-20 00:20:33,641 - ProactiveContextMonitor - INFO - Proactive Context Monitor starting on port 7119
    ```
- agents/ForPC2/unified_utils_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:20:48,616 - UnifiedUtilsAgent - INFO - UnifiedUtilsAgent initialized on port 7118
2025-06-20 00:20:48,616 - UnifiedUtilsAgent - INFO - UnifiedUtilsAgent starting on port 7118
    ```
- agents/ForPC2/UnifiedErrorAgent.py: FAILED
  Error Log:
    ```
2025-06-20 00:21:03,715 - UnifiedErrorAgent - INFO - Unified Error Agent initialized on port 7117
2025-06-20 00:21:03,715 - UnifiedErrorAgent - INFO - Unified Error Agent starting on port 7117
    ```
- agents/ForPC2/AuthenticationAgent.py: FAILED
  Error Log:
    ```
No specific error message captured.
    ```
- agents/ForPC2/health_monitor.py: FAILED
  Error Log:
    ```
No specific error message captured.
    ```
- agents/self_healing_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - SelfHealingAgent PUB socket bound to port 7126
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - SelfHealingAgent health REP socket bound to port 7129
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - SelfHealingAgent initialized on port 7125
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - SelfHealingAgent starting on port 7125
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - Starting agent monitoring loop
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - Starting resource monitoring loop
2025-06-20 00:21:50,071 - SelfHealingAgent - INFO - Starting log scanning loop
2025-06-20 00:21:50,082 - SelfHealingAgent - INFO - Starting health check loop (health port REP)
    ```
- agents/DreamingModeAgent.py: FAILED
  Error Log:
    ```
2025-06-20 00:22:05,167 - DreamingModeAgent - INFO - DreamingModeAgent health socket bound to port 7128
2025-06-20 00:22:05,169 - DreamingModeAgent - INFO - Connected to DreamWorldAgent on port 7104
2025-06-20 00:22:05,169 - DreamingModeAgent - INFO - DreamingModeAgent initialized on port 7127
2025-06-20 00:22:05,170 - DreamingModeAgent - INFO - DreamingModeAgent starting on port 7127
2025-06-20 00:22:05,170 - DreamingModeAgent - INFO - Starting health check loop
2025-06-20 00:22:05,171 - DreamingModeAgent - INFO - Starting dream scheduler loop
2025-06-20 00:22:05,172 - DreamingModeAgent - INFO - Scheduled dream time reached, starting dream cycle
2025-06-20 00:22:05,172 - DreamingModeAgent - INFO - Starting dream cycle #1
    ```
- agents/unified_web_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:22:20,681 [INFO] [unified_web_agent.py:96] Unified Web Agent bound to port 7126
2025-06-20 00:22:20,681 [INFO] [unified_web_agent.py:101] Health check bound to port 7127
2025-06-20 00:22:20,681 [INFO] [unified_web_agent.py:182] Database tables created
2025-06-20 00:22:20,681 [INFO] [unified_web_agent.py:139] Unified Web Agent initialized on port 7126
2025-06-20 00:22:20,681 [INFO] [unified_web_agent.py:602] Starting Unified Web Agent on port 7126
2025-06-20 00:22:20,681 [INFO] [unified_web_agent.py:630] Starting health check loop
    ```
- agents/task_scheduler.py: FAILED
  Error Log:
    ```
2025-06-20 00:22:35,381 - TaskScheduler - INFO - TaskSchedulerAgent main socket bound to port 7115
2025-06-20 00:22:35,381 - TaskScheduler - INFO - Health check endpoint on port 7116
2025-06-20 00:22:35,381 - TaskScheduler - INFO - TaskSchedulerAgent starting on port 7115 (health: 7116)
2025-06-20 00:22:35,381 - TaskScheduler - INFO - Starting TaskSchedulerAgent main loop
2025-06-20 00:22:36,395 - TaskScheduler - INFO - TaskSchedulerAgent initialization completed
    ```
- agents/resource_manager.py: FAILED
  Error Log:
    ```
2025-06-20 00:22:53,508 - __main__ - INFO - ResourceManager main socket bound to port 7113
2025-06-20 00:22:53,508 - __main__ - INFO - Health check endpoint on port 7114
2025-06-20 00:22:53,523 - __main__ - INFO - ResourceManager starting on port 7113 (health: 7114)
2025-06-20 00:22:53,523 - __main__ - INFO - Starting ResourceManager main loop
2025-06-20 00:22:53,523 - __main__ - INFO - Resource monitoring initialized
2025-06-20 00:22:53,523 - __main__ - INFO - ResourceManager initialization completed
    ```
- agents/experience_tracker.py: FAILED
  Error Log:
    ```
2025-06-20 00:23:05,594 - __main__ - INFO - ExperienceTrackerAgent main socket bound to port 7112
2025-06-20 00:23:05,596 - __main__ - INFO - Health check endpoint on port 7113
2025-06-20 00:23:05,600 - __main__ - INFO - ExperienceTrackerAgent starting on port 7112 (health: 7113)
2025-06-20 00:23:05,600 - __main__ - INFO - Starting ExperienceTrackerAgent main loop
2025-06-20 00:23:06,614 - __main__ - INFO - ExperienceTrackerAgent initialization completed
    ```
- agents/memory_manager.py: FAILED
  Error Log:
    ```
2025-06-20 00:23:20,648 - __main__ - INFO - MemoryManager main socket bound to port 7110
2025-06-20 00:23:20,648 - __main__ - INFO - Health check endpoint on port 7111
2025-06-20 00:23:20,663 - __main__ - INFO - MemoryManager starting on port 7110 (health: 7111)
2025-06-20 00:23:20,663 - __main__ - INFO - Starting MemoryManager main loop
2025-06-20 00:23:20,663 - __main__ - INFO - Memory database initialized
2025-06-20 00:23:20,663 - __main__ - INFO - MemoryManager initialization completed
    ```
- agents/context_manager.py: FAILED
  Error Log:
    ```
2025-06-20 00:23:35,896 - __main__ - INFO - ContextManagerAgent main socket bound to port 7111
2025-06-20 00:23:35,896 - __main__ - INFO - Health check endpoint on port 7112
2025-06-20 00:23:35,896 - __main__ - INFO - [ContextManager] Initialized with size range 5-20, current: 10
2025-06-20 00:23:35,896 - __main__ - INFO - ContextManagerAgent starting on port 7111 (health: 7112)
2025-06-20 00:23:35,896 - __main__ - INFO - Starting ContextManagerAgent main loop
2025-06-20 00:23:36,914 - __main__ - INFO - ContextManagerAgent initialization completed
    ```
- agents/EpisodicMemoryAgent.py: FAILED
  Error Log:
    ```
2025-06-20 00:23:52,113 - __main__ - INFO - EpisodicMemoryAgent main socket bound to port 7106
2025-06-20 00:23:52,115 - __main__ - INFO - Health check endpoint on port 7107
2025-06-20 00:23:52,116 - __main__ - INFO - EpisodicMemoryAgent starting on port 7106 (health: 7107)
2025-06-20 00:23:52,116 - __main__ - INFO - Starting EpisodicMemoryAgent service loop
2025-06-20 00:23:52,117 - __main__ - INFO - TF-IDF vectorizer initialized for text similarity
2025-06-20 00:23:52,117 - __main__ - INFO - EpisodicMemoryAgent initialization completed
    ```
- agents/unified_memory_reasoning_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:24:06,260 [INFO] [unified_memory_reasoning_agent.py:258] Agent bound to ports 7105 (main) and 7106 (health)
2025-06-20 00:24:06,260 [INFO] [unified_memory_reasoning_agent.py:301] Unified Memory and Reasoning Agent starting initialization...
2025-06-20 00:24:06,260 [INFO] [unified_memory_reasoning_agent.py:856] Starting main service loop
2025-06-20 00:24:06,262 [INFO] [unified_memory_reasoning_agent.py:368] No existing twin store found, starting with empty store
2025-06-20 00:24:06,262 [INFO] [unified_memory_reasoning_agent.py:89] [ContextManager] Initialized with size range 5-20, current: 10
2025-06-20 00:24:06,264 [INFO] [unified_memory_reasoning_agent.py:322] Connected to memory agent: episodic
2025-06-20 00:24:06,266 [INFO] [unified_memory_reasoning_agent.py:322] Connected to memory agent: dreamworld
2025-06-20 00:24:06,266 [INFO] [unified_memory_reasoning_agent.py:330] Unified Memory and Reasoning Agent initialization completed
    ```
- agents/DreamWorldAgent.py: FAILED
  Error Log:
    ```
2025-06-20 00:24:21,349 - __main__ - INFO - DreamWorld Agent listening on 0.0.0.0:7104
2025-06-20 00:24:21,349 - __main__ - INFO - Health check endpoint on 0.0.0.0:7105
2025-06-20 00:24:21,349 - __main__ - INFO - DreamWorld Agent starting on 0.0.0.0:7104 (health: 7105)
2025-06-20 00:24:21,365 - __main__ - INFO - Connected to Enhanced Model Router at localhost:5598
2025-06-20 00:24:21,365 - __main__ - INFO - Connected to Episodic Memory Agent at localhost:5629
2025-06-20 00:24:21,365 - __main__ - INFO - Dream World Agent initialization completed
    ```
- agents/cache_manager.py: FAILED
  Error Log:
    ```
No specific error message captured.
    ```
- agents/tiered_responder.py: FAILED
  Error Log:
    ```
2025-06-20 00:24:54,111 - INFO - Tiered Responder started
    ```
- agents/LearningAdjusterAgent.py: FAILED
  Error Log:
    ```
2025-06-20 00:25:06,499 - __main__ - INFO - LearningAdjusterAgent listening on 0.0.0.0:5643
2025-06-20 00:25:06,499 - __main__ - INFO - Connected to PerformanceLoggerAgent at localhost:5632
2025-06-20 00:25:06,499 - __main__ - INFO - Connected to AgentTrustScorer at localhost:5628
2025-06-20 00:25:06,499 - __main__ - INFO - Connected to LearningAgent at localhost:5633
2025-06-20 00:25:06,499 - __main__ - INFO - LearningAdjusterAgent initialized on port None
2025-06-20 00:25:06,499 - __main__ - INFO - LearningAdjusterAgent started
    ```
- agents/remote_connector_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:25:21,733 - RemoteConnector - INFO - [remote_connector_agent.py:591] - Starting Remote Connector Agent...
2025-06-20 00:25:21,733 - RemoteConnector - INFO - [remote_connector_agent.py:49] - ================================================================================
2025-06-20 00:25:21,733 - RemoteConnector - INFO - [remote_connector_agent.py:50] - Initializing Remote Connector Agent
2025-06-20 00:25:21,733 - RemoteConnector - INFO - [remote_connector_agent.py:51] - ================================================================================
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:59] - Remote Connector bound to port 5557
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:70] - Connected to Model Manager on 192.168.100.16:5610
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:81] - Subscribed to Model Manager status updates on 192.168.100.16:5620
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:113] - Remote Connector Agent initialized
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:114] - Cache enabled: True
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:115] - Cache TTL: 3600 seconds
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:116] - Standalone mode: False
2025-06-20 00:25:21,748 - RemoteConnector - INFO - [remote_connector_agent.py:117] - ================================================================================
    ```
- agents/tutor_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:25:41,746 [INFO] Tutor Agent listening on 0.0.0.0:5603
    ```
- agents/tutoring_service_agent.py: FAILED
  Error Log:
    ```
INFO:__main__:Tutoring Service Agent listening on 0.0.0.0:5604
    ```
- agents/UnifiedMemoryReasoningAgent.py: FAILED
  Error Log:
    ```
INFO:__main__:Unified Memory Reasoning Agent listening on 0.0.0.0:5596
    ```
- agents/performance_monitor.py: FAILED
  Error Log:
    ```
2025-06-20 00:26:22,267 - INFO - Performance Monitor started
    ```
- agents/async_processor.py: FAILED
  Error Log:
    ```
2025-06-20 00:26:39,845 - INFO - Async Processor started
    ```
- agents/enhanced_contextual_memory.py: FAILED
  Error Log:
    ```
2025-06-20 00:26:52,414 [INFO] [enhanced_contextual_memory.py:209] Enhanced Contextual Memory started on port 5596
2025-06-20 00:26:52,414 [INFO] [enhanced_contextual_memory.py:367] Starting Enhanced Contextual Memory service
    ```
- agents/PerformanceLoggerAgent.py: FAILED
  Error Log:
    ```
2025-06-20 00:27:09,333 - __main__ - INFO - PerformanceLoggerAgent initialized on port 5632
2025-06-20 00:27:09,333 - __main__ - INFO - PerformanceLoggerAgent started
    ```
- agents/AgentTrustScorer.py: FAILED
  Error Log:
    ```
2025-06-20 00:27:24,445 - __main__ - INFO - AgentTrustScorer initialized on port 5626
2025-06-20 00:27:24,445 - __main__ - INFO - AgentTrustScorer started
    ```
- agents/memory_decay_manager.py: FAILED
  Error Log:
    ```
2025-06-20 00:27:39,503 - __main__ - INFO - MemoryDecayManager initialized and listening on port 5624
2025-06-20 00:27:39,503 - __main__ - INFO - Starting MemoryDecayManager main loop
    ```
- agents/filesystem_assistant_agent.py: FAILED
  Error Log:
    ```
2025-06-20 00:27:55,679 [INFO] [FileSystemAssistant] Agent started on port 5606 with REP socket
2025-06-20 00:27:55,679 [INFO] [FileSystemAssistant] Working directory: D:\DISKARTE\Voice Assistant
2025-06-20 00:27:55,679 [INFO] [FileSystemAssistant] Starting agent...
2025-06-20 00:27:55,679 [INFO] [FileSystemAssistant] Starting request handling loop
    ```
