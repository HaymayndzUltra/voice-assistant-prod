#!/usr/bin/env python3
"""
Comprehensive Agent Inventory Analyzer
Extracts all agents from MainPC and PC2 startup configuration files
for comprehensive agent audit and optimization analysis.

Part of Phase 1: Agent Inventory & Analysis
"""

import yaml
import json
from pathlib import Path
from collections import defaultdict
import sys

def parse_agent_config(config_file_path, system_name):
    """
    Parse agent configuration file and extract all agent information
    
    Args:
        config_file_path (str): Path to the startup_config.yaml file
        system_name (str): Name of the system (MainPC or PC2)
    
    Returns:
        dict: Comprehensive agent information
    """
    
    try:
        with open(config_file_path, 'r') as file:
            config = yaml.safe_load(file)
    except Exception as e:
        print(f"❌ Error loading {config_file_path}: {e}")
        return {}
    
    agents_info = {
        'system': system_name,
        'config_file': config_file_path,
        'agent_groups': {},
        'total_agents': 0,
        'agents_list': []
    }
    
    # Extract agent groups (MainPC format)
    if 'agent_groups' in config:
        agent_groups = config['agent_groups']
        
        for group_name, agents in agent_groups.items():
            if isinstance(agents, dict):
                agents_info['agent_groups'][group_name] = []
                
                for agent_name, agent_config in agents.items():
                    if isinstance(agent_config, dict):
                        agent_info = {
                            'name': agent_name,
                            'group': group_name,
                            'script_path': agent_config.get('script_path', 'N/A'),
                            'port': agent_config.get('port', 'N/A'),
                            'health_check_port': agent_config.get('health_check_port', 'N/A'),
                            'required': agent_config.get('required', False),
                            'dependencies': agent_config.get('dependencies', []),
                            'config': agent_config.get('config', {}),
                            'system': system_name
                        }
                        
                        agents_info['agent_groups'][group_name].append(agent_info)
                        agents_info['agents_list'].append(agent_info)
                        agents_info['total_agents'] += 1
    
    # Extract PC2 services (PC2 format)
    elif 'pc2_services' in config:
        pc2_services = config['pc2_services']
        agents_info['agent_groups']['pc2_services'] = []
        
        for agent_config in pc2_services:
            if isinstance(agent_config, dict):
                agent_info = {
                    'name': agent_config.get('name', 'N/A'),
                    'group': 'pc2_services',
                    'script_path': agent_config.get('script_path', 'N/A'),
                    'port': agent_config.get('port', 'N/A'),
                    'health_check_port': agent_config.get('health_check_port', 'N/A'),
                    'required': agent_config.get('required', False),
                    'dependencies': agent_config.get('dependencies', []),
                    'host': agent_config.get('host', 'N/A'),
                    'system': system_name
                }
                
                agents_info['agent_groups']['pc2_services'].append(agent_info)
                agents_info['agents_list'].append(agent_info)
                agents_info['total_agents'] += 1
    
    return agents_info

def analyze_dependencies(agents_info):
    """
    Analyze dependencies between agents
    
    Args:
        agents_info (dict): Agent information from parse_agent_config
    
    Returns:
        dict: Dependency analysis
    """
    
    dependency_analysis = {
        'dependency_graph': {},
        'dependency_count': {},
        'critical_agents': [],  # Agents with many dependents
        'orphaned_agents': []   # Agents with no dependencies
    }
    
    # Build dependency graph
    for agent in agents_info['agents_list']:
        agent_name = agent['name']
        dependencies = agent['dependencies']
        
        dependency_analysis['dependency_graph'][agent_name] = dependencies
        dependency_analysis['dependency_count'][agent_name] = len(dependencies)
        
        if len(dependencies) == 0:
            dependency_analysis['orphaned_agents'].append(agent_name)
    
    # Find critical agents (agents that many others depend on)
    dependents_count = defaultdict(int)
    for agent_name, deps in dependency_analysis['dependency_graph'].items():
        for dep in deps:
            dependents_count[dep] += 1
    
    # Agents with 3+ dependents are considered critical
    critical_threshold = 3
    for agent, count in dependents_count.items():
        if count >= critical_threshold:
            dependency_analysis['critical_agents'].append({
                'name': agent,
                'dependents_count': count
            })
    
    return dependency_analysis

