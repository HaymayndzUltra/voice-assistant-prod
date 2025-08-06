#!/usr/bin/env python3
"""
Dependency Analysis for Docker services
Extracts, merges, and analyzes requirements.txt files per PHASE 2 requirements
"""

import os
import json
import pathlib
from collections import defaultdict
from typing import Dict, List, Set, Tuple

def extract_requirements_files() -> Dict[str, List[str]]:
    """Extract all requirements.txt files from docker services"""
    requirements_data = {}
    
    # Load docker sets
    with open('_qa_artifacts/docker_sets.json', 'r') as f:
        docker_sets = json.load(f)
    
    all_services = docker_sets["pc2"] + docker_sets["mainpc"]
    
    for service in all_services:
        service_dir = pathlib.Path("docker") / service
        req_file = service_dir / "requirements.txt"
        
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    lines = f.readlines()
                
                # Clean and parse requirements
                requirements = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        requirements.append(line)
                
                requirements_data[service] = requirements
                print(f"Found requirements.txt in {service}: {len(requirements)} dependencies")
            except Exception as e:
                print(f"Error reading requirements.txt in {service}: {e}")
        else:
            print(f"No requirements.txt found in {service}")
    
    return requirements_data

def merge_and_deduplicate_dependencies(requirements_data: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    """Merge and deduplicate dependencies"""
    all_deps = defaultdict(set)
    
    for service, deps in requirements_data.items():
        for dep in deps:
            # Extract package name (before ==, >=, etc.)
            package_name = dep.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].split('[')[0].strip()
            all_deps[package_name].add(dep)
    
    return dict(all_deps)

def analyze_base_images() -> Dict[str, List[str]]:
    """Analyze and categorize services for base image recommendations"""
    # Load docker sets
    with open('_qa_artifacts/docker_sets.json', 'r') as f:
        docker_sets = json.load(f)
    
    gpu_services = []
    cpu_services = []
    
    all_services = docker_sets["pc2"] + docker_sets["mainpc"]
    
    for service in all_services:
        # Check if service has GPU in name or check docker-compose for GPU resources
        service_dir = pathlib.Path("docker") / service
        compose_file = service_dir / "docker-compose.yml"
        
        is_gpu_service = False
        
        # Check name for GPU indicators
        if 'gpu' in service.lower() or 'vision' in service.lower() or 'dream' in service.lower():
            is_gpu_service = True
        
        # Check docker-compose for GPU resources
        if compose_file.exists():
            try:
                with open(compose_file, 'r') as f:
                    content = f.read()
                if 'nvidia' in content.lower() or 'gpu' in content.lower():
                    is_gpu_service = True
            except Exception:
                pass
        
        if is_gpu_service:
            gpu_services.append(service)
        else:
            cpu_services.append(service)
    
    return {
        "gpu_services": gpu_services,
        "cpu_services": cpu_services
    }

def generate_optimization_report():
    """Generate comprehensive optimization report"""
    print("Starting dependency analysis...")
    
    # Extract requirements
    requirements_data = extract_requirements_files()
    
    # Merge and deduplicate
    merged_deps = merge_and_deduplicate_dependencies(requirements_data)
    
    # Analyze base images
    base_image_analysis = analyze_base_images()
    
    # Generate statistics
    total_services_with_reqs = len(requirements_data)
    total_unique_packages = len(merged_deps)
    
    # Find most common dependencies
    package_usage = defaultdict(int)
    for service, deps in requirements_data.items():
        for dep in deps:
            package_name = dep.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].split('[')[0].strip()
            package_usage[package_name] += 1
    
    most_common = sorted(package_usage.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Create optimization report
    optimization_report = {
        "summary": {
            "total_services": len(requirements_data),
            "services_with_requirements": total_services_with_reqs,
            "unique_packages": total_unique_packages
        },
        "base_image_recommendations": {
            "gpu_services": {
                "count": len(base_image_analysis["gpu_services"]),
                "services": base_image_analysis["gpu_services"],
                "recommended_base": "nvidia/cuda:12.1.1-runtime-ubuntu22.04"
            },
            "cpu_services": {
                "count": len(base_image_analysis["cpu_services"]),
                "services": base_image_analysis["cpu_services"],
                "recommended_base": "python:3.10-slim-bullseye"
            }
        },
        "top_dependencies": most_common,
        "merged_dependencies": {pkg: list(versions) for pkg, versions in merged_deps.items()},
        "top_5_optimizations": [
            {
                "priority": 1,
                "title": "Switch CPU-only images to python:3.10-slim-bullseye",
                "description": "Use pip install --no-cache-dir to cut ~65% of image size",
                "affected_services": len(base_image_analysis["cpu_services"]),
                "estimated_savings": "~65% image size reduction"
            },
            {
                "priority": 2,
                "title": "Unify CUDA base to nvidia/cuda:12.1.1-runtime-ubuntu22.04",
                "description": "Avoid driver mismatch across GPU services",
                "affected_services": len(base_image_analysis["gpu_services"]),
                "estimated_savings": "Reduced maintenance, consistent CUDA environment"
            },
            {
                "priority": 3,
                "title": "Add HEALTHCHECK to all containers",
                "description": "Missing in containers without healthcheck",
                "affected_services": "15 services (from structural scan)",
                "estimated_savings": "Improved reliability and monitoring"
            },
            {
                "priority": 4,
                "title": "Enable pip cache pruning",
                "description": "Use --build-arg PIP_DISABLE_PIP_VERSION_CHECK=1 and prune cache",
                "affected_services": "All services",
                "estimated_savings": "Reduced layer bloat"
            },
            {
                "priority": 5,
                "title": "Migrate to multi-stage builds",
                "description": "Builder → runtime for compiled dependencies",
                "affected_services": "Services with PyTorch, TensorRT, etc.",
                "estimated_savings": "Drop unused toolchains from final image"
            }
        ]
    }
    
    # Save to file
    with open('_qa_artifacts/optimization_report.json', 'w') as f:
        json.dump(optimization_report, f, indent=2)
    
    # Save merged dependencies separately
    with open('_qa_artifacts/merged_dependencies.txt', 'w') as f:
        for package, versions in sorted(merged_deps.items()):
            f.write(f"# {package} (used in {package_usage[package]} services)\n")
            for version in sorted(versions):
                f.write(f"{version}\n")
            f.write("\n")
    
    print(f"\n=== DEPENDENCY ANALYSIS SUMMARY ===")
    print(f"Services with requirements.txt: {total_services_with_reqs}")
    print(f"Unique packages found: {total_unique_packages}")
    print(f"GPU services: {len(base_image_analysis['gpu_services'])}")
    print(f"CPU services: {len(base_image_analysis['cpu_services'])}")
    print(f"\nTop 10 most common dependencies:")
    for pkg, count in most_common[:10]:
        print(f"  {pkg}: {count} services")
    print(f"\nOptimization report saved to: _qa_artifacts/optimization_report.json")
    print(f"Merged dependencies saved to: _qa_artifacts/merged_dependencies.txt")

if __name__ == "__main__":
    generate_optimization_report()
