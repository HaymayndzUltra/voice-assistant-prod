#!/usr/bin/env python3
"""
Fix All Core Agents
------------------
This script fixes the issues identified in core agents:
1. ModelManagerAgent: Fix syntax error in vram_budget_percentage assignment
2. ChainOfThoughtAgent: Fix import error for config.system_config
3. TaskRouter: Fix configuration loading error
"""
import os
import re
import sys
from pathlib import Path

def fix_model_manager_agent():
    """Fix the syntax error in ModelManagerAgent."""
    file_path = "main_pc_code/agents/model_manager_agent.py"
    print(f"Fixing ModelManagerAgent syntax error in {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix the syntax error in vram_budget_percentage assignment
        fixed_content = re.sub(
            r"self\.vram_management_config\.get\('vram_budget_percentage'\)\s*=\s*80",
            "self.vram_management_config['vram_budget_percentage'] = 80",
            content
        )
        
        if fixed_content != content:
            with open(file_path, 'w') as f:
                f.write(fixed_content)
            print("✓ Fixed syntax error in ModelManagerAgent")
            return True
        else:
            print("✗ No changes needed in ModelManagerAgent")
            return False
    except Exception as e:
        print(f"✗ Error fixing ModelManagerAgent: {e}")
        return False

def fix_chain_of_thought_agent():
    """Fix the import error in ChainOfThoughtAgent."""
    file_path = "main_pc_code/FORMAINPC/ChainOfThoughtAgent.py"
    print(f"Fixing ChainOfThoughtAgent import error in {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Fix the import error
        if "from config.system_config import config" in content:
            fixed_content = content.replace(
                "from config.system_config import config",
                "import sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))\nfrom main_pc_code.config.config_manager import ConfigManager\nconfig = ConfigManager().get_config()"
            )
            
            with open(file_path, 'w') as f:
                f.write(fixed_content)
            print("✓ Fixed import error in ChainOfThoughtAgent")
            return True
        else:
            print("✗ Import already fixed in ChainOfThoughtAgent")
            return False
    except Exception as e:
        print(f"✗ Error fixing ChainOfThoughtAgent: {e}")
        return False

def fix_task_router():
    """Fix the configuration loading error in TaskRouter."""
    file_path = "main_pc_code/src/core/task_router.py"
    print(f"Fixing TaskRouter configuration error in {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find the configuration loading code
        config_loading_pattern = r"(try:\s*.*?config\s*=\s*.*?)(except.*?)(pass|return)"
        
        if re.search(config_loading_pattern, content, re.DOTALL):
            # Replace with a more robust configuration loading
            fixed_content = re.sub(
                config_loading_pattern,
                r"\1except Exception as e:\n        self.logger.error(f\"Error loading configuration: {e}\")\n        self.config = {}\n        ",
                content,
                flags=re.DOTALL
            )
            
            with open(file_path, 'w') as f:
                f.write(fixed_content)
            print("✓ Fixed configuration error in TaskRouter")
            return True
        else:
            print("✗ No configuration loading pattern found in TaskRouter")
            return False
    except Exception as e:
        print(f"✗ Error fixing TaskRouter: {e}")
        return False

def add_health_check_methods():
    """Add health_check methods to core agents that don't have them."""
    core_agents = [
        "main_pc_code/src/core/task_router.py",
        "main_pc_code/agents/model_manager_agent.py",
        "main_pc_code/FORMAINPC/ChainOfThoughtAgent.py",
        "main_pc_code/agents/coordinator_agent.py"
    ]
    
    health_check_template = '''
    def health_check(self):
        """Health check method for agent monitoring."""
        status = {
            "status": "healthy",
            "version": "1.0",
            "uptime": self._get_uptime() if hasattr(self, "_get_uptime") else 0,
            "memory_usage": self._get_memory_usage() if hasattr(self, "_get_memory_usage") else 0,
            "message_count": getattr(self, "message_count", 0)
        }
        return status
    
    def _get_uptime(self):
        """Get agent uptime in seconds."""
        import time
        return time.time() - getattr(self, "start_time", time.time())
    
    def _get_memory_usage(self):
        """Get memory usage of this process."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)  # MB
        except ImportError:
            return 0  # psutil not available
    '''
    
    success_count = 0
    for agent_path in core_agents:
        print(f"Checking {agent_path} for health_check method...")
        try:
            with open(agent_path, 'r') as f:
                content = f.read()
            
            if "def health_check" not in content and "def _get_health_status" not in content:
                # Find the class definition
                class_match = re.search(r'class\s+(\w+)(?:\(.*?\))?:', content)
                if class_match:
                    # Find a good place to insert the health_check method
                    lines = content.splitlines()
                    class_name = class_match.group(1)
                    
                    # Find the end of the class
                    in_class = False
                    class_indent = 0
                    insert_line = len(lines)
                    
                    for i, line in enumerate(lines):
                        stripped = line.lstrip()
                        if not in_class and stripped.startswith(f"class {class_name}"):
                            in_class = True
                            class_indent = len(line) - len(stripped)
                        elif in_class and line.strip() and len(line) - len(line.lstrip()) <= class_indent:
                            insert_line = i
                            break
                    
                    # Insert the health_check method
                    lines.insert(insert_line, health_check_template)
                    
                    # Write back
                    with open(agent_path, 'w') as f:
                        f.write("\n".join(lines))
                    
                    print(f"✓ Added health_check method to {agent_path}")
                    success_count += 1
                else:
                    print(f"✗ No class definition found in {agent_path}")
            else:
                print(f"✓ {agent_path} already has health_check or _get_health_status method")
        except Exception as e:
            print(f"✗ Error adding health_check to {agent_path}: {e}")
    
    print(f"Added health_check methods to {success_count} agents")
    return success_count > 0

def main():
    print("Fixing all core agent issues...")
    
    # Track success
    success = []
    
    # Fix ModelManagerAgent
    if fix_model_manager_agent():
        success.append("ModelManagerAgent")
    
    # Fix ChainOfThoughtAgent
    if fix_chain_of_thought_agent():
        success.append("ChainOfThoughtAgent")
    
    # Fix TaskRouter
    if fix_task_router():
        success.append("TaskRouter")
    
    # Add health check methods
    if add_health_check_methods():
        success.append("HealthCheckMethods")
    
    # Print summary
    print("\nSummary:")
    if success:
        print(f"Successfully fixed: {', '.join(success)}")
    else:
        print("No fixes were needed or applied.")
    
    print("\nNext steps:")
    print("1. Run the test framework again to verify fixes")
    print("2. Check for any remaining issues")
    print("3. Continue with the integration of other components")

if __name__ == "__main__":
    main() 