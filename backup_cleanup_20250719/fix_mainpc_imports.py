#!/usr/bin/env python3
"""
Fix MainPC Imports Script
------------------------
This script fixes import path issues in MainPC agents by:
1. Ensuring the correct PYTHONPATH is set up
2. Making sure all agents use utils.config_loader instead of config_parser
3. Checking for duplicate method declarations
4. Standardizing configuration access patterns
5. Verifying relative imports

Usage:
    python fix_mainpc_imports.py
"""

import os
import sys
import re
import json
import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'
AGENT_REPORT_PATH = PROJECT_ROOT / 'analysis_output' / 'agent_report.json'

# Output paths
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
FIXED_FILES_REPORT = OUTPUT_DIR / 'fixed_files_report.json'

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class ImportFixer:
    """Class to fix import issues in agent files."""
    
    def __init__(self):
        self.agent_files: Dict[str, str] = {}  # Map of agent name to file path
        self.fixed_files: List[Dict[str, Any]] = []
        self.issues_found: int = 0
        self.issues_fixed: int = 0
        
    def load_agent_files(self):
        """Load agent files from agent_scanner.py output."""
        if not AGENT_REPORT_PATH.exists():
            logger.error(f"Agent report not found at {AGENT_REPORT_PATH}. Please run agent_scanner.py first.")
            sys.exit(1)
            
        try:
            with open(AGENT_REPORT_PATH, 'r') as f:
                agent_report = json.load(f)
                
            # Extract agent file paths
            for agent_name, agent_data in agent_report.get('agents', {}).items():
                file_path = agent_data.get('file_path', '')
                if file_path:
                    if agent_data.get('source_config') == 'mainpc':
                        full_path = MAIN_PC_CODE / file_path
                    else:
                        full_path = PC2_CODE / file_path
                    
                    if full_path.exists():
                        self.agent_files[agent_name] = str(full_path)
                    else:
                        logger.warning(f"Agent file not found: {full_path}")
                        
            logger.info(f"Loaded {len(self.agent_files)} agent files for fixing.")
            
        except Exception as e:
            logger.error(f"Error loading agent report: {e}")
            sys.exit(1)
    
    def fix_all_agents(self):
        """Fix import issues in all agent files."""
        logger.info("Fixing import issues in all agent files...")
        
        # Load agent files
        self.load_agent_files()
        
        # Fix each agent file
        for agent_name, file_path in self.agent_files.items():
            try:
                logger.info(f"Fixing agent: {agent_name} ({file_path})")
                self._fix_file(Path(file_path), agent_name)
            except Exception as e:
                logger.error(f"Error fixing {file_path}: {e}")
        
        # Generate report
        self._generate_report()
        
        logger.info(f"Fixed {self.issues_fixed} issues in {len(self.fixed_files)} files.")
    
    def _fix_file(self, file_path: Path, agent_name: str):
        """Fix import issues in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            issues_found = 0
            issues_fixed = 0
            fixes_applied = []
            
            # Fix 1: Add PYTHONPATH setup if missing
            if 'import sys' in content and not re.search(r'sys\.path\.insert\(0,', content) and not re.search(r'sys\.path\.append\(', content):
                path_setup = self._generate_path_setup(file_path)
                # Add after imports but before the rest of the code
                import_section_end = self._find_import_section_end(content)
                if import_section_end > 0:
                    content = content[:import_section_end] + "\n" + path_setup + "\n" + content[import_section_end:]
                    issues_found += 1
                    issues_fixed += 1
                    fixes_applied.append("Added PYTHONPATH setup")
            
            # Fix 2: Replace config_parser with config_loader
            if 'config_parser' in content:
                new_content = re.sub(r'from\s+(?:.*\.)?utils\.config_parser\s+import', 'from utils.config_loader import', content)
                if new_content != content:
                    content = new_content
                    issues_found += 1
                    issues_fixed += 1
                    fixes_applied.append("Replaced config_parser with config_loader")
            
            # Fix 3: Check for duplicate method declarations
            duplicate_methods = self._find_duplicate_methods(content)
            if duplicate_methods:
                logger.warning(f"Found duplicate methods in {file_path}: {', '.join(duplicate_methods)}")
                issues_found += len(duplicate_methods)
                fixes_applied.append(f"Found duplicate methods: {', '.join(duplicate_methods)}")
            
            # Fix 4: Standardize configuration access patterns
            if 'config' in content:
                # Replace direct dictionary access with get() method
                new_content = re.sub(r'config\[([\'"][\w_]+[\'"]+)\]', r'config.get(\1)', content)
                if new_content != content:
                    content = new_content
                    issues_found += 1
                    issues_fixed += 1
                    fixes_applied.append("Standardized config access patterns")
            
            # Fix 5: Fix relative imports
            if 'from .' in content or 'from ..' in content:
                new_content = self._fix_relative_imports(content, file_path)
                if new_content != content:
                    content = new_content
                    issues_found += 1
                    issues_fixed += 1
                    fixes_applied.append("Fixed relative imports")
            
            # Save changes if any were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.fixed_files.append({
                    'agent_name': agent_name,
                    'file_path': str(file_path),
                    'issues_found': issues_found,
                    'issues_fixed': issues_fixed,
                    'fixes_applied': fixes_applied
                })
                
                self.issues_found += issues_found
                self.issues_fixed += issues_fixed
                
                logger.info(f"Fixed {issues_fixed} issues in {file_path}")
            else:
                logger.info(f"No issues to fix in {file_path}")
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    def _generate_path_setup(self, file_path: Path) -> str:
        """Generate PYTHONPATH setup code based on file location."""
        relative_path = file_path.relative_to(PROJECT_ROOT)
        depth = len(relative_path.parts) - 1  # -1 for the filename itself
        
        if 'main_pc_code' in str(file_path):
            return """
# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())
"""
        elif 'pc2_code' in str(file_path):
            return """
# Add the project's pc2_code directory to the Python path
import sys
import os
from pathlib import Path
PC2_CODE_DIR = Path(__file__).resolve().parent.parent
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())
"""
        else:
            return """
# Add the project root to the Python path
import sys
import os
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if PROJECT_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, PROJECT_ROOT.as_posix())
"""
    
    def _find_import_section_end(self, content: str) -> int:
        """Find the end of the import section in the file."""
        lines = content.split('\n')
        in_import_section = False
        last_import_line = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                in_import_section = True
                last_import_line = i
            elif in_import_section and stripped and not stripped.startswith('#'):
                # Found a non-empty, non-comment line after imports
                return lines[last_import_line].find('import') + len(lines[last_import_line])
        
        # If we didn't find a clear end, return the end of the last import line
        if last_import_line > 0:
            return len('\n'.join(lines[:last_import_line + 1]))
        
        # Default to the beginning of the file
        return 0
    
    def _find_duplicate_methods(self, content: str) -> List[str]:
        """Find duplicate method declarations in a file."""
        try:
            tree = ast.parse(content)
            method_names = []
            duplicate_methods = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if item.name in class_methods:
                                duplicate_methods.append(f"{node.name}.{item.name}")
                            else:
                                class_methods.append(item.name)
            
            return duplicate_methods
        except Exception as e:
            logger.error(f"Error parsing AST: {e}")
            return []
    
    def _fix_relative_imports(self, content: str, file_path: Path) -> str:
        """Fix relative imports in a file."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if line.strip().startswith('from .') and 'import' in line:
                # Get the relative import path
                match = re.match(r'from\s+(\.+)([^\s]*)\s+import', line)
                if match:
                    dots = match.group(1)  # The dots (., .., ...)
                    module_path = match.group(2)  # The rest of the import path
                    
                    # Calculate the absolute import path
                    if 'main_pc_code' in str(file_path):
                        base_path = 'main_pc_code'
                    elif 'pc2_code' in str(file_path):
                        base_path = 'pc2_code'
                    else:
                        base_path = ''
                    
                    # Get the directory of the current file relative to the base
                    relative_dir = os.path.dirname(str(file_path.relative_to(PROJECT_ROOT)))
                    
                    # Remove the base path from the relative directory
                    if base_path and relative_dir.startswith(base_path):
                        relative_dir = relative_dir[len(base_path) + 1:]  # +1 for the slash
                    
                    # Split into parts
                    parts = relative_dir.split(os.sep)
                    
                    # Go up based on the number of dots
                    up_levels = len(dots) - 1
                    if up_levels >= len(parts):
                        # Can't go up that many levels, leave as is
                        fixed_lines.append(line)
                        continue
                    
                    # Calculate the new import path
                    new_path = '.'.join(parts[:-up_levels]) if up_levels > 0 else '.'.join(parts)
                    if module_path:
                        if new_path:
                            new_path += '.' + module_path
                        else:
                            new_path = module_path
                    
                    # Replace the relative import with an absolute import
                    fixed_line = f"from {new_path} import" + line.split('import', 1)[1]
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _generate_report(self):
        """Generate a report of the fixed files."""
        report = {
            'total_files_processed': len(self.agent_files),
            'total_files_fixed': len(self.fixed_files),
            'total_issues_found': self.issues_found,
            'total_issues_fixed': self.issues_fixed,
            'fixed_files': self.fixed_files
        }
        
        with open(FIXED_FILES_REPORT, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {FIXED_FILES_REPORT}")

def main():
    """Main function."""
    print("=== Fix MainPC Imports ===")
    
    fixer = ImportFixer()
    fixer.fix_all_agents()
    
    print("\nImport fixing complete!")

if __name__ == "__main__":
    main() 