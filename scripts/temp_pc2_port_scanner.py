import yaml
from collections import defaultdict

CONFIG_PATH = '/home/haymayndz/AI_System_Monorepo/pc2_code/config/startup_config.yaml'

def find_port_conflicts():
    """Scans the PC2 startup config for duplicate port assignments."""
    port_usage = defaultdict(list)
    health_port_usage = defaultdict(list)

    print(f"Scanning configuration file: {CONFIG_PATH}\n")

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            
            # Check if pc2_services exists (the actual key in the YAML)
            if 'pc2_services' not in config:
                print("ERROR: 'pc2_services' key not found in YAML.")
                return

            for agent_config in config['pc2_services']:
                agent_name = agent_config.get('name', 'UnnamedAgent')
                
                if 'port' in agent_config:
                    port = agent_config['port']
                    port_usage[port].append(agent_name)
                
                if 'health_check_port' in agent_config:
                    health_port = agent_config['health_check_port']
                    health_port_usage[health_port].append(agent_name)

        print("--- ZMQ Port Conflicts ---")
        found_conflict = False
        for port, agents in port_usage.items():
            if len(agents) > 1:
                print(f"CONFLICT: Port {port} is used by: {', '.join(agents)}")
                found_conflict = True
        if not found_conflict:
            print("No ZMQ port conflicts found.")

        print("\n--- Health Check Port Conflicts ---")
        found_conflict = False
        for port, agents in health_port_usage.items():
            if len(agents) > 1:
                print(f"CONFLICT: Health Port {port} is used by: {', '.join(agents)}")
                found_conflict = True
        if not found_conflict:
            print("No health check port conflicts found.")

        # Print all port assignments for reference
        print("\n--- All Port Assignments ---")
        for port in sorted(port_usage.keys()):
            agents = port_usage[port]
            print(f"Port {port}: {', '.join(agents)}")

    except FileNotFoundError:
        print(f"ERROR: Configuration file not found at {CONFIG_PATH}")
    except yaml.YAMLError as e:
        print(f"ERROR: Could not parse YAML file: {e}")

if __name__ == "__main__":
    find_port_conflicts() 