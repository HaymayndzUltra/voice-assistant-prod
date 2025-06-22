#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import zmq
import time
import json
from colorama import Fore, Style, init

# Initialize colorama
init()

def connect_to_translation_service(host="localhost", port=5581):
    """Connect to the translation service"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    print(f"Connecting to translation service at {host}:{port}...")
    socket.connect(f"tcp://{host}:{port}")
    print("Connected successfully")
    return socket

def test_translation(socket, text, src_lang="tl", tgt_lang="en"):
    """Test translation for a single phrase"""
    request = {
        "text": text,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang
    }
    
    # Send request
    start_time = time.time()
    socket.send_json(request)
    
    # Receive response
    response = socket.recv_json()
    end_time = time.time()
    
    # Calculate time taken
    time_taken = end_time - start_time
    
    # Print results
    if "error" in response:
        print(f"Original:   '{text}'")
        print(f"{Fore.RED}Error: {response['error']}{Style.RESET_ALL}")
        return False, time_taken
    else:
        print(f"Original:   '{text}'")
        print(f"Translated: '{response['translated_text']}'")
        print(f"Time:       {time_taken:.2f} seconds")
        return True, time_taken

def main():
    # Connect to translation service
    socket = connect_to_translation_service()
    
    # List of Taglish phrases to test
    taglish_phrases = [
        "I need to buy groceries para sa dinner natin",
        "Can you download yung latest update?",
        "This weekend pupunta tayo sa beach",
        "May meeting ako tomorrow morning",
        "Please check mo yung email ko kahapon",
        "Si John ang assigned sa new project natin",
        "Mag-breakfast muna tayo before the meeting",
        "After work, mag-grocery shopping tayo",
        "I'm planning to buy a new phone kasi nasira yung old one ko",
        "Let's cancel na lang yung reservation natin"
    ]
    
    # Test each phrase
    successful_translations = 0
    total_time = 0
    
    print("-" * 50)
    for i, phrase in enumerate(taglish_phrases, 1):
        print(f"\nTest {i}/{len(taglish_phrases)}")
        success, time_taken = test_translation(socket, phrase)
        
        if success:
            successful_translations += 1
        total_time += time_taken
        
        print("-" * 50)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Taglish Translation Test Summary")
    print("=" * 50)
    print(f"Total phrases tested: {len(taglish_phrases)}")
    print(f"Successful translations: {successful_translations}/{len(taglish_phrases)}")
    
    if len(taglish_phrases) > 0:
        print(f"Average translation time: {total_time/len(taglish_phrases):.2f} seconds")
        print(f"Success rate: {successful_translations/len(taglish_phrases)*100:.1f}%")
    
    print("\nTest completed")

if __name__ == "__main__":
    main()
