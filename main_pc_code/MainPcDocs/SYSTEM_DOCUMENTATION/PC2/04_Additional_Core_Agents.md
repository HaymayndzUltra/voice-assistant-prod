# Group: Additional Core Agents

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: AgentTrustScorer
- **Main Class:** AgentTrustScorer
- **Host Machine:** PC2
- **Role:** Tracks and scores the reliability of AI models based on their performance metrics
- **🎯 Responsibilities:** 
  - Maintains a database of trust scores for different models
  - Logs model performance including success/failure and response time
  - Provides historical performance data for models
  - Calculates trust scores based on success rate and response time
- **🔗 Interactions:** 
  - Receives performance metrics from other agents
  - Provides trust scores to agents that need to select optimal models
  - Reports errors to the central Error Bus
- **🧬 Technical Deep Dive:** 
  - Uses SQLite database to store model scores and performance logs
  - Calculates trust scores using weighted combination of success rate (70%) and response time (30%)
  - Implements REQ/REP pattern for synchronous communication with other agents
  - Provides an API for logging performance metrics and retrieving scores
- **⚠️ Panganib:** 
  - Database corruption could lead to loss of model trust history
  - Potential performance bottleneck with high volume of requests
  - Incorrect trust scores could lead to suboptimal model selection
- **📡 Communication Details:** 
  - **🔌 Health Port:** AGENT_TRUST_SCORER_PORT + 1
  - **🛰️ Port:** 5626

---
### 🧠 AGENT PROFILE: FileSystemAssistantAgent
- **Main Class:** FileSystemAssistantAgent
- **Host Machine:** PC2
- **Role:** Provides controlled file system operations to other agents in the distributed system
- **🎯 Responsibilities:** 
  - Performs file operations (read, write, list, delete, copy, move)
  - Creates and manages directories
  - Checks file existence and attributes
  - Provides file metadata and information
- **🔗 Interactions:** 
  - Services file operation requests from any agent in the system
  - Reports errors to the central Error Bus
  - Provides health status information
- **🧬 Technical Deep Dive:** 
  - Uses ZMQ REP socket for request-response communication
  - Implements a thread-safe design with locks for file operations
  - Provides a health check endpoint on a separate port
  - Maintains detailed logging of all file operations
  - Implements error handling and reporting
- **⚠️ Panganib:** 
  - Access control limitations - can potentially modify any file with permissions
  - Risk of filesystem exhaustion if misused
  - Possible file locking issues with concurrent operations
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5607
  - **🛰️ Port:** 5606

---
### 🧠 AGENT PROFILE: RemoteConnectorAgent
- **Main Class:** RemoteConnectorAgent
- **Host Machine:** PC2
- **Role:** Provides a unified interface for AI model API requests to remote/local models
- **🎯 Responsibilities:** 
  - Handles API requests to various AI model endpoints
  - Manages model access and selection
  - Implements response caching for improved performance
  - Monitors model status and availability
- **🔗 Interactions:** 
  - Connects to Model Manager Agent for model availability information
  - Communicates with external AI model APIs
  - Reports errors to the central Error Bus
  - Services requests from other agents needing AI model access
- **🧬 Technical Deep Dive:** 
  - Uses ZMQ REQ/REP pattern for synchronous communication
  - Subscribes to model status updates for real-time availability
  - Implements disk-based caching with TTL for model responses
  - Provides health status reporting
  - Can operate in standalone mode if Model Manager is unavailable
- **⚠️ Panganib:** 
  - Dependency on external model services
  - Cache could serve stale data if not properly invalidated
  - Potential bottleneck for high request volumes
- **📡 Communication Details:** 
  - **🔌 Health Port:** REMOTE_CONNECTOR_PORT + 1
  - **🛰️ Port:** 5557

---
### 🧠 AGENT PROFILE: UnifiedWebAgent
- **Main Class:** UnifiedWebAgent
- **Host Machine:** PC2
- **Role:** Provides web browsing, information gathering, and context-aware navigation capabilities
- **🎯 Responsibilities:** 
  - Performs web browsing using headless browser automation
  - Searches the web for information
  - Extracts content from web pages
  - Handles form submission and interaction
  - Provides proactive information gathering
