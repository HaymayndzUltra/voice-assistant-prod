from main_pc_code.src.core.base_agent import BaseAgent
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import time
import logging
import sys
from pathlib import Path
from datetime import datetime
from prettytable import PrettyTable
import socket
from common.utils.log_setup import configure_logging

# Add parent directory to path to import system_config
sys.path.append(str(Path(__file__).parent.parent))
from main_pc_code.config.system_config import DEFAULT_CONFIG

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)
log_filename = f"pc2_zmq_protocol_finder_extended_{datetime.now().strftime('%Y%m%d_%H%M%Sstr(PathManager.get_logs_dir() / ")}.log")
log_filepath = log_dir / log_filename
logger = configure_logging(__name__)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Extract PC2 ZMQ services from system_config
def get_pc2_zmq_services():
    services = {}
    
    # Access the model_configs section directly where PC2 services are defined
    model_configs = DEFAULT_CONFIG.get("main_pc_settings", {}).get("model_configs", {})
    
    for model_id, model_info in model_configs.items():
        if (
            isinstance(model_info, dict) and
            model_info.get("serving_method") == "zmq_service_remote" and
            model_info.get("zmq_address", "").startswith("tcp://192.168.1.2")
        ):
            services[model_id] = {
                "zmq_address": model_info.get("zmq_address"),
                "display_name": model_info.get("display_name"),
                "zmq_actions": model_info.get("zmq_actions", {}),
                "expected_health_response_contains": model_info.get("expected_health_response_contains", {})
            }
            logger.debug(f"Found PC2 ZMQ service: {model_id} at {model_info.get('zmq_address')}")
    
    if not services:
        logger.warning("No PC2 ZMQ services found. Debug information follows:")
        print("No PC2 ZMQ services found. Checking configuration structure...")
        # Print keys to debug
        logger.debug(f"Available keys in DEFAULT_CONFIG: {list(DEFAULT_CONFIG.keys())}")
        if 'main_pc_settings' in DEFAULT_CONFIG:
            logger.debug(f"Available keys in main_pc_settings: {list(DEFAULT_CONFIG['main_pc_settings'].keys())}")
            if 'model_configs' in DEFAULT_CONFIG['main_pc_settings']:
                model_count = len(DEFAULT_CONFIG['main_pc_settings']['model_configs'])
                logger.debug(f"Total models in model_configs: {model_count}")
                
                # List some models for debugging
                for model_id, model_info in list(DEFAULT_CONFIG['main_pc_settings']['model_configs'].items())[:5]:
                    logger.debug(f"Model: {model_id}, serving_method: {model_info.get('serving_method', 'unknown')}")
    
    return services

# Generate various protocol payload formats for testing
def generate_test_payloads():
    payloads = [
        # Standard action payloads
        {"action": "health_check"},
        {"action": "health"},
        {"action": "status"},
        {"action": "ping"},
        {"action": "check"},
        {"action": "alive"},
        
        # Request type payloads
        {"request_type": "health_check"},
        {"request_type": "health"},
        {"request_type": "status"},
        {"request_type": "check_status"},
        {"request_type": "check_status", "model": "default"},
        {"request_type": "check_status", "model": "phi3"},
        
        # Command payloads
        {"command": "health_check"},
        {"command": "status"},
        
        # Request payloads
        {"request": "health_check"},
        {"request": "status"},
        
        # Type payloads
        {"type": "health_check"},
        {"type": "status"},
        
        # Query payloads
        {"query": "health_check"},
        {"query": "status"},
        
        # Translator specific payloads
        {"action": "translate", "text": "ping", "source_lang": "en", "target_lang": "tl"},
        {"action": "translate", "text": "health_check", "source_lang": "en", "target_lang": "tl"},
        
        # Chain of thought specific payloads
        {"action": "ping_chain_of_thought"},
        {"action": "ping", "service": "chain_of_thought"},
        {"action": "breakdown", "request": "health_check"},
        
        # Advanced combinations
        {"action": "health", "service": "check"},
        {"check": "health"},
        {"health": "check"},
        {"get_status": True},
        {"check_health": True},
        {"health_check": True},
        
        # Empty payload
        {},
    ]
    return payloads

