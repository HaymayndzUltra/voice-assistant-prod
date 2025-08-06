#!/usr/bin/env python3
"""
Agent Compliance Fixer Script

This script automatically fixes common compliance issues found in agent files:
1. Syntax errors (indentation, class definition, docstring placement)
2. Missing BaseAgent inheritance
3. Missing health check methods
4. Improper config loading

Usage:
    python3 scripts/fix_agent_compliance.py --agent [agent_path]
    python3 scripts/fix_agent_compliance.py --group [group_name]
    python3 scripts/fix_agent_compliance.py --system [mainpc|pc2|all]
    python3 scripts/fix_agent_compliance.py --phase [1-5] --system [mainpc|pc2|all]
    python3 scripts/fix_agent_compliance.py --batch [file_with_agent_paths]
"""

import os
import sys
import re
import ast
import argparse
import logging
import yaml
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional, Set
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_compliance_fixes.log')
    ]
)
logger = logging.getLogger("AgentComplianceFixer")

# Define paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
MAIN_CONFIG_PATH = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'

# Templates for fixes
HEALTH_CHECK_TEMPLATE = '''
    def _get_health_status(self) -> dict:
        """Return health status information."""
        # Get base health status from parent class
        base_status = super()._get_health_status()
        
        # Add agent-specific health information
        base_status.update({
            'service': self.__class__.__name__,
            'uptime_seconds': int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
            'request_count': self.request_count if hasattr(self, 'request_count') else 0,
            'status': 'HEALTHY'
        })
        
        return base_status
'''

MAIN_BLOCK_TEMPLATE = '''
if __name__ == "__main__":
    agent = None
    try:
        agent = {agent_class_name}()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {{e}}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()
'''

CONFIG_LOADER_MAINPC = """
from main_pc_code.utils.config_loader import load_config

# Load configuration at the module level
config = load_config()
"""

CONFIG_LOADER_PC2 = """
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()
"""

CLEANUP_METHOD_TEMPLATE = '''
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            
            if hasattr(self, 'context') and self.context:
                self.context.term()
                
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
'''

def load_config(config_path: Path) -> Dict:
    """Load YAML configuration file."""
    try:
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return {}
            
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def get_all_agents() -> Dict[str, Any]:
    """Get all agents from both MainPC and PC2 configs."""
    result = {"mainpc": {}, "pc2": [], "core_services": []}
    
    # Load MainPC agents
    mainpc_config = load_config(MAIN_CONFIG_PATH)
    if "agent_groups" in mainpc_config:
        result["mainpc"] = mainpc_config["agent_groups"]
    
    # Load PC2 agents
    pc2_config = load_config(PC2_CONFIG_PATH)
    if "pc2_services" in pc2_config:
        result["pc2"] = pc2_config["pc2_services"]
    if "core_services" in pc2_config:
        result["core_services"] = pc2_config["core_services"]
    
    return result

