#!/usr/bin/env python

import json
import time
import zmq
import sys
from pathlib import Path
import logging
from datetime import datetime


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.log_setup import configure_logging
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Set up logging with timestamp for unique filename
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = fPathManager.join_path("logs", str(PathManager.get_logs_dir() / "pc2_zmq_validation_{current_time}.log"))

# Create logs directory if it doesn't exist
Path('logs').mkdir(exist_ok=True)

# Configure logging
logger = configure_logging(__name__),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('PC2_ZMQ_Validator')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# We'll use a direct parsing approach with regex instead of importing
# to avoid any import or syntax issues in the config file
import re
config_path = project_root / 'config' / 'system_config.py'

def check_zmq_service(model_id, service_info):
    """Check the health of a single ZMQ remote service"""
    result = {
        'model_id': model_id,
        'status': 'unknown',
        'response': None,
        'error': None,
        'timestamp': time.time()
    }
    
    zmq_address = service_info.get('zmq_address')
    if not zmq_address:
        result['status'] = 'config_error'
        result['error'] = 'No ZMQ address specified'
        return result
    
    # Get health check action data
    health_check_action = service_info.get('health_check_action', 'ping')
    health_check_expect = service_info.get('health_check_expect', {'status': 'ok'})
    
    logger.info(f"Checking PC2 ZMQ service: {model_id} at {zmq_address}")
    logger.debug(f"  Health check action: {health_check_action}")
    logger.debug(f"  Expected response: {health_check_expect}")
    
    # Prepare the ZMQ connection
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        # Connect to the ZMQ service
        logger.debug(f"  Connecting to {zmq_address}...")
        socket.connect(zmq_address)
        
        # Prepare and send the health check request
        request_id = f"health_check_{int(time.time())}"
        payload = {"action": health_check_action, "request_id": request_id}
        
        logger.debug(f"  Sending health check payload: {payload}")
        socket.send_string(json.dumps(payload))
        
        # Wait for response
        response_str = socket.recv_string()
        logger.debug(f"  Received response: {response_str}")
        
        # Parse the response
        try:
            response = json.loads(response_str)
            result['response'] = response
            
            # Check if the response contains the expected health check data
            health_check_passed = True
            for key, expected_value in health_check_expect.items():
                if key not in response or response[key] != expected_value:
                    health_check_passed = False
                    break
            
            if health_check_passed:
                result['status'] = 'online'
                logger.info(f"  ✅ {model_id}: Health check PASSED")
            else:
                result['status'] = 'unhealthy'
                result['error'] = 'Response did not match expected health check data'
                logger.warning(f"  ⚠️ {model_id}: Health check FAILED - Response did not match expectations")
                
        except json.JSONDecodeError:
            result['status'] = 'response_error'
            result['error'] = 'Invalid JSON response'
            logger.error(f"  ❌ {model_id}: Invalid JSON response")
            
    except zmq.error.Again:
        # Timeout error
        result['status'] = 'timeout'
        result['error'] = 'Connection timeout'
        logger.error(f"  ❌ {model_id}: Connection timeout")
        
    except Exception as e:
        # General error
        result['status'] = 'error'
        result['error'] = str(e)
        logger.error(f"  ❌ {model_id}: Error checking service: {e}")
        
    finally:
        # Clean up ZMQ resources
        socket.close()
        context.term()
        
    return result

