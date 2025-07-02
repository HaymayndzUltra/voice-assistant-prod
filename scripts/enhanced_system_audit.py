#!/usr/bin/env python3
"""
Enhanced System Audit Script (v4 - UPDATED FOR CONFIG_LOADER)
- Loads all agents from startup_config.yaml
- Analyzes each agent file for compliance with architectural and configuration standards
- Strictly checks for CANONICAL import paths and other criteria.
- Prints a markdown table report
"""
import os
import re
import sys
import yaml
import ast
from pathlib import Path

# === CONFIG ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_CONFIG_PATH = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'
CODEBASE_ROOT = PROJECT_ROOT / 'main_pc_code'
PC2_CODEBASE_ROOT = PROJECT_ROOT / 'pc2_code'
PC2_AGENTS_ROOT = PROJECT_ROOT / 'pc2_code' / 'agents'

# === AGENT GATHERING ===
def gather_targeted_agents():
    """Load agents from main_pc_code/config/startup_config.yaml"""
    
    agents = []
    
    try:
        with open(MAIN_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        # Process all service categories from main_pc_code config
        service_categories = [
            'core_services', 'main_pc_gpu_services', 'emotion_system', 
            'language_processing', 'memory_system', 'learning_knowledge',
            'planning_execution', 'tts_services', 'code_generation',
            'audio_processing', 'vision', 'monitoring_security'
        ]
        
        for category in service_categories:
            if category in config:
                for agent_config in config[category]:
                    name = agent_config.get('name', '')
                    script_path = agent_config.get('script_path', '')
                    
                    if name and script_path:
                        # Convert to absolute path for consistency
                        if not script_path.startswith('/'):
                            script_path = f"main_pc_code/{script_path}"
                        
                        agents.append({
                            'name': name,
                            'script_path': script_path
                        })
    
        print(f"Loaded {len(agents)} agents from main_pc_code config.")
        return agents
    except Exception as e:
        print(f"Error loading agents from config: {e}")
        return []

# === COMPLIANCE CHECKS (UPDATED FOR CONFIG_LOADER) ===
def check_base_agent_inheritance(source_code):
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if (isinstance(base, ast.Name) and base.id == 'BaseAgent') or \
                       (isinstance(base, ast.Attribute) and getattr(base, 'attr', None) == 'BaseAgent'):
                        return True
        return False
    except Exception:
        return False

def check_super_init_call(source_code):
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                for n in ast.walk(node):
                    if isinstance(n, ast.Call):
                        func = n.func
                        if isinstance(func, ast.Attribute) and func.attr == '__init__':
                            if isinstance(func.value, ast.Call):
                                if isinstance(func.value.func, ast.Name) and func.value.func.id == 'super':
                                    return True
                            elif isinstance(func.value, ast.Name) and func.value.id == 'super':
                                return True
        return False
    except Exception:
        return False

def check_get_health_status_implemented(source_code):
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == '_get_health_status':
                return True
        return False
    except Exception:
        return False

def check_config_loader_usage(source_code):
    # UPDATED LOGIC: Check for config_loader instead of config_parser
    try:
        tree = ast.parse(source_code)
        canonical_import_found = False
        loader_called_at_module_level = False
        
        for node in ast.walk(tree):
            # Check for the canonical import
            if isinstance(node, ast.ImportFrom):
                if node.module == 'main_pc_code.utils.config_loader' and any(alias.name == 'load_config' for alias in node.names):
                    canonical_import_found = True
            
            # Check for module-level assignment `config = load_config()`
            if isinstance(node, ast.Assign):
                # Ensure it's at the top level of the module body
                if any(isinstance(target, ast.Name) and target.id == 'config' for target in node.targets):
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'load_config':
                        # Check if this assignment is in the module's top-level body
                        # This is a heuristic: check if it's directly in the module's body, not inside a function/class
                        if node in tree.body: # Direct check if node is a top-level statement
                            loader_called_at_module_level = True
                            
        return canonical_import_found and loader_called_at_module_level
    except Exception:
        return False

def check_main_block(source_code):
    # TRULY CORRECTED LOGIC: Check for standard template and absence of argparse.
    try:
        tree = ast.parse(source_code)
        main_block_found = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test = node.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == '__name__'
                    and any(isinstance(op, ast.Eq) for op in test.ops)
                    and any(
                        (isinstance(c, ast.Constant) and c.value == '__main__') or
                        (isinstance(c, ast.Str) and c.s == '__main__')
                        for c in test.comparators
                    )
                ):
                    main_block_found = True
                    block_source = ast.get_source_segment(source_code, node)
                    if block_source is None: return False # Cannot extract source, assume non-compliant
                    
                    # Check for argparse within the block
                    if 'argparse' in block_source:
                        return False # Fails if argparse is found
                    
                    # Check for the presence of the standardized template elements
                    # This is a heuristic, but covers the key parts of our template
                    if 'agent = None' in block_source and \
                       'try:' in block_source and \
                       'agent.run()' in block_source and \
                       'except KeyboardInterrupt:' in block_source and \
                       'except Exception as e:' in block_source and \
                       'finally:' in block_source and \
                       "if agent and hasattr(agent, 'cleanup'):" in block_source:
                        return True
                    else:
                        return False # Does not match standardized template
        
        return False # No __main__ block found, or it didn't match the template
    except Exception:
        return False

