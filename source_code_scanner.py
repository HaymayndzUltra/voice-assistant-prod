#!/usr/bin/env python3
"""
Source Code Scanner
------------------
Advanced scanner that analyzes actual Python source code of agents to discover:
- Import dependencies between agents
- Health check implementations
- Function calls and method invocations
- Code quality issues
- Missing implementations
- Architecture patterns
"""

import os
import sys
import ast
import yaml
import json
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import re

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'
MAIN_PC_CONFIG_PATH = MAIN_PC_CODE / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PC2_CODE / 'config' / 'startup_config.yaml'

# Output paths
OUTPUT_DIR = PROJECT_ROOT / 'analysis_output'
SOURCE_GRAPH_OUTPUT = OUTPUT_DIR / 'source_code_dependency_graph.png'
SOURCE_REPORT_OUTPUT = OUTPUT_DIR / 'source_code_analysis.json'
HEALTH_CHECK_REPORT = OUTPUT_DIR / 'health_check_analysis.json'
CODE_QUALITY_REPORT = OUTPUT_DIR / 'code_quality_issues.json'
MISSING_IMPLEMENTATIONS = OUTPUT_DIR / 'missing_implementations.json'

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class CodeAnalysis:
    """Class to store code analysis results."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: List[str] = []
        self.classes: List[str] = []
        self.functions: List[str] = []
        self.health_checks: List[str] = []
        self.agent_dependencies: List[str] = []
        self.external_dependencies: List[str] = []
        self.issues: List[str] = []
        self.lines_of_code: int = 0
        self.complexity_score: int = 0

class SourceCodeScanner:
    """Advanced scanner for analyzing Python source code of agents."""
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.code_analysis: Dict[str, CodeAnalysis] = {}
        self.dependency_graph = nx.DiGraph()
        self.health_check_graph = nx.Graph()
        self.agent_files: Dict[str, str] = {}
        
    def scan_all_agents(self):
        """Scan all agent source code files."""
        print("🔍 Scanning agent source code files...")
        
        # Load configs to get agent file paths
        self._load_agent_configs()
        
        # Scan each agent's source code
        for agent_name, file_path in self.agent_files.items():
            if file_path and os.path.exists(file_path):
                print(f"  📁 Analyzing: {agent_name} -> {file_path}")
                self._analyze_agent_source(agent_name, file_path)
            else:
                print(f"  ❌ Missing file for {agent_name}: {file_path}")
        
        # Build dependency graphs
        self._build_dependency_graphs()
        
        print(f"✅ Analyzed {len(self.code_analysis)} agent source files")
    
    def _load_agent_configs(self):
        """Load agent configurations to get file paths."""
        # Load MainPC config
        if MAIN_PC_CONFIG_PATH.exists():
            with open(MAIN_PC_CONFIG_PATH, 'r') as f:
                mainpc_config = yaml.safe_load(f)
                self._extract_agent_files(mainpc_config, 'mainpc')
        
        # Load PC2 config
        if PC2_CONFIG_PATH.exists():
            with open(PC2_CONFIG_PATH, 'r') as f:
                pc2_config = yaml.safe_load(f)
                self._extract_agent_files(pc2_config, 'pc2')
    
    def _extract_agent_files(self, config: Dict[str, Any], config_type: str):
        """Extract agent file paths from config."""
        if config_type == 'mainpc':
            # MainPC uses agent_groups structure
            agent_groups = config.get('agent_groups', {})
            for group_name, group_data in agent_groups.items():
                if isinstance(group_data, dict):
                    for agent_name, agent_data in group_data.items():
                        if isinstance(agent_data, dict) and 'script_path' in agent_data:
                            script_path = agent_data.get('script_path', '')
                            if script_path:
                                # Fix path resolution for MainPC
                                if script_path.startswith('main_pc_code/'):
                                    # Remove the main_pc_code/ prefix since we're already in MAIN_PC_CODE
                                    relative_path = script_path.replace('main_pc_code/', '')
                                    full_path = MAIN_PC_CODE / relative_path
                                elif script_path.startswith('phase1_implementation/'):
                                    # Handle phase1_implementation paths - use PROJECT_ROOT
                                    full_path = PROJECT_ROOT / script_path
                                elif script_path.startswith('FORMAINPC/'):
                                    # Handle FORMAINPC paths
                                    full_path = MAIN_PC_CODE / script_path
                                else:
                                    full_path = MAIN_PC_CODE / script_path
                                self.agent_files[agent_name] = str(full_path)
        else:  # pc2
            pc2_services = config.get('pc2_services', [])
            for agent_data in pc2_services:
                if isinstance(agent_data, dict) and 'name' in agent_data:
                    name = agent_data.get('name')
                    script_path = agent_data.get('script_path', '')
                    if name and script_path:
                        # Fix path resolution for PC2
                        if script_path.startswith('pc2_code/'):
                            # Remove the pc2_code/ prefix since we're already in PC2_CODE
                            relative_path = script_path.replace('pc2_code/', '')
                            full_path = PC2_CODE / relative_path
                        elif script_path.startswith('phase1_implementation/'):
                            # Handle phase1_implementation paths - use PROJECT_ROOT
                            full_path = PROJECT_ROOT / script_path
                        else:
                            full_path = PC2_CODE / script_path
                        self.agent_files[name] = str(full_path)
    
    def _analyze_agent_source(self, agent_name: str, file_path: str):
        """Analyze a single agent's source code."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Create analysis object
            analysis = CodeAnalysis(file_path)
            analysis.lines_of_code = len(content.splitlines())
            
            # Analyze AST
            self._analyze_ast(tree, analysis, agent_name)
            
            # Store analysis
            self.code_analysis[agent_name] = analysis
            
        except Exception as e:
            print(f"  ❌ Error analyzing {agent_name}: {e}")
    
    def _analyze_ast(self, tree: ast.AST, analysis: CodeAnalysis, agent_name: str):
        """Analyze AST for imports, classes, functions, etc."""
        for node in ast.walk(tree):
            # Analyze imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.name)
                    self._categorize_dependency(alias.name, analysis, agent_name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    full_import = f"{module}.{alias.name}" if module else alias.name
                    analysis.imports.append(full_import)
                    self._categorize_dependency(full_import, analysis, agent_name)
            
            # Analyze classes
            elif isinstance(node, ast.ClassDef):
                analysis.classes.append(node.name)
                self._analyze_class_methods(node, analysis)
            
            # Analyze functions
            elif isinstance(node, ast.FunctionDef):
                analysis.functions.append(node.name)
                self._analyze_function_content(node, analysis)
    
    def _categorize_dependency(self, import_name: str, analysis: CodeAnalysis, agent_name: str):
        """Categorize imports as agent dependencies or external."""
        # Check if it's an agent dependency
        if import_name in self.agent_files:
            analysis.agent_dependencies.append(import_name)
        else:
            # Check for common patterns
            if any(pattern in import_name.lower() for pattern in [
                'agent', 'service', 'manager', 'orchestrator', 'coordinator'
            ]):
                analysis.agent_dependencies.append(import_name)
            else:
                analysis.external_dependencies.append(import_name)
    
    def _analyze_class_methods(self, class_node: ast.ClassDef, analysis: CodeAnalysis):
        """Analyze methods within a class."""
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                method_name = node.name
                analysis.functions.append(f"{class_node.name}.{method_name}")
                
                # Check for health check methods
                if any(health_pattern in method_name.lower() for health_pattern in [
                    'health', 'check', 'status', 'ping', 'alive', 'ready'
                ]):
                    analysis.health_checks.append(f"{class_node.name}.{method_name}")
                
                self._analyze_function_content(node, analysis)
    
    def _analyze_function_content(self, func_node: ast.FunctionDef, analysis: CodeAnalysis):
        """Analyze function content for health checks and other patterns."""
        # Check function name for health patterns
        if any(health_pattern in func_node.name.lower() for health_pattern in [
            'health', 'check', 'status', 'ping', 'alive', 'ready', 'monitor'
        ]):
            analysis.health_checks.append(func_node.name)
        
        # Analyze function body for health check implementations
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'attr'):
                    func_name = node.func.attr
                    if any(health_pattern in func_name.lower() for health_pattern in [
                        'health', 'check', 'status', 'ping', 'alive', 'ready'
                    ]):
                        analysis.health_checks.append(f"{func_node.name}->{func_name}")
    
    def _build_dependency_graphs(self):
        """Build dependency and health check graphs."""
        print("🔗 Building dependency graphs...")
        
        # Add nodes to dependency graph
        for agent_name in self.agent_files:
            self.dependency_graph.add_node(agent_name)
        
        # Add edges based on imports
        for agent_name, analysis in self.code_analysis.items():
            for dependency in analysis.agent_dependencies:
                if dependency in self.agent_files:
                    self.dependency_graph.add_edge(agent_name, dependency)
        
        # Build health check graph
        for agent_name, analysis in self.code_analysis.items():
            if analysis.health_checks:
                self.health_check_graph.add_node(agent_name, health_checks=len(analysis.health_checks))
    
    def detect_issues(self):
        """Detect various code quality and implementation issues."""
        print("🔍 Detecting code issues...")
        
        all_issues = []
        
        for agent_name, analysis in self.code_analysis.items():
            agent_issues = []
            
            # Check for missing health checks
            if not analysis.health_checks:
                agent_issues.append("No health check methods found")
            
            # Check for circular dependencies
            if agent_name in self.dependency_graph:
                try:
                    cycles = list(nx.simple_cycles(self.dependency_graph))
                    for cycle in cycles:
                        if agent_name in cycle:
                            agent_issues.append(f"Circular dependency in cycle: {' -> '.join(cycle)}")
                except nx.NetworkXNoCycle:
                    pass
            
            # Check for high complexity
            if analysis.lines_of_code > 1000:
                agent_issues.append(f"Large file: {analysis.lines_of_code} lines")
            
            # Check for missing common patterns
            if not any('main' in func.lower() for func in analysis.functions):
                agent_issues.append("No main function or entry point found")
            
            if agent_issues:
                all_issues.append({
                    'agent': agent_name,
                    'issues': agent_issues
                })
        
        return all_issues
    
    def generate_visualizations(self):
        """Generate visual graphs."""
        print("📊 Generating visualizations...")
        
        # Dependency graph
        plt.figure(figsize=(20, 15))
        pos = nx.spring_layout(self.dependency_graph, seed=42)
        
        # Color nodes by health check status
        node_colors = []
        for node in self.dependency_graph.nodes():
            if node in self.code_analysis and self.code_analysis[node].health_checks:
                node_colors.append('lightgreen')  # Has health checks
            else:
                node_colors.append('lightcoral')  # No health checks
        
        nx.draw_networkx_nodes(self.dependency_graph, pos, node_color=node_colors, node_size=800)
        nx.draw_networkx_edges(self.dependency_graph, pos, edge_color='gray', arrows=True)
        nx.draw_networkx_labels(self.dependency_graph, pos, font_size=10)
        
        plt.title("Agent Source Code Dependencies\nGreen = Has Health Checks, Red = No Health Checks")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(SOURCE_GRAPH_OUTPUT, format='png', dpi=300)
        plt.close()
        
        print(f"📈 Dependency graph saved to {SOURCE_GRAPH_OUTPUT}")
    
    def generate_reports(self):
        """Generate comprehensive reports."""
        print("📋 Generating reports...")
        
        # Main analysis report
        analysis_report = {
            'total_agents': len(self.agent_files),
            'analyzed_agents': len(self.code_analysis),
            'agents_with_health_checks': sum(1 for a in self.code_analysis.values() if a.health_checks),
            'total_dependencies': sum(len(a.agent_dependencies) for a in self.code_analysis.values()),
            'detailed_analysis': {
                agent_name: {
                    'file_path': analysis.file_path,
                    'lines_of_code': analysis.lines_of_code,
                    'classes': analysis.classes,
                    'functions': analysis.functions,
                    'health_checks': analysis.health_checks,
                    'agent_dependencies': analysis.agent_dependencies,
                    'external_dependencies': analysis.external_dependencies
                }
                for agent_name, analysis in self.code_analysis.items()
            }
        }
        
        with open(SOURCE_REPORT_OUTPUT, 'w') as f:
            json.dump(analysis_report, f, indent=2)
        
        # Health check specific report
        health_report = {
            'agents_with_health_checks': [],
            'agents_without_health_checks': [],
            'health_check_methods': {}
        }
        
        for agent_name, analysis in self.code_analysis.items():
            if analysis.health_checks:
                health_report['agents_with_health_checks'].append(agent_name)
                health_report['health_check_methods'][agent_name] = analysis.health_checks
            else:
                health_report['agents_without_health_checks'].append(agent_name)
        
        with open(HEALTH_CHECK_REPORT, 'w') as f:
            json.dump(health_report, f, indent=2)
        
        # Code quality issues report
        issues = self.detect_issues()
        with open(CODE_QUALITY_REPORT, 'w') as f:
            json.dump(issues, f, indent=2)
        
        # Missing implementations report
        missing_impl = {
            'agents_without_health_checks': health_report['agents_without_health_checks'],
            'agents_with_issues': [issue['agent'] for issue in issues]
        }
        
        with open(MISSING_IMPLEMENTATIONS, 'w') as f:
            json.dump(missing_impl, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("📊 SOURCE CODE ANALYSIS SUMMARY")
        print("="*50)
        print(f"Total agents: {len(self.agent_files)}")
        print(f"Successfully analyzed: {len(self.code_analysis)}")
        print(f"Agents with health checks: {health_report['agents_with_health_checks']}")
        print(f"Agents without health checks: {health_report['agents_without_health_checks']}")
        print(f"Total issues found: {len(issues)}")
        print(f"\n📁 Reports saved to:")
        print(f"  - {SOURCE_REPORT_OUTPUT}")
        print(f"  - {HEALTH_CHECK_REPORT}")
        print(f"  - {CODE_QUALITY_REPORT}")
        print(f"  - {MISSING_IMPLEMENTATIONS}")
        print(f"  - {SOURCE_GRAPH_OUTPUT}")

def main():
    """Main function."""
    print("🚀 Starting Source Code Scanner...")
    
    scanner = SourceCodeScanner()
    scanner.scan_all_agents()
    scanner.generate_visualizations()
    scanner.generate_reports()
    
    print("\n✅ Source code analysis complete!")

if __name__ == "__main__":
    main() 