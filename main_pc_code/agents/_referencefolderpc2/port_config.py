"""
Centralized port configuration for PC2 agents.
This file serves as the single source of truth for all port numbers.
"""

# Core Service Ports
ENHANCED_MODEL_ROUTER_PORT = 5598  # Primary model routing service
DREAM_WORLD_PORT = 5599  # Dream world updates
TRANSLATOR_PORT = 5563  # Translation services
TUTORING_PORT = 5568  # Tutoring services
MEMORY_PORT = 5596  # Memory operations
REMOTE_CONNECTOR_PORT = 5557  # Remote model connections
WEB_AGENT_PORT = 5604  # Web operations
FILESYSTEM_PORT = 5606  # File operations
HEALTH_CHECK_PORT = 5611  # Health monitoring
CHAIN_OF_THOUGHT_PORT = 5612  # Reasoning operations
TINYLLAMA_PORT = 5615  # TinyLlama service

# Port Registry for Documentation
PORT_REGISTRY = {
    ENHANCED_MODEL_ROUTER_PORT: "EnhancedModelRouter (PC2)",
    DREAM_WORLD_PORT: "DreamWorld Agent (PC2)",
    TRANSLATOR_PORT: "Consolidated Translator (PC2)",
    TUTORING_PORT: "Tutoring Service (PC2)",
    MEMORY_PORT: "Unified Memory Reasoning (PC2)",
    REMOTE_CONNECTOR_PORT: "Remote Connector (PC2)",
    WEB_AGENT_PORT: "Unified Web Agent (PC2)",
    FILESYSTEM_PORT: "Filesystem Assistant (PC2)",
    HEALTH_CHECK_PORT: "Self-Healing Agent (PC2)",
    CHAIN_OF_THOUGHT_PORT: "Chain of Thought (PC2)",
    TINYLLAMA_PORT: "TinyLlama Service (PC2)"
}

def get_port_description(port: int) -> str:
    """Get the description of a port from the registry."""
    return PORT_REGISTRY.get(port, "Unknown Port") 