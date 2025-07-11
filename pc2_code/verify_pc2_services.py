#!/usr/bin/env python3
"""
PC2 Services Verification Script
===============================
Critical system verification tool for checking all 11 essential PC2 ZMQ services
using their exact required health check protocols.

This script tests each service with its specific health check payload format
and provides detailed diagnostic information.
"""

import zmq
import json
import time
import socket
from datetime import datetime
import sys
import os
from pathlib import Path
import threading
import colorama
from colorama import Fore, Style
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip

# Initialize colorama for colored terminal output
colorama.init()

# Verification timestamp
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Define timeout for ZMQ requests (milliseconds)
REQUEST_TIMEOUT = 2000  # 2 seconds 

# Define all PC2 services to test with their correct health check payloads
PC2_SERVICES = [
    {
        "name": "Primary Translator",
        "script": "translator_simple.py", 
        "port": 5563,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "TRANSLATION"
    },
    {
        "name": "Fallback Translator",
        "script": "quick_translator_fix.py",
        "port": 5564,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "TRANSLATION"
    },
    {
        "name": "NLLB Translation Adapter",
        "script": "nllb_translation_adapter.py",
        "port": 5581,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "TRANSLATION"
    },
    {
        "name": "TinyLlama Service",
        "script": "tinyllama_service_enhanced.py",
        "port": 5615,
        "health_check_payload": "health_check",
        "expected_pattern": "ok",
        "category": "LLM"
    },
    {
        "name": "Memory Agent (Consolidated)",
        "script": "agents/memory.py",
        "port": 5590,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "MEMORY"
    },
    {
        "name": "Memory Agent Health Port",
        "script": "agents/memory.py", 
        "port": 5598,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "MEMORY"
    },
    {
        "name": "Contextual Memory Agent",
        "script": "agents/contextual_memory_agent.py",
        "port": 5596,
        "health_check_payload": {"action": "get_context", "session_id": "health_check"},
        "expected_pattern": "context",
        "category": "MEMORY"
    },
    {
        "name": "Digital Twin Agent",
        "script": "agents/digital_twin_agent.py",
        "port": 5597,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "MEMORY"
    },
    {
        "name": "Error Pattern Memory",
        "script": "agents/error_pattern_memory.py",
        "port": 5611,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "MEMORY"
    },
    {
        "name": "Context Summarizer Agent",
        "script": "agents/context_summarizer_agent.py",
        "port": 5610,
        "health_check_payload": {"action": "health_check"},
        "expected_pattern": "ok",
        "category": "SUMMARIZATION"
    },
    {
        "name": "Chain of Thought Agent",
        "script": "agents/chain_of_thought_agent.py",
        "port": 5612,
        "health_check_payload": {"action": "breakdown", "request": "health_check"},
        "expected_pattern": "ok",
        "category": "REASONING"
    },
    {
        "name": "Remote Connector Agent",
        "script": "agents/remote_connector_agent.py",
        "port": 5557,
        "health_check_payload": {"request_type": "check_status", "model": "phi3"},
        "expected_pattern": "success",
        "category": "CONNECTOR"
    }
]

