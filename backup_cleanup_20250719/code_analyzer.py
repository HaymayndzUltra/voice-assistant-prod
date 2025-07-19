#!/usr/bin/env python3
"""
Code Analyzer
------------
Analyzes Python files of agents defined in startup_config.yaml to detect common patterns and anti-patterns,
identify potential bugs and performance issues, and generate optimization recommendations.
Uses the output from agent_scanner.py to determine which files to analyze.
"""

import os
import sys
import ast
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'

# Output paths
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
AGENT_REPORT_PATH = OUTPUT_DIR / 'agent_report.json'
REPORT_OUTPUT = OUTPUT_DIR / 'code_analysis_report.json'
ISSUES_OUTPUT = OUTPUT_DIR / 'code_issues.json'
RECOMMENDATIONS_OUTPUT = OUTPUT_DIR / 'optimization_recommendations.json'

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Constants
MAX_COMPLEXITY = 10  # Maximum acceptable cyclomatic complexity
MAX_LINE_LENGTH = 100  # Maximum acceptable line length
MAX_FUNCTION_LINES = 100  # Maximum acceptable function length
MAX_CLASS_LINES = 500  # Maximum acceptable class length

# Directories to exclude from analysis
EXCLUDED_DIRS = [
    "_trash", 
    "archive", 
    "backups", 
    "_archive", 
    "venv", 
    "__pycache__", 
    "needtoverify"
]

class CodeIssue:
    """Class to represent a code issue."""
    def __init__(self, file_path: str, line: int, issue_type: str, message: str, severity: str):
        self.file_path = file_path
        self.line = line
        self.issue_type = issue_type
        self.message = message
        self.severity = severity  # 'high', 'medium', 'low'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'line': self.line,
            'issue_type': self.issue_type,
            'message': self.message,
            'severity': self.severity
        }

class CodePattern:
    """Class to represent a code pattern."""
    def __init__(self, pattern_type: str, count: int, examples: List[str]):
        self.pattern_type = pattern_type
        self.count = count
        self.examples = examples
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'pattern_type': self.pattern_type,
            'count': self.count,
            'examples': self.examples
        }

