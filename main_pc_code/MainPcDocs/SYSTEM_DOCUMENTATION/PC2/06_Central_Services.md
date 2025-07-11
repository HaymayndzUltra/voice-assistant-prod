# Group: Central Services

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: MemoryOrchestratorService
- **Main Class:** MemoryOrchestratorService
- **Host Machine:** PC2
- **Role:** Central unified memory system for the entire distributed AI system
- **🎯 Responsibilities:** 
  - Manages all memory types (interaction, episodic, knowledge)
  - Implements hierarchical, tiered storage system (short, medium, long)
  - Handles memory lifecycle: decay, consolidation, and summarization
  - Provides memory relationships and context grouping
  - Supports search and semantic retrieval of memories
- **🔗 Interactions:** 
  - Serves as central memory API for all agents in the system
  - Reports errors to the central Error Bus
  - Integrates with Redis for high-performance caching
  - Provides SQLite database persistence for long-term storage
- **🧬 Technical Deep Dive:** 
  - Uses Pydantic models for robust data validation
  - Implements a sophisticated decay algorithm based on memory tiers
  - Supports explicit memory relationships and context grouping
  - Provides thread-safe database access
  - Features background lifecycle management for memory processing
  - Handles batch operations for efficient memory management
- **⚠️ Panganib:** 
  - Single point of failure for system memory
  - Database corruption risks
  - Redis dependency for optimal performance
  - Memory leaks possible with high volume of persistent memories
  - Computational overhead of lifecycle management
- **📡 Communication Details:** 
  - **🔌 Health Port:** DEFAULT_PORT + 1
  - **🛰️ Port:** 7140

---
