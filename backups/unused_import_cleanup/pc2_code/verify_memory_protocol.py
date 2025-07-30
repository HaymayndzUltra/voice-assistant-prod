"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Memory Agent Protocol Testing Script
For testing both payload formats with the Memory Agent
"""

import zmq
import json
import time
import sys
from colorama import Fore, Style, init
from common.env_helpers import get_env

init(autoreset=True)

# Test configurations
TEST_PORTS = [5590, 5598]
PAYLOAD_FORMATS = [
    {"action": "health_check"},
    {"request_type": "health_check"}
]

def connect_to_socket(port):
    """Connect to a ZMQ socket on the specified port."""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    socket.connect(f"tcp://localhost:{port}")
    return socket, context

def test_memory_agent(port, payload):
    """Test memory agent with specific payload format."""
    print(f"{Fore.CYAN}Testing Memory Agent on port {port} with payload: {payload}")
    
    socket, context = connect_to_socket(port)
    
    try:
        # Send request
        socket.send_json(payload)
        print(f"{Fore.YELLOW}Sent: {json.dumps(payload)}")
        
        # Get response
        response = socket.recv_json()
        print(f"{Fore.GREEN}Received: {json.dumps(response)}")
        
        return True, response
    except zmq.error.Again:
        print(f"{Fore.RED}Timeout waiting for response from port {port}")
        return False, None
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False, None
    finally:
        socket.close()
        context.term()

def main():
    """Test both payload formats on both memory agent ports."""
    results = []
    
    for port in TEST_PORTS:
        for payload in PAYLOAD_FORMATS:
            success, response = test_memory_agent(port, payload)
            results.append({
                "port": port,
                "payload": payload,
                "success": success,
                "response": response
            })
            # Wait between requests
            time.sleep(1)
    
    # Print summary
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.WHITE}MEMORY AGENT PROTOCOL TEST RESULTS:")
    print(f"{Fore.CYAN}{'='*50}")
    
    for result in results:
        port = result["port"]
        payload_type = "action" if "action" in result["payload"] else "request_type"
        success_str = f"{Fore.GREEN}SUCCESS" if result["success"] else f"{Fore.RED}FAILED"
        print(f"Port {port} + {payload_type}: {success_str}")
        if result["response"]:
            if "error" in result["response"].get("status", "") or \
               "error" in result["response"].get("message", ""):
                print(f"  {Fore.YELLOW}Response indicates error: {result['response']}")
            else:
                print(f"  {Fore.GREEN}Valid response: {result['response']}")
    
    print(f"\n{Fore.CYAN}RECOMMENDATIONS:")
    action_works = any(r["success"] and "action" in r["payload"] for r in results)
    request_type_works = any(r["success"] and "request_type" in r["payload"] for r in results)
    
    if action_works and not request_type_works:
        print(f"{Fore.YELLOW}- Update verification script to use 'action' format")
    elif request_type_works and not action_works:
        print(f"{Fore.YELLOW}- Update verification script to use 'request_type' format")
    elif not action_works and not request_type_works:
        print(f"{Fore.RED}- Memory agent not responding to either format - check if it's running")
    else:
        print(f"{Fore.GREEN}- Both formats work! No changes needed.")

if __name__ == "__main__":
    main()
