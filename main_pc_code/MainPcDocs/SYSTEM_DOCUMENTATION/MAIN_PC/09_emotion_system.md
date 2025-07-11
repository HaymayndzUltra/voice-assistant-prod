# Group: Emotion System

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: EmotionEngine
- **Main Class:** `EmotionEngine` (`main_pc_code/agents/emotion_engine.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Manages and processes emotional states and responses, serving as the central hub for the system's emotional intelligence.
- **🎯 Responsibilities:** 
  - Maintains current emotional state (tone, sentiment, intensity, dominant emotion)
  - Processes emotional cues from various sources
  - Broadcasts emotional state updates to subscribers
  - Maps emotional combinations to nuanced states
  - Reports errors to central error bus
- **🔗 Interactions:** 
  - Broadcasts to MoodTrackerAgent and other subscribers
  - Receives emotional cues from various agents
  - Reports errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses ZMQ REP socket for handling requests
  - Uses ZMQ PUB socket for broadcasting emotional state
  - Maintains emotion thresholds for sentiment and intensity
  - Maps emotion combinations (e.g., 'angry'+'high' = 'furious')
  - Implements health check endpoint
- **⚠️ Panganib:** 
  - Emotional state broadcasts could be interrupted
  - Emotion processing could become biased with insufficient inputs
  - Potential for feedback loops if not properly calibrated
- **📡 Communication Details:** 
  - **🔌 Health Port:** Port + 1 (default: 5591)
  - **🛰️ Port:** Default 5590
  - **🔧 Environment Variables:** AGENT_NAME, AGENT_PORT, HEALTH_CHECK_PORT, PROJECT_ROOT, PC2_IP
  - **📑 Sample Request:** `{"action": "update_emotional_state", "emotional_cues": {"tone": "happy", "sentiment": 0.8, "intensity": 0.7}}`
  - **📊 Resource Footprint (baseline):** Lightweight, primarily CPU-bound for emotion processing
  - **🔒 Security & Tuning Flags:** None documented in source

---
### 🧠 AGENT PROFILE: MoodTrackerAgent
- **Main Class:** `MoodTrackerAgent` (`main_pc_code/agents/mood_tracker_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Tracks and analyzes user mood over time based on emotional state updates from EmotionEngine.
- **🎯 Responsibilities:** 
  - Subscribes to EmotionEngine broadcasts
  - Tracks current mood state
  - Maintains mood history
  - Maps user emotions to appropriate AI response emotions
  - Provides mood history and long-term mood analysis
- **🔗 Interactions:** 
  - Subscribes to EmotionEngine for emotional state updates
  - Responds to queries from other agents about current mood and history
  - Reports errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses ZMQ SUB socket to receive EmotionEngine broadcasts
  - Maintains fixed-size deque for mood history
  - Implements emotion mapping (e.g., 'sad' → 'empathetic')
  - Calculates long-term mood trends using weighted averages
- **⚠️ Panganib:** 
  - Dependency on EmotionEngine broadcasts
  - Limited history size could lose important historical context
  - Potential for memory growth if history size not properly managed
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5581 (main_port+1) – inherited & bound
  - **🛰️ Port:** Default 5580
  - **🔧 Environment Variables:** HOST, PC2_IP

---
### 🧠 AGENT PROFILE: HumanAwarenessAgent
- **Main Class:** `HumanAwarenessAgent` (`main_pc_code/agents/HumanAwarenessAgent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Monitors and analyzes human interaction patterns, including tone detection and emotional analysis.
- **🎯 Responsibilities:** 
  - Monitors tone of speech through ToneDetector
  - Maintains tone history
  - Provides context window for interaction
  - Responds to tone and context queries
- **🔗 Interactions:** 
  - Connects to ToneDetector for tone updates
  - Responds to requests for tone and context information
- **🧬 Technical Deep Dive:** 
  - Uses ZMQ SUB socket to receive tone updates
  - Manages tone detector as a subprocess
  - Maintains history of detected tones
  - Provides REP socket for handling queries
- **⚠️ Panganib:** 
  - Dependency on tone detector subprocess
  - Potential for resource leaks if subprocess not properly managed
  - Limited error handling for tone detection failures
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (loaded from config, e.g., **5627**) – ensure binding
  - **🛰️ Port:** Loaded from configuration
  - **🔧 Environment Variables:** None explicitly defined in source

---
### 🧠 AGENT PROFILE: ToneDetector
- **Main Class:** `ToneDetector` (`main_pc_code/agents/tone_detector.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Analyzes speech transcriptions to detect emotional tone and language.
- **🎯 Responsibilities:** 
  - Connects to Whisper stream for speech transcriptions
  - Analyzes tone of speech (neutral, frustrated, confused, excited, tired)
  - Detects language (English, Tagalog, Taglish)
  - Provides tone information to other agents
  - Falls back to direct microphone access if needed
- **🔗 Interactions:** 
  - Connects to Whisper stream for transcriptions
  - Optionally connects to TagalogAnalyzer service
  - Reports errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses ZMQ SUB socket to receive Whisper transcriptions
  - Can initialize Whisper model directly if stream unavailable
  - Implements tone analysis using keyword and pattern matching
  - Uses queue for sharing detected tones with other components
  - Has development mode for simulated tone detection
- **⚠️ Panganib:** 
  - Dependency on Whisper transcription service
  - Resource intensive when using direct microphone access
  - Pattern-based tone detection may not be accurate for all contexts
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5626 (main_port+1) – inherited & bound
  - **🛰️ Port:** Default 5625
  - **🔧 Environment Variables:** PC2_IP

---
### 🧠 AGENT PROFILE: VoiceProfilingAgent
- **Main Class:** `VoiceProfilingAgent` (`main_pc_code/agents/voice_profiling_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Handles voice enrollment, speaker recognition, and voice profile management.
- **🎯 Responsibilities:** 
  - Enrolls new speakers with voice samples
  - Identifies speakers from audio data
  - Manages voice profiles
  - Updates profiles through continuous learning
  - Provides voice profile information to other agents
- **🔗 Interactions:** 
  - Receives audio samples for enrollment and identification
  - Reports errors to error bus
- **🧬 Technical Deep Dive:** 
  - Stores voice profiles as JSON files
  - Implements speaker identification with confidence scoring
  - Supports continuous learning to improve profiles
  - Configurable confidence thresholds for recognition
- **⚠️ Panganib:** 
  - Privacy concerns with stored voice profiles
  - Potential for false positives in speaker identification
  - Storage growth with continuous learning
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5601 (main_port+1) – inherited & bound
  - **🛰️ Port:** Default 5600
  - **🔧 Environment Variables:** PC2_IP

---
### 🧠 AGENT PROFILE: EmpathyAgent
- **Main Class:** `EmpathyAgent` (`main_pc_code/agents/EmpathyAgent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Adapts system responses based on emotional context, providing appropriate empathetic reactions.
- **🎯 Responsibilities:** 
  - Updates emotional profile based on detected emotions
  - Determines appropriate voice settings for TTS
  - Forwards voice settings to StreamingTTSAgent
  - Manages persona-based response patterns
- **🔗 Interactions:** 
  - Connects to StreamingTTSAgent to update voice settings
  - Receives emotional state updates
- **🧬 Technical Deep Dive:** 
  - Uses service discovery to find StreamingTTSAgent
  - Maps emotional states to voice parameter adjustments
  - Supports secure ZMQ connections
  - Implements voice setting determination based on emotion and intensity
- **⚠️ Panganib:** 
  - Dependency on StreamingTTSAgent
  - Voice setting adjustments may not be appropriate for all contexts
  - Potential for disconnection from TTS service
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5704 (main_port+1) – inherited & bound
  - **🛰️ Port:** Default 5703
  - **🔧 Environment Variables:** None explicitly defined in source

---
### 🧠 AGENT PROFILE: EmotionSynthesisAgent
- **Main Class:** `EmotionSynthesisAgent` (`main_pc_code/agents/emotion_synthesis_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Adds emotional nuance to text responses based on specified emotions.
- **🎯 Responsibilities:** 
  - Synthesizes emotional markers in text
  - Adds appropriate interjections, sentence starters, and modifiers
  - Adjusts text based on emotion and intensity
  - Reports errors to error bus
- **🔗 Interactions:** 
  - Receives text synthesis requests
  - Reports errors to error bus
- **🧬 Technical Deep Dive:** 
  - Maintains emotion markers dictionary for different emotions
  - Implements probabilistic text modification based on intensity
  - Tracks metrics for synthesis operations
  - Provides health status reporting
- **⚠️ Panganib:** 
  - Synthesized emotions may not always be appropriate
  - Potential for overuse of emotional markers
  - Limited emotional vocabulary for some emotions
- **📡 Communication Details:** 
  - **🔌 Health Port:** 6643 (explicit)
  - **🛰️ Port:** Default 5643
  - **🔧 Environment Variables:** PC2_IP

---

### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| EmotionEngine | ✓ | |
| MoodTrackerAgent | ✓ | |
| HumanAwarenessAgent | ✓ | |
| ToneDetector | ✓ | |
| VoiceProfilingAgent | ✓ | |
| EmpathyAgent | ✓ | |
| EmotionSynthesisAgent | ✓ | |

