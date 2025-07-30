#!/usr/bin/env python3
"""
PC2 Health Check Tool

This script provides a comprehensive health check for all active PC2 agents:
1. Translator Agent (port 5563)
2. NLLB Translation Adapter (port 5581)
3. TinyLlama Service (port 5615)

It tests connectivity, checks service status, and verifies basic functionality
of each service. The script can be run from PC2 locally or from Main PC remotely
by changing the host parameter.

Usage:
    python pc2_health_check.py [--host PC2_IP_ADDRESS]
"""

import zmq
import json
import time
import argparse
import socket
from tabulate import tabulate
import sys
from colorama import init, Fore, Style
from common.env_helpers import get_env

# Initialize colorama for colored terminal output
init()

def check_port_open(host, port):
    """Check if a port is open on the given host."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def send_zmq_request(host, port, request, timeout=5000, retries=1, retry_delay=2):
    """Send a ZMQ request and return the response with retry logic."""
    for attempt in range(retries + 1):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        
        # Add connection debug logging
        print(f"Connecting to {host}:{port} (attempt {attempt+1}/{retries+1})")
        socket.connect(f"tcp://{host}:{port}")
        
        try:
            print(f"Sending request to {host}:{port}: {request}")
            socket.send_json(request)
            response = socket.recv_json()
            print(f"Received response from {host}:{port}")
            return response
        except zmq.error.Again:
            if attempt < retries:
                print(f"Request to {host}:{port} timed out, retrying in {retry_delay}s... ({attempt+1}/{retries})")
                time.sleep(retry_delay)
            else:
                print(f"Request to {host}:{port} timed out after {retries+1} attempts")
                return {"status": "error", "message": "Request timed out after multiple attempts"}
        except Exception as e:
            print(f"Error communicating with {host}:{port}: {str(e)}")
            return {"status": "error", "message": f"Error: {str(e)}"}
        finally:
            socket.close()
            context.term()

def check_translator_agent(host):
    """Check Translator Agent health and functionality."""
    port = 5563
    results = {
        "name": "Translator Agent",
        "port": port,
        "host": host,
        "port_status": check_port_open(host, port),
        "health_check": None,
        "translation_test": None
    }
    
    if results["port_status"]:
        # Health check
        results["health_check"] = send_zmq_request(host, port, {"action": "health_check"})
        
        # Simple translation test
        translation_request = {
            "action": "translate", 
            "text": "Buksan mo ang file", 
            "source_lang": "tl", 
            "target_lang": "en", 
            "session_id": "health_check_session", 
            "request_id": "health_check_1"
        }
        results["translation_test"] = send_zmq_request(host, port, translation_request)
    
    return results

def check_nllb_adapter(host):
    """Check NLLB Translation Adapter functionality."""
    port = 5581
    results = {
        "name": "NLLB Translation Adapter",
        "port": port,
        "host": host,
        "port_status": check_port_open(host, port),
        "health_check": None,
        "translation_test": None
    }
    
    if results["port_status"]:
        # NLLB doesn't have a health check endpoint
        results["health_check"] = {"status": "not_supported", "message": "NLLB adapter doesn't support health_check action"}
        
        # Translation test
        translation_request = {
            "action": "translate", 
            "text": "Magandang umaga po", 
            "source_lang": "tgl_Latn", 
            "target_lang": "eng_Latn"
        }
        results["translation_test"] = send_zmq_request(host, port, translation_request, timeout=30000)  # Longer timeout for model loading
    
    return results

def check_tinyllama_service(host):
    """Check TinyLlama Service health."""
    port = 5615
    results = {
        "name": "TinyLlama Service",
        "port": port,
        "host": host,
        "port_status": check_port_open(host, port),
        "health_check": None
    }
    
    if results["port_status"]:
        # Health check
        results["health_check"] = send_zmq_request(host, port, {"action": "health_check"})
    
    return results

def display_results(results):
    """Display health check results in a formatted table."""
    print(f"\n{Fore.CYAN}PC2 SERVICES HEALTH CHECK RESULTS{Style.RESET_ALL}\n")
    
    summary_rows = []
    for service in results:
        status = "Unknown"
        details = ""
        
        if not service["port_status"]:
            status = f"{Fore.RED}CLOSED{Style.RESET_ALL}"
        elif service["name"] == "TinyLlama Service":
            if service["health_check"] and service["health_check"].get("status") == "ok":
                status = f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}"
                details = f"Model: {service['health_check'].get('model_status', 'unknown')}, Device: {service['health_check'].get('device', 'unknown')}"
            else:
                status = f"{Fore.RED}ERROR{Style.RESET_ALL}"
                details = service["health_check"].get("message", "Unknown error") if service["health_check"] else "No response"
        else:
            # Translator Agent and NLLB Adapter
            if service["translation_test"] and service["translation_test"].get("status") == "success":
                status = f"{Fore.GREEN}ACTIVE{Style.RESET_ALL}"
                if service["name"] == "Translator Agent":
                    if service["health_check"] and service["health_check"].get("status") == "success":
                        uptime = service["health_check"].get("uptime_seconds", 0)
                        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
                        details = f"Uptime: {uptime_str}, Requests: {service['health_check'].get('total_requests', 'unknown')}"
                    else:
                        details = "Translation working, health check failed"
                else:  # NLLB Adapter
                    translation = service["translation_test"].get("translated_text", "N/A")
                    details = f"Translation: '{translation}'"
            else:
                status = f"{Fore.RED}ERROR{Style.RESET_ALL}"
                details = service["translation_test"].get("message", "Unknown error") if service["translation_test"] else "No response"
        
        summary_rows.append([
            service["name"],
            f"tcp://{service['host']}:{service['port']}",
            status,
            details
        ])
    
    print(tabulate(summary_rows, headers=["Service", "Address", "Status", "Details"], tablefmt="grid"))
    
    # Overall status
    all_active = all(service["port_status"] for service in results)
    if all_active:
        print(f"\n{Fore.GREEN}[PASS] All PC2 services are active and accessible.{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}[FAIL] Some PC2 services are not accessible.{Style.RESET_ALL}")
    
    # Display detailed results for each service
    for service in results:
        print(f"\n{Fore.YELLOW}{'=' * 70}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}DETAILED RESULTS FOR {service['name']}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'=' * 70}{Style.RESET_ALL}")
        
        if not service["port_status"]:
            print(f"{Fore.RED}Port {service['port']} is CLOSED on {service['host']}{Style.RESET_ALL}")
            continue
        
        print(f"{Fore.GREEN}Port {service['port']} is OPEN on {service['host']}{Style.RESET_ALL}")
        
        if service["health_check"]:
            print(f"\n{Fore.CYAN}Health Check Response:{Style.RESET_ALL}")
            print(json.dumps(service["health_check"], indent=2))
        
        if service.get("translation_test"):
            print(f"\n{Fore.CYAN}Translation Test Response:{Style.RESET_ALL}")
            print(json.dumps(service["translation_test"], indent=2))

def main():
    parser = argparse.ArgumentParser(description="PC2 Health Check Tool")
    parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), help="PC2 host address (default: localhost)")
    args = parser.parse_args()
    
    print(f"\n{Fore.CYAN}Starting PC2 Health Check...{Style.RESET_ALL}")
    print(f"Target host: {args.host}")
    
    try:
        results = []
        
        # Check all services
        print(f"\n{Fore.YELLOW}Checking Translator Agent...{Style.RESET_ALL}")
        results.append(check_translator_agent(args.host))
        
        print(f"\n{Fore.YELLOW}Checking NLLB Translation Adapter...{Style.RESET_ALL}")
        results.append(check_nllb_adapter(args.host))
        
        print(f"\n{Fore.YELLOW}Checking TinyLlama Service...{Style.RESET_ALL}")
        results.append(check_tinyllama_service(args.host))
        
        # Display results
        display_results(results)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Health check interrupted by user.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error during health check: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()
