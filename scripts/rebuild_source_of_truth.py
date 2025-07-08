#!/usr/bin/env python3
"""
Rebuild Source of Truth Script

This script rebuilds the source of truth YAML file for the AI system based on discovered agents.
It uses the output from discover_active_agents.py to create a comprehensive configuration file.

Usage:
    python rebuild_source_of_truth.py [--input INPUT_FILE] [--output OUTPUT_FILE]
"""

import os
import sys
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def rebuild_source_of_truth(agent_data: Dict[str, Any], output_file: str):
    """Rebuild the source of truth YAML file from agent data."""
    # Create the base structure for the source of truth file
    source_of_truth = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_agents": agent_data["total_agents"],
            "description": "Automatically regenerated source of truth file"
        },
        "main_pc_agents": [],
        "pc2_agents": [],
        "network": {
            "zmq_ports": [],
            "health_check_ports": [],
            "error_bus_endpoint": "tcp://0.0.0.0:5555"
        },
        "settings": {
            "error_management": {
                "enabled": True,
                "error_bus_endpoint": "tcp://0.0.0.0:5555",
                "max_retry_attempts": 3,
                "retry_delay_seconds": 5
            },
            "health_monitoring": {
                "enabled": True,
                "check_interval_seconds": 30,
                "timeout_seconds": 5
            }
        }
    }
    
    # Process agents by machine
    for agent in agent_data["agents"]:
        agent_config = {
            "name": agent["name"],
            "script_path": agent["file_paths"][0] if agent["file_paths"] else None,
            "port": agent["ports"][0] if agent["ports"] else None,
            "health_check_port": agent["health_ports"][0] if agent["health_ports"] else None,
            "dependencies": agent["dependencies"],
            "has_error_bus": agent["has_error_bus"],
            "critical": False  # Default to non-critical
        }
        
        # Add to the appropriate machine list
        if "main_pc" in agent["machines"]:
            source_of_truth["main_pc_agents"].append(agent_config)
        elif "pc2" in agent["machines"]:
            source_of_truth["pc2_agents"].append(agent_config)
    
    # Collect all ports for network configuration
    all_ports = []
    health_ports = []
    
    for agent in agent_data["agents"]:
        all_ports.extend(agent["ports"])
        health_ports.extend(agent["health_ports"])
    
    source_of_truth["network"]["zmq_ports"] = sorted(list(set(all_ports)))
    source_of_truth["network"]["health_check_ports"] = sorted(list(set(health_ports)))
    
    # Write the YAML file
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(source_of_truth, f, default_flow_style=False, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description="Rebuild source of truth YAML file")
    parser.add_argument("--input", default="active_agents_report.json", help="Input JSON file from discover_active_agents.py")
    parser.add_argument("--output", default="source_of_truth.yaml", help="Output YAML file")
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        print("Please run discover_active_agents.py first to generate the JSON report.")
        sys.exit(1)
    
    # Load agent data
    with open(args.input, 'r', encoding='utf-8') as f:
        agent_data = json.load(f)
    
    # Rebuild source of truth
    rebuild_source_of_truth(agent_data, args.output)
    
    print(f"Source of truth rebuilt and saved to {args.output}")
    print("Please review the file and make any necessary adjustments before using it.")

if __name__ == "__main__":
    main() 