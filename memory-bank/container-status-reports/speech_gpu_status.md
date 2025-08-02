# Speech GPU Group - Container Status Report
**Report Generated:** 2025-08-02 16:15:30

## Group Overview
- **Total Containers:** 10
- **Healthy:** 1
- **Problematic:** 9

## ✅ HEALTHY CONTAINERS

### redis_speech
- **Status:** Up 7 hours (healthy)
- **Ports:** 0.0.0.0:6387->6379/tcp
- **Issue:** None - Working correctly

## ❌ PROBLEMATIC CONTAINERS

### tts_service
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing sounddevice module
- **Error:** `ModuleNotFoundError: No module named 'sounddevice'`

**Logs:**
```
File "/app/main_pc_code/agents/streaming_tts_agent.py", line 37, in <module>
    import sounddevice as sd
ModuleNotFoundError: No module named 'sounddevice'
```

### wake_word_detector
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing pvporcupine module
- **Error:** `ModuleNotFoundError: No module named 'pvporcupine'`

**Logs:**
```
File "/app/main_pc_code/agents/wake_word_detector.py", line 15, in <module>
    import pvporcupine
ModuleNotFoundError: No module named 'pvporcupine'
```

### streaming_speech_recognition
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing noisereduce module
- **Error:** `ModuleNotFoundError: No module named 'noisereduce'`

**Logs:**
```
File "/app/main_pc_code/agents/streaming_speech_recognition.py", line 22, in <module>
    import noisereduce as nr
ModuleNotFoundError: No module named 'noisereduce'
```

### fused_audio_preprocessor
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing audio processing modules

### audio_capture
- **Status:** Exited (0) 7 hours ago
- **Issue:** Clean exit but not running

### streaming_language_analyzer
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing dependencies

### streaming_interrupt_handler
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing dependencies

### streaming_tts_agent
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing sounddevice module

### stt_service
- **Status:** Exited (1) 7 hours ago
- **Issue:** Missing speech recognition dependencies

## Root Cause Analysis
**Speech GPU group has MAJOR dependency issues:**

1. **Missing audio libraries:** sounddevice, pvporcupine, noisereduce
2. **Incomplete requirements.txt** - Missing specialized audio processing libraries
3. **Audio hardware dependencies** not properly handled in Docker

## Required Fixes
1. Update speech_gpu/requirements.txt with missing packages:
   - sounddevice
   - pvporcupine  
   - noisereduce
   - Additional audio processing libraries

2. Install system audio dependencies in Dockerfile
3. Handle audio hardware access in Docker environment

## Summary
Speech GPU group is 10% functional. Critical rebuild required with proper audio dependencies.
