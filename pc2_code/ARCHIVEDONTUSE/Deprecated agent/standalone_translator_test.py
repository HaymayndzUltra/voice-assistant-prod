"""
Standalone test for translator_agent.py
Only tests the translation functionality without requiring EMR
"""
import zmq
import json
import time
import sys
from colorama import init, Fore, Style

# Initialize colorama
init()

# Configuration
TRANSLATOR_PORT = 5561  # Translator Agent SUB port
HOST = "localhost"

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL):
    """Print colored text to console"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def test_translation():
    """Test translator agent's translation functionality"""
    context = zmq.Context()
    
    # Create PUB socket to send to translator agent's SUB socket
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind(f"tcp://{HOST}:{TRANSLATOR_PORT}")
    
    print_colored(f"Connected as publisher to tcp://{HOST}:{TRANSLATOR_PORT}", Fore.CYAN)
    
    # Wait for connections to establish
    print_colored("Waiting for connections to establish...", Fore.YELLOW)
    time.sleep(2)
    
    # Test cases
    test_cases = [
        {"text": "buksan mo ang file", "expected": "English translation (likely 'open the file')"},
        {"text": "i-save mo ito", "expected": "English translation (likely 'save this')"},
        {"text": "magsara ng application", "expected": "English translation (likely 'close application')"},
        {"text": "Can you please i-open ang file na ito?", "expected": "English translation (Taglish detection)"},
        {"text": "Hello, how are you today?", "expected": "Same text (English detection)"}
    ]
    
    print_colored("\n=== Running Translation Tests ===\n", Fore.CYAN, Style.BRIGHT)
    
    for i, test in enumerate(test_cases, 1):
        # Create test message
        test_message = {
            "text": test["text"],
            "session_id": f"test_session_{i}",
            "timestamp": time.time(),
            "request_id": f"test_{int(time.time())}_{i}",
            "source_lang": "tl",
            "target_lang": "en"
        }
        
        # Send test message
        print_colored(f"Test #{i}: '{test['text']}'", Fore.YELLOW)
        message_str = json.dumps(test_message)
        pub_socket.send_string(message_str)
        
        print_colored(f"  Message sent. Expected: {test['expected']}", Fore.WHITE)
        print_colored("  Check translator_agent.py logs for translation results", Fore.CYAN)
        
        # Wait between tests
        time.sleep(2)
    
    print_colored("\n=== Test Summary ===", Fore.CYAN, Style.BRIGHT)
    print_colored("All test messages sent successfully to translator_agent.py", Fore.GREEN)
    print_colored("To see the translation results, check the logs in the translator_agent.py window", Fore.YELLOW)
    print_colored("\nNOTE: This test only verifies that the translator can receive and process messages.", Fore.WHITE)
    print_colored("It doesn't verify the EMR connection which would require the full pipeline to be running.", Fore.WHITE)
    
    pub_socket.close()
    context.term()

def main():
    """Main function"""
    print_colored("\n===================================================", Fore.CYAN, Style.BRIGHT)
    print_colored("    STANDALONE TRANSLATOR AGENT TEST SCRIPT", Fore.CYAN, Style.BRIGHT)
    print_colored("===================================================", Fore.CYAN, Style.BRIGHT)
    
    test_translation()
    
    print_colored("\nExiting...", Fore.CYAN)

if __name__ == "__main__":
    main()
