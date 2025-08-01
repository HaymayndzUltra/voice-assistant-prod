#!/usr/bin/env python3
"""
Common Utilities Consolidation Plan
Provides a detailed plan to consolidate the scattered common utilities
into a unified, well-organized structure
"""
import json
import pathlib
from datetime import datetime

class CommonUtilitiesConsolidationPlan:
    def __init__(self):
        self.plan = {
            "current_structure": {},
            "proposed_structure": {},
            "migration_steps": [],
            "benefits": [],
            "risks": [],
            "timeline": {}
        }
    
    def load_analysis(self):
        """Load the common utilities analysis"""
        try:
            with open('common_utilities_analysis.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠️  common_utilities_analysis.json not found. Run common_utilities_analyzer.py first.")
            return {}
    
    def generate_consolidation_plan(self):
        """Generate comprehensive consolidation plan"""
        analysis = self.load_analysis()
        
        print("🔍 Generating Common Utilities Consolidation Plan...")
        
        # Current structure analysis
        self.plan["current_structure"] = {
            "directories": analysis.get("structure", {}),
            "file_count": analysis.get("file_count", {}),
            "categories": analysis.get("categories", {}),
            "duplicates": analysis.get("potential_duplicates", [])
        }
        
        # Proposed unified structure
        self.plan["proposed_structure"] = {
            "root": "common_lib/",
            "modules": {
                "core": {
                    "description": "Core utilities and base classes",
                    "files": ["base_health_mixin.py", "data_models.py", "lazy_loader.py"]
                },
                "config": {
                    "description": "Configuration management and environment handling",
                    "files": ["config_manager.py", "env_helpers.py", "env_loader.py", "env_standardizer.py", 
                             "unified_config_loader.py", "docker_paths.py", "path_env.py"]
                },
                "networking": {
                    "description": "Network utilities, ZMQ, ports, and service discovery",
                    "files": ["zmq_helper.py", "port_registry.py", "network_util.py", "hostname_resolver.py"]
                },
                "observability": {
                    "description": "Logging, monitoring, and observability tools",
                    "files": ["logger_util.py", "prometheus_exporter.py", "base_health_mixin.py", "health.py"]
                },
                "security": {
                    "description": "Security and secret management",
                    "files": ["secret_manager.py"]
                },
                "data": {
                    "description": "Data handling and JSON utilities",
                    "files": ["fast_json.py", "data_models.py"]
                },
                "async": {
                    "description": "Asynchronous utilities",
                    "files": ["async_io.py"]
                },
                "agents": {
                    "description": "Agent-specific utilities",
                    "files": ["agent_helpers.py", "agent_ready_signal.py"]
                },
                "error": {
                    "description": "Error handling and resilience",
                    "files": ["error_handling.py"]
                },
                "learning": {
                    "description": "Learning and ML utilities",
                    "files": ["learning_models.py"]
                },
                "path": {
                    "description": "Path management utilities",
                    "files": ["path_manager.py"]
                }
            }
        }
        
        # Migration steps
        self.plan["migration_steps"] = [
            {
                "step": 1,
                "action": "Create new common_lib/ directory structure",
                "description": "Set up the new unified directory structure with all modules",
                "commands": [
                    "mkdir -p common_lib/{core,config,networking,observability,security,data,async,agents,error,learning,path}",
                    "touch common_lib/__init__.py",
                    "touch common_lib/{core,config,networking,observability,security,data,async,agents,error,learning,path}/__init__.py"
                ]
            },
            {
                "step": 2,
                "action": "Move files to new structure",
                "description": "Move existing files to their new locations in common_lib/",
                "commands": [
                    "# Example: mv common/utils/fast_json.py common_lib/data/",
                    "# Example: mv common_utils/zmq_helper.py common_lib/networking/",
                    "# Example: mv common/config_manager.py common_lib/config/"
                ]
            },
            {
                "step": 3,
                "action": "Update import statements",
                "description": "Update all import statements across the codebase to use new paths",
                "commands": [
                    "# Find all Python files with old imports",
                    "find . -name '*.py' -exec grep -l 'from common' {} \\;",
                    "find . -name '*.py' -exec grep -l 'from common_utils' {} \\;",
                    "# Update imports to use common_lib"
                ]
            },
            {
                "step": 4,
                "action": "Resolve duplicate functionality",
                "description": "Merge duplicate files and consolidate similar functionality",
                "commands": [
                    "# Review and merge __init__.py files",
                    "# Consolidate similar configuration utilities",
                    "# Merge overlapping networking utilities"
                ]
            },
            {
                "step": 5,
                "action": "Update requirements and dependencies",
                "description": "Ensure all dependencies are properly managed",
                "commands": [
                    "# Update setup.py or pyproject.toml if needed",
                    "# Verify all imports work correctly",
                    "# Run tests to ensure functionality is preserved"
                ]
            },
            {
                "step": 6,
                "action": "Clean up old directories",
                "description": "Remove old common/ and common_utils/ directories after verification",
                "commands": [
                    "# Backup old directories first",
                    "cp -r common common_backup_$(date +%Y%m%d)",
                    "cp -r common_utils common_utils_backup_$(date +%Y%m%d)",
                    "# Remove after successful migration",
                    "# rm -rf common common_utils"
                ]
            }
        ]
        
        # Benefits
        self.plan["benefits"] = [
            "Reduced code duplication and maintenance overhead",
            "Improved code organization and discoverability",
            "Clearer separation of concerns by functionality",
            "Easier dependency management",
            "Better import structure and namespace organization",
            "Simplified CI/CD pipeline with unified utilities",
            "Reduced Docker image sizes by eliminating duplicates"
        ]
        
        # Risks
        self.plan["risks"] = [
            "Breaking changes to existing import statements",
            "Potential functionality loss during consolidation",
            "Temporary disruption during migration",
            "Need to update documentation and examples",
            "Risk of introducing bugs during refactoring"
        ]
        
        # Timeline
        self.plan["timeline"] = {
            "phase1": {
                "duration": "1-2 days",
                "tasks": ["Create new structure", "Move files", "Update imports"],
                "risk_level": "Medium"
            },
            "phase2": {
                "duration": "1 day",
                "tasks": ["Resolve duplicates", "Test functionality"],
                "risk_level": "Low"
            },
            "phase3": {
                "duration": "1 day",
                "tasks": ["Clean up", "Update documentation"],
                "risk_level": "Low"
            }
        }
    
    def generate_detailed_report(self):
        """Generate detailed consolidation report"""
        print("\n" + "="*100)
        print("COMMON UTILITIES CONSOLIDATION PLAN")
        print("="*100)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Current State
        print("\n📊 CURRENT STATE:")
        current = self.plan["current_structure"]
        if "file_count" in current:
            total_files = sum(current["file_count"].values())
            print(f"   Total utility files: {total_files}")
            for name, count in current["file_count"].items():
                print(f"   {name}: {count} files")
        
        # Proposed Structure
        print("\n🏗️  PROPOSED STRUCTURE:")
        proposed = self.plan["proposed_structure"]
        print(f"   Root: {proposed['root']}")
        for module, info in proposed["modules"].items():
            print(f"   {module}/: {info['description']}")
            print(f"      Files: {len(info['files'])} utilities")
        
        # Migration Steps
        print("\n📋 MIGRATION STEPS:")
        for step in self.plan["migration_steps"]:
            print(f"   Step {step['step']}: {step['action']}")
            print(f"      {step['description']}")
        
        # Benefits
        print("\n✅ BENEFITS:")
        for i, benefit in enumerate(self.plan["benefits"], 1):
            print(f"   {i}. {benefit}")
        
        # Risks
        print("\n⚠️  RISKS:")
        for i, risk in enumerate(self.plan["risks"], 1):
            print(f"   {i}. {risk}")
        
        # Timeline
        print("\n⏰ TIMELINE:")
        for phase, details in self.plan["timeline"].items():
            print(f"   {phase.upper()}: {details['duration']} ({details['risk_level']} risk)")
            for task in details['tasks']:
                print(f"      • {task}")
        
        # Implementation Commands
        print("\n🔧 IMPLEMENTATION COMMANDS:")
        print("   # Phase 1: Create new structure")
        print("   mkdir -p common_lib/{core,config,networking,observability,security,data,async,agents,error,learning,path}")
        print("   touch common_lib/__init__.py")
        print("   touch common_lib/{core,config,networking,observability,security,data,async,agents,error,learning,path}/__init__.py")
        print("   ")
        print("   # Phase 2: Move files (example)")
        print("   mv common/utils/fast_json.py common_lib/data/")
        print("   mv common_utils/zmq_helper.py common_lib/networking/")
        print("   mv common/config_manager.py common_lib/config/")
        print("   ")
        print("   # Phase 3: Update imports")
        print("   find . -name '*.py' -exec sed -i 's/from common/from common_lib/g' {} \\;")
        print("   find . -name '*.py' -exec sed -i 's/from common_utils/from common_lib/g' {} \\;")
        
        # Save detailed plan
        with open('common_utilities_consolidation_plan.json', 'w') as f:
            json.dump(self.plan, f, indent=2)
        
        print(f"\n💾 Detailed plan saved to: common_utilities_consolidation_plan.json")
        print("="*100)

def main():
    planner = CommonUtilitiesConsolidationPlan()
    planner.generate_consolidation_plan()
    planner.generate_detailed_report()

if __name__ == "__main__":
    main() 