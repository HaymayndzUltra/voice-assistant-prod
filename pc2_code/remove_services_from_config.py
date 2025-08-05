from pathlib import Path

def update_system_config():
    # Read the current system_config.py
    config_path = Path(get_file_path("data", "voice_samples/system_config.py")
    config_content = config_path.read_text()
    
    # List of services to remove
    services_to_remove = [
        "consolidated-translator-pc2",
        "learning_adjuster",
        "cognitive_model",
        "nllb-translation-adapter-pc2",
        "tinyllama-service-pc2",
        "phi-llm-service-pc2"
    ]
    
    # Remove service configurations
    config_lines = config_content.split('\n')
    updated_lines = []
    skip_next = False
    
    for line in config_lines:
        if skip_next:
            skip_next = False
            continue
            
        if any(service in line for service in services_to_remove):
            skip_next = True  # Skip the next line which contains the service config
            continue
            
        updated_lines.append(line)
    
    # Write back the updated content
    updated_content = '\n'.join(updated_lines)
    config_path.write_text(updated_content)
    
    print("Services removed from system_config.py")

if __name__ == "__main__":
    update_system_config()
