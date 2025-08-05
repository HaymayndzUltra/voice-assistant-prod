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
        self.dockerfile_template = self.workspace_root / "templates" / "Dockerfile.template"
        self.scripts_dir = self.workspace_root / "scripts"
        self.docker_dir = self.workspace_root / "docker"
        
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
    
    def create_agent_directory(self, agent_name: str) -> Path:
        """Create the individual directory structure for an agent."""
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
    
    def create_dockerfile(self, agent_name: str, agent_dir: Path, agent_data: Dict[str, Any]) -> bool:
        """Create Dockerfile for an agent using the template."""
        dockerfile_path = agent_dir / "Dockerfile"
        
        try:
            # Read the template
            with open(self.dockerfile_template, 'r') as f:
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
    
    def create_docker_compose(self, agent_name: str, agent_dir: Path, agent_data: Dict[str, Any]) -> bool:
        """Create docker-compose.yml for an agent."""
        compose_path = agent_dir / "docker-compose.yml"
        
        try:
            # Build the service configuration
            service_config = {
                'version': '3.8',
                'services': {
                    agent_name: {
                        'build': {
                            'context': '../..',
                            'dockerfile': f'docker/{agent_name}/Dockerfile'
                        },
                        'image': f'{agent_name}:latest',
                        'container_name': agent_name,
                        'command': agent_data.get('command', []),
                        'restart': 'unless-stopped'
                    }
                }
            }
            
            # Add ports if specified
            ports = agent_data.get('ports', [])
            if ports:
                service_config['services'][agent_name]['ports'] = ports
            
            # Add environment variables
            environment = agent_data.get('environment', {})
            if environment:
                service_config['services'][agent_name]['environment'] = environment
            
            # Add dependencies (simplified for individual containers)
            depends_on = agent_data.get('depends_on', [])
            if depends_on:
                # Filter dependencies to only include essential infrastructure
                essential_deps = []
                for dep in depends_on:
                    if any(keyword in dep.lower() for keyword in ['redis', 'nats', 'postgres', 'mongo']):
                        essential_deps.append(dep)
                
                if essential_deps:
                    service_config['services'][agent_name]['depends_on'] = essential_deps
            
            # Add health check if agent has health port
            health_port = self.extract_health_port(agent_data)
            if health_port:
                service_config['services'][agent_name]['healthcheck'] = {
                    'test': [f'CMD', 'curl', '-f', f'http://localhost:{health_port}/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3,
                    'start_period': '40s'
                }
            
            # Add networks
            service_config['services'][agent_name]['networks'] = [f'{agent_name}_net']
            service_config['networks'] = {
                f'{agent_name}_net': {
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
    
    def migrate_agent(self, agent_name: str, agent_data: Dict[str, Any]) -> bool:
        """Migrate a single agent to individual container structure."""
        self.logger.info(f"Starting migration for agent: {agent_name}")
        
        try:
            # Create agent directory
            agent_dir = self.create_agent_directory(agent_name)
            
            # Extract requirements
            if not self.extract_requirements(agent_name, agent_dir):
                self.logger.warning(f"Requirements extraction failed for {agent_name}, continuing...")
            
            # Create Dockerfile
            if not self.create_dockerfile(agent_name, agent_dir, agent_data):
                return False
            
            # Create docker-compose.yml
            if not self.create_docker_compose(agent_name, agent_dir, agent_data):
                return False
            
            self.logger.info(f"Successfully migrated agent: {agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate agent {agent_name}: {e}")
            return False
    
    def migrate_agents(self, agent_names: Optional[List[str]] = None) -> Dict[str, bool]:
        """Migrate all specified agents or all agents if none specified."""
        migration_data = self.load_migration_data()
        agents = migration_data['agents']
        
        # Determine which agents to migrate
        if agent_names:
            agents_to_migrate = {name: agents[name] for name in agent_names if name in agents}
            missing_agents = [name for name in agent_names if name not in agents]
            if missing_agents:
                self.logger.warning(f"Agents not found in migration data: {missing_agents}")
        else:
            agents_to_migrate = agents
        
        self.logger.info(f"Migrating {len(agents_to_migrate)} agents")
        
        results = {}
        successful = 0
        failed = 0
        
        for agent_name, agent_data in agents_to_migrate.items():
            success = self.migrate_agent(agent_name, agent_data)
            results[agent_name] = success
            
            if success:
                successful += 1
            else:
                failed += 1
        
        self.logger.info(f"Migration complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            self.logger.error("Failed agents:")
            for agent_name, success in results.items():
                if not success:
                    self.logger.error(f"  - {agent_name}")
        
        return results
    
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