def categorize_agents(agents_info):
    """
    Categorize agents by function and resource requirements
    
    Args:
        agents_info (dict): Agent information from parse_agent_config
    
    Returns:
        dict: Agent categorization
    """
    
    categorization = {
        'by_function': {
            'AI Processing': [],
            'Data Management': [],
            'Communication': [],
            'System Infrastructure': [],
            'User Interface': [],
            'Monitoring & Analytics': [],
            'Audio/Speech': [],
            'Translation': [],
            'Learning & Training': [],
            'Other': []
        },
        'by_resource_type': {
            'CPU-Intensive': [],
            'Memory-Heavy': [],
            'GPU-Required': [],
            'I/O-Bound': [],
            'Network-Heavy': [],
            'Storage-Heavy': []
        }
    }
    
    # Function-based categorization (based on agent names and groups)
    for agent in agents_info['agents_list']:
        agent_name = agent['name'].lower()
        group_name = agent['group'].lower()
        script_path = agent['script_path'].lower()
        
        # AI Processing
        if any(keyword in agent_name for keyword in ['model', 'llm', 'orchestrator', 'reasoning', 'chain', 'thought', 'nlu', 'nlp', 'inference']):
            categorization['by_function']['AI Processing'].append(agent)
        
        # Data Management
        elif any(keyword in agent_name for keyword in ['memory', 'knowledge', 'database', 'storage', 'cache', 'digital_twin']):
            categorization['by_function']['Data Management'].append(agent)
        
        # Communication
        elif any(keyword in agent_name for keyword in ['coordinator', 'registry', 'service', 'request', 'streaming']):
            categorization['by_function']['Communication'].append(agent)
        
        # Audio/Speech
        elif any(keyword in agent_name for keyword in ['stt', 'tts', 'speech', 'audio', 'voice', 'streaming', 'wake']):
            categorization['by_function']['Audio/Speech'].append(agent)
        
        # System Infrastructure
        elif any(keyword in agent_name for keyword in ['system', 'vram', 'optimizer', 'observability', 'unified']):
            categorization['by_function']['System Infrastructure'].append(agent)
        
        # Learning & Training
        elif any(keyword in agent_name for keyword in ['learning', 'training', 'fine', 'tuner', 'adjuster']):
            categorization['by_function']['Learning & Training'].append(agent)
        
        # Translation
        elif any(keyword in agent_name for keyword in ['translation', 'nllb', 'translate']):
            categorization['by_function']['Translation'].append(agent)
        
        # Monitoring & Analytics
        elif any(keyword in agent_name for keyword in ['monitor', 'analytics', 'metrics', 'tracker', 'observability']):
            categorization['by_function']['Monitoring & Analytics'].append(agent)
        
        # User Interface
        elif any(keyword in agent_name for keyword in ['ui', 'interface', 'command', 'handler', 'chitchat', 'proactive']):
            categorization['by_function']['User Interface'].append(agent)
        
        else:
            categorization['by_function']['Other'].append(agent)
        
        # Resource-based categorization (heuristic based on function)
        if agent['name'] in ['ModelManagerSuite', 'VRAMOptimizerAgent'] or 'model' in agent_name:
            categorization['by_resource_type']['GPU-Required'].append(agent)
        elif any(keyword in agent_name for keyword in ['memory', 'knowledge', 'cache']):
            categorization['by_resource_type']['Memory-Heavy'].append(agent)
        elif any(keyword in agent_name for keyword in ['streaming', 'audio', 'speech', 'stt', 'tts']):
            categorization['by_resource_type']['CPU-Intensive'].append(agent)
        elif any(keyword in agent_name for keyword in ['coordinator', 'registry', 'service']):
            categorization['by_resource_type']['Network-Heavy'].append(agent)
        elif any(keyword in agent_name for keyword in ['storage', 'database', 'digital_twin']):
            categorization['by_resource_type']['Storage-Heavy'].append(agent)
        else:
            categorization['by_resource_type']['I/O-Bound'].append(agent)
    
    return categorization

