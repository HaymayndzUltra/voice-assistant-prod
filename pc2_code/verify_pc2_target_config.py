#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PC2 TARGET CONFIGURATION VERIFICATION TOOL
==========================================
This script verifies all essential PC2 services against the official target configuration
as specified by the Main PC Model Manager Agent requirements.
"""

import zmq
import json
import socket
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from common.env_helpers import get_env

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Create docs directory if it doesn't exist
Path("docs/pc2").mkdir(parents=True, exist_ok=True)

# Service definitions based on TARGET CONFIGURATION
SERVICES = [
    {
        "name": "Primary Translator",
        "script": "agents/translator_agent.py",
        "port": int(os.getenv('TRANSLATOR_PORT', '5563')),
        "bind_address": "0.0.0.0",
        "health_check_payload": {"action": "health_check"},
        "expected_response_pattern": ["status", "ok", "success"],
        "notes": "Enhanced translator with pattern matching and fallbacks"
    },
    {
        "name": "Fallback Translator",
        "script": "quick_translator_fix.py",
        "port": 5564,
        "bind_address": "0.0.0.0",
        "health_check_payload": {"action": "health_check"},
        "expected_response_pattern": ["status", "ok", "success"],
        "notes": "Simple pattern-based translator that works without internet"
    },
    {
        "name": "NLLB Translation Adapter",
        "script": "nllb_translation_adapter.py",
        "port": int(os.getenv('NLLB_ADAPTER_PORT', '5581')),
        "bind_address": "0.0.0.0",
        "health_check_payload": {
            "action": "translate", 
            "text": "ping_hc_nllb_final", 
            "source_lang": "tgl_Latn", 
            "target_lang": "eng_Latn"
        },
        "expected_response_pattern": ["status"],  # Any valid JSON response
        "notes": "Neural machine translation using Facebook's NLLB model"
    },
    {
        "name": "TinyLlama Service",
        "script": "agents/tinyllama_service_enhanced.py",
        "port": 5615,
        "bind_address": "0.0.0.0",
        "health_check_payload": {"action": "health_check"},
        "expected_response_pattern": ["status", "ok"],
        "notes": "Lightweight LLM for fast responses and fallbacks"
    },
    {
        "name": "Memory Agent (Consolidated)",
        "script": "agents/memory.py",
        "port": 5590,
        "bind_address": "0.0.0.0",
        "health_check_payload": {"action": "health_check"},
        "expected_response_pattern": ["status", "ok", "success"],
        "notes": "Main memory operations port"
    },
    {
        "name": "Memory Agent Health Port",
        "script": "agents/memory.py (health port)",
        "port": int(os.getenv('EMR_PORT', '5598')),
        "bind_address": "0.0.0.0",
        "health_check_payload": {"action": "health_check"},
        "expected_response_pattern": ["status", "ok", "success"],
        "notes": "Dedicated health check port monitored by MMA"
    },
    {
        "name": "Contextual Memory Agent",
        "script": "agents/contextual_memory_agent.py",
        "port": 5596,
        "bind_address": "0.0.0.0",
        "health_check_payload": {},  # Connection-based check
        "expected_response_pattern": ["status", "ok"],
        "notes": "Advanced context management and summarization"
    },
    {
        "name": "Digital Twin Agent",
        "script": "agents/digital_twin_agent.py",
        "port": 5597,
        "bind_address": "0.0.0.0", 
        "health_check_payload": {},  # Connection-based check
        "expected_response_pattern": ["status", "ok"],
        "notes": "User modeling and behavioral analysis"
    },
    {
        "name": "Error Pattern Memory",
        "script": "agents/error_pattern_memory.py",
        "port": 5611,
        "bind_address": "0.0.0.0",
        "health_check_payload": {},  # Connection-based check
        "expected_response_pattern": ["status", "ok"],
        "notes": "Tracks error patterns and solutions"
    },
    {
        "name": "Context Summarizer Agent",
        "script": "agents/context_summarizer_agent.py",
        "port": 5610,
        "bind_address": "0.0.0.0",
        "health_check_payload": {},  # Connection-based check
        "expected_response_pattern": ["status", "ok"],
        "notes": "Provides summarization of conversation context"
    },
    {
        "name": "Chain of Thought Agent",
        "script": "agents/chain_of_thought_agent.py",
        "port": 5612,
        "bind_address": "0.0.0.0",
        "health_check_payload": {"action": "breakdown", "request": "health_check"},
        "expected_response_pattern": ["status", "ok"],
        "notes": "Provides multi-step reasoning for complex tasks"
    },
    {
        "name": "Remote Connector Agent",
        "script": "agents/remote_connector_agent.py",
        "port": int(os.getenv('REMOTE_CONNECTOR_PORT', '5557')),
        "bind_address": "0.0.0.0",
        "health_check_payload": {"request_type": "check_status", "model": "phi3"},
        "expected_response_pattern": ["status", "success"],
        "notes": "Manages direct model inference and caching"
    }
]

def is_port_open(port, host='localhost'):
    """Check if a port is open on the specified host"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def check_service_health(service):
    """Check health of a service using its health check mechanism"""
    port = service["port"]
    
    # Check if port is open
    if not is_port_open(port):
        return {
            "status": "PORT_NOT_ACTIVE",
            "response_time": 0,
            "notes": f"Port {port} is not open on the system",
            "response": None
        }
    
    # Connect to service
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second timeout
    socket.connect(f"tcp://localhost:{port}")
    
    try:
        # Send health check payload
        start_time = time.time()
        socket.send_json(service["health_check_payload"])
        
        # Get response
        response = socket.recv_json()
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)  # ms
        
        # Check if response contains expected pattern
        if isinstance(response, dict):
            # Check if any of the expected values are present
            pattern_matched = False
            for key in response.keys():
                if key in service["expected_response_pattern"]:
                    pattern_matched = True
                    break
                    
            if "status" in response:
                status_value = response["status"]
                if status_value in service["expected_response_pattern"]:
                    pattern_matched = True
            
            if pattern_matched:
                return {
                    "status": "HEALTHY",
                    "response_time": response_time,
                    "notes": "Service responded correctly",
                    "response": response
                }
            else:
                return {
                    "status": "ERROR_RESPONSE",
                    "response_time": response_time,
                    "notes": f"Response doesn't match expected pattern '{', '.join(service['expected_response_pattern'])}'",
                    "response": response
                }
        else:
            return {
                "status": "INVALID_RESPONSE",
                "response_time": response_time,
                "notes": "Response is not a valid JSON object",
                "response": response
            }
            
    except zmq.error.Again:
        # Timeout
        return {
            "status": "TIMEOUT",
            "response_time": 3000,
            "notes": "Service timed out after 3 seconds",
            "response": None
        }
    except Exception as e:
        # Other error
        return {
            "status": "ERROR",
            "response_time": 0,
            "notes": f"Error communicating with service: {str(e)}",
            "response": None
        }
    finally:
        socket.close()
        context.term()

