import yaml
import os

SOT_PATH = 'config/startup_config.yaml'
COMPOSE_PATH = 'docker-compose.yml'

# Sections in SOT that contain agents
AGENT_SECTIONS = [
    'core_services', 'main_pc_gpu_services', 'emotion_system', 'language_processing',
    'memory_system', 'learning_knowledge', 'planning_execution', 'tts_services',
    'code_generation', 'audio_processing', 'vision', 'monitoring_security'
]

with open(SOT_PATH, 'r') as f:
    sot = yaml.safe_load(f)

services = {}
for section in AGENT_SECTIONS:
    agents = sot.get(section, [])
    for agent in agents:
        name = agent['name'].lower()
        script = agent['script_path']
        port = agent.get('port')
        service = {
            'build': '.',
            'container_name': f'main_pc_{name}',
            'command': ["python", script],
            'volumes': [
                './config:/app/config',
                './logs:/app/logs',
                '${MODELS_BASE_PATH}:/app/models'
            ],
            'env_file': ['.env'],
            'networks': ['ai_system_network'],
            'restart': 'unless-stopped',
        }
        if port:
            service['ports'] = [f"{port}:{port}"]
        services[name] = service

compose = {
    'version': '3.8',
    'services': services,
    'networks': {
        'ai_system_network': {
            'driver': 'bridge'
        }
    }
}

with open(COMPOSE_PATH, 'w') as f:
    yaml.dump(compose, f, sort_keys=False)

print(f"Generated {COMPOSE_PATH} with {len(services)} services.") 