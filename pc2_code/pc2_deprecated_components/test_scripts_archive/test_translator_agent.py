#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Script for Enhanced Translator Agent (PC2)
- Tests the tiered translation approach (Google API → NLLB → Dictionary)
- Includes test cases for Tagalog, Taglish, English phrases
- Provides simulation options for testing fallback mechanisms
"""

import zmq
import json
import time
import os
import sys
import argparse
from datetime import datetime
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

# Configuration
TRANSLATOR_PORT = 5561  # Translator Agent SUB/REQ port
HEALTH_CHECK_PORT = 5559  # Translator Agent health check port
HOST = "localhost"

# Environment variables to simulate failures for testing fallback mechanisms
# Set these to "1" to simulate failures
os.environ.setdefault("SIMULATE_GOOGLE_FAILURE", "0")
os.environ.setdefault("SIMULATE_NLLB_FAILURE", "0")

# Test cases for different language scenarios
TEST_CASES = [
    # Pure Tagalog phrases
    {"type": "Tagalog", "input": "buksan mo ang file", "expected_translation": "open the file"},
    {"type": "Tagalog", "input": "i-save mo ang document", "expected_translation": "save the document"},
    {"type": "Tagalog", "input": "magsimula ng bagong project", "expected_translation": "start a new project"},
    {"type": "Tagalog", "input": "kumusta ka na?", "expected_translation": "how are you?"},
    {"type": "Tagalog", "input": "mahalaga ang pamilya sa ating kultura", "expected_translation": "family is important in our culture"},
    
    # Taglish phrases (mixed Filipino-English)
    {"type": "Taglish", "input": "i-download mo ang file na iyon", "expected_translation": "download that file"},
    {"type": "Taglish", "input": "pwede mo ba i-share ang presentation?", "expected_translation": "can you share the presentation?"},
    {"type": "Taglish", "input": "i-close mo ang browser window", "expected_translation": "close the browser window"},
    {"type": "Taglish", "input": "can you please i-open ang file na ito?", "expected_translation": "can you please open this file?"},
    
    # Already English (should be detected and skipped)
    {"type": "English", "input": "open the document", "expected_translation": "open the document"},
    {"type": "English", "input": "hello, can you help me?", "expected_translation": "hello, can you help me?"},
    
    # Phrases in dictionary pattern matching
    {"type": "Dictionary", "input": "buksan mo ang file", "expected_translation": "open the file"},
    {"type": "Dictionary", "input": "i-save mo ito", "expected_translation": "save this"},
    
    # Phrases not in dictionary (will rely on Google/NLLB)
    {"type": "Non-Dictionary", "input": "ang kuwento ay tungkol sa isang batang lalaki", "expected_translation": "the story is about a young boy"},
    {"type": "Non-Dictionary", "input": "siya ay naglalakad sa parke tuwing umaga", "expected_translation": "he/she walks in the park every morning"},
]

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL):
    """Print colored text to console"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def check_health():
    """Check the health of the Translator Agent"""
    context = zmq.Context()
    health_socket = context.socket(zmq.REQ)
    health_socket.connect(f"tcp://{HOST}:{HEALTH_CHECK_PORT}")
    
    print_colored("\n=== Checking Translator Agent Health ===", Fore.CYAN, Style.BRIGHT)
    
    try:
        request = {
            "action": "health_check",
            "request_id": f"test_{int(time.time())}"
        }
        health_socket.send_json(request)
        
        # Set a timeout in case the health check doesn't respond
        poller = zmq.Poller()
        poller.register(health_socket, zmq.POLLIN)
        
        if poller.poll(5000):  # 5 second timeout
            response = health_socket.recv_json()
            
            # Print health status
            status = response.get("status", "unknown")
            status_color = Fore.GREEN if status == "ok" else Fore.RED
            print_colored(f"Health Status: {status}", status_color, Style.BRIGHT)
            
            # Print statistics
            print_colored("\nTranslation Statistics:", Fore.CYAN)
            stats = response.get("stats", {})
            for key, value in stats.items():
                print_colored(f"  {key}: {value}", Fore.WHITE)
                
            # Print memory usage if available
            memory_usage = response.get("memory_usage", {})
            if memory_usage:
                print_colored("\nMemory Usage:", Fore.CYAN)
                for key, value in memory_usage.items():
                    print_colored(f"  {key}: {value}", Fore.WHITE)
                    
            # Check for active sessions
            session_count = response.get("session_count", 0)
            print_colored(f"\nActive Sessions: {session_count}", Fore.CYAN)
            
            return True
        else:
            print_colored("Health check request timed out", Fore.RED, Style.BRIGHT)
            return False
            
    except Exception as e:
        print_colored(f"Error checking health: {str(e)}", Fore.RED, Style.BRIGHT)
        return False
    finally:
        health_socket.close()
        context.term()

