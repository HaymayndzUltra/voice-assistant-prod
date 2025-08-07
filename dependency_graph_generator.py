#!/usr/bin/env python3
"""
AI System Dependency Graph Generator
Generates visual dependency graphs showing agent relationships and module dependencies.
"""

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
from typing import Dict, List, Tuple, Set
import json
import os

# Agent dependency data extracted from configuration analysis
MAINPC_AGENTS = {
    # Foundation Services
    "ServiceRegistry": {"deps": [], "category": "foundation", "port": 7200},
    "SystemDigitalTwin": {"deps": ["ServiceRegistry"], "category": "foundation", "port": 7220},
    "RequestCoordinator": {"deps": ["SystemDigitalTwin"], "category": "foundation", "port": 26002},
    "ModelManagerSuite": {"deps": ["SystemDigitalTwin"], "category": "foundation", "port": 7211},
    "VRAMOptimizerAgent": {"deps": ["ModelManagerSuite", "RequestCoordinator", "SystemDigitalTwin"], "category": "foundation", "port": 5572},
    "ObservabilityHub": {"deps": ["SystemDigitalTwin"], "category": "foundation", "port": 9000},
    "UnifiedSystemAgent": {"deps": ["SystemDigitalTwin"], "category": "foundation", "port": 7201},
    "SelfHealingSupervisor": {"deps": ["ObservabilityHub"], "category": "foundation", "port": 7009},
    
    # Memory System
    "MemoryClient": {"deps": ["SystemDigitalTwin"], "category": "memory", "port": 5713},
    "SessionMemoryAgent": {"deps": ["RequestCoordinator", "SystemDigitalTwin", "MemoryClient"], "category": "memory", "port": 5574},
    "KnowledgeBase": {"deps": ["MemoryClient", "SystemDigitalTwin"], "category": "memory", "port": 5715},
    
    # AI/Reasoning
    "ChainOfThoughtAgent": {"deps": ["ModelManagerSuite", "SystemDigitalTwin"], "category": "reasoning", "port": 5612},
    "GoTToTAgent": {"deps": ["ModelManagerSuite", "SystemDigitalTwin", "ChainOfThoughtAgent"], "category": "reasoning", "port": 5646},
    "CognitiveModelAgent": {"deps": ["ChainOfThoughtAgent", "SystemDigitalTwin"], "category": "reasoning", "port": 5641},
    
    # Language Processing
    "NLUAgent": {"deps": ["SystemDigitalTwin"], "category": "language", "port": 5709},
    "AdvancedCommandHandler": {"deps": ["NLUAgent", "CodeGenerator", "SystemDigitalTwin"], "category": "language", "port": 5710},
    "Responder": {"deps": ["EmotionEngine", "FaceRecognitionAgent", "NLUAgent", "StreamingTTSAgent", "SystemDigitalTwin"], "category": "language", "port": 5637},
    "ModelOrchestrator": {"deps": ["RequestCoordinator", "ModelManagerSuite", "SystemDigitalTwin"], "category": "language", "port": 7213},
    
    # Audio/Speech
    "STTService": {"deps": ["ModelManagerSuite", "SystemDigitalTwin"], "category": "audio", "port": 5800},
    "TTSService": {"deps": ["ModelManagerSuite", "SystemDigitalTwin"], "category": "audio", "port": 5801},
    "AudioCapture": {"deps": ["SystemDigitalTwin"], "category": "audio", "port": 6550},
    "StreamingTTSAgent": {"deps": ["RequestCoordinator", "TTSService", "SystemDigitalTwin"], "category": "audio", "port": 5562},
    "StreamingSpeechRecognition": {"deps": ["FusedAudioPreprocessor", "RequestCoordinator", "STTService", "SystemDigitalTwin"], "category": "audio", "port": 6553},
    
    # Emotion System
    "EmotionEngine": {"deps": ["SystemDigitalTwin"], "category": "emotion", "port": 5590},
    "MoodTrackerAgent": {"deps": ["EmotionEngine", "SystemDigitalTwin"], "category": "emotion", "port": 5704},
    "EmpathyAgent": {"deps": ["EmotionEngine", "StreamingTTSAgent", "SystemDigitalTwin"], "category": "emotion", "port": 5703},
    
    # Utility Services
    "CodeGenerator": {"deps": ["SystemDigitalTwin", "ModelManagerSuite"], "category": "utility", "port": 5650},
    "PredictiveHealthMonitor": {"deps": ["SystemDigitalTwin"], "category": "utility", "port": 5613},
    "Executor": {"deps": ["CodeGenerator", "SystemDigitalTwin"], "category": "utility", "port": 5606},
    "FaceRecognitionAgent": {"deps": ["RequestCoordinator", "ModelManagerSuite", "SystemDigitalTwin"], "category": "vision", "port": 5610},
    "FusedAudioPreprocessor": {"deps": ["AudioCapture", "SystemDigitalTwin"], "category": "audio", "port": 6551},
}

