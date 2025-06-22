# Voice Assistant System Agent Documentation

## Current Integration Status

### Active Components
1. **Main Translator (Port 5563)**
   - ✅ INTEGRATED
   - Running on PC2
   - Connected through redundant ZMQ bridge
   - Has fallback mechanisms

2. **Translation Engines**
   - ✅ NLLB (Neural Translation) - INTEGRATED
   - ✅ Phi-3 (Local Model) - INTEGRATED
   - ✅ Google Translate (Fallback) - INTEGRATED
   - ✅ Dictionary-based (Fast Fallback) - INTEGRATED

3. **Bridge System**
   - ✅ Redundant ZMQ Bridge - INTEGRATED
   - Active-Passive configuration
   - Automatic failover
   - Health monitoring

## Main PC Agents

### 1. Audio Processing Agents

#### Streaming Audio Capture (Port 5555)
- **Status:** ✅ ACTIVE
- **File:** `streaming_audio_capture.py`
- **Purpose:** Captures raw microphone audio and publishes it via ZMQ
- **Key Features:**
  - Real-time PCM stream
  - Device selection
  - Timestamping
  - Health monitoring
- **Integration Points:**
  - PUB socket: `tcp://*:5555`
  - Health status: `tcp://*:5556`
- **Dependencies:** None
- **Notes:** Root of the audio pipeline

#### Noise Reduction Agent (Port 5556)
- **Status:** ✅ ACTIVE
- **File:** `noise_reduction_agent.py`
- **Purpose:** Cleans incoming audio frames
- **Key Features:**
  - RNNoise implementation
  - Spectral gating
  - Adaptive noise profile
  - Real-time processing
- **Integration Points:**
  - Subscribes: `tcp://localhost:5555`
  - PUB socket: `tcp://*:5556`
  - Health status: `tcp://*:5557`
- **Dependencies:** `streaming_audio_capture.py`
- **Notes:** Builds noise profile on demand

#### Speech Recognition (Port 5557)
- **Status:** ✅ ACTIVE
- **File:** `speech_recognition_agent.py`
- **Purpose:** Speech to text conversion
- **Key Features:**
  - Whisper model integration
  - Chunked inference
  - Language auto-detection
  - Real-time transcription
- **Integration Points:**
  - Subscribes: `tcp://localhost:5556`
  - PUB socket: `tcp://*:5557`
  - Health: `tcp://*:5558`
- **Dependencies:** `noise_reduction_agent.py`

### 2. Language Processing Agents

#### Language & Translation Coordinator (Port 5558)
- **Status:** ✅ ACTIVE
- **File:** `language_and_translation_coordinator.py`
- **Purpose:** Language processing and translation
- **Key Features:**
  - Language identification
  - Translation routing
  - Context management
  - Multi-language support
- **Integration Points:**
  - Subscribes: `tcp://localhost:5557`
  - PUB socket: `tcp://*:5558`
- **Dependencies:** `speech_recognition_agent.py`

#### Intent Recognition (Port 5559)
- **Status:** ✅ ACTIVE
- **File:** `intent_recognition_agent.py`
- **Purpose:** Intent classification and task routing
- **Features:**
  - Intent classification
  - Multi-language support (English & Filipino)
  - Confidence scoring
  - Entity extraction
  - Pattern matching
  - Intent caching
  - Performance metrics tracking

#### Intention Validator (Port 5627)
- **File:** `IntentionValidatorAgent.py`
- **Purpose:** Validates user intentions and commands
- **Features:**
  - Command structure validation
  - Command history tracking
  - Risk level assessment
  - User profile validation
  - SQLite database for validation history
  - Sensitive command detection
  - Pattern-based validation
  - Real-time validation logging

#### Code Generation Intent Handler (Port 5556)
- **File:** `agents/intent_handlers/code_generation_intent.py`
- **Purpose:** Handles code generation intents
- **Features:**
  - Code generation intent detection
  - Multi-language support (English & Filipino)
  - Language detection
  - Code prompt extraction
  - Model Manager Agent integration
  - Request tracking with UUIDs
  - Connection management
  - Error handling and recovery