- **🔗 Interactions:** 
  - Connects to SystemDigitalTwin through service discovery
  - Interfaces with memory system for storing web information
  - Reports errors to the central Error Bus
  - Services requests from other agents needing web data
- **🧬 Technical Deep Dive:** 
  - Uses Selenium for browser automation
  - Implements content caching in SQLite database
  - Provides context-aware navigation using NLP techniques
  - Features proactive topic monitoring and information gathering
  - Handles interrupts for stopping long-running operations
- **⚠️ Panganib:** 
  - Browser automation can be fragile and break with website changes
  - Risk of IP blocking from too many requests
  - Memory leaks from browser instances if not properly managed
  - Network dependency for all operations
- **📡 Communication Details:** 
  - **🔌 Health Port:** 7127
  - **🛰️ Port:** 7126

---
### 🧠 AGENT PROFILE: DreamingModeAgent
- **Main Class:** DreamingModeAgent
- **Host Machine:** PC2
- **Role:** Coordinates system dreaming and simulation cycles for learning and optimization
- **🎯 Responsibilities:** 
  - Manages dreaming intervals and schedules
  - Coordinates with DreamWorldAgent for simulations
  - Tracks dream success rates and quality
  - Optimizes dream scheduling based on system state
- **🔗 Interactions:** 
  - Communicates with DreamWorldAgent to run simulations
  - Reports errors to the central Error Bus
  - Provides dream status information to other agents
- **🧬 Technical Deep Dive:** 
  - Implements background threads for scheduling and health checks
  - Tracks dream statistics (count, success rate, quality)
  - Provides configurable dream intervals and durations
  - Supports manual and automatic dream cycle triggering
- **⚠️ Panganib:** 
  - Resource contention during dream cycles
  - Potential system instability if dream simulations fail
  - Scheduling conflicts with critical system operations
- **📡 Communication Details:** 
  - **🔌 Health Port:** 7128
  - **🛰️ Port:** 7127

---
### 🧠 AGENT PROFILE: PerformanceLoggerAgent
- **Main Class:** PerformanceLoggerAgent
- **Host Machine:** PC2
- **Role:** Logs and tracks performance metrics for system components
- **🎯 Responsibilities:** 
  - Records performance metrics for agents and actions
  - Tracks resource usage (CPU, memory)
  - Provides historical performance data
  - Handles cleanup of old performance data
- **🔗 Interactions:** 
  - Receives performance metrics from other agents
  - Reports errors to the central Error Bus
  - Provides performance data upon request
- **🧬 Technical Deep Dive:** 
  - Uses SQLite database for storing metrics and resource usage
  - Implements automatic cleanup of old data
  - Provides thread-safe database access
  - Supports querying metrics by agent and time range
- **⚠️ Panganib:** 
  - Database growth could impact performance over time
  - Single point of failure for performance tracking
  - Potential performance overhead from extensive logging
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5633
  - **🛰️ Port:** 5632

---
### 🧠 AGENT PROFILE: AdvancedRouter
- **Main Class:** AdvancedRouterAgent
- **Host Machine:** PC2
- **Role:** Provides task classification and intelligent routing for system requests
- **🎯 Responsibilities:** 
  - Analyzes input text to detect task types
  - Maps tasks to appropriate model capabilities
  - Tracks task type statistics
  - Helps optimize task routing in the system
- **🔗 Interactions:** 
  - Services routing requests from other agents
  - Reports errors to the central Error Bus
  - Provides task classification information
- **🧬 Technical Deep Dive:** 
  - Uses keyword matching and pattern recognition for task classification
  - Implements multiple task categories (code, reasoning, chat, creative, factual, math)
  - Provides confidence scores for classifications
  - Tracks statistics on task type distribution
- **⚠️ Panganib:** 
  - Incorrect task classification could lead to suboptimal routing
  - Pattern recognition may become outdated without updates
  - Limited by the predefined task categories
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5556
  - **🛰️ Port:** 5555

---

### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| AgentTrustScorer | ✓ | |
| FileSystemAssistantAgent | ✓ | |
| RemoteConnectorAgent | ✓ | |
| UnifiedWebAgent | ✓ | |
| DreamingModeAgent | ✓ | |
| PerformanceLoggerAgent | ✓ | |
| AdvancedRouter | ✓ | |
