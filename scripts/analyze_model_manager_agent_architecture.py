#!/usr/bin/env python3
"""
ModelManagerAgent Architecture Analysis Script
Deep analysis of the ModelManagerAgent for Phase 1 Week 4 Day 1
Analyzes socket management, threading, dependencies, and migration requirements.
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
class SocketPattern:
    """TODO: Add description for SocketPattern."""
    line_num: int
    pattern: str
    context: str
    risk_level: str

@dataclass
    """TODO: Add description for ThreadPattern."""
class ThreadPattern:
    line_num: int
    thread_name: str
    target_function: str
    purpose: str

     """TODO: Add description for DependencyPattern."""
@dataclass
class DependencyPattern:
    line_num: int
    import_type: str
    module: str
    usage_context: str

class ModelManagerAgentAnalyzer:
    """Comprehensive architecture analysis for ModelManagerAgent"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.mma_file = self.project_root / "main_pc_code" / "agents" / "model_manager_agent.py"
        self.analysis_results = {
            "file_info": {},
            "socket_patterns": [],
            "threading_patterns": [],
            "dependency_patterns": [],
            "baseagent_usage": {},
            "critical_functions": [],
            "migration_risk_assessment": {},
            "migration_strategy": {}
        }

    def analyze_file_structure(self):
        """Analyze basic file structure and metrics"""
        print("🔍 ANALYZING MODELMANAGERAGENT FILE STRUCTURE")
        print("=" * 60)

        with open(self.mma_file, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        file_size_kb = self.mma_file.stat().st_size / 1024
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

        self.analysis_results["file_info"] = {
            "total_lines": len(lines),
            "code_lines": code_lines,
            "file_size_kb": file_size_kb,
            "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
            "blank_lines": len([line for line in lines if not line.strip()])
        }

        print(f"📏 File Size: {file_size_kb:.1f}KB")
        print(f"📄 Total Lines: {len(lines)}")
        print(f"💻 Code Lines: {code_lines}")
        print(f"📝 Comment Lines: {self.analysis_results['file_info']['comment_lines']}")

        return content, lines

    def analyze_socket_management(self, content: str):
        """Analyze socket management patterns"""
        print("\n🔌 ANALYZING SOCKET MANAGEMENT PATTERNS")
        print("-" * 60)

        socket_patterns = []
        lines = content.split('\n')

        # ZMQ socket patterns
        zmq_patterns = [
            (r'zmq\.socket\(', "ZMQ socket creation"),
            (r'socket\.connect\(', "ZMQ socket connection"),
            (r'socket\.bind\(', "ZMQ socket binding"),
            (r'socket\.send\(', "ZMQ socket send"),
            (r'socket\.recv\(', "ZMQ socket receive"),
            (r'context\.socket\(', "ZMQ context socket creation")
        ]

        # Regular socket patterns
        socket_patterns_list = [
            (r'socket\.socket\(', "Raw socket creation"),
            (r'socket\.bind\(', "Raw socket binding"),
            (r'socket\.connect\(', "Raw socket connection")
        ]

        for i, line in enumerate(lines, 1):
            for pattern, description in zmq_patterns + socket_patterns_list:
                if re.search(pattern, line):
                    risk_level = "HIGH" if "raw socket" in description.lower() else "MEDIUM"
                    socket_patterns.append(SocketPattern(
                        line_num=i,
                        pattern=pattern,
                        context=line.strip(),
                        risk_level=risk_level
                    ))

        self.analysis_results["socket_patterns"] = [
            {
                "line_num": sp.line_num,
                "pattern": sp.pattern,
                "context": sp.context,
                "risk_level": sp.risk_level
            }
            for sp in socket_patterns
        ]

        print(f"🔍 Found {len(socket_patterns)} socket management patterns:")
        for sp in socket_patterns[:10]:  # Show first 10
            print(f"  Line {sp.line_num}: {sp.risk_level} - {sp.context[:80]}...")

        if len(socket_patterns) > 10:
            print(f"  ... and {len(socket_patterns) - 10} more")

    def analyze_threading_patterns(self, content: str):
        """Analyze threading and concurrency patterns"""
        print("\n🧵 ANALYZING THREADING PATTERNS")
        print("-" * 60)

        threading_patterns = []
        lines = content.split('\n')

        thread_creation_patterns = [
            (r'threading\.Thread\(.*target=([^,)]+)', "Thread creation"),
            (r'Thread\(.*target=([^,)]+)', "Thread creation"),
            (r'([a-zA-Z_][a-zA-Z0-9_]*_thread)\s*=', "Thread variable assignment"),
            (r'threading\.Lock\(\)', "Threading lock creation"),
            (r'\.start\(\)', "Thread start"),
            (r'\.join\(\)', "Thread join")
        ]

        for i, line in enumerate(lines, 1):
            for pattern, description in thread_creation_patterns:
                match = re.search(pattern, line)
                if match:
                    target_func = match.group(1) if match.groups() else "unknown"
                    threading_patterns.append(ThreadPattern(
                        line_num=i,
                        thread_name=target_func,
                        target_function=target_func,
                        purpose=description
                    ))

        self.analysis_results["threading_patterns"] = [
            {
                "line_num": tp.line_num,
                "thread_name": tp.thread_name,
                "target_function": tp.target_function,
                "purpose": tp.purpose
            }
            for tp in threading_patterns
        ]

        print(f"🔍 Found {len(threading_patterns)} threading patterns:")
        for tp in threading_patterns:
            print(f"  Line {tp.line_num}: {tp.purpose} - {tp.target_function}")

    def analyze_baseagent_integration(self, content: str):
        """Analyze current BaseAgent integration status"""
        print("\n🏗️ ANALYZING BASEAGENT INTEGRATION")
        print("-" * 60)

        baseagent_patterns = {
            "inheritance": bool(re.search(r'class\s+ModelManagerAgent\s*\([^)]*BaseAgent[^)]*\)', content)),
            "super_init": bool(re.search(r'super\(\).__init__\(', content)),
            "baseagent_import": bool(re.search(r'from.*BaseAgent', content)),
            "health_method": bool(re.search(r'def\s+_get_health_status\s*\(', content)),
            "custom_sockets": len(re.findall(r'zmq\.socket\(|socket\.socket\(', content)),
            "custom_threads": len(re.findall(r'threading\.Thread\(', content))
        }

        self.analysis_results["baseagent_usage"] = baseagent_patterns

        print(f"✅ BaseAgent Inheritance: {baseagent_patterns['inheritance']}")
        print(f"✅ Super Init Call: {baseagent_patterns['super_init']}")
        print(f"✅ BaseAgent Import: {baseagent_patterns['baseagent_import']}")
        print(f"✅ Health Method: {baseagent_patterns['health_method']}")
        print(f"⚠️  Custom Sockets: {baseagent_patterns['custom_sockets']}")
        print(f"⚠️  Custom Threads: {baseagent_patterns['custom_threads']}")

    def analyze_critical_functions(self, content: str):
        """Identify critical business logic functions"""
        print("\n🎯 ANALYZING CRITICAL FUNCTIONS")
        print("-" * 60)

        critical_functions = []

        # Find all function definitions
        function_patterns = [
            (r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', "Function definition"),
            (r'def\s+(load_[a-zA-Z0-9_]*)\s*\(', "Model loading function"),
            (r'def\s+(unload_[a-zA-Z0-9_]*)\s*\(', "Model unloading function"),
            (r'def\s+([a-zA-Z0-9_]*_vram[a-zA-Z0-9_]*)\s*\(', "VRAM management function"),
            (r'def\s+([a-zA-Z0-9_]*_memory[a-zA-Z0-9_]*)\s*\(', "Memory management function")
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, description in function_patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(1)
                    critical_functions.append({
                        "line_num": i,
                        "function_name": func_name,
                        "type": description,
                        "context": line.strip()
                    })

        # Filter to most critical functions (model management, VRAM, health)
        critical_keywords = ['load', 'unload', 'vram', 'memory', 'health', 'manage', 'init', 'start', 'stop']
        filtered_functions = [
            func for func in critical_functions
            if any(keyword in func['function_name'].lower() for keyword in critical_keywords)
        ]

        self.analysis_results["critical_functions"] = filtered_functions[:20]  # Top 20

        print(f"🔍 Found {len(critical_functions)} total functions")
        print(f"🎯 Identified {len(filtered_functions)} critical functions:")
        for func in filtered_functions[:10]:
            print(f"  Line {func['line_num']}: {func['function_name']} ({func['type']})")

    def assess_migration_risk(self):
        """Assess migration risk and complexity"""
        print("\n🚨 MIGRATION RISK ASSESSMENT")
        print("-" * 60)

        risk_factors = {
            "socket_complexity": len(self.analysis_results["socket_patterns"]),
            "threading_complexity": len(self.analysis_results["threading_patterns"]),
            "file_size_risk": "HIGH" if self.analysis_results["file_info"]["file_size_kb"] > 200 else "MEDIUM",
            "code_complexity": "HIGH" if self.analysis_results["file_info"]["code_lines"] > 3000 else "MEDIUM",
            "baseagent_integration": "PARTIAL" if self.analysis_results["baseagent_usage"]["inheritance"] else "NONE"
        }

        # Calculate overall risk score
        risk_score = 0
        risk_score += min(risk_factors["socket_complexity"] * 2, 20)  # Max 20 points
        risk_score += min(risk_factors["threading_complexity"] * 3, 15)  # Max 15 points
        risk_score += 10 if risk_factors["file_size_risk"] == "HIGH" else 5
        risk_score += 10 if risk_factors["code_complexity"] == "HIGH" else 5
        risk_score += 0 if risk_factors["baseagent_integration"] == "PARTIAL" else 10

        self.analysis_results["migration_risk_assessment"] = {
            "risk_factors": risk_factors,
            "overall_risk_score": risk_score,
            "risk_level": "CRITICAL" if risk_score > 40 else "HIGH" if risk_score > 25 else "MEDIUM"
        }

        print(f"📊 Overall Risk Score: {risk_score}/60")
        print(f"🚨 Risk Level: {self.analysis_results['migration_risk_assessment']['risk_level']}")
        print(f"🔌 Socket Patterns: {risk_factors['socket_complexity']}")
        print(f"🧵 Threading Patterns: {risk_factors['threading_complexity']}")
        print(f"📏 File Size Risk: {risk_factors['file_size_risk']}")
        print(f"💻 Code Complexity: {risk_factors['code_complexity']}")
        print(f"🏗️ BaseAgent Integration: {risk_factors['baseagent_integration']}")

    def generate_migration_strategy(self):
        """Generate migration strategy based on analysis"""
        print("\n📋 MIGRATION STRATEGY RECOMMENDATIONS")
        print("-" * 60)

        strategy = {
            "approach": "STAGED_MIGRATION",
            "phases": [
                {
                    "phase": 1,
                    "name": "Infrastructure Preparation",
                    "tasks": [
                        "Create comprehensive backup",
                        "Set up parallel testing environment",
                        "Deploy enhanced monitoring for GPU/VRAM operations",
                        "Create automated rollback scripts"
                    ]
                },
                {
                    "phase": 2,
                    "name": "BaseAgent Integration",
                    "tasks": [
                        "Verify BaseAgent inheritance is working",
                        "Migrate custom socket management to BaseAgent patterns",
                        "Integrate health check with BaseAgent health system",
                        "Update configuration management to use BaseAgent patterns"
                    ]
                },
                {
                    "phase": 3,
                    "name": "Threading Migration",
                    "tasks": [
                        "Analyze custom threading patterns",
                        "Migrate memory management thread to BaseAgent lifecycle",
                        "Migrate health check thread to BaseAgent health system",
                        "Migrate request handling thread to BaseAgent request system"
                    ]
                },
                {
                    "phase": 4,
                    "name": "Business Logic Validation",
                    "tasks": [
                        "Validate model loading/unloading functionality",
                        "Verify VRAM optimization remains functional",
                        "Test cross-machine coordination with PC2 agents",
                        "Comprehensive integration testing"
                    ]
                }
            ],
            "rollback_triggers": [
                "Any GPU operation failure",
                "Model loading/unloading failure",
                "VRAM optimization degradation >20%",
                "Cross-machine communication failure",
                "Health check failure for >5 minutes"
            ],
            "monitoring_requirements": [
                "Real-time GPU memory tracking",
                "Model loading performance metrics",
                "Thread health monitoring",
                "Socket connection status",
                "Cross-machine coordination status"
            ]
        }

        self.analysis_results["migration_strategy"] = strategy

        print("📌 Recommended Approach: STAGED_MIGRATION")
        print(f"📅 Migration Phases: {len(strategy['phases'])}")
        for phase in strategy['phases']:
            print(f"  Phase {phase['phase']}: {phase['name']}")
            for task in phase['tasks'][:2]:  # Show first 2 tasks
                print(f"    • {task}")
            if len(phase['tasks']) > 2:
                print(f"    ... and {len(phase['tasks']) - 2} more tasks")

    def save_analysis_report(self):
        """Save comprehensive analysis report"""
        report_file = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN" / "PHASE_1_WEEK_4_DAY_1_MMA_ANALYSIS.json"

        with open(report_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)

        print(f"\n📋 Analysis report saved: {report_file}")
        return report_file

    def run_complete_analysis(self):
        """Run complete architecture analysis"""
        print("\n" + "="*80)
        print("🔍 MODELMANAGERAGENT DEEP ARCHITECTURE ANALYSIS")
        print("📅 Phase 1 Week 4 Day 1 - Task 4A")
        print("="*80)

        content, lines = self.analyze_file_structure()
        self.analyze_socket_management(content)
        self.analyze_threading_patterns(content)
        self.analyze_baseagent_integration(content)
        self.analyze_critical_functions(content)
        self.assess_migration_risk()
        self.generate_migration_strategy()

        report_file = self.save_analysis_report()

        print("\n" + "="*80)
        print("✅ MODELMANAGERAGENT ANALYSIS COMPLETE")
        print("🎯 Ready for Phase 1 Week 4 Day 1 Task 4B: Migration Procedure Design")
        print("="*80)

        return self.analysis_results

def main():
    analyzer = ModelManagerAgentAnalyzer()
    results = analyzer.run_complete_analysis()

    print(f"\n🚀 Next Steps:")
    print(f"  1. Review analysis report for migration planning")
    print(f"  2. Proceed to Task 4B: Create specialized migration procedure")
    print(f"  3. Set up enhanced monitoring (Task 4C)")

if __name__ == "__main__":
    main()
