#!/usr/bin/env python3
"""
Test script for the Translator Agent with various Taglish/Tagalog messages
"""
import zmq
import json
import time
import sys
from pathlib import Path

# Setup ZMQ
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.setsockopt(zmq.LINGER, 0)
socket.RCVTIMEO = 5000  # 5 second timeout

# Connect to translator agent
port = 5563
socket.connect(f"tcp://localhost:{port}")

# Test phrases - mix of pure Tagalog and Taglish
test_phrases = [
    # Pure Tagalog phrases
    "Buksan mo ang file na ito",
    "Ipadala mo ang email sa akin mamaya",
    "Isara mo ang bintana",
    "Ilipat mo ang file sa desktop",
    "Pakiayos ang mga larawan sa folder",
    "Maghanap ka ng mga bagong laro",
    
    # Taglish phrases
    "I-save mo yung file na ginawa ko kanina",
    "Pwede mo bang i-open yung browser",
    "I-check mo kung may new messages ako",
    "Pakiprocess yung data sa spreadsheet",
    "Hindi gumagana yung mouse ko",
    "Na-corrupt yung file ko kahapon",
    
    # Command phrases with technical terms
    "I-restart mo yung computer",
    "Mag-install ka ng bagong app",
    "I-delete mo yung temporary files",
    "I-scan mo yung document",
    "I-format mo yung USB drive",
    "I-backup mo yung important files",
]

print(f"Testing Translator Agent with {len(test_phrases)} phrases\n")
print("-" * 80)

successful = 0
failed = 0

for i, phrase in enumerate(test_phrases):
    try:
        print(f"\nTest {i+1}: '{phrase}'")
        
        # Prepare request
        request = {
            "action": "translate",
            "text": phrase,
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": "test_session_123",
            "request_id": f"test_{i}_{int(time.time())}"
        }
        
        # Send request
        print(f"Sending request: {json.dumps(request)}")
        socket.send_json(request)
        
        # Get response
        response = socket.recv_json()
        
        # Display result
        if response.get("status") == "success":
            print(f"✅ SUCCESS: '{phrase}' → '{response.get('translated_text')}'")
            print(f"   Method: {response.get('translation_method', 'unknown')}")
            print(f"   Confidence: {response.get('confidence_score', 'unknown')}")
            successful += 1
        else:
            print(f"❌ FAILED: {response.get('error_message', 'Unknown error')}")
            failed += 1
            
    except zmq.error.Again:
        print(f"❌ TIMEOUT: No response received for '{phrase}'")
        failed += 1
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        failed += 1
    
    print("-" * 80)
    # Small delay between requests
    time.sleep(0.5)

# Print summary
print(f"\nTest Summary:")
print(f"Total phrases tested: {len(test_phrases)}")
print(f"Successful translations: {successful}")
print(f"Failed translations: {failed}")
print(f"Success rate: {successful/len(test_phrases)*100:.1f}%")

# Clean up
socket.close()
context.term()