# Test a service with each payload, recording successful responses
def test_service_protocols(service_id, service_info):
    logger.info(f"Testing protocols for {service_id} at {service_info['zmq_address']}...")
    print(f"Testing protocols for {service_id} at {service_info['zmq_address']}...")
    
    successful_protocols = []
    payloads = generate_test_payloads()
    
    for payload in payloads:
        try:
            # Create a new context and socket for each test for robustness
            context = None  # Using pool
            socket = get_req_socket(endpoint).socket
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
            socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2 second timeout for send
            
            logger.debug(f"Connecting to {service_info['zmq_address']}")
            socket.connect(service_info['zmq_address'])
            
            logger.debug(f"Sending payload to {service_id}: {payload}")
            socket.send_json(payload)
            
            response_text = socket.recv().decode('utf-8', errors='replace')
            response = json.loads(response_text)
            logger.debug(f"Received response from {service_id}: {response}")
            
            # Check if response indicates success
            if isinstance(response, dict) and response.get('status') in ['ok', 'success', 'alive', 'online', 'loaded']:
                logger.info(f"[SUCCESS] | Payload: {payload} | Response: {response}")
                print(f"[SUCCESS] | Payload: {payload} | Response: {str(response)[:50]}...")
                
                # Determine if this is the current configured protocol
                is_current = False
                health_action = service_info['zmq_actions'].get('health')
                if health_action and isinstance(health_action, str) and 'action' in payload and payload['action'] == health_action:
                    is_current = True
                
                # Format the system_config.py entry
                if 'action' in payload:
                    if len(payload) == 1:
                        config_entry = f"\"zmq_actions\": {{ \"health\": \"{payload['action']}\" }}"
                    else:
                        config_entry = f"\"zmq_actions\": {{ \"health\": {json.dumps(payload)} }}"
                elif 'request_type' in payload:
                    if len(payload) == 1:
                        config_entry = f"\"zmq_actions\": {{ \"health\": \"{payload['request_type']}\" }}"
                    else:
                        config_entry = f"\"zmq_actions\": {{ \"health\": {json.dumps(payload)} }}"
                else:
                    config_entry = f"\"zmq_actions\": {{ \"health\": {json.dumps(payload)} }}"
                
                # Expected response format
                status_value = response.get('status')
                if isinstance(status_value, str):
                    expected_response = f"\"expected_health_response_contains\": {{ \"status\": \"{status_value}\" }}"
                else:
                    expected_response = f"\"expected_health_response_contains\": {{ \"status\": {json.dumps(status_value)} }}"
                
                successful_protocols.append({
                    'payload': payload,
                    'response': response,
                    'config_entry': config_entry,
                    'expected_response': expected_response,
                    'is_current': is_current
                })
            else:
                logger.debug(f"[FAILED] | Payload: {payload} | Response: {str(response)[:50]}...")
                print(f"[FAILED] | Payload: {payload} | Response: {str(response)[:50]}...")
        except zmq.error.Again:
            logger.debug(f"[TIMEOUT] | Payload: {payload}")
            print(f"[TIMEOUT] | Payload: {payload}")
        except Exception as e:
            logger.warning(f"[ERROR] | Payload: {payload} | Error: {str(e)[:50]}...")
            print(f"[ERROR] | Payload: {payload} | Error: {str(e)[:50]}...")
        finally:
            time.sleep(0.5)  # Brief pause between attempts
    
    return successful_protocols

# Print summary report
def print_service_summary(service_id, service_info, successful_protocols):
    print("\n" + "-" * 80)
    print(f"\nSummary for {service_id} ({service_info['display_name']}):\n")
    logger.info(f"Summary for {service_id} ({service_info['display_name']}):\n")
    
    if successful_protocols:
        print(f"Found {len(successful_protocols)} successful protocol(s):")
        logger.info(f"Found {len(successful_protocols)} successful protocol(s):")
        
        for i, protocol in enumerate(successful_protocols, 1):
            print(f"{i}. Payload: {protocol['payload']}")
            print(f"   Response: {protocol['response']}")
            print(f"   system_config.py: {protocol['config_entry']},")
            print(f"   Expected response: {protocol['expected_response']},")
            if protocol['is_current']:
                print(f"   ** This is the currently configured protocol **")
            print()
            
            logger.info(f"{i}. Payload: {protocol['payload']}")
            logger.info(f"   Response: {protocol['response']}")
            logger.info(f"   system_config.py: {protocol['config_entry']},")
            logger.info(f"   Expected response: {protocol['expected_response']},")
            if protocol['is_current']:
                logger.info(f"   ** This is the currently configured protocol **")
    else:
        print("No successful protocols found.")
        logger.info("No successful protocols found.")
    
    print("\n" + "-" * 80 + "\n")

# Print final summary
def print_final_summary(services, results):
    print("\n\nFINAL SUMMARY")
    print("==============")
    success_count = 0
    
    for service_id, protocols in results.items():
        status = "SUCCESS" if protocols else "FAILED"
        if protocols:
            success_count += 1
        print(f"[{status}] | {service_id} ({services[service_id]['display_name']}) | {len(protocols)}/{len(generate_test_payloads())} successful protocols")
    
    print(f"\n{success_count}/{len(services)} services have working health check protocols.")
    print(f"Log file: {log_filepath}")

# Main function
def main():
    try:
        print("PC2 ZMQ Protocol Finder Extended")
        print("="*50)
        print(f"Starting protocol discovery at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Get PC2 ZMQ services
        services = get_pc2_zmq_services()
        if not services:
            logger.error("No PC2 ZMQ services found in system_config.py")
            print("Error: No PC2 ZMQ services found in system_config.py")
            return
        
        print(f"Found {len(services)} PC2 ZMQ services to test.\n")
        
        # Test each service
        results = {}
        for service_id, service_info in services.items():
            successful_protocols = test_service_protocols(service_id, service_info)
            results[service_id] = successful_protocols
            print_service_summary(service_id, service_info, successful_protocols)
        
        # Print final summary
        print_final_summary(services, results)
        
    except Exception as e:
        logger.error(f"Error in main protocol finder: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