PC2_AGENTS = {
    # Infrastructure
    "PC2_ObservabilityHub": {"deps": [], "category": "infrastructure", "port": 9100},
    "ResourceManager": {"deps": ["PC2_ObservabilityHub"], "category": "infrastructure", "port": 7113},
    
    # Memory Stack
    "MemoryOrchestratorService": {"deps": [], "category": "memory", "port": 7140},
    "CacheManager": {"deps": ["MemoryOrchestratorService"], "category": "memory", "port": 7102},
    "UnifiedMemoryReasoningAgent": {"deps": ["MemoryOrchestratorService"], "category": "memory", "port": 7105},
    "ContextManager": {"deps": ["MemoryOrchestratorService"], "category": "memory", "port": 7111},
    "ExperienceTracker": {"deps": ["MemoryOrchestratorService"], "category": "memory", "port": 7112},
    
    # Processing Pipeline
    "AsyncProcessor": {"deps": ["ResourceManager"], "category": "processing", "port": 7101},
    "TaskScheduler": {"deps": ["AsyncProcessor"], "category": "processing", "port": 7115},
    "AdvancedRouter": {"deps": ["TaskScheduler"], "category": "processing", "port": 7129},
    "TieredResponder": {"deps": ["ResourceManager"], "category": "processing", "port": 7100},
    
    # Specialized Services
    "VisionProcessingAgent": {"deps": ["CacheManager"], "category": "vision", "port": 7150},
    "DreamWorldAgent": {"deps": ["MemoryOrchestratorService"], "category": "specialized", "port": 7104},
    "DreamingModeAgent": {"deps": ["DreamWorldAgent"], "category": "specialized", "port": 7127},
    "UnifiedWebAgent": {"deps": ["FileSystemAssistantAgent", "MemoryOrchestratorService"], "category": "web", "port": 7126},
    "TutoringServiceAgent": {"deps": ["MemoryOrchestratorService"], "category": "specialized", "port": 7108},
    
    # Utility Services
    "UnifiedUtilsAgent": {"deps": ["PC2_ObservabilityHub"], "category": "utility", "port": 7118},
    "FileSystemAssistantAgent": {"deps": ["UnifiedUtilsAgent"], "category": "utility", "port": 7123},
    "AuthenticationAgent": {"deps": ["UnifiedUtilsAgent"], "category": "security", "port": 7116},
    "AgentTrustScorer": {"deps": ["PC2_ObservabilityHub"], "category": "security", "port": 7122},
}

# Color scheme for different categories
COLORS = {
    "foundation": "#FF6B6B",      # Red - Critical infrastructure
    "memory": "#4ECDC4",          # Teal - Memory systems
    "reasoning": "#45B7D1",       # Blue - AI/Reasoning
    "language": "#96CEB4",        # Green - Language processing
    "audio": "#FFEAA7",           # Yellow - Audio/Speech
    "emotion": "#DDA0DD",         # Purple - Emotion systems
    "utility": "#98D8C8",         # Light green - Utilities
    "vision": "#F7DC6F",          # Light yellow - Vision
    "infrastructure": "#FF7675",   # Light red - Infrastructure
    "processing": "#74B9FF",      # Light blue - Processing
    "specialized": "#A29BFE",     # Light purple - Specialized
    "web": "#FD79A8",             # Pink - Web services
    "security": "#E17055",        # Orange - Security
}

