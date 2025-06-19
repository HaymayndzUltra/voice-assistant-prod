import os
from pathlib import Path

def update_active_agents():
    # Read the current active_pc2_agents.md
    agents_path = Path("d:\\DISKARTE\\Voice Assistant\\agents\\active_pc2_agents.md")
    agents_content = agents_path.read_text()
    
    # List of services to remove
    services_to_remove = [
        "consolidated_translator.py",
        "LearningAdjusterAgent.py",
        "CognitiveModelAgent.py",
        "TinyLlamaServiceEnhanced.py",
        "chain_of_thought_agent.py",
        "got_tot_agent.py",
        "learning_adjuster_agent.py",
        "local_fine_tuner_agent.py",
        "self_training_orchestrator.py"
    ]
    
    # Remove service entries
    updated_content = []
    
    for line in agents_content.split('\n'):
        if not any(service in line for service in services_to_remove):
            updated_content.append(line)
    
    # Write back the updated content
    updated_content = '\n'.join(updated_content)
    agents_path.write_text(updated_content)
    
    print("Services removed from active_pc2_agents.md")

if __name__ == "__main__":
    update_active_agents()