#### Intent Processing Pipeline
1. **Intent Detection**
   - Text input received
   - Pattern matching against intent triggers
   - Language detection
   - Entity extraction
   - Confidence scoring

2. **Intent Validation**
   - Command structure validation
   - User profile verification
   - Risk assessment
   - History checking
   - Pattern validation

3. **Intent Processing**
   - Intent classification
   - Task routing
   - Response generation
   - Performance tracking

4. **Specialized Handlers**
   - Code Generation Handler
   - Command Handler
   - Query Handler
   - Conversation Handler

#### Message Types
1. **Intent Detection Request**
```json
{
    "action": "detect_intent",
    "text": "string",
    "language": "string",
    "context": "object"
}
```

2. **Intent Validation Request**
```json
{
    "action": "validate_command",
    "command": "string",
    "parameters": "object",
    "user_id": "string",
    "profile": "string"
}
```

3. **Code Generation Request**
```json
{
    "action": "generate_code",
    "prompt": "string",
    "language": "string",
    "request_id": "string"
}
```

4. **Validation History Request**
```json
{
    "action": "get_validation_history",
    "user_id": "string",
    "profile": "string",
    "limit": "number"
}
```

#### Integration Points
1. **Model Manager Agent**
   - Port: 5556
   - Purpose: Code generation requests
   - Protocol: ZMQ REQ/REP

2. **Language & Translation**
   - Port: 5558
   - Purpose: Multi-language support
   - Protocol: ZMQ PUB/SUB

3. **Security Policy Agent**
   - Port: 5560
   - Purpose: Security validation
   - Protocol: ZMQ REQ/REP

4. **Error Pattern Memory**
   - Port: 5611
   - Purpose: Error tracking
   - Protocol: ZMQ PUB/SUB

#### Performance Metrics
1. **Intent Recognition**
   - Total requests
   - Recognition errors
   - Error rate
   - Average processing time

2. **Validation**
   - Validation success rate
   - Risk level distribution
   - Command frequency
   - Failure patterns

3. **Code Generation**
   - Success rate
   - Language distribution
   - Response time
   - Error types

#### Error Handling
1. **Connection Errors**
   - Automatic reconnection
   - Timeout handling
   - Error logging
   - State recovery

2. **Validation Errors**
   - Detailed error messages
   - Error categorization
   - History tracking
   - Pattern analysis

3. **Processing Errors**
   - Graceful degradation
   - Error reporting
   - State preservation
   - Recovery procedures

## PC2 Agents

### 1. Translation System

#### Main Translator (Port 5563)
- **Status:** ✅ ACTIVE
- **File:** `consolidated_translator.py`
- **Purpose:** Primary translation service
- **Key Features:**
  - Multi-engine translation pipeline
  - Language detection with confidence scoring
  - Fallback mechanisms
  - Translation caching
  - Quality control
- **Engines:**
  1. NLLB (Neural Translation) - ✅ ACTIVE
  2. Phi-3 (Local Model) - ✅ ACTIVE
  3. Google Translate (Fallback) - ✅ ACTIVE
  4. Dictionary-based (Fast Fallback) - ✅ ACTIVE
- **Integration Points:**
  - REP socket: `tcp://*:5563`
  - Health monitoring
  - Translation operations

#### NLLB Adapter (Port 5581)
- **Status:** ✅ ACTIVE
- **File:** `nllb_adapter.py`
- **Purpose:** Neural translation model
- **Key Features:**
  - High-quality translation
  - Multiple language pairs
  - Context awareness
  - Quality metrics
- **Integration Points:**
  - REP socket: `tcp://*:5581`
  - Health monitoring
  - Translation operations

### 2. Memory System

#### Unified Memory (Port 5570)
- **Status:** ✅ ACTIVE
- **File:** `unified_memory_agent.py`
- **Purpose:** Memory management and reasoning
- **Key Features:**
  - Memory query processing
  - Context management
  - Reasoning capabilities
  - Memory operations
