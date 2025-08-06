import zmq
import json
import time
import logging
import sys
import re
import os
from datetime import datetime


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.log_setup import configure_logging
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Configure logging
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = fPathManager.join_path("logs", str(PathManager.get_logs_dir() / "pc2_zmq_protocol_finder_{log_timestamp}.log"))
logger = configure_logging(__name__) as f:
            config_content = f.read()
        
        # Find all model definitions
        model_pattern = r'\"([\w-]+)\"\s*:\s*{[^}]*?\"serving_method\"\s*:\s*\"zmq_service_remote\"[^}]*?}'
        model_matches = re.finditer(model_pattern, config_content, re.DOTALL)
        
        zmq_services = []
        for match in model_matches:
            model_text = match.group(0)
            model_id = re.search(r'\"([\w-]+)\"', model_text).group(1)
            
            # Extract display name
            display_name_match = re.search(r'\"display_name\"\s*:\s*\"([^\"]+)\"', model_text)
            display_name = display_name_match.group(1) if display_name_match else "Unknown"
            
            # Extract ZMQ address
            zmq_address_match = re.search(r'\"zmq_address\"\s*:\s*\"([^\"]+)\"', model_text)
            zmq_address = zmq_address_match.group(1) if zmq_address_match else None
            
            if zmq_address:
                zmq_services.append({
                    "model_id": model_id,
                    "display_name": display_name,
                    "zmq_address": zmq_address,
                })
                logging.debug(f"Found PC2 ZMQ service: {model_id} at {zmq_address}")
        
        return zmq_services
    except Exception as e:
        logging.error(f"Error extracting ZMQ services: {str(e)}")
        return []

# Connect to a ZMQ service and try various health check variations
def find_working_health_check(service):
    model_id = service["model_id"]
    zmq_address = service["zmq_address"]
    display_name = service["display_name"]
    
    logging.info(f"Testing protocols for {model_id} at {zmq_address}...")
    print(f"Testing protocols for {model_id} at {zmq_address}...")
    
    working_protocols = []
    
    # Create ZMQ context
    context = zmq.Context()
    
    for variation in HEALTH_CHECK_VARIATIONS:
        # Create socket for this attempt
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.setsockopt(zmq.LINGER, 0)  # Don't keep messages in memory after close
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        try:
            logging.debug(f"Connecting to {zmq_address}")
            socket.connect(zmq_address)
            
            # Send request
            payload = variation
            logging.debug(f"Sending payload to {model_id}: {payload}")
            socket.send_json(payload)
            
            # Wait for response
            try:
                response = socket.recv_json()
                logging.debug(f"Received response from {model_id}: {response}")
                
                # Check if response indicates success
                success = False
                if isinstance(response, dict):
                    if 'status' in response and response['status'] in ['ok', 'success', 'available']:
                        success = True
                    elif 'available' in response and response['available'] is True:
                        success = True
                    elif 'is_alive' in response and response['is_alive'] is True:
                        success = True
                
                result = {
                    "model_id": model_id,
                    "payload": payload,
                    "response": response,
                    "success": success
                }
                
                working_protocols.append(result)
                status = "✅ SUCCESS" if success else "❌ FAILED"
                print(f"{status} | Payload: {payload} | Response: {str(response)[:50]}...")
                
            except zmq.error.Again:
                logging.warning(f"Timeout receiving from {model_id} with payload {payload}")
                print(f"⏱️ TIMEOUT | Payload: {payload}")
        except Exception as e:
            logging.error(f"Error communicating with {model_id}: {str(e)}")
            print(f"⚠️ ERROR | Payload: {payload} | Error: {str(e)}")
        finally:
            socket.close()
        
        # Brief pause between attempts
        time.sleep(0.5)
    
    # Print summary
    print(f"\nSummary for {model_id} ({display_name}):")
    if working_protocols:
        successful_protocols = [p for p in working_protocols if p["success"]]
        if successful_protocols:
            print(f"Found {len(successful_protocols)} successful protocol(s):")
            for idx, protocol in enumerate(successful_protocols, 1):
                print(f"{idx}. Payload: {protocol['payload']}")
                print(f"   Response: {protocol['response']}")
                
                # Create system_config.py snippet
                config_payload = json.dumps(protocol['payload'])
                print(f"   system_config.py: \"zmq_actions\": {{ \"health\": {config_payload} }},")
                
                # Try to determine expected response pattern
                if isinstance(protocol['response'], dict):
                    if 'status' in protocol['response']:
                        print(f"   Expected response: \"expected_health_response_contains\": {{ \"status\": \"{protocol['response']['status']}\" }},")
        else:
            print("No successful protocols found. Showing all attempted protocols:")
            for idx, protocol in enumerate(working_protocols, 1):
                print(f"{idx}. Payload: {protocol['payload']}")
                print(f"   Response: {protocol['response']}")
    else:
        print("No responses received from this service.")
    
    print("\n" + "-"*80 + "\n")
    return working_protocols

def main():
    print("PC2 ZMQ PROTOCOL FINDER")
    print("=======================")
    
    # Extract ZMQ services from config
    services = extract_zmq_services_from_config()
    
    if not services:
        print("No PC2 ZMQ services found in system_config.py")
        return
    
    print(f"Found {len(services)} PC2 ZMQ services. Testing protocols...\n")
    
    # Test each service
    results = []
    for service in services:
        working_protocols = find_working_health_check(service)
        results.append({
            "service": service,
            "protocols": working_protocols
        })
    
    # Print final summary
    print("\nFINAL SUMMARY")
    print("==============")
    
    success_count = 0
    for result in results:
        service = result["service"]
        protocols = result["protocols"]
        successful_protocols = [p for p in protocols if p["success"]]
        
        status = "✅ SUCCESS" if successful_protocols else "❌ FAILED"
        if successful_protocols:
            success_count += 1
        
        print(f"{status} | {service['model_id']} ({service['display_name']}) | {len(successful_protocols)}/{len(protocols)} successful protocols")
    
    print(f"\n{success_count}/{len(services)} services have working health check protocols.")
    print(f"Log file: {log_file}")

if __name__ == "__main__":
    main()