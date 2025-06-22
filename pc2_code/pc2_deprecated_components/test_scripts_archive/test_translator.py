"""
Test script for the Translator Agent
Tests the translation functionality with various Filipino phrases
"""
import sys
import os
import json
import zmq
import time

# Add the parent directory to the path to import the agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test phrases in Filipino
test_phrases = [
    "Magandang umaga",  # Good morning
    "Kumusta ka?",  # How are you?
    "Salamat sa tulong mo",  # Thank you for your help
    "Gusto ko ng pagkain",  # I want food
    "Pakibukas ng ilaw",  # Please turn on the light
    "Mahal kita",  # I love you
    "Anong oras na?",  # What time is it?
    "Saan ang banyo?",  # Where is the bathroom?
    "Tulungan mo ako",  # Help me
    "Hindi ko maintindihan"  # I don't understand
]

def test_translator():
    """Test the translator agent with various Filipino phrases"""
    print("=== Testing Translator Agent ===")
    
    # Connect to the translator agent
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5561")  # Translator agent REQ/REP port
    
    print("\nSending test phrases to translator agent...\n")
    
    for i, phrase in enumerate(test_phrases):
        print(f"Test {i+1}: '{phrase}'")
        
        # Create request
        request = {
            "action": "translate",
            "text": phrase,
            "source_lang": "tl",
            "target_lang": "en",
            "request_id": f"test_{i+1}"
        }
        
        # Send request
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        
        # Print response
        print(f"  Original: {phrase}")
        print(f"  Translated: {response.get('text', 'ERROR')}")
        print(f"  Method: {response.get('translation_method', 'unknown')}")
        print(f"  Confidence: {response.get('confidence_score', 0):.2f}")
        print(f"  Status: {response.get('translation_status', 'unknown')}")
        print(f"  Time: {response.get('translation_time_ms', 0):.2f}ms")
        print()
        
        # Small delay between requests
        time.sleep(0.5)
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_translator()
