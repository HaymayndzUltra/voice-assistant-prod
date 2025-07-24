#!/usr/bin/env python3
"""
Fix remaining syntax errors that were missed by the first fix script.
"""

import re
import shutil
from pathlib import Path
import argparse

class RemainingErrorFixer:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.files_fixed = 0
        
    def fix_file(self, file_path: Path, error_type: str, line_num: int = None) -> bool:
        """Fix specific error types in files."""
        
        try:
            # Backup file
            if not self.dry_run:
                backup_path = file_path.with_suffix('.bak2')
                if not backup_path.exists():
                    shutil.copy2(file_path, backup_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            modified = False
            
            # Fix based on error type
            if "unmatched ')'" in error_type:
                # Fix extra parentheses
                patterns = [
                    (r'sys\.path\.insert\(0, os\.path\.abspath\(join_path\("main_pc_code", "\.\."\)\)\)\)', 
                     'sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))'),
                    (r'sys\.path\.insert\(0, os\.path\.abspath\(os\.path\.join\(__file__, "\.\."\)\)\)\)',
                     'sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..")))'),
                    (r'get_zmq_connection_string\((\d+), "localhost"\)\)\)',
                     r'get_zmq_connection_string(\1, "localhost"))')
                ]
                
                for pattern, replacement in patterns:
                    if re.search(pattern, content):
                        content = re.sub(pattern, replacement, content)
                        modified = True
                        print(f"  Fixed unmatched parenthesis pattern")
                        
            elif "expected an indented block" in error_type:
                # Add pass statements where needed
                if line_num and line_num > 0:
                    # Check if we need to add a pass statement
                    if line_num <= len(lines):
                        prev_line = lines[line_num - 2] if line_num > 1 else ""
                        curr_line = lines[line_num - 1] if line_num - 1 < len(lines) else ""
                        
                        # Check if previous line ends with : and current line is not indented
                        if prev_line.strip().endswith(':') and (not curr_line or not curr_line.startswith(' ')):
                            # Insert pass statement
                            indent = len(prev_line) - len(prev_line.lstrip()) + 4
                            lines.insert(line_num - 1, ' ' * indent + 'pass')
                            content = '\n'.join(lines)
                            modified = True
                            print(f"  Added 'pass' statement at line {line_num}")
                            
            elif "unexpected indent" in error_type:
                # Fix indentation issues
                if line_num and line_num > 0 and line_num <= len(lines):
                    # Try to fix the indentation
                    problem_line = lines[line_num - 1]
                    if problem_line.strip():  # Not empty
                        # Find expected indentation from previous non-empty line
                        expected_indent = 0
                        for i in range(line_num - 2, -1, -1):
                            if lines[i].strip():
                                expected_indent = len(lines[i]) - len(lines[i].lstrip())
                                if lines[i].strip().endswith(':'):
                                    expected_indent += 4
                                break
                        
                        # Fix the line
                        lines[line_num - 1] = ' ' * expected_indent + problem_line.lstrip()
                        content = '\n'.join(lines)
                        modified = True
                        print(f"  Fixed indentation at line {line_num}")
                        
            elif "expected 'except' or 'finally' block" in error_type:
                # Add except block after try
                if line_num and line_num > 0:
                    # Find the try block
                    for i in range(line_num - 2, max(0, line_num - 20), -1):
                        if lines[i].strip().startswith('try:'):
                            indent = len(lines[i]) - len(lines[i].lstrip())
                            # Insert except block
                            lines.insert(line_num - 1, ' ' * indent + 'except Exception as e:')
                            lines.insert(line_num, ' ' * (indent + 4) + 'pass')
                            content = '\n'.join(lines)
                            modified = True
                            print(f"  Added except block at line {line_num}")
                            break
                            
            elif "invalid syntax" in error_type:
                # Handle specific invalid syntax cases
                if file_path.name == "advanced_suggestion_system.py":
                    # Fix specific issue in this file
                    content = re.sub(r'from\s+\.\s+import', 'from . import', content)
                    modified = True
                    
            # Write fixed content
            if modified and not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.files_fixed += 1
                self.fixes_applied += 1
                
            return modified
            
        except Exception as e:
            print(f"  Error fixing {file_path}: {e}")
            return False
    
    def process_errors(self, error_list: list):
        """Process a list of syntax errors."""
        
        for error in error_list:
            # Parse error format: path:line: error message
            parts = error.split(':', 2)
            if len(parts) >= 3:
                file_path = Path("/workspace") / parts[0]
                try:
                    line_num = int(parts[1])
                    error_msg = parts[2].strip()
                    
                    if file_path.exists():
                        print(f"\nFixing {file_path.name} (line {line_num}): {error_msg}")
                        self.fix_file(file_path, error_msg, line_num)
                except ValueError:
                    pass


def main():
    parser = argparse.ArgumentParser(description='Fix remaining syntax errors')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be fixed without making changes')
    
    args = parser.parse_args()
    
    # List of known errors from validation
    errors = [
        "main_pc_code/agents/chitchat_agent.py:474: expected an indented block after 'if' statement on line 472",
        "main_pc_code/agents/vram_optimizer_agent.py:1520: unexpected indent",
        "main_pc_code/agents/unified_system_agent.py:717: expected an indented block after 'for' statement on line 715",
        "main_pc_code/agents/predictive_health_monitor.py:1267: expected an indented block after 'try' statement on line 1266",
        "main_pc_code/agents/request_coordinator.py:350: expected an indented block after 'if' statement on line 349",
        "main_pc_code/agents/streaming_interrupt_handler.py:344: unexpected indent",
        "main_pc_code/agents/streaming_tts_agent.py:733: unexpected indent",
        "main_pc_code/agents/model_manager_agent.py:3988: expected an indented block after 'try' statement on line 3986",
    ]
    
    # Also fix specific files with known patterns
    specific_fixes = [
        ("main_pc_code/agents/vision_capture_agent.py", "unmatched ')'"),
        ("main_pc_code/agents/vram_optimizer_agent.py", "unmatched ')'"),
        ("main_pc_code/scripts/auto_fix_health_checks.py", "expected an indented block"),
        ("main_pc_code/scripts/fix_agent_health_issues.py", "expected 'except' or 'finally' block"),
        ("main_pc_code/scripts/validate_agents.py", "expected an indented block"),
    ]
    
    fixer = RemainingErrorFixer(dry_run=args.dry_run)
    
    print("=" * 80)
    print("FIXING REMAINING SYNTAX ERRORS")
    print("=" * 80)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")
    
    # Process known errors
    fixer.process_errors(errors)
    
    # Process specific files
    for file_path, error_type in specific_fixes:
        full_path = Path("/workspace") / file_path
        if full_path.exists():
            print(f"\nFixing {full_path.name}: {error_type}")
            fixer.fix_file(full_path, error_type)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total fixes applied: {fixer.fixes_applied}")
    print(f"Total files fixed: {fixer.files_fixed}")
    
    if args.dry_run:
        print("\nTo apply these fixes, run without --dry-run flag")
    else:
        print("\nBackup files created with .bak2 extension")
        print("Run validation again to check remaining issues")


if __name__ == "__main__":
    main()