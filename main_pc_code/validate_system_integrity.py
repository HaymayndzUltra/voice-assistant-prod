import yaml
import os
from pathlib import Path
from collections import defaultdict


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
SOT_CONFIG_PATH = Path(join_path("config", "source_of_truth_config.yaml"))
PROJECT_ROOT = Path(__file__).parent

class SystemValidator:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = self._load_config()
        self.all_agents = {}
        self.dependency_graph = defaultdict(list)
        self.errors = []
        self.warnings = []

    def _load_config(self):
        """Loads the source of truth YAML configuration file."""
        if not self.config_path.exists():
            self.errors.append(f"Configuration file not found: {self.config_path}")
            return None
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _collect_all_agents(self):
        """Collect all agent definitions from all sections."""
        if not self.config:
            return

        for section, agents in self.config.items():
            if isinstance(agents, list) and section != 'network':
                for agent_data in agents:
                    if isinstance(agent_data, dict) and 'name' in agent_data:
                        agent_name = agent_data['name']
                        if agent_name in self.all_agents:
                            self.warnings.append(f"Duplicate agent name '{agent_name}' found in section '{section}'.")
                        self.all_agents[agent_name] = agent_data

    def validate_paths(self):
        """Checks if the script_path for each agent exists."""
        print("\n--- Validating Agent Script Paths ---")
        for name, data in self.all_agents.items():
            script_path_str = data.get('script_path')
            if not script_path_str:
                self.errors.append(f"Agent '{name}' is missing 'script_path'.")
                continue
            
            script_path = PROJECT_ROOT / script_path_str
            if not script_path.exists():
                self.errors.append(f"[FAIL] Agent '{name}': Script not found at '{script_path_str}'")
            else:
                print(f"[OK] Agent '{name}': Found at '{script_path_str}'")

    def build_dependency_graph(self):
        """Builds a graph of dependencies between agents."""
        for name, data in self.all_agents.items():
            dependencies = data.get('dependencies', [])
            if dependencies:
                for dep in dependencies:
                    self.dependency_graph[name].append(dep)
                    if dep not in self.all_agents:
                        self.errors.append(f"Agent '{name}' has an undefined dependency: '{dep}'")

    def check_for_circular_dependencies(self):
        """Detects circular dependencies in the graph using DFS."""
        print("\n--- Checking for Circular Dependencies ---")
        path = set()  # Nodes currently in the recursion stack
        visited = set()  # All nodes ever visited

        for node in self.dependency_graph:
            if node not in visited:
                if self._is_cyclic_util(node, visited, path):
                    # The cycle details are printed within the recursive function
                    pass
        print("Circular dependency check complete.")

    def _is_cyclic_util(self, node, visited, path):
        visited.add(node)
        path.add(node)

        for neighbour in self.dependency_graph.get(node, []):
            if neighbour not in visited:
                if self._is_cyclic_util(neighbour, visited, path):
                    return True
            elif neighbour in path:
                self.errors.append(f"Circular dependency detected: {path} -> {neighbour}")
                return True
        
        path.remove(node) # Backtrack
        return False

    def run_validation(self):
        """Runs all validation checks."""
        if not self.config:
            self.display_report()
            return

        self._collect_all_agents()
        self.validate_paths()
        self.build_dependency_graph()
        self.check_for_circular_dependencies()
        self.display_report()

    def display_report(self):
        """Prints a summary report of all errors and warnings."""
        print("\n=========================================")
        print("      System Integrity Report")
        print("=========================================")
        if not self.errors and not self.warnings:
            print("\n\033[92mAll checks passed. System integrity is good!\033[0m")
        else:
            if self.errors:
                print(f"\n\033[91mFound {len(self.errors)} Error(s):\033[0m")
                for i, error in enumerate(self.errors, 1):
                    print(f"  {i}. {error}")
            if self.warnings:
                print(f"\n\033[93mFound {len(self.warnings)} Warning(s):\033[0m")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")
        print("\nReport finished.")

if __name__ == "__main__":
    validator = SystemValidator(SOT_CONFIG_PATH)
    validator.run_validation()
