#!/usr/bin/env python3
"""
Network Configuration Upgrader

Updates network configuration to support hostname-based service discovery.
Implements Blueprint.md Step 6: Network Fixes.

This script:
1. Updates network_config.yaml to support hostnames
2. Adds Docker service name mappings
3. Provides fallback to IP-based discovery
4. Creates environment-specific hostname mappings

Usage:
    python tools/network_config_upgrader.py --dry-run    # Preview changes
    python tools/network_config_upgrader.py --apply      # Apply changes
"""

import os
import yaml
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List
from copy import deepcopy
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s: %(message)s')
logger = logging.getLogger(__name__)

class NetworkConfigUpgrader:
    """
    Upgrades network configuration for hostname-based service discovery.
    """
    
    def __init__(self, project_root: Path):
        """Initialize upgrader with project root."""
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "config" / "network_config.yaml"
        
    def load_current_config(self) -> Dict[str, Any]:
        """Load the current network configuration."""
        if not self.config_path.exists():
            logger.error(f"Network config not found: {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load network config: {e}")
            return {}
    
    def create_upgraded_config(self, current_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create upgraded configuration with hostname support."""
        upgraded = deepcopy(current_config)
        
        # Add hostname-based configuration section
        if "hostname_discovery" not in upgraded:
            upgraded["hostname_discovery"] = {
                "enabled": True,
                "docker_service_names": {
                    "mainpc": "mainpc-service",
                    "pc2": "pc2-service"
                },
                "kubernetes_namespace": "ai-system",
                "kubernetes_cluster_domain": "cluster.local",
                "fallback_to_ip": True
            }
        
        # Update environment configurations
        for env_name, env_config in upgraded.get("environment", {}).items():
            # Add hostname support to each environment
            if "hostname_discovery" not in env_config:
                env_config["hostname_discovery"] = True
            
            # Add Docker-specific hostnames
            if env_name == "docker":
                env_config.update({
                    "mainpc_hostname": "mainpc-service",
                    "pc2_hostname": "pc2-service",
                    "use_service_names": True
                })
            elif env_name == "kubernetes":
                env_config.update({
                    "mainpc_hostname": "mainpc-service.ai-system.svc.cluster.local",
                    "pc2_hostname": "pc2-service.ai-system.svc.cluster.local",
                    "use_service_names": True
                })
            else:
                # For development/production, keep IP-based but add hostname support
                env_config.update({
                    "mainpc_hostname": env_config.get("mainpc_ip", "localhost"),
                    "pc2_hostname": env_config.get("pc2_ip", "localhost"),
                    "use_service_names": False
                })
        
        # Add docker environment if not present
        if "docker" not in upgraded.get("environment", {}):
            upgraded.setdefault("environment", {})["docker"] = {
                "use_local_mode": False,
                "hostname_discovery": True,
                "mainpc_ip": "mainpc-service",
                "pc2_ip": "pc2-service", 
                "mainpc_hostname": "mainpc-service",
                "pc2_hostname": "pc2-service",
                "use_service_names": True,
                "bind_address": "0.0.0.0",
                "service_discovery_timeout": 10000,
                "secure_zmq": False,
                "metrics_enabled": True
            }
        
        # Add kubernetes environment if not present
        if "kubernetes" not in upgraded.get("environment", {}):
            upgraded.setdefault("environment", {})["kubernetes"] = {
                "use_local_mode": False,
                "hostname_discovery": True,
                "mainpc_ip": "mainpc-service.ai-system.svc.cluster.local",
                "pc2_ip": "pc2-service.ai-system.svc.cluster.local",
                "mainpc_hostname": "mainpc-service.ai-system.svc.cluster.local",
                "pc2_hostname": "pc2-service.ai-system.svc.cluster.local",
                "use_service_names": True,
                "bind_address": "0.0.0.0",
                "service_discovery_timeout": 10000,
                "secure_zmq": True,
                "metrics_enabled": True
            }
        
        # Update machine definitions with hostname support
        for machine_name, machine_config in upgraded.get("machines", {}).items():
            machine_config["hostname"] = machine_config.get("hostname", machine_name.lower())
            
            # Add Docker service name mapping
            if machine_name.lower() == "mainpc":
                machine_config["docker_service_name"] = "mainpc-service"
                machine_config["k8s_service_name"] = "mainpc-service"
            elif machine_name.lower() == "pc2":
                machine_config["docker_service_name"] = "pc2-service"
                machine_config["k8s_service_name"] = "pc2-service"
        
        # Add service discovery resolution order
        upgraded["service_discovery"] = upgraded.get("service_discovery", {})
        upgraded["service_discovery"]["resolution_order"] = [
            "hostname", "docker_service", "kubernetes_service", "ip_fallback"
        ]
        
        # Add service naming conventions
        upgraded["service_naming"] = {
            "docker": {
                "pattern": "{machine}-{service}",
                "examples": {
                    "SystemDigitalTwin": "mainpc-systemdigitaltwin",
                    "ServiceRegistry": "mainpc-serviceregistry",
                    "Translator": "pc2-translator"
                }
            },
            "kubernetes": {
                "pattern": "{service}.{namespace}.svc.{cluster_domain}",
                "examples": {
                    "SystemDigitalTwin": "mainpc-systemdigitaltwin.ai-system.svc.cluster.local",
                    "ServiceRegistry": "mainpc-serviceregistry.ai-system.svc.cluster.local", 
                    "Translator": "pc2-translator.ai-system.svc.cluster.local"
                }
            }
        }
        
        return upgraded
    
    def analyze_changes(self, current_config: Dict[str, Any], upgraded_config: Dict[str, Any]) -> List[str]:
        """Analyze what changes will be made."""
        changes = []
        
        # Check for new top-level sections
        new_sections = set(upgraded_config.keys()) - set(current_config.keys())
        for section in new_sections:
            changes.append(f"Added new section: {section}")
        
        # Check for hostname discovery additions
        if "hostname_discovery" not in current_config:
            changes.append("Added hostname discovery configuration")
        
        # Check for new environments
        current_envs = set(current_config.get("environment", {}).keys())
        new_envs = set(upgraded_config.get("environment", {}).keys())
        for env in new_envs - current_envs:
            changes.append(f"Added new environment: {env}")
        
        # Check for hostname additions to machines
        for machine_name, machine_config in upgraded_config.get("machines", {}).items():
            current_machine = current_config.get("machines", {}).get(machine_name, {})
            if "hostname" not in current_machine:
                changes.append(f"Added hostname to machine: {machine_name}")
            if "docker_service_name" not in current_machine:
                changes.append(f"Added Docker service name to machine: {machine_name}")
        
        return changes
    
    def backup_current_config(self) -> Path:
        """Create a backup of the current configuration."""
        backup_path = self.config_path.with_suffix('.yaml.backup')
        
        try:
            if self.config_path.exists():
                backup_path.write_text(self.config_path.read_text())
                logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def write_upgraded_config(self, upgraded_config: Dict[str, Any]) -> None:
        """Write the upgraded configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                # Add header comment
                f.write("# Network Configuration for AI System\n")
                f.write("# Updated for hostname-based service discovery (Blueprint.md Step 6)\n")
                f.write("# This file defines the network topology and connection parameters\n\n")
                
                yaml.dump(upgraded_config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Updated network configuration: {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to write upgraded config: {e}")
            raise
    
    def run_upgrade(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Run the network configuration upgrade.
        
        Args:
            dry_run: If True, only preview changes without applying them
            
        Returns:
            Dictionary with upgrade results
        """
        logger.info(f"{'🔍 ANALYZING' if dry_run else '🔧 UPGRADING'} network configuration...")
        
        # Load current configuration
        current_config = self.load_current_config()
        if not current_config:
            logger.error("Cannot proceed without valid current configuration")
            return {"success": False, "error": "Invalid current configuration"}
        
        # Create upgraded configuration
        upgraded_config = self.create_upgraded_config(current_config)
        
        # Analyze changes
        changes = self.analyze_changes(current_config, upgraded_config)
        
        if dry_run:
            logger.info(f"\n📊 NETWORK CONFIG UPGRADE PREVIEW:")
            logger.info(f"Configuration file: {self.config_path}")
            logger.info(f"Changes to be made: {len(changes)}")
            
            if changes:
                logger.info(f"\n📋 Changes:")
                for change in changes:
                    logger.info(f"  • {change}")
            else:
                logger.info("No changes needed - configuration is already up to date")
            
            return {
                "success": True,
                "dry_run": True,
                "changes": changes,
                "config_preview": upgraded_config
            }
        else:
            # Apply changes
            if changes:
                # Create backup
                backup_path = self.backup_current_config()
                
                # Write upgraded config
                self.write_upgraded_config(upgraded_config)
                
                logger.info(f"\n✅ NETWORK CONFIG UPGRADE COMPLETE!")
                logger.info(f"Changes applied: {len(changes)}")
                logger.info(f"Backup created: {backup_path}")
                
                return {
                    "success": True,
                    "dry_run": False,
                    "changes": changes,
                    "backup_path": str(backup_path)
                }
            else:
                logger.info("No changes needed - configuration is already up to date")
                return {
                    "success": True,
                    "dry_run": False,
                    "changes": [],
                    "message": "No changes needed"
                }

def main():
    """Main entry point for the network config upgrader."""
    parser = argparse.ArgumentParser(description="Upgrade network configuration for hostname-based discovery")
    parser.add_argument('--dry-run', action='store_true', help="Preview changes without applying them")
    parser.add_argument('--apply', action='store_true', help="Apply configuration upgrades")
    parser.add_argument('--project-root', default='.', help="Project root directory")
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        parser.error("Must specify either --dry-run or --apply")
    
    # Initialize upgrader
    project_root = Path(args.project_root).resolve()
    upgrader = NetworkConfigUpgrader(project_root)
    
    # Run upgrade
    try:
        results = upgrader.run_upgrade(dry_run=args.dry_run)
        
        if args.dry_run and results.get("success"):
            logger.info(f"\n🚀 To apply these changes, run:")
            logger.info(f"python {__file__} --apply")
        
        return 0 if results.get("success") else 1
        
    except Exception as e:
        logger.error(f"Network config upgrade failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 