def get_agents_by_phase(phase: int, system: str = "all") -> List[str]:
    """Get all agents for a specific phase and system."""
    phase_mapping = {
        1: {
            "mainpc": ["core_services", "memory_system"],
            "pc2": ["TieredResponder", "AsyncProcessor", "CacheManager", "PerformanceMonitor", "VisionProcessingAgent"]
        },
        2: {
            "mainpc": ["utility_services", "ai_models_gpu_services"],
            "pc2": ["DreamWorldAgent", "UnifiedMemoryReasoningAgent", "TutorAgent", "TutoringServiceAgent", "ContextManager"]
        },
        3: {
            "mainpc": ["vision_system", "learning_knowledge"],
            "pc2": ["ExperienceTracker", "ResourceManager", "HealthMonitor", "TaskScheduler"]
        },
        4: {
            "mainpc": ["language_processing", "audio_processing"],
            "pc2": ["AuthenticationAgent", "SystemHealthManager", "UnifiedUtilsAgent", "ProactiveContextMonitor"]
        },
        5: {
            "mainpc": ["emotion_system", "utilities_support", "reasoning_services"],
            "pc2": ["AgentTrustScorer", "FileSystemAssistantAgent", "RemoteConnectorAgent", "UnifiedWebAgent", 
                   "DreamingModeAgent", "PerformanceLoggerAgent", "AdvancedRouter", "TutoringAgent", "MemoryOrchestratorService"]
        }
    }
    
    agent_paths = []
    all_agents = get_all_agents()
    
    if system in ["all", "mainpc"] and phase in phase_mapping:
        for group_name in phase_mapping[phase]["mainpc"]:
            if group_name in all_agents["mainpc"]:
                for agent_name, agent_config in all_agents["mainpc"][group_name].items():
                    script_path = agent_config.get("script_path")
                    if script_path:
                        full_path = os.path.join(PROJECT_ROOT, script_path)
                        agent_paths.append(full_path)
    
    if system in ["all", "pc2"] and phase in phase_mapping:
        for agent_name in phase_mapping[phase]["pc2"]:
            for agent in all_agents["pc2"] + all_agents["core_services"]:
                if isinstance(agent, dict) and agent.get("name") == agent_name:
                    script_path = agent.get("script_path")
                    if script_path:
                        full_path = os.path.join(PROJECT_ROOT, script_path)
                        agent_paths.append(full_path)
    
    return agent_paths

def fix_syntax_errors(content: str) -> Tuple[str, bool]:
    """Fix common syntax errors in Python code."""
    fixed_content = content
    
    # Fix 1: Fix class definition with docstring
    pattern = r'class\s+(\w+)\(\s*\n\s*"""([\s\S]*?)"""\s*(\w+)\):'
    replacement = r'class \1(\3):\n    """\2"""'
    fixed_content = re.sub(pattern, replacement, fixed_content)
    
    # Fix 2: Fix incomplete statements
    pattern = r'(\s+)self\.\s*\n'
    replacement = r'\1# TODO: Fix incomplete statement\n'
    fixed_content = re.sub(pattern, replacement, fixed_content)
    
    # Fix 3: Fix docstrings after function arguments
    pattern = r'def\s+(\w+)\(([^)]*)\)\s*"""([\s\S]*?)"""'
    replacement = r'def \1(\2):\n    """\3"""'
    fixed_content = re.sub(pattern, replacement, fixed_content)
    
    # Fix 4: Fix docstrings after variable assignments
    pattern = r'(\s*)(\w+)\s*=\s*([^=\n]+)"""([\s\S]*?)"""'
    replacement = r'\1\2 = \3\n\1"""\4"""'
    fixed_content = re.sub(pattern, replacement, fixed_content)
    
    # Check if we actually fixed anything
    fixed = fixed_content != content
    
    # Verify the syntax is now correct
    try:
        ast.parse(fixed_content)
        return fixed_content, True
    except SyntaxError as e:
        logger.warning(f"Could not fix all syntax errors: {e}")
        return fixed_content, fixed

def add_base_agent_inheritance(content: str, class_name: str) -> Tuple[str, bool]:
    """Add BaseAgent inheritance to a class."""
    # Check if already inherits from BaseAgent
    if re.search(rf'class\s+{class_name}\s*\(\s*BaseAgent\s*\)', content):
        return content, False
    
    # Find the class definition
    pattern = rf'class\s+{class_name}\s*\(([^)]*)\)'
    match = re.search(pattern, content)
    
    if match:
        current_inheritance = match.group(1).strip()
        if current_inheritance:
            # Already inherits from something, add BaseAgent
            if 'BaseAgent' not in current_inheritance:
                new_inheritance = f'BaseAgent, {current_inheritance}'
                new_class_def = f'class {class_name}({new_inheritance})'
                fixed_content = content.replace(match.group(0), new_class_def)
                return fixed_content, True
        else:
            # No inheritance, add BaseAgent
            new_class_def = f'class {class_name}(BaseAgent)'
            fixed_content = content.replace(match.group(0), new_class_def)
            return fixed_content, True
    
    return content, False

