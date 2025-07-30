#!/usr/bin/env python3
"""
Dependency Optimizer - Intelligent Dependency Management and Optimization
Provides comprehensive dependency analysis with circular dependency detection and optimization.

Features:
- Circular dependency detection and resolution
- Import dependency graph analysis and visualization
- Dependency coupling analysis and decoupling suggestions
- Dead import detection and cleanup
- Dependency layer architecture validation
- Performance impact analysis of dependencies
"""
from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import ast
import time
import json
import logging
import threading
import networkx as nx
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
from enum import Enum
import re

# Core imports
from common.core.base_agent import BaseAgent

# Event system imports

# Try to import graph analysis libraries
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    GRAPH_LIBS_AVAILABLE = True
except ImportError:
    GRAPH_LIBS_AVAILABLE = False
    print("Graph libraries not available - install with: pip install networkx matplotlib")

class DependencyType(Enum):
    """Types of dependencies"""
    DIRECT_IMPORT = "direct_import"
    FROM_IMPORT = "from_import"
    DYNAMIC_IMPORT = "dynamic_import"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    FUNCTION_CALL = "function_call"

class DependencyIssue(Enum):
    """Types of dependency issues"""
    CIRCULAR_DEPENDENCY = "circular_dependency"
    DEAD_IMPORT = "dead_import"
    UNNECESSARY_IMPORT = "unnecessary_import"
    COMPLEX_COUPLING = "complex_coupling"
    LAYER_VIOLATION = "layer_violation"
    PERFORMANCE_IMPACT = "performance_impact"