- **Integration Points:**
  - REP socket: `tcp://*:5570`
  - Health monitoring
  - Memory operations

#### Memory Manager (Port 5571)
- **Status:** ✅ ACTIVE
- **File:** `memory_manager_agent.py`
- **Purpose:** Memory operations and management
- **Key Features:**
  - Memory operations
  - Context management
  - Data persistence
  - Query optimization
- **Integration Points:**
  - REP socket: `tcp://*:5571`
  - Health monitoring
  - Memory operations

### 3. System Management

#### System Monitor (Port 5575)
- **Status:** ✅ ACTIVE
- **File:** `system_monitor_agent.py`
- **Purpose:** System health monitoring
- **Key Features:**
  - Health monitoring
  - Performance tracking
  - Resource management
  - Service status
- **Integration Points:**
  - REP socket: `tcp://*:5575`
  - Health monitoring
  - System management

#### Health Check (Port 5576)
- **Status:** ✅ ACTIVE
- **File:** `health_check_agent.py`
- **Purpose:** Service health verification
- **Key Features:**
  - Service health checks
  - Dependency verification
  - Status reporting
  - Recovery coordination
- **Integration Points:**
  - REP socket: `tcp://*:5576`
  - Health monitoring
  - System management

## Cognitive & Emotional Components

### Personality Engine (Port 5571)

- **File:** `personality_engine.py`
- **Purpose:** Manages personality traits and response styling
- **Features:**
  - Personality trait management
  - Response style adaptation
  - Emotional state integration
  - Multi-language support
  - LLM-based response styling
  - Real-time emotion monitoring
  - Health monitoring
  - Performance metrics

### Emotion Engine (Port 5570)

- **File:** `emotion_engine.py`
- **Purpose:** Manages emotional states and processing
- **Features:**
  - Emotional state tracking
  - Sentiment analysis
  - Intensity measurement
  - Emotion combination mapping
  - Real-time state broadcasting
  - Threshold-based classification
  - Health monitoring
  - State persistence

### Learning Manager (Port 5569)

- **File:** `learning_manager.py`
- **Purpose:** Coordinates learning operations
- **Features:**
  - Conversation analysis
  - Knowledge extraction
  - Long-term memory integration
  - Short-term context management
  - LLM-based learning
  - Multi-agent coordination
  - Health monitoring
  - Performance tracking

### 3. MetaCognition Agent (Port 5630)
- **Status:** ✅ ENHANCED & ACTIVE
- **File:** `MetaCognitionAgent.py`
- **Purpose:** Advanced learning analysis, memory optimization, and system monitoring
- **Key Features:**
  - Learning Analysis
    - Pattern mining and trend analysis
    - Knowledge graph maintenance
    - Performance metrics tracking
    - Self-assessment capabilities
  - Memory Optimization
    - Dynamic cache management
    - Memory usage monitoring
    - Automatic garbage collection
    - Resource optimization
  - Monitoring Systems
    - Real-time system metrics
    - Alert thresholds
    - Performance tracking
    - Error rate monitoring
- **Integration Points:**
  - Main REP socket: `tcp://*:5630`
  - ChainOfThought SUB: `tcp://localhost:5600`
  - ModelVoting SUB: `tcp://localhost:5601`
  - KnowledgeBase REQ: `tcp://localhost:5565`
  - Coordinator REQ: `tcp://localhost:5590`
- **Database Tables:**
  - thought_traces
  - reasoning_steps
  - learning_metrics
  - knowledge_graph
  - memory_stats
  - system_metrics
- **Dependencies:**
  - numpy
  - scikit-learn
  - torch
  - psutil
  - pyzmq
  - sqlite3
