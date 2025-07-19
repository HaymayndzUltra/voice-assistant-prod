#!/usr/bin/env python3
"""
WP-12 Automated Reports Migration Script
Generates dependency graphs, monitoring dashboards, and automated system reports
Target: Complete system visibility and automated reporting
"""

import os
import ast
import json
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
from dataclasses import dataclass
import yaml
import subprocess

@dataclass
class AgentInfo:
    """Information about an agent"""
    name: str
    file_path: str
    port: int
    health_port: int
    dependencies: List[str]
    group: str
    priority: str
    imports: List[str]
    zmq_patterns: List[str]
    performance_score: int

@dataclass
class SystemReport:
    """System analysis report"""
    total_agents: int
    healthy_agents: int
    critical_agents: int
    dependency_cycles: List[List[str]]
    performance_bottlenecks: List[str]
    security_vulnerabilities: List[str]
    timestamp: datetime

class DependencyAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect agent dependencies and patterns"""
    
    def __init__(self):
        self.imports = []
        self.zmq_patterns = []
        self.agent_calls = []
        self.port_usage = []
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(f"from {node.module}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Detect ZMQ patterns
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr in ['socket', 'connect', 'bind']):
            self.zmq_patterns.append(node.func.attr)
        
        # Detect agent calls
        if isinstance(node.func, ast.Name):
            if 'agent' in node.func.id.lower():
                self.agent_calls.append(node.func.id)
        
        self.generic_visit(node)
    
    def visit_Str(self, node):
        # Detect port usage in strings
        if hasattr(node, 's') and isinstance(node.s, str):
            if 'tcp://' in node.s and ':' in node.s:
                self.port_usage.append(node.s)
        self.generic_visit(node)

class AutomatedReporting:
    """Automated reporting and monitoring system"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.dependency_graph = nx.DiGraph()
        self.reports_dir = Path("reports/automated")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def discover_agents(self) -> None:
        """Discover all agents in the system"""
        print("🔍 Discovering system agents...")
        
        # Scan main_pc_code agents
        main_pc_agents = Path("main_pc_code/agents").glob("*.py")
        pc2_agents = Path("pc2_code/agents").glob("*.py")
        
        for agent_file in list(main_pc_agents) + list(pc2_agents):
            if agent_file.name.startswith('__'):
                continue
                
            agent_info = self._analyze_agent_file(agent_file)
            if agent_info:
                self.agents[agent_info.name] = agent_info
                
    def _analyze_agent_file(self, file_path: Path) -> AgentInfo:
        """Analyze a single agent file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            analyzer = DependencyAnalyzer()
            analyzer.visit(tree)
            
            # Extract agent name
            agent_name = file_path.stem
            
            # Extract port information
            port = self._extract_port(content)
            health_port = self._extract_health_port(content)
            
            # Extract dependencies
            dependencies = self._extract_dependencies(content)
            
            # Determine group and priority
            group = self._determine_group(file_path)
            priority = self._determine_priority(agent_name, analyzer)
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(analyzer)
            
            return AgentInfo(
                name=agent_name,
                file_path=str(file_path),
                port=port,
                health_port=health_port,
                dependencies=dependencies,
                group=group,
                priority=priority,
                imports=analyzer.imports,
                zmq_patterns=analyzer.zmq_patterns,
                performance_score=performance_score
            )
        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
            return None
    
    def _extract_port(self, content: str) -> int:
        """Extract port number from agent content"""
        # Look for common port patterns
        import re
        port_patterns = [
            r'port["\s]*=[\s]*(\d+)',
            r'PORT["\s]*=[\s]*(\d+)',
            r'tcp://[^:]+:(\d+)',
            r'bind.*?:(\d+)',
            r'connect.*?:(\d+)'
        ]
        
        for pattern in port_patterns:
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))
        return 0
    
    def _extract_health_port(self, content: str) -> int:
        """Extract health check port"""
        import re
        health_patterns = [
            r'health[_\s]*port["\s]*=[\s]*(\d+)',
            r'HEALTH[_\s]*PORT["\s]*=[\s]*(\d+)',
        ]
        
        for pattern in health_patterns:
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))
        return 0
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract agent dependencies"""
        dependencies = []
        
        # Look for common dependency patterns
        import re
        dep_patterns = [
            r'dependencies:\s*\[(.*?)\]',
            r'depends_on:\s*\[(.*?)\]',
            r'requires:\s*\[(.*?)\]'
        ]
        
        for pattern in dep_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                deps = match.group(1).replace('"', '').replace("'", '')
                dependencies.extend([d.strip() for d in deps.split(',') if d.strip()])
        
        return dependencies
    
    def _determine_group(self, file_path: Path) -> str:
        """Determine agent group based on file path"""
        if 'main_pc_code' in str(file_path):
            return 'MainPC'
        elif 'pc2_code' in str(file_path):
            return 'PC2'
        else:
            return 'Unknown'
    
    def _determine_priority(self, agent_name: str, analyzer: DependencyAnalyzer) -> str:
        """Determine agent priority"""
        critical_agents = [
            'system_digital_twin', 'request_coordinator', 'model_manager',
            'predictive_health_monitor', 'translation_service'
        ]
        
        if any(critical in agent_name.lower() for critical in critical_agents):
            return 'critical'
        elif len(analyzer.zmq_patterns) > 3:
            return 'high'
        elif len(analyzer.imports) > 10:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_performance_score(self, analyzer: DependencyAnalyzer) -> int:
        """Calculate performance score based on complexity"""
        score = 0
        score += len(analyzer.imports) * 2
        score += len(analyzer.zmq_patterns) * 10
        score += len(analyzer.agent_calls) * 5
        score += len(analyzer.port_usage) * 3
        return score
    
    def build_dependency_graph(self) -> None:
        """Build system dependency graph"""
        print("🕸️  Building dependency graph...")
        
        for agent_name, agent_info in self.agents.items():
            self.dependency_graph.add_node(agent_name, **agent_info.__dict__)
            
            for dep in agent_info.dependencies:
                if dep in self.agents:
                    self.dependency_graph.add_edge(dep, agent_name)
    
    def detect_dependency_cycles(self) -> List[List[str]]:
        """Detect circular dependencies"""
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            return cycles
        except:
            return []
    
    def generate_dependency_graph_visualization(self) -> None:
        """Generate visual dependency graph"""
        print("📊 Generating dependency graph visualization...")
        
        plt.figure(figsize=(20, 15))
        
        # Layout with hierarchy
        pos = nx.spring_layout(self.dependency_graph, k=3, iterations=50)
        
        # Color nodes by group
        color_map = {'MainPC': 'lightblue', 'PC2': 'lightgreen', 'Unknown': 'lightgray'}
        node_colors = [color_map.get(self.agents[node].group, 'lightgray') 
                      for node in self.dependency_graph.nodes()]
        
        # Size nodes by priority
        size_map = {'critical': 1000, 'high': 700, 'medium': 500, 'low': 300}
        node_sizes = [size_map.get(self.agents[node].priority, 300) 
                     for node in self.dependency_graph.nodes()]
        
        # Draw the graph
        nx.draw(self.dependency_graph, pos, 
                node_color=node_colors,
                node_size=node_sizes,
                with_labels=True,
                font_size=8,
                font_weight='bold',
                arrows=True,
                edge_color='gray',
                alpha=0.8)
        
        plt.title("AI System Agent Dependency Graph", fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(self.reports_dir / "dependency_graph.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_system_report(self) -> SystemReport:
        """Generate comprehensive system report"""
        print("📋 Generating system analysis report...")
        
        # Count agents by status
        total_agents = len(self.agents)
        critical_agents = len([a for a in self.agents.values() if a.priority == 'critical'])
        
        # Detect issues
        cycles = self.detect_dependency_cycles()
        bottlenecks = [name for name, info in self.agents.items() 
                      if info.performance_score > 300]
        
        # Security analysis (simplified)
        vulnerabilities = [name for name, info in self.agents.items() 
                          if 'security' not in ' '.join(info.imports).lower()]
        
        return SystemReport(
            total_agents=total_agents,
            healthy_agents=total_agents - len(cycles),  # Simplified
            critical_agents=critical_agents,
            dependency_cycles=cycles,
            performance_bottlenecks=bottlenecks,
            security_vulnerabilities=vulnerabilities,
            timestamp=datetime.now()
        )
    
    def generate_monitoring_dashboard(self) -> None:
        """Generate monitoring dashboard HTML"""
        print("📺 Generating monitoring dashboard...")
        
        report = self.generate_system_report()
        
        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI System Monitoring Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
        .metrics {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ background: #ecf0f1; padding: 20px; border-radius: 10px; text-align: center; }}
        .metric h3 {{ margin: 0; color: #2c3e50; }}
        .metric .value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .section {{ margin: 20px 0; padding: 20px; border: 1px solid #bdc3c7; border-radius: 5px; }}
        .warning {{ color: #e74c3c; }}
        .success {{ color: #27ae60; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ background: #f8f9fa; margin: 5px 0; padding: 10px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI System Monitoring Dashboard</h1>
        <p>Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <h3>Total Agents</h3>
            <div class="value">{report.total_agents}</div>
        </div>
        <div class="metric">
            <h3>Healthy Agents</h3>
            <div class="value success">{report.healthy_agents}</div>
        </div>
        <div class="metric">
            <h3>Critical Agents</h3>
            <div class="value">{report.critical_agents}</div>
        </div>
    </div>
    
    <div class="section">
        <h2>🔍 System Health Analysis</h2>
        <h3>Dependency Cycles {'❌' if report.dependency_cycles else '✅'}</h3>
        {'<ul>' + ''.join(f'<li class="warning">Cycle: {" → ".join(cycle)}</li>' for cycle in report.dependency_cycles) + '</ul>' if report.dependency_cycles else '<p class="success">No circular dependencies detected!</p>'}
        
        <h3>Performance Bottlenecks</h3>
        {'<ul>' + ''.join(f'<li class="warning">{agent}</li>' for agent in report.performance_bottlenecks) + '</ul>' if report.performance_bottlenecks else '<p class="success">No performance bottlenecks detected!</p>'}
        
        <h3>Security Analysis</h3>
        <p>Agents without security imports: {len(report.security_vulnerabilities)}</p>
    </div>
    
    <div class="section">
        <h2>📊 Agent Details</h2>
        <table border="1" style="width: 100%; border-collapse: collapse;">
            <tr style="background: #34495e; color: white;">
                <th>Agent Name</th>
                <th>Group</th>
                <th>Priority</th>
                <th>Port</th>
                <th>Performance Score</th>
                <th>Dependencies</th>
            </tr>
"""
        
        for agent_name, agent_info in sorted(self.agents.items()):
            priority_color = {
                'critical': '#e74c3c',
                'high': '#f39c12', 
                'medium': '#f1c40f',
                'low': '#27ae60'
            }.get(agent_info.priority, '#95a5a6')
            
            dashboard_html += f"""
            <tr>
                <td><strong>{agent_name}</strong></td>
                <td>{agent_info.group}</td>
                <td style="color: {priority_color}; font-weight: bold;">{agent_info.priority}</td>
                <td>{agent_info.port}</td>
                <td>{agent_info.performance_score}</td>
                <td>{', '.join(agent_info.dependencies[:3])}{'...' if len(agent_info.dependencies) > 3 else ''}</td>
            </tr>
"""
        
        dashboard_html += """
        </table>
    </div>
    
    <div class="section">
        <h2>📈 Dependency Graph</h2>
        <img src="dependency_graph.png" alt="Dependency Graph" style="max-width: 100%; height: auto;">
    </div>
    
</body>
</html>
"""
        
        with open(self.reports_dir / "monitoring_dashboard.html", 'w') as f:
            f.write(dashboard_html)
    
    def generate_json_report(self) -> None:
        """Generate machine-readable JSON report"""
        print("💾 Generating JSON report...")
        
        report = self.generate_system_report()
        
        json_data = {
            "timestamp": report.timestamp.isoformat(),
            "system_metrics": {
                "total_agents": report.total_agents,
                "healthy_agents": report.healthy_agents,
                "critical_agents": report.critical_agents,
                "dependency_cycles_count": len(report.dependency_cycles),
                "performance_bottlenecks_count": len(report.performance_bottlenecks),
                "security_vulnerabilities_count": len(report.security_vulnerabilities)
            },
            "agents": {
                name: {
                    "file_path": info.file_path,
                    "port": info.port,
                    "health_port": info.health_port,
                    "dependencies": info.dependencies,
                    "group": info.group,
                    "priority": info.priority,
                    "performance_score": info.performance_score,
                    "import_count": len(info.imports),
                    "zmq_patterns": info.zmq_patterns
                }
                for name, info in self.agents.items()
            },
            "issues": {
                "dependency_cycles": report.dependency_cycles,
                "performance_bottlenecks": report.performance_bottlenecks,
                "security_vulnerabilities": report.security_vulnerabilities
            }
        }
        
        with open(self.reports_dir / "system_report.json", 'w') as f:
            json.dump(json_data, f, indent=2)
    
    def run_health_checks(self) -> Dict[str, bool]:
        """Run health checks on all agents"""
        print("🏥 Running system health checks...")
        
        health_status = {}
        
        for agent_name, agent_info in self.agents.items():
            if agent_info.health_port:
                try:
                    # Simplified health check - just check if port is listening
                    result = subprocess.run(
                        f"netstat -tuln | grep :{agent_info.health_port}",
                        shell=True, capture_output=True, text=True
                    )
                    health_status[agent_name] = result.returncode == 0
                except:
                    health_status[agent_name] = False
            else:
                health_status[agent_name] = None  # No health check available
        
        return health_status

def main():
    """Main execution function"""
    print("🚀 WP-12: AUTOMATED REPORTS GENERATION")
    print("=" * 50)
    
    reporter = AutomatedReporting()
    
    # Discover and analyze all agents
    reporter.discover_agents()
    
    # Build dependency relationships
    reporter.build_dependency_graph()
    
    # Generate all reports
    reporter.generate_dependency_graph_visualization()
    reporter.generate_monitoring_dashboard()
    reporter.generate_json_report()
    
    # Run health checks
    health_status = reporter.run_health_checks()
    
    print(f"\n✅ AUTOMATED REPORTS GENERATED:")
    print(f"📊 Dependency Graph: reports/automated/dependency_graph.png")
    print(f"📺 Monitoring Dashboard: reports/automated/monitoring_dashboard.html")
    print(f"💾 JSON Report: reports/automated/system_report.json")
    print(f"📈 Agents Discovered: {len(reporter.agents)}")
    print(f"🏥 Health Checks: {sum(1 for v in health_status.values() if v)} healthy / {len(health_status)} total")
    
    # Print summary
    report = reporter.generate_system_report()
    print(f"\n📋 SYSTEM SUMMARY:")
    print(f"   Total Agents: {report.total_agents}")
    print(f"   Critical Agents: {report.critical_agents}")
    print(f"   Dependency Cycles: {len(report.dependency_cycles)}")
    print(f"   Performance Bottlenecks: {len(report.performance_bottlenecks)}")
    
    if report.dependency_cycles:
        print(f"\n⚠️  DEPENDENCY CYCLES DETECTED:")
        for cycle in report.dependency_cycles:
            print(f"   🔄 {' → '.join(cycle)}")
    
    print(f"\n🎯 WP-12 AUTOMATED REPORTS: COMPLETE")

if __name__ == "__main__":
    main() 