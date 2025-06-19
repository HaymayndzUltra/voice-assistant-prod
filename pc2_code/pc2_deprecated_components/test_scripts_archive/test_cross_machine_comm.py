"""
Cross-Machine Communication Test
-------------------------------
Tests the connection between Main PC and PC2 using the ZMQ Bridge
Verifies code generation requests are properly routed from PC2 to Main PC
"""
import os
import sys
import time
import json
import zmq
import argparse
import socket
from pathlib import Path
from datetime import datetime
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init()

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

# Try to load configuration
try:
    with open(os.path.join(parent_dir, "config", "config.json"), "r") as f:
        config = json.load(f)
except Exception as e:
    print(f"{Fore.RED}Error loading config.json: {e}{Style.RESET_ALL}")
    config = {}

try:
    with open(os.path.join(parent_dir, "config", "distributed_config.json"), "r") as f:
        distributed_config = json.load(f)
except Exception as e:
    print(f"{Fore.RED}Error loading distributed_config.json: {e}{Style.RESET_ALL}")
    distributed_config = {}

# ZMQ Bridge Configuration
ZMQ_BRIDGE_PORT = distributed_config.get("zmq_bridge", {}).get("port", 5600)
PC2_IP = distributed_config.get("pc2", {}).get("ip", "192.168.1.2")
MAIN_PC_IP = distributed_config.get("main_pc", {}).get("ip", "192.168.1.27")

# Test Configuration
TEST_TIMEOUT = 5  # seconds
ROUTE_COMPONENTS = [
    {
        "name": "ZMQ Bridge",
        "port": ZMQ_BRIDGE_PORT,
        "machine": "both"
    },
    {
        "name": "Code Generator",
        "port": distributed_config.get("ports", {}).get("code_generator_agent", 6000),
        "machine": "main_pc"
    },
    {
        "name": "Remote Connector",
        "port": distributed_config.get("ports", {}).get("remote_connector_agent", 5557),
        "machine": "pc2"
    },
    {
        "name": "Task Router",
        "port": distributed_config.get("ports", {}).get("task_router_agent", 5558),
        "machine": "pc2"
    },
    {
        "name": "LLM Translation Adapter",
        "port": distributed_config.get("ports", {}).get("llm_translation_adapter", 5581),
        "machine": "pc2"
    }
]

def check_local_port(port):
    """Check if a local port is open (has a service listening)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def check_remote_port(ip, port):
    """Check if a remote port is open (has a service listening)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((ip, port))
    sock.close()
    return result == 0

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a public DNS to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def test_zmq_bridge(mode="receive"):
    """Test the ZMQ Bridge between Main PC and PC2"""
    print(f"\n{Fore.CYAN}=== Testing ZMQ Bridge (Port {ZMQ_BRIDGE_PORT}) ==={Style.RESET_ALL}")
    
    local_ip = get_local_ip()
    print(f"Local IP: {local_ip}")
    
    if mode == "receive":
        # Set up ZMQ server to receive messages
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://*:{ZMQ_BRIDGE_PORT}")
        print(f"{Fore.YELLOW}Listening for messages on port {ZMQ_BRIDGE_PORT}...{Style.RESET_ALL}")
        print(f"Other machine should run: python test_cross_machine_comm.py --mode send --ip {local_ip}")
        
        try:
            socket.setsockopt(zmq.RCVTIMEO, TEST_TIMEOUT * 1000)
            message = socket.recv_json()
            print(f"{Fore.GREEN}Received message: {message}{Style.RESET_ALL}")
            
            # Send response
            response = {
                "status": "success",
                "message": "Response from ZMQ Bridge",
                "timestamp": datetime.now().isoformat(),
                "ip": local_ip
            }
            socket.send_json(response)
            print(f"{Fore.GREEN}Sent response: {response}{Style.RESET_ALL}")
            
            # Wait for a second message to test continuous communication
            print(f"{Fore.YELLOW}Waiting for another message...{Style.RESET_ALL}")
            try:
                message2 = socket.recv_json()
                print(f"{Fore.GREEN}Received second message: {message2}{Style.RESET_ALL}")
                socket.send_json({"status": "success", "message": "Second response"})
                print(f"{Fore.GREEN}Test PASSED! Two-way communication successful.{Style.RESET_ALL}")
            except zmq.Again:
                print(f"{Fore.YELLOW}No second message received, but first exchange was successful.{Style.RESET_ALL}")
            
            return True
        except zmq.Again:
            print(f"{Fore.RED}Timeout: No message received within {TEST_TIMEOUT} seconds.{Style.RESET_ALL}")
            return False
        finally:
            socket.close()
            context.term()
    
    elif mode == "send":
        # Set up ZMQ client to send messages
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        
        target_ip = args.ip if args.ip else PC2_IP if local_ip == MAIN_PC_IP else MAIN_PC_IP
        print(f"Connecting to: {target_ip}:{ZMQ_BRIDGE_PORT}")
        
        socket.connect(f"tcp://{target_ip}:{ZMQ_BRIDGE_PORT}")
        socket.setsockopt(zmq.RCVTIMEO, TEST_TIMEOUT * 1000)
        
        try:
            # Send test message
            message = {
                "test": "cross_machine_communication",
                "timestamp": datetime.now().isoformat(),
                "from_ip": local_ip
            }
            print(f"{Fore.YELLOW}Sending message: {message}{Style.RESET_ALL}")
            socket.send_json(message)
            
            # Wait for response
            try:
                response = socket.recv_json()
                print(f"{Fore.GREEN}Received response: {response}{Style.RESET_ALL}")
                
                # Send a second message to test continuous communication
                message2 = {
                    "test": "continuous_communication",
                    "timestamp": datetime.now().isoformat(),
                    "from_ip": local_ip
                }
                print(f"{Fore.YELLOW}Sending second message: {message2}{Style.RESET_ALL}")
                socket.send_json(message2)
                
                try:
                    response2 = socket.recv_json()
                    print(f"{Fore.GREEN}Received second response: {response2}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}Test PASSED! Two-way communication successful.{Style.RESET_ALL}")
                except zmq.Again:
                    print(f"{Fore.YELLOW}No response to second message, but first exchange was successful.{Style.RESET_ALL}")
                
                return True
            except zmq.Again:
                print(f"{Fore.RED}Timeout: No response received within {TEST_TIMEOUT} seconds.{Style.RESET_ALL}")
                return False
        finally:
            socket.close()
            context.term()