- **Message Types:**
```json
{
    "action": "analyze_learning",
    "data": {
        "confidence": "float",
        "performance": "float",
        "context": "object"
    }
}
```
```json
{
    "action": "optimize_memory",
    "threshold": "float",
    "cache_size": "integer"
}
```
```json
{
    "action": "monitor_system",
    "metrics": {
        "cpu_usage": "float",
        "memory_usage": "float",
        "response_time": "float",
        "error_rate": "float"
    }
}
```
- **Performance Metrics:**
  - Learning rate trends
  - Memory optimization count
  - System resource usage
  - Error rate tracking
- **Error Handling:**
  - Automatic recovery
  - State preservation
  - Error logging
  - Alert generation

### 4. Future Enhancements
1. **Learning Analysis**
   - Implement sequence mining for pattern detection
   - Add anomaly detection for unusual patterns
   - Enhance self-assessment capabilities
   - Add learning visualization tools

2. **Memory Optimization**
   - Implement adaptive cache sizing
   - Add memory usage visualization
   - Enhance garbage collection tuning
   - Add memory compression strategies

3. **Monitoring Systems**
   - Add real-time web dashboard
   - Implement notification system
   - Add historical analytics
   - Enhance alert system

4. **Integration & API**
   - Add REST API endpoints
   - Implement plugin system
   - Add external monitoring hooks
   - Enhance data export capabilities

5. **Testing & Validation**
   - Add unit tests
   - Implement integration tests
   - Add performance benchmarks
   - Enhance error recovery

### Empathy Agent (Port 5585)

- **File:** `EmpathyAgent.py`
- **Purpose:** Manages empathetic responses
- **Features:**
  - Emotional understanding
  - Response adaptation
  - Context awareness
  - User state tracking
  - Multi-modal empathy
  - Health monitoring
  - Performance metrics

### Mood Tracker (Port 5586)

- **File:** `mood_tracker_agent.py`
- **Purpose:** Tracks and analyzes user mood
- **Features:**
  - Mood state tracking
  - Pattern recognition
  - Trend analysis
  - Response adaptation
  - Health monitoring
  - Performance metrics

### Human Awareness Agent (Port 5587)

- **File:** `HumanAwarenessAgent.py`
- **Purpose:** Manages human interaction awareness
- **Features:**
  - Interaction pattern recognition
  - User preference learning
  - Context adaptation
  - Response personalization
  - Health monitoring
  - Performance tracking

### Dynamic Identity Agent (Port 5588)

- **File:** `DynamicIdentityAgent.py`
- **Purpose:** Manages dynamic identity adaptation
- **Features:**
  - Identity state management
  - Context-based adaptation
  - User preference learning
  - Response personalization
  - Health monitoring
  - Performance metrics

### Tutor Agent (Port 5575)

- **File:** `tutor_agent.py`
- **Purpose:** Manages adaptive learning and tutoring
- **Features:**
  - Adaptive learning engine
  - Student profile management
  - Progress tracking
  - Performance analysis
  - Personalized feedback
  - Learning style adaptation
  - Difficulty adjustment
  - Parent dashboard
  - Session management
  - Multi-subject support
  - Real-time assessment
  - Health monitoring
  - Performance metrics

### Adaptive Learning Components

1. **Student Profile Management**
   - Learning style detection
   - Performance history
   - Mastery levels
   - Weak/strong areas
   - Interest tracking
   - Age/grade adaptation

2. **Progress Tracking**
   - Accuracy metrics
   - Speed metrics
   - Confidence scoring
   - Completion time
   - Mistake analysis
   - Strength identification
   - Trend analysis
   - Recommendation generation

3. **Learning Style Analysis**
   - Visual learning
   - Auditory learning
   - Kinesthetic learning
   - Balanced approach
   - Style adaptation
   - Content customization

4. **Difficulty Adjustment**
   - Neural network-based prediction
   - Performance-based scaling
   - Prerequisite checking
   - Age-appropriate content
   - Progressive difficulty
   - Mastery-based advancement

### Integration Points

1. **Personality & Emotion Integration**
   - Personality Engine → Emotion Engine (Port 5580)
   - Emotion Engine → Personality Engine (Port 5571)
   - Both → Coordinator Agent (Port 5590)