# Additional verification to check for port conflicts
def check_port_in_use(port):
    """Check if a port is already in use on this system"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# Verify a specific ZMQ service
def verify_service(service, context):
    """Send health check to a service and verify its response"""
    
    port_in_use = check_port_in_use(service["port"])
    
    if not port_in_use:
        return {
            "name": service["name"],
            "port": service["port"],
            "status": "PORT_NOT_ACTIVE",
            "response": None,
            "response_time_ms": 0,
            "notes": f"Port {service['port']} is not open on the system"
        }
    
    # Create socket and set timeout
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, REQUEST_TIMEOUT)
    socket.connect(get_zmq_connection_string({service[, "localhost"))port']}")
    
    # Measure response time
    start_time = time.time()
    
    try:
        # Send health check payload in the correct format
        socket.send_json(service["health_check_payload"])
        
        # Wait for response with timeout
        response = socket.recv_json()
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Check if response matches expected pattern
        if isinstance(response, dict):
            response_str = json.dumps(response)
        else:
            response_str = str(response)
            
        if service["expected_pattern"] in response_str.lower():
            status = "HEALTHY"
            notes = "Service responded correctly"
        else:
            status = "ERROR_RESPONSE"
            notes = f"Response doesn't match expected pattern '{service['expected_pattern']}'"
        
        return {
            "name": service["name"],
            "port": service["port"],
            "status": status,
            "response": response,
            "response_time_ms": response_time_ms,
            "notes": notes
        }
        
    except zmq.error.Again:
        # Timeout occurred
        return {
            "name": service["name"],
            "port": service["port"],
            "status": "TIMEOUT",
            "response": None,
            "response_time_ms": REQUEST_TIMEOUT,
            "notes": f"Request timed out after {REQUEST_TIMEOUT}ms"
        }
    except Exception as e:
        # Other error occurred
        return {
            "name": service["name"],
            "port": service["port"],
            "status": "ERROR",
            "response": None,
            "response_time_ms": 0,
            "notes": f"Error: {str(e)}"
        }
    finally:
        socket.close()

def color_status(status):
    """Return colored status text"""
    if status == "HEALTHY":
        return f"{Fore.GREEN}{status}{Style.RESET_ALL}"
    elif status == "TIMEOUT":
        return f"{Fore.RED}{status}{Style.RESET_ALL}"
    elif status == "ERROR" or status == "ERROR_RESPONSE":
        return f"{Fore.RED}{status}{Style.RESET_ALL}"
    elif status == "PORT_NOT_ACTIVE":
        return f"{Fore.YELLOW}{status}{Style.RESET_ALL}"
    else:
        return status

def print_service_result(result):
    """Print formatted service verification result"""
    print(f"\n{Fore.CYAN}■ {result['name']} (Port {result['port']}){Style.RESET_ALL}")
    print(f"  Status: {color_status(result['status'])}")
    print(f"  Response Time: {result['response_time_ms']}ms")
    print(f"  Notes: {result['notes']}")
    
    if result['response']:
        if isinstance(result['response'], dict):
            # Pretty print JSON response
            response_str = json.dumps(result['response'], indent=2)
            print(f"  Response: {response_str}")
        else:
            print(f"  Response: {result['response']}")

def generate_source_of_truth_entry(service, result):
    """Generate a markdown entry for the source of truth document"""
    status_icon = "✅" if result["status"] == "HEALTHY" else "❌"
    
    # Format health check payload for display
    if isinstance(service["health_check_payload"], dict):
        payload_str = json.dumps(service["health_check_payload"])
    else:
        payload_str = f'"{service["health_check_payload"]}"'
    
    # Format expected response for display
    expected_response = service["expected_pattern"]
    if expected_response:
        expected_response_str = f'"{expected_response}"'
    else:
        expected_response_str = "N/A"
    
    # Construct full path
    script_path = service["script"]
    
    # Format the actual response
    if result["status"] == "HEALTHY" and result["response"]:
        if isinstance(result["response"], dict):
            response_pattern = json.dumps(result["response"])
        else:
            response_pattern = str(result["response"])
    else:
        response_pattern = "N/A"
    
    return (
        f"| **{service['name']}** | `{script_path}` | {service['port']} | 0.0.0.0 | "
        f"{status_icon} {result['status']} | {payload_str} | {response_pattern} |"
    )

def main():
    """Main verification function"""
    print(f"\n{Fore.WHITE}{Style.BRIGHT}PC2 SERVICES VERIFICATION TOOL{Style.RESET_ALL}")
    print(f"{Fore.WHITE}=============================")
    print(f"Timestamp: {TIMESTAMP}{Style.RESET_ALL}\n")
    
    # Create ZMQ context
    context = zmq.Context()
    
    # Track results by category
    results_by_category = {}
    
    # Total counts
    total_services = len(PC2_SERVICES)
    healthy_services = 0
    problem_services = 0
    
    # Verify each service
    results = []
    for service in PC2_SERVICES:
        category = service.get("category", "OTHER")
        
        if category not in results_by_category:
            results_by_category[category] = []
        
        result = verify_service(service, context)
        results.append(result)
        results_by_category[category].append((service, result))
        
        if result["status"] == "HEALTHY":
            healthy_services += 1
        else:
            problem_services += 1
        
        print_service_result(result)
    
    # Print summary
    print(f"\n{Fore.WHITE}{Style.BRIGHT}VERIFICATION SUMMARY{Style.RESET_ALL}")
    print(f"{Fore.WHITE}===================={Style.RESET_ALL}")
    print(f"Total Services: {total_services}")
    print(f"Healthy: {Fore.GREEN}{healthy_services}{Style.RESET_ALL}")
    print(f"Problems: {Fore.RED}{problem_services}{Style.RESET_ALL}")
    
    # Generate Source of Truth markdown
    sot_filename = f"docs/pc2/PC2_SYSTEM_SOURCE_OF_TRUTH_VERIFIED_{datetime.now().strftime('%Y-%m-%d')}.md"
    
    print(f"\n{Fore.WHITE}{Style.BRIGHT}GENERATING SOURCE OF TRUTH DOCUMENT{Style.RESET_ALL}")
    print(f"{Fore.WHITE}====================================={Style.RESET_ALL}")
    print(f"File: {sot_filename}")
    
    with open(sot_filename, "w") as f:
        f.write(f"# PC2 SYSTEM SOURCE OF TRUTH - VERIFIED {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("This document serves as the definitive reference for all essential PC2 services.\n")
        f.write("It was automatically generated by the PC2 verification tool and contains verified port numbers,\n")
        f.write("health check payloads, and expected responses for each service.\n\n")
        
        f.write("## VERIFICATION SUMMARY\n\n")
        f.write(f"- **Verification Time**: {TIMESTAMP}\n")
        f.write(f"- **Total Services**: {total_services}\n")
        f.write(f"- **Healthy Services**: {healthy_services}\n")
        f.write(f"- **Problem Services**: {problem_services}\n\n")
        
        for category, services in results_by_category.items():
            f.write(f"## {category} SERVICES\n\n")
            f.write("| Service Name | Script Path | Port | Bind Address | Status | Health Check Payload | Expected Response |\n")
            f.write("|-------------|-------------|------|--------------|--------|----------------------|--------------------|\n")
            
            for service, result in services:
                entry = generate_source_of_truth_entry(service, result)
                f.write(f"{entry}\n")
            
            f.write("\n")
        
        f.write("## HEALTH CHECK PROTOCOL\n\n")
        f.write("To perform health checks on these services, use the exact health check payload format specified for each service.\n")
        f.write("This can be done using the `verify_pc2_services.py` script or by sending the appropriate ZMQ message directly.\n\n")
        
        f.write("## NOTES FOR MAIN PC MMA CONFIGURATION\n\n")
        f.write("When configuring the Main PC Model Manager Agent (MMA) to monitor these services:\n\n")
        f.write("1. Use the exact port numbers specified in this document\n")
        f.write("2. Configure each service with its specific health check payload format\n")
        f.write("3. Look for the expected response pattern in the service's reply\n")
        f.write("4. Set appropriate timeouts (recommended: 2000ms)\n")
        f.write("5. For any service listed as non-healthy, resolve the issue before final deployment\n\n")
        
        f.write("## DEPRECATED SERVICES\n\n")
        f.write("These services are no longer considered essential and should not be monitored:\n\n")
        f.write("- `agents/Deprecated agent/jarvis_memory_agent.py` (replaced by consolidated memory.py)\n")
        f.write("- `agents/Deprecated agent/memory_agent.py` (replaced by consolidated memory.py)\n")
        f.write("- `agents/filesystem_assistant_agent.py` (non-essential for main functionality)\n")
        f.write("- `agents/bark_tts_agent.py` (non-essential for main functionality)\n\n")
        
        f.write("## ADDITIONAL INFORMATION\n\n")
        f.write("For details on service startup procedures, dependencies, and troubleshooting,\n")
        f.write("refer to the documentation in the `docs/pc2` directory.\n\n")
        
        f.write("---\n\n")
        f.write("This document was automatically generated by the PC2 verification tool and serves as the\n")
        f.write("definitive reference for the Main PC MMA configuration. Do not edit manually.\n")
    
    print(f"\n{Fore.GREEN}Source of Truth document generated: {sot_filename}{Style.RESET_ALL}")
    print(f"\n{Fore.WHITE}{Style.BRIGHT}VERIFICATION COMPLETE{Style.RESET_ALL}")
    
if __name__ == "__main__":
    main()
