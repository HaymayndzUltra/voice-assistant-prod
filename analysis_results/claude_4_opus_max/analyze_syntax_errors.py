#!/usr/bin/env python3
"""
Analyze and categorize syntax errors in the MainPC codebase.
This script will find all incomplete self. statements and other syntax issues.
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

class SyntaxErrorAnalyzer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.errors = defaultdict(list)
        self.incomplete_self_pattern = re.compile(r'^\s*self\.\s*$', re.MULTILINE)
        self.context_lines = 5  # Lines of context to show
        
    def analyze_file(self, file_path: Path) -> Dict[str, List[Tuple[int, str, str]]]:
        """Analyze a single Python file for syntax errors."""
        errors = defaultdict(list)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            errors['file_read_error'].append((0, str(e), ""))
            return errors
            
        # Check for incomplete self. statements
        for match in self.incomplete_self_pattern.finditer(content):
            line_num = content[:match.start()].count('\n') + 1
            context = self._get_context(lines, line_num - 1)
            errors['incomplete_self'].append((line_num, "self.", context))
            
        # Try to parse the file to find other syntax errors
        try:
            ast.parse(content)
        except SyntaxError as e:
            context = self._get_context(lines, e.lineno - 1 if e.lineno else 0)
            errors['syntax_error'].append((e.lineno or 0, str(e), context))
            
        # Check for other common patterns
        self._check_cleanup_methods(lines, errors)
        self._check_zmq_context_usage(lines, errors)
        
        return errors
    
    def _get_context(self, lines: List[str], line_index: int) -> str:
        """Get context around a specific line."""
        start = max(0, line_index - self.context_lines)
        end = min(len(lines), line_index + self.context_lines + 1)
        context_lines = []
        
        for i in range(start, end):
            prefix = ">>> " if i == line_index else "    "
            context_lines.append(f"{i+1:4d}: {prefix}{lines[i]}")
            
        return "\n".join(context_lines)
    
    def _check_cleanup_methods(self, lines: List[str], errors: Dict):
        """Check for incomplete cleanup methods."""
        in_cleanup = False
        cleanup_start = 0
        
        for i, line in enumerate(lines):
            if 'def cleanup(' in line or 'def _cleanup(' in line:
                in_cleanup = True
                cleanup_start = i
            elif in_cleanup and (line.strip().startswith('def ') or 
                                (i == len(lines) - 1)):
                # Check if cleanup method seems incomplete
                method_lines = lines[cleanup_start:i]
                method_text = '\n'.join(method_lines)
                if 'self.' in method_text and method_text.strip().endswith('self.'):
                    errors['incomplete_cleanup'].append(
                        (cleanup_start + 1, "Incomplete cleanup method", 
                         self._get_context(lines, i-1))
                    )
                in_cleanup = False
    
    def _check_zmq_context_usage(self, lines: List[str], errors: Dict):
        """Check for ZMQ context termination issues."""
        for i, line in enumerate(lines):
            if 'self.context.term()' in line or 'context.term()' in line:
                # Check if it's incomplete
                if line.strip() == 'self.' or line.strip().endswith('self.'):
                    errors['incomplete_zmq_term'].append(
                        (i + 1, "Incomplete ZMQ context termination",
                         self._get_context(lines, i))
                    )
    
    def analyze_directory(self, directory: Path) -> Dict[str, Dict]:
        """Analyze all Python files in a directory recursively."""
        all_errors = defaultdict(lambda: defaultdict(list))
        
        for py_file in directory.rglob("*.py"):
            if '__pycache__' in str(py_file) or '_trash_' in str(py_file):
                continue
                
            relative_path = py_file.relative_to(self.base_path)
            file_errors = self.analyze_file(py_file)
            
            if file_errors:
                for error_type, error_list in file_errors.items():
                    all_errors[error_type][str(relative_path)] = error_list
                    
        return all_errors
    
    def generate_report(self) -> str:
        """Generate a comprehensive error report."""
        report = []
        report.append("=" * 80)
        report.append("MAINPC CODEBASE SYNTAX ERROR ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Analyze MainPC agents
        mainpc_errors = self.analyze_directory(self.base_path / "main_pc_code")
        
        # Summary
        total_errors = sum(
            len(files) 
            for error_type in mainpc_errors.values() 
            for files in error_type.values()
        )
        
        report.append(f"Total files with errors: {total_errors}")
        report.append("")
        
        # Detailed breakdown by error type
        for error_type, files_dict in mainpc_errors.items():
            report.append(f"\n{error_type.upper().replace('_', ' ')} ({len(files_dict)} files):")
            report.append("-" * 60)
            
            for file_path, errors in sorted(files_dict.items()):
                report.append(f"\n{file_path}:")
                for line_num, error_text, context in errors:
                    report.append(f"  Line {line_num}: {error_text}")
                    if context:
                        report.append("  Context:")
                        for ctx_line in context.split('\n'):
                            report.append(f"    {ctx_line}")
                    report.append("")
        
        # Generate fix suggestions
        report.append("\n" + "=" * 80)
        report.append("FIX SUGGESTIONS")
        report.append("=" * 80)
        
        if 'incomplete_self' in mainpc_errors:
            report.append("\nINCOMPLETE SELF STATEMENTS:")
            report.append("Most common fix: self.context.term()")
            report.append("Pattern found in cleanup/termination methods")
            
        return "\n".join(report)
    
    def generate_fix_script(self) -> str:
        """Generate a script to automatically fix common errors."""
        script = []
        script.append("#!/usr/bin/env python3")
        script.append('"""Auto-generated script to fix common syntax errors."""')
        script.append("")
        script.append("import re")
        script.append("from pathlib import Path")
        script.append("")
        
        # Add fix functions
        script.append("def fix_incomplete_self_context_term(content: str) -> str:")
        script.append('    """Fix incomplete self. statements that should be self.context.term()."""')
        script.append("    # Pattern to find incomplete self. in cleanup contexts")
        script.append("    pattern = r'(\\s+)self\\.\\s*$'")
        script.append("    ")
        script.append("    # Check if this is in a cleanup/termination context")
        script.append("    lines = content.splitlines()")
        script.append("    fixed_lines = []")
        script.append("    ")
        script.append("    for i, line in enumerate(lines):")
        script.append("        if line.strip() == 'self.':")
        script.append("            # Look for context clues in surrounding lines")
        script.append("            context_start = max(0, i - 10)")
        script.append("            context = '\\n'.join(lines[context_start:i+1])")
        script.append("            ")
        script.append("            if 'context' in context and ('cleanup' in context.lower() or 'close' in context.lower()):")
        script.append("                indent = len(line) - len(line.lstrip())")
        script.append("                fixed_lines.append(' ' * indent + 'self.context.term()')")
        script.append("            else:")
        script.append("                fixed_lines.append(line)  # Keep as is for manual review")
        script.append("        else:")
        script.append("            fixed_lines.append(line)")
        script.append("    ")
        script.append("    return '\\n'.join(fixed_lines)")
        script.append("")
        
        return "\n".join(script)


def main():
    """Main function to run the analysis."""
    analyzer = SyntaxErrorAnalyzer(Path("/workspace"))
    
    print("Analyzing MainPC codebase for syntax errors...")
    report = analyzer.generate_report()
    
    # Save report
    report_path = Path("/workspace/syntax_error_report.txt")
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    
    # Generate fix script
    fix_script = analyzer.generate_fix_script()
    fix_script_path = Path("/workspace/fix_syntax_errors.py")
    with open(fix_script_path, 'w') as f:
        f.write(fix_script)
    print(f"Fix script saved to: {fix_script_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(report.split("FIX SUGGESTIONS")[0])


if __name__ == "__main__":
    main()