2. **Learning & Memory Integration**
   - Learning Manager → Memory Manager (Port 5572)
   - Learning Manager → Knowledge Base (Port 5565)
   - Learning Manager → Coordinator Agent (Port 5590)

3. **MetaCognition Integration**
   - MetaCognition → Chain of Thought (Port 5600)
   - MetaCognition → Model Voting (Port 5601)
   - MetaCognition → Knowledge Base (Port 5565)
   - MetaCognition → Coordinator Agent (Port 5590)

4. **Empathy & Mood Integration**
   - Empathy Agent → Emotion Engine (Port 5580)
   - Mood Tracker → Emotion Engine (Port 5580)
   - Both → Coordinator Agent (Port 5590)

5. **Tutor & Learning Integration**
   - Tutor Agent → Learning Manager (Port 5569)
   - Tutor Agent → Knowledge Base (Port 5565)
   - Tutor Agent → Coordinator Agent (Port 5590)

6. **Tutor & Emotion Integration**
   - Tutor Agent → Emotion Engine (Port 5580)
   - Tutor Agent → Personality Engine (Port 5571)
   - Tutor Agent → Empathy Agent (Port 5585)

7. **Tutor & Memory Integration**
   - Tutor Agent → Memory Manager (Port 5572)
   - Tutor Agent → Session Memory (Port 5573)
   - Tutor Agent → Progress Database

### Message Types

1. **Emotional State Update**
```json
{
    "type": "emotional_state_update",
    "data": {
        "tone": "string",
        "sentiment": "float",
        "intensity": "float",
        "dominant_emotion": "string",
        "combined_emotion": "string",
        "timestamp": "float"
    }
}
```

2. **Personality Response Request**
```json
{
    "action": "generate_response_style",
    "base_response": "string",
    "user_query": "string",
    "use_llm": "boolean"
}
```

3. **Learning Request**
```json
{
    "action": "analyze_and_learn",
    "conversation": "string|array",
    "context": "object"
}
```

4. **MetaCognition Request**
```json
{
    "action": "analyze_task_outcome",
    "task_id": "string",
    "outcome": "string",
    "details": "object"
}
```

5. **Tutor Session Request**
```json
{
    "action": "start_session",
    "user_id": "string",
    "subject": "string",
    "difficulty": "float",
    "learning_style": "string"
}
```

6. **Lesson Request**
```json
{
    "action": "get_lesson",
    "subject": "string",
    "difficulty": "float",
    "user_profile": {
        "student_id": "string",
        "learning_style": "string",
        "mastery_levels": "object",
        "weak_areas": "array",
        "strong_areas": "array"
    }
}
```

7. **Performance Update**
```json
{
    "action": "update_progress",
    "student_id": "string",
    "lesson_id": "string",
    "performance": {
        "accuracy": "float",
        "speed": "float",
        "confidence": "float",
        "completion_time": "float",
        "mistakes": "array",
        "strengths": "array",
        "areas_for_improvement": "array"
    }
}
```

8. **Parent Dashboard Update**
```json
{
    "action": "update_dashboard",
    "student_id": "string",
    "progress_data": {
        "overall_progress": "object",
        "trends": "object",
        "weak_areas": "array",
        "strong_areas": "array",
        "recommendations": "array"
    }
}
```

### Performance Metrics

1. **Emotional Processing**
   - Response time
   - Accuracy
   - State transition frequency
   - Error rate

2. **Personality Adaptation**
   - Style adaptation success
   - Response appropriateness
   - User satisfaction
   - Error rate

3. **Learning Performance**
   - Knowledge extraction rate
   - Memory integration success
   - Context retention
   - Error rate

4. **MetaCognition Metrics**
   - Reasoning step count
   - Confidence levels
   - Reflection quality
   - Task success rate

5. **Learning Performance**
   - Accuracy rates
   - Speed metrics
   - Confidence levels
   - Completion times
   - Mistake patterns
   - Progress trends

