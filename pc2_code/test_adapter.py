"""
Simple test client for the Phi Translation Adapter
"""
import zmq
import json
import time
from common.env_helpers import get_env

def test_translation(text, source_lang="tl", target_lang="en"):
    # Connect to the adapter
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5581")
    
    # Send a translation request
    request = {
        "action": "translate",
        "text": text,
        "source_lang": source_lang,
        "target_lang": target_lang
    }
    
    print(f"\nSending request: {request}")
    socket.send_json(request)
    
    # Wait for response with timeout
    start_time = time.time()
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    try:
        response = socket.recv_json()
        elapsed = time.time() - start_time
        print(f"Received response in {elapsed:.2f} seconds:")
        print(f"Original: {response.get('original', '')}")
        print(f"Translated: {response.get('translated', '')}")
        print(f"Success: {response.get('success', False)}")
        print(f"Message: {response.get('message', '')}")
        return response
    except zmq.error.Again:
        print("Timeout waiting for response. Is the adapter running?")
        return None
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    # Interactive test loop
    print("=== Phi Translation Adapter Test Client ===")
    print("Type 'exit' to quit")
    print("Type 'switch' to toggle translation direction")
    
    source_lang = "tl"
    target_lang = "en"
    
    while True:
        print(f"\nCurrent direction: {source_lang} -> {target_lang}")
        text = input("Enter text to translate: ")
        
        if text.lower() == 'exit':
            print("Exiting...")
            break
        
        if text.lower() == 'switch':
            source_lang, target_lang = target_lang, source_lang
            print(f"Direction switched: {source_lang} → {target_lang}")
            continue
        
        if text:
            test_translation(text, source_lang, target_lang)
