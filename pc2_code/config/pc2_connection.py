"""
PC2 Connection Configuration
---------------------------
Central configuration for all connections to PC2 agents.
This file serves as the single source of truth for PC2 IP and port information.
"""

import os
import logging
from pathlib import Path

# PC2 network configuration
PC2_IP = "192.168.1.2"  # IP address of PC2
PC2_HOSTNAME = "PC2"    # Hostname for logging/display

# Create logger
logger = logging.getLogger("PC2Config")

# Dictionary of all agents running on PC2
PC2_AGENTS = {
    # Model Management & Routing
    "model_manager": {
        "port": 5556,
        "description": "Dynamic model loading/unloading, VRAM optimization"
    },
    "context_bridge": {
        "port": 5595,
        "description": "Bridges user context between agents"
    },
    
    # Code Generation & Execution
    "code_generator": {
        "port": 5604,
        "description": "Multi-model voting code generation"
    },
    "chain_of_thought": {
        "port": 5612,
        "description": "Stepwise reasoning for complex tasks"
    },
    "progressive_code_generator": {
        "port": 5607,
        "description": "Guided, stepwise code generation"
    },
    "auto_fixer": {
        "port": 5605,
        "description": "Auto code correction and debugging"
    },
    "test_generator": {
        "port": 5613,
        "description": "Auto test creation and validation"
    },
    "executor": {
        "port": 5603,
        "description": "Safe code execution environment"
    },
    
    # Language & Information
    "translator": {
        "port": 5559,
        "alt_port": 5573,
        "description": "Filipino-English translation with auto-correction"
    },
    "web_scraper": {
        "port": 5602,
        "description": "Advanced web scraping and content extraction"
    },
    
    # Memory & Context
    "contextual_memory": {
        "port": 5596,
        "description": "Short-term context with memory decay"
    },
    "context_summarizer": {
        "port": 5610,
        "description": "Context summarization for efficient LLM context"
    },
    "error_pattern_memory": {
        "port": 5611,
        "description": "Error/fix database and solution suggestion"
    },
    "jarvis_memory": {
        "port": 5598,
        "description": "User-specific persistent memory"
    },
    "digital_twin": {
        "port": 5597,
        "description": "User modeling and behavior simulation"
    },
    "filesystem_assistant": {
        "port": 5594,
        "description": "File operations and management"
    },
    "learning_mode": {
        "port": 5599,
        "description": "Feedback-driven agent learning"
    }
"autonomous_web_assistant": {
    "port": 5620,
    "description": "Autonomous decision-making web assistant with proactive information retrieval"
},
}

def get_connection_string(agent_name, use_alt_port=False):
    """
    Get ZMQ connection string for a PC2 agent
    
    Args:
        agent_name: Name of the agent in PC2_AGENTS dictionary
        use_alt_port: Use alternative port if available (for agents with multiple ports)
        
    Returns:
        Connection string in format: "tcp://IP:PORT"
        
    Raises:
        ValueError: If agent_name not found in PC2_AGENTS
    """
    if agent_name not in PC2_AGENTS:
        logger.error(f"Unknown PC2 agent: {agent_name}")
        raise ValueError(f"Unknown PC2 agent: {agent_name}")
    
    agent_info = PC2_AGENTS[agent_name]
    
    if use_alt_port and "alt_port" in agent_info:
        port = agent_info["alt_port"]
    else:
        port = agent_info["port"]
    
    return f"tcp://{PC2_IP}:{port}"

def list_pc2_agents():
    """
    Returns a formatted string listing all PC2 agents and their ports
    """
    result = f"PC2 ({PC2_IP}) Agents:\n"
    result += "-" * 50 + "\n"
    
    # Group by category
    categories = {
        "Model Management": ["model_manager", "context_bridge"],
        "Code Generation": ["code_generator", "chain_of_thought", "progressive_code_generator", 
                           "auto_fixer", "test_generator", "executor"],
        "Language": ["translator", "web_scraper"],
        "Memory": ["contextual_memory", "context_summarizer", "error_pattern_memory", 
                  "jarvis_memory", "digital_twin", "filesystem_assistant", "learning_mode"]
    }
    
    for category, agents in categories.items():
        result += f"\n{category}:\n"
        for agent in agents:
            info = PC2_AGENTS[agent]
            port_info = f"{info['port']}"
            if "alt_port" in info:
                port_info += f"/{info['alt_port']}"
            result += f"  - {agent}: {port_info} - {info['description']}\n"
    
    return result

# Example usage
if __name__ == "__main__":
    print(list_pc2_agents())
    print(f"Example connection string: {get_connection_string('translator')}")
