#!/usr/bin/env python3
"""
Test script for service discovery client
"""

import json
from main_pc_code.utils.service_discovery_client import get_service_discovery_client

def main():
    # Get the service discovery client
    client = get_service_discovery_client()
    """TODO: Add description for main."""

    # Try to discover the SystemDigitalTwin service
    success, response = client.discover_service("SystemDigitalTwin")

    # Print the result
    print(f"Success: {success}")
    print(f"Response: {json.dumps(response, indent=2)}")

    if success:
        print("\nSUCCESS: The service discovery test passed. The client successfully connected to SystemDigitalTwin and received a valid service registration response.")
    else:
        print("\nFAILURE: The service discovery test failed. Check the logs for details.")

if __name__ == "__main__":
    main()
