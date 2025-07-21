#!/usr/bin/env python3
import yaml
import sys
import re

def add_healthchecks(compose_file):
    with open(compose_file, 'r') as f:
        compose = yaml.safe_load(f)
    
    for service_name, service_config in compose.get('services', {}).items():
        if 'healthcheck' not in service_config:
            # Add socket-based healthcheck
            service_config['healthcheck'] = {
                'test': ["CMD", "python", "-c", 
                        "import socket,sys,os; p=int(os.getenv('HEALTH_PORT',8000)); s=socket.socket(); s.settimeout(2); sys.exit(1 if s.connect_ex(('localhost',p)) else 0)"],
                'interval': '30s',
                'timeout': '5s',
                'retries': 3
            }
    
    with open(compose_file, 'w') as f:
        yaml.dump(compose, f, default_flow_style=False)
    
    print(f"✅ Added healthchecks to {compose_file}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_healthchecks.py <compose_file>")
        sys.exit(1)
    add_healthchecks(sys.argv[1]) 