def create_dependency_graph():
    """Create a comprehensive dependency graph of all agents"""
    G = nx.DiGraph()
    
    # Add MainPC agents
    for agent, info in MAINPC_AGENTS.items():
        G.add_node(f"MainPC_{agent}", 
                  category=info["category"], 
                  machine="MainPC",
                  port=info["port"])
        
        # Add dependency edges
        for dep in info["deps"]:
            if dep in MAINPC_AGENTS:
                G.add_edge(f"MainPC_{dep}", f"MainPC_{agent}")
    
    # Add PC2 agents
    for agent, info in PC2_AGENTS.items():
        G.add_node(f"PC2_{agent}", 
                  category=info["category"], 
                  machine="PC2",
                  port=info["port"])
        
        # Add dependency edges
        for dep in info["deps"]:
            if dep in PC2_AGENTS:
                G.add_edge(f"PC2_{dep}", f"PC2_{agent}")
    
    # Add cross-machine dependencies
    G.add_edge("MainPC_ObservabilityHub", "PC2_ObservabilityHub")  # Sync relationship
    
    return G

def create_hierarchical_layout(G, all_agents):
    """Create a hierarchical layout based on dependency levels"""
    pos = {}
    
    # Calculate dependency levels
    levels = {}
    for agent in all_agents:
        level = calculate_dependency_level(G, agent, all_agents)
        if level not in levels:
            levels[level] = []
        levels[level].append(agent)
    
    # Position nodes by level and category
    y_offset = 0
    level_height = 3
    
    for level in sorted(levels.keys()):
        agents_in_level = levels[level]
        
        # Group by category for better visual organization
        categories = {}
        for agent in agents_in_level:
            category = G.nodes[agent].get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(agent)
        
        x_offset = 0
        category_width = 8
        
        for category, category_agents in categories.items():
            agents_per_row = 4
            rows = (len(category_agents) + agents_per_row - 1) // agents_per_row
            
            for i, agent in enumerate(category_agents):
                row = i // agents_per_row
                col = i % agents_per_row
                
                x = x_offset + col * 2
                y = y_offset - row * 0.8
                
                pos[agent] = (x, y)
            
            x_offset += category_width
        
        y_offset -= level_height
    
    return pos

def calculate_dependency_level(G, agent, all_agents):
    """Calculate the dependency level of an agent (0 = no dependencies)"""
    if not G.has_node(agent):
        return 0
    
    predecessors = list(G.predecessors(agent))
    if not predecessors:
        return 0
    
    max_pred_level = 0
    for pred in predecessors:
        if pred in all_agents:  # Avoid infinite recursion
            pred_level = calculate_dependency_level(G, pred, all_agents - {agent})
            max_pred_level = max(max_pred_level, pred_level)
    
    return max_pred_level + 1

