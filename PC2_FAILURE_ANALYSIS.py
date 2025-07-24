#!/usr/bin/env python3
"""
PC2 Agent Failure Analysis Script
Analyzes PC2 agents and categorizes failures by proven patterns
"""

import sys
import os
import importlib.util
import re
from pathlib import Path

def analyze_pc2_agents():
    """Analyze PC2 agents for import failures using PC2 proven patterns"""
    
    print("🔍 PC2 FAILURE ANALYSIS - APPLYING PC2 INTELLIGENCE:")
    print()
    
    # Add project root to path
    project_root = Path('.').resolve()
    sys.path.insert(0, str(project_root))
    
    # Get PC2 agents from startup config
    pc2_config_path = 'pc2_code/config/startup_config.yaml'
    
    if os.path.exists(pc2_config_path):
        with open(pc2_config_path, 'r') as f:
            content = f.read()
        
        # Extract script paths from PC2 config
        script_paths = re.findall(r'script_path:\s*([^,\s]+)', content)
        pc2_agents = [path.strip() for path in script_paths if 'pc2_code/agents/' in path]
    else:
        # Fallback: scan PC2 agents directory directly
        print("📁 PC2 config not found, scanning directory directly...")
        pc2_agents_dir = Path('pc2_code/agents')
        if pc2_agents_dir.exists():
            pc2_agents = []
            for py_file in pc2_agents_dir.rglob('*.py'):
                if py_file.name != '__init__.py':
                    relative_path = str(py_file.relative_to(project_root))
                    pc2_agents.append(relative_path)
        else:
            print("❌ PC2 agents directory not found!")
            return
    
    print(f'🎯 ANALYZING PC2 AGENT FAILURES ({len(pc2_agents)} agents):')
    print()
    
    # Categorize errors by PC2 proven patterns
    pattern_categories = {
        'error_bus_template': [],      # Missing error_bus_template imports
        'path_concatenation': [],      # str / str operations
        'missing_get_pc2_code': [],    # get_pc2_code not defined
        'as_posix_issues': [],         # str.as_posix() calls
        'join_path_missing': [],       # join_path not defined
        'syntax_errors': [],           # Syntax/indentation issues
        'import_errors': [],           # General import issues
        'other': []                    # Uncategorized
    }
    
    failed_count = 0
    successful_count = 0
    
    for agent_path in pc2_agents:
        agent_name = Path(agent_path).stem
        
        # Convert path to module name
        if agent_path.startswith('pc2_code/'):
            module_name = agent_path.replace('/', '.').replace('.py', '')
        else:
            module_name = f'pc2_code.{agent_path.replace("/", ".").replace(".py", "")}'
        
        try:
            # Try to import the agent
            spec = importlib.util.spec_from_file_location(module_name, agent_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            successful_count += 1
            
        except Exception as e:
            failed_count += 1
            error_msg = str(e).lower()
            
            # Categorize by PC2 proven patterns
            if 'error_bus_template' in error_msg:
                pattern_categories['error_bus_template'].append((agent_name, str(e)[:80]))
            elif 'unsupported operand type' in error_msg and ('str' in error_msg or '/' in error_msg):
                pattern_categories['path_concatenation'].append((agent_name, str(e)[:80]))
            elif 'get_pc2_code' in error_msg and 'not defined' in error_msg:
                pattern_categories['missing_get_pc2_code'].append((agent_name, str(e)[:80]))
            elif 'as_posix' in error_msg and ('str' in error_msg or 'attribute' in error_msg):
                pattern_categories['as_posix_issues'].append((agent_name, str(e)[:80]))
            elif 'join_path' in error_msg and 'not defined' in error_msg:
                pattern_categories['join_path_missing'].append((agent_name, str(e)[:80]))
            elif 'syntax' in error_msg or 'indent' in error_msg or 'invalid' in error_msg:
                pattern_categories['syntax_errors'].append((agent_name, str(e)[:80]))
            elif 'import' in error_msg or 'module' in error_msg:
                pattern_categories['import_errors'].append((agent_name, str(e)[:80]))
            else:
                pattern_categories['other'].append((agent_name, str(e)[:80]))
    
    print(f'📊 PC2 FAILURE ANALYSIS RESULTS:')
    print(f'✅ Successful: {successful_count} agents')
    print(f'❌ Failed: {failed_count} agents')
    print(f'📈 Success Rate: {(successful_count/(successful_count+failed_count)*100):.1f}%')
    print()
    
    # Show categorized failures
    for category, agents in pattern_categories.items():
        if agents:
            print(f'🔧 {category.upper().replace("_", " ")}: {len(agents)} agents')
            for name, error in agents[:3]:  # Show first 3
                print(f'   • {name}: {error}...')
            if len(agents) > 3:
                print(f'   ... and {len(agents)-3} more')
            print()
    
    # Calculate fixable agents using proven patterns
    proven_fixable = (
        len(pattern_categories['error_bus_template']) +
        len(pattern_categories['path_concatenation']) +
        len(pattern_categories['missing_get_pc2_code']) +
        len(pattern_categories['as_posix_issues']) +
        len(pattern_categories['join_path_missing'])
    )
    
    print(f'🎯 PROVEN PC2 PATTERNS CAN FIX: {proven_fixable} agents immediately!')
    print(f'🚀 POTENTIAL SUCCESS RATE AFTER FIXES: {((successful_count + proven_fixable)/(successful_count+failed_count)*100):.1f}%')
    
    # Provide specific fix recommendations
    if pattern_categories['error_bus_template']:
        print(f'\n🔧 IMMEDIATE FIX #1: Create pc2_code/agents/error_bus_template.py')
        print(f'   → Will fix {len(pattern_categories["error_bus_template"])} agents instantly')
    
    if pattern_categories['path_concatenation']:
        print(f'\n🔧 IMMEDIATE FIX #2: Convert str paths to Path objects')
        print(f'   → Will fix {len(pattern_categories["path_concatenation"])} agents')
    
    if pattern_categories['missing_get_pc2_code']:
        print(f'\n🔧 IMMEDIATE FIX #3: Add get_pc2_code imports')
        print(f'   → Will fix {len(pattern_categories["missing_get_pc2_code"])} agents')

if __name__ == "__main__":
    analyze_pc2_agents() 