def test_route_components():
    """Test if all components in the route are running and accessible"""
    print(f"\n{Fore.CYAN}=== Testing Route Components ==={Style.RESET_ALL}")
    
    local_ip = get_local_ip()
    
    # Determine which machine we're on
    on_main_pc = local_ip == MAIN_PC_IP
    on_pc2 = local_ip == PC2_IP
    
    if not on_main_pc and not on_pc2:
        print(f"{Fore.YELLOW}Cannot determine which machine this is running on.{Style.RESET_ALL}")
        print(f"Local IP: {local_ip}")
        print(f"Expected Main PC IP: {MAIN_PC_IP}")
        print(f"Expected PC2 IP: {PC2_IP}")
        machine = input("Which machine is this? (main_pc/pc2): ")
        on_main_pc = machine.lower() == "main_pc"
        on_pc2 = machine.lower() == "pc2"
    
    machine_type = "main_pc" if on_main_pc else "pc2" if on_pc2 else "unknown"
    print(f"Running on {machine_type.upper()} ({local_ip})")
    
    all_passed = True
    
    for component in ROUTE_COMPONENTS:
        name = component["name"]
        port = component["port"]
        machine = component["machine"]
        
        if machine == "both" or (machine == "main_pc" and on_main_pc) or (machine == "pc2" and on_pc2):
            # Check local component
            print(f"Checking local component: {name} (Port {port})...")
            if check_local_port(port):
                print(f"{Fore.GREEN}✓ {name} is running locally on port {port}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ {name} is NOT running locally on port {port}{Style.RESET_ALL}")
                all_passed = False
        
        if (machine == "main_pc" and on_pc2) or (machine == "pc2" and on_main_pc):
            # Check remote component
            remote_ip = MAIN_PC_IP if machine == "main_pc" else PC2_IP
            print(f"Checking remote component: {name} on {remote_ip}:{port}...")
            if check_remote_port(remote_ip, port):
                print(f"{Fore.GREEN}✓ {name} is accessible remotely on {remote_ip}:{port}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ {name} is NOT accessible remotely on {remote_ip}:{port}{Style.RESET_ALL}")
                all_passed = False
    
    return all_passed

def test_code_generation_routing():
    """Test if code generation requests are properly routed from PC2 to Main PC"""
    print(f"\n{Fore.CYAN}=== Testing Code Generation Routing ==={Style.RESET_ALL}")
    
    local_ip = get_local_ip()
    
    # This test should be run from PC2
    if local_ip != PC2_IP:
        print(f"{Fore.YELLOW}This test should be run from PC2 ({PC2_IP}).{Style.RESET_ALL}")
        print(f"Current IP: {local_ip}")
        proceed = input("Continue anyway? (y/n): ")
        if proceed.lower() != "y":
            return False
    
    # Set up ZMQ client to send code generation request through remote connector
    remote_connector_port = distributed_config.get("ports", {}).get("remote_connector_agent", 5557)
    
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{remote_connector_port}")
    socket.setsockopt(zmq.RCVTIMEO, TEST_TIMEOUT * 1000)
    
    try:
        # Simple code generation request
        code_request = {
            "type": "code_generation",
            "prompt": "Write a simple hello world function in Python",
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"{Fore.YELLOW}Sending code generation request through Remote Connector...{Style.RESET_ALL}")
        socket.send_json(code_request)
        
        try:
            response = socket.recv_json()
            print(f"{Fore.GREEN}Received response: {response}{Style.RESET_ALL}")
            
            if response.get("status") == "success" or "code" in response:
                print(f"{Fore.GREEN}Test PASSED! Code generation request was properly routed.{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Test FAILED! Received response but without expected code content.{Style.RESET_ALL}")
                return False
        except zmq.Again:
            print(f"{Fore.RED}Timeout: No response received within {TEST_TIMEOUT} seconds.{Style.RESET_ALL}")
            print("This may indicate that the request did not reach the Code Generator on Main PC.")
            return False
    finally:
        socket.close()
        context.term()

