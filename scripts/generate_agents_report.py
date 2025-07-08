#!/usr/bin/env python3
"""
Generate Agents Report Script

This script generates a comprehensive markdown report of all agents in the system.
It uses the output from discover_active_agents.py to create a human-readable report.

Usage:
    python generate_agents_report.py [--input INPUT_FILE] [--output OUTPUT_FILE]
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def generate_markdown_report(agent_data: Dict[str, Any], output_file: str):
    """Generate a markdown report from the agent data."""
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write("# AI System Agents Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write summary
        f.write("## Summary\n\n")
        f.write(f"- **Total Agents**: {agent_data['total_agents']}\n")
        f.write(f"- **Running Agents**: {agent_data['running_agents']}\n")
        f.write(f"- **Agents with Error Bus Integration**: {agent_data['agents_with_error_bus']}\n")
        
        # Count agents by machine
        main_pc_agents = sum(1 for agent in agent_data['agents'] if "main_pc" in agent["machines"])
        pc2_agents = sum(1 for agent in agent_data['agents'] if "pc2" in agent["machines"])
        f.write(f"- **Main PC Agents**: {main_pc_agents}\n")
        f.write(f"- **PC2 Agents**: {pc2_agents}\n\n")
        
        # Generate dependency graph
        f.write("## Agent Dependency Graph\n\n")
        f.write("```mermaid\ngraph TD;\n")
        
        # Add nodes
        for agent in agent_data['agents']:
            status = "🟢" if agent["running"] else "🔴"
            error_bus = "🔄" if agent["has_error_bus"] else ""
            machine_icons = {"main_pc": "💻", "pc2": "🖥️", "unknown": "❓"}
            machine_icon = " ".join(machine_icons.get(m, "❓") for m in agent["machines"])
            
            f.write(f'  {agent["name"]}["{status} {machine_icon} {agent["name"]}{error_bus}"];\n')
        
        # Add edges for dependencies
        for agent in agent_data['agents']:
            for dep in agent["dependencies"]:
                if any(a["name"] == dep for a in agent_data['agents']):
                    f.write(f'  {dep} --> {agent["name"]};\n')
        
        f.write("```\n\n")
        
        # Legend
        f.write("### Legend\n\n")
        f.write("- 🟢 Running agent\n")
        f.write("- 🔴 Not running agent\n")
        f.write("- 💻 Main PC agent\n")
        f.write("- 🖥️ PC2 agent\n")
        f.write("- 🔄 Has Error Bus integration\n\n")
        
        # Write agents by machine
        f.write("## Agents by Machine\n\n")
        
        # Main PC agents
        f.write("### Main PC Agents\n\n")
        f.write("| Agent | Status | Error Bus | Ports | Health Ports | Dependencies |\n")
        f.write("|-------|--------|-----------|-------|--------------|-------------|\n")
        
        for agent in sorted([a for a in agent_data['agents'] if "main_pc" in a["machines"]], key=lambda x: x["name"]):
            status = "🟢 Running" if agent["running"] else "🔴 Not Running"
            error_bus = "✅" if agent["has_error_bus"] else "❌"
            ports = ", ".join(map(str, agent["ports"])) if agent["ports"] else "-"
            health_ports = ", ".join(map(str, agent["health_ports"])) if agent["health_ports"] else "-"
            dependencies = ", ".join(agent["dependencies"]) if agent["dependencies"] else "-"
            
            f.write(f"| {agent['name']} | {status} | {error_bus} | {ports} | {health_ports} | {dependencies} |\n")
        
        f.write("\n")
        
        # PC2 agents
        f.write("### PC2 Agents\n\n")
        f.write("| Agent | Status | Error Bus | Ports | Health Ports | Dependencies |\n")
        f.write("|-------|--------|-----------|-------|--------------|-------------|\n")
        
        for agent in sorted([a for a in agent_data['agents'] if "pc2" in a["machines"]], key=lambda x: x["name"]):
            status = "🟢 Running" if agent["running"] else "🔴 Not Running"
            error_bus = "✅" if agent["has_error_bus"] else "❌"
            ports = ", ".join(map(str, agent["ports"])) if agent["ports"] else "-"
            health_ports = ", ".join(map(str, agent["health_ports"])) if agent["health_ports"] else "-"
            dependencies = ", ".join(agent["dependencies"]) if agent["dependencies"] else "-"
            
            f.write(f"| {agent['name']} | {status} | {error_bus} | {ports} | {health_ports} | {dependencies} |\n")
        
        f.write("\n")
        
        # Detailed agent information
        f.write("## Detailed Agent Information\n\n")
        
        for agent in sorted(agent_data['agents'], key=lambda x: x["name"]):
            f.write(f"### {agent['name']}\n\n")
            
            # Status and basic info
            status = "🟢 Running" if agent["running"] else "🔴 Not Running"
            f.write(f"- **Status**: {status}\n")
            f.write(f"- **Machines**: {', '.join(agent['machines'])}\n")
            f.write(f"- **Error Bus Integration**: {'Yes' if agent['has_error_bus'] else 'No'}\n")
            
            # Ports
            if agent["ports"]:
                f.write(f"- **Ports**: {', '.join(map(str, agent['ports']))}\n")
            
            # Health check ports
            if agent["health_ports"]:
                f.write(f"- **Health Check Ports**: {', '.join(map(str, agent['health_ports']))}\n")
            
            # Dependencies
            if agent["dependencies"]:
                f.write(f"- **Dependencies**: {', '.join(agent['dependencies'])}\n")
            
            # File paths
            if agent["file_paths"]:
                f.write("- **Implementation Files**:\n")
                for path in agent["file_paths"]:
                    f.write(f"  - `{path}`\n")
            
            # Configuration files
            if "in_config_files" in agent and agent["in_config_files"]:
                f.write("- **Configuration Files**:\n")
                for path in agent["in_config_files"]:
                    f.write(f"  - `{path}`\n")
            
            f.write("\n")
        
        # Recommendations
        f.write("## Recommendations\n\n")
        
        # Check for agents without error bus
        agents_without_error_bus = [a["name"] for a in agent_data['agents'] if not a["has_error_bus"]]
        if agents_without_error_bus:
            f.write("### Agents Missing Error Bus Integration\n\n")
            f.write("The following agents should be updated to integrate with the Error Bus:\n\n")
            for agent in agents_without_error_bus:
                f.write(f"- {agent}\n")
            f.write("\n")
        
        # Check for critical agents not running
        critical_not_running = []
        for agent in agent_data['agents']:
            if not agent["running"] and agent.get("critical", False):
                critical_not_running.append(agent["name"])
        
        if critical_not_running:
            f.write("### Critical Agents Not Running\n\n")
            f.write("The following critical agents are not currently running and should be started:\n\n")
            for agent in critical_not_running:
                f.write(f"- {agent}\n")
            f.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Generate a markdown report of all agents")
    parser.add_argument("--input", default="active_agents_report.json", help="Input JSON file from discover_active_agents.py")
    parser.add_argument("--output", default="active_agents_report.md", help="Output markdown file")
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
        print("Please run discover_active_agents.py first to generate the JSON report.")
        sys.exit(1)
    
    # Load agent data
    with open(args.input, 'r', encoding='utf-8') as f:
        agent_data = json.load(f)
    
    # Generate markdown report
    generate_markdown_report(agent_data, args.output)
    
    print(f"Report generated at {args.output}")

if __name__ == "__main__":
    main() 