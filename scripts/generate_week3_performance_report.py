#!/usr/bin/env python3
"""
Generate Week 3 Performance Report - Phase 1 Week 3 Day 7
Aggregates all optimization, validation, and monitoring results into a comprehensive report
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

class Week3PerformanceReporter:
    """Aggregate and generate comprehensive Week 3 performance report"""
    
    def __init__(self):
        self.project_root = Path(PathManager.get_project_root())
        self.action_plan_dir = self.project_root / "implementation_roadmap" / "PHASE1_ACTION_PLAN"
        self.report = {
            "generated": datetime.now().isoformat(),
            "phase": "Phase 1 Week 3",
            "status": "COMPLETE",
            "optimization": {},
            "validation": {},
            "monitoring": {},
            "load_testing": {},
            "advanced_features": {},
            "success_criteria": {},
            "recommendations": []
        }
    
    def generate(self, comprehensive: bool = True):
        print("\n📈 GENERATING WEEK 3 PERFORMANCE REPORT")
        print("=" * 60)
        self._aggregate_optimization()
        self._aggregate_validation()
        self._aggregate_monitoring()
        self._aggregate_load_testing()
        self._aggregate_advanced_features()
        self._evaluate_success_criteria()
        self._save_report()
        print("\n🎉 WEEK 3 PERFORMANCE REPORT GENERATED!")
        return True
    
    def _aggregate_optimization(self):
        try:
            opt_report = self.action_plan_dir / "PHASE_1_WEEK_3_DAY_4_SYSTEM_WIDE_OPTIMIZATION_REPORT.json"
            if opt_report.exists():
                with open(opt_report, 'r') as f:
                    self.report["optimization"] = json.load(f)
        except Exception as e:
            self.report["optimization"] = {"error": str(e)}
    
    def _aggregate_validation(self):
        try:
            val_report = self.action_plan_dir / "PHASE_1_WEEK_3_DAY_4_SYSTEM_WIDE_VALIDATION_REPORT.json"
            if val_report.exists():
                with open(val_report, 'r') as f:
                    self.report["validation"] = json.load(f)
        except Exception as e:
            self.report["validation"] = {"error": str(e)}
    
    def _aggregate_monitoring(self):
        try:
            mon_report = self.action_plan_dir / "PHASE_1_WEEK_3_DAY_5_COMPLETION_REPORT.md"
            if mon_report.exists():
                with open(mon_report, 'r') as f:
                    self.report["monitoring"] = {"summary": f.read()}
        except Exception as e:
            self.report["monitoring"] = {"error": str(e)}
    
    def _aggregate_load_testing(self):
        try:
            load_report = self.action_plan_dir / "PHASE_1_WEEK_3_DAY_6_LOAD_TESTING_REPORT.json"
            if load_report.exists():
                with open(load_report, 'r') as f:
                    self.report["load_testing"] = json.load(f)
        except Exception as e:
            self.report["load_testing"] = {"error": str(e)}
    
    def _aggregate_advanced_features(self):
        try:
            adv_report = self.action_plan_dir / "PHASE_1_WEEK_3_DAY_5_COMPLETION_REPORT.md"
            if adv_report.exists():
                with open(adv_report, 'r') as f:
                    self.report["advanced_features"] = {"summary": f.read()}
        except Exception as e:
            self.report["advanced_features"] = {"error": str(e)}
    
    def _evaluate_success_criteria(self):
        # Evaluate based on all aggregated data
        opt = self.report.get("optimization", {})
        val = self.report.get("validation", {})
        load = self.report.get("load_testing", {})
        adv = self.report.get("advanced_features", {})
        
        self.report["success_criteria"] = {
            "optimization_success": opt.get("summary", {}).get("success_rate", 0) >= 75.0,
            "validation_passed": val.get("success", False),
            "load_testing_passed": load.get("success", False),
            "advanced_features_deployed": bool(adv.get("summary") or adv.get("summary", "")),
        }
        if not self.report["success_criteria"]["validation_passed"]:
            self.report["recommendations"].append("Re-run validation with ObservabilityHub online for full health check.")
        if not self.report["success_criteria"]["load_testing_passed"]:
            self.report["recommendations"].append("Review load testing results for any delayed issues.")
    
    def _save_report(self):
        try:
            report_file = self.action_plan_dir / "PHASE_1_WEEK_3_PERFORMANCE_REPORT.json"
            with open(report_file, 'w') as f:
                json.dump(self.report, f, indent=2)
            print(f"\n📋 Week 3 performance report saved: {report_file}")
        except Exception as e:
            print(f"❌ Error saving performance report: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate comprehensive Week 3 performance report")
    parser.add_argument("--comprehensive", action="store_true", help="Generate comprehensive report")
    args = parser.parse_args()
    reporter = Week3PerformanceReporter()
    reporter.generate(comprehensive=args.comprehensive)

if __name__ == "__main__":
    main() 