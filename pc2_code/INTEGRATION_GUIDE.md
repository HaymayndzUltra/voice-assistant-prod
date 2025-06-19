# Phi-3 Translator Integration Guide

## New Translation Architecture

```
[Main PC Voice Pipeline] → [Direct ZMQ Requests] → [PC2 Phi-3 Translator (5581)]
```

## Current Status

- ✅ Enhanced Phi-3 Translator running on PC2 (port 5581)
- ✅ Authentication disabled for simplified integration
- ✅ Dynamic prompt engineering with 64+ examples implemented
- ✅ Advanced testing framework created
- ✅ Bridge connection to Main PC verified (port 5600)

## Integration Instructions for Main PC

### 1. Replace Translation Mechanism

Modify any component that needs translation to directly connect to PC2:

```python
import zmq
import json

# Setup connection to Phi-3 Translator
context = zmq.Context()
translator_socket = context.socket(zmq.REQ)
translator_socket.connect("tcp://192.168.1.2:5581")

def translate_text(text, source_lang="tl", target_lang="en"):
    """Send text to Phi-3 Translator on PC2"""
    request = {
        "action": "translate",
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang
    }
    
    translator_socket.send_json(request)
    response = translator_socket.recv_json()
    
    if response.get("success", False):
        return response.get("translated", text)
    else:
        # Log error and return original text as fallback
        print(f"Translation error: {response.get('message')}")
        return text
```

### 2. Disable Local Translator

To prevent confusion and resource waste:

- Stop `translator_agent.py` service on Main PC
- Modify system startup to avoid launching it
- Document the change in architecture

### 3. Fallback Strategy

In case of connection issues to PC2:

```python
def translate_with_fallback(text):
    try:
        # Try Phi-3 first
        return translate_text(text)
    except Exception as e:
        print(f"Phi-3 translation failed: {e}")
        # Use local pattern matching as emergency fallback
        for pattern, replacement in COMMON_TRANSLATIONS.items():
            if pattern in text.lower():
                return text.lower().replace(pattern, replacement)
        return text  # Last resort: return original text
```

### 4. Testing the Integration

Run this test script on Main PC to verify connection:

```python
import zmq
import json
import time

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://192.168.1.2:5581")

test_cases = [
    "I-check mo kung may available updates.",
    "Buksan mo yung browser tapos mag-search ka ng latest tech news.",
    "Pakidownload yung file at i-save sa downloads folder."
]

for text in test_cases:
    print(f"Testing: '{text}'")
    start = time.time()
    
    # Send translation request
    request = {"action": "translate", "text": text}
    socket.send_json(request)
    
    # Get response
    response = socket.recv_json()
    elapsed = time.time() - start
    
    print(f"Translation: '{response.get('translated', 'ERROR')}'")
    print(f"Time: {elapsed:.4f}s")
    print(f"Success: {response.get('success', False)}")
    print("-" * 50)
```

## Performance Expectations

- Average translation time: <0.1s
- Success rate: >99%
- Technical accuracy: High

## Maintenance

- PC2 will handle all Phi-3 Translator updates
- Any prompt improvements will be applied automatically
- Regular performance benchmarks will be conducted