class OptimizationPriority(Enum):
    """Priority levels for optimization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class DependencyNode:
    """Dependency graph node"""
    module_path: str
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    layer: Optional[str] = None
    complexity_score: float = 0.0
    lines_of_code: int = 0

@dataclass
class DependencyEdge:
    """Dependency relationship"""
    source: str
    target: str
    dependency_type: DependencyType
    line_number: int
    import_statement: str
    usage_count: int = 0
    is_necessary: bool = True

@dataclass
class CircularDependency:
    """Circular dependency detection result"""
    cycle_id: str
    modules: List[str]
    cycle_length: int
    complexity_score: float
    suggested_resolution: str
    breaking_point: Optional[Tuple[str, str]] = None
    
    @property
    def cycle_description(self) -> str:
        return " → ".join(self.modules + [self.modules[0]])

@dataclass
class DependencyIssueReport:
    """Dependency issue report"""
    issue_id: str
    issue_type: DependencyIssue
    priority: OptimizationPriority
    affected_modules: List[str]
    description: str
    impact_analysis: str
    suggested_fix: str
    estimated_effort: str
    detected_at: datetime = field(default_factory=datetime.now)

@dataclass
class LayerDefinition:
    """Architecture layer definition"""
    layer_name: str
    modules: List[str]
    allowed_dependencies: List[str]
    forbidden_dependencies: List[str] = field(default_factory=list)
    
class DependencyOptimizer(BaseAgent):
    """
    Comprehensive dependency optimization system.
    
    Analyzes module dependencies, detects circular dependencies,
    and provides optimization suggestions for better architecture.
    """
    
    def __init__(self, 
                 analysis_interval_hours: int = 12,
                 enable_auto_optimization: bool = False,
                 **kwargs):
        super().__init__(name="DependencyOptimizer", **kwargs)
        
        # Configuration
        self.analysis_interval = analysis_interval_hours * 3600
        self.enable_auto_optimization = enable_auto_optimization
        
        # Dependency analysis data
        self.dependency_graph: nx.DiGraph = nx.DiGraph() if GRAPH_LIBS_AVAILABLE else None
        self.dependency_nodes: Dict[str, DependencyNode] = {}
        self.dependency_edges: List[DependencyEdge] = []
        self.circular_dependencies: Dict[str, CircularDependency] = {}
        self.dependency_issues: Dict[str, DependencyIssueReport] = {}
        
        # Architecture layers
        self.layer_definitions = self._initialize_layer_definitions()
        
        # Analysis history
        self.analysis_history: deque = deque(maxlen=50)
        self.optimization_history: List[Dict[str, Any]] = []
        
        # Metrics
        self.dependency_metrics = {
            'total_modules': 0,
            'total_dependencies': 0,
            'circular_dependencies': 0,
            'dead_imports': 0,
            'average_coupling': 0.0,
            'layer_violations': 0
        }
        
        # Initialize system
        if GRAPH_LIBS_AVAILABLE:
            self._start_dependency_monitoring()
        
        self.logger.info("Dependency Optimizer initialized")
    
    def _initialize_layer_definitions(self) -> Dict[str, LayerDefinition]:
        """Initialize architecture layer definitions"""
        return {
            'presentation': LayerDefinition(
                layer_name='presentation',
                modules=['main_pc_code/ui/', 'main_pc_code/api/'],
                allowed_dependencies=['business', 'common']
            ),
            'business': LayerDefinition(
                layer_name='business',
                modules=['main_pc_code/agents/', 'main_pc_code/complexity/', 'main_pc_code/security/'],
                allowed_dependencies=['data', 'common'],
                forbidden_dependencies=['presentation']
            ),
            'data': LayerDefinition(
                layer_name='data',
                modules=['main_pc_code/database/', 'main_pc_code/storage/'],
                allowed_dependencies=['common'],
                forbidden_dependencies=['presentation', 'business']
            ),
            'common': LayerDefinition(
                layer_name='common',
                modules=['common/', 'events/', 'common_utils/'],
                allowed_dependencies=[],
                forbidden_dependencies=['presentation', 'business', 'data']
            )
        }
    
    def _start_dependency_monitoring(self) -> None:
        """Start background dependency monitoring"""
        # Main analysis thread
        analysis_thread = threading.Thread(target=self._dependency_analysis_loop, daemon=True)
        analysis_thread.start()
        
        # Circular dependency detection thread
        circular_thread = threading.Thread(target=self._circular_dependency_loop, daemon=True)
        circular_thread.start()
        
        # Optimization opportunity thread
        optimization_thread = threading.Thread(target=self._optimization_opportunity_loop, daemon=True)
        optimization_thread.start()
    
    def _dependency_analysis_loop(self) -> None:
        """Background dependency analysis loop"""
        while self.running:
            try:
                self._run_full_dependency_analysis()
                
                time.sleep(self.analysis_interval)
                
            except Exception as e:
                self.logger.error(f"Dependency analysis error: {e}")
                time.sleep(3600)
    
    def _circular_dependency_loop(self) -> None:
        """Background circular dependency detection"""
        while self.running:
            try:
                self._detect_circular_dependencies()
                self._validate_layer_architecture()
                
                time.sleep(1800)  # Every 30 minutes
                
            except Exception as e:
                self.logger.error(f"Circular dependency detection error: {e}")
                time.sleep(3600)
    
    def _optimization_opportunity_loop(self) -> None:
        """Background optimization opportunity detection"""
        while self.running:
            try:
                self._detect_dead_imports()
                self._analyze_coupling_complexity()
                self._suggest_optimizations()
                
                time.sleep(3600)  # Every hour
                
            except Exception as e:
                self.logger.error(f"Optimization opportunity error: {e}")
                time.sleep(1800)
    
    async def analyze_module_dependencies(self, module_path: str) -> DependencyNode:
        """Analyze dependencies for a single module"""
        try:
            full_path = Path(PROJECT_ROOT) / module_path
            
            if not full_path.exists() or not full_path.suffix == '.py':
                raise ValueError(f"Invalid Python module: {module_path}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST for dependency analysis
            tree = ast.parse(content, filename=str(full_path))
            
            # Extract dependencies
            imports, dependencies = self._extract_dependencies(tree, content)
            exports = self._extract_exports(tree)
            
            # Calculate complexity score
            complexity_score = self._calculate_dependency_complexity(dependencies, imports)
            
            # Create dependency node
            node = DependencyNode(
                module_path=module_path,
                imports=imports,
                exports=exports,
                dependencies=dependencies,
                complexity_score=complexity_score,
                lines_of_code=len(content.split('\n'))
            )
            
            # Determine layer
            node.layer = self._determine_module_layer(module_path)
            
            self.dependency_nodes[module_path] = node
            
            self.logger.debug(f"Module analyzed: {module_path} ({len(dependencies)} dependencies)")
            
            return node
            
        except Exception as e:
            self.logger.error(f"Module analysis failed for {module_path}: {e}")
            raise
    
    def _extract_dependencies(self, tree: ast.AST, content: str) -> Tuple[List[str], Set[str]]:
        """Extract import dependencies from AST"""
        imports = []
        dependencies = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_name = alias.name
                    imports.append(import_name)
                    
                    # Add to dependencies if it's an internal module
                    if self._is_internal_module(import_name):
                        dependencies.add(import_name)
                        
                        # Create dependency edge
                        edge = DependencyEdge(
                            source="current_module",  # Will be updated
                            target=import_name,
                            dependency_type=DependencyType.DIRECT_IMPORT,
                            line_number=node.lineno,
                            import_statement=f"import {import_name}"
                        )
                        self.dependency_edges.append(edge)
            
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ''
                imports.append(module_name)
                
                if self._is_internal_module(module_name):
                    dependencies.add(module_name)
                    
                    # Create dependency edge for each imported name
                    for alias in node.names:
                        edge = DependencyEdge(
                            source="current_module",
                            target=module_name,
                            dependency_type=DependencyType.FROM_IMPORT,
                            line_number=node.lineno,
                            import_statement=f"from {module_name} import {alias.name}"
                        )
                        self.dependency_edges.append(edge)
        
        return imports, dependencies
    
    def _extract_exports(self, tree: ast.AST) -> List[str]:
        """Extract exported functions and classes"""
        exports = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not node.name.startswith('_'):  # Public functions/classes
                    exports.append(node.name)
        
        return exports
    
    def _is_internal_module(self, module_name: str) -> bool:
        """Check if module is internal to the project"""
        internal_prefixes = ['main_pc_code', 'pc2_code', 'common', 'events', 'common_utils']
        return any(module_name.startswith(prefix) for prefix in internal_prefixes)
    
    def _calculate_dependency_complexity(self, dependencies: Set[str], imports: List[str]) -> float:
        """Calculate dependency complexity score"""
        # Base complexity from number of dependencies
        base_complexity = len(dependencies)
        
        # Penalty for external dependencies
        external_count = len([imp for imp in imports if not self._is_internal_module(imp)])
        external_penalty = external_count * 0.5
        
        # Penalty for deep import chains
        deep_import_penalty = 0
        for imp in imports:
            if imp.count('.') > 2:  # Deep import chain
                deep_import_penalty += 1
        
        return base_complexity + external_penalty + deep_import_penalty
    
    def _determine_module_layer(self, module_path: str) -> Optional[str]:
        """Determine which architecture layer a module belongs to"""
        for layer_name, layer_def in self.layer_definitions.items():
            for layer_module in layer_def.modules:
                if module_path.startswith(layer_module):
                    return layer_name
        return None
    
    def _run_full_dependency_analysis(self) -> None:
        """Run full project dependency analysis"""
        self.logger.info("Starting full dependency analysis...")
        
        analysis_start = datetime.now()
        
        # Clear previous analysis
        if GRAPH_LIBS_AVAILABLE:
            self.dependency_graph.clear()
        self.dependency_nodes.clear()
        self.dependency_edges.clear()
        
        # Find all Python modules
        python_modules = []
        for directory in ['main_pc_code', 'pc2_code', 'common', 'events', 'common_utils']:
            dir_path = Path(PROJECT_ROOT) / directory
            if dir_path.exists():
                python_modules.extend(dir_path.rglob('*.py'))
        
        modules_analyzed = 0
        
        # Analyze each module
        for module_path in python_modules:
            try:
                relative_path = str(module_path.relative_to(PROJECT_ROOT))
                
                # Skip certain files
                if any(skip in relative_path for skip in ['__pycache__', '.git', 'venv', 'test_']):
                    continue
                
                node = asyncio.run(self.analyze_module_dependencies(relative_path))
                modules_analyzed += 1
                
                # Add to graph
                if GRAPH_LIBS_AVAILABLE:
                    self.dependency_graph.add_node(relative_path, **asdict(node))
                
            except Exception as e:
                self.logger.debug(f"Skipped module {module_path}: {e}")
        
        # Build dependency graph edges
        if GRAPH_LIBS_AVAILABLE:
            self._build_dependency_graph()
        
        # Update edges with correct source information
        self._update_dependency_edges()
        
        analysis_duration = (datetime.now() - analysis_start).total_seconds()
        
        # Update metrics
        self._update_dependency_metrics()
        
        # Record analysis in history
        self.analysis_history.append({
            'timestamp': analysis_start,
            'modules_analyzed': modules_analyzed,
            'total_dependencies': len(self.dependency_edges),
            'analysis_duration': analysis_duration
        })
        
        self.logger.info(f"Dependency analysis completed: {modules_analyzed} modules, {len(self.dependency_edges)} dependencies")
    
    def _build_dependency_graph(self) -> None:
        """Build the dependency graph with edges"""
        if not GRAPH_LIBS_AVAILABLE:
            return
        
        for module_path, node in self.dependency_nodes.items():
            for dependency in node.dependencies:
                # Find the actual module path for the dependency
                dependency_path = self._resolve_dependency_path(dependency)
                
                if dependency_path and dependency_path in self.dependency_nodes:
                    self.dependency_graph.add_edge(module_path, dependency_path)
                    
                    # Update dependents
                    self.dependency_nodes[dependency_path].dependents.add(module_path)
    
    def _resolve_dependency_path(self, dependency: str) -> Optional[str]:
        """Resolve dependency name to actual module path"""
        # This is a simplified resolution - real implementation would be more sophisticated
        for module_path in self.dependency_nodes.keys():
            if dependency in module_path or module_path.endswith(f"{dependency}.py"):
                return module_path
        return None
    
    def _update_dependency_edges(self) -> None:
        """Update dependency edges with correct source information"""
        for edge in self.dependency_edges:
            if edge.source == "current_module":
                # Find the actual source module for this edge
                # This would need more sophisticated tracking
                edge.source = "unknown"
    
    def _detect_circular_dependencies(self) -> None:
        """Detect circular dependencies in the dependency graph"""
        if not GRAPH_LIBS_AVAILABLE or self.dependency_graph.number_of_nodes() == 0:
            return
        
        try:
            # Find strongly connected components (cycles)
            cycles = list(nx.strongly_connected_components(self.dependency_graph))
            
            self.circular_dependencies.clear()
            
            for cycle in cycles:
                if len(cycle) > 1:  # Actual cycle (more than one node)
                    cycle_modules = list(cycle)
                    cycle_id = self._generate_cycle_id(cycle_modules)
                    
                    # Calculate cycle complexity
                    complexity_score = sum(
                        self.dependency_nodes[module].complexity_score 
                        for module in cycle_modules
                        if module in self.dependency_nodes
                    )
                    
                    # Suggest resolution
                    suggested_resolution = self._suggest_cycle_resolution(cycle_modules)
                    
                    # Find best breaking point
                    breaking_point = self._find_best_breaking_point(cycle_modules)
                    
                    circular_dep = CircularDependency(
                        cycle_id=cycle_id,
                        modules=cycle_modules,
                        cycle_length=len(cycle_modules),
                        complexity_score=complexity_score,
                        suggested_resolution=suggested_resolution,
                        breaking_point=breaking_point
                    )
                    
                    self.circular_dependencies[cycle_id] = circular_dep
                    
                    # Create dependency issue
                    issue = DependencyIssueReport(
                        issue_id=f"circular_{cycle_id}",
                        issue_type=DependencyIssue.CIRCULAR_DEPENDENCY,
                        priority=OptimizationPriority.HIGH if len(cycle_modules) > 2 else OptimizationPriority.MEDIUM,
                        affected_modules=cycle_modules,
                        description=f"Circular dependency detected: {circular_dep.cycle_description}",
                        impact_analysis="Circular dependencies can cause import errors and make code harder to test",
                        suggested_fix=suggested_resolution,
                        estimated_effort="4-8 hours"
                    )
                    
                    self.dependency_issues[issue.issue_id] = issue
            
            if self.circular_dependencies:
                self.logger.warning(f"Detected {len(self.circular_dependencies)} circular dependencies")
            
        except Exception as e:
            self.logger.error(f"Circular dependency detection failed: {e}")
    
    def _suggest_cycle_resolution(self, cycle_modules: List[str]) -> str:
        """Suggest resolution for circular dependency"""
        suggestions = [
            "Extract common interface or base class",
            "Use dependency injection",
            "Move shared functionality to a common module",
            "Apply the Dependency Inversion Principle",
            "Use late imports or import inside functions"
        ]
        
        # Choose suggestion based on cycle characteristics
        if len(cycle_modules) == 2:
            return suggestions[0]  # Interface extraction
        elif len(cycle_modules) > 3:
            return suggestions[2]  # Common module
        else:
            return suggestions[1]  # Dependency injection
    
    def _find_best_breaking_point(self, cycle_modules: List[str]) -> Optional[Tuple[str, str]]:
        """Find the best point to break the circular dependency"""
        if not GRAPH_LIBS_AVAILABLE or len(cycle_modules) < 2:
            return None
        
        # Find the edge with lowest "coupling strength"
        best_edge = None
        min_coupling = float('inf')
        
        for i in range(len(cycle_modules)):
            source = cycle_modules[i]
            target = cycle_modules[(i + 1) % len(cycle_modules)]
            
            # Calculate coupling strength (simplified)
            coupling_strength = self._calculate_coupling_strength(source, target)
            
            if coupling_strength < min_coupling:
                min_coupling = coupling_strength
                best_edge = (source, target)
        
        return best_edge
    
    def _calculate_coupling_strength(self, source: str, target: str) -> float:
        """Calculate coupling strength between two modules"""
        # Count the number of dependencies between the modules
        edge_count = sum(
            1 for edge in self.dependency_edges
            if edge.source == source and edge.target == target
        )
        
        # Factor in usage frequency
        usage_count = sum(
            edge.usage_count for edge in self.dependency_edges
            if edge.source == source and edge.target == target
        )
        
        return edge_count + (usage_count * 0.1)
    
    def _validate_layer_architecture(self) -> None:
        """Validate architecture layer constraints"""
        layer_violations = []
        
        for module_path, node in self.dependency_nodes.items():
            if not node.layer:
                continue
            
            layer_def = self.layer_definitions.get(node.layer)
            if not layer_def:
                continue
            
            # Check dependencies against allowed layers
            for dependency in node.dependencies:
                dep_module_path = self._resolve_dependency_path(dependency)
                if not dep_module_path:
                    continue
                
                dep_node = self.dependency_nodes.get(dep_module_path)
                if not dep_node or not dep_node.layer:
                    continue
                
                # Check if this dependency is allowed
                if (dep_node.layer not in layer_def.allowed_dependencies and
                    dep_node.layer in layer_def.forbidden_dependencies):
                    
                    violation = {
                        'source_module': module_path,
                        'source_layer': node.layer,
                        'target_module': dep_module_path,
                        'target_layer': dep_node.layer,
                        'violation_type': 'forbidden_dependency'
                    }
                    layer_violations.append(violation)
        
        # Create issues for layer violations
        for violation in layer_violations:
            issue = DependencyIssueReport(
                issue_id=f"layer_violation_{len(self.dependency_issues)}",
                issue_type=DependencyIssue.LAYER_VIOLATION,
                priority=OptimizationPriority.HIGH,
                affected_modules=[violation['source_module'], violation['target_module']],
                description=f"Layer violation: {violation['source_layer']} → {violation['target_layer']}",
                impact_analysis="Layer violations break architectural constraints and increase coupling",
                suggested_fix="Refactor to respect layer boundaries or update architecture definition",
                estimated_effort="2-4 hours"
            )
            
            self.dependency_issues[issue.issue_id] = issue
        
        self.dependency_metrics['layer_violations'] = len(layer_violations)
    
    def _detect_dead_imports(self) -> None:
        """Detect unused imports"""
        dead_imports = []
        
        for module_path, node in self.dependency_nodes.items():
            try:
                full_path = Path(PROJECT_ROOT) / module_path
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check each import for usage
                for import_name in node.imports:
                    if not self._is_import_used(content, import_name):
                        dead_imports.append({
                            'module': module_path,
                            'import': import_name,
                            'type': 'unused_import'
                        })
                        
            except Exception as e:
                self.logger.debug(f"Dead import detection failed for {module_path}: {e}")
        
        # Create issues for dead imports
        for dead_import in dead_imports:
            issue = DependencyIssueReport(
                issue_id=f"dead_import_{len(self.dependency_issues)}",
                issue_type=DependencyIssue.DEAD_IMPORT,
                priority=OptimizationPriority.LOW,
                affected_modules=[dead_import['module']],
                description=f"Unused import: {dead_import['import']}",
                impact_analysis="Dead imports increase module loading time and clutter code",
                suggested_fix="Remove unused import statement",
                estimated_effort="5 minutes"
            )
            
            self.dependency_issues[issue.issue_id] = issue
        
        self.dependency_metrics['dead_imports'] = len(dead_imports)
    
    def _is_import_used(self, content: str, import_name: str) -> bool:
        """Check if an import is actually used in the code"""
        # Simplified check - look for the import name in the content
        # Real implementation would be more sophisticated
        
        # Get the last part of the import name
        name_to_check = import_name.split('.')[-1]
        
        # Check if the name appears in the content (excluding the import line)
        lines = content.split('\n')
        non_import_lines = [
            line for line in lines 
            if not (line.strip().startswith('import ') or line.strip().startswith('from '))
        ]
        
        non_import_content = '\n'.join(non_import_lines)
        
        # Simple regex check for usage
        usage_pattern = rf'\b{re.escape(name_to_check)}\b'
        return bool(re.search(usage_pattern, non_import_content))
    
    def _analyze_coupling_complexity(self) -> None:
        """Analyze coupling complexity between modules"""
        coupling_issues = []
        
        for module_path, node in self.dependency_nodes.items():
            # High fan-out (many dependencies)
            if len(node.dependencies) > 10:
                coupling_issues.append({
                    'module': module_path,
                    'type': 'high_fan_out',
                    'count': len(node.dependencies),
                    'description': f"Module has {len(node.dependencies)} dependencies"
                })
            
            # High fan-in (many dependents)
            if len(node.dependents) > 15:
                coupling_issues.append({
                    'module': module_path,
                    'type': 'high_fan_in',
                    'count': len(node.dependents),
                    'description': f"Module has {len(node.dependents)} dependents"
                })
        
        # Create issues for coupling problems
        for coupling_issue in coupling_issues:
            priority = OptimizationPriority.HIGH if coupling_issue['count'] > 20 else OptimizationPriority.MEDIUM
            
            issue = DependencyIssueReport(
                issue_id=f"coupling_{len(self.dependency_issues)}",
                issue_type=DependencyIssue.COMPLEX_COUPLING,
                priority=priority,
                affected_modules=[coupling_issue['module']],
                description=coupling_issue['description'],
                impact_analysis="High coupling makes modules harder to test and modify",
                suggested_fix="Consider refactoring to reduce dependencies or split module",
                estimated_effort="4-8 hours"
            )
            
            self.dependency_issues[issue.issue_id] = issue
    
    def _suggest_optimizations(self) -> None:
        """Generate optimization suggestions"""
        # This would analyze patterns and suggest specific optimizations
    
    def _update_dependency_metrics(self) -> None:
        """Update dependency analysis metrics"""
        self.dependency_metrics.update({
            'total_modules': len(self.dependency_nodes),
            'total_dependencies': len(self.dependency_edges),
            'circular_dependencies': len(self.circular_dependencies),
            'average_coupling': sum(
                len(node.dependencies) for node in self.dependency_nodes.values()
            ) / max(len(self.dependency_nodes), 1)
        })
    
    def _generate_cycle_id(self, cycle_modules: List[str]) -> str:
        """Generate unique ID for circular dependency"""
        import hashlib
        content = '_'.join(sorted(cycle_modules))
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    async def generate_dependency_graph_visualization(self) -> Optional[str]:
        """Generate dependency graph visualization"""
        if not GRAPH_LIBS_AVAILABLE or self.dependency_graph.number_of_nodes() == 0:
            return None
        
        try:
            plt.figure(figsize=(12, 8))
            
            # Use spring layout for better visualization
            pos = nx.spring_layout(self.dependency_graph, k=1, iterations=50)
            
            # Draw nodes
            nx.draw_networkx_nodes(
                self.dependency_graph, pos,
                node_color='lightblue',
                node_size=500,
                alpha=0.7
            )
            
            # Draw edges
            nx.draw_networkx_edges(
                self.dependency_graph, pos,
                edge_color='gray',
                arrows=True,
                arrowsize=20,
                alpha=0.5
            )
            
            # Draw labels
            nx.draw_networkx_labels(
                self.dependency_graph, pos,
                font_size=8,
                font_weight='bold'
            )
            
            plt.title("Module Dependency Graph")
            plt.axis('off')
            
            # Save to file
            graph_path = Path(PROJECT_ROOT) / "dependency_graph.png"
            plt.savefig(graph_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"Dependency graph saved: {graph_path}")
            return str(graph_path)
            
        except Exception as e:
            self.logger.error(f"Graph visualization failed: {e}")
            return None
    
    def get_dependency_report(self) -> Dict[str, Any]:
        """Get comprehensive dependency analysis report"""
        # Top most coupled modules
        top_coupled = sorted(
            self.dependency_nodes.items(),
            key=lambda x: len(x[1].dependencies) + len(x[1].dependents),
            reverse=True
        )[:10]
        
        # Critical issues
        critical_issues = [
            issue for issue in self.dependency_issues.values()
            if issue.priority == OptimizationPriority.CRITICAL
        ]
        
        return {
            'analysis_summary': {
                'total_modules': len(self.dependency_nodes),
                'total_dependencies': len(self.dependency_edges),
                'circular_dependencies': len(self.circular_dependencies),
                'total_issues': len(self.dependency_issues),
                'critical_issues': len(critical_issues)
            },
            'dependency_metrics': self.dependency_metrics,
            'circular_dependencies': [
                {
                    'cycle_id': cycle.cycle_id,
                    'modules': cycle.modules,
                    'cycle_length': cycle.cycle_length,
                    'complexity_score': cycle.complexity_score,
                    'suggested_resolution': cycle.suggested_resolution,
                    'cycle_description': cycle.cycle_description
                }
                for cycle in self.circular_dependencies.values()
            ],
            'top_coupled_modules': [
                {
                    'module_path': module_path,
                    'dependencies': len(node.dependencies),
                    'dependents': len(node.dependents),
                    'complexity_score': node.complexity_score,
                    'layer': node.layer
                }
                for module_path, node in top_coupled
            ],
            'critical_issues': [
                {
                    'issue_id': issue.issue_id,
                    'issue_type': issue.issue_type.value,
                    'affected_modules': issue.affected_modules,
                    'description': issue.description,
                    'suggested_fix': issue.suggested_fix,
                    'estimated_effort': issue.estimated_effort
                }
                for issue in critical_issues
            ],
            'layer_analysis': {
                layer_name: {
                    'modules_count': len([
                        node for node in self.dependency_nodes.values()
                        if node.layer == layer_name
                    ]),
                    'allowed_dependencies': layer_def.allowed_dependencies,
                    'forbidden_dependencies': layer_def.forbidden_dependencies
                }
                for layer_name, layer_def in self.layer_definitions.items()
            },
            'analysis_history': [
                {
                    'timestamp': entry['timestamp'].isoformat(),
                    'modules_analyzed': entry['modules_analyzed'],
                    'total_dependencies': entry['total_dependencies'],
                    'analysis_duration': entry['analysis_duration']
                }
                for entry in list(self.analysis_history)[-10:]
            ]
        }
    
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
        """Shutdown the dependency optimizer"""
        # Clear analysis data
        if GRAPH_LIBS_AVAILABLE and self.dependency_graph:
            self.dependency_graph.clear()
        self.dependency_nodes.clear()
        self.dependency_edges.clear()
        self.circular_dependencies.clear()
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import asyncio
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_dependency_optimizer():
        optimizer = DependencyOptimizer(analysis_interval_hours=1)
        
        try:
            # Analyze a specific module
            node = await optimizer.analyze_module_dependencies("main_pc_code/agents/base_agent.py")
            print(f"Dependencies: {len(node.dependencies)}, Complexity: {node.complexity_score}")
            
            # Generate visualization if available
            graph_path = await optimizer.generate_dependency_graph_visualization()
            if graph_path:
                print(f"Dependency graph saved: {graph_path}")
            
            # Get comprehensive report
            report = optimizer.get_dependency_report()
            print(json.dumps(report, indent=2, default=str))
            
        finally:
            optimizer.shutdown()
    
    if GRAPH_LIBS_AVAILABLE:
        asyncio.run(test_dependency_optimizer())
    else:
        print("Graph libraries not available - skipping test") 