def print_service_status(service, result):
    """Print service status with colors"""
    name = service["name"]
    port = service["port"]
    
    if result["status"] == "HEALTHY":
        status_color = Colors.OKGREEN
        status_symbol = "✓"
    else:
        status_color = Colors.FAIL
        status_symbol = "✗"
    
    print(f"\n{Colors.BOLD}■ {name} (Port {port}){Colors.ENDC}")
    print(f"  Status: {status_color}{result['status']}{Colors.ENDC}")
    print(f"  Response Time: {result['response_time']}ms")
    print(f"  Notes: {result['notes']}")
    
    if result["response"]:
        print(f"  Response: {json.dumps(result['response'], indent=2)}")

def generate_source_of_truth_doc(services, results):
    """Generate a Markdown document with the source of truth for all services"""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"docs/pc2/PC2_SYSTEM_SOURCE_OF_TRUTH_VERIFIED_{timestamp}.md"
    
    healthy_count = sum(1 for r in results if r["status"] == "HEALTHY")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# PC2 SYSTEM SOURCE OF TRUTH (VERIFIED)\n")
        f.write(f"**Date: {timestamp}**\n\n")
        f.write("This document serves as the definitive source of truth for all essential PC2 services monitored by the Main PC Model Manager Agent (MMA). This represents the verified state after comprehensive testing.\n\n")
        
        f.write(f"## Verification Summary\n")
        f.write(f"- Total Services: {len(services)}\n")
        f.write(f"- Healthy Services: {healthy_count}\n")
        f.write(f"- Services with Issues: {len(services) - healthy_count}\n\n")
        
        f.write("## Essential PC2 Services\n\n")
        
        for i, (service, result) in enumerate(zip(services, results), 1):
            status_symbol = "(ONLINE)" if result["status"] == "HEALTHY" else "(OFFLINE)"
            
            f.write(f"### {i}. {service['name']} {status_symbol}\n")
            f.write(f"- **Script Filename & Path**: `{service['script']}`\n")
            f.write(f"- **Port Number**: {service['port']} (REP)\n")
            f.write(f"- **Bind Address**: `{service['bind_address']}` (all interfaces)\n")
            f.write(f"- **Health Check Mechanism**:\n")
            f.write(f"  - **ZMQ Payload**: `{json.dumps(service['health_check_payload'])}`\n")
            f.write(f"  - **Expected Response Pattern**: Contains key/value matching one of: `{', '.join(service['expected_response_pattern'])}`\n")
            f.write(f"- **Verification Status**: {result['status']}\n")
            if result["response"]:
                f.write(f"  - **Response**: `{json.dumps(result['response'])}`\n")
            if result["notes"]:
                f.write(f"  - **Notes**: {result['notes']}\n")
            f.write(f"- **Role**: {service['notes']}\n\n")
        
        f.write("## Deprecated or Non-Essential Services\n\n")
        f.write("The following services exist but are not part of the essential PC2 services monitored by the Main PC MMA:\n\n")
        
        f.write("### Bark TTS Agent\n")
        f.write("- **Status**: Deprecated, functionality moved to Main PC XTTS\n")
        f.write("- **Former Port**: 5562\n")
        f.write("- **Notes**: Text-to-speech capabilities now centralized on Main PC\n\n")
        
        f.write("### Filesystem Assistant Agent\n")
        f.write("- **Status**: Non-essential\n")
        f.write("- **Port**: 5594\n")
        f.write("- **Notes**: Not currently part of essential MMA-monitored services\n\n")
        
        f.write("### Jarvis Memory Agent\n")
        f.write("- **Status**: Deprecated, consolidated into memory.py\n")
        f.write("- **Former Port**: 5598\n")
        f.write("- **Notes**: Functionality fully merged into the consolidated Memory Agent\n\n")
        
        f.write("---\n\n")
        f.write("## Startup Instructions\n\n")
        f.write("To start all essential PC2 services in the correct order:\n\n")
        f.write("1. Run the startup batch file:\n")
        f.write("   ```\n")
        f.write("   d:\\DISKARTE\\Voice Assistant\\start_essential_pc2_services.bat\n")
        f.write("   ```\n\n")
        f.write("2. Verify all services are running:\n")
        f.write("   ```\n")
        f.write("   python verify_pc2_target_config.py\n")
        f.write("   ```\n\n")
        f.write("**Note**: All services should bind to `0.0.0.0` to be accessible remotely by the Main PC MMA.\n")
    
    return filename

def main():
    print("\nPC2 TARGET CONFIGURATION VERIFICATION TOOL")
    print("============================= ")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # Check all services
    results = []
    for service in SERVICES:
        result = check_service_health(service)
        print_service_status(service, result)
        results.append(result)
    
    # Print summary
    healthy_count = sum(1 for r in results if r["status"] == "HEALTHY")
    print("\nVERIFICATION SUMMARY")
    print("====================")
    print(f"Total Services: {len(SERVICES)}")
    print(f"Healthy: {healthy_count}")
    print(f"Problems: {len(SERVICES) - healthy_count}")
    
    # Generate source of truth document
    print("\nGENERATING SOURCE OF TRUTH DOCUMENT")
    print("=====================================")
    filename = generate_source_of_truth_doc(SERVICES, results)
    print(f"File: {filename}")
    print(f"\nSource of Truth document generated: {filename}")
    
    print("\nVERIFICATION COMPLETE")
    
    # Critical warning if most services are down
    if healthy_count < len(SERVICES) / 2:
        print("\nCRITICAL: MOST SERVICES ARE NOT RUNNING")
        print("You should start the essential services before deployment validation.")

if __name__ == "__main__":
    main()
