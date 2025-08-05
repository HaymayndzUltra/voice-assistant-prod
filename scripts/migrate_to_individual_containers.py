#!/usr/bin/env python3
"""
Main Migration Script for Agent Containerization

This script orchestrates the migration of all agents from monolithic Docker Compose
services into individual, containerized agent services.

Usage:
    python migrate_to_individual_containers.py [--agents AGENT1,AGENT2,...] [--dry-run]
    
Example:
    python migrate_to_individual_containers.py --agents service_registry,system_digital_twin --dry-run
"""

import json
import os
import shutil
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging


class AgentMigrator:
    """Handles the migration of agents to individual containers."""
    
    def __init__(self, workspace_root: str = "/workspace", dry_run: bool = False):
        self.workspace_root = Path(workspace_root)
        self.dry_run = dry_run
        self.migration_data_file = self.workspace_root / "migration_data.json"
        self.pc2_migration_data_file = self.workspace_root / "pc2_migration_data.json"
        self.dockerfile_template = self.workspace_root / "templates" / "Dockerfile.template"
        self.pc2_dockerfile_template = self.workspace_root / "templates" / "pc2" / "Dockerfile.template"
        self.scripts_dir = self.workspace_root / "scripts"
        self.docker_dir = self.workspace_root / "docker"
        self.individual_compose_file = self.workspace_root / "docker-compose.individual.yml"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.workspace_root / 'migration.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        if dry_run:
            self.logger.info("Running in DRY-RUN mode - no files will be created or modified")
    
    def load_migration_data(self) -> Dict[str, Any]:
        """Load the migration data from Phase 1."""
        try:
            with open(self.migration_data_file, 'r') as f:
                data = json.load(f)
            self.logger.info(f"Loaded migration data for {len(data['agents'])} agents")
            return data
        except FileNotFoundError:
            self.logger.error(f"Migration data file not found: {self.migration_data_file}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in migration data file: {e}")
            raise
    
    def load_pc2_migration_data(self) -> Dict[str, Any]:
        """Load the PC-2 migration data from Phase 1."""
        try:
            with open(self.pc2_migration_data_file, 'r') as f:
                data = json.load(f)
            self.logger.info(f"Loaded PC-2 migration data for {len(data['agents'])} agents")
            return data
        except FileNotFoundError:
            self.logger.error(f"PC-2 migration data file not found: {self.pc2_migration_data_file}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in PC-2 migration data file: {e}")
            raise
    
    def validate_prerequisites(self) -> bool:
        """Validate that all required files and directories exist."""
        missing_items = []
        
        if not self.migration_data_file.exists():
            missing_items.append(str(self.migration_data_file))
        
        if not self.dockerfile_template.exists():
            missing_items.append(str(self.dockerfile_template))
        
        requirements_script = self.scripts_dir / "extract_individual_requirements.py"
        if not requirements_script.exists():
            missing_items.append(str(requirements_script))
        
        if missing_items:
            self.logger.error("Missing required files:")
            for item in missing_items:
                self.logger.error(f"  - {item}")
            return False
        
        self.logger.info("All prerequisites validated successfully")
        return True
    
    def is_pc2_agent(self, agent_name: str) -> bool:
        """Determine if an agent is a PC-2 agent."""
        try:
            pc2_data = self.load_pc2_migration_data()
            return agent_name in pc2_data['agents']
        except (FileNotFoundError, KeyError):
            return False
    
    def create_agent_directory(self, agent_name: str, is_pc2: bool = False) -> Path:
        """Create the individual directory structure for an agent."""
        if is_pc2:
            agent_dir = self.docker_dir / f"pc2_{agent_name}"
        else:
            agent_dir = self.docker_dir / agent_name
        
        if self.dry_run:
            self.logger.info(f"DRY-RUN: Would create directory {agent_dir}")
            return agent_dir
        
        agent_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Created directory: {agent_dir}")
        return agent_dir
    
    def extract_requirements(self, agent_name: str, agent_dir: Path) -> bool:
        """Extract requirements for a specific agent."""
        requirements_script = self.scripts_dir / "extract_individual_requirements.py"
        requirements_file = agent_dir / "requirements.txt"
        
        if self.dry_run:
            self.logger.info(f"DRY-RUN: Would extract requirements for {agent_name} to {requirements_file}")
            return True
        
        try:
            # Run the requirements extraction script
            cmd = [
                sys.executable,
                str(requirements_script),
                agent_name,
                "--output", str(requirements_file),
                "--workspace", str(self.workspace_root)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.info(f"Successfully extracted requirements for {agent_name}")
                return True
            else:
                self.logger.error(f"Failed to extract requirements for {agent_name}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during requirements extraction for {agent_name}: {e}")
            return False
    
    def create_dockerfile(self, agent_name: str, agent_dir: Path, agent_data: Dict[str, Any], is_pc2: bool = False) -> bool:
        """Create Dockerfile for an agent using the template."""
        dockerfile_path = agent_dir / "Dockerfile"
        
        try:
            # Choose the appropriate template
            template_file = self.pc2_dockerfile_template if is_pc2 else self.dockerfile_template
            
            # Read the template
            with open(template_file, 'r') as f:
                template_content = f.read()
            
            # Replace placeholders
            dockerfile_content = template_content.replace("AGENT_NAME", agent_name)
            
            # Extract health port from agent data for HEALTH_PORT placeholder
            health_port = self.extract_health_port(agent_data)
            if health_port:
                dockerfile_content = dockerfile_content.replace("${HEALTH_PORT}", str(health_port))
            else:
                # Default health check if no specific port found
                dockerfile_content = dockerfile_content.replace(
                    "CMD curl -f http://localhost:${HEALTH_PORT}/health || exit 1",
                    "CMD python -c \"print('OK')\" || exit 1"
                )
            
            if self.dry_run:
                self.logger.info(f"DRY-RUN: Would create Dockerfile for {agent_name}")
                self.logger.debug(f"Dockerfile content preview:\n{dockerfile_content[:200]}...")
                return True
            
            # Write the Dockerfile
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            self.logger.info(f"Created Dockerfile: {dockerfile_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Dockerfile for {agent_name}: {e}")
            return False
    
    def extract_health_port(self, agent_data: Dict[str, Any]) -> Optional[int]:
        """Extract health check port from agent data."""
        # Look for health-related environment variables
        env = agent_data.get('environment', {})
        
        health_port_vars = ['HEALTH_PORT', 'HEALTH_CHECK_PORT']
        for var in health_port_vars:
            if var in env:
                try:
                    return int(env[var])
                except (ValueError, TypeError):
                    pass
        
        # Look for health check port in ports list
        ports = agent_data.get('ports', [])
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ':' in port_mapping:
                host_port, container_port = port_mapping.split(':')
                # Common pattern: health port is often service port + 1000
                try:
                    container_port_int = int(container_port)
                    # Check if this looks like a health port (common patterns)
                    if container_port_int > 6000 or 'health' in str(port_mapping).lower():
                        return container_port_int
                except (ValueError, TypeError):
                    pass
        
        return None
    
    def adjust_pc2_ports(self, ports: List[str]) -> List[str]:
        """Adjust ports to ensure they fall within the PC-2 range (8000-9000)."""
        adjusted_ports = []
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ':' in port_mapping:
                host_port, container_port = port_mapping.split(':')
                try:
                    host_port_int = int(host_port)
                    # If host port is not in PC-2 range, adjust it
                    if not (8000 <= host_port_int <= 9000):
                        # Map to PC-2 range while trying to preserve the pattern
                        new_host_port = 8000 + (host_port_int % 1000)
                        adjusted_ports.append(f"{new_host_port}:{container_port}")
                    else:
                        adjusted_ports.append(port_mapping)
                except (ValueError, TypeError):
                    # Keep original if we can't parse
                    adjusted_ports.append(port_mapping)
            else:
                adjusted_ports.append(port_mapping)
        return adjusted_ports
    
    def create_docker_compose(self, agent_name: str, agent_dir: Path, agent_data: Dict[str, Any], is_pc2: bool = False) -> bool:
        """Create docker-compose.yml for an agent."""
        compose_path = agent_dir / "docker-compose.yml"
        
        try:
            # Determine service name and directory prefix
            service_name = f"pc2_{agent_name}" if is_pc2 else agent_name
            docker_dir_name = f"pc2_{agent_name}" if is_pc2 else agent_name
            
            # Build the service configuration
            service_config = {
                'version': '3.8',
                'services': {
                    service_name: {
                        'build': {
                            'context': '../..',
                            'dockerfile': f'docker/{docker_dir_name}/Dockerfile'
                        },
                        'image': f'{service_name}:latest',
                        'container_name': service_name,
                        'command': agent_data.get('command', []),
                        'restart': 'unless-stopped'
                    }
                }
            }
            
            # Add ports if specified (adjust for PC-2 range if needed)
            ports = agent_data.get('ports', [])
            if ports:
                if is_pc2:
                    # Ensure PC-2 ports are in the 8000-9000 range
                    adjusted_ports = self.adjust_pc2_ports(ports)
                    service_config['services'][service_name]['ports'] = adjusted_ports
                else:
                    service_config['services'][service_name]['ports'] = ports
            
            # Add environment variables
            environment = agent_data.get('environment', {}).copy()
            if is_pc2:
                # Inject PC2_ENVIRONMENT variable for PC-2 agents
                environment['PC2_ENVIRONMENT'] = 'true'
            
            if environment:
                service_config['services'][service_name]['environment'] = environment
            
            # Add dependencies (simplified for individual containers)
            depends_on = agent_data.get('depends_on', [])
            if depends_on:
                # Filter dependencies to only include essential infrastructure
                essential_deps = []
                for dep in depends_on:
                    if any(keyword in dep.lower() for keyword in ['redis', 'nats', 'postgres', 'mongo']):
                        essential_deps.append(dep)
                
                if essential_deps:
                    service_config['services'][service_name]['depends_on'] = essential_deps
            
            # Add health check if agent has health port
            health_port = self.extract_health_port(agent_data)
            if health_port:
                service_config['services'][service_name]['healthcheck'] = {
                    'test': [f'CMD', 'curl', '-f', f'http://localhost:{health_port}/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3,
                    'start_period': '40s'
                }
            
            # Add networks
            service_config['services'][service_name]['networks'] = [f'{service_name}_net']
            service_config['networks'] = {
                f'{service_name}_net': {
                    'driver': 'bridge'
                }
            }
            
            if self.dry_run:
                self.logger.info(f"DRY-RUN: Would create docker-compose.yml for {agent_name}")
                return True
            
            # Write the docker-compose.yml
            import yaml
            with open(compose_path, 'w') as f:
                yaml.dump(service_config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Created docker-compose.yml: {compose_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create docker-compose.yml for {agent_name}: {e}")
            return False
    
    def migrate_agent(self, agent_name: str, agent_data: Dict[str, Any], is_pc2: bool = False) -> bool:
        """Migrate a single agent to individual container structure."""
        agent_type = "PC-2" if is_pc2 else "Main-PC"
        self.logger.info(f"Starting migration for {agent_type} agent: {agent_name}")
        
        try:
            # Create agent directory
            agent_dir = self.create_agent_directory(agent_name, is_pc2)
            
            # Extract requirements
            if not self.extract_requirements(agent_name, agent_dir):
                self.logger.warning(f"Requirements extraction failed for {agent_name}, continuing...")
            
            # Create Dockerfile
            if not self.create_dockerfile(agent_name, agent_dir, agent_data, is_pc2):
                return False
            
            # Create docker-compose.yml
            if not self.create_docker_compose(agent_name, agent_dir, agent_data, is_pc2):
                return False
            
            self.logger.info(f"Successfully migrated {agent_type} agent: {agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate agent {agent_name}: {e}")
            return False
    
    def migrate_agents(self, agent_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """Migrate all specified agents or all agents if none specified."""
        # Load both Main-PC and PC-2 migration data
        main_migration_data = self.load_migration_data()
        main_agents = main_migration_data['agents']
        
        try:
            pc2_migration_data = self.load_pc2_migration_data()
            pc2_agents = pc2_migration_data['agents']
        except (FileNotFoundError, KeyError):
            self.logger.warning("PC-2 migration data not found, skipping PC-2 agents")
            pc2_agents = {}
        
        # Combine agents for selection
        all_agents = {**main_agents, **pc2_agents}
        
        # Determine which agents to migrate
        if agent_names:
            agents_to_migrate = {name: all_agents[name] for name in agent_names if name in all_agents}
            missing_agents = [name for name in agent_names if name not in all_agents]
            if missing_agents:
                self.logger.warning(f"Agents not found in migration data: {missing_agents}")
        else:
            agents_to_migrate = all_agents
        
        self.logger.info(f"Migrating {len(agents_to_migrate)} agents ({len([n for n in agents_to_migrate if n in main_agents])} Main-PC, {len([n for n in agents_to_migrate if n in pc2_agents])} PC-2)")
        
        results = {}
        successful = 0
        failed = 0
        
        for agent_name, agent_data in agents_to_migrate.items():
            is_pc2 = agent_name in pc2_agents
            success = self.migrate_agent(agent_name, agent_data, is_pc2)
            results[agent_name] = success
            
            if success:
                successful += 1
            else:
                failed += 1
        
        # Create master docker-compose.individual.yml
        if not self.dry_run and successful > 0:
            self.create_master_compose_file()
        
        self.logger.info(f"Migration complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            self.logger.error("Failed agents:")
            for agent_name, success in results.items():
                if not success:
                    self.logger.error(f"  - {agent_name}")
        
        return results
    
    def create_master_compose_file(self) -> bool:
        """Create the master docker-compose.individual.yml file with Main-PC and PC-2 sections."""
        try:
            # Load migration data
            main_data = self.load_migration_data()
            main_agents = main_data['agents']
            
            try:
                pc2_data = self.load_pc2_migration_data()
                pc2_agents = pc2_data['agents']
            except (FileNotFoundError, KeyError):
                pc2_agents = {}
            
            # Start building the master compose file
            master_config = {
                'version': '3.8',
                'services': {},
                'networks': {}
            }
            
            # Add infrastructure services first
            master_config['services']['redis'] = {
                'image': 'redis:7.2-alpine',
                'container_name': 'redis',
                'ports': ['6379:6379'],
                'restart': 'unless-stopped',
                'networks': ['shared_network']
            }
            
            master_config['services']['nats'] = {
                'image': 'nats:2.10-alpine',
                'container_name': 'nats',
                'ports': ['4222:4222', '8222:8222'],
                'restart': 'unless-stopped',
                'networks': ['shared_network']
            }
            
            # Add Main-PC agents
            for agent_name, agent_data in main_agents.items():
                service_config = {
                    'build': {
                        'context': '.',
                        'dockerfile': f'docker/{agent_name}/Dockerfile'
                    },
                    'image': f'{agent_name}:latest',
                    'container_name': agent_name,
                    'command': agent_data.get('command', []),
                    'restart': 'unless-stopped',
                    'networks': ['shared_network']
                }
                
                # Add ports, environment, etc.
                if agent_data.get('ports'):
                    service_config['ports'] = agent_data['ports']
                if agent_data.get('environment'):
                    service_config['environment'] = agent_data['environment']
                
                master_config['services'][agent_name] = service_config
            
            # Add PC-2 agents section
            if pc2_agents:
                # Add comment marker for PC-2 section (will be added as a dummy service comment)
                for agent_name, agent_data in pc2_agents.items():
                    service_name = f'pc2_{agent_name}'
                    service_config = {
                        'build': {
                            'context': '.',
                            'dockerfile': f'docker/pc2_{agent_name}/Dockerfile'
                        },
                        'image': f'{service_name}:latest',
                        'container_name': service_name,
                        'command': agent_data.get('command', []),
                        'restart': 'unless-stopped',
                        'networks': ['shared_network']
                    }
                    
                    # Add ports (adjusted for PC-2 range), environment with PC2_ENVIRONMENT, etc.
                    if agent_data.get('ports'):
                        service_config['ports'] = self.adjust_pc2_ports(agent_data['ports'])
                    
                    environment = agent_data.get('environment', {}).copy()
                    environment['PC2_ENVIRONMENT'] = 'true'
                    service_config['environment'] = environment
                    
                    master_config['services'][service_name] = service_config
            
            # Add shared network
            master_config['networks']['shared_network'] = {
                'driver': 'bridge'
            }
            
            # Write the master compose file
            import yaml
            with open(self.individual_compose_file, 'w') as f:
                # Write header comment
                f.write("# Individual Agent Services\n")
                f.write("# This file contains both Main-PC and PC-2 individual agents\n\n")
                
                # Split into sections with comments
                main_services = {k: v for k, v in master_config['services'].items() if not k.startswith('pc2_') and k not in ['redis', 'nats']}
                pc2_services = {k: v for k, v in master_config['services'].items() if k.startswith('pc2_')}
                infra_services = {k: v for k, v in master_config['services'].items() if k in ['redis', 'nats']}
                
                # Infrastructure first
                infra_config = {
                    'version': '3.8',
                    'services': infra_services
                }
                yaml.dump(infra_config, f, default_flow_style=False, indent=2)
                
                # Main-PC Individual Agents
                if main_services:
                    f.write("\n  # Main-PC Individual Agents\n")
                    for service_name, service_config in main_services.items():
                        f.write(f"  {service_name}:\n")
                        yaml.dump({service_name: service_config}, f, default_flow_style=False, indent=2)
                        f.write("\n")
                
                # PC-2 Individual Agents
                if pc2_services:
                    f.write("  # PC-2 Individual Agents\n")
                    for service_name, service_config in pc2_services.items():
                        f.write(f"  {service_name}:\n")
                        yaml.dump({service_name: service_config}, f, default_flow_style=False, indent=2)
                        f.write("\n")
                
                # Networks
                f.write("networks:\n")
                yaml.dump(master_config['networks'], f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Created master compose file: {self.individual_compose_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create master compose file: {e}")
            return False
    
    def test_migration_script(self) -> bool:
        """Test the migration script functionality with a small subset."""
        self.logger.info("Running migration script tests...")
        
        # Test with a simple agent
        test_agents = ['service_registry', 'system_digital_twin']
        available_agents = []
        
        migration_data = self.load_migration_data()
        for agent in test_agents:
            if agent in migration_data['agents']:
                available_agents.append(agent)
        
        if not available_agents:
            self.logger.error("No test agents available for testing")
            return False
        
        # Run test with dry-run mode
        original_dry_run = self.dry_run
        self.dry_run = True
        
        try:
            results = self.migrate_agents(available_agents[:1])  # Test with one agent
            success = all(results.values())
            
            self.logger.info(f"Test migration {'PASSED' if success else 'FAILED'}")
            return success
            
        finally:
            self.dry_run = original_dry_run


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Migrate agents to individual containers")
    parser.add_argument("--agents", help="Comma-separated list of specific agents to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--test", action="store_true", help="Run functionality tests")
    parser.add_argument("--workspace", default="/workspace", help="Workspace root directory")
    
    args = parser.parse_args()
    
    migrator = AgentMigrator(args.workspace, args.dry_run)
    
    # Validate prerequisites
    if not migrator.validate_prerequisites():
        sys.exit(1)
    
    # Run tests if requested
    if args.test:
        if migrator.test_migration_script():
            print("All tests passed!")
            sys.exit(0)
        else:
            print("Tests failed!")
            sys.exit(1)
    
    # Parse agent list
    agent_list = None
    if args.agents:
        agent_list = [agent.strip() for agent in args.agents.split(',')]
    
    # Run migration
    try:
        results = migrator.migrate_agents(agent_list)
        
        successful_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"\nMigration Summary:")
        print(f"  Total agents: {total_count}")
        print(f"  Successful: {successful_count}")
        print(f"  Failed: {total_count - successful_count}")
        
        if successful_count == total_count:
            print("Migration completed successfully!")
            sys.exit(0)
        else:
            print("Migration completed with errors!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()