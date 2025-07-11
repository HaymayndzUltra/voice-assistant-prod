# Group: Additional Agents

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: TutoringAgent
- **Main Class:** AdvancedTutoringAgent
- **Host Machine:** PC2
- **Role:** Provides personalized tutoring and educational lesson generation
- **🎯 Responsibilities:** 
  - Generates educational lessons on various topics
  - Adapts content based on difficulty level and student profile
  - Tracks user progress and learning history
  - Provides personalized lesson recommendations
  - Caches lessons for improved performance
- **🔗 Interactions:** 
  - Communicates with Model Orchestrator for LLM-based lesson generation
  - Reports errors to the central Error Bus
  - Provides health status information to monitoring systems
- **🧬 Technical Deep Dive:** 
  - Uses LLM models to generate structured educational content
  - Implements lesson caching for improved performance
  - Provides JSON-structured lessons with exercises and answers
  - Maintains fallback options when LLM is unavailable
  - Supports various difficulty levels and student profiles
- **⚠️ Panganib:** 
  - Dependency on LLM availability for high-quality content
  - Cache invalidation challenges for updated topics
  - Quality of content dependent on prompt engineering
  - Risk of generating incorrect or outdated information
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5651
  - **🛰️ Port:** 5650

---
