#!/usr/bin/env python3
# -*- coding: utf-8 -*-
print('hello')
import ast
import re
import argparse
from pathlib import Path

# Compliance check functions

def check_parse_agent_args_usage(tree):
    # Check for import and call
    imported = False
    called = False
    
    # Check for imports from either path
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'utils.config_loader' or node.module == 'main_pc_code.utils.config_parser':
                for n in node.names:
                    if n.name == 'parse_agent_args':
                        imported = True
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                if hasattr(node.value.func, 'id') and node.value.func.id == 'parse_agent_args':
                    called = True
    return imported and called

def check_canonical_import(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == 'utils.config_loader' or node.module == 'main_pc_code.utils.config_parser':
                for n in node.names:
                    if n.name == 'parse_agent_args':
                        return True
    return False

def check_config_from_agent_args(tree):
    # Look for _agent_args.get or _agent_args[ or getattr(_agent_args in __init__
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            src = ast.get_source_segment(opened_code, node)
            if '_agent_args.get(' in src or '_agent_args[' in src or 'getattr(_agent_args' in src:
                return True
    return False

def check_no_hardcoded_values(code):
    # Look for hardcoded ports or IPs
    hardcoded_patterns = [r'\b5572\b', r'\b8571\b', r'0\.0\.0\.0']
    for pat in hardcoded_patterns:
        if re.search(pat, code):
            return False
    return True

def check_super_init_args(tree):
    # Look for super().__init__(_agent_args) in __init__
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    if hasattr(n.func, 'attr') and n.func.attr == '__init__':
                        for arg in n.args:
                            if hasattr(arg, 'id') and arg.id == '_agent_args':
                                return True
    return False

def audit_agent(filepath):
    global opened_code
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        opened_code = code
        tree = ast.parse(code)
    except Exception as e:
        return [False, False, False, False, False, f'Parse error: {e}']
    results = [
        check_parse_agent_args_usage(tree),
        check_canonical_import(tree),
        check_config_from_agent_args(tree),
        check_no_hardcoded_values(code),
        check_super_init_args(tree)
    ]
    return results + ['']

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent_list', nargs='+', help='List of agent file paths to audit', required=True)
    args = parser.parse_args()
    header = [
        'Agent Name', 'Script Path', 'parse_agent_args', 'Canonical Import',
        'All Config from _agent_args', 'No Hardcoded Values', 'Passes to super()', 'Error'
    ]
    table = [header]
    for path in args.agent_list:
        name = Path(path).stem
        abs_path = Path(path).resolve()
        results = audit_agent(abs_path)
        row = [name, str(path)]
        for r in results[:-1]:
            row.append('[✅]' if r else '[❌]')
        row.append(results[-1])
        table.append(row)
    # Print Markdown table
    col_widths = [max(len(str(row[i])) for row in table) for i in range(len(header))]
    def fmt_row(row):
        return '| ' + ' | '.join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)) + ' |'
    print(fmt_row(table[0]))
    print('|' + '|'.join('-' * (w + 2) for w in col_widths) + '|')
    for row in table[1:]:
        print(fmt_row(row))

if __name__ == '__main__':
    import traceback
    try:
        main()
    except Exception as e:
        print('ERROR:', e)
        traceback.print_exc() 