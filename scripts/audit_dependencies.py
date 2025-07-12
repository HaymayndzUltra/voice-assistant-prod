#!/usr/bin/env python3
"""
Dependency Audit Script
-----------------------
This script analyzes the true dependencies of all agents in the system by
examining their source code for service connections and imports.
"""

import os
import re
import yaml
import logging
from pathlib import Path
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("audit_dependencies.log")
    ]
)

logger = logging.getLogger("DependencyAudit")

# Map of common service name patterns to standardized agent names
SERVICE_NAME_MAP = {
    "StreamingTtsAgent": "StreamingTTSAgent",
    "StreamingTTS": "StreamingTTSAgent",
    "TtsService": "TTSService",
    "TTSCache": "TTSService",
    "TTSConnector": "TTSService",
    "FaceRecognition": "FaceRecognitionAgent",
    "MemoryOrchestrator": "MemoryOrchestratorService",
    "ModelManager": "ModelManagerAgent",
    "GGUF": "GGUFModelManager",
    "VRAMOptimizer": "VRAMOptimizerAgent",
    "SystemDigital": "SystemDigitalTwin",
    "RequestCoord": "RequestCoordinator",
    # Add more mappings as needed
}

def normalize_agent_name(name):
    """Normalize service names to match the canonical agent names in config"""
    # Direct match in the map
    if name in SERVICE_NAME_MAP:
        return SERVICE_NAME_MAP[name]
    
    # Check for partial matches
    for key, value in SERVICE_NAME_MAP.items():
        if key in name:
            return value
    
    # If name ends with Agent, return as is
    if name.endswith("Agent") or name.endswith("Service"):
        return name
        
    # Otherwise, add Agent suffix if it's not already there
    if not name.endswith("Agent") and not name.endswith("Service"):
        name = f"{name}Agent"
    
    return name

