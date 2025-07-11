#!/usr/bin/env python3
"""
System Diagram Generator
------------------------
Creates a comprehensive visualization of the AI System's agents across MainPC and PC2.
Generates an HTML file with a visual representation of the agents.
"""

import yaml
import os
import sys
from datetime import datetime

# Colors for different agent groups
COLOR_SCHEME = {
    # MainPC colors
    'core_services': '#e1eaef',
    'memory_system': '#f0e6d2',
    'utility_services': '#e8f0e7',
    'ai_models_gpu_services': '#d5e8d4',
    'vision_system': '#fff2cc',
    'learning_knowledge': '#dae8fc',
    'language_processing': '#d5e8d4',
    'audio_processing': '#f8cecc',
    'emotion_system': '#e1d5e7',
    'utilities_support': '#fff2cc',
    'reasoning_services': '#d5e8d4',
    
    # PC2 colors
    'pc2_integration': '#ffe6cc',
    'pc2_core': '#d0cee2',
    'pc2_for_pc2': '#b9e0a5',
    'pc2_additional': '#fad9d5',
    'pc2_central': '#ffcc99',
}

def load_config(config_path):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return None

def categorize_pc2_agents(agents):
    """Categorize PC2 agents into groups based on their script paths."""
    categorized = {
        'pc2_integration': [],
        'pc2_core': [],
        'pc2_for_pc2': [],
        'pc2_additional': [],
        'pc2_central': []
    }
    
    for agent in agents:
        path = agent.get('script_path', '')
        name = agent.get('name', '')
        
        if 'ForPC2' in path:
            categorized['pc2_for_pc2'].append(agent)
        elif any(word in name for word in ['Memory', 'MemoryOrchestrator']):
            categorized['pc2_central'].append(agent)
        elif any(word in name for word in ['Agent', 'Processor', 'Manager', 'Monitor']):
            if name in ['TieredResponder', 'AsyncProcessor', 'CacheManager', 'PerformanceMonitor', 'VisionProcessingAgent']:
                categorized['pc2_integration'].append(agent)
            elif name in ['AgentTrustScorer', 'FileSystemAssistantAgent', 'RemoteConnectorAgent', 'UnifiedWebAgent', 'DreamingModeAgent', 'PerformanceLoggerAgent', 'AdvancedRouter', 'TutoringAgent']:
                categorized['pc2_additional'].append(agent)
            else:
                categorized['pc2_core'].append(agent)
        else:
            categorized['pc2_core'].append(agent)
    
    return categorized

def generate_agent_html(agent_name, port, health_port, bg_color):
    """Generate HTML for a single agent box."""
    return f'''
    <div class="agent" style="background-color: {bg_color};">
        <div class="agent-name">{agent_name}</div>
        <div class="agent-port">Port: {port}</div>
        <div class="agent-health">Health: {health_port}</div>
    </div>
    '''

def create_html_diagram(mainpc_config, pc2_config, output_file='system_diagram.html'):
    """Create an HTML representation of the system architecture."""
    
    # Start the HTML content
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI System Architecture</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 100%;
            margin: 0 auto;
        }}
        h1, h2, h3 {{
            text-align: center;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        h2 {{
            color: #444;
            margin-top: 30px;
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 5px;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
            margin-bottom: 10px;
            padding: 5px;
            border-radius: 5px;
        }}
        .mainpc {{
            background-color: #e6f3ff;
            border: 2px solid #0066cc;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .mainpc h2 {{
            background-color: #0066cc;
            color: white;
        }}
        .pc2 {{
            background-color: #e6ffe6;
            border: 2px solid #009933;
            padding: 20px;
            border-radius: 10px;
        }}
        .pc2 h2 {{
            background-color: #009933;
            color: white;
        }}
        .group {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 20px;
        }}
        .agents-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
        }}
        .agent {{
            border: 1px solid #333;
            border-radius: 5px;
            padding: 10px;
            width: 180px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        .agent-name {{
            font-weight: bold;
            text-align: center;
            margin-bottom: 5px;
            font-size: 14px;
        }}
        .agent-port, .agent-health {{
            font-size: 12px;
            color: #555;
        }}
        .timestamp {{
            text-align: center;
            font-size: 12px;
            color: #777;
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI System Architecture</h1>
        
        <!-- MainPC System -->
        <div class="mainpc">
            <h2>MainPC System</h2>
'''

    # Add MainPC agent groups
    for group_name, agents in mainpc_config.get('agent_groups', {}).items():
        group_color = COLOR_SCHEME.get(group_name, '#f0f0f0')
        html_content += f'''
            <div class="group" style="background-color: {group_color};">
                <h3>{group_name.replace('_', ' ').title()}</h3>
                <div class="agents-container">
'''
        
        # Add agents in this group
        for agent_name, agent_data in agents.items():
            port = agent_data.get('port', 'N/A')
            health_port = agent_data.get('health_check_port', 'N/A')
            html_content += generate_agent_html(agent_name, port, health_port, group_color)
        
        html_content += '''
                </div>
            </div>
'''

    # Start PC2 section
    html_content += '''
        </div>
        
        <!-- PC2 System -->
        <div class="pc2">
            <h2>PC2 System</h2>
'''

    # Add PC2 core services
    if pc2_config.get('core_services'):
        group_color = COLOR_SCHEME.get('pc2_central', '#ffcc99')
        html_content += f'''
            <div class="group" style="background-color: {group_color};">
                <h3>Central Services</h3>
                <div class="agents-container">
'''
        
        for service in pc2_config.get('core_services', []):
            name = service.get('name', '')
            port = service.get('port', 'N/A')
            health_port = service.get('health_check_port', 'N/A')
            html_content += generate_agent_html(name, port, health_port, group_color)
        
        html_content += '''
                </div>
            </div>
'''

    # Categorize PC2 agents
    pc2_agents = pc2_config.get('pc2_services', [])
    categorized_agents = categorize_pc2_agents(pc2_agents)
    
    # Add PC2 agent groups
    for group_name, agents in categorized_agents.items():
        if not agents:
            continue
            
        group_color = COLOR_SCHEME.get(group_name, '#f0f0f0')
        html_content += f'''
            <div class="group" style="background-color: {group_color};">
                <h3>{group_name.replace('pc2_', '').replace('_', ' ').title()}</h3>
                <div class="agents-container">
'''
        
        # Add agents in this group
        for agent in agents:
            name = agent.get('name', '')
            port = agent.get('port', 'N/A')
            health_port = agent.get('health_check_port', 'N/A')
            html_content += generate_agent_html(name, port, health_port, group_color)
        
        html_content += '''
                </div>
            </div>
'''

    # Close HTML
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    html_content += f'''
        </div>
        
        <div class="timestamp">Generated on {timestamp}</div>
    </div>
</body>
</html>
'''

    # Write to file
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"HTML diagram created: {output_file}")
    return output_file

def main():
    # Get file paths
    mainpc_config_path = 'main_pc_code/config/startup_config.yaml'
    pc2_config_path = 'pc2_code/config/startup_config.yaml'
    
    # Load configurations
    mainpc_config = load_config(mainpc_config_path)
    pc2_config = load_config(pc2_config_path)
    
    if not mainpc_config or not pc2_config:
        print("Error: Could not load one or more configuration files.")
        sys.exit(1)
    
    # Create the diagram
    output_file = create_html_diagram(mainpc_config, pc2_config, 'ai_system_architecture.html')
    print(f"Please open {output_file} in your browser to view the system diagram.")

if __name__ == "__main__":
    main() 