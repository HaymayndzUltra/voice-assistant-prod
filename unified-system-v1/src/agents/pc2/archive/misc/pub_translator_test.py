"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
PUB test script for translator_agent.py
Uses the correct socket pattern (PUB to translator's SUB socket)
"""
import zmq
import json
import time
import sys
from colorama import init, Fore, Style
from common.env_helpers import get_env

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
TRANSLATOR_PORT = 5561  # Translator Agent SUB port
EMR_PUB_PORT = 7701     # Enhanced Model Router PUB port (for listening to results)
HOST = get_env("BIND_ADDRESS", "0.0.0.0")

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL):
    """Print colored text to console"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def test_pub_sub():
    """Test connection to the translator agent using PUB/SUB pattern"""
    context = zmq.Context()
    
    # Create PUB socket to send to translator agent's SUB socket
    pub_socket = context.socket(zmq.PUB)
    # Bind to localhost to simulate the listener agent
    pub_socket.bind(f"tcp://{HOST}:{TRANSLATOR_PORT}")
    
    # Also create a SUB socket to listen for results from EMR
    sub_socket = context.socket(zmq.SUB)
    sub_socket.connect(f"tcp://{HOST}:{EMR_PUB_PORT}")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    sub_socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    
    print_colored(f"Connected as publisher to tcp://{HOST}:{TRANSLATOR_PORT}", Fore.CYAN)
    print_colored(f"Listening for results on tcp://{HOST}:{EMR_PUB_PORT}", Fore.CYAN)
    
    # Wait for connections to establish
    print_colored("Waiting for connections to establish...", Fore.YELLOW)
    time.sleep(2)
    
    # Create test message
    test_message = {
        "text": "buksan mo ang file",
        "session_id": "test_session",
        "timestamp": time.time(),
        "request_id": f"test_{int(time.time())}",
        "source_lang": "tl",
        "target_lang": "en"
    }
    
    # Send test message
    print_colored("\nSending test message:", Fore.YELLOW)
    print_colored(json.dumps(test_message, indent=2), Fore.WHITE)
    
    message_str = json.dumps(test_message)
    pub_socket.send_string(message_str)
    print_colored("Message sent! Waiting for response on EMR PUB channel...", Fore.GREEN)
    
    # Wait for response from EMR
    try:
        start_time = time.time()
        timeout = 15  # 15 seconds total timeout
        
        while time.time() - start_time < timeout:
            try:
                response_str = sub_socket.recv_string()
                response = json.loads(response_str)
                
                # Check if this is our response
                if response.get("source") == "translator_agent" and response.get("session_id") == test_message["session_id"]:
                    print_colored("\nReceived response:", Fore.GREEN, Style.BRIGHT)
                    print_colored(json.dumps(response, indent=2), Fore.WHITE)
                    
                    # Extract translation details if available
                    if "original_text" in response and "text" in response:
                        print_colored("\nTranslation Summary:", Fore.CYAN, Style.BRIGHT)
                        print_colored(f"Original:    '{response.get('original_text')}'", Fore.WHITE)
                        print_colored(f"Translated:  '{response.get('text')}'", Fore.GREEN)
                    
                    return True
            except zmq.error.Again:
                # No message available yet, wait a bit
                time.sleep(0.5)
                continue
        
        print_colored("\nERROR: No response received within timeout period.", Fore.RED, Style.BRIGHT)
        print_colored("Make sure the translator agent and EMR are running and properly connected.", Fore.RED)
        return False
        
    except Exception as e:
        print_colored(f"\nERROR: {str(e)}", Fore.RED, Style.BRIGHT)
        return False
        
    finally:
        pub_socket.close()
        sub_socket.close()
        context.term()

def main():
    """Main function"""
    print_colored("\n===================================================", Fore.CYAN, Style.BRIGHT)
    print_colored("      PUB/SUB TRANSLATOR AGENT TEST SCRIPT", Fore.CYAN, Style.BRIGHT)
    print_colored("===================================================", Fore.CYAN, Style.BRIGHT)
    
    # Test PUB/SUB connection
    success = test_pub_sub()
    
    # Show final status
    if success:
        print_colored("\n✓ Test completed successfully!", Fore.GREEN, Style.BRIGHT)
    else:
        print_colored("\n✗ Test failed. Please check the translator agent configuration.", Fore.RED, Style.BRIGHT)
        print_colored("  - Verify translator_agent.py is running", Fore.RED)
        print_colored("  - Check that it's listening on port 5561", Fore.RED)
        print_colored("  - Ensure Enhanced Model Router (EMR) is running", Fore.RED)
    
    # Clean up
    print_colored("\nExiting...", Fore.CYAN)

if __name__ == "__main__":
    main()
