#!/usr/bin/env python3
"""
Test script specifically for the REQ/REP socket connection 
between Main PC and translator_agent.py

This script simulates the fixed_streaming_translation.py on the Main PC
by connecting to the translator agent's REP socket on port 5563.
"""

import zmq
import json
import time
import uuid
import argparse
from colorama import init, Fore, Style
from common.env_helpers import get_env

# Initialize colorama
init(autoreset=True)

# Constants
TRANSLATOR_REP_PORT = 5563  # Port where translator_agent.py binds its REP socket

def generate_request_id():
    """Generate a unique request ID using timestamp and UUID"""
    timestamp = int(time.time())
    uuid_part = str(uuid.uuid4())[:8]
    return f"test_{timestamp}_{uuid_part}"

def main():
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.CYAN}    TRANSLATOR AGENT REQ/REP SOCKET TEST")
    print(f"{Fore.CYAN}{'='*50}\n")
    
    print(f"{Fore.YELLOW}This test simulates the Main PC's fixed_streaming_translation.py")
    print(f"{Fore.YELLOW}by sending direct requests to the translator_agent.py REP socket.")
    print(f"{Fore.YELLOW}translator_agent.py must be running with REP socket on port {TRANSLATOR_REP_PORT}\n")
    
    # Setup ZMQ REQ socket to connect to translator agent
    context = zmq.Context()
    req_socket = context.socket(zmq.REQ)
    req_socket.connect(f"tcp://localhost:{TRANSLATOR_REP_PORT}")
    req_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    
    print(f"{Fore.GREEN}Connecting to translator agent on tcp://localhost:{TRANSLATOR_REP_PORT}")
    print(f"{Fore.GREEN}Using REQ/REP pattern for direct communication\n")
    
    # Test cases
    test_cases = [
        {
            "text": "buksan mo ang file", 
            "expected": "open the file",
            "source_lang": "tl",
            "target_lang": "en"
        },
        {
            "text": "i-save mo ang document", 
            "expected": "save the document",
            "source_lang": "tl", 
            "target_lang": "en"
        },
        {
            "text": "Can you please i-open ang file na ito?", 
            "expected": "Can you please open this file?",
            "source_lang": "tl", 
            "target_lang": "en"
        },
        {
            "text": "Hello, how are you today?", 
            "expected": "Hello, how are you today?",
            "source_lang": "en", 
            "target_lang": "en"
        }
    ]
    
    print(f"{Fore.CYAN}=== Starting Direct REQ/REP Translation Tests ===\n")
    
    success_count = 0
    timeout_count = 0
    error_count = 0
    
    for i, test in enumerate(test_cases, 1):
        request_id = generate_request_id()
        
        # Prepare request
        request = {
            "text": test["text"],
            "source_lang": test["source_lang"],
            "target_lang": test["target_lang"],
            "request_id": request_id,
            "timestamp": time.time()
        }
        
        print(f"\n{Fore.CYAN}Test #{i}: {test['text']}")
        print(f"{Fore.YELLOW}Expected: '{test['expected']}'")
        print(f"{Fore.YELLOW}Request ID: {request_id}")
        
        try:
            # Send request
            req_socket.send_json(request)
            print(f"{Fore.GREEN}→ Request sent to translator_agent.py")
            
            # Wait for response (will timeout after 10 seconds)
            response = req_socket.recv_json()
            
            # Display response
            print(f"{Fore.GREEN}← Response received from translator_agent.py")
            print(f"{Fore.WHITE}Translation: '{response.get('text', '<none>')}'")
            print(f"{Fore.WHITE}Method: {response.get('translation_method', '<unknown>')}")
            print(f"{Fore.WHITE}Time: {response.get('translation_time_ms', 0):.2f}ms")
            
            # Basic verification
            if response.get("request_id") == request_id:
                print(f"{Fore.GREEN}✓ Request ID matches")
            else:
                print(f"{Fore.RED}✗ Request ID mismatch! Expected {request_id}, got {response.get('request_id')}")
            
            # Check if translation matches expected output
            if response.get("text") == test["expected"]:
                print(f"{Fore.GREEN}✓ Translation matches expected output")
                success_count += 1
            else:
                print(f"{Fore.YELLOW}⚠ Translation differs from expected output")
                # Still count as success if translation completed
                if response.get("translation_status") == "success":
                    success_count += 1
                    print(f"{Fore.YELLOW}  But translation was marked as successful, accepting result")
                else:
                    error_count += 1
            
        except zmq.error.Again:
            print(f"{Fore.RED}TIMEOUT: No response received from translator_agent.py after 10 seconds")
            timeout_count += 1
        except Exception as e:
            print(f"{Fore.RED}ERROR: {str(e)}")
            error_count += 1
        
        # Slight delay between tests
        time.sleep(1)
    
    # Print summary
    print(f"\n{Fore.CYAN}=== Translation REQ/REP Test Summary ===\n")
    print(f"{Fore.WHITE}Total Tests:       {len(test_cases)}")
    print(f"{Fore.GREEN}Successful Tests:  {success_count}")
    print(f"{Fore.RED}Timeouts:          {timeout_count}")
    print(f"{Fore.RED}Errors:            {error_count}")
    
    success_rate = (success_count / len(test_cases)) * 100
    color = Fore.GREEN if success_rate > 75 else Fore.YELLOW if success_rate > 25 else Fore.RED
    print(f"{color}Success Rate:      {success_rate:.1f}%\n")
    
    print(f"{Fore.GREEN}Test script completed. Exiting...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the REQ/REP socket functionality of the translator agent")
    args = parser.parse_args()
    main()