def test_translation_adapter():
    """Test if the LLM Translation Adapter is working properly"""
    print(f"\n{Fore.CYAN}=== Testing LLM Translation Adapter ==={Style.RESET_ALL}")
    
    local_ip = get_local_ip()
    
    # This can be run from either machine, but we need to know which one
    on_pc2 = local_ip == PC2_IP
    
    # Connect to LLM Translation Adapter (on PC2 or remote)
    adapter_port = distributed_config.get("ports", {}).get("llm_translation_adapter", 5581)
    adapter_ip = "localhost" if on_pc2 else PC2_IP
    
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://{adapter_ip}:{adapter_port}")
    socket.setsockopt(zmq.RCVTIMEO, TEST_TIMEOUT * 1000)
    
    try:
        # Simple translation request (Tagalog to English)
        translation_request = {
            "text": "Kumusta ka? Maganda ang araw ngayon.",
            "source_lang": "tl",
            "target_lang": "en"
        }
        
        print(f"{Fore.YELLOW}Sending translation request to LLM Adapter at {adapter_ip}:{adapter_port}...{Style.RESET_ALL}")
        socket.send_json(translation_request)
        
        try:
            response = socket.recv_json()
            print(f"{Fore.GREEN}Received response: {response}{Style.RESET_ALL}")
            
            if response.get("success") == True and "translated" in response:
                print(f"{Fore.GREEN}Test PASSED! Translation request was successful.{Style.RESET_ALL}")
                print(f"Original: {translation_request['text']}")
                print(f"Translated: {response['translated']}")
                return True
            else:
                print(f"{Fore.RED}Test FAILED! Translation response indicates failure.{Style.RESET_ALL}")
                print(f"Error: {response.get('message', 'Unknown error')}")
                return False
        except zmq.Again:
            print(f"{Fore.RED}Timeout: No response received within {TEST_TIMEOUT} seconds.{Style.RESET_ALL}")
            return False
    finally:
        socket.close()
        context.term()

def run_all_tests():
    """Run all cross-machine communication tests"""
    results = {}
    
    # Test route components
    results["route_components"] = test_route_components()
    
    # Test translation adapter (most commonly used cross-machine component)
    results["translation_adapter"] = test_translation_adapter()
    
    # Test code generation routing (only if on PC2)
    if get_local_ip() == PC2_IP:
        results["code_generation"] = test_code_generation_routing()
    
    # Print summary
    print(f"\n{Fore.CYAN}=== Test Summary ==={Style.RESET_ALL}")
    all_passed = True
    
    for test, result in results.items():
        status = f"{Fore.GREEN}PASSED{Style.RESET_ALL}" if result else f"{Fore.RED}FAILED{Style.RESET_ALL}"
        print(f"{test}: {status}")
        all_passed = all_passed and result
    
    if all_passed:
        print(f"\n{Fore.GREEN}All tests PASSED! Cross-machine communication is working properly.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}Some tests FAILED. Please check the issues above.{Style.RESET_ALL}")
    
    return all_passed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test cross-machine communication between Main PC and PC2")
    parser.add_argument("--mode", choices=["send", "receive", "all"], default="all", help="Test mode (send/receive/all)")
    parser.add_argument("--ip", help="IP address of the target machine")
    parser.add_argument("--port", type=int, default=ZMQ_BRIDGE_PORT, help="Port to use for ZMQ bridge test")
    parser.add_argument("--test", choices=["bridge", "components", "code", "translation", "all"], default="all", help="Which test to run")
    
    args = parser.parse_args()
    
    if args.port:
        ZMQ_BRIDGE_PORT = args.port
    
    if args.test == "bridge":
        if args.mode == "all":
            print("For bridge test, please specify --mode as 'send' or 'receive'")
        else:
            test_zmq_bridge(args.mode)
    elif args.test == "components":
        test_route_components()
    elif args.test == "code":
        test_code_generation_routing()
    elif args.test == "translation":
        test_translation_adapter()
    else:  # all tests
        if args.mode == "all":
            run_all_tests()
        else:
            test_zmq_bridge(args.mode)
