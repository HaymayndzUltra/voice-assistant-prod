#!/usr/bin/env python3
"""
High-Risk Legacy Agent Identification Script
Analyzes the codebase to identify legacy agents that don't inherit from BaseAgent
and prioritizes them by risk factors for migration planning.
"""

import sys
import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

@dataclass
class AgentRiskAnalysis:
    """TODO: Add description for AgentRiskAnalysis."""
    name: str
    file_path: str
    risk_score: int
    risk_factors: List[str]
    complexity_score: int
    dependencies: List[str]
    uses_baseagent: bool
    file_size_kb: float
    lines_of_code: int

class HighRiskAgentIdentifier:
    """Identify and analyze high-risk legacy agents for migration priority"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.agents = []
        self.exclude_paths = [
            'archive', 'backups', 'test', '_test', 'deprecated',
            'ForPC2', 'needtoverify', '_trash'
        ]

    def should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from analysis"""
        return any(exclude in path for exclude in self.exclude_paths)

    def analyze_agent_file(self, file_path: Path) -> AgentRiskAnalysis:
        """Analyze a single agent file for risk factors"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Basic metrics
            lines_of_code = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith('#')])
            file_size_kb = file_path.stat().st_size / 1024

            # Check BaseAgent inheritance
            uses_baseagent = bool(re.search(r'class\s+\w+.*\(.*BaseAgent.*\)', content))

            # Extract class name
            class_match = re.search(r'class\s+(\w+Agent|\w+Service|\w+Manager)\s*\(', content)
            agent_name = class_match.group(1) if class_match else file_path.stem

            # Risk factor analysis
            risk_factors = []
            risk_score = 0

            # 1. No BaseAgent inheritance (highest risk)
            if not uses_baseagent:
                risk_factors.append("No BaseAgent inheritance")
                risk_score += 10

            # 2. Complex socket management
            if re.search(r'zmq\.socket|socket\.socket|asyncio\.start_server', content):
                risk_factors.append("Manual socket management")
                risk_score += 8

            # 3. Custom health check implementation
            if re.search(r'health.*check|/health|health.*endpoint', content, re.IGNORECASE):
                risk_factors.append("Custom health check logic")
                risk_score += 6

            # 4. Large file size (>50KB)
            if file_size_kb > 50:
                risk_factors.append(f"Large file size ({file_size_kb:.1f}KB)")
                risk_score += 4

            # 5. High complexity (>500 lines)
            if lines_of_code > 500:
                risk_factors.append(f"High complexity ({lines_of_code} lines)")
                risk_score += 5

            # 6. Threading/multiprocessing
            if re.search(r'threading|multiprocessing|Thread\(|Process\(', content):
                risk_factors.append("Manual threading/multiprocessing")
                risk_score += 7

            # 7. Database connections
            if re.search(r'sqlite3|psycopg2|mysql|redis|connect\(', content):
                risk_factors.append("Database connections")
                risk_score += 3

            # 8. Config management
            if re.search(r'config.*load|load.*config|yaml\.load|json\.load', content):
                risk_factors.append("Custom config management")
                risk_score += 2

            # Extract dependencies (imports and discovery calls)
            dependencies = []
            import_matches = re.findall(r'from\s+[\w.]+\s+import\s+([\w,\s]+)', content)
            for match in import_matches:
                dependencies.extend([dep.strip() for dep in match.split(',')])

            discover_matches = re.findall(r'discover\(["\'](\w+)["\']', content)
            dependencies.extend(discover_matches)

            complexity_score = lines_of_code + len(dependencies) * 5

            return AgentRiskAnalysis(
                name=agent_name,
                file_path=str(file_path.relative_to(self.project_root)),
                risk_score=risk_score,
                risk_factors=risk_factors,
                complexity_score=complexity_score,
                dependencies=list(set(dependencies)),
                uses_baseagent=uses_baseagent,
                file_size_kb=file_size_kb,
                lines_of_code=lines_of_code
            )

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def find_agent_files(self) -> List[Path]:
        """Find all agent files in the project"""
        agent_files = []

        # Search patterns for agent files
        patterns = ['*agent*.py', '*service*.py', '*manager*.py']
        search_dirs = ['main_pc_code/agents', 'pc2_code/agents']

        for search_dir in search_dirs:
            search_path = self.project_root / search_dir
            if search_path.exists():
                for pattern in patterns:
                    for file_path in search_path.rglob(pattern):
                        if not self.should_exclude_path(str(file_path)):
                            agent_files.append(file_path)

        return agent_files

    def analyze_all_agents(self) -> List[AgentRiskAnalysis]:
        """Analyze all agent files and return risk analysis"""
        agent_files = self.find_agent_files()
        print(f"🔍 Found {len(agent_files)} agent files to analyze")

        analyses = []
        for file_path in agent_files:
            analysis = self.analyze_agent_file(file_path)
            if analysis:
                analyses.append(analysis)

        return analyses

    def identify_top_risks(self, analyses: List[AgentRiskAnalysis], top_n: int = 3) -> List[AgentRiskAnalysis]:
        """Identify the top N highest-risk agents"""
        # Sort by risk score (descending), then by complexity (descending)
        sorted_analyses = sorted(
            analyses,
            key=lambda x: (x.risk_score, x.complexity_score),
            reverse=True
        )

        return sorted_analyses[:top_n]

    def generate_report(self, analyses: List[AgentRiskAnalysis], top_risks: List[AgentRiskAnalysis]):
        """Generate comprehensive risk analysis report"""
        print("\n" + "="*80)
        print("🚨 HIGH-RISK LEGACY AGENT MIGRATION ANALYSIS")
        print("="*80)

        print(f"\n📊 SUMMARY:")
        print(f"  Total Agents Analyzed: {len(analyses)}")
        legacy_count = len([a for a in analyses if not a.uses_baseagent])
        print(f"  Legacy Agents (No BaseAgent): {legacy_count}")
        print(f"  BaseAgent Compliant: {len(analyses) - legacy_count}")

        print(f"\n🎯 TOP 3 HIGHEST-RISK LEGACY AGENTS:")
        print("-" * 80)

        for i, agent in enumerate(top_risks, 1):
            print(f"\n{i}. {agent.name}")
            print(f"   📁 File: {agent.file_path}")
            print(f"   🚨 Risk Score: {agent.risk_score}/50")
            print(f"   📏 Size: {agent.file_size_kb:.1f}KB ({agent.lines_of_code} lines)")
            print(f"   🔗 Dependencies: {len(agent.dependencies)}")
            print(f"   ⚠️  Risk Factors:")
            for factor in agent.risk_factors:
                print(f"      • {factor}")

        # Save detailed JSON report
        report_data = {
            "analysis_summary": {
                "total_agents": len(analyses),
                "legacy_agents": legacy_count,
                "baseagent_compliant": len(analyses) - legacy_count
            },
            "top_risks": [
                {
                    "name": agent.name,
                    "file_path": agent.file_path,
                    "risk_score": agent.risk_score,
                    "risk_factors": agent.risk_factors,
                    "complexity_score": agent.complexity_score,
                    "dependencies": agent.dependencies,
                    "uses_baseagent": agent.uses_baseagent,
                    "file_size_kb": agent.file_size_kb,
                    "lines_of_code": agent.lines_of_code
                }
                for agent in top_risks
            ],
            "all_legacy_agents": [
                {
                    "name": agent.name,
                    "file_path": agent.file_path,
                    "risk_score": agent.risk_score,
                    "uses_baseagent": agent.uses_baseagent
                }
                for agent in analyses if not agent.uses_baseagent
            ]
        }

        report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_HIGH_RISK_AGENTS_ANALYSIS.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📋 Detailed report saved: {report_file}")

        return top_risks

def main():
    identifier = HighRiskAgentIdentifier()
    analyses = identifier.analyze_all_agents()
    top_risks = identifier.identify_top_risks(analyses, 3)
    identifier.generate_report(analyses, top_risks)

    print(f"\n✅ Analysis complete. Ready for Week 4 migration planning.")

if __name__ == "__main__":
    main()