def draw_comprehensive_graph():
    """Draw the complete system dependency graph"""
    G = create_dependency_graph()
    
    # Create figure with subplots
    fig = plt.figure(figsize=(24, 16))
    fig.suptitle("AI System Agent Dependency Graph\n77 Agents Across MainPC and PC2", 
                fontsize=20, fontweight='bold')
    
    # Main graph
    ax1 = plt.subplot(1, 1, 1)
    
    all_agents = set(G.nodes())
    pos = create_hierarchical_layout(G, all_agents)
    
    # Draw nodes by category
    for category, color in COLORS.items():
        category_nodes = [n for n in G.nodes() if G.nodes[n].get('category') == category]
        if category_nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=category_nodes, 
                                 node_color=color, node_size=800, 
                                 alpha=0.8, ax=ax1)
    
    # Draw edges with different styles for cross-machine connections
    mainpc_edges = [(u, v) for u, v in G.edges() if u.startswith('MainPC') and v.startswith('MainPC')]
    pc2_edges = [(u, v) for u, v in G.edges() if u.startswith('PC2') and v.startswith('PC2')]
    cross_edges = [(u, v) for u, v in G.edges() if 
                   (u.startswith('MainPC') and v.startswith('PC2')) or 
                   (u.startswith('PC2') and v.startswith('MainPC'))]
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, edgelist=mainpc_edges, edge_color='blue', 
                          alpha=0.6, arrows=True, arrowsize=20, ax=ax1)
    nx.draw_networkx_edges(G, pos, edgelist=pc2_edges, edge_color='green', 
                          alpha=0.6, arrows=True, arrowsize=20, ax=ax1)
    nx.draw_networkx_edges(G, pos, edgelist=cross_edges, edge_color='red', 
                          alpha=0.8, arrows=True, arrowsize=25, width=2, ax=ax1)
    
    # Draw labels
    labels = {}
    for node in G.nodes():
        machine, agent = node.split('_', 1)
        if agent.startswith('PC2_'):
            agent = agent[4:]  # Remove PC2_ prefix for cleaner labels
        labels[node] = agent.replace('Agent', '').replace('Service', '')[:12]
    
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold', ax=ax1)
    
    # Create legend
    legend_elements = []
    for category, color in COLORS.items():
        legend_elements.append(mpatches.Patch(color=color, label=category.title()))
    
    # Add machine and edge type legends
    legend_elements.extend([
        mpatches.Patch(color='white', label=''),  # Spacer
        plt.Line2D([0], [0], color='blue', lw=2, label='MainPC Dependencies'),
        plt.Line2D([0], [0], color='green', lw=2, label='PC2 Dependencies'),
        plt.Line2D([0], [0], color='red', lw=3, label='Cross-Machine Links'),
    ])
    
    ax1.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1))
    ax1.set_title("Complete Agent Dependency Network", fontsize=14, fontweight='bold')
    ax1.axis('off')
    
    plt.tight_layout()
    return fig, G

def generate_statistics(G):
    """Generate dependency statistics"""
    stats = {
        "total_agents": len(G.nodes()),
        "total_dependencies": len(G.edges()),
        "mainpc_agents": len([n for n in G.nodes() if n.startswith('MainPC')]),
        "pc2_agents": len([n for n in G.nodes() if n.startswith('PC2')]),
        "cross_machine_links": len([(u, v) for u, v in G.edges() if 
                                   (u.startswith('MainPC') and v.startswith('PC2')) or 
                                   (u.startswith('PC2') and v.startswith('MainPC'))]),
        "most_depended_upon": [],
        "category_distribution": {}
    }
    
    # Find most depended upon agents
    in_degrees = dict(G.in_degree())
    sorted_by_deps = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)
    stats["most_depended_upon"] = sorted_by_deps[:10]
    
    # Category distribution
    for node in G.nodes():
        category = G.nodes[node].get('category', 'unknown')
        stats["category_distribution"][category] = stats["category_distribution"].get(category, 0) + 1
    
    return stats

def create_module_dependency_graph():
    """Create a high-level module dependency graph"""
    module_graph = nx.DiGraph()
    
    # Define key modules and their relationships
    modules = {
        "common.core.base_agent": {"deps": [], "type": "core"},
        "common.pools.zmq_pool": {"deps": [], "type": "communication"},
        "common.config_manager": {"deps": [], "type": "configuration"},
        "common.utils.path_manager": {"deps": [], "type": "utility"},
        "common.env_helpers": {"deps": [], "type": "environment"},
        "common.error_bus.unified_error_handler": {"deps": ["common.core.base_agent"], "type": "error_handling"},
        "main_pc_code.utils.service_discovery_client": {"deps": ["common.config_manager"], "type": "service_discovery"},
        "main_pc_code.utils.network_utils": {"deps": ["common.env_helpers"], "type": "networking"},
        "pc2_code.utils.config_loader": {"deps": ["common.config_manager"], "type": "configuration"},
        "pc2_code.utils.pc2_error_publisher": {"deps": ["common.pools.zmq_pool"], "type": "error_handling"},
    }
    
    # Add nodes and edges
    for module, info in modules.items():
        module_graph.add_node(module, module_type=info["type"])
        for dep in info["deps"]:
            module_graph.add_edge(dep, module)
    
    return module_graph