6. **Adaptation Performance**
   - Style detection accuracy
   - Difficulty adjustment success
   - Content customization effectiveness
   - Learning path optimization

7. **Session Performance**
   - Session duration
   - Engagement levels
   - Completion rates
   - Feedback effectiveness
   - Error recovery

### Error Handling

1. **Emotional State Errors**
   - State recovery
   - Default state fallback
   - Error logging
   - State persistence

2. **Personality Errors**
   - Style fallback
   - Default traits
   - Error logging
   - State recovery

3. **Learning Errors**
   - Knowledge validation
   - Memory recovery
   - Error logging
   - State preservation

4. **MetaCognition Errors**
   - Trace recovery
   - Default reasoning
   - Error logging
   - State preservation

5. **Learning Errors**
   - Content validation
   - Progress recovery
   - Session preservation
   - State management

6. **Adaptation Errors**
   - Style detection fallback
   - Difficulty adjustment limits
   - Content customization bounds
   - Learning path recovery

7. **Session Errors**
   - Session recovery
   - State preservation
   - Progress backup
   - Error logging

## Integration Status & Plan

### Current Integration Status

✅ INTEGRATED COMPONENTS:
1. Personality Engine (Port 5571)
   - Active and running
   - Connected to Emotion Engine and Tutor Agent
   - Health monitoring active
   - Performance metrics tracking

2. Emotion Engine (Port 5570)
   - Active and integrated
   - Connected to Personality Engine and Mood Tracker
   - Emotional state management active
   - Response generation working

3. Learning Manager (Port 5569)
   - Active and integrated
   - Connected to Memory Manager and Knowledge Base
   - Learning operations active
   - Progress tracking implemented

4. Empathy Agent (Port 5585)
   - Active and integrated
   - Connected to Emotion Engine and Tutor Agent
   - Empathy responses working
   - User interaction tracking

5. Mood Tracker (Port 5586)
   - Active and integrated
   - Connected to Emotion Engine
   - Mood analysis active
   - State persistence working

### Planned Integration

🔄 IN PROGRESS:

1. Human Awareness Agent (Port 5587)
   - Status: Partially Implemented
   - Components:
     * Window detection system
     * Tone analysis (TagaBERTa)
     * Media pose detection
   - Integration Points:
     * Emotion Engine (Port 5570)
     * Personality Engine (Port 5571)
     * Coordinator Agent (Port 5590)
   - Message Types:
```json
{
    "action": "awareness_update",
    "type": "window|tone|pose",
    "data": {
        "window_info": "object",
        "tone_analysis": "object",
        "pose_data": "object"
    }
}
```
   - Performance Metrics:
     * Detection accuracy
     * Response time
     * Context relevance
     * User engagement

2. MetaCognition Agent (Port 5630)
   - Status: Planning Phase
   - Components:
     * Learning analysis
     * Memory optimization
     * Cognitive load monitoring
   - Integration Points:
     * Learning Manager (Port 5569)
     * Memory Manager (Port 5572)
     * Coordinator Agent (Port 5590)
   - Message Types:
```json
{
    "action": "meta_cognition_request",
    "type": "analysis|reflection|optimization",
    "context": {
        "learning_state": "object",
        "memory_state": "object",
        "performance_metrics": "object"
    }
}
```
   - Performance Metrics:
     * Learning efficiency
     * Memory optimization
     * Cognitive load
     * Adaptation effectiveness

3. Dynamic Identity Agent (Port 5588)
   - Status: Planning Phase
   - Components:
     * Identity management
     * State persistence
     * Transition handling
   - Integration Points:
     * Personality Engine (Port 5571)
     * Emotion Engine (Port 5570)
     * Memory Manager (Port 5572)
   - Message Types:
```json
{
    "action": "identity_update",
    "type": "personality|emotion|preference",
    "data": {
        "current_state": "object",
        "target_state": "object",
        "transition_params": "object"
    }
}
```