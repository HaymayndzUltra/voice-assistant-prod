#!/usr/bin/env python3
"""
Fix FORMAINPC agents and observability hub backup file for compliance
"""
import pathlib
import re
import ast
import json
from typing import Set, Dict, List

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Files to fix
FILES_TO_FIX = [
    'main_pc_code/FORMAINPC/chain_of_thought_agent.py',
    'main_pc_code/FORMAINPC/cognitive_model_agent.py',
    'main_pc_code/FORMAINPC/consolidated_translator_simple.py',
    'main_pc_code/FORMAINPC/got_tot_agent.py',
    'main_pc_code/FORMAINPC/learning_adjuster_agent.py',
    'main_pc_code/FORMAINPC/local_fine_tuner_agent.py',
    'main_pc_code/FORMAINPC/nllb_adapter.py',
    'main_pc_code/FORMAINPC/self_training_orchestrator.py',
    'main_pc_code/FORMAINPC/tiny_llama_service_enhanced.py',
    'main_pc_code/FORMAINPC/ConsolidatedTranslator.py',
    'phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py'
]

def fix_forbidden_patterns(file_path: pathlib.Path) -> bool:
    """Remove forbidden patterns from a file"""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    original_content = content
    
    # Remove sys.path.insert lines
    content = re.sub(r'sys\.path\.insert.*?\n', '', content)
    
    # Replace logging.basicConfig with proper log_setup
    if "logging.basicConfig" in content:
        # Add log_setup import if not present
        if "from common.utils.log_setup import configure_logging" not in content:
            lines = content.split('\n')
            import_line_idx = -1
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_line_idx = i
            
            if import_line_idx >= 0:
                lines.insert(import_line_idx + 1, "from common.utils.log_setup import configure_logging")
                content = '\n'.join(lines)
        
        # Replace logging.basicConfig calls
        content = re.sub(
            r'logging\.basicConfig\([^)]*\)',
            'logger = configure_logging(__name__)',
            content
        )
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False

def check_missing_imports(file_path: pathlib.Path) -> List[str]:
    """Check which required imports are missing"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []
    
    # Get all imports
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    
    missing = []
    
    # Required imports
    required_imports = {
        "common.utils.env_standardizer": "from common.utils.env_standardizer import get_env",
        "common.core.base_agent": "from common.core.base_agent import BaseAgent", 
        "common.utils.log_setup": "from common.utils.log_setup import configure_logging",
    }
    
    for module, import_stmt in required_imports.items():
        if module not in imports:
            missing.append(import_stmt)
    
    # Error publisher (main PC for these files)
    if "main_pc_code.agents.error_publisher" not in imports:
        missing.append("from main_pc_code.agents.error_publisher import ErrorPublisher")
    
    return missing

def add_missing_imports(file_path: pathlib.Path, missing_imports: List[str]) -> bool:
    """Add missing imports to a file"""
    if not missing_imports:
        return False
        
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    lines = content.split('\n')
    
    # Find insertion point
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() and not line.startswith('#') and insert_idx > 0:
            break
    
    # Insert missing imports
    for import_stmt in missing_imports:
        lines.insert(insert_idx, import_stmt)
        insert_idx += 1
    
    file_path.write_text('\n'.join(lines), encoding='utf-8')
    return True

def fix_syntax_errors(file_path: pathlib.Path) -> bool:
    """Try to fix common syntax errors caused by our regex replacements"""
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    original_content = content
    
    # Fix incomplete regex replacements that might have created syntax errors
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix logger = configure_logging(__name__) syntax issues
        if 'logger = configure_logging(__name__)' in line:
            # Remove any trailing corrupted text
            if re.search(r'logger = configure_logging\(__name__\).*[^\w\s\(\)]', line):
                line = re.sub(r'(logger = configure_logging\(__name__\)).*', r'\1', line)
        
        # Fix unterminated strings around our replacements
        if line.count('"') % 2 == 1 and 'configure_logging' in line:
            line = line.replace('"', '')
        
        # Fix hanging quotes or brackets
        if line.strip().endswith('"""') and not line.strip().startswith('"""'):
            line = line.replace('"""', '')
        
        fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    if fixed_content != original_content:
        file_path.write_text(fixed_content, encoding='utf-8')
        return True
    return False

def fix_file(file_path_str: str) -> Dict:
    """Fix a specific file"""
    print(f"\n🔧 Fixing file: {file_path_str}")
    
    file_path = ROOT / file_path_str
    
    result = {
        "file": file_path_str,
        "exists": file_path.exists(),
        "patterns_fixed": False,
        "syntax_fixed": False,
        "imports_added": False,
        "missing_imports": []
    }
    
    if not file_path.exists():
        print(f"  ❌ File not found: {file_path}")
        return result
    
    # First fix syntax errors
    syntax_fixed = fix_syntax_errors(file_path)
    result["syntax_fixed"] = syntax_fixed
    if syntax_fixed:
        print(f"  ✅ Fixed syntax issues")
    
    # Fix forbidden patterns
    patterns_fixed = fix_forbidden_patterns(file_path)
    result["patterns_fixed"] = patterns_fixed
    if patterns_fixed:
        print(f"  ✅ Fixed forbidden patterns")
    
    # Check and add missing imports
    missing_imports = check_missing_imports(file_path)
    result["missing_imports"] = missing_imports
    
    if missing_imports:
        imports_added = add_missing_imports(file_path, missing_imports)
        result["imports_added"] = imports_added
        print(f"  ✅ Added {len(missing_imports)} missing imports")
    
    if not patterns_fixed and not missing_imports and not syntax_fixed:
        print(f"  ✨ Already compliant")
    
    return result

def main():
    """Main function to fix FORMAINPC and observability files"""
    print("🎯 FIXING FORMAINPC & OBSERVABILITY HUB FILES")
    print(f"📋 Processing {len(FILES_TO_FIX)} files")
    print("=" * 60)
    
    results = []
    fixed_count = 0
    compliant_count = 0
    missing_count = 0
    
    for file_path_str in FILES_TO_FIX:
        result = fix_file(file_path_str)
        results.append(result)
        
        if not result["exists"]:
            missing_count += 1
        elif result["patterns_fixed"] or result["imports_added"] or result["syntax_fixed"]:
            fixed_count += 1
        else:
            compliant_count += 1
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print(f"✅ Fixed: {fixed_count} files")
    print(f"✨ Already compliant: {compliant_count} files") 
    print(f"❌ Missing files: {missing_count} files")
    print(f"📦 Total processed: {len(FILES_TO_FIX)} files")
    
    # Save detailed results
    results_file = ROOT / "scripts" / "formainpc_observability_fix_results.json"
    with results_file.open('w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print("\n🎉 FORMAINPC & OBSERVABILITY FIX COMPLETE!")

if __name__ == "__main__":
    main()