# Group: Audio Processing and Speech Services

Ang mga agents sa dating audio_processing group ay nahahati na sa dalawang bagong grupo: **speech_services** at **audio_interface**. Ito ang mga agents na kabilang sa mga grupong ito:

## Speech Services Group

Ang mga agents na ito ay nagbibigay ng speech-to-text at text-to-speech functionality gamit ang ModelManagerAgent:

---

### 🧠 AGENT PROFILE: STTService
- **Main Class:** `STTService` (`main_pc_code/services/stt_service.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Lightweight wrapper that receives audio data and uses model_client to request transcription from ModelManagerAgent.
- **🎯 Responsibilities:** 
  - Receive audio data from StreamingSpeechRecognition
  - Use model_client to request transcription from ModelManagerAgent
  - Handle audio preprocessing and format conversion
  - Support multiple languages
  - Report errors to error bus
- **🔗 Interactions:** 
  - Receives requests from StreamingSpeechRecognition
  - Connects to ModelManagerAgent via model_client
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Lightweight wrapper around model_client
  - Audio normalization and preprocessing
  - Service discovery for finding dependencies
  - Error handling and reporting
- **⚠️ Panganib:** 
  - Dependent on ModelManagerAgent availability
  - May experience latency if ModelManagerAgent is busy
  - Audio format conversion may introduce artifacts
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6800 (from config)
  - **🛰️ Port:** Default 5800 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`
  - **📑 Sample Request:**
    ```json
    {
      "action": "transcribe",
      "audio_data": [0.1, 0.2, ...],
      "language": "en"
    }
    ```
  - **📊 Resource Footprint (baseline):** Low CPU and memory usage (model loading handled by ModelManagerAgent)
  - **🔒 Security & Tuning Flags:** None explicitly defined

---
### 🧠 AGENT PROFILE: TTSService
- **Main Class:** `TTSService` (`main_pc_code/services/tts_service.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Lightweight wrapper that receives text and uses model_client to request speech synthesis from ModelManagerAgent.
- **🎯 Responsibilities:** 
  - Receive text from StreamingTTSAgent
  - Use model_client to request speech synthesis from ModelManagerAgent
  - Handle audio streaming and format conversion
  - Support voice customization options
  - Cache generated audio for repeated phrases
- **🔗 Interactions:** 
  - Receives requests from StreamingTTSAgent
  - Connects to ModelManagerAgent via model_client
  - Subscribes to interrupt handler
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Lightweight wrapper around model_client
  - Audio caching with LRU eviction policy
  - Service discovery for finding dependencies
  - Background threads for audio playback
  - Error handling and reporting
- **⚠️ Panganib:** 
  - Dependent on ModelManagerAgent availability
  - May experience latency if ModelManagerAgent is busy
  - Cache can consume significant memory if not managed
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6801 (from config)
  - **🛰️ Port:** Default 5801 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`
  - **📑 Sample Request:**
    ```json
    {
      "action": "speak",
      "text": "Hello, world!",
      "language": "en",
      "voice_sample": "/path/to/voice.wav",
      "temperature": 0.7,
      "speed": 1.0,
      "volume": 1.0
    }
    ```
  - **📊 Resource Footprint (baseline):** Low CPU and memory usage (model loading handled by ModelManagerAgent)
  - **🔒 Security & Tuning Flags:** None explicitly defined

## Audio Interface Group

Ang mga agents na ito ay nag-handle ng real-time audio capture, processing, at streaming:

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
  - Connects to STTService for transcription
  - Connects to RequestCoordinator
  - Publishes transcriptions via ZMQ PUB socket
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Delegates transcription to STTService
  - Dynamic resource management based on system load
  - Language detection for multilingual support
  - Wake word and VAD integration for better accuracy
  - Noise reduction for improved recognition
- **⚠️ Panganib:** 
  - Dependent on STTService availability
  - May struggle with accented speech or background noise
  - Dependent on multiple services being available
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6582 (from config)
  - **🛰️ Port:** Default 5707 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`, `SECURE_ZMQ`
  - **📑 Sample Request:** N/A (subscribes to audio, publishes transcriptions)
  - **📊 Resource Footprint (baseline):** Moderate CPU and memory usage (model loading handled by STTService)
  - **🔒 Security & Tuning Flags:** Dynamic resource management, configurable batch size and quantization

---
### 🧠 AGENT PROFILE: StreamingTTSAgent
- **Main Class:** `UltimateTTSAgent` (`main_pc_code/agents/streaming_tts_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Provides advanced text-to-speech capabilities with a 4-tier fallback system.
- **🎯 Responsibilities:** 
  - Convert text to speech using TTS Service (primary)
  - Provide fallbacks: Windows SAPI, pyttsx3, console print
  - Stream audio chunks for real-time playback
  - Support voice customization and emotions
  - Handle interruptions
- **🔗 Interactions:** 
  - Receives TTS requests via ZMQ REP socket
  - Connects to TTSService for speech synthesis
  - Connects to UnifiedSystemAgent for health monitoring
  - Subscribes to interrupt handler
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Delegates speech synthesis to TTSService
  - Audio cache with LRU eviction policy
  - Background threads for initialization, playback, health monitoring
  - Sentence splitting for more natural speech
  - Voice customization with speaker samples
- **⚠️ Panganib:** 
  - Dependent on TTSService availability
  - May have high latency for first-time speech
  - Cache can consume significant memory if not managed
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (default **5563**) – inherited & should be bound
  - **🛰️ Port:** Default 5562 (from config)
  - **🔧 Environment Variables:** `SECURE_ZMQ`, `BIND_ADDRESS`, `TETEY_VOICE_PATH`, `PC2_IP`
  - **📑 Sample Request:** 
    ```json
    {
      "text": "Hello, world!",
      "emotion": "joy",
      "speed": 1.0
    }
    ```
  - **📊 Resource Footprint (baseline):** Moderate CPU usage during speech synthesis, low memory usage (model loading handled by TTSService)
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
  - **📊 Resource Footprint (baseline):** Low to moderate CPU usage, moderate memory usage for language models
  - **🔒 Security & Tuning Flags:** Configurable language detection thresholds, secure ZMQ support

---
### 🧠 AGENT PROFILE: ProactiveAgent
- **Main Class:** `ProactiveAgent` (`main_pc_code/agents/ProactiveAgent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Monitors user behavior and context to proactively suggest actions or information.
- **🎯 Responsibilities:** 
  - Monitor user activity patterns
  - Analyze context from various sources
  - Generate proactive suggestions
  - Trigger notifications at appropriate times
  - Integrate with memory system
- **🔗 Interactions:** 
  - Connects to RequestCoordinator
  - Connects to MemoryClient
  - Publishes suggestions via ZMQ PUB socket
  - Publishes health status via ZMQ PUB socket
  - Publishes errors to error bus
- **🧬 Technical Deep Dive:** 
  - Uses LLM for context understanding
  - Pattern recognition for user behavior
  - Time-based triggers for suggestions
  - Integration with system events
  - Background threads for monitoring and suggestion generation
- **⚠️ Panganib:** 
  - May generate irrelevant suggestions
  - Privacy concerns with behavior monitoring
  - Potential for notification fatigue
  - Resource usage during context analysis
- **📡 Communication Details:** 
  - **🔌 Health Port:** Default 6624 (from config)
  - **🛰️ Port:** Default 5624 (from config)
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`
  - **📑 Sample Request:** N/A (generates suggestions proactively)
  - **📊 Resource Footprint (baseline):** Moderate CPU usage, moderate memory usage
  - **🔒 Security & Tuning Flags:** Configurable suggestion threshold, privacy settings

---

### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| AudioCapture | ✓ | |
| FusedAudioPreprocessor | ✓ | |
| StreamingInterruptHandler | ✓ | |
| STTService | ✓ | |
| StreamingSpeechRecognition | ✓ | |
| TTSService | ✓ | |
| StreamingTTSAgent | ✓ | |
| WakeWordDetector | ✓ | |
| StreamingLanguageAnalyzer | ✓ | |
| ProactiveAgent | ✓ | |

---

### Container Grouping Updates

Ang dating **audio_processing** group ay nahahati na sa dalawang bagong grupo para sa mas mahusay na resource management at containerization:

1. **speech_services** - Lightweight wrappers para sa ModelManagerAgent na nagbibigay ng speech-to-text at text-to-speech functionality:
   - STTService
   - TTSService

2. **audio_interface** - Real-time audio capture, processing, at streaming agents:
   - AudioCapture
   - FusedAudioPreprocessor
   - StreamingInterruptHandler
   - StreamingSpeechRecognition
   - StreamingTTSAgent
   - WakeWordDetector
   - StreamingLanguageAnalyzer
   - ProactiveAgent

Ang pagbabagong ito ay nagbibigay ng mga sumusunod na benepisyo:
- Mas mahusay na resource allocation - ang speech services ay maaaring i-scale nang hiwalay mula sa audio interface
- Mas mababang network overhead - ang mga closely related agents ay nasa parehong container
- Mas malinaw na separation of concerns - ang model inference ay hiwalay sa audio streaming
- Mas mahusay na fault isolation - ang isang problema sa audio capture ay hindi direktang makakaapekto sa speech processing services

