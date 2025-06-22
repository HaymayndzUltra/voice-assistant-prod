"""
Comprehensive Translator Agent Test Script

This script tests the complete translation pipeline by:
1. Sending Filipino/Taglish text to translator_agent.py via PUB-SUB pattern (port 5561)
2. Listening for translated responses from Enhanced Model Router (EMR) via SUB socket (port 7701)
3. Verifying request-response matching via request_id tracking

PREREQUISITES:
- translator_agent.py must be running and listening on port 5561
- Enhanced Model Router (EMR) must be running and publishing on port 7701
- NLLB Translation Adapter should be running (as a fallback option)
"""

import zmq
import json
import time
import sys
import argparse
import uuid
import traceback
from colorama import init, Fore, Style

# Initialize colorama for colored output
try:
    init()
except ImportError:
    print("Colorama not installed. Output will not be colored.")
    # Define dummy color constants if colorama is not available
    class DummyFore:
        def __getattr__(self, name):
            return ''
    class DummyStyle:
        def __getattr__(self, name):
            return ''
    Fore = DummyFore()
    Style = DummyStyle()

# Configuration
TRANSLATOR_PORT = 5561  # Translator Agent SUB socket connects here
EMR_PUB_PORT = 7701     # Enhanced Model Router PUB port for responses
HOST = "localhost"

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL):
    """Print colored text to console"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def generate_request_id():
    """Generate a unique request ID"""
    return f"test_{int(time.time())}_{str(uuid.uuid4())[:8]}"

def test_translation_pipeline(test_cases=None, timeout=10, verbose=False):
    """
    Test the complete translation pipeline (Translator Agent → EMR)

    Args:
        test_cases: List of test cases to run
        timeout: Maximum time to wait for EMR response in seconds
        verbose: Whether to print detailed logs
    """
    if not test_cases:
        # Default test cases if none provided
        test_cases = [
            {
                "text": "buksan mo ang file",
                "description": "Basic Tagalog command",
                "expected": "open the file"
            },
            {
                "text": "i-save mo ang document",
                "description": "Taglish command with i- prefix",
                "expected": "save the document"
            },
            {
                "text": "Can you please i-open ang file na ito?",
                "description": "Mixed Taglish sentence",
                "expected": "Can you please open this file?"
            },
            {
                "text": "Hello, how are you today?",
                "description": "Pure English (should be detected and passed through)",
                "expected": "Hello, how are you today?"
            }
        ]

    context = zmq.Context()

    # Create PUB socket to send to translator agent's SUB socket
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind(f"tcp://*:{TRANSLATOR_PORT}")

    # Create SUB socket to listen for responses from EMR
    emr_sub_socket = context.socket(zmq.SUB)
    emr_sub_socket.connect(f"tcp://{HOST}:{EMR_PUB_PORT}")
    emr_sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # Subscribe to all messages

    # Setup poller for EMR responses
    poller = zmq.Poller()
    poller.register(emr_sub_socket, zmq.POLLIN)

    print_colored(f"Sending translation requests to tcp://*:{TRANSLATOR_PORT}", Fore.CYAN)
    print_colored(f"Listening for EMR responses on tcp://{HOST}:{EMR_PUB_PORT}", Fore.CYAN)

    # Wait for connections to establish
    print_colored("\nWaiting for connections to establish...", Fore.YELLOW)
    time.sleep(2)  # Give ZMQ sockets time to connect

    # Track test results
    results = {
        "total": len(test_cases),
        "successful_send": 0,
        "received_response": 0,
        "timeout": 0,
        "errors": 0,
        "details": []
    }

    # Process each test case
    print_colored("\n=== Starting Translation Pipeline Tests ===\n", Fore.CYAN, Style.BRIGHT)

    for idx, test in enumerate(test_cases, 1):
        # Create unique request ID for tracking
        request_id = generate_request_id()
        session_id = f"test_session_{idx}"

        # Prepare test message
        test_message = {
            "text": test["text"],
            "session_id": session_id,
            "request_id": request_id,
            "timestamp": time.time(),
            "source_lang": "tl",  # Default source language (Tagalog)
            "target_lang": "en"   # Default target language (English)
        }

        # Log the test case
        print_colored(f"\nTest #{idx}: {test['description']}", Fore.YELLOW, Style.BRIGHT)
        print_colored(f"Request: '{test['text']}'", Fore.WHITE)
        print_colored(f"Expected: '{test['expected']}'", Fore.WHITE)
        print_colored(f"Request ID: {request_id}", Fore.CYAN)

        # Send the test message
        try:
            message_str = json.dumps(test_message)
            pub_socket.send_string(message_str)
            print_colored("→ Request sent to translator_agent.py", Fore.GREEN)
            results["successful_send"] += 1
        except Exception as e:
            print_colored(f"ERROR sending message: {str(e)}", Fore.RED, Style.BRIGHT)
            results["errors"] += 1
            results["details"].append({
                "test": idx,
                "text": test["text"],
                "error": str(e),
                "stage": "send"
            })
            continue

        # Wait for and process EMR response
        response_received = False
        start_time = time.time()
        wait_time = timeout  # seconds to wait for response

        while time.time() - start_time < wait_time:
            # Check for EMR response with timeout
            socks = dict(poller.poll(500))  # 500ms poll timeout

            if emr_sub_socket in socks and socks[emr_sub_socket] == zmq.POLLIN:
                try:
                    # Receive message from EMR
                    emr_message = emr_sub_socket.recv_string()
                    emr_data = json.loads(emr_message)

                    # Only process if this response matches our request_id
                    if emr_data.get("request_id") == request_id:
                        print_colored("\n← Received matching response from EMR:", Fore.GREEN, Style.BRIGHT)
                        if verbose:
                            print_colored(json.dumps(emr_data, indent=2), Fore.WHITE)

                        # Extract translation details
                        original = emr_data.get("original_text", "<missing>")
                        translated = emr_data.get("text", "<missing>")

                        print_colored("\nTranslation Results:", Fore.CYAN, Style.BRIGHT)
                        print_colored(f"Original:    '{original}'", Fore.WHITE)
                        print_colored(f"Translated:  '{translated}'", Fore.GREEN)

                        # Check if translation matches expected output
                        expected = test.get("expected", "")
                        if expected.lower() in translated.lower():
                            print_colored(f"Expected ✓: '{expected}'", Fore.GREEN, Style.BRIGHT)
                        else:
                            print_colored(f"Expected ✗: '{expected}'", Fore.YELLOW, Style.BRIGHT)

                        # Record success
                        response_received = True
                        results["received_response"] += 1
                        results["details"].append({
                            "test": idx,
                            "text": test["text"],
                            "translated": translated,
                            "expected": expected,
                            "match": expected.lower() in translated.lower(),
                            "time": time.time() - start_time
                        })
                        break
                    elif verbose:
                        # Show non-matching responses if verbose mode
                        print_colored(f"Received non-matching response (ID: {emr_data.get('request_id')})", Fore.YELLOW)

                except Exception as e:
                    print_colored(f"ERROR processing EMR response: {str(e)}", Fore.RED)
                    if verbose:
                        print_colored(traceback.format_exc(), Fore.RED)

            # Short delay between polls
            time.sleep(0.1)

        # Check for timeout
        if not response_received:
            print_colored(f"\nTIMEOUT: No matching response received from EMR after {wait_time} seconds", Fore.RED, Style.BRIGHT)
            results["timeout"] += 1
            results["details"].append({
                "test": idx,
                "text": test["text"],
                "error": "timeout",
                "stage": "receive"
            })

        # Wait between tests
        time.sleep(1)

    # Print test summary
    print_colored("\n=== Translation Pipeline Test Summary ===\n", Fore.CYAN, Style.BRIGHT)
    print_colored(f"Total Tests:       {results['total']}", Fore.WHITE)
    print_colored(f"Requests Sent:     {results['successful_send']}", Fore.WHITE)
    print_colored(f"Responses Received: {results['received_response']}", Fore.WHITE)
    print_colored(f"Timeouts:          {results['timeout']}", Fore.WHITE)
    print_colored(f"Errors:            {results['errors']}", Fore.WHITE)

    # Success rate
    success_rate = (results['received_response'] / results['total']) * 100 if results['total'] > 0 else 0
    success_color = Fore.GREEN if success_rate > 80 else (Fore.YELLOW if success_rate > 50 else Fore.RED)
    print_colored(f"Success Rate:      {success_rate:.1f}%", success_color, Style.BRIGHT)

    # Clean up
    pub_socket.close()
    emr_sub_socket.close()
    context.term()

    return results

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test the translator agent pipeline")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds for EMR responses")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--num-tests", type=int, default=4, help="Number of tests to run (uses default test cases)")

    args = parser.parse_args()

    print_colored("\n===================================================", Fore.CYAN, Style.BRIGHT)
    print_colored("    COMPREHENSIVE TRANSLATOR PIPELINE TEST", Fore.CYAN, Style.BRIGHT)
    print_colored("===================================================", Fore.CYAN, Style.BRIGHT)

    print_colored("\nPREREQUISITES:", Fore.YELLOW, Style.BRIGHT)
    print_colored("1. translator_agent.py must be running (SUB socket on port 5561)", Fore.YELLOW)
    print_colored("2. Enhanced Model Router (EMR) must be running (PUB socket on port 7701)", Fore.YELLOW)
    print_colored("3. NLLB Translation Adapter should be running (optional fallback)", Fore.YELLOW)

    # Run tests
    test_translation_pipeline(timeout=args.timeout, verbose=args.verbose)

    print_colored("\nTest script completed. Exiting...", Fore.CYAN)

if __name__ == "__main__":
    main()
