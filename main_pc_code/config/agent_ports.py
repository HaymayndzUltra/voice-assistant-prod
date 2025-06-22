"""
Agent Port Configuration
Defines default ports for all agents in the system
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class AgentPorts:
    """Default ports for all agents"""
    # Core agents
    meta_cognition_port: int = 5001
    chain_of_thought_port: int = 5003
    voting_port: int = 5004
    knowledge_base_port: int = 5005
    coordinator_port: int = 5006
    
    # Learning agents
    active_learning_port: int = 5007
    orchestrator_port: int = 5008
    
    # Planning agents
    planning_agent_port: int = 5009
    model_manager_port: int = 5010
    autogen_framework_port: int = 5011
    
    # Health check ports (main_port + 1)
    @property
    def health_check_ports(self) -> Dict[str, int]:
        """Get health check ports for all agents"""
        return {
            'meta_cognition': self.meta_cognition_port + 1,
            'chain_of_thought': self.chain_of_thought_port + 1,
            'voting': self.voting_port + 1,
            'knowledge_base': self.knowledge_base_port + 1,
            'coordinator': self.coordinator_port + 1,
            'active_learning': self.active_learning_port + 1,
            'orchestrator': self.orchestrator_port + 1,
            'planning_agent': self.planning_agent_port + 1,
            'model_manager': self.model_manager_port + 1,
            'autogen_framework': self.autogen_framework_port + 1
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert port configuration to dictionary"""
        return {
            'meta_cognition_port': self.meta_cognition_port,
            'chain_of_thought_port': self.chain_of_thought_port,
            'voting_port': self.voting_port,
            'knowledge_base_port': self.knowledge_base_port,
            'coordinator_port': self.coordinator_port,
            'active_learning_port': self.active_learning_port,
            'orchestrator_port': self.orchestrator_port,
            'planning_agent_port': self.planning_agent_port,
            'model_manager_port': self.model_manager_port,
            'autogen_framework_port': self.autogen_framework_port,
            'health_check_ports': self.health_check_ports
        }

# Create default port configuration
default_ports = AgentPorts() 