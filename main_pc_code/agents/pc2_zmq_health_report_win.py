from main_pc_code.src.core.base_agent import BaseAgent
#!/usr/bin/env python

import os
import sys
import json
import time
import zmq
import re
import logging
from pathlib import Path
from datetime import datetime
import traceback
import prettytable


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", ".."))))
from common.utils.path_manager import PathManager
# Set up logging
current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
log_filename = fPathManager.join_path("logs", "pc2_zmq_health_report_{current_time}.log")

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('PC2ZMQHealthReport')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# We'll use a direct parsing approach with regex to avoid import issues
import re
config_path = project_root / 'config' / 'system_config.py'

def load_pc2_zmq_services():
    """Load all PC2 ZMQ remote services from system_config.py"""
    # Read the system_config.py file content
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Look for PC2 ZMQ service patterns using regex
    pattern = r'"([^"]+)"\s*:\s*{[^}]*"serving_method"\s*:\s*"zmq_service_remote"[^}]*}'
    model_ids = re.findall(pattern, content, re.DOTALL)
    
    logger.info(f"Found {len(model_ids)} PC2 ZMQ services in system_config.py")
    
    # Check if we found any matches
    if not model_ids:
        logger.error("No PC2 ZMQ services found with 'zmq_service_remote' serving method")
        return {}
    
    # Extract and prepare model info
    zmq_services = {}
    for model_id in model_ids:
        # Extract service details using regex
        zmq_address_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_address"\s*:\s*"([^"]+)"', content, re.DOTALL)
        zmq_address = zmq_address_match.group(1) if zmq_address_match else None
        
        if not zmq_address:
            logger.warning(f"No ZMQ address found for {model_id}, skipping")
            continue
        
        # Extract display name
        display_name_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"display_name"\s*:\s*"([^"]+)"', content, re.DOTALL)
        display_name = display_name_match.group(1) if display_name_match else model_id
        
        # Extract health check action
        health_action_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_actions"\s*:\s*{{\s*"health"\s*:\s*"([^"]+)"', content, re.DOTALL)
        health_action = health_action_match.group(1) if health_action_match else "health_check"
        
        # Extract expected health response
        health_expect_pattern = fr'"{model_id}"\s*:\s*{{[^}}]*"expected_health_response_contains"\s*:\s*{{\s*"status"\s*:\s*"([^"]+)"'
        health_expect_match = re.search(health_expect_pattern, content, re.DOTALL)
        expected_status = health_expect_match.group(1) if health_expect_match else "ok"
        
        # Build service info
        zmq_services[model_id] = {
            "model_id": model_id,
            "display_name": display_name,
            "zmq_address": zmq_address,
            "health_action": health_action,
            "expected_status": expected_status
        }
        
        logger.debug(f"Found PC2 ZMQ service: {model_id} at {zmq_address}, health action: {health_action}")
    
    return zmq_services

def check_zmq_service(service_info, timeout_ms=5000, retries=2):
    """Check the health of a ZMQ remote service with retries"""
    model_id = service_info["model_id"]
    zmq_address = service_info["zmq_address"]
    health_action = service_info["health_action"]
    expected_status = service_info["expected_status"]
    
    logger.debug(f"Checking service {model_id} at {zmq_address} with action '{health_action}'")
    
    result = {
        "model_id": model_id,
        "display_name": service_info["display_name"],
        "zmq_address": zmq_address,
        "status": "unknown",
        "error": None,
        "response": None,
        "latency_ms": 0,
        "expected_status": expected_status
    }
    
    # Try with retries
    for attempt in range(1, retries+1):
        # Create new context and socket for each attempt
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
        socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
        
        try:
            start_time = time.time()
            
            # Connect to service
            logger.debug(f"Connecting to {zmq_address} (attempt {attempt}/{retries})")
            socket.connect(zmq_address)
            
            # Send health check request
            payload = {"action": health_action}
            logger.debug(f"Sending payload to {model_id}: {payload}")
            socket.send_json(payload)
            
            # Wait for response
            raw_response = socket.recv()
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            # Parse response
            response_text = raw_response.decode('utf-8', errors='replace')
            response = json.loads(response_text)
            logger.debug(f"Received response from {model_id}: {response}")
            
            # Analyze response
            if isinstance(response, dict):
                service_status = response.get('status', '').lower()
                is_alive = response.get('alive', None)
                
                if (service_status == expected_status or 
                    service_status in ['loaded', 'online', 'ok', 'success', 'available_not_loaded'] or 
                    is_alive is True):
                    result["status"] = "healthy"
                else:
                    result["status"] = "unhealthy"
                    error_details = f"Response did not match expected health check data"
                    error_message = f"Received: {response} | Expected keys: {expected_status}"
                    result["error"] = error_message
                    result["response_data"] = response
            else:
                result["status"] = "error"
                result["error"] = f"Unexpected response format: {type(response).__name__}"
            
            result["response"] = response
            result["latency_ms"] = latency_ms
            
            # If successful, no need to retry
            if result["status"] == "healthy":
                break
            
            logger.warning(f"Health check for {model_id} returned {result['status']} on attempt {attempt}/{retries}")
            
        except zmq.error.Again:
            result["status"] = "timeout"
            result["error"] = "Connection timeout"
            logger.warning(f"Timeout connecting to {model_id} at {zmq_address} (attempt {attempt}/{retries})")
        except json.JSONDecodeError as e:
            result["status"] = "error"
            result["error"] = f"Invalid JSON response: {e}"
            logger.error(f"JSON decode error for {model_id}: {e}")
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Error checking {model_id}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            socket.close()
            context.term()
            
            # If successful, no need to retry
            if result["status"] == "healthy":
                break
            
            # Wait briefly before retry
            if attempt < retries:
                time.sleep(0.5)
    
    return result

def generate_health_report(results):
    """Generate a formatted health report"""
    # Count results by status
    status_counts = {"healthy": 0, "unhealthy": 0, "timeout": 0, "error": 0}
    for result in results:
        if result["status"] in status_counts:
            status_counts[result["status"]] += 1
    
    # Create tables
    table = prettytable.PrettyTable()
    table.field_names = ["Service ID", "Display Name", "ZMQ Address", "Status", "Latency", "Response Data / Error"]
    table.align = "l"
    table.max_width["Response Data / Error"] = 60
    
    # Add rows
    for result in results:
        status_icon = "[OK]" if result["status"] == "healthy" else "[X]" 
        latency = f"{result['latency_ms']}ms" if result['latency_ms'] > 0 else "N/A"
        error_display = result["error"] or "None"
        if "response_data" in result and result["status"] != "healthy":
            error_display = f"Response: {str(result['response_data'])[:50]}..."

        table.add_row([
            result["model_id"], 
            result["display_name"], 
            result["zmq_address"], 
            f"{status_icon} {result['status']}",
            latency,
            error_display
        ])
    
    # Generate summary
    summary = f"""
PC2 ZMQ HEALTH CHECK REPORT
{'='*80}

Detailed health report for {len(results)} PC2 ZMQ remote services
Run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RESULTS SUMMARY:
- Total services: {len(results)}
- Healthy: {status_counts['healthy']}
- Unhealthy: {status_counts['unhealthy']}
- Timeout: {status_counts['timeout']}
- Error: {status_counts['error']}

DETAILED RESULTS:
{table}

MODEL MANAGER AGENT RECOMMENDATIONS:
1. Ensure all 13 PC2 ZMQ services are running on PC2
2. Verify network connectivity between Main PC and PC2
3. Check that each service is properly implementing the expected health check protocol
4. Update system_config.py if the health check actions or expected responses need adjustment
5. Restart the ModelManagerAgent to apply any configuration changes

Log file: {log_filename}
{'='*80}
"""
    
    return summary

def save_report_to_file(report, results):
    """Save the report and raw results to files"""
    report_path = Path('logs') / f'pc2_zmq_health_report_{current_time}.txt'
    json_path = Path('logs') / f'pc2_zmq_health_results_{current_time}.json'
    
    # Save text report
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Save JSON results
    with open(json_path, 'w', encoding='utf-8') as f:
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            result_copy = result.copy()
            # Handle non-serializable types
            if 'response' in result_copy and not isinstance(result_copy['response'], (dict, list, str, int, float, bool, type(None))):
                result_copy['response'] = str(result_copy['response'])
            serializable_results.append(result_copy)
        
        json.dump(serializable_results, f, indent=2)
    
    logger.info(f"Report saved to {report_path}")
    logger.info(f"Raw results saved to {json_path}")
    
    return report_path, json_path

def main():
    print("\nPC2 ZMQ HEALTH CHECK REPORTER")
    print("================================")
    print("Starting comprehensive health check of all PC2 ZMQ services...")
    print(f"Detailed logs will be written to: {log_filename}")
    
    try:
        # Load PC2 ZMQ services
        services = load_pc2_zmq_services()
        
        if not services:
            print("\n[X] No PC2 ZMQ services found in system_config.py")
            return
        
        print(f"\nFound {len(services)} PC2 ZMQ services to check")
        
        # Check each service
        results = []
        for model_id, service_info in services.items():
            print(f"Checking {model_id} at {service_info['zmq_address']}...")
            result = check_zmq_service(service_info, timeout_ms=5000, retries=2)
            results.append(result)
            
            # Display status
            status_icon = "[OK]" if result["status"] == "healthy" else "[X]"
            print(f"  {status_icon} {result['status']} {result['error'] or ''}")
        
        # Generate report
        report = generate_health_report(results)
        
        # Save report
        report_path, _ = save_report_to_file(report, results)
        
        # Print report
        print(report)
        print(f"\nReport saved to {report_path}")
        
    except Exception as e:
        logger.error(f"Error in health check reporter: {e}")
        logger.debug(traceback.format_exc())
        print(f"\n[ERROR] {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