def add_imports_for_base_agent(content: str) -> Tuple[str, bool]:
    """Add necessary imports for BaseAgent."""
    if 'from common.core.base_agent import BaseAgent' in content:
        return content, False
    
    # Check if there are any imports
    if 'import ' in content:
        # Add after the last import
        lines = content.split('\n')
        last_import_line = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                last_import_line = i
        
        lines.insert(last_import_line + 1, 'from common.core.base_agent import BaseAgent')
        return '\n'.join(lines), True
    else:
        # Add at the beginning
        return 'from common.core.base_agent import BaseAgent\n\n' + content, True

def add_health_check_method(content: str) -> Tuple[str, bool]:
    """Add health check method if missing."""
    if '_get_health_status' in content:
        return content, False
    
    # Find the last method in the class
    methods = re.finditer(r'def\s+(\w+)\s*\(', content)
    last_method_end = 0
    for method in methods:
        method_name = method.group(1)
        method_start = method.start()
        
        # Find the end of this method (next method or end of file)
        next_method = re.search(r'def\s+\w+\s*\(', content[method_start + 1:])
        if next_method:
            method_end = method_start + 1 + next_method.start()
        else:
            method_end = len(content)
        
        if method_end > last_method_end:
            last_method_end = method_end
    
    if last_method_end > 0:
        # Insert health check method after the last method
        fixed_content = content[:last_method_end] + HEALTH_CHECK_TEMPLATE + content[last_method_end:]
        return fixed_content, True
    
    return content, False

def add_cleanup_method(content: str) -> Tuple[str, bool]:
    """Add cleanup method if missing."""
    if 'def cleanup(' in content:
        return content, False
    
    # Find the last method in the class
    methods = re.finditer(r'def\s+(\w+)\s*\(', content)
    last_method_end = 0
    for method in methods:
        method_name = method.group(1)
        method_start = method.start()
        
        # Find the end of this method (next method or end of file)
        next_method = re.search(r'def\s+\w+\s*\(', content[method_start + 1:])
        if next_method:
            method_end = method_start + 1 + next_method.start()
        else:
            method_end = len(content)
        
        if method_end > last_method_end:
            last_method_end = method_end
    
    if last_method_end > 0:
        # Insert cleanup method after the last method
        fixed_content = content[:last_method_end] + CLEANUP_METHOD_TEMPLATE + content[last_method_end:]
        return fixed_content, True
    
    return content, False

def fix_config_loading(content: str, agent_path: str) -> Tuple[str, bool]:
    """Fix config loading in the agent file."""
    # Determine if this is a MainPC or PC2 agent
    is_mainpc = 'main_pc_code' in agent_path
    
    # Check if config loading is already correct
    if is_mainpc and 'from main_pc_code.utils.config_loader import load_config' in content:
        return content, False
    elif not is_mainpc and 'from pc2_code.agents.utils.config_loader import Config' in content:
        return content, False
    
    # Remove existing config loading
    content = re.sub(r'from .*config_loader import .*\n', '', content)
    
    # Add correct config loading
    if is_mainpc:
        config_loader = CONFIG_LOADER_MAINPC
    else:
        config_loader = CONFIG_LOADER_PC2
    
    # Add after imports
    lines = content.split('\n')
    last_import_line = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            last_import_line = i
    
    lines.insert(last_import_line + 1, config_loader)
    return '\n'.join(lines), True

def add_main_block(content: str, class_name: str) -> Tuple[str, bool]:
    """Add standard main block if missing."""
    if '__name__ == "__main__"' in content:
        return content, False
    
    main_block = MAIN_BLOCK_TEMPLATE.format(agent_class_name=class_name)
    return content + '\n' + main_block, True

