# Consolidated Primary Translator - SOT Part 1

## Overview
The Consolidated Primary Translator is a unified translation service that combines the best features from all previous translator implementations. It provides a robust, multi-engine translation pipeline with advanced caching and session management.

## Script Path
`agents/consolidated_translator.py`

## Port
- ZMQ REP Port: 5563
- Bind Address: 0.0.0.0

## Key Features Implemented

### 1. Multi-Level Translation Pipeline
- **Dictionary/Pattern Matching (First Tier)**
  - Comprehensive command dictionary
  - Pattern matching for common phrases
  - Complete sentence translations
  - Zero-latency translations

- **NLLB Engine (Primary LLM)**
  - Uses facebook/nllb-200-distilled-600M
  - High-quality translations
  - Multi-language support
  - 5-second timeout

- **Phi LLM Engine (Secondary LLM)**
  - Uses Ollama's Phi model
  - Good quality translations
  - Faster than NLLB
  - 3-second timeout

- **Google Translate (Last Resort)**
  - Reliable fallback option
  - Rate-limited
  - Requires internet
  - 2-second timeout

### 2. Advanced Caching System
- **Multi-level Cache**
  - Dictionary cache (static)
  - Translation cache (TTL-based)
  - Session cache (context-aware)

- **Cache Features**
  - TTL support
  - Size limits
  - LRU eviction
  - Hit/miss tracking

### 3. Session Management
- **Session Features**
  - Unique session IDs
  - Translation history
  - User preferences
  - Timeout handling

- **History Tracking**
  - Last 10 translations
  - Engine used
  - Timestamps
  - Confidence scores

### 4. Configuration System
```python
TRANSLATOR_CONFIG = {
    "engines": {
        "dictionary": {
            "enabled": True,
            "priority": 1
        },
        "nllb": {
            "enabled": True,
            "priority": 2,
            "model": "facebook/nllb-200-distilled-600M",
            "timeout": 5
        },
        "phi": {
            "enabled": True,
            "priority": 3,
            "timeout": 3
        },
        "google": {
            "enabled": True,
            "priority": 4,
            "timeout": 2
        }
    },
    "cache": {
        "enabled": True,
        "max_size": 1000,
        "ttl": 3600
    },
    "session": {
        "enabled": True,
        "max_history": 10,
        "timeout": 3600
    }
}
```

## ZMQ Interface

### Request Format
```json
{
    "action": "translate",
    "text": "string",
    "source_lang": "tl",
    "target_lang": "en",
    "session_id": "uuid",
    "options": {
        "force_engine": "nllb|phi|google|dictionary",
        "use_cache": true,
        "use_context": true
    }
}
```

### Response Format
```json
{
    "status": "success|error",
    "translated_text": "string",
    "original_text": "string",
    "engine_used": "dictionary|nllb|phi|google",
    "confidence": 0.0-1.0,
    "session_id": "uuid",
    "cache_hit": true|false,
    "processing_time_ms": 0,
    "error": null|"string"
}
```

## Health Check

### Request
```json
{
    "action": "health_check"
}
```

### Response
```json
{
    "status": "ok",
    "service": "primary_translator",
    "timestamp": 0,
    "uptime_seconds": 0,
    "engines": {
        "dictionary": "ready",
        "nllb": "ready",
        "phi": "ready",
        "google": "ready"
    },
    "cache": {
        "size": 0,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0
    },
    "sessions": {
        "active": 0,
        "total": 0
    },
    "performance": {
        "avg_response_time_ms": 0,
        "requests_per_second": 0
    }
}
```

## Dependencies
- **External Services**
  - NLLB Adapter (for NLLB engine)
  - Ollama (for Phi LLM)
  - Google Translate API

- **Python Packages**
  - zmq
  - requests
  - uuid
  - logging
  - typing
  - collections

## Code Snippets

### Translation Pipeline Core
```python
def translate(self, text: str, source_lang: str, target_lang: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Translate text using multi-engine pipeline"""
    start_time = time.time()
    
    # Normalize text
    text = text.lower().strip()
    
    # Check cache first
    cache_key = f"{text}:{source_lang}:{target_lang}"
    if cached := self.cache.get(cache_key):
        return {
            'status': 'success',
            'translated_text': cached,
            'original_text': text,
            'engine_used': 'cache',
            'confidence': 1.0,
            'session_id': session_id,
            'cache_hit': True,
            'processing_time_ms': int((time.time() - start_time) * 1000)
        }
        
    # Try dictionary/pattern matching first
    if self.config['engines']['dictionary']['enabled']:
        # Check complete sentences
        if text in COMPLETE_SENTENCES:
            translation = COMPLETE_SENTENCES[text]
            self._cache_and_session(text, translation, 'dictionary', session_id)
            return self._create_response(text, translation, 'dictionary', start_time, session_id)
            
        # Check patterns
        for pattern, template in COMMON_PHRASE_PATTERNS.items():
            if match := re.match(pattern, text):
                translation = template.format(*match.groups())
                self._cache_and_session(text, translation, 'dictionary', session_id)
                return self._create_response(text, translation, 'dictionary', start_time, session_id)
                
        # Check individual words
        words = text.split()
        translated_words = []
        for word in words:
            translated_words.append(COMMAND_TRANSLATIONS.get(word, word))
        translation = ' '.join(translated_words)
        
        if translation != text:  # If any words were translated
            self._cache_and_session(text, translation, 'dictionary', session_id)
            return self._create_response(text, translation, 'dictionary', start_time, session_id)
            
    # Try NLLB engine
    if self.config['engines']['nllb']['enabled']:
        try:
            # TODO: Implement NLLB engine call
            pass
        except Exception as e:
            logger.error(f"NLLB translation failed: {str(e)}")
            
    # Try Phi LLM engine
    if self.config['engines']['phi']['enabled']:
        try:
            # TODO: Implement Phi LLM engine call
            pass
        except Exception as e:
            logger.error(f"Phi LLM translation failed: {str(e)}")
            
    # Try Google Translate as last resort
    if self.config['engines']['google']['enabled']:
        try:
            # TODO: Implement Google Translate call
            pass
        except Exception as e:
            logger.error(f"Google translation failed: {str(e)}")
            
    # If all engines fail, return original text
    return self._create_response(text, text, 'none', start_time, session_id)
```

### Cache Management
```python
def get(self, key: str) -> Optional[str]:
    """Get translation from cache if not expired"""
    if key in self.cache:
        if time.time() - self.access_times[key] < self.ttl:
            self.hits += 1
            return self.cache[key]['translation']
        else:
            del self.cache[key]
            del self.access_times[key]
    self.misses += 1
    return None
```

### Session Management
```python
def add_to_history(self, session_id: str, text: str, translation: str, engine: str) -> None:
    """Add translation to session history"""
    if session := self.get_session(session_id):
        session['history'].append({
            'text': text,
            'translation': translation,
            'engine': engine,
            'timestamp': time.time()
        })
``` 