def generate_report(mainpc_info, pc2_info):
    """
    Generate comprehensive agent audit report
    
    Args:
        mainpc_info (dict): MainPC agent information
        pc2_info (dict): PC2 agent information
    
    Returns:
        str: Formatted report
    """
    
    report_lines = []
    report_lines.append("🎯 COMPREHENSIVE AGENT AUDIT REPORT")
    report_lines.append("=" * 50)
    report_lines.append("")
    
    # System Overview
    report_lines.append("📊 SYSTEM OVERVIEW:")
    report_lines.append(f"• MainPC Agents: {mainpc_info.get('total_agents', 0)}")
    report_lines.append(f"• PC2 Agents: {pc2_info.get('total_agents', 0)}")
    report_lines.append(f"• Total Agents: {mainpc_info.get('total_agents', 0) + pc2_info.get('total_agents', 0)}")
    report_lines.append("")
    
    # MainPC Agent Groups
    report_lines.append("🖥️ MAINPC AGENT GROUPS:")
    for group_name, agents in mainpc_info.get('agent_groups', {}).items():
        report_lines.append(f"• {group_name}: {len(agents)} agents")
        for agent in agents[:3]:  # Show first 3 agents per group
            report_lines.append(f"  - {agent['name']} (Port: {agent['port']})")
        if len(agents) > 3:
            report_lines.append(f"  ... and {len(agents) - 3} more")
    report_lines.append("")
    
    # PC2 Agent Groups  
    report_lines.append("💻 PC2 AGENT GROUPS:")
    for group_name, agents in pc2_info.get('agent_groups', {}).items():
        report_lines.append(f"• {group_name}: {len(agents)} agents")
        for agent in agents[:3]:  # Show first 3 agents per group
            report_lines.append(f"  - {agent['name']} (Port: {agent['port']})")
        if len(agents) > 3:
            report_lines.append(f"  ... and {len(agents) - 3} more")
    report_lines.append("")
    
    return "\n".join(report_lines)

def main():
    """Main execution function"""
    
    print("🚀 Starting Comprehensive Agent Audit...")
    print("Phase 1: Agent Inventory & Analysis")
    print("=" * 50)
    
    # Define config file paths
    mainpc_config = "/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml"
    pc2_config = "/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml"
    
    # Parse MainPC agents
    print("📊 Parsing MainPC agents...")
    mainpc_info = parse_agent_config(mainpc_config, "MainPC")
    print(f"✅ Found {mainpc_info.get('total_agents', 0)} MainPC agents")
    
    # Parse PC2 agents
    print("📊 Parsing PC2 agents...")
    pc2_info = parse_agent_config(pc2_config, "PC2")
    print(f"✅ Found {pc2_info.get('total_agents', 0)} PC2 agents")
    
    # Analyze dependencies
    print("🔍 Analyzing dependencies...")
    mainpc_deps = analyze_dependencies(mainpc_info)
    pc2_deps = analyze_dependencies(pc2_info)
    
    # Categorize agents
    print("📋 Categorizing agents...")
    mainpc_categories = categorize_agents(mainpc_info)
    pc2_categories = categorize_agents(pc2_info)
    
    # Generate report
    print("📄 Generating report...")
    report = generate_report(mainpc_info, pc2_info)
    print("\n" + report)
    
    # Save detailed data
    output_data = {
        'mainpc': {
            'agents_info': mainpc_info,
            'dependencies': mainpc_deps,
            'categorization': mainpc_categories
        },
        'pc2': {
            'agents_info': pc2_info,
            'dependencies': pc2_deps,
            'categorization': pc2_categories
        },
        'summary': {
            'total_agents': mainpc_info.get('total_agents', 0) + pc2_info.get('total_agents', 0),
            'mainpc_agents': mainpc_info.get('total_agents', 0),
            'pc2_agents': pc2_info.get('total_agents', 0)
        }
    }
    
    # Save to JSON file
    output_file = "/home/haymayndz/AI_System_Monorepo/agent_audit_phase1_results.json"
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"💾 Detailed results saved to: {output_file}")
    print("🎉 Phase 1 Analysis Complete!")
    
    return output_data

if __name__ == "__main__":
    main()
