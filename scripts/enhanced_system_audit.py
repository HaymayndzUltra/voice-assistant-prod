#!/usr/bin/env python3
"""
Enhanced System Audit Script (v3 - TRULY CORRECTED)
- Loads all agents from startup_config.yaml
- Analyzes each agent file for compliance with architectural and configuration standards
- Strictly checks for CANONICAL import paths and other criteria.
- Prints a markdown table report
"""
import os
import yaml
import ast
from pathlib import Path

# === CONFIG ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
CODEBASE_ROOT = PROJECT_ROOT / 'main_pc_code'

# === COMPLIANCE CHECKS (TRULY CORRECTED) ===
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

def check_config_parser_usage(source_code):
    # TRULY CORRECTED LOGIC: Must check for the exact canonical path and module-level call.
    try:
        tree = ast.parse(source_code)
        canonical_import_found = False
        parser_called_at_module_level = False
        
        for node in ast.walk(tree):
            # Check for the canonical import
            if isinstance(node, ast.ImportFrom):
                if node.module == 'main_pc_code.utils.config_parser' and any(alias.name == 'parse_agent_args' for alias in node.names):
                    canonical_import_found = True
            
            # Check for module-level assignment `_agent_args = parse_agent_args()`
            if isinstance(node, ast.Assign):
                # Ensure it's at the top level of the module body
                if any(isinstance(target, ast.Name) and target.id == '_agent_args' for target in node.targets):
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'parse_agent_args':
                        # Check if this assignment is in the module's top-level body
                        # This is a heuristic: check if it's directly in the module's body, not inside a function/class
                        if node in tree.body: # Direct check if node is a top-level statement
                            parser_called_at_module_level = True
                            
        return canonical_import_found and parser_called_at_module_level
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

# === AGENT GATHERING ===
def gather_agents_from_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    agents = []
    agent_sections = [k for k, v in config.items() if isinstance(v, list)]
    for section in agent_sections:
        for agent in config[section]:
            if isinstance(agent, dict) and 'name' in agent and 'script_path' in agent:
                agents.append({
                    'name': agent['name'].strip(),
                    'script_path': agent['script_path'].strip()
                })
    return agents

# === MAIN AUDIT ===
def main():
    if not CONFIG_PATH.exists():
        print(f"Error: Config file not found at {CONFIG_PATH}")
        return

    agents = gather_agents_from_config(CONFIG_PATH)
    results = []

    for agent in agents:
        agent_name = agent['name']
        rel_path = agent['script_path']
        abs_path = (CODEBASE_ROOT / rel_path).resolve()
        
        issues = []
        if not abs_path.exists():
            status = '❌ NON-COMPLIANT'
            issues.append('File not found')
        else:
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Run all checks
                if not check_base_agent_inheritance(code): issues.append('C1/C2: No BaseAgent inheritance')
                if not check_super_init_call(code): issues.append('C3: super().__init__ not called')
                if not check_get_health_status_implemented(code): issues.append('C4: _get_health_status missing')
                if not check_config_parser_usage(code): issues.append('C6/C7: Config parser not used correctly')
                if not check_main_block(code): issues.append('C10: __main__ block not standardized')

                if not issues:
                    status = '✅ FULLY COMPLIANT'
                elif len(issues) <= 2:
                    status = '🟠 PARTIALLY COMPLIANT'
                else:
                    status = '❌ NON-COMPLIANT'

            except Exception as e:
                status = '❌ NON-COMPLIANT'
                issues.append(f'File read/parse error: {e}')

        results.append({
            'name': agent_name,
            'file': rel_path,
            'status': status,
            'issues': issues
        })

    # Print markdown table
    print('| Agent Name | File Path | Compliance Status | Issues Found |')
    print('|------------|-----------|-------------------|--------------|')
    for r in results:
        issues_str = ', '.join(r['issues']) if r['issues'] else 'None'
        print(f"| {r['name']} | {r['file']} | {r['status']} | {issues_str} |")

if __name__ == '__main__':
    main() 