def extract_class_name(file_path: str) -> str:
    """Extract the main agent class name from a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for class that inherits from BaseAgent
        match = re.search(r'class\s+(\w+)\s*\([^)]*BaseAgent[^)]*\)', content)
        if match:
            return match.group(1)
        
        # If not found, look for any class
        match = re.search(r'class\s+(\w+)', content)
        if match:
            return match.group(1)
        
        # If still not found, use filename
        return os.path.basename(file_path).replace('.py', '')
    except Exception as e:
        logger.error(f"Error extracting class name: {e}")
        return os.path.basename(file_path).replace('.py', '')

def fix_agent(agent_path: str) -> Dict[str, bool]:
    """Fix compliance issues in an agent file."""
    results = {
        "syntax": False,
        "base_agent": False,
        "health_check": False,
        "config_loading": False,
        "main_block": False,
        "cleanup": False
    }
    
    try:
        # Read the file
        with open(agent_path, 'r') as f:
            content = f.read()
        
        # Fix syntax errors
        try:
            ast.parse(content)
            logger.info(f"No syntax errors in {agent_path}")
            results["syntax"] = True
        except SyntaxError as e:
            logger.info(f"Found syntax error in {agent_path}: {e}")
            content, fixed = fix_syntax_errors(content)
            results["syntax"] = fixed
            if not fixed:
                logger.warning(f"Could not fix all syntax errors in {agent_path}: {e}")
                # If we couldn't fix syntax errors, return early
                return results
        
        # Extract class name
        class_name = extract_class_name(agent_path)
        
        # Fix BaseAgent inheritance
        content, fixed = add_base_agent_inheritance(content, class_name)
        if fixed:
            logger.info(f"Added BaseAgent inheritance to {agent_path}")
            # Add necessary imports
            content, _ = add_imports_for_base_agent(content)
        else:
            logger.info(f"Already inherits from BaseAgent in {agent_path}")
        results["base_agent"] = True
        
        # Add health check method
        content, fixed = add_health_check_method(content)
        if fixed:
            logger.info(f"Added health check method to {agent_path}")
        else:
            logger.info(f"Health check method already exists in {agent_path}")
        results["health_check"] = True
        
        # Fix config loading
        content, fixed = fix_config_loading(content, agent_path)
        if fixed:
            logger.info(f"Fixed config loading in {agent_path}")
        else:
            logger.info(f"Config loading already correct in {agent_path}")
        results["config_loading"] = True
        
        # Add main block
        content, fixed = add_main_block(content, class_name)
        if fixed:
            logger.info(f"Added main block to {agent_path}")
        else:
            logger.info(f"Main block already compliant in {agent_path}")
        results["main_block"] = True
        
        # Add cleanup method
        content, fixed = add_cleanup_method(content)
        if fixed:
            logger.info(f"Added cleanup method to {agent_path}")
        else:
            logger.info(f"Cleanup method already exists in {agent_path}")
        results["cleanup"] = True
        
        # Write the fixed content back to the file
        with open(agent_path, 'w') as f:
            f.write(content)
        
        return results
    except Exception as e:
        logger.error(f"Error fixing {agent_path}: {e}")
        logger.error(traceback.format_exc())
        return results

def fix_agents_by_group(group_name: str, system: str = "mainpc") -> Dict[str, Dict[str, bool]]:
    """Fix all agents in a group."""
    all_agents = get_all_agents()
    results = {}
    
    if system == "mainpc":
        if group_name in all_agents["mainpc"]:
            agents = all_agents["mainpc"][group_name]
            if isinstance(agents, dict):
                for agent_name, agent_config in agents.items():
                    script_path = agent_config.get("script_path")
                    if script_path:
                        full_path = os.path.join(PROJECT_ROOT, script_path)
                        logger.info(f"Fixing {agent_name} at {full_path}")
                        results[agent_name] = fix_agent(full_path)
            else:
                logger.error(f"Invalid agent configuration for group {group_name}")
        else:
            logger.error(f"Group not found: {group_name}")
    elif system == "pc2":
        pc2_agents = all_agents["pc2"] + all_agents["core_services"]
        for agent in pc2_agents:
            if isinstance(agent, dict) and agent.get("name") == group_name:
                script_path = agent.get("script_path")
                if script_path:
                    full_path = os.path.join(PROJECT_ROOT, script_path)
                    logger.info(f"Fixing {group_name} at {full_path}")
                    results[group_name] = fix_agent(full_path)
                break
        else:
            logger.error(f"Agent not found: {group_name}")
    
    return results

def fix_agents_by_system(system: str = "all") -> Dict[str, Dict[str, bool]]:
    """Fix all agents in a system."""
    all_agents = get_all_agents()
    results = {}
    
    if system in ["all", "mainpc"]:
        for group_name, agents in all_agents["mainpc"].items():
            if isinstance(agents, dict):
                for agent_name, agent_config in agents.items():
                    script_path = agent_config.get("script_path")
                    if script_path:
                        full_path = os.path.join(PROJECT_ROOT, script_path)
                        logger.info(f"Fixing {agent_name} at {full_path}")
                        results[agent_name] = fix_agent(full_path)
    
    if system in ["all", "pc2"]:
        pc2_agents = all_agents["pc2"] + all_agents["core_services"]
        for agent in pc2_agents:
            if isinstance(agent, dict):
                agent_name = agent.get("name")
                script_path = agent.get("script_path")
                if agent_name and script_path:
                    full_path = os.path.join(PROJECT_ROOT, script_path)
                    logger.info(f"Fixing {agent_name} at {full_path}")
                    results[agent_name] = fix_agent(full_path)
    
    return results

def fix_agents_by_phase(phase: int, system: str = "all") -> Dict[str, Dict[str, bool]]:
    """Fix all agents in a phase."""
    agent_paths = get_agents_by_phase(phase, system)
    results = {}
    
    for path in agent_paths:
        agent_name = os.path.basename(path).replace('.py', '')
        logger.info(f"Fixing {agent_name} at {path}")
        results[agent_name] = fix_agent(path)
    
    return results

def fix_agents_from_batch_file(batch_file: str) -> Dict[str, Dict[str, bool]]:
    """Fix agents listed in a batch file."""
    results = {}
    
    try:
        with open(batch_file, 'r') as f:
            agent_paths = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        for path in agent_paths:
            full_path = os.path.join(PROJECT_ROOT, path)
            agent_name = os.path.basename(path).replace('.py', '')
            logger.info(f"Fixing {agent_name} at {full_path}")
            results[agent_name] = fix_agent(full_path)
    except Exception as e:
        logger.error(f"Error processing batch file: {e}")
    
    return results

def print_results(results: Dict[str, Dict[str, bool]]):
    """Print the results of fixing agents."""
    for agent_name, agent_results in results.items():
        print(f"Results for {agent_name}:")
        for check, passed in agent_results.items():
            status = "✅" if passed else "❌"
            print(f"  {check}: {status}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Fix compliance issues in agent files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agent", help="Path to agent file")
    group.add_argument("--group", help="Agent group name")
    group.add_argument("--system", choices=["mainpc", "pc2", "all"], help="System to fix")
    group.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Phase to fix")
    group.add_argument("--batch", help="Path to batch file with agent paths")
    
    parser.add_argument("--system-for-phase", choices=["mainpc", "pc2", "all"], default="all", 
                        help="System to fix for phase (only used with --phase)")
    
    args = parser.parse_args()
    
    if args.agent:
        results = {os.path.basename(args.agent).replace('.py', ''): fix_agent(args.agent)}
    elif args.group:
        results = fix_agents_by_group(args.group, "mainpc")
    elif args.system:
        results = fix_agents_by_system(args.system)
    elif args.phase:
        results = fix_agents_by_phase(args.phase, args.system_for_phase)
    elif args.batch:
        results = fix_agents_from_batch_file(args.batch)
    
    print_results(results)

if __name__ == "__main__":
    main() 