# === MAIN AUDIT ===
def main():
    """Main function to run the audit."""
    targeted_agents = gather_targeted_agents()
    print(f"Auditing {len(targeted_agents)} agents from startup_config.yaml.")
    
    # Print table header
    print("| Agent Name | File Path | Compliance Status | Issues Found |")
    print("|------------|-----------|-------------------|--------------|")
    
    for agent in targeted_agents:
        name = agent['name']
        script_path = agent['script_path']
        
        compliance_status, issues = check_compliance(script_path)
        
        issues_str = ", ".join(issues) if issues else "None"
        print(f"| {name} | {script_path} | {compliance_status} | {issues_str} |")

def check_compliance(file_path):
    """Check agent file for compliance with standards."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    issues = []
    
    # C1/C2: Check for BaseAgent inheritance
    if not re.search(r'class\s+\w+\s*\(\s*BaseAgent\s*\)', content):
        issues.append("C1/C2: No BaseAgent inheritance")
    
    # C3: Check for super().__init__ call
    if not re.search(r'super\(\)\.__init__', content):
        issues.append("C3: super().__init__ not called")
    
    # C4: Check for _get_health_status method
    if not re.search(r'def\s+_get_health_status\s*\(', content):
        issues.append("C4: _get_health_status missing")
    
    # C6/C7: Check for config loader usage
    # Check for PC2 config loader pattern
    pc2_config_pattern = (re.search(r'from\s+pc2_code\.agents\.utils\.config_loader\s+import\s+Config', content) and 
                          re.search(r'config\s*=\s*Config\(\)\.get_config\(\)', content))
    
    # Check for main PC config loader pattern
    main_pc_config_pattern = (re.search(r'from\s+main_pc_code\.utils\.config_loader\s+import\s+load_config', content) and 
                             re.search(r'config\s*=\s*load_config\(\)', content))
    
    # Also check for the alternative main PC pattern with Config class
    main_pc_config_pattern_alt = (re.search(r'from\s+main_pc_code\.utils\.config_loader\s+import\s+Config', content) and 
                                 re.search(r'config\s*=\s*Config\(\)', content))
    
    # If none of the patterns match, report the issue
    if not (pc2_config_pattern or main_pc_config_pattern or main_pc_config_pattern_alt):
        issues.append("C6/C7: Config loader not used correctly")
    
    # C10: Check for standardized __main__ block
    if not re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', content):
        issues.append("C10: __main__ block not standardized")
    
    is_compliant = len(issues) == 0
    is_partially_compliant = 0 < len(issues) <= 2
    
    compliance_status = "✅ COMPLIANT" if is_compliant else "🟠 PARTIALLY COMPLIANT" if is_partially_compliant else "❌ NON-COMPLIANT"
    
    return compliance_status, issues

if __name__ == "__main__":
    main() 