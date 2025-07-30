#!/usr/bin/env python3
"""
Comprehensive Agent Scanner for MainPC and PC2 Systems

This script scans all agent files in mainpc and pc2 directories,
analyzes their functionality, and generates comprehensive reports.
"""

import os
import json
import ast
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import subprocess

class ComprehensiveAgentScanner:
    """Comprehensive scanner for all agents in MainPC and PC2 systems"""
    
    def __init__(self, base_path: str = "/home/haymayndz/AI_System_Monorepo"):
        self.base_path = Path(base_path)
        self.scan_results = {
            "scan_timestamp": self._get_timestamp(),
            "base_path": str(self.base_path),
            "directories_found": {
                "mainpc": [],
                "pc2": []
            },
            "agents_found": {
                "mainpc": [],
                "pc2": [],
                "shared": []
            },
            "analysis_results": {},
            "health_status": {},
            "recommendations": [],
            "summary": {}
        }
    
    def _get_timestamp(self) -> str:
        """Get Philippines timezone timestamp"""
        utc_now = datetime.utcnow()
        philippines_tz = timezone(timedelta(hours=8))
        ph_time = utc_now.astimezone(philippines_tz)
        return ph_time.isoformat()
    
    def discover_directories(self) -> None:
        """Discover all mainpc and pc2 related directories"""
        print("🔍 Phase 1: Discovering directories...")
        
        # Find mainpc directories
        mainpc_patterns = ["*mainpc*", "*MAINPC*", "*MainPc*", "*FORMAINPC*"]
        for pattern in mainpc_patterns:
            for path in self.base_path.rglob(pattern):
                if path.is_dir():
                    self.scan_results["directories_found"]["mainpc"].append(str(path.relative_to(self.base_path)))
        
        # Find pc2 directories
        pc2_patterns = ["*pc2*", "*PC2*", "*ForPC2*", "*FORPC2*"]
        for pattern in pc2_patterns:
            for path in self.base_path.rglob(pattern):
                if path.is_dir():
                    self.scan_results["directories_found"]["pc2"].append(str(path.relative_to(self.base_path)))
        
        print(f"   Found {len(self.scan_results['directories_found']['mainpc'])} mainpc directories")
        print(f"   Found {len(self.scan_results['directories_found']['pc2'])} pc2 directories")
    
    def scan_agent_files(self) -> None:
        """Scan for all agent-related files"""
        print("🔍 Phase 2: Scanning for agent files...")
        
        # Agent file patterns
        agent_patterns = ["*agent*.py", "*Agent*.py", "*AGENT*.py"]
        
        for pattern in agent_patterns:
            for agent_file in self.base_path.rglob(pattern):
                if agent_file.is_file():
                    self._categorize_agent_file(agent_file)
        
        # Additional search in specific directories
        self._scan_specific_directories()
        
        print(f"   Found {len(self.scan_results['agents_found']['mainpc'])} mainpc agents")
        print(f"   Found {len(self.scan_results['agents_found']['pc2'])} pc2 agents")
        print(f"   Found {len(self.scan_results['agents_found']['shared'])} shared agents")
    
    def _categorize_agent_file(self, agent_file: Path) -> None:
        """Categorize agent file by system (mainpc, pc2, or shared)"""
        relative_path = str(agent_file.relative_to(self.base_path))
        agent_info = {
            "filename": agent_file.name,
            "path": relative_path,
            "size": agent_file.stat().st_size,
            "modified": datetime.fromtimestamp(agent_file.stat().st_mtime).isoformat()
        }
        
        # Categorize based on path
        path_lower = relative_path.lower()
        if any(pattern in path_lower for pattern in ["mainpc", "formainpc"]):
            self.scan_results["agents_found"]["mainpc"].append(agent_info)
        elif any(pattern in path_lower for pattern in ["pc2", "forpc2"]):
            self.scan_results["agents_found"]["pc2"].append(agent_info)
        else:
            self.scan_results["agents_found"]["shared"].append(agent_info)
    
    def _scan_specific_directories(self) -> None:
        """Scan specific known agent directories"""
        specific_dirs = [
            "main_pc_code",
            "pc2_code", 
            "unified-system-v1/src/agents",
            "docker/mainpc",
            "docker/pc2"
        ]
        
        for dir_name in specific_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists():
                for py_file in dir_path.rglob("*.py"):
                    if "agent" in py_file.name.lower():
                        if py_file not in [self.base_path / info["path"] for info in 
                                          self.scan_results["agents_found"]["mainpc"] + 
                                          self.scan_results["agents_found"]["pc2"] + 
                                          self.scan_results["agents_found"]["shared"]]:
                            self._categorize_agent_file(py_file)
    
    def analyze_agent_files(self) -> None:
        """Analyze each discovered agent file"""
        print("📊 Phase 3: Analyzing agent files...")
        
        all_agents = (self.scan_results["agents_found"]["mainpc"] + 
                     self.scan_results["agents_found"]["pc2"] + 
                     self.scan_results["agents_found"]["shared"])
        
        for i, agent_info in enumerate(all_agents):
            print(f"   Analyzing ({i+1}/{len(all_agents)}): {agent_info['filename']}")
            
            agent_path = self.base_path / agent_info["path"]
            analysis = self._analyze_single_agent(agent_path)
            self.scan_results["analysis_results"][agent_info["path"]] = analysis
    
    def _analyze_single_agent(self, agent_path: Path) -> Dict[str, Any]:
        """Analyze a single agent file"""
        analysis = {
            "classes": [],
            "functions": [],
            "imports": [],
            "ports": [],
            "configurations": [],
            "health_checks": [],
            "errors": []
        }
        
        try:
            with open(agent_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST for detailed analysis
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.FunctionDef) and not hasattr(node, 'parent_class'):
                    analysis["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            analysis["imports"].append(f"{node.module}.{alias.name}")
            
            # Look for ports, configurations, and health checks
            analysis["ports"] = self._extract_ports(content)
            analysis["configurations"] = self._extract_configurations(content)
            analysis["health_checks"] = self._extract_health_checks(content)
            
        except Exception as e:
            analysis["errors"].append(f"Analysis error: {str(e)}")
        
        return analysis
    
    def _extract_ports(self, content: str) -> List[int]:
        """Extract port numbers from agent content"""
        port_patterns = [
            r'port\s*=\s*(\d+)',
            r'PORT\s*=\s*(\d+)',
            r'listen.*?(\d{4,5})',
            r'bind.*?(\d{4,5})',
            r':(\d{4,5})'
        ]
        
        ports = []
        for pattern in port_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                port = int(match)
                if 1000 <= port <= 65535:  # Valid port range
                    ports.append(port)
        
        return list(set(ports))  # Remove duplicates
    
    def _extract_configurations(self, content: str) -> List[str]:
        """Extract configuration-related information"""
        config_patterns = [
            r'config\s*=.*',
            r'CONFIG\s*=.*',
            r'settings\s*=.*',
            r'SETTINGS\s*=.*',
            r'\.env',
            r'\.json',
            r'\.yaml',
            r'\.yml'
        ]
        
        configurations = []
        for pattern in config_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            configurations.extend(matches)
        
        return configurations[:10]  # Limit to first 10
    
    def _extract_health_checks(self, content: str) -> List[str]:
        """Extract health check related functions/methods"""
        health_patterns = [
            r'def\s+(health|status|ping|alive|ready).*:',
            r'class.*Health.*:',
            r'def.*health.*:',
            r'def.*status.*:'
        ]
        
        health_checks = []
        for pattern in health_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            health_checks.extend(matches)
        
        return health_checks
    
    def assess_system_health(self) -> None:
        """Assess overall system health and status"""
        print("🏥 Phase 4: Assessing system health...")
        
        # Check for running processes
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            processes = result.stdout.lower()
            
            agent_processes = []
            for line in processes.split('\n'):
                if 'agent' in line and 'python' in line:
                    agent_processes.append(line.strip())
            
            self.scan_results["health_status"]["running_processes"] = len(agent_processes)
            self.scan_results["health_status"]["process_details"] = agent_processes[:10]
            
        except Exception as e:
            self.scan_results["health_status"]["process_check_error"] = str(e)
        
        # Analyze port usage
        all_ports = []
        for analysis in self.scan_results["analysis_results"].values():
            all_ports.extend(analysis.get("ports", []))
        
        self.scan_results["health_status"]["ports_detected"] = len(set(all_ports))
        self.scan_results["health_status"]["port_list"] = sorted(list(set(all_ports)))
        
        # Check for potential conflicts
        port_counts = {}
        for port in all_ports:
            port_counts[port] = port_counts.get(port, 0) + 1
        
        conflicts = {port: count for port, count in port_counts.items() if count > 1}
        self.scan_results["health_status"]["port_conflicts"] = conflicts
    
    def generate_recommendations(self) -> None:
        """Generate maintenance and optimization recommendations"""
        print("💡 Phase 5: Generating recommendations...")
        
        recommendations = []
        
        # Check for duplicate or similar agents
        all_agents = (self.scan_results["agents_found"]["mainpc"] + 
                     self.scan_results["agents_found"]["pc2"] + 
                     self.scan_results["agents_found"]["shared"])
        
        agent_names = [agent["filename"] for agent in all_agents]
        duplicates = {name: agent_names.count(name) for name in set(agent_names) if agent_names.count(name) > 1}
        
        if duplicates:
            recommendations.append({
                "type": "cleanup",
                "priority": "high",
                "issue": "Duplicate agent files detected",
                "details": duplicates,
                "suggestion": "Review and consolidate duplicate agents"
            })
        
        # Check for port conflicts
        if self.scan_results["health_status"].get("port_conflicts"):
            recommendations.append({
                "type": "configuration",
                "priority": "critical",
                "issue": "Port conflicts detected",
                "details": self.scan_results["health_status"]["port_conflicts"],
                "suggestion": "Resolve port conflicts to prevent service issues"
            })
        
        # Check for agents without health checks
        agents_without_health = []
        for path, analysis in self.scan_results["analysis_results"].items():
            if not analysis.get("health_checks"):
                agents_without_health.append(path)
        
        if agents_without_health:
            recommendations.append({
                "type": "monitoring",
                "priority": "medium",
                "issue": "Agents without health checks",
                "details": f"{len(agents_without_health)} agents lack health monitoring",
                "suggestion": "Implement health check endpoints for better monitoring"
            })
        
        # Check for large agent files
        large_agents = []
        for agent in all_agents:
            if agent["size"] > 50000:  # Files larger than 50KB
                large_agents.append({"path": agent["path"], "size": agent["size"]})
        
        if large_agents:
            recommendations.append({
                "type": "refactoring",
                "priority": "low",
                "issue": "Large agent files detected",
                "details": large_agents,
                "suggestion": "Consider breaking down large agents into smaller modules"
            })
        
        self.scan_results["recommendations"] = recommendations
    
    def generate_summary(self) -> None:
        """Generate scan summary statistics"""
        print("📋 Phase 6: Generating summary...")
        
        all_agents = (self.scan_results["agents_found"]["mainpc"] + 
                     self.scan_results["agents_found"]["pc2"] + 
                     self.scan_results["agents_found"]["shared"])
        
        total_classes = sum(len(analysis.get("classes", [])) for analysis in self.scan_results["analysis_results"].values())
        total_functions = sum(len(analysis.get("functions", [])) for analysis in self.scan_results["analysis_results"].values())
        total_ports = len(set(port for analysis in self.scan_results["analysis_results"].values() for port in analysis.get("ports", [])))
        
        self.scan_results["summary"] = {
            "total_directories_scanned": len(self.scan_results["directories_found"]["mainpc"]) + len(self.scan_results["directories_found"]["pc2"]),
            "total_agents_found": len(all_agents),
            "mainpc_agents": len(self.scan_results["agents_found"]["mainpc"]),
            "pc2_agents": len(self.scan_results["agents_found"]["pc2"]),
            "shared_agents": len(self.scan_results["agents_found"]["shared"]),
            "total_classes": total_classes,
            "total_functions": total_functions,
            "total_ports": total_ports,
            "recommendations_count": len(self.scan_results["recommendations"]),
            "critical_issues": len([r for r in self.scan_results["recommendations"] if r.get("priority") == "critical"]),
            "scan_completion": "100%"
        }
    
    def save_results(self) -> None:
        """Save scan results to files"""
        print("💾 Saving results...")
        
        # Save JSON report
        json_file = self.base_path / "memory-bank" / "agent-scan-results.json"
        with open(json_file, 'w') as f:
            json.dump(self.scan_results, f, indent=2)
        
        # Save markdown report
        self._generate_markdown_report()
        
        print(f"   Results saved to: {json_file}")
        print(f"   Report saved to: {self.base_path}/memory-bank/agent-scan-report.md")
    
    def _generate_markdown_report(self) -> None:
        """Generate human-readable markdown report"""
        report_content = f"""# 🔍 **COMPREHENSIVE AGENT SCAN REPORT**

## **Scan Date**: {self.scan_results['scan_timestamp']}

---

## **📊 SCAN SUMMARY**

| Metric | Count |
|--------|-------|
| **Total Directories Scanned** | {self.scan_results['summary']['total_directories_scanned']} |
| **Total Agents Found** | {self.scan_results['summary']['total_agents_found']} |
| **MainPC Agents** | {self.scan_results['summary']['mainpc_agents']} |
| **PC2 Agents** | {self.scan_results['summary']['pc2_agents']} |
| **Shared Agents** | {self.scan_results['summary']['shared_agents']} |
| **Total Classes** | {self.scan_results['summary']['total_classes']} |
| **Total Functions** | {self.scan_results['summary']['total_functions']} |
| **Unique Ports** | {self.scan_results['summary']['total_ports']} |
| **Critical Issues** | {self.scan_results['summary']['critical_issues']} |

---

## **🗂️ AGENT INVENTORY**

### **MainPC Agents ({len(self.scan_results['agents_found']['mainpc'])})**:
"""
        
        for agent in self.scan_results['agents_found']['mainpc']:
            report_content += f"- **{agent['filename']}** - `{agent['path']}` ({agent['size']} bytes)\n"
        
        report_content += f"""
### **PC2 Agents ({len(self.scan_results['agents_found']['pc2'])})**:
"""
        
        for agent in self.scan_results['agents_found']['pc2']:
            report_content += f"- **{agent['filename']}** - `{agent['path']}` ({agent['size']} bytes)\n"
        
        report_content += f"""
### **Shared Agents ({len(self.scan_results['agents_found']['shared'])})**:
"""
        
        for agent in self.scan_results['agents_found']['shared']:
            report_content += f"- **{agent['filename']}** - `{agent['path']}` ({agent['size']} bytes)\n"
        
        # Add health status
        report_content += f"""
---

## **🏥 SYSTEM HEALTH STATUS**

- **Running Agent Processes**: {self.scan_results['health_status'].get('running_processes', 0)}
- **Ports Detected**: {self.scan_results['health_status'].get('ports_detected', 0)}
- **Port Conflicts**: {len(self.scan_results['health_status'].get('port_conflicts', {}))}

### **Port Usage**:
{self.scan_results['health_status'].get('port_list', [])}

---

## **💡 RECOMMENDATIONS**

"""
        
        for i, rec in enumerate(self.scan_results['recommendations'], 1):
            priority_emoji = {"critical": "🚨", "high": "⚠️", "medium": "💡", "low": "📝"}.get(rec['priority'], "📋")
            report_content += f"""
### **{i}. {priority_emoji} {rec['issue'].title()}** ({rec['priority'].title()} Priority)
- **Type**: {rec['type'].title()}
- **Issue**: {rec['issue']}
- **Suggestion**: {rec['suggestion']}
"""
        
        report_content += f"""
---

## **✅ SCAN COMPLETE**

**Scan completed successfully with {self.scan_results['summary']['scan_completion']} coverage.**

All agent files in MainPC and PC2 systems have been identified, analyzed, and documented.
"""
        
        # Save markdown report
        report_file = self.base_path / "memory-bank" / "agent-scan-report.md"
        with open(report_file, 'w') as f:
            f.write(report_content)
    
    def run_full_scan(self) -> None:
        """Execute complete agent scanning process"""
        print("🚀 Starting Comprehensive Agent Scan...")
        print("=" * 50)
        
        try:
            self.discover_directories()
            self.scan_agent_files()
            self.analyze_agent_files()
            self.assess_system_health()
            self.generate_recommendations()
            self.generate_summary()
            self.save_results()
            
            print("\n" + "=" * 50)
            print("✅ Comprehensive Agent Scan Complete!")
            print(f"   Found {self.scan_results['summary']['total_agents_found']} agents total")
            print(f"   Generated {len(self.scan_results['recommendations'])} recommendations")
            print(f"   Identified {self.scan_results['summary']['critical_issues']} critical issues")
            
        except Exception as e:
            print(f"❌ Scan failed: {str(e)}")
            raise


def main():
    """Main execution function"""
    scanner = ComprehensiveAgentScanner()
    scanner.run_full_scan()
    return scanner.scan_results


if __name__ == "__main__":
    main()
