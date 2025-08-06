#!/usr/bin/env python3
"""
Structural Integrity Scan for Docker services
Checks for required files and configurations per PHASE 1 requirements
"""

import os
import json
import yaml
import pathlib
from typing import Dict, List, Any

def check_dockerfile_exists(service_dir: pathlib.Path) -> bool:
    """Check if Dockerfile exists"""
    return (service_dir / "Dockerfile").exists()

def check_compose_exists(service_dir: pathlib.Path) -> bool:
    """Check if docker-compose.yml exists"""
    return (service_dir / "docker-compose.yml").exists()

def check_healthcheck_exists(service_dir: pathlib.Path) -> bool:
    """Check if docker-compose.yml contains healthcheck block"""
    compose_file = service_dir / "docker-compose.yml"
    if not compose_file.exists():
        return False
    
    try:
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        # Check if any service has healthcheck
        services = compose_data.get('services', {})
        for service_name, service_config in services.items():
            if 'healthcheck' in service_config:
                return True
        return False
    except Exception:
        return False

def check_dockerfile_pinned_versions(service_dir: pathlib.Path) -> bool:
    """Check if Dockerfile uses pinned versions instead of :latest"""
    dockerfile = service_dir / "Dockerfile"
    if not dockerfile.exists():
        return False
    
    try:
        with open(dockerfile, 'r') as f:
            content = f.read()
        
        # Look for FROM statements with :latest
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('FROM ') and ':latest' in line:
                return False
        return True
    except Exception:
        return False

def scan_service(service_name: str, service_type: str) -> Dict[str, Any]:
    """Scan a single service directory"""
    service_dir = pathlib.Path("docker") / service_name
    
    result = {
        "name": service_name,
        "type": service_type,
        "dockerfile_exists": check_dockerfile_exists(service_dir),
        "compose_exists": check_compose_exists(service_dir),
        "healthcheck_exists": check_healthcheck_exists(service_dir),
        "pinned_versions": check_dockerfile_pinned_versions(service_dir)
    }
    
    # Calculate overall status
    result["status"] = "PASS" if all([
        result["dockerfile_exists"],
        result["compose_exists"],
        result["healthcheck_exists"],
        result["pinned_versions"]
    ]) else "FAIL"
    
    return result

def main():
    """Main scanning function"""
    print("Starting structural integrity scan...")
    
    # Load docker sets
    with open('_qa_artifacts/docker_sets.json', 'r') as f:
        docker_sets = json.load(f)
    
    results = {
        "pc2": [],
        "mainpc": [],
        "summary": {}
    }
    
    # Scan PC2 services
    for service in docker_sets["pc2"]:
        result = scan_service(service, "PC2")
        results["pc2"].append(result)
        print(f"PC2 {service}: {result['status']}")
    
    # Scan MAIN-PC services  
    for service in docker_sets["mainpc"]:
        result = scan_service(service, "MAIN-PC")
        results["mainpc"].append(result)
        print(f"MAIN-PC {service}: {result['status']}")
    
    # Generate summary
    total_services = len(results["pc2"]) + len(results["mainpc"])
    passed_services = len([r for r in results["pc2"] + results["mainpc"] if r["status"] == "PASS"])
    
    # Count specific issues
    missing_dockerfile = len([r for r in results["pc2"] + results["mainpc"] if not r["dockerfile_exists"]])
    missing_compose = len([r for r in results["pc2"] + results["mainpc"] if not r["compose_exists"]])
    missing_healthcheck = len([r for r in results["pc2"] + results["mainpc"] if not r["healthcheck_exists"]])
    unpinned_versions = len([r for r in results["pc2"] + results["mainpc"] if not r["pinned_versions"]])
    
    results["summary"] = {
        "total_services": total_services,
        "passed_services": passed_services,
        "failed_services": total_services - passed_services,
        "pass_rate": f"{(passed_services/total_services)*100:.1f}%",
        "missing_dockerfile": missing_dockerfile,
        "missing_compose": missing_compose,
        "missing_healthcheck": missing_healthcheck,
        "unpinned_versions": unpinned_versions
    }
    
    # Save results
    with open('_qa_artifacts/structural_scan_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n=== STRUCTURAL INTEGRITY SCAN SUMMARY ===")
    print(f"Total services: {total_services}")
    print(f"Passed: {passed_services} ({results['summary']['pass_rate']})")
    print(f"Failed: {results['summary']['failed_services']}")
    print(f"Missing Dockerfile: {missing_dockerfile}")
    print(f"Missing docker-compose.yml: {missing_compose}")
    print(f"Missing healthcheck: {missing_healthcheck}")
    print(f"Unpinned versions: {unpinned_versions}")
    print(f"\nDetailed results saved to: _qa_artifacts/structural_scan_results.json")

if __name__ == "__main__":
    main()