def draw_module_graph():
    """Draw the module dependency graph"""
    G = create_module_dependency_graph()
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    
    # Use hierarchical layout
    pos = nx.spring_layout(G, k=3, iterations=50)
    
    # Color by module type
    module_colors = {
        "core": "#FF6B6B",
        "communication": "#4ECDC4",
        "configuration": "#45B7D1",
        "utility": "#96CEB4",
        "environment": "#FFEAA7",
        "error_handling": "#DDA0DD",
        "service_discovery": "#98D8C8",
        "networking": "#F7DC6F",
    }
    
    for module_type, color in module_colors.items():
        nodes = [n for n in G.nodes() if G.nodes[n].get('module_type') == module_type]
        if nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=nodes, node_color=color, 
                                 node_size=2000, alpha=0.8, ax=ax)
    
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, ax=ax)
    
    # Draw labels with line breaks for long module names
    labels = {}
    for node in G.nodes():
        parts = node.split('.')
        if len(parts) > 3:
            labels[node] = f"{parts[0]}.{parts[1]}.\n{'.'.join(parts[2:])}"
        else:
            labels[node] = node
    
    nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight='bold', ax=ax)
    
    # Create legend
    legend_elements = [mpatches.Patch(color=color, label=mtype.replace('_', ' ').title()) 
                      for mtype, color in module_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right')
    
    ax.set_title("Core Module Dependencies\nShared Infrastructure Components", 
                fontsize=16, fontweight='bold')
    ax.axis('off')
    
    plt.tight_layout()
    return fig

def main():
    """Generate all dependency graphs and statistics"""
    print("Generating AI System Dependency Analysis...")
    
    # Create output directory
    os.makedirs("dependency_analysis", exist_ok=True)
    
    # Generate main dependency graph
    fig1, G = draw_comprehensive_graph()
    fig1.savefig("dependency_analysis/agent_dependency_graph.png", dpi=300, bbox_inches='tight')
    print("✅ Agent dependency graph saved to dependency_analysis/agent_dependency_graph.png")
    
    # Generate module dependency graph
    fig2 = draw_module_graph()
    fig2.savefig("dependency_analysis/module_dependency_graph.png", dpi=300, bbox_inches='tight')
    print("✅ Module dependency graph saved to dependency_analysis/module_dependency_graph.png")
    
    # Generate statistics
    stats = generate_statistics(G)
    
    # Save statistics to JSON
    with open("dependency_analysis/dependency_statistics.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("✅ Statistics saved to dependency_analysis/dependency_statistics.json")
    
    # Print key statistics
    print("\n📊 Key Statistics:")
    print(f"Total Agents: {stats['total_agents']}")
    print(f"MainPC Agents: {stats['mainpc_agents']}")
    print(f"PC2 Agents: {stats['pc2_agents']}")
    print(f"Total Dependencies: {stats['total_dependencies']}")
    print(f"Cross-Machine Links: {stats['cross_machine_links']}")
    
    print("\n🔗 Most Depended Upon Agents:")
    for agent, count in stats['most_depended_upon'][:5]:
        clean_name = agent.replace('MainPC_', '').replace('PC2_', '')
        print(f"  {clean_name}: {count} dependencies")
    
    print("\n📂 Category Distribution:")
    for category, count in sorted(stats['category_distribution'].items()):
        print(f"  {category.title()}: {count} agents")
    
    print(f"\n✅ Analysis complete! Check the dependency_analysis/ folder for visual graphs.")
    
    return G, stats

if __name__ == "__main__":
    G, stats = main()