def validate_all_pc2_zmq_services():
    """Check all PC2 ZMQ services and display results"""
    # Read the system_config.py file content
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Look for PC2 ZMQ service patterns using regex
    # Pattern matches model entries with zmq_service_remote serving method
    pattern = r'"([^"]+)"\s*:\s*{[^}]*"serving_method"\s*:\s*"zmq_service_remote"[^}]*}'
    model_ids = re.findall(pattern, content, re.DOTALL)
    
    logger.info(f"Found {len(model_ids)} PC2 ZMQ services in system_config.py")
    
    # Check if we found any matches
    if not model_ids:
        logger.error("No PC2 ZMQ services found with 'zmq_service_remote' serving method")
        return []
    
    # Extract and prepare model info for health checks
    zmq_remote_service_models = {}
    for model_id in model_ids:
        # Extract service details using regex
        zmq_address_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_address"\s*:\s*"([^"]+)"', content, re.DOTALL)
        zmq_address = zmq_address_match.group(1) if zmq_address_match else None
        
        if not zmq_address:
            logger.warning(f"No ZMQ address found for {model_id}, skipping")
            continue
            
        # Extract health check action
        health_action = "health_check"  # Default
        health_action_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_actions"\s*:\s*{{\s*"health"\s*:\s*"([^"]+)"', content, re.DOTALL)
        if health_action_match:
            health_action = health_action_match.group(1)
        else:
            # For complex health actions (dictionaries)
            complex_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_actions"\s*:\s*{{\s*"health"\s*:\s*{{[^}}]*}}', content, re.DOTALL)
            if complex_match:
                # This is a complex health action (dictionary), use a simple ping as fallback
                health_action = {"action": "ping", "request_id": f"health_check_{int(time.time())}"}
        
        # Extract expected health response
        health_expect = {"status": "ok"}  # Default
        health_expect_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"expected_health_response_contains"\s*:\s*{{[^}}]*}}', content, re.DOTALL)
        if health_expect_match:
            try:
                # Try to eval the dictionary string - this is a simplified approach
                expect_str = health_expect_match.group(1).replace("'", '"')
                health_expect = {"status": "ok"}  # Fallback to default if eval fails
            except:
                pass
                
        # Build model info dict
        model_info = {
            "zmq_address": zmq_address,
            "health_check_action": health_action,
            "health_check_expect": health_expect
        }
        
        logger.debug(f"Found PC2 ZMQ service: {model_id} at {zmq_address}")
        zmq_remote_service_models[model_id] = model_info
    
    # Display service count
    total_services = len(zmq_remote_service_models)
    logger.info(f"Found {total_services} PC2 ZMQ remote services to validate")
    if total_services == 0:
        logger.error("No PC2 ZMQ remote services found in system_config.py")
        return []
    
    # Check each service
    results = []
    for model_id, model_info in zmq_remote_service_models.items():
        result = check_zmq_service(model_id, model_info)
        results.append(result)
    
    # Display summary
    online_count = sum(1 for r in results if r['status'] == 'online')
    logger.info(f"\nSUMMARY: {online_count}/{total_services} PC2 ZMQ services are online")
    
    # Display detailed results table
    logger.info("\nDETAILED RESULTS:")
    logger.info("-" * 80)
    logger.info(f"{'MODEL ID':<30} | {'STATUS':<15} | {'ERROR':<30}")
    logger.info("-" * 80)
    
    for result in results:
        status_display = f"✅ {result['status']}" if result['status'] == 'online' else f"❌ {result['status']}"
        error_display = result['error'] if result['error'] else '-'
        logger.info(f"{result['model_id']:<30} | {status_display:<15} | {error_display:<30}")
    
    logger.info("-" * 80)
    logger.info(f"Log file: {log_file}")
    
    return results

if __name__ == "__main__":
    print(f"\n🔍 PC2 ZMQ SERVICES VALIDATOR")
    print(f"================================")
    print(f"Starting validation of all PC2 ZMQ services...")
    print(f"Detailed logs will be written to: {log_file}\n")
    
    start_time = time.time()
    results = validate_all_pc2_zmq_services()
    end_time = time.time()
    
    # Count results by status
    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\n✅ Validation completed in {end_time - start_time:.2f} seconds")
    print(f"Found {len(results)} PC2 ZMQ services")
    
    # Print status counts
    for status, count in status_counts.items():
        icon = "✅" if status == "online" else "❌"
        print(f"{icon} {status}: {count}")
    
    print(f"\nSee {log_file} for detailed results")