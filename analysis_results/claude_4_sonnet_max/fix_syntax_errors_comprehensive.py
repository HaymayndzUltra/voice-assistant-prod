#!/usr/bin/env python3
"""
🚨 COMPREHENSIVE AI SYSTEM SYNTAX ERROR FIX SCRIPT
=================================================

This script systematically fixes critical syntax errors across the MainPC codebase:
1. Incomplete self. statements
2. Missing cleanup methods
3. Duplicated main blocks
4. Import chain issues

Usage: python fix_syntax_errors_comprehensive.py
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class SyntaxErrorFixer:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.mainpc_agents_dir = self.project_root / "main_pc_code" / "agents"
        self.formainpc_dir = self.project_root / "main_pc_code" / "FORMAINPC"
        self.fixes_applied = []
        self.errors_found = []
        
    def scan_for_syntax_errors(self) -> Dict[str, List[str]]:
        """Scan all Python files for syntax errors."""
        print("🔍 Scanning for syntax errors...")
        
        errors = {}
        
        # Scan main_pc_code/agents/
        if self.mainpc_agents_dir.exists():
            for py_file in self.mainpc_agents_dir.glob("*.py"):
                file_errors = self._scan_file(py_file)
                if file_errors:
                    errors[str(py_file)] = file_errors
        
        # Scan main_pc_code/FORMAINPC/
        if self.formainpc_dir.exists():
            for py_file in self.formainpc_dir.glob("*.py"):
                file_errors = self._scan_file(py_file)
                if file_errors:
                    errors[str(py_file)] = file_errors
                    
        return errors
    
    def _scan_file(self, file_path: Path) -> List[str]:
        """Scan a single file for syntax errors."""
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for incomplete self. statements
                if re.match(r'^\s*self\.\s*$', line):
                    errors.append(f"Line {i}: Incomplete self. statement")
                
                # Check for incomplete method calls
                if re.match(r'^\s*self\.\w+_\s*$', line):
                    errors.append(f"Line {i}: Incomplete method call: {line_stripped}")
                    
                # Check for duplicate main blocks
                if line_stripped.startswith('if __name__ == "__main__":'):
                    # Count how many main blocks exist
                    main_count = sum(1 for l in lines if l.strip().startswith('if __name__ == "__main__":'))
                    if main_count > 1:
                        errors.append(f"Line {i}: Duplicate main block detected ({main_count} total)")
                        
        except Exception as e:
            errors.append(f"Error reading file: {e}")
            
        return errors
    
    def fix_incomplete_self_statements(self, file_path: Path) -> int:
        """Fix incomplete self. statements in a file."""
        print(f"🔧 Fixing incomplete self. statements in {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            fixes_count = 0
            
            # Common patterns for incomplete self. statements
            patterns_fixes = [
                # self.socket -> self.socket.close()
                (r'(\s+)self\.socket\s*$', r'\1# self.socket.close()  # Fixed incomplete statement'),
                # self.context -> self.context.term()
                (r'(\s+)self\.context\s*$', r'\1# self.context.term()  # Fixed incomplete statement'),
                # self.emotion_sub_ -> self.emotion_sub_socket.close()
                (r'(\s+)self\.emotion_sub_\s*$', r'\1# self.emotion_sub_socket.close()  # Fixed incomplete statement'),
                # self.tts_ -> self.tts_socket.close()
                (r'(\s+)self\.tts_\s*$', r'\1# self.tts_socket.close()  # Fixed incomplete statement'),
                # General incomplete self. -> comment it out
                (r'(\s+)self\.\s*$', r'\1# self.  # Fixed incomplete statement'),
            ]
            
            for pattern, replacement in patterns_fixes:
                new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                if new_content != content:
                    fixes_count += content.count(pattern.replace(r'(\s+)', '').replace(r'\s*$', ''))
                    content = new_content
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixes_applied.append(f"Fixed {fixes_count} incomplete self. statements in {file_path.name}")
                return fixes_count
                
        except Exception as e:
            print(f"❌ Error fixing {file_path}: {e}")
            self.errors_found.append(f"Error fixing {file_path}: {e}")
            
        return 0
    
    def fix_duplicate_main_blocks(self, file_path: Path) -> int:
        """Remove duplicate main blocks, keeping only the last one."""
        print(f"🔧 Fixing duplicate main blocks in {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Find all main block start indices
            main_indices = []
            for i, line in enumerate(lines):
                if line.strip().startswith('if __name__ == "__main__":'):
                    main_indices.append(i)
            
            if len(main_indices) <= 1:
                return 0  # No duplicates
                
            # Keep only the last main block
            new_lines = lines[:main_indices[0]]  # Everything before first main
            
            # Add the last main block
            last_main_start = main_indices[-1]
            new_lines.extend(lines[last_main_start:])
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            fixes_count = len(main_indices) - 1
            self.fixes_applied.append(f"Removed {fixes_count} duplicate main blocks in {file_path.name}")
            return fixes_count
            
        except Exception as e:
            print(f"❌ Error fixing duplicate mains in {file_path}: {e}")
            self.errors_found.append(f"Error fixing duplicate mains in {file_path}: {e}")
            
        return 0
    
    def fix_missing_cleanup_methods(self, file_path: Path) -> int:
        """Add proper cleanup methods if missing."""
        print(f"🔧 Adding cleanup methods to {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if cleanup method exists
            if 'def cleanup(self):' in content:
                return 0  # Already has cleanup
                
            # Find class definition
            class_match = re.search(r'class\s+(\w+)\s*\([^)]*\):', content)
            if not class_match:
                return 0  # No class found
                
            class_name = class_match.group(1)
            
            # Add cleanup method before the last main block
            cleanup_method = f'''
    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            self.running = False
            
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            if hasattr(self, 'context') and self.context:
                self.context.term()
            if hasattr(self, 'health_socket') and self.health_socket:
                self.health_socket.close()
            if hasattr(self, 'health_context') and self.health_context:
                self.health_context.term()
                
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {{e}}")
'''
            
            # Find insertion point (before last main block or at end)
            main_match = list(re.finditer(r'\nif __name__ == "__main__":', content))
            if main_match:
                insert_pos = main_match[-1].start()
                content = content[:insert_pos] + cleanup_method + content[insert_pos:]
            else:
                content += cleanup_method
                
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.fixes_applied.append(f"Added cleanup method to {file_path.name}")
            return 1
            
        except Exception as e:
            print(f"❌ Error adding cleanup to {file_path}: {e}")
            self.errors_found.append(f"Error adding cleanup to {file_path}: {e}")
            
        return 0
    
    def fix_import_errors(self, file_path: Path) -> int:
        """Fix common import chain issues."""
        print(f"🔧 Fixing imports in {file_path.name}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            fixes_count = 0
            
            # Common import fixes
            import_fixes = [
                # Add missing logger import if logger is used but not imported
                (r'^(?!.*import logging)(?=.*logger\.)', 
                 'import logging\nimport time\nimport zmq\nimport json\nfrom datetime import datetime\n'),
                # Fix BaseAgent import
                (r'from.*base_agent.*import.*BaseAgent', 
                 'from common.core.base_agent import BaseAgent'),
            ]
            
            # Check if logger is used but not imported
            if 'logger.' in content and 'import logging' not in content and 'from.*logging' not in content:
                # Add logging imports at the top
                lines = content.split('\n')
                import_index = 0
                
                # Find where to insert imports (after docstring/comments, before first code)
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""') and not line.strip().startswith("'''"):
                        import_index = i
                        break
                
                missing_imports = [
                    'import logging',
                    'import time', 
                    'import zmq',
                    'import json',
                    'from datetime import datetime'
                ]
                
                for imp in missing_imports:
                    if imp not in content:
                        lines.insert(import_index, imp)
                        import_index += 1
                        fixes_count += 1
                
                content = '\n'.join(lines)
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                if fixes_count > 0:
                    self.fixes_applied.append(f"Fixed {fixes_count} import issues in {file_path.name}")
                return fixes_count
                
        except Exception as e:
            print(f"❌ Error fixing imports in {file_path}: {e}")
            self.errors_found.append(f"Error fixing imports in {file_path}: {e}")
            
        return 0
    
    def run_comprehensive_fix(self):
        """Run comprehensive syntax error fixes."""
        print("🚀 Starting comprehensive syntax error fix...")
        print("=" * 60)
        
        # First, scan for all errors
        errors = self.scan_for_syntax_errors()
        
        print(f"📊 Found syntax errors in {len(errors)} files:")
        for file_path, file_errors in errors.items():
            print(f"  📁 {Path(file_path).name}: {len(file_errors)} errors")
            for error in file_errors[:3]:  # Show first 3 errors
                print(f"    ⚠️  {error}")
            if len(file_errors) > 3:
                print(f"    ... and {len(file_errors) - 3} more")
        
        print("\n🔧 Applying fixes...")
        print("=" * 40)
        
        total_fixes = 0
        
        # Fix each file
        for file_path_str in errors.keys():
            file_path = Path(file_path_str)
            if not file_path.exists():
                continue
                
            print(f"\n📝 Processing {file_path.name}...")
            
            # Apply different types of fixes
            total_fixes += self.fix_incomplete_self_statements(file_path)
            total_fixes += self.fix_duplicate_main_blocks(file_path)
            total_fixes += self.fix_missing_cleanup_methods(file_path)
            total_fixes += self.fix_import_errors(file_path)
        
        # Summary
        print("\n" + "=" * 60)
        print("📈 FIX SUMMARY")
        print("=" * 60)
        print(f"✅ Total fixes applied: {total_fixes}")
        print(f"📁 Files processed: {len(errors)}")
        print(f"✨ Successful fixes: {len(self.fixes_applied)}")
        print(f"❌ Errors encountered: {len(self.errors_found)}")
        
        if self.fixes_applied:
            print("\n🎉 FIXES APPLIED:")
            for fix in self.fixes_applied:
                print(f"  ✅ {fix}")
        
        if self.errors_found:
            print("\n⚠️  ERRORS ENCOUNTERED:")
            for error in self.errors_found:
                print(f"  ❌ {error}")
        
        print("\n🏁 Comprehensive syntax fix completed!")
        return total_fixes

if __name__ == "__main__":
    # Run the comprehensive fix
    fixer = SyntaxErrorFixer()
    total_fixes = fixer.run_comprehensive_fix()
    
    if total_fixes > 0:
        print(f"\n🎊 SUCCESS: Applied {total_fixes} fixes to the codebase!")
        print("📋 Next steps:")
        print("  1. Run syntax validation: python -m py_compile <fixed_files>")
        print("  2. Test core services startup")
        print("  3. Verify health checks are working")
    else:
        print("\n📋 No syntax errors found or all files already clean!")