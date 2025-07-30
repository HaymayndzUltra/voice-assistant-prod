#!/usr/bin/env python

import os
import re

# Direct parsing approach to scan for PC2 ZMQ services
def scan_config_for_zmq_services():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'system_config.py')
    
    print(f"Scanning for PC2 ZMQ services in: {config_path}\n")
    
    # Read the file content
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Look for PC2 ZMQ service patterns using regex
    # Pattern matches model entries with zmq_service_remote serving method
    pattern = r'"([^"]+)"\s*:\s*{[^}]*"serving_method"\s*:\s*"zmq_service_remote"[^}]*}'
    matches = re.findall(pattern, content, re.DOTALL)
    
    # Check if we found any matches
    if not matches:
        print("No PC2 ZMQ services found with 'zmq_service_remote' serving method.")
        return []
    
    # Extract details for each service
    zmq_services = []
    for model_id in matches:
        # Extract service details using regex
        zmq_address_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_address"\s*:\s*"([^"]+)"', content, re.DOTALL)
        zmq_address = zmq_address_match.group(1) if zmq_address_match else "Unknown"
        
        display_name_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"display_name"\s*:\s*"([^"]+)"', content, re.DOTALL)
        display_name = display_name_match.group(1) if display_name_match else model_id
        
        enabled_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"enabled"\s*:\s*(True|False)', content, re.DOTALL)
        enabled = enabled_match.group(1) == "True" if enabled_match else False
        
        health_action_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_actions"\s*:\s*{{\s*"health"\s*:\s*"([^"]+)"', content, re.DOTALL)
        health_action = health_action_match.group(1) if health_action_match else "Unknown"
        
        # For complex health actions (dictionaries)
        if not health_action_match:
            health_action_match = re.search(fr'"{model_id}"\s*:\s*{{[^}}]*"zmq_actions"\s*:\s*{{\s*"health"\s*:\s*({{[^}}]*}})', content, re.DOTALL)
            health_action = "Complex" if health_action_match else "Not Found"
        
        # Add to our list
        zmq_services.append({
            "model_id": model_id,
            "display_name": display_name,
            "zmq_address": zmq_address,
            "enabled": enabled,
            "health_action": health_action
        })
    
    return zmq_services

# Main function to run the scan
def main():
    print("\n🔍 PC2 ZMQ SERVICES DETECTOR")
    print("================================")
    
    # Scan for services
    services = scan_config_for_zmq_services()
    
    # Print results
    if services:
        print(f"\n✅ Found {len(services)} PC2 ZMQ services:\n")
        print(f"{'MODEL ID':<30} | {'DISPLAY NAME':<40} | {'ZMQ ADDRESS':<30} | {'ENABLED':<10} | {'HEALTH ACTION':<15}")
        print("-" * 135)
        
        for service in services:
            enabled_icon = "✅" if service["enabled"] else "❌"
            print(f"{service['model_id']:<30} | {service['display_name']:<40} | {service['zmq_address']:<30} | {enabled_icon:<10} | {service['health_action']:<15}")
        
        # Count enabled services
        enabled_count = sum(1 for s in services if s["enabled"])
        print("\nSUMMARY:")
        print(f"- Total PC2 ZMQ services found: {len(services)}")
        print(f"- Enabled PC2 ZMQ services: {enabled_count}")
        print(f"- Disabled PC2 ZMQ services: {len(services) - enabled_count}")
    
    print("\n" + "-" * 80)
    print("This direct scan looks for 'zmq_service_remote' patterns in system_config.py")
    print("To perform health checks on these services, use the validate_pc2_zmq_services.py script")

if __name__ == "__main__":
    main()
