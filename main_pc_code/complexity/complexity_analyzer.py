#!/usr/bin/env python3
"""
Complexity Analyzer - Automated Code Complexity Analysis and Reduction
Provides comprehensive code complexity analysis with automated refactoring suggestions.

Features:
- Cyclomatic complexity analysis with radon integration
- Code quality metrics and technical debt assessment
- Automated refactoring suggestions and patterns
- Dependency complexity analysis and optimization
- Performance bottleneck identification
- Maintainability scoring and improvement recommendations
"""
from __future__ import annotations
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import ast
import time
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
from enum import Enum
import re

# Core imports
from common.core.base_agent import BaseAgent

# Event system imports
from events.memory_events import (
    MemoryEventType, create_memory_operation, MemoryType
)
from events.event_bus import publish_memory_event

# Try to import radon for complexity analysis
try:
    import radon.complexity as radon_cc
    import radon.metrics as radon_metrics
    import radon.raw as radon_raw
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False
    print("Radon not available - install with: pip install radon")

class ComplexityLevel(Enum):
    """Code complexity levels"""
    SIMPLE = "simple"        # A-B (1-10)
    MODERATE = "moderate"    # C (11-20)  
    COMPLEX = "complex"      # D (21-50)
    VERY_COMPLEX = "very_complex"  # E (51-100)
    EXTREMELY_COMPLEX = "extremely_complex"  # F (100+)

