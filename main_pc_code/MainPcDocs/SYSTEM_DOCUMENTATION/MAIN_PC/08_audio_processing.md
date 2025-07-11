# Group: Audio Processing

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: AudioCapture
- **Main Class:** `StreamingAudioCapture` (`main_pc_code/agents/streaming_audio_capture.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Captures and streams audio chunks in real-time to downstream modules via ZMQ, with integrated wake word detection.
- **🎯 Responsibilities:** 
  - Capture raw audio from microphone
  - Stream audio chunks to downstream modules
  - Detect wake words using Whisper
  - Provide energy-based fallback detection
  - Report errors to central error bus
- **🔗 Interactions:** 
  - Publishes raw audio via ZMQ PUB socket
  - Publishes health status via ZMQ REP socket
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses PyAudio for audio capture (with dummy mode fallback)
  - Audio buffer with configurable size for wake word detection
  - Whisper model for wake word detection
  - Energy-based fallback detection
  - Background threads for health monitoring and wake word detection
- **⚠️ Panganib:** 
  - PyAudio initialization failures can occur
  - Wake word detection is resource-intensive
  - False positives/negatives in wake word detection
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default port + 1 (e.g., 6576)
  - **🛰️ Port:** Default 6575 (from config)
  - **🔧 Environment Variables:** `USE_DUMMY_AUDIO`, `AGENT_NAME`, `AGENT_PORT`, `PROJECT_ROOT`, `PC2_IP`
  - **📑 Sample Request:** N/A (publishes audio chunks as binary data)
  - **📊 Resource Footprint (baseline):** High CPU usage during wake word detection, moderate memory usage for audio buffers and Whisper model
  - **🔒 Security & Tuning Flags:** Error bus reporting, configurable wake word sensitivity and energy threshold

---
### 🧠 AGENT PROFILE: FusedAudioPreprocessor
- **Main Class:** `FusedAudioPreprocessor` (`main_pc_code/agents/fused_audio_preprocessor.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Optimized audio preprocessing agent that combines noise reduction and voice activity detection.
- **🎯 Responsibilities:** 
  - Subscribe to raw audio from StreamingAudioCapture
  - Apply noise reduction algorithms
  - Perform voice activity detection (VAD)
  - Publish cleaned audio and VAD events
  - Apply acoustic echo cancellation (AEC) and automatic gain control (AGC)
- **🔗 Interactions:** 
  - Subscribes to raw audio from StreamingAudioCapture
  - Publishes cleaned audio via ZMQ PUB socket
  - Publishes VAD events via ZMQ PUB socket
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses noisereduce for spectral gating noise reduction
  - Voice activity detection with adaptive threshold
  - Acoustic echo cancellation with adaptive filter
  - Automatic gain control for consistent audio levels
  - Service discovery for finding audio source
- **⚠️ Panganib:** 
  - Noise reduction can distort speech if too aggressive
  - VAD may miss soft speech or detect non-speech as speech
  - High CPU usage during processing
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6581 (from config)
  - **🛰️ Port:** Default 5703 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`
  - **📑 Sample Request:** N/A (subscribes to audio chunks, publishes processed audio)
  - **📊 Resource Footprint (baseline):** Moderate to high CPU usage, moderate memory usage
  - **🔒 Security & Tuning Flags:** Configurable noise reduction strength, VAD threshold, AEC and AGC parameters

---
### 🧠 AGENT PROFILE: StreamingInterruptHandler
- **Main Class:** `StreamingInterrupt` (`main_pc_code/agents/streaming_interrupt.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Listens for interruption keywords in real-time while the assistant is responding.
- **🎯 Responsibilities:** 
  - Listen for interrupt keywords (stop, wait, cancel, pause, change)
  - Use Vosk for lightweight local speech recognition
  - Send interrupt signals via ZMQ
- **🔗 Interactions:** 
  - Publishes interrupt events via ZMQ PUB socket
- **🧬 Technical Deep Dive:** 
  - Uses Vosk for lightweight speech recognition
  - Processes audio in real-time through callback
  - Detects specific interrupt keywords
  - Inherits from BaseAgent
- **⚠️ Panganib:** 
  - May miss interruptions if speech is unclear
  - Requires Vosk model to be available
  - Fixed device index may cause issues if audio setup changes
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (default **5563**) – inherited & should be bound for monitoring
  - **🛰️ Port:** Default 5562 (interrupt PUB), BaseAgent main REQ/REP unused
  - **🔧 Environment Variables:** None explicitly defined
  - **📑 Sample Request:** N/A (publishes interrupt events as JSON)
  - **📊 Resource Footprint (baseline):** Low to moderate CPU usage, low memory usage
  - **🔒 Security & Tuning Flags:** None explicitly defined

---
### 🧠 AGENT PROFILE: StreamingSpeechRecognition
- **Main Class:** `StreamingSpeechRecognition` (`main_pc_code/agents/streaming_speech_recognition.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Enhanced speech recognition system with wake word integration, dynamic model management, and real-time streaming.
- **🎯 Responsibilities:** 
  - Subscribe to clean audio from FusedAudioPreprocessor
  - Process audio for speech recognition
  - Detect language automatically
  - Integrate with wake word detection
  - Publish transcriptions
- **🔗 Interactions:** 
  - Subscribes to clean audio from FusedAudioPreprocessor
  - Subscribes to wake word events
  - Subscribes to VAD events
  - Publishes transcriptions via ZMQ PUB socket
  - Connects to ModelManagerAgent for model loading
  - Connects to RequestCoordinator
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses Whisper for speech recognition
  - Dynamic resource management based on system load
  - Language detection for multilingual support
  - Wake word and VAD integration for better accuracy
  - Noise reduction for improved recognition
- **⚠️ Panganib:** 
  - High resource usage during speech recognition
  - May struggle with accented speech or background noise
  - Dependent on multiple services being available
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6582 (from config)
  - **🛰️ Port:** Default 5707 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`, `SECURE_ZMQ`
  - **📑 Sample Request:** N/A (subscribes to audio, publishes transcriptions)
  - **📊 Resource Footprint (baseline):** High CPU and memory usage, especially with larger models
  - **🔒 Security & Tuning Flags:** Dynamic resource management, configurable batch size and quantization

---
### 🧠 AGENT PROFILE: StreamingTTSAgent
- **Main Class:** `UltimateTTSAgent` (`main_pc_code/agents/streaming_tts_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Provides advanced text-to-speech capabilities with a 4-tier fallback system.
- **🎯 Responsibilities:** 
  - Convert text to speech using XTTS v2 (primary)
  - Provide fallbacks: Windows SAPI, pyttsx3, console print
  - Stream audio chunks for real-time playback
  - Support voice customization and emotions
  - Handle interruptions
- **🔗 Interactions:** 
  - Receives TTS requests via ZMQ REP socket
  - Connects to UnifiedSystemAgent for health monitoring
  - Subscribes to interrupt handler
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses XTTS v2 for high-quality multilingual speech
  - Audio cache with LRU eviction policy
  - Background threads for initialization, playback, health monitoring
  - Sentence splitting for more natural speech
  - Voice customization with speaker samples
- **⚠️ Panganib:** 
  - XTTS initialization is resource-intensive
  - May have high latency for first-time speech
  - Cache can consume significant memory if not managed
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (default **5563**) – inherited & should be bound
  - **🛰️ Port:** Default 5562 (from config)
  - **🔧 Environment Variables:** `SECURE_ZMQ`, `BIND_ADDRESS`, `XTTS_PATH`, `TETEY_VOICE_PATH`, `PC2_IP`
  - **📑 Sample Request:** 
    ```json
    {
      "text": "Hello, world!",
      "emotion": "joy",
      "speed": 1.0
    }
    ```
  - **📊 Resource Footprint (baseline):** High memory usage for XTTS model, moderate CPU usage during speech synthesis
  - **🔒 Security & Tuning Flags:** Secure ZMQ optional, configurable voice parameters

---
### 🧠 AGENT PROFILE: WakeWordDetector
- **Main Class:** `WakeWordDetector` (`main_pc_code/agents/wake_word_detector.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Integrates with existing streaming pipeline for wake word detection.
- **🎯 Responsibilities:** 
  - Use Porcupine for wake word detection
  - Subscribe to audio from StreamingAudioCapture
  - Integrate with VAD for improved accuracy
  - Publish wake word events
- **🔗 Interactions:** 
  - Subscribes to audio from StreamingAudioCapture
  - Subscribes to VAD events
  - Publishes wake word events via ZMQ PUB socket
  - Publishes health status via ZMQ PUB socket
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses Porcupine for wake word detection
  - Audio format conversion for compatibility
  - Energy calculation for confidence scoring
  - VAD integration for better accuracy
  - Detection cooldown to prevent multiple triggers
- **⚠️ Panganib:** 
  - Requires Porcupine API key for full functionality
  - May have false positives in noisy environments
  - Dependent on audio stream quality
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6579 (from config)
  - **🛰️ Port:** Default 5705 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PORCUPINE_ACCESS_KEY`, `PC2_IP`
  - **📑 Sample Request:** N/A (publishes wake word events as JSON)
  - **📊 Resource Footprint (baseline):** Low to moderate CPU usage, low memory usage
  - **🔒 Security & Tuning Flags:** Configurable sensitivity, energy threshold, detection cooldown

---
### 🧠 AGENT PROFILE: StreamingLanguageAnalyzer
- **Main Class:** `StreamingLanguageAnalyzer` (`main_pc_code/agents/streaming_language_analyzer.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Analyzes real-time transcriptions for language detection (English, Tagalog, Taglish) and sentiment analysis.
- **🎯 Responsibilities:** 
  - Subscribe to transcriptions from StreamingSpeechRecognition
  - Detect language of spoken text
  - Identify Taglish (mixed English-Tagalog)
  - Analyze sentiment in Tagalog text
  - Publish language analysis results
  - Report metrics and health status
- **🔗 Interactions:** 
  - Subscribes to StreamingSpeechRecognition for transcriptions
  - Connects to TagaBERTa service for sentiment analysis
  - Connects to TranslationService for additional language support
  - Publishes language analysis via ZMQ PUB socket
  - Publishes health status via ZMQ PUB socket
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Multiple language detection methods:
    - FastText model (if available)
    - Tagalog word ratio analysis
    - Whisper language detection integration
    - TagaBERTa service integration
  - Maintains statistics on language distribution
  - Service discovery for finding dependencies
  - Secure ZMQ support
  - Fallback mechanisms when services unavailable
- **⚠️ Panganib:** 
  - May misclassify short phrases or uncommon words
  - Dependent on TagaBERTa service for sentiment analysis
  - Accuracy limited by lexicon size for ratio-based detection
  - May struggle with heavy code-switching
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 5597 (from config)
  - **🛰️ Port:** Default 5577 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `SECURE_ZMQ`, `PC2_IP`
  - **📑 Sample Request:** N/A (subscribes to transcriptions, publishes analysis)
  - **📊 Resource Footprint (baseline):** Low to moderate CPU usage, moderate memory usage if using FastText model
  - **🔒 Security & Tuning Flags:** Secure ZMQ optional, configurable lexicon for Tagalog detection

---
### 🧠 AGENT PROFILE: ProactiveAgent
- **Main Class:** `ProactiveAgent` (`main_pc_code/agents/proactive.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Provides proactive suggestions and reminders to users.
- **🎯 Responsibilities:** 
  - Check and announce reminders
  - Generate contextual suggestions
  - Track active users
  - Publish proactive messages
- **🔗 Interactions:** 
  - Publishes messages via ZMQ PUB socket
  - Reads user profiles from file system
- **🧬 Technical Deep Dive:** 
  - Periodic checking of reminders
  - Time-based contextual suggestions
  - User profile management
  - JSON-based data storage
- **⚠️ Panganib:** 
  - Relies on file system for user profiles
  - Limited user detection capabilities
  - Basic contextual awareness
- **📡 Communication Details:** 
  - **🔌 Health Port:** Not explicitly set
  - **🛰️ Port:** Inherited from BaseAgent (not explicitly set)
  - **🔧 Environment Variables:** `RESPONDER_HOST`
  - **📑 Sample Request:** N/A (publishes proactive messages as JSON)
  - **📊 Resource Footprint (baseline):** Very low CPU and memory usage
  - **🔒 Security & Tuning Flags:** None explicitly defined

---

### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|----------------|
| StreamingAudioCapture | ✓ | |
| FusedAudioPreprocessor | ✓ | |
| StreamingInterrupt | ✓ | |
| StreamingSpeechRecognition | ✓ | |
| UltimateTTSAgent | ✓ | |
| WakeWordDetector | ✓ | |
| StreamingLanguageAnalyzer | ✓ | |
| ProactiveAgent | ✓ | |

