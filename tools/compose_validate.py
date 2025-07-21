#!/usr/bin/env python3
import yaml
import sys
import os

def validate_compose(compose_file):
    if not os.path.exists(compose_file):
        print(f"❌ File not found: {compose_file}")
        return
        
    with open(compose_file, 'r') as f:
        compose = yaml.safe_load(f)
    
    issues = []
    
    services = compose.get('services', {})
    if not services:
        print("❌ No services found in compose file")
        return
    
    for service_name, service_config in services.items():
        # Check for healthcheck
        if 'healthcheck' not in service_config:
            issues.append(f"❌ {service_name}: Missing healthcheck")
        else:
            issues.append(f"✅ {service_name}: Has healthcheck")
        
        # Check for ports
        if 'ports' not in service_config:
            issues.append(f"⚠️ {service_name}: No ports defined")
        else:
            ports = service_config['ports']
            issues.append(f"✅ {service_name}: Has {len(ports)} port(s)")
        
        # Check for environment variables
        if 'environment' not in service_config:
            issues.append(f"⚠️ {service_name}: No environment variables")
    
    print(f"\n📋 VALIDATION RESULTS FOR {compose_file}:")
    print("=" * 50)
    for issue in issues:
        print(issue)
    
    print(f"\n📊 SUMMARY: {len(services)} services checked")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python compose_validate.py <compose_file>")
        sys.exit(1)
    validate_compose(sys.argv[1]) 