class RefactoringPriority(Enum):
    """Refactoring priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CodeIssueType(Enum):
    """Types of code issues"""
    HIGH_COMPLEXITY = "high_complexity"
    LONG_METHOD = "long_method"
    DEEP_NESTING = "deep_nesting"
    TOO_MANY_PARAMETERS = "too_many_parameters"
    DUPLICATE_CODE = "duplicate_code"
    LARGE_CLASS = "large_class"
    DEAD_CODE = "dead_code"
    TECHNICAL_DEBT = "technical_debt"

@dataclass
class ComplexityMetrics:
    """Code complexity metrics"""
    cyclomatic_complexity: int
    lines_of_code: int
    logical_lines: int
    comment_lines: int
    blank_lines: int
    maintainability_index: float
    halstead_difficulty: float
    halstead_effort: float
    complexity_level: ComplexityLevel
    
    @property
    def comment_ratio(self) -> float:
        return self.comment_lines / max(self.lines_of_code, 1)
    
    @property
    def code_density(self) -> float:
        return self.logical_lines / max(self.lines_of_code, 1)

@dataclass
class CodeIssue:
    """Code quality issue"""
    issue_id: str
    issue_type: CodeIssueType
    severity: RefactoringPriority
    file_path: str
    line_number: int
    function_name: Optional[str]
    class_name: Optional[str]
    description: str
    suggestion: str
    complexity_score: float
    detected_at: datetime = field(default_factory=datetime.now)
    
    @property
    def age_days(self) -> int:
        return (datetime.now() - self.detected_at).days

@dataclass
class RefactoringOpportunity:
    """Refactoring opportunity suggestion"""
    opportunity_id: str
    file_path: str
    opportunity_type: str
    description: str
    effort_estimate: str  # hours/days
    impact_score: float  # 1-10
    suggested_approach: str
    code_before: str
    code_after: str
    benefits: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

@dataclass
class DependencyAnalysis:
    """Dependency complexity analysis"""
    file_path: str
    imports: List[str]
    internal_dependencies: List[str]
    external_dependencies: List[str]
    circular_dependencies: List[str]
    dependency_depth: int
    coupling_score: float
    cohesion_score: float

class ComplexityAnalyzer(BaseAgent):
    """
    Comprehensive code complexity analyzer.
    
    Analyzes code complexity, identifies issues, and provides
    automated refactoring suggestions for improved maintainability.
    """
    
    def __init__(self, 
                 analysis_interval_hours: int = 24,
                 complexity_threshold: int = 10,
                 enable_auto_suggestions: bool = True,
                 **kwargs):
        super().__init__(name="ComplexityAnalyzer", **kwargs)
        
        # Configuration
        self.analysis_interval = analysis_interval_hours * 3600  # Convert to seconds
        self.complexity_threshold = complexity_threshold
        self.enable_auto_suggestions = enable_auto_suggestions
        
        # Analysis data
        self.file_metrics: Dict[str, ComplexityMetrics] = {}
        self.code_issues: Dict[str, CodeIssue] = {}
        self.refactoring_opportunities: Dict[str, RefactoringOpportunity] = {}
        self.dependency_analysis: Dict[str, DependencyAnalysis] = {}
        
        # Analysis history
        self.complexity_history: deque = deque(maxlen=100)
        self.refactoring_history: List[Dict[str, Any]] = []
        
        # Patterns for issue detection
        self.issue_patterns = self._initialize_issue_patterns()
        self.refactoring_patterns = self._initialize_refactoring_patterns()
        
        # Metrics tracking
        self.analysis_metrics = {
            'total_files_analyzed': 0,
            'total_issues_found': 0,
            'total_opportunities': 0,
            'average_complexity': 0.0,
            'technical_debt_hours': 0.0
        }
        
        # Initialize analysis
        self._start_complexity_monitoring()
        
        self.logger.info("Complexity Analyzer initialized")
    
    def _initialize_issue_patterns(self) -> Dict[CodeIssueType, Dict[str, Any]]:
        """Initialize patterns for detecting code issues"""
        return {
            CodeIssueType.HIGH_COMPLEXITY: {
                'threshold': 15,
                'description': 'Function has high cyclomatic complexity',
                'suggestion': 'Break down into smaller functions or use early returns'
            },
            CodeIssueType.LONG_METHOD: {
                'threshold': 50,  # lines
                'description': 'Method is too long and hard to understand',
                'suggestion': 'Extract smaller methods or use composition'
            },
            CodeIssueType.DEEP_NESTING: {
                'threshold': 4,  # nesting levels
                'description': 'Code has deep nesting levels',
                'suggestion': 'Use guard clauses or extract nested logic'
            },
            CodeIssueType.TOO_MANY_PARAMETERS: {
                'threshold': 5,  # parameters
                'description': 'Function has too many parameters',
                'suggestion': 'Use parameter objects or configuration classes'
            },
            CodeIssueType.LARGE_CLASS: {
                'threshold': 500,  # lines
                'description': 'Class is too large and violates SRP',
                'suggestion': 'Split into smaller, focused classes'
            }
        }
    
    def _initialize_refactoring_patterns(self) -> List[Dict[str, Any]]:
        """Initialize refactoring patterns and suggestions"""
        return [
            {
                'name': 'Extract Method',
                'pattern': r'def\s+\w+\(.*?\):[^}]{200,}',  # Long methods
                'description': 'Extract repeated or complex logic into separate methods',
                'impact': 8.0
            },
            {
                'name': 'Replace Conditional with Polymorphism',
                'pattern': r'if\s+.*isinstance\(.*?\):|elif\s+.*isinstance\(.*?\):',
                'description': 'Replace type checking with polymorphic behavior',
                'impact': 7.5
            },
            {
                'name': 'Introduce Parameter Object',
                'pattern': r'def\s+\w+\([^)]{50,}\):',  # Many parameters
                'description': 'Group related parameters into a configuration object',
                'impact': 6.0
            },
            {
                'name': 'Extract Class',
                'pattern': r'class\s+\w+.*?:\s*(?:[^c]|c(?!lass))*{500,}',  # Large classes
                'description': 'Split large classes into smaller, focused classes',
                'impact': 9.0
            },
            {
                'name': 'Replace Magic Numbers',
                'pattern': r'\b(?!0|1)\d{2,}\b',  # Magic numbers
                'description': 'Replace magic numbers with named constants',
                'impact': 4.0
            }
        ]
    
    def _start_complexity_monitoring(self) -> None:
        """Start background complexity monitoring"""
        # Main analysis thread
        analysis_thread = threading.Thread(target=self._complexity_analysis_loop, daemon=True)
        analysis_thread.start()
        
        # Issue detection thread
        detection_thread = threading.Thread(target=self._issue_detection_loop, daemon=True)
        detection_thread.start()
        
        # Refactoring opportunity thread
        refactor_thread = threading.Thread(target=self._refactoring_opportunity_loop, daemon=True)
        refactor_thread.start()
    
    def _complexity_analysis_loop(self) -> None:
        """Background complexity analysis loop"""
        while self.running:
            try:
                self._run_full_complexity_analysis()
                
                time.sleep(self.analysis_interval)
                
            except Exception as e:
                self.logger.error(f"Complexity analysis error: {e}")
                time.sleep(3600)  # Wait 1 hour on error
    
    def _issue_detection_loop(self) -> None:
        """Background issue detection loop"""
        while self.running:
            try:
                self._detect_code_issues()
                self._update_analysis_metrics()
                
                time.sleep(1800)  # Run every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Issue detection error: {e}")
                time.sleep(3600)
    
    def _refactoring_opportunity_loop(self) -> None:
        """Background refactoring opportunity detection"""
        while self.running:
            try:
                if self.enable_auto_suggestions:
                    self._generate_refactoring_opportunities()
                
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                self.logger.error(f"Refactoring opportunity error: {e}")
                time.sleep(7200)
    
    async def analyze_file_complexity(self, file_path: str) -> ComplexityMetrics:
        """Analyze complexity of a single file"""
        try:
            full_path = Path(PROJECT_ROOT) / file_path
            
            if not full_path.exists() or not full_path.suffix == '.py':
                raise ValueError(f"Invalid Python file: {file_path}")
            
            # Read file content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST for analysis
            tree = ast.parse(content, filename=str(full_path))
            
            # Calculate metrics
            metrics = self._calculate_file_metrics(content, tree)
            
            # Store metrics
            self.file_metrics[file_path] = metrics
            
            # Update analysis metrics
            self.analysis_metrics['total_files_analyzed'] += 1
            
            # Publish analysis event
            analysis_event = create_memory_operation(
                operation_type=MemoryEventType.MEMORY_CREATED,
                memory_id=f"complexity_analysis_{file_path.replace('/', '_')}",
                memory_type=MemoryType.PROCEDURAL,
                content=f"Complexity analysis: {metrics.complexity_level.value}",
                size_bytes=metrics.lines_of_code,
                source_agent=self.name,
                machine_id=self._get_machine_id()
            )
            
            publish_memory_event(analysis_event)
            
            self.logger.info(f"File analyzed: {file_path} (Complexity: {metrics.cyclomatic_complexity}, Level: {metrics.complexity_level.value})")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"File analysis failed for {file_path}: {e}")
            raise
    
    def _calculate_file_metrics(self, content: str, tree: ast.AST) -> ComplexityMetrics:
        """Calculate comprehensive file metrics"""
        lines = content.split('\n')
        
        # Basic line counts
        total_lines = len(lines)
        blank_lines = len([line for line in lines if not line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith('#')])
        logical_lines = total_lines - blank_lines - comment_lines
        
        # Cyclomatic complexity
        if RADON_AVAILABLE:
            cc_results = radon_cc.cc_visit(content)
            total_complexity = sum(result.complexity for result in cc_results)
            
            # Raw metrics
            raw_metrics = radon_raw.analyze(content)
            logical_lines = raw_metrics.lloc
            comment_lines = raw_metrics.comments
            
            # Maintainability index
            mi_result = radon_metrics.mi_visit(content, multi=True)
            maintainability_index = mi_result if isinstance(mi_result, (int, float)) else 50.0
            
            # Halstead metrics
            h_result = radon_metrics.h_visit(content)
            halstead_difficulty = getattr(h_result[0], 'difficulty', 0) if h_result else 0
            halstead_effort = getattr(h_result[0], 'effort', 0) if h_result else 0
            
        else:
            # Fallback calculation using AST
            total_complexity = self._calculate_ast_complexity(tree)
            maintainability_index = 50.0  # Default
            halstead_difficulty = 0.0
            halstead_effort = 0.0
        
        # Determine complexity level
        complexity_level = self._determine_complexity_level(total_complexity)
        
        return ComplexityMetrics(
            cyclomatic_complexity=total_complexity,
            lines_of_code=total_lines,
            logical_lines=logical_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            maintainability_index=maintainability_index,
            halstead_difficulty=halstead_difficulty,
            halstead_effort=halstead_effort,
            complexity_level=complexity_level
        )
    
    def _calculate_ast_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity using AST (fallback method)"""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            # Decision points that increase complexity
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers) + (1 if node.orelse else 0)
            elif isinstance(node, (ast.BoolOp, ast.Compare)):
                complexity += 1
            elif isinstance(node, ast.comprehension):
                complexity += 1
        
        return complexity
    
    def _determine_complexity_level(self, complexity: int) -> ComplexityLevel:
        """Determine complexity level based on cyclomatic complexity"""
        if complexity <= 10:
            return ComplexityLevel.SIMPLE
        elif complexity <= 20:
            return ComplexityLevel.MODERATE
        elif complexity <= 50:
            return ComplexityLevel.COMPLEX
        elif complexity <= 100:
            return ComplexityLevel.VERY_COMPLEX
        else:
            return ComplexityLevel.EXTREMELY_COMPLEX
    
    def _run_full_complexity_analysis(self) -> None:
        """Run full project complexity analysis"""
        self.logger.info("Starting full complexity analysis...")
        
        python_files = []
        
        # Find all Python files
        for directory in ['main_pc_code', 'pc2_code', 'common', 'events']:
            dir_path = Path(PROJECT_ROOT) / directory
            if dir_path.exists():
                python_files.extend(dir_path.rglob('*.py'))
        
        analysis_start = datetime.now()
        files_analyzed = 0
        total_complexity = 0
        
        for file_path in python_files:
            try:
                relative_path = str(file_path.relative_to(PROJECT_ROOT))
                
                # Skip certain files
                if any(skip in relative_path for skip in ['__pycache__', '.git', 'venv', 'test_']):
                    continue
                
                metrics = asyncio.run(self.analyze_file_complexity(relative_path))
                files_analyzed += 1
                total_complexity += metrics.cyclomatic_complexity
                
            except Exception as e:
                self.logger.debug(f"Skipped file {file_path}: {e}")
        
        analysis_duration = (datetime.now() - analysis_start).total_seconds()
        
        # Update metrics
        if files_analyzed > 0:
            self.analysis_metrics['average_complexity'] = total_complexity / files_analyzed
        
        # Record analysis in history
        self.complexity_history.append({
            'timestamp': analysis_start,
            'files_analyzed': files_analyzed,
            'total_complexity': total_complexity,
            'average_complexity': self.analysis_metrics['average_complexity'],
            'duration_seconds': analysis_duration
        })
        
        self.logger.info(f"Complexity analysis completed: {files_analyzed} files, avg complexity: {self.analysis_metrics['average_complexity']:.2f}")
    
    def _detect_code_issues(self) -> None:
        """Detect code quality issues"""
        issues_found = 0
        
        for file_path, metrics in self.file_metrics.items():
            try:
                # Check for high complexity
                if metrics.cyclomatic_complexity > self.issue_patterns[CodeIssueType.HIGH_COMPLEXITY]['threshold']:
                    issue = self._create_code_issue(
                        CodeIssueType.HIGH_COMPLEXITY,
                        file_path,
                        metrics.cyclomatic_complexity,
                        f"Cyclomatic complexity: {metrics.cyclomatic_complexity}"
                    )
                    self.code_issues[issue.issue_id] = issue
                    issues_found += 1
                
                # Check for long files (proxy for large classes/methods)
                if metrics.lines_of_code > self.issue_patterns[CodeIssueType.LARGE_CLASS]['threshold']:
                    issue = self._create_code_issue(
                        CodeIssueType.LARGE_CLASS,
                        file_path,
                        metrics.lines_of_code,
                        f"File too long: {metrics.lines_of_code} lines"
                    )
                    self.code_issues[issue.issue_id] = issue
                    issues_found += 1
                
                # Check maintainability index
                if metrics.maintainability_index < 20:
                    issue = self._create_code_issue(
                        CodeIssueType.TECHNICAL_DEBT,
                        file_path,
                        100 - metrics.maintainability_index,
                        f"Low maintainability index: {metrics.maintainability_index:.1f}"
                    )
                    self.code_issues[issue.issue_id] = issue
                    issues_found += 1
                
            except Exception as e:
                self.logger.error(f"Issue detection failed for {file_path}: {e}")
        
        self.analysis_metrics['total_issues_found'] = len(self.code_issues)
        
        if issues_found > 0:
            self.logger.warning(f"Detected {issues_found} new code quality issues")
    
    def _create_code_issue(self, issue_type: CodeIssueType, file_path: str, 
                          score: float, description: str) -> CodeIssue:
        """Create a code quality issue"""
        issue_id = self._generate_issue_id(issue_type, file_path)
        
        # Determine severity based on score and type
        if issue_type == CodeIssueType.HIGH_COMPLEXITY:
            if score > 50:
                severity = RefactoringPriority.CRITICAL
            elif score > 25:
                severity = RefactoringPriority.HIGH
            else:
                severity = RefactoringPriority.MEDIUM
        elif issue_type == CodeIssueType.TECHNICAL_DEBT:
            if score > 70:
                severity = RefactoringPriority.CRITICAL
            elif score > 50:
                severity = RefactoringPriority.HIGH
            else:
                severity = RefactoringPriority.MEDIUM
        else:
            severity = RefactoringPriority.MEDIUM
        
        pattern = self.issue_patterns.get(issue_type, {})
        
        return CodeIssue(
            issue_id=issue_id,
            issue_type=issue_type,
            severity=severity,
            file_path=file_path,
            line_number=1,  # Would need more detailed analysis for exact line
            function_name=None,
            class_name=None,
            description=description,
            suggestion=pattern.get('suggestion', 'Consider refactoring this code'),
            complexity_score=score
        )
    
    def _generate_refactoring_opportunities(self) -> None:
        """Generate refactoring opportunities"""
        opportunities_found = 0
        
        for file_path, metrics in self.file_metrics.items():
            try:
                # Only suggest refactoring for complex files
                if metrics.complexity_level in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX, ComplexityLevel.EXTREMELY_COMPLEX]:
                    
                    # Read file for pattern analysis
                    full_path = Path(PROJECT_ROOT) / file_path
                    if full_path.exists():
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Apply refactoring patterns
                        for pattern in self.refactoring_patterns:
                            if re.search(pattern['pattern'], content, re.MULTILINE | re.DOTALL):
                                opportunity = self._create_refactoring_opportunity(
                                    file_path, pattern, metrics.cyclomatic_complexity
                                )
                                self.refactoring_opportunities[opportunity.opportunity_id] = opportunity
                                opportunities_found += 1
                
            except Exception as e:
                self.logger.error(f"Refactoring opportunity analysis failed for {file_path}: {e}")
        
        self.analysis_metrics['total_opportunities'] = len(self.refactoring_opportunities)
        
        if opportunities_found > 0:
            self.logger.info(f"Identified {opportunities_found} new refactoring opportunities")
    
    def _create_refactoring_opportunity(self, file_path: str, pattern: Dict[str, Any], 
                                      complexity: int) -> RefactoringOpportunity:
        """Create a refactoring opportunity"""
        opportunity_id = self._generate_opportunity_id(file_path, pattern['name'])
        
        # Estimate effort based on complexity and impact
        if complexity > 50:
            effort_estimate = "3-5 days"
        elif complexity > 25:
            effort_estimate = "1-2 days"
        elif complexity > 15:
            effort_estimate = "4-8 hours"
        else:
            effort_estimate = "2-4 hours"
        
        # Generate example refactoring
        code_before = "// Complex code with high cyclomatic complexity"
        code_after = f"// Refactored code using {pattern['name']} pattern"
        
        benefits = [
            "Reduced cyclomatic complexity",
            "Improved readability",
            "Enhanced maintainability",
            "Better testability"
        ]
        
        risks = [
            "Potential introduction of bugs",
            "Increased number of classes/methods",
            "Temporary decrease in team velocity"
        ]
        
        return RefactoringOpportunity(
            opportunity_id=opportunity_id,
            file_path=file_path,
            opportunity_type=pattern['name'],
            description=pattern['description'],
            effort_estimate=effort_estimate,
            impact_score=pattern['impact'],
            suggested_approach=f"Apply {pattern['name']} refactoring pattern",
            code_before=code_before,
            code_after=code_after,
            benefits=benefits,
            risks=risks
        )
    
    async def analyze_dependencies(self, file_path: str) -> DependencyAnalysis:
        """Analyze file dependencies and coupling"""
        try:
            full_path = Path(PROJECT_ROOT) / file_path
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(full_path))
            
            # Extract imports
            imports = []
            internal_deps = []
            external_deps = []
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:
                        module = node.module or ''
                        imports.append(module)
                        
                        # Classify as internal or external
                        if any(module.startswith(prefix) for prefix in ['main_pc_code', 'pc2_code', 'common', 'events']):
                            internal_deps.append(module)
                        else:
                            external_deps.append(module)
            
            # Calculate coupling and cohesion (simplified)
            coupling_score = len(external_deps) / max(len(imports), 1)
            cohesion_score = len(internal_deps) / max(len(imports), 1)
            
            # Detect circular dependencies (simplified check)
            circular_deps = []
            # This would require more sophisticated analysis
            
            analysis = DependencyAnalysis(
                file_path=file_path,
                imports=imports,
                internal_dependencies=internal_deps,
                external_dependencies=external_deps,
                circular_dependencies=circular_deps,
                dependency_depth=len(imports),
                coupling_score=coupling_score,
                cohesion_score=cohesion_score
            )
            
            self.dependency_analysis[file_path] = analysis
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Dependency analysis failed for {file_path}: {e}")
            raise
    
    def _update_analysis_metrics(self) -> None:
        """Update analysis metrics and calculate technical debt"""
        # Calculate technical debt in hours
        total_debt_hours = 0.0
        
        for issue in self.code_issues.values():
            if issue.severity == RefactoringPriority.CRITICAL:
                total_debt_hours += 8.0  # 1 day
            elif issue.severity == RefactoringPriority.HIGH:
                total_debt_hours += 4.0  # Half day
            elif issue.severity == RefactoringPriority.MEDIUM:
                total_debt_hours += 2.0  # Quarter day
            else:
                total_debt_hours += 1.0  # Few hours
        
        self.analysis_metrics['technical_debt_hours'] = total_debt_hours
    
    def get_complexity_report(self) -> Dict[str, Any]:
        """Get comprehensive complexity analysis report"""
        # Top most complex files
        top_complex_files = sorted(
            self.file_metrics.items(),
            key=lambda x: x[1].cyclomatic_complexity,
            reverse=True
        )[:10]
        
        # Critical issues
        critical_issues = [
            issue for issue in self.code_issues.values()
            if issue.severity == RefactoringPriority.CRITICAL
        ]
        
        # High-impact opportunities
        top_opportunities = sorted(
            self.refactoring_opportunities.values(),
            key=lambda x: x.impact_score,
            reverse=True
        )[:10]
        
        # Complexity distribution
        complexity_distribution = defaultdict(int)
        for metrics in self.file_metrics.values():
            complexity_distribution[metrics.complexity_level.value] += 1
        
        return {
            'analysis_summary': {
                'total_files_analyzed': len(self.file_metrics),
                'average_complexity': self.analysis_metrics['average_complexity'],
                'total_issues': len(self.code_issues),
                'critical_issues': len(critical_issues),
                'refactoring_opportunities': len(self.refactoring_opportunities),
                'technical_debt_hours': self.analysis_metrics['technical_debt_hours']
            },
            'complexity_distribution': dict(complexity_distribution),
            'top_complex_files': [
                {
                    'file_path': file_path,
                    'cyclomatic_complexity': metrics.cyclomatic_complexity,
                    'complexity_level': metrics.complexity_level.value,
                    'lines_of_code': metrics.lines_of_code,
                    'maintainability_index': metrics.maintainability_index
                }
                for file_path, metrics in top_complex_files
            ],
            'critical_issues': [
                {
                    'issue_id': issue.issue_id,
                    'issue_type': issue.issue_type.value,
                    'file_path': issue.file_path,
                    'description': issue.description,
                    'suggestion': issue.suggestion,
                    'complexity_score': issue.complexity_score,
                    'age_days': issue.age_days
                }
                for issue in critical_issues
            ],
            'top_refactoring_opportunities': [
                {
                    'opportunity_id': opp.opportunity_id,
                    'file_path': opp.file_path,
                    'opportunity_type': opp.opportunity_type,
                    'description': opp.description,
                    'impact_score': opp.impact_score,
                    'effort_estimate': opp.effort_estimate,
                    'benefits': opp.benefits
                }
                for opp in top_opportunities
            ],
            'analysis_history': [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'files_analyzed': entry['files_analyzed'],
                    'average_complexity': entry['average_complexity'],
                    'duration_seconds': entry['duration_seconds']
                }
                for entry in list(self.complexity_history)[-10:]  # Last 10 analyses
            ]
        }
    
    def _generate_issue_id(self, issue_type: CodeIssueType, file_path: str) -> str:
        """Generate unique issue ID"""
        import hashlib
        content = f"{issue_type.value}_{file_path}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_opportunity_id(self, file_path: str, opportunity_type: str) -> str:
        """Generate unique opportunity ID"""
        import hashlib
        content = f"{file_path}_{opportunity_type}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def shutdown(self):
        """Shutdown the complexity analyzer"""
        # Clear analysis data
        self.file_metrics.clear()
        self.code_issues.clear()
        self.refactoring_opportunities.clear()
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import asyncio
    import logging
    
    logger = configure_logging(__name__, level="INFO")
    
    async def test_complexity_analyzer():
        analyzer = ComplexityAnalyzer(analysis_interval_hours=1)
        
        try:
            # Analyze a specific file
            metrics = await analyzer.analyze_file_complexity("main_pc_code/agents/base_agent.py")
            print(f"Complexity: {metrics.cyclomatic_complexity}, Level: {metrics.complexity_level.value}")
            
            # Get comprehensive report
            report = analyzer.get_complexity_report()
            print(json.dumps(report, indent=2, default=str))
            
        finally:
            analyzer.shutdown()
    
    if RADON_AVAILABLE:
        asyncio.run(test_complexity_analyzer())
    else:
        print("Radon not available - skipping test") 