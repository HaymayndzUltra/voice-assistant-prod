#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Custom Test Script for Translator Agent
- Tests with new phrases not included in the standard test suite
- Includes a variety of Tagalog, Taglish, and complex phrases
"""

import zmq
import json
import time
import sys
from colorama import init, Fore, Style
from common.env_helpers import get_env

# Initialize colorama for colored console output
init()

# Configuration
TRANSLATOR_PORT = 5561  # Translator Agent REQ port
HOST = get_env("BIND_ADDRESS", "0.0.0.0")

# New test cases with different words and phrases
NEW_TEST_CASES = [
    # Pure Tagalog commands
    {"type": "Tagalog", "input": "i-delete mo ang mga lumang files", "expected": "delete the old files"},
    {"type": "Tagalog", "input": "palakihin mo ang font size", "expected": "increase the font size"},
    {"type": "Tagalog", "input": "i-minimize mo ang browser", "expected": "minimize the browser"},
    {"type": "Tagalog", "input": "i-export mo ang data bilang CSV", "expected": "export the data as CSV"},
    
    # Taglish phrases
    {"type": "Taglish", "input": "i-analyze mo ang performance ng system", "expected": "analyze the performance of the system"},
    {"type": "Taglish", "input": "pwede bang i-filter ang results by date", "expected": "can you filter the results by date"},
    {"type": "Taglish", "input": "i-summarize mo ang content ng webpage na ito", "expected": "summarize the content of this webpage"},
    
    # Complex phrases
    {"type": "Complex", "input": "kailangan kong mag-debug ng error sa login page", "expected": "I need to debug an error on the login page"},
    {"type": "Complex", "input": "mag-install ka ng bagong version ng application", "expected": "install a new version of the application"},
    {"type": "Complex", "input": "i-optimize mo ang database queries para mas mabilis", "expected": "optimize the database queries to be faster"},
    
    # Conversational phrases
    {"type": "Conversational", "input": "ano ang status ng server ngayon?", "expected": "what is the status of the server now?"},
    {"type": "Conversational", "input": "kailan ang next meeting natin?", "expected": "when is our next meeting?"},
    {"type": "Conversational", "input": "paano ko ma-access ang cloud storage?", "expected": "how can I access the cloud storage?"}
]

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL):
    """Print colored text to console"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def translate_text(text):
    """Send a translation request to the Translator Agent"""
    context = zmq.Context()
    translator_socket = context.socket(zmq.REQ)
    translator_socket.connect(f"tcp://{HOST}:{TRANSLATOR_PORT}")
    
    try:
        # Create translation request
        request = {
            "action": "translate",
            "text": text,
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": "custom_test",
            "timestamp": time.time(),
            "request_id": f"custom_{int(time.time())}"
        }
        
        # Send request
        translator_socket.send_json(request)
        
        # Set a timeout in case the translator doesn't respond
        poller = zmq.Poller()
        poller.register(translator_socket, zmq.POLLIN)
        
        if poller.poll(5000):  # 5 second timeout
            response = translator_socket.recv_json()
            
            # Extract translation information - handle different response formats
            translated_text = response.get("translated_text", response.get("text", text))
            method = response.get("method", "unknown")
            
            # Print raw response for debugging
            print_colored(f"  Raw Response: {json.dumps(response, indent=2)[:100]}...", Fore.BLUE)
            
            return {
                "original": text,
                "translated": translated_text,
                "method": method,
                "is_translated": response.get("success", False),
                "raw_response": response
            }
        else:
            print_colored("Translation request timed out", Fore.RED, Style.BRIGHT)
            return {
                "original": text,
                "translated": text,
                "method": "timeout",
                "is_translated": False,
                "raw_response": {}
            }
            
    except Exception as e:
        print_colored(f"Error translating text: {str(e)}", Fore.RED, Style.BRIGHT)
        return {
            "original": text,
            "translated": text,
            "method": "error",
            "is_translated": False,
            "raw_response": {"error": str(e)}
        }
    finally:
        translator_socket.close()
        context.term()

def run_custom_tests():
    """Run all custom test cases"""
    print_colored("\n==================================================", Fore.CYAN, Style.BRIGHT)
    print_colored("      CUSTOM TRANSLATOR AGENT TEST SCRIPT", Fore.CYAN, Style.BRIGHT)
    print_colored("==================================================", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Testing agent at: tcp://{HOST}:{TRANSLATOR_PORT}", Fore.WHITE)
    
    print_colored("\n=== Starting Custom Translation Tests ===", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n", Fore.WHITE)
    
    # Track results
    results = {
        "total": len(NEW_TEST_CASES),
        "successful": 0,
        "failed": 0,
        "by_type": {}
    }
    
    # Initialize results by type
    for case in NEW_TEST_CASES:
        test_type = case["type"]
        if test_type not in results["by_type"]:
            results["by_type"][test_type] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }
        results["by_type"][test_type]["total"] += 1
    
    # Run each test case
    for i, test_case in enumerate(NEW_TEST_CASES):
        input_text = test_case["input"]
        expected = test_case["expected"]
        test_type = test_case["type"]
        
        print_colored(f"Test #{i+1}: [{test_type}] '{input_text}'", Fore.CYAN)
        
        # Translate text
        result = translate_text(input_text)
        translated = result["translated"]
        method = result["method"]
        
        # Compare with expected translation (case-insensitive)
        if translated.lower() == expected.lower():
            status = "PASS"
            status_color = Fore.GREEN
            results["successful"] += 1
            results["by_type"][test_type]["successful"] += 1
        else:
            status = "FAIL"
            status_color = Fore.RED
            results["failed"] += 1
            results["by_type"][test_type]["failed"] += 1
        
        # Print result
        print_colored(f"  Input:      '{input_text}'", Fore.WHITE)
        print_colored(f"  Expected:   '{expected}'", Fore.WHITE)
        print_colored(f"  Translated: '{translated}'", Fore.WHITE)
        print_colored(f"  Method:     {method}", Fore.WHITE)
        print_colored(f"  Status:     {status}", status_color, Style.BRIGHT)
        print()
        
        # Add a small delay between tests
        time.sleep(0.5)
    
    # Print summary
    print_colored("\n=== Test Summary ===", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Total Tests:    {results['total']}", Fore.WHITE)
    print_colored(f"Successful:     {results['successful']}", Fore.GREEN)
    print_colored(f"Failed:         {results['failed']}", Fore.RED)
    
    # Print results by type
    print_colored("\nResults by Type:", Fore.CYAN)
    for test_type, stats in results["by_type"].items():
        print_colored(f"  {test_type}:", Fore.YELLOW)
        print_colored(f"    Total: {stats['total']}, Passed: {stats['successful']}, Failed: {stats['failed']}", Fore.WHITE)
    
    # Calculate overall accuracy
    accuracy = (results["successful"] / results["total"]) * 100 if results["total"] > 0 else 0
    print_colored(f"\nOverall Accuracy: {accuracy:.2f}%", Fore.CYAN, Style.BRIGHT)
    
    return results

if __name__ == "__main__":
    run_custom_tests()