class FileStats:
    """Class to store statistics about a file."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.loc = 0  # Lines of code
        self.comment_lines = 0
        self.blank_lines = 0
        self.imports = []
        self.classes = []
        self.functions = []
        self.complexity = 0
        self.issues = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'loc': self.loc,
            'comment_lines': self.comment_lines,
            'blank_lines': self.blank_lines,
            'imports': self.imports,
            'classes': self.classes,
            'functions': self.functions,
            'complexity': self.complexity,
            'issues': [issue.to_dict() for issue in self.issues]
        }

class CodeAnalyzer:
    """Analyzer for Python code in the codebase."""
    
    def __init__(self):
        self.files: Dict[str, FileStats] = {}
        self.patterns: Dict[str, CodePattern] = {}
        self.issues: List[CodeIssue] = []
        self.recommendations: List[Dict[str, Any]] = []
        self.agent_files: Dict[str, str] = {}  # Map of agent name to file path
        
        # Patterns to look for
        self.anti_patterns = {
            'global_variables': r'\bglobal\b',
            'bare_except': r'except:',
            'pass_in_except': r'except.*:\s*\n\s*pass',
            'time_sleep': r'time\.sleep\(',
            'print_debug': r'\bprint\(',
            'mutable_default_args': r'def\s+\w+\([^)]*=\[\][^)]*\)',
            'hardcoded_paths': r'[\'"][\/\\](?:home|usr|var|etc|opt|tmp)[\/\\][^\'"]*[\'"]',
            'hardcoded_ips': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'hardcoded_ports': r'[\'"](?:port|PORT)[\'"]:\s*\d+',
            'hardcoded_credentials': r'(?:password|PASSWORD|secret|SECRET|key|KEY)\s*=\s*[\'"][^\'"]+[\'"]'
        }
        
        # Good patterns to look for
        self.good_patterns = {
            'type_hints': r'def\s+\w+\([^)]*\)\s*->\s*\w+',
            'context_managers': r'with\s+',
            'list_comprehensions': r'\[\s*\w+\s+for\s+\w+\s+in\s+',
            'docstrings': r'"""[\s\S]*?"""',
            'exception_handling': r'try\s*:[\s\S]*?except\s+\w+',
            'logging': r'logging\.\w+\('
        }
        
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
                        
            logger.info(f"Loaded {len(self.agent_files)} agent files for analysis.")
            
        except Exception as e:
            logger.error(f"Error loading agent report: {e}")
            sys.exit(1)
        
    def analyze_agents(self):
        """Analyze agent files."""
        logger.info("Analyzing agent files...")
        
        # Load agent files
        self.load_agent_files()
        
        # Analyze each agent file
        for agent_name, file_path in self.agent_files.items():
            try:
                logger.info(f"Analyzing agent: {agent_name} ({file_path})")
                self._analyze_file(Path(file_path), agent_name)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
        
        # Analyze patterns
        self._analyze_patterns()
        
        # Generate recommendations
        self._generate_recommendations()
        
        logger.info(f"Analyzed {len(self.files)} agent files.")
    
    def _analyze_file(self, file_path: Path, agent_name: str):
        """Analyze a Python file."""
        # Skip excluded directories
        for excluded_dir in EXCLUDED_DIRS:
            if excluded_dir in str(file_path):
                logger.info(f"Skipping excluded directory: {file_path}")
                return
                
        relative_path = file_path.relative_to(PROJECT_ROOT)
        file_stats = FileStats(str(relative_path))
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()
            
        # Count lines
        file_stats.loc = len(lines)
        file_stats.blank_lines = sum(1 for line in lines if not line.strip())
        file_stats.comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        
        # Parse AST
        try:
            tree = ast.parse(content)
            
            # Extract imports
            file_stats.imports = self._extract_imports(tree)
            
            # Extract classes and functions
            self._extract_classes_and_functions(tree, file_stats)
            
            # Calculate complexity
            file_stats.complexity = self._calculate_complexity(tree)
            
            # Check for issues
            self._check_for_issues(tree, content, lines, file_stats)
            
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
            issue = CodeIssue(
                file_path=str(relative_path),
                line=e.lineno or 0,
                issue_type="syntax_error",
                message=f"Syntax error: {e}",
                severity="high"
            )
            file_stats.issues.append(issue)
            self.issues.append(issue)
        
        # Store file stats
        self.files[str(relative_path)] = file_stats
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from an AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for name in node.names:
                        imports.append(f"{node.module}.{name.name}")
        
        return imports
    
    def _extract_classes_and_functions(self, tree: ast.AST, file_stats: FileStats):
        """Extract classes and functions from an AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Count lines in class
                start_line = node.lineno
                end_line = self._find_end_line(node)
                class_lines = end_line - start_line + 1
                
                class_info = {
                    'name': node.name,
                    'line': start_line,
                    'lines': class_lines,
                    'methods': []
                }
                
                # Check methods
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        method_start = child.lineno
                        method_end = self._find_end_line(child)
                        method_lines = method_end - method_start + 1
                        
                        method_info = {
                            'name': child.name,
                            'line': method_start,
                            'lines': method_lines
                        }
                        
                        class_info['methods'].append(method_info)
                
                file_stats.classes.append(class_info)
                
            elif isinstance(node, ast.FunctionDef) and not self._is_method(node):
                # Only count top-level functions
                start_line = node.lineno
                end_line = self._find_end_line(node)
                func_lines = end_line - start_line + 1
                
                func_info = {
                    'name': node.name,
                    'line': start_line,
                    'lines': func_lines
                }
                
                file_stats.functions.append(func_info)
    
    def _is_method(self, node: ast.FunctionDef) -> bool:
        """Check if a function definition is a method (part of a class)."""
        # Check if the parent node is a class
        parent = getattr(node, 'parent', None)
        if parent is None:
            # If parent attribute is not available, check the node's context
            # This is a simplified approach that may not be 100% accurate
            for field_name, field_value in ast.iter_fields(node):
                if isinstance(field_value, ast.ClassDef):
                    return True
            return False
        return isinstance(parent, ast.ClassDef)
    
    def _find_end_line(self, node: ast.AST) -> int:
        """Find the end line of a node."""
        max_line = node.lineno
        
        for child in ast.iter_child_nodes(node):
            if hasattr(child, 'lineno'):
                child_end = self._find_end_line(child)
                max_line = max(max_line, child_end)
        
        return max_line
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of a file."""
        # Simple complexity calculation based on control flow statements
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
                complexity += len(node.values) - 1
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                complexity += len(node.values) - 1
        
        return complexity
    
    def _check_for_issues(self, tree: ast.AST, content: str, lines: List[str], file_stats: FileStats):
        """Check for issues in the code."""
        # Check line length
        for i, line in enumerate(lines):
            if len(line) > MAX_LINE_LENGTH:
                issue = CodeIssue(
                    file_path=file_stats.file_path,
                    line=i + 1,
                    issue_type="line_too_long",
                    message=f"Line too long ({len(line)} > {MAX_LINE_LENGTH})",
                    severity="low"
                )
                file_stats.issues.append(issue)
                self.issues.append(issue)
        
        # Check function length
        for func in file_stats.functions:
            if func['lines'] > MAX_FUNCTION_LINES:
                issue = CodeIssue(
                    file_path=file_stats.file_path,
                    line=func['line'],
                    issue_type="function_too_long",
                    message=f"Function '{func['name']}' is too long ({func['lines']} > {MAX_FUNCTION_LINES} lines)",
                    severity="medium"
                )
                file_stats.issues.append(issue)
                self.issues.append(issue)
        
        # Check class length
        for cls in file_stats.classes:
            if cls['lines'] > MAX_CLASS_LINES:
                issue = CodeIssue(
                    file_path=file_stats.file_path,
                    line=cls['line'],
                    issue_type="class_too_long",
                    message=f"Class '{cls['name']}' is too long ({cls['lines']} > {MAX_CLASS_LINES} lines)",
                    severity="medium"
                )
                file_stats.issues.append(issue)
                self.issues.append(issue)
            
            # Check method length
            for method in cls['methods']:
                if method['lines'] > MAX_FUNCTION_LINES:
                    issue = CodeIssue(
                        file_path=file_stats.file_path,
                        line=method['line'],
                        issue_type="method_too_long",
                        message=f"Method '{cls['name']}.{method['name']}' is too long ({method['lines']} > {MAX_FUNCTION_LINES} lines)",
                        severity="medium"
                    )
                    file_stats.issues.append(issue)
                    self.issues.append(issue)
        
        # Check complexity
        if file_stats.complexity > MAX_COMPLEXITY:
            issue = CodeIssue(
                file_path=file_stats.file_path,
                line=1,
                issue_type="high_complexity",
                message=f"File has high cyclomatic complexity ({file_stats.complexity} > {MAX_COMPLEXITY})",
                severity="high"
            )
            file_stats.issues.append(issue)
            self.issues.append(issue)
        
        # Check for anti-patterns
        for pattern_name, pattern in self.anti_patterns.items():
            for match in re.finditer(pattern, content):
                line_no = content[:match.start()].count('\n') + 1
                issue = CodeIssue(
                    file_path=file_stats.file_path,
                    line=line_no,
                    issue_type=f"anti_pattern_{pattern_name}",
                    message=f"Anti-pattern detected: {pattern_name}",
                    severity="medium"
                )
                file_stats.issues.append(issue)
                self.issues.append(issue)
        
        # Check for missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    issue = CodeIssue(
                        file_path=file_stats.file_path,
                        line=node.lineno,
                        issue_type="missing_docstring",
                        message=f"Missing docstring for {'class' if isinstance(node, ast.ClassDef) else 'function'} '{node.name}'",
                        severity="low"
                    )
                    file_stats.issues.append(issue)
                    self.issues.append(issue)
    
    def _analyze_patterns(self):
        """Analyze patterns across the codebase."""
        logger.info("Analyzing code patterns...")
        
        # Count anti-patterns
        anti_pattern_counts = defaultdict(int)
        anti_pattern_examples = defaultdict(list)
        
        # Count good patterns
        good_pattern_counts = defaultdict(int)
        good_pattern_examples = defaultdict(list)
        
        for file_path, file_stats in self.files.items():
            # Read file content
            full_path = PROJECT_ROOT / file_path
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for anti-patterns
                for pattern_name, pattern in self.anti_patterns.items():
                    matches = list(re.finditer(pattern, content))
                    anti_pattern_counts[pattern_name] += len(matches)
                    
                    # Store examples (up to 3 per file)
                    for match in matches[:3]:
                        line_no = content[:match.start()].count('\n') + 1
                        example = {
                            'file': file_path,
                            'line': line_no,
                            'snippet': match.group(0)
                        }
                        anti_pattern_examples[pattern_name].append(example)
                
                # Check for good patterns
                for pattern_name, pattern in self.good_patterns.items():
                    matches = list(re.finditer(pattern, content))
                    good_pattern_counts[pattern_name] += len(matches)
                    
                    # Store examples (up to 3 per file)
                    for match in matches[:3]:
                        line_no = content[:match.start()].count('\n') + 1
                        example = {
                            'file': file_path,
                            'line': line_no,
                            'snippet': match.group(0)
                        }
                        good_pattern_examples[pattern_name].append(example)
                        
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
        
        # Store anti-patterns
        for pattern_name, count in anti_pattern_counts.items():
            examples = anti_pattern_examples[pattern_name]
            self.patterns[f"anti_{pattern_name}"] = CodePattern(
                pattern_type=f"anti_{pattern_name}",
                count=count,
                examples=[f"{e['file']}:{e['line']} - {e['snippet']}" for e in examples[:5]]
            )
        
        # Store good patterns
        for pattern_name, count in good_pattern_counts.items():
            examples = good_pattern_examples[pattern_name]
            self.patterns[f"good_{pattern_name}"] = CodePattern(
                pattern_type=f"good_{pattern_name}",
                count=count,
                examples=[f"{e['file']}:{e['line']} - {e['snippet']}" for e in examples[:5]]
            )
    
    def _generate_recommendations(self):
        """Generate optimization recommendations."""
        logger.info("Generating optimization recommendations...")
        
        # Recommendation: Fix high complexity files
        high_complexity_files = [
            file_path for file_path, stats in self.files.items()
            if stats.complexity > MAX_COMPLEXITY
        ]
        
        if high_complexity_files:
            self.recommendations.append({
                'title': 'Reduce code complexity',
                'description': 'The following files have high cyclomatic complexity. Consider refactoring them into smaller, more manageable functions.',
                'priority': 'high',
                'affected_files': high_complexity_files
            })
        
        # Recommendation: Fix bare excepts
        bare_except_count = self.patterns.get('anti_bare_except', CodePattern('', 0, [])).count
        if bare_except_count > 0:
            self.recommendations.append({
                'title': 'Replace bare excepts',
                'description': f'Found {bare_except_count} instances of bare except clauses. Replace them with specific exception types to avoid masking errors.',
                'priority': 'high',
                'examples': self.patterns.get('anti_bare_except', CodePattern('', 0, [])).examples
            })
        
        # Recommendation: Fix hardcoded credentials
        hardcoded_creds_count = self.patterns.get('anti_hardcoded_credentials', CodePattern('', 0, [])).count
        if hardcoded_creds_count > 0:
            self.recommendations.append({
                'title': 'Remove hardcoded credentials',
                'description': f'Found {hardcoded_creds_count} instances of hardcoded credentials. Move them to environment variables or secure configuration files.',
                'priority': 'critical',
                'examples': self.patterns.get('anti_hardcoded_credentials', CodePattern('', 0, [])).examples
            })
        
        # Recommendation: Add type hints
        total_functions = sum(len(stats.functions) for stats in self.files.values())
        type_hints_count = self.patterns.get('good_type_hints', CodePattern('', 0, [])).count
        
        if total_functions > 0 and type_hints_count / total_functions < 0.5:
            self.recommendations.append({
                'title': 'Add type hints',
                'description': f'Only {type_hints_count} out of approximately {total_functions} functions have type hints. Adding type hints improves code readability and enables better tooling support.',
                'priority': 'medium'
            })
        
        # Recommendation: Add docstrings
        missing_docstrings = sum(1 for issue in self.issues if issue.issue_type == 'missing_docstring')
        if missing_docstrings > 0:
            self.recommendations.append({
                'title': 'Add missing docstrings',
                'description': f'Found {missing_docstrings} functions or classes without docstrings. Adding docstrings improves code maintainability.',
                'priority': 'medium'
            })
        
        # Recommendation: Replace print statements with logging
        print_count = self.patterns.get('anti_print_debug', CodePattern('', 0, [])).count
        logging_count = self.patterns.get('good_logging', CodePattern('', 0, [])).count
        
        if print_count > logging_count:
            self.recommendations.append({
                'title': 'Replace print statements with logging',
                'description': f'Found {print_count} print statements, but only {logging_count} logging statements. Replace print statements with proper logging for better debugging capabilities.',
                'priority': 'medium',
                'examples': self.patterns.get('anti_print_debug', CodePattern('', 0, [])).examples
            })
    
    def generate_report(self):
        """Generate a detailed report of the code analysis."""
        logger.info("Generating code analysis report...")
        
        report = {
            'total_files': len(self.files),
            'total_loc': sum(stats.loc for stats in self.files.values()),
            'total_issues': len(self.issues),
            'files': {path: stats.to_dict() for path, stats in self.files.items()},
            'patterns': {name: pattern.to_dict() for name, pattern in self.patterns.items()},
            'issues_summary': self._generate_issues_summary(),
            'recommendations': self.recommendations
        }
        
        # Save report
        with open(REPORT_OUTPUT, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save issues
        issues_report = {
            'total_issues': len(self.issues),
            'issues_by_severity': {
                'critical': [issue.to_dict() for issue in self.issues if issue.severity == 'critical'],
                'high': [issue.to_dict() for issue in self.issues if issue.severity == 'high'],
                'medium': [issue.to_dict() for issue in self.issues if issue.severity == 'medium'],
                'low': [issue.to_dict() for issue in self.issues if issue.severity == 'low']
            }
        }
        
        with open(ISSUES_OUTPUT, 'w') as f:
            json.dump(issues_report, f, indent=2)
        
        # Save recommendations
        with open(RECOMMENDATIONS_OUTPUT, 'w') as f:
            json.dump({'recommendations': self.recommendations}, f, indent=2)
        
        logger.info(f"Code analysis report saved to {REPORT_OUTPUT}")
        logger.info(f"Issues report saved to {ISSUES_OUTPUT}")
        logger.info(f"Recommendations saved to {RECOMMENDATIONS_OUTPUT}")
        
        # Print summary
        print("\n=== Code Analyzer Summary ===")
        print(f"Total files analyzed: {len(self.files)}")
        print(f"Total lines of code: {sum(stats.loc for stats in self.files.values())}")
        print(f"Total issues found: {len(self.issues)}")
        print(f"Critical issues: {len([i for i in self.issues if i.severity == 'critical'])}")
        print(f"High severity issues: {len([i for i in self.issues if i.severity == 'high'])}")
        print(f"Medium severity issues: {len([i for i in self.issues if i.severity == 'medium'])}")
        print(f"Low severity issues: {len([i for i in self.issues if i.severity == 'low'])}")
        print(f"Recommendations: {len(self.recommendations)}")
        print(f"Detailed report saved to: {REPORT_OUTPUT}")
    
    def _generate_issues_summary(self) -> Dict[str, int]:
        """Generate a summary of issues by type."""
        summary = defaultdict(int)
        
        for issue in self.issues:
            summary[issue.issue_type] += 1
        
        return dict(summary)

def main():
    """Main function."""
    print("=== Code Analyzer ===")
    
    analyzer = CodeAnalyzer()
    analyzer.analyze_agents()
    analyzer.generate_report()
    
    print("\nCode analysis complete!")

if __name__ == "__main__":
    main() 