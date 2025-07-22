#!/usr/bin/env python3
"""
Circular Import Detection Script
===============================

This script systematically tests for circular import patterns in the AI Agent System.
It validates the dependency chains identified in Phase 1 Week 1 analysis.

Test Categories:
1. Foundation Layer Imports (PathManager, RequestCoordinator, ErrorPublisher)
2. Cross-Agent Import Chains (Agent A → Agent B → Shared Utility → Agent A)
3. PC2/MainPC Cross-Machine Dependencies
4. Service Discovery Circular Patterns

Each test runs in an isolated subprocess to avoid import contamination.
"""

import sys
import os
import subprocess
import importlib
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class CircularImportDetector:
    """Detects circular import patterns through systematic testing."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = {
            "foundation_tests": {},
            "cross_agent_tests": {},
            "cross_machine_tests": {},
            "service_discovery_tests": {},
            "circular_patterns": [],
            "safe_imports": [],
            "failed_imports": []
        }
        
    def test_import_in_subprocess(self, module_path: str) -> Tuple[bool, str, float]:
        """Test import in isolated subprocess to avoid contamination."""
        start_time = time.time()
        
        test_script = f'''
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path("{self.project_root}")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import {module_path}
    print("SUCCESS: Import completed")
except ImportError as e:
    print(f"IMPORT_ERROR: {{e}}")
    sys.exit(1)
except Exception as e:
    print(f"RUNTIME_ERROR: {{e}}")
    sys.exit(2)
'''
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return True, "SUCCESS", duration
            elif result.returncode == 1:
                return False, f"IMPORT_ERROR: {result.stdout.strip()}", duration
            elif result.returncode == 2:
                return False, f"RUNTIME_ERROR: {result.stdout.strip()}", duration
            else:
                return False, f"UNKNOWN_ERROR: {result.stderr.strip()}", duration
                
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT: Import took >30 seconds (likely circular)", 30.0
        except Exception as e:
            return False, f"SUBPROCESS_ERROR: {e}", time.time() - start_time
    
    def test_foundation_layer(self) -> Dict[str, Dict]:
        """Test foundation layer imports (PathManager, RequestCoordinator, etc.)."""
        print("🔍 Testing Foundation Layer Imports...")
        
        foundation_modules = [
            # Path utilities (should be safe)
            "common.utils.path_env",
            "common.utils.path_manager", 
            
            # Core agents that others depend on
            "main_pc_code.agents.request_coordinator",
            "main_pc_code.agents.memory_client",
            
            # Shared utilities
            "main_pc_code.utils.service_discovery_client",
            "main_pc_code.utils.network_utils",
        ]
        
        foundation_results = {}
        
        for module in foundation_modules:
            print(f"  Testing: {module}")
            success, message, duration = self.test_import_in_subprocess(module)
            
            foundation_results[module] = {
                "success": success,
                "message": message,
                "duration": duration,
                "category": "foundation"
            }
            
            if success:
                self.results["safe_imports"].append(module)
                print(f"    ✅ SUCCESS ({duration:.2f}s)")
            else:
                self.results["failed_imports"].append(module)
                print(f"    ❌ FAILED: {message}")
        
        return foundation_results
    
    def test_cross_agent_imports(self) -> Dict[str, Dict]:
        """Test known problematic cross-agent import chains."""
        print("\n🔗 Testing Cross-Agent Import Chains...")
        
        # Test agents that import from other agents
        cross_agent_modules = [
            # High-risk agents from dependency analysis
            "main_pc_code.agents.model_orchestrator",  # Imports CircuitBreaker
            "main_pc_code.agents.translation_service",  # Imports CircuitBreaker
            "main_pc_code.agents.learning_orchestration_service",  # Imports CircuitBreaker
            "main_pc_code.agents.goal_manager",  # Imports MemoryClient
            "main_pc_code.agents.session_memory_agent",  # Imports MemoryClient
            
            # Agents with ErrorPublisher dependencies
            "main_pc_code.agents.face_recognition_agent",  # Imports ErrorPublisher
            "main_pc_code.agents.nlu_agent",  # Imports ErrorPublisher
            "main_pc_code.agents.tiered_responder",  # Imports ErrorPublisher
        ]
        
        cross_agent_results = {}
        
        for module in cross_agent_modules:
            print(f"  Testing: {module}")
            success, message, duration = self.test_import_in_subprocess(module)
            
            cross_agent_results[module] = {
                "success": success,
                "message": message,
                "duration": duration,
                "category": "cross_agent"
            }
            
            if success:
                self.results["safe_imports"].append(module)
                print(f"    ✅ SUCCESS ({duration:.2f}s)")
            else:
                self.results["failed_imports"].append(module)
                print(f"    ❌ FAILED: {message}")
                
        return cross_agent_results
    
    def test_cross_machine_imports(self) -> Dict[str, Dict]:
        """Test PC2 agents importing MainPC utilities."""
        print("\n🌐 Testing Cross-Machine Import Patterns...")
        
        # PC2 agents that import MainPC utilities
        cross_machine_modules = [
            "pc2_code.agents.remote_connector_agent",  # Uses MainPC service discovery
            "pc2_code.agents.unified_web_agent",  # Uses MainPC network utils
            "pc2_code.agents.memory_orchestrator_service",  # Complex cross-dependencies
            "pc2_code.agents.unified_memory_reasoning_agent",  # Uses common utilities
            "pc2_code.agents.filesystem_assistant_agent",  # Uses common utilities
        ]
        
        cross_machine_results = {}
        
        for module in cross_machine_modules:
            print(f"  Testing: {module}")
            success, message, duration = self.test_import_in_subprocess(module)
            
            cross_machine_results[module] = {
                "success": success,
                "message": message,
                "duration": duration,
                "category": "cross_machine"
            }
            
            if success:
                self.results["safe_imports"].append(module)
                print(f"    ✅ SUCCESS ({duration:.2f}s)")
            else:
                self.results["failed_imports"].append(module)
                print(f"    ❌ FAILED: {message}")
                
        return cross_machine_results
    
    def test_problematic_agents(self) -> Dict[str, Dict]:
        """Test agents with known import order issues."""
        print("\n⚠️  Testing Agents with Known Import Issues...")
        
        # Agents from Task 1A analysis with import order problems
        problematic_modules = [
            "main_pc_code.agents.remote_connector_agent",  # get_main_pc_code() before import
            "main_pc_code.agents.streaming_interrupt",  # Usage before import
            "main_pc_code.agents.streaming_language_to_llm",  # Usage before import
            "main_pc_code.agents.human_awareness_agent",  # Mixed path systems
            "main_pc_code.agents.advanced_command_handler",  # Mixed path systems
        ]
        
        problematic_results = {}
        
        for module in problematic_modules:
            print(f"  Testing: {module}")
            success, message, duration = self.test_import_in_subprocess(module)
            
            problematic_results[module] = {
                "success": success,
                "message": message,
                "duration": duration,
                "category": "problematic",
                "expected_issue": "Import order or path management issues"
            }
            
            if success:
                print(f"    ⚠️  UNEXPECTED SUCCESS ({duration:.2f}s) - Issue may be intermittent")
            else:
                print(f"    ❌ CONFIRMED ISSUE: {message}")
                
        return problematic_results
    
    def detect_circular_patterns(self) -> List[Dict]:
        """Analyze results to identify circular dependency patterns."""
        print("\n🔄 Analyzing for Circular Dependency Patterns...")
        
        circular_patterns = []
        
        # Look for timeout failures (likely circular imports)
        for module in self.results["failed_imports"]:
            module_results = None
            
            # Find the module results across all test categories
            for category in ["foundation_tests", "cross_agent_tests", "cross_machine_tests"]:
                if module in self.results.get(category, {}):
                    module_results = self.results[category][module]
                    break
            
            if module_results and "TIMEOUT" in module_results.get("message", ""):
                circular_patterns.append({
                    "module": module,
                    "pattern": "Import timeout - likely circular dependency",
                    "duration": module_results["duration"],
                    "category": module_results["category"]
                })
        
        # Look for specific circular import error messages
        circular_keywords = ["circular import", "partially initialized", "ImportError", "AttributeError"]
        
        for category_name, category_results in [
            ("foundation", self.results.get("foundation_tests", {})),
            ("cross_agent", self.results.get("cross_agent_tests", {})),
            ("cross_machine", self.results.get("cross_machine_tests", {}))
        ]:
            for module, result in category_results.items():
                message = result.get("message", "").lower()
                
                for keyword in circular_keywords:
                    if keyword in message:
                        circular_patterns.append({
                            "module": module,
                            "pattern": f"Error pattern: {keyword}",
                            "message": result.get("message", ""),
                            "category": category_name
                        })
                        break
        
        return circular_patterns
    
    def generate_report(self) -> str:
        """Generate comprehensive circular import analysis report."""
        report = []
        report.append("# CIRCULAR IMPORT DETECTION REPORT")
        report.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Project Root:** {self.project_root}")
        report.append("")
        
        # Summary statistics
        total_tested = len(self.results["safe_imports"]) + len(self.results["failed_imports"])
        success_rate = len(self.results["safe_imports"]) / total_tested * 100 if total_tested > 0 else 0
        
        report.append("## 📊 SUMMARY STATISTICS")
        report.append(f"- **Total Modules Tested:** {total_tested}")
        report.append(f"- **Successful Imports:** {len(self.results['safe_imports'])} ({success_rate:.1f}%)")
        report.append(f"- **Failed Imports:** {len(self.results['failed_imports'])}")
        report.append(f"- **Circular Patterns Detected:** {len(self.results['circular_patterns'])}")
        report.append("")
        
        # Circular patterns analysis
        if self.results["circular_patterns"]:
            report.append("## 🔄 CIRCULAR DEPENDENCY PATTERNS")
            for i, pattern in enumerate(self.results["circular_patterns"], 1):
                report.append(f"{i}. **{pattern['module']}**")
                report.append(f"   - Pattern: {pattern['pattern']}")
                report.append(f"   - Category: {pattern['category']}")
                if 'message' in pattern:
                    report.append(f"   - Details: {pattern['message']}")
                report.append("")
        
        # Failed imports analysis
        if self.results["failed_imports"]:
            report.append("## ❌ FAILED IMPORTS ANALYSIS")
            for module in self.results["failed_imports"]:
                report.append(f"- `{module}`")
            report.append("")
        
        # Successful imports (validation)
        if self.results["safe_imports"]:
            report.append("## ✅ SUCCESSFUL IMPORTS (Safe Dependencies)")
            for module in self.results["safe_imports"][:10]:  # Show first 10
                report.append(f"- `{module}`")
            if len(self.results["safe_imports"]) > 10:
                report.append(f"- ... and {len(self.results['safe_imports']) - 10} more")
            report.append("")
        
        # Recommendations
        report.append("## 📋 RECOMMENDATIONS")
        report.append("1. **Fix import order issues** in modules with NameError/ImportError")
        report.append("2. **Resolve circular dependencies** in modules with timeout/circular patterns")
        report.append("3. **Standardize path management** in modules with mixed path systems")
        report.append("4. **Test imports systematically** after each fix to prevent regressions")
        report.append("")
        
        return "\n".join(report)
    
    def run_full_analysis(self) -> Dict:
        """Run complete circular import analysis."""
        print("🚀 Starting Circular Import Detection Analysis")
        print("=" * 60)
        
        # Test different categories
        self.results["foundation_tests"] = self.test_foundation_layer()
        self.results["cross_agent_tests"] = self.test_cross_agent_imports()
        self.results["cross_machine_tests"] = self.test_cross_machine_imports()
        self.results["problematic_tests"] = self.test_problematic_agents()
        
        # Analyze patterns
        self.results["circular_patterns"] = self.detect_circular_patterns()
        
        # Generate report
        report_content = self.generate_report()
        
        # Save results
        results_file = self.project_root / "phase1_week1_circular_import_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        report_file = self.project_root / "phase1_week1_circular_import_report.md"
        with open(report_file, "w") as f:
            f.write(report_content)
        
        print("\n" + "=" * 60)
        print("🎯 Analysis Complete!")
        print(f"📄 Report saved to: {report_file}")
        print(f"📊 Raw results saved to: {results_file}")
        
        return self.results

if __name__ == "__main__":
    detector = CircularImportDetector()
    results = detector.run_full_analysis()
    
    # Print key findings
    print("\n🔍 KEY FINDINGS:")
    print(f"- Total modules tested: {len(results['safe_imports']) + len(results['failed_imports'])}")
    print(f"- Failed imports: {len(results['failed_imports'])}")
    print(f"- Circular patterns: {len(results['circular_patterns'])}")
    
    if results['failed_imports']:
        print("\n❌ Critical Issues Found:")
        for module in results['failed_imports'][:5]:
            print(f"  - {module}")
    
    if results['circular_patterns']:
        print("\n🔄 Circular Dependencies Detected:")
        for pattern in results['circular_patterns'][:3]:
            print(f"  - {pattern['module']}: {pattern['pattern']}") 