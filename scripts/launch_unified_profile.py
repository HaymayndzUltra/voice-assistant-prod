#!/usr/bin/env python3
"""
Unified System Profile-Based Launcher - Phase 3
Launches system with profile-specific configuration
"""

import os
import sys
import yaml
import copy
import time
import subprocess
import logging
import signal
from typing import Dict, List, Set, Optional
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ProfileLauncher')

class ProfileBasedLauncher:
    def __init__(self):
        self.profile_name = os.environ.get('PROFILE', 'core').lower()
        self.base_config_path = "config/unified_startup_phase2.yaml"
        self.profile_path = f"profiles/{self.profile_name}.yaml"
        self.output_config_path = f"config/unified_startup_{self.profile_name}.yaml"
        
        self.base_config = None
        self.profile_config = None
        self.merged_config = None
        
        logger.info(f"Initializing with profile: {self.profile_name}")
        
    def load_configurations(self):
        """Load base configuration and profile"""
        # Load base configuration
        try:
            with open(self.base_config_path, 'r') as f:
                self.base_config = yaml.safe_load(f)
            logger.info(f"Loaded base configuration from {self.base_config_path}")
        except Exception as e:
            logger.error(f"Failed to load base configuration: {e}")
            raise
            
        # Load profile configuration
        try:
            with open(self.profile_path, 'r') as f:
                self.profile_config = yaml.safe_load(f)
            logger.info(f"Loaded profile configuration from {self.profile_path}")
        except FileNotFoundError:
            logger.error(f"Profile '{self.profile_name}' not found at {self.profile_path}")
            logger.info("Available profiles: core, vision, learning, tutoring, full")
            raise
        except Exception as e:
            logger.error(f"Failed to load profile configuration: {e}")
            raise
            
    def apply_profile(self):
        """Apply profile rules to generate final configuration"""
        # Start with a deep copy of base config
        self.merged_config = copy.deepcopy(self.base_config)
        
        # Apply resource overrides
        if 'resource_overrides' in self.profile_config:
            self._apply_resource_overrides()
            
        # Apply agent selection rules
        if 'agent_selection' in self.profile_config:
            self._apply_agent_selection()
            
        # Apply startup parameters
        if 'startup' in self.profile_config:
            self._apply_startup_parameters()
            
        # Apply features
        if 'features' in self.profile_config:
            self._apply_features()
            
        logger.info(f"Profile '{self.profile_name}' applied successfully")
        
    def _apply_resource_overrides(self):
        """Apply resource limit overrides from profile"""
        overrides = self.profile_config['resource_overrides']
        
        # Global settings overrides
        if 'global_settings' in overrides:
            for key, value in overrides['global_settings'].items():
                if key in self.merged_config['global_settings']:
                    self.merged_config['global_settings'][key].update(value)
                else:
                    self.merged_config['global_settings'][key] = value
                    
        # Agent-specific overrides
        if 'agent_overrides' in overrides:
            for agent_name, agent_overrides in overrides['agent_overrides'].items():
                # Find agent in configuration
                for group_name, group_agents in self.merged_config['agent_groups'].items():
                    if agent_name in group_agents:
                        if 'config' not in group_agents[agent_name]:
                            group_agents[agent_name]['config'] = {}
                        group_agents[agent_name]['config'].update(agent_overrides)
                        
    def _apply_agent_selection(self):
        """Apply agent selection rules from profile"""
        selection = self.profile_config['agent_selection']
        filtered_groups = {}
        
        # Process include/exclude groups
        include_groups = selection.get('include_groups', [])
        exclude_groups = selection.get('exclude_groups', [])
        
        for group_name, group_agents in self.merged_config['agent_groups'].items():
            if exclude_groups and group_name in exclude_groups:
                continue
            if include_groups and group_name not in include_groups:
                # Check if we need to keep for specific agents
                has_required_agent = False
                include_agents = selection.get('include_agents', [])
                for agent_name in group_agents:
                    if agent_name in include_agents:
                        has_required_agent = True
                        break
                if not has_required_agent:
                    continue
                    
            filtered_groups[group_name] = group_agents
            
        # Process include/exclude specific agents
        include_agents = selection.get('include_agents', [])
        exclude_agents = selection.get('exclude_agents', [])
        
        if include_agents or exclude_agents:
            for group_name, group_agents in filtered_groups.items():
                filtered_agents = {}
                for agent_name, agent_config in group_agents.items():
                    # Check if agent is required (essential)
                    if agent_config.get('required', True):
                        # Always include essential agents unless explicitly excluded
                        if agent_name not in exclude_agents:
                            filtered_agents[agent_name] = agent_config
                    else:
                        # Optional agent - check include list
                        if include_agents and agent_name in include_agents:
                            filtered_agents[agent_name] = agent_config
                            
                filtered_groups[group_name] = filtered_agents
                
        # Handle optional agents setting
        optional_setting = selection.get('optional_agents', True)
        if optional_setting == False:
            # Remove all optional agents
            for group_name, group_agents in filtered_groups.items():
                filtered_groups[group_name] = {
                    name: config for name, config in group_agents.items()
                    if config.get('required', True)
                }
        elif optional_setting == 'all':
            # Keep all agents (no filtering)
            pass
        elif isinstance(optional_setting, dict) and 'include' in optional_setting:
            # Include specific optional agents
            include_optional = optional_setting['include']
            for group_name, group_agents in self.merged_config['agent_groups'].items():
                if group_name not in filtered_groups:
                    filtered_groups[group_name] = {}
                for agent_name, agent_config in group_agents.items():
                    if agent_name in include_optional and not agent_config.get('required', True):
                        filtered_groups[group_name][agent_name] = agent_config
                        
        # Apply autoload settings
        autoload_agents = selection.get('autoload_on_startup', [])
        for agent_name in autoload_agents:
            for group_name, group_agents in filtered_groups.items():
                if agent_name in group_agents:
                    # Change autoload setting
                    if group_agents[agent_name].get('autoload') == 'on_demand':
                        group_agents[agent_name]['autoload'] = 'on_startup'
                        group_agents[agent_name]['required'] = True
                        
        # Update merged config with filtered groups
        self.merged_config['agent_groups'] = filtered_groups
        
        # Count agents
        total_agents = sum(len(agents) for agents in filtered_groups.values())
        essential = sum(
            1 for group in filtered_groups.values() 
            for agent in group.values() 
            if agent.get('required', True)
        )
        logger.info(f"Profile '{self.profile_name}': {total_agents} agents ({essential} essential)")
        
    def _apply_startup_parameters(self):
        """Apply startup parameters from profile"""
        startup = self.profile_config['startup']
        
        # Apply to global settings
        if 'health_checks' not in self.merged_config['global_settings']:
            self.merged_config['global_settings']['health_checks'] = {}
            
        health_checks = self.merged_config['global_settings']['health_checks']
        
        if 'timeout_seconds' in startup:
            health_checks['start_period_seconds'] = startup['timeout_seconds']
        if 'health_check_retries' in startup:
            health_checks['retries'] = startup['health_check_retries']
            
        # Store parallel starts for launcher
        if 'parallel_starts' in startup:
            self.merged_config['launcher_settings'] = {
                'parallel_starts': startup['parallel_starts']
            }
            
    def _apply_features(self):
        """Apply feature flags from profile"""
        features = self.profile_config['features']
        
        # Add feature flags to environment
        if 'environment' not in self.merged_config['global_settings']:
            self.merged_config['global_settings']['environment'] = {}
            
        env = self.merged_config['global_settings']['environment']
        
        for feature, enabled in features.items():
            env_var = f"FEATURE_{feature.upper()}"
            env[env_var] = 'true' if enabled else 'false'
            
    def save_merged_config(self):
        """Save the merged configuration to file"""
        try:
            with open(self.output_config_path, 'w') as f:
                yaml.dump(self.merged_config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"Saved merged configuration to {self.output_config_path}")
        except Exception as e:
            logger.error(f"Failed to save merged configuration: {e}")
            raise
            
    def launch_system(self):
        """Launch the system with the generated configuration"""
        # Use the Phase 2 launcher with our generated config
        launcher_script = "scripts/launch_unified_phase2.py"
        
        # Set config path environment variable
        env = os.environ.copy()
        env['UNIFIED_CONFIG_PATH'] = self.output_config_path
        
        logger.info(f"Launching system with profile '{self.profile_name}'...")
        
        # Modify launcher to use our config
        cmd = [sys.executable, launcher_script, self.output_config_path]
        
        try:
            process = subprocess.run(cmd, env=env)
            return process.returncode
        except KeyboardInterrupt:
            logger.info("Launch interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Failed to launch system: {e}")
            return 1
            
    def run(self):
        """Main execution method"""
        try:
            # Load configurations
            self.load_configurations()
            
            # Apply profile
            self.apply_profile()
            
            # Save merged configuration
            self.save_merged_config()
            
            # Display summary
            self._display_summary()
            
            # Launch system
            return self.launch_system()
            
        except Exception as e:
            logger.error(f"Profile launcher failed: {e}")
            return 1
            
    def _display_summary(self):
        """Display profile summary"""
        print("\n" + "="*60)
        print(f"UNIFIED SYSTEM - PROFILE: {self.profile_name.upper()}")
        print("="*60)
        
        profile_info = self.profile_config.get('profile', {})
        print(f"Description: {profile_info.get('description', 'N/A')}")
        
        # Count agents
        total = sum(len(agents) for agents in self.merged_config['agent_groups'].values())
        essential = sum(
            1 for group in self.merged_config['agent_groups'].values() 
            for agent in group.values() 
            if agent.get('required', True)
        )
        optional = total - essential
        
        print(f"\nAgent Configuration:")
        print(f"  Total agents: {total}")
        print(f"  Essential: {essential}")
        print(f"  Optional: {optional}")
        
        # Resource limits
        limits = self.merged_config['global_settings']['resource_limits']
        print(f"\nResource Limits:")
        print(f"  CPU: {limits['cpu_percent']}%")
        print(f"  Memory: {limits['memory_mb']} MB")
        print(f"  Threads: {limits['max_threads']}")
        
        print("\nConfiguration saved to:", self.output_config_path)
        print("="*60 + "\n")

if __name__ == "__main__":
    launcher = ProfileBasedLauncher()
    sys.exit(launcher.run())