def translate_text(text, session_id="test_session"):
    """Send a translation request to the Translator Agent"""
    context = zmq.Context()
    translator_socket = context.socket(zmq.REQ)
    translator_socket.connect(f"tcp://{HOST}:{TRANSLATOR_PORT}")
    
    try:
        # Create translation request in the format expected by translator_agent.py
        request = {
            "action": "translate",
            "text": text,
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": session_id,
            "timestamp": time.time(),
            "request_id": f"test_{int(time.time())}",
            "env": {
                "SIMULATE_GOOGLE_FAILURE": os.environ.get("SIMULATE_GOOGLE_FAILURE", "0"),
                "SIMULATE_NLLB_FAILURE": os.environ.get("SIMULATE_NLLB_FAILURE", "0")
            }
        }
        
        # Send request
        translator_socket.send_json(request)
        
        # Set a timeout for the response
        poller = zmq.Poller()
        poller.register(translator_socket, zmq.POLLIN)
        
        if poller.poll(10000):  # 10 second timeout
            response = translator_socket.recv_json()
            
            # Extract translated text and other information from the translator agent response
            translated_text = response.get("text", text)
            original_text = response.get("original_text", text)
            translation_method = response.get("translation_method", "unknown")
            is_translated = response.get("translation_status", "") == "success"
            
            return {
                "original": original_text,
                "translated": translated_text,
                "method": translation_method,
                "is_translated": is_translated,
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

def run_tests(simulate_google_failure=False, simulate_nllb_failure=False):
    """Run all test cases"""
    # Set environment variables for failure simulation
    os.environ["SIMULATE_GOOGLE_FAILURE"] = "1" if simulate_google_failure else "0"
    os.environ["SIMULATE_NLLB_FAILURE"] = "1" if simulate_nllb_failure else "0"
    
    # Determine test mode based on environment variables
    if simulate_google_failure and simulate_nllb_failure:
        test_mode = "Dictionary Only (Google + NLLB Failure)"
    elif simulate_google_failure:
        test_mode = "NLLB + Dictionary (Google Failure)"
    elif simulate_nllb_failure:
        test_mode = "Google + Dictionary (NLLB Failure)"
    else:
        test_mode = "Full Tiered System (Google → NLLB → Dictionary)"
    
    print_colored(f"\n=== Starting Translation Tests: {test_mode} ===\n", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Fore.CYAN)
    
    # Track success/failure counts
    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "by_type": {}
    }
    
    # Run each test case
    for i, test in enumerate(TEST_CASES, 1):
        test_type = test["type"]
        input_text = test["input"]
        expected = test["expected_translation"]
        
        # Initialize test type stats if not present
        if test_type not in results["by_type"]:
            results["by_type"][test_type] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0
            }
        
        # Update total counts
        results["total"] += 1
        results["by_type"][test_type]["total"] += 1
        
        # Run the test
        print_colored(f"\nTest #{i}: [{test_type}] '{input_text}'", Fore.YELLOW, Style.BRIGHT)
        
        # Send to translator
        result = translate_text(input_text)
        
        # Extract results
        translated = result["translated"]
        is_translated = result["is_translated"]
        method = result.get("method", "unknown")
        
        # For English phrases, they should be skipped
        if test_type == "English" and input_text == translated:
            status = "SKIPPED"
            status_color = Fore.BLUE
            results["skipped"] += 1
            results["by_type"][test_type]["skipped"] += 1
        # For others, check if translation matches expected
        elif translated.lower() == expected.lower():
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
        
        # Add a small delay between tests to prevent overloading
        time.sleep(0.5)
    
    # Print summary
    print_colored("\n=== Test Summary ===", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Total Tests:    {results['total']}", Fore.WHITE)
    print_colored(f"Successful:     {results['successful']}", Fore.GREEN)
    print_colored(f"Failed:         {results['failed']}", Fore.RED)
    print_colored(f"Skipped:        {results['skipped']}", Fore.BLUE)
    
    # Print results by type
    print_colored("\nResults by Type:", Fore.CYAN)
    for test_type, stats in results["by_type"].items():
        print_colored(f"  {test_type}:", Fore.YELLOW)
        print_colored(f"    Total: {stats['total']}, Passed: {stats['successful']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}", Fore.WHITE)
    
    return results

def main():
    """Main function to run the test script"""
    parser = argparse.ArgumentParser(description="Test the Translator Agent's tiered translation approach")
    parser.add_argument("--health-only", action="store_true", help="Only run health check")
    parser.add_argument("--simulate-google-failure", action="store_true", help="Simulate Google API failure to test NLLB fallback")
    parser.add_argument("--simulate-nllb-failure", action="store_true", help="Simulate NLLB failure to test dictionary fallback")
    parser.add_argument("--simulate-all-failures", action="store_true", help="Simulate all failures to test complete fallback chain")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip health check and proceed with tests directly")
    
    args = parser.parse_args()
    
    # Print script header
    print_colored("\n==================================================", Fore.CYAN, Style.BRIGHT)
    print_colored("      TRANSLATOR AGENT (PC2) TEST SCRIPT", Fore.CYAN, Style.BRIGHT)
    print_colored("==================================================", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Testing agent at: tcp://{HOST}:{TRANSLATOR_PORT}", Fore.WHITE)
    print_colored(f"Health check at: tcp://{HOST}:{HEALTH_CHECK_PORT}", Fore.WHITE)
    
    # Skip health check if requested
    health_ok = True
    if not args.skip_health_check:
        health_ok = check_health()
        
        if not health_ok:
            print_colored("\nWARNING: Translator Agent health check failed or is unavailable.", Fore.RED, Style.BRIGHT)
            print_colored("Health check port 5559 may be in use by another process.", Fore.RED)
            print_colored("Tests will proceed directly to translation testing.", Fore.YELLOW)
    
    if args.health_only:
        print_colored("\nHealth check only mode - exiting.", Fore.CYAN)
        return
    
    # Run full test suite with appropriate simulation flags
    if args.simulate_all_failures:
        run_tests(simulate_google_failure=True, simulate_nllb_failure=True)
    elif args.simulate_google_failure:
        run_tests(simulate_google_failure=True)
    elif args.simulate_nllb_failure:
        run_tests(simulate_nllb_failure=True)
    else:
        # Run normal tests without simulating failures
        run_tests()
    
    # Add an extra check at the end to see how the agent's stats changed
    print_colored("\nFinal Health Check (After Tests):", Fore.CYAN, Style.BRIGHT)
    check_health()

if __name__ == "__main__":
    main()