def analyze_dependencies(file_path):
    """
    Extract actual dependencies from a Python file by analyzing:
    - Import statements
    - Service discovery calls
    - Socket connections
    - Config references
    """
    logger.info(f"Analyzing dependencies in {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return set()
    
    # Known patterns for service connections
    connection_patterns = [
        # Service discovery patterns
        r'discover_service\(["\']([^"\']+)["\']',
        r'get_service_address\(["\']([^"\']+)["\']',
        
        # Config port references
        r'config\.get\(["\']([^"\']+)_port["\']\)',
        r'config\.get\(["\']([^"\']+)_host["\']\)',
        
        # Socket connections
        r'\.connect\(["\']tcp://[^"\']+["\'].*?# ([A-Za-z0-9]+)',
        r'\.connect\(["\']tcp://[^"\']+/([A-Za-z0-9]+)',
        
        # Dependency declarations
        r'dependencies\s*=\s*\[[^\]]*["\']([A-Za-z0-9]+)["\']',
        
        # Common method naming patterns
        r'connect_to_([A-Za-z0-9]+)',
        r'([A-Za-z0-9]+)_socket\s*=',
        r'self\.([A-Za-z0-9]+)_socket\s*=',
        r'([A-Za-z0-9]+)_address\s*=',
        
        # Direct string mentions
        r'["\']depends_on["\'].*?["\']([A-Za-z0-9]+)["\']'
    ]
    
    # Collect all potential service connections
    connections = []
    for pattern in connection_patterns:
        matches = re.findall(pattern, content)
        if matches:
            connections.extend(matches)
    
    # Look for import statements that indicate dependencies
    import_patterns = [
        # Look for imports from both main_pc_code and pc2_code
        r'from\s+main_pc_code\.(agents|FORMAINPC)\.([a-zA-Z0-9_]+)\s+import',
        r'import\s+main_pc_code\.(agents|FORMAINPC)\.([a-zA-Z0-9_]+)',
        r'from\s+pc2_code\.(agents|ForPC2)\.([a-zA-Z0-9_]+)\s+import',
        r'import\s+pc2_code\.(agents|ForPC2)\.([a-zA-Z0-9_]+)'
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content)
        if matches:
            for match in matches:
                if len(match) >= 2:
                    connections.append(match[1])
    
    # Clean and normalize the connection names
    normalized_connections = set()
    for conn in connections:
        if conn and isinstance(conn, str) and len(conn) >= 3:  # Avoid very short names
            # Clean the name: remove non-alphanumeric chars and normalize
            clean_name = re.sub(r'[^A-Za-z0-9]', '', conn)
            normalized = normalize_agent_name(clean_name)
            if normalized and len(normalized) >= 3:
                normalized_connections.add(normalized)
    
    # SystemDigitalTwin is almost always a dependency for main_pc_code agents
    if "main_pc_code" in file_path and "SystemDigitalTwin" not in normalized_connections and len(normalized_connections) > 0:
        normalized_connections.add("SystemDigitalTwin")
    
    return normalized_connections

def verify_agent_exists_in_config(agent_name, config):
    """Check if an agent with this name exists in the config"""
    if not config:
        return False
    
    # Check in main_pc_code config format
    if 'agent_groups' in config:
        for group_name, group in config['agent_groups'].items():
            if group and agent_name in group:
                return True
    
    # Check in pc2_code config format
    if 'pc2_services' in config:
        for service in config['pc2_services']:
            if service.get('name') == agent_name:
                return True
    
    # Check in core_services for pc2
    if 'core_services' in config:
        for service in config['core_services']:
            if service.get('name') == agent_name:
                return True
                
    return False

def load_configs():
    """Load both main_pc and pc2 configs"""
    configs = {}
    
    # Load main_pc config
    main_pc_config_path = "main_pc_code/config/startup_config.yaml"
    if os.path.exists(main_pc_config_path):
        try:
            with open(main_pc_config_path, 'r') as f:
                configs['main_pc'] = yaml.safe_load(f)
            logger.info(f"Loaded main_pc config from {main_pc_config_path}")
        except Exception as e:
            logger.error(f"Error loading main_pc config: {str(e)}")
    
    # Load pc2 config
    pc2_config_path = "pc2_code/config/startup_config.yaml"
    if os.path.exists(pc2_config_path):
        try:
            with open(pc2_config_path, 'r') as f:
                configs['pc2'] = yaml.safe_load(f)
            logger.info(f"Loaded pc2 config from {pc2_config_path}")
        except Exception as e:
            logger.error(f"Error loading pc2 config: {str(e)}")
    
    return configs

def fix_dependencies(source_config_path, target_config_path):
    """Update startup config with correct dependencies"""
    logger.info(f"Fixing dependencies in {source_config_path}")
    
    # Check if the file exists
    if not os.path.exists(source_config_path):
        logger.error(f"Config file not found: {source_config_path}")
        return False
    
    # Determine if this is main_pc or pc2 config
    is_main_pc = "main_pc_code" in source_config_path
    
    # Load config
    try:
        with open(source_config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate config structure
        if not config:
            logger.error(f"Empty configuration in {source_config_path}")
            return False
            
        if is_main_pc and 'agent_groups' not in config:
            logger.error(f"Missing 'agent_groups' section in {source_config_path}")
            return False
            
        if not is_main_pc and 'pc2_services' not in config:
            logger.error(f"Missing 'pc2_services' section in {source_config_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error loading config {source_config_path}: {str(e)}")
        return False
    
    # Map to keep track of agent to file path
    agent_file_paths = {}
    
    # Process each agent
    fixed_agents = 0
    added_deps = 0
    
    if is_main_pc:
        # Process main_pc config format
        # First pass: collect all agent script paths
        for group_name, group in config['agent_groups'].items():
            if not group:  # Skip empty groups
                logger.warning(f"Empty group found: {group_name}")
                continue
                
            for agent_name, agent_info in group.items():
                if agent_info and 'script_path' in agent_info:
                    script_path = agent_info['script_path']
                    agent_file_paths[agent_name] = script_path
        
        # Second pass: analyze and update dependencies
        for group_name, group in config['agent_groups'].items():
            if not group:  # Skip empty groups
                continue
                
            for agent_name, agent_info in group.items():
                if not agent_info:
                    logger.warning(f"Empty agent info for {agent_name} in group {group_name}")
                    continue
                    
                if 'script_path' in agent_info:
                    script_path = agent_info['script_path']
                    
                    # Use the absolute path from the workspace root
                    full_path = os.path.join(os.getcwd(), script_path)
                    
                    # Check if file exists
                    if not os.path.exists(full_path):
                        logger.warning(f"Agent {agent_name} script not found at {full_path}")
                        continue
                    
                    # Get current configured dependencies
                    current_deps = set(agent_info.get('dependencies', []))
                    
                    # Analyze actual dependencies from code
                    actual_deps = analyze_dependencies(full_path)
                    
                    # Filter out dependencies that don't exist in the config
                    valid_actual_deps = set()
                    for dep in actual_deps:
                        if verify_agent_exists_in_config(dep, config):
                            valid_actual_deps.add(dep)
                        else:
                            logger.warning(f"Dependency {dep} for {agent_name} not found in config")
                    
                    # Don't allow self-dependencies
                    if agent_name in valid_actual_deps:
                        valid_actual_deps.remove(agent_name)
                    
                    # Find missing dependencies
                    missing_deps = valid_actual_deps - current_deps
                    
                    # Update if needed
                    if missing_deps:
                        fixed_agents += 1
                        added_deps += len(missing_deps)
                        logger.info(f"Updating {agent_name}: Adding dependencies: {missing_deps}")
                        
                        # Merge dependencies
                        new_deps = list(current_deps.union(valid_actual_deps))
                        # Sort for consistency
                        new_deps.sort()
                        agent_info['dependencies'] = new_deps
    else:
        # Process pc2 config format
        # First pass: collect all agent script paths
        for service in config.get('pc2_services', []):
            if 'name' in service and 'script_path' in service:
                agent_name = service['name']
                script_path = service['script_path']
                agent_file_paths[agent_name] = script_path
        
        # Add core services too
        for service in config.get('core_services', []):
            if 'name' in service and 'script_path' in service:
                agent_name = service['name']
                script_path = service['script_path']
                agent_file_paths[agent_name] = script_path
        
        # Second pass: analyze and update dependencies
        for service in config.get('pc2_services', []) + config.get('core_services', []):
            if 'name' in service and 'script_path' in service:
                agent_name = service['name']
                script_path = service['script_path']
                
                # Use the absolute path from the workspace root
                full_path = os.path.join(os.getcwd(), script_path)
                
                # Check if file exists
                if not os.path.exists(full_path):
                    logger.warning(f"Agent {agent_name} script not found at {full_path}")
                    continue
                
                # Get current configured dependencies
                current_deps = set(service.get('dependencies', []))
                
                # Analyze actual dependencies from code
                actual_deps = analyze_dependencies(full_path)
                
                # Filter out dependencies that don't exist in the config
                valid_actual_deps = set()
                for dep in actual_deps:
                    if verify_agent_exists_in_config(dep, config):
                        valid_actual_deps.add(dep)
                    else:
                        logger.warning(f"Dependency {dep} for {agent_name} not found in config")
                
                # Don't allow self-dependencies
                if agent_name in valid_actual_deps:
                    valid_actual_deps.remove(agent_name)
                
                # Find missing dependencies
                missing_deps = valid_actual_deps - current_deps
                
                # Update if needed
                if missing_deps:
                    fixed_agents += 1
                    added_deps += len(missing_deps)
                    logger.info(f"Updating {agent_name}: Adding dependencies: {missing_deps}")
                    
                    # Merge dependencies
                    new_deps = list(current_deps.union(valid_actual_deps))
                    # Sort for consistency
                    new_deps.sort()
                    service['dependencies'] = new_deps
    
    # Save updated config
    try:
        os.makedirs(os.path.dirname(target_config_path), exist_ok=True)
        with open(target_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Updated config saved to {target_config_path}")
        logger.info(f"Fixed {fixed_agents} agents by adding {added_deps} dependencies")
        return True
    except Exception as e:
        logger.error(f"Error saving updated config to {target_config_path}: {str(e)}")
        return False

def generate_dependency_graph(config_path, output_path):
    """Generate a graphviz dependency graph from the config file"""
    try:
        import graphviz
    except ImportError:
        logger.error("graphviz package not installed. Please install with: pip install graphviz")
        return False
    
    logger.info(f"Generating dependency graph from {config_path}")
    
    # Check if the file exists
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return False
    
    # Determine if this is main_pc or pc2 config
    is_main_pc = "main_pc_code" in config_path
    
    # Load config
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate config structure
        if not config:
            logger.error(f"Empty configuration in {config_path}")
            return False
            
        if is_main_pc and 'agent_groups' not in config:
            logger.error(f"Missing 'agent_groups' section in {config_path}")
            return False
            
        if not is_main_pc and 'pc2_services' not in config:
            logger.error(f"Missing 'pc2_services' section in {config_path}")
            return False
    except Exception as e:
        logger.error(f"Error loading config {config_path}: {str(e)}")
        return False
    
    # Create graph
    dot = graphviz.Digraph(comment='System Dependencies', 
                          format='png', 
                          engine='dot', 
                          graph_attr={'rankdir': 'LR', 'size': '12,8', 'ratio': 'fill'})
    
    # Group colors for better visualization
    group_colors = {
        'core_services': '#FF6B6B',  # Red
        'memory_system': '#4ECDC4',  # Teal
        'utility_services': '#45B7D1', # Light Blue
        'gpu_infrastructure': '#FFA726', # Orange
        'reasoning_services': '#66BB6A', # Green
        'vision_processing': '#BA68C8', # Purple
        'learning_knowledge': '#FFD54F', # Yellow
        'language_processing': '#7986CB', # Indigo
        'speech_services': '#4FC3F7', # Sky Blue
        'audio_interface': '#AED581', # Light Green
        'emotion_system': '#FF8A65', # Deep Orange
    }
    
    # Create nodes and edges based on config type
    if is_main_pc:
        # Process main_pc config format
        # First create all nodes grouped by agent_group
        for group_name, group in config['agent_groups'].items():
            if not group:  # Skip empty groups
                continue
                
            # Create a subgraph for this group
            subgraph_name = f'cluster_{group_name}'
            subgraph = graphviz.Digraph(name=subgraph_name)
            subgraph.attr(label=group_name, style='filled', color=group_colors.get(group_name, '#CCCCCC'),
                         fontsize='16', fontcolor='black', fontname='Arial')
            
            # Add all agents in this group as nodes
            for agent_name in group:
                subgraph.node(agent_name, agent_name, shape='box', 
                             style='filled', fillcolor='white', fontname='Arial')
            
            # Add the subgraph to the main graph
            dot.subgraph(subgraph)
        
        # Now add all dependency edges
        for group_name, group in config['agent_groups'].items():
            if not group:
                continue
                
            for agent_name, agent_info in group.items():
                if not agent_info:
                    continue
                    
                # Add edges for each dependency
                for dep in agent_info.get('dependencies', []):
                    dot.edge(agent_name, dep, fontname='Arial')
    else:
        # Process pc2 config format
        # Create a subgraph for pc2 services
        pc2_subgraph = graphviz.Digraph(name='cluster_pc2_services')
        pc2_subgraph.attr(label='PC2 Services', style='filled', color='#4ECDC4',
                        fontsize='16', fontcolor='black', fontname='Arial')
        
        # Add all pc2 services as nodes
        for service in config.get('pc2_services', []):
            if 'name' in service:
                agent_name = service['name']
                pc2_subgraph.node(agent_name, agent_name, shape='box', 
                                style='filled', fillcolor='white', fontname='Arial')
        
        # Add the pc2 services subgraph to the main graph
        dot.subgraph(pc2_subgraph)
        
        # Create a subgraph for core services
        core_subgraph = graphviz.Digraph(name='cluster_core_services')
        core_subgraph.attr(label='Core Services', style='filled', color='#FF6B6B',
                         fontsize='16', fontcolor='black', fontname='Arial')
        
        # Add all core services as nodes
        for service in config.get('core_services', []):
            if 'name' in service:
                agent_name = service['name']
                core_subgraph.node(agent_name, agent_name, shape='box', 
                                 style='filled', fillcolor='white', fontname='Arial')
        
        # Add the core services subgraph to the main graph
        dot.subgraph(core_subgraph)
        
        # Add all dependency edges
        for service in config.get('pc2_services', []) + config.get('core_services', []):
            if 'name' in service:
                agent_name = service['name']
                for dep in service.get('dependencies', []):
                    dot.edge(agent_name, dep, fontname='Arial')
    
    # Render the graph
    try:
        dot.render(output_path, cleanup=True)
        logger.info(f"Dependency graph saved to {output_path}.png")
        return True
    except Exception as e:
        logger.error(f"Error generating dependency graph: {str(e)}")
        return False

if __name__ == "__main__":
    # Check if a specific config was provided
    if len(sys.argv) > 1 and sys.argv[1] in ["main", "pc2"]:
        config_type = sys.argv[1]
        if config_type == "main":
            source_config = "main_pc_code/config/startup_config.yaml"
            target_config = "main_pc_code/config/startup_config.v2.yaml"
            graph_output = "main_pc_dependencies"
        else:
            source_config = "pc2_code/config/startup_config.yaml"
            target_config = "pc2_code/config/startup_config.v2.yaml"
            graph_output = "pc2_dependencies"
    else:
        # Default to main_pc
        source_config = "main_pc_code/config/startup_config.yaml"
        target_config = "main_pc_code/config/startup_config.v2.yaml"
        graph_output = "system_dependencies"
    
    # Fix dependencies
    if fix_dependencies(source_config, target_config):
        # Generate dependency graph
        generate_dependency_graph(target_config, graph_output)
        
        logger.info("Dependency audit complete. Results saved to:")
        logger.info(f"1. Updated config: {target_config}")
        logger.info(f"2. Dependency graph: {graph_output}.png")
        logger.info(f"3. Audit log: audit_dependencies.log")
        print("\nDependency audit complete!")
    else:
        logger.error("Dependency audit failed.")
        print("\nDependency audit failed. Check audit_dependencies.log for details.") 