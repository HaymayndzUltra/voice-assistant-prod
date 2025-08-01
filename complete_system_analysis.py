#!/usr/bin/env python3
"""
Complete System Analysis - Comprehensive analysis of ALL system components
Includes utilities, memory system, GUI, scripts, tests, backups, and more
"""
import pathlib
import json
from collections import defaultdict
from datetime import datetime

class CompleteSystemAnalyzer:
    def __init__(self):
        self.analysis = {
            "system_components": {},
            "file_count": {},
            "categories": defaultdict(list),
            "migration_components": [],
            "critical_paths": [],
            "dependencies": {},
            "timeline": {}
        }
    
    def scan_all_system_components(self):
        """Scan ALL system components"""
        print("🔍 Scanning ALL System Components...")
        
        # Define all major system components
        system_components = {
            "main_pc_code": "main_pc_code/",
            "pc2_code": "pc2_code/",
            "common": "common/",
            "common_utils": "common_utils/",
            "memory_system": "memory_system/",
            "remote_api_adapter": "remote_api_adapter/",
            "gui": "gui/",
            "scripts": "scripts/",
            "tests": "tests/",
            "docker": "docker/",
            "k8s": "k8s/",
            "docs": "docs/",
            "backups": "backups/",
            "implementation_roadmap": "implementation_roadmap/",
            "analysis_output": "analysis_output/",
            "config": "config/",
            "logs": "logs/",
            "data": "data/",
            "models": "models/"
        }
        
        for name, path in system_components.items():
            dir_path = pathlib.Path(path)
            if dir_path.exists():
                all_files = []
                all_subdirs = []
                
                # Recursively scan all files
                for item in dir_path.rglob("*"):
                    if item.is_file():
                        relative_path = item.relative_to(dir_path)
                        all_files.append(str(relative_path))
                    elif item.is_dir() and not item.name.startswith('__'):
                        all_subdirs.append(item.name)
                
                self.analysis["system_components"][name] = {
                    "path": str(dir_path.absolute()),
                    "files": all_files,
                    "subdirectories": all_subdirs,
                    "total_files": len(all_files),
                    "total_subdirs": len(all_subdirs),
                    "file_types": self._analyze_file_types(all_files)
                }
                self.analysis["file_count"][name] = len(all_files)
            else:
                self.analysis["system_components"][name] = {
                    "path": str(dir_path.absolute()),
                    "status": "MISSING"
                }
    
    def _analyze_file_types(self, files):
        """Analyze file types in a directory"""
        file_types = defaultdict(int)
        for file_path in files:
            if '.' in file_path:
                ext = file_path.split('.')[-1].lower()
                file_types[ext] += 1
            else:
                file_types['no_extension'] += 1
        return dict(file_types)
    
    def categorize_all_components(self):
        """Categorize ALL system components"""
        print("🔍 Categorizing ALL System Components...")
        
        categories = {
            "Core System": ["main_pc_code", "pc2_code"],
            "Utilities": ["common", "common_utils"],
            "Memory & Intelligence": ["memory_system"],
            "User Interface": ["gui"],
            "Infrastructure": ["docker", "k8s", "config"],
            "Automation": ["scripts"],
            "Testing": ["tests"],
            "Documentation": ["docs"],
            "Data & Storage": ["data", "logs", "models"],
            "Backup & Recovery": ["backups"],
            "Planning": ["implementation_roadmap"],
            "Analysis": ["analysis_output"],
            "API Integration": ["remote_api_adapter"]
        }
        
        for category, components in categories.items():
            for component in components:
                if component in self.analysis["system_components"]:
                    info = self.analysis["system_components"][component]
                    if "status" not in info:
                        self.analysis["categories"][category].append({
                            "name": component,
                            "path": info["path"],
                            "files": info["total_files"],
                            "subdirs": info["total_subdirs"]
                        })
    
    def identify_migration_components(self):
        """Identify components that need migration"""
        print("🔍 Identifying Migration Components...")
        
        migration_components = [
            {
                "component": "main_pc_code",
                "priority": "HIGH",
                "description": "Main PC agent system",
                "migration_type": "agent_consolidation"
            },
            {
                "component": "pc2_code", 
                "priority": "HIGH",
                "description": "PC2 agent system",
                "migration_type": "agent_consolidation"
            },
            {
                "component": "common",
                "priority": "HIGH",
                "description": "Common utilities (83 files)",
                "migration_type": "utility_consolidation"
            },
            {
                "component": "common_utils",
                "priority": "HIGH", 
                "description": "Common utilities (6 files)",
                "migration_type": "utility_consolidation"
            },
            {
                "component": "docker",
                "priority": "MEDIUM",
                "description": "Docker configurations",
                "migration_type": "container_optimization"
            },
            {
                "component": "scripts",
                "priority": "MEDIUM",
                "description": "Automation scripts (100+ files)",
                "migration_type": "script_organization"
            },
            {
                "component": "tests",
                "priority": "MEDIUM",
                "description": "Test framework",
                "migration_type": "test_consolidation"
            },
            {
                "component": "gui",
                "priority": "LOW",
                "description": "User interface",
                "migration_type": "ui_enhancement"
            },
            {
                "component": "memory_system",
                "priority": "LOW",
                "description": "Memory and intelligence system",
                "migration_type": "feature_enhancement"
            }
        ]
        
        self.analysis["migration_components"] = migration_components
    
    def identify_critical_paths(self):
        """Identify critical system paths"""
        print("🔍 Identifying Critical System Paths...")
        
        critical_paths = [
            {
                "path": "main_pc_code/config/startup_config.yaml",
                "type": "configuration",
                "criticality": "HIGH",
                "description": "Main PC startup configuration"
            },
            {
                "path": "pc2_code/config/startup_config.yaml", 
                "type": "configuration",
                "criticality": "HIGH",
                "description": "PC2 startup configuration"
            },
            {
                "path": "docker-compose.yml",
                "type": "infrastructure",
                "criticality": "HIGH", 
                "description": "Main Docker Compose configuration"
            },
            {
                "path": "Dockerfile",
                "type": "infrastructure",
                "criticality": "HIGH",
                "description": "Main Dockerfile"
            },
            {
                "path": "requirements.txt",
                "type": "dependencies",
                "criticality": "HIGH",
                "description": "Python dependencies"
            },
            {
                "path": "data/unified_memory.db",
                "type": "data",
                "criticality": "HIGH",
                "description": "Unified memory database"
            },
            {
                "path": "models/",
                "type": "models",
                "criticality": "MEDIUM",
                "description": "AI model files"
            },
            {
                "path": "logs/",
                "type": "logs",
                "criticality": "MEDIUM",
                "description": "System logs"
            }
        ]
        
        self.analysis["critical_paths"] = critical_paths
    
    def analyze_dependencies(self):
        """Analyze system dependencies"""
        print("🔍 Analyzing System Dependencies...")
        
        dependencies = {
            "python_packages": {
                "main_pc_code/requirements.txt": "Main PC dependencies",
                "pc2_code/requirements.txt": "PC2 dependencies", 
                "requirements.txt": "Root dependencies",
                "requirements-web.txt": "Web dependencies",
                "gui/requirements.txt": "GUI dependencies"
            },
            "docker_files": {
                "Dockerfile": "Main Dockerfile",
                "docker/mainpc/Dockerfile": "MainPC Dockerfile",
                "docker/pc2/Dockerfile": "PC2 Dockerfile",
                "remote_api_adapter/Dockerfile": "API adapter Dockerfile"
            },
            "compose_files": {
                "docker-compose.yml": "Main compose",
                "docker-compose.observability.yml": "Observability compose",
                "docker-compose.secrets.yml": "Secrets compose",
                "docker-compose.test.yml": "Test compose",
                "docker-compose.foundation-test.yml": "Foundation test compose"
            },
            "configuration_files": {
                "main_pc_code/config/": "Main PC configs",
                "pc2_code/config/": "PC2 configs",
                "config/": "Root configs"
            }
        }
        
        self.analysis["dependencies"] = dependencies
    
    def generate_migration_timeline(self):
        """Generate comprehensive migration timeline"""
        print("🔍 Generating Migration Timeline...")
        
        timeline = {
            "phase0": {
                "duration": "1-2 days",
                "components": ["analysis", "planning"],
                "tasks": [
                    "Complete system analysis",
                    "Dependency mapping", 
                    "Migration planning",
                    "Risk assessment"
                ],
                "risk_level": "LOW"
            },
            "phase1": {
                "duration": "3-4 days", 
                "components": ["common", "common_utils"],
                "tasks": [
                    "Consolidate common utilities",
                    "Resolve duplicates",
                    "Update import statements",
                    "Test functionality"
                ],
                "risk_level": "MEDIUM"
            },
            "phase2": {
                "duration": "2-3 days",
                "components": ["main_pc_code", "pc2_code"],
                "tasks": [
                    "Agent path validation",
                    "Configuration consolidation",
                    "Docker optimization",
                    "Health check implementation"
                ],
                "risk_level": "MEDIUM"
            },
            "phase3": {
                "duration": "2-3 days",
                "components": ["docker", "scripts", "tests"],
                "tasks": [
                    "Docker image optimization",
                    "Script organization",
                    "Test consolidation",
                    "CI/CD enhancement"
                ],
                "risk_level": "LOW"
            },
            "phase4": {
                "duration": "1-2 days",
                "components": ["documentation", "cleanup"],
                "tasks": [
                    "Update documentation",
                    "Clean up backups",
                    "Final testing",
                    "Deployment validation"
                ],
                "risk_level": "LOW"
            }
        }
        
        self.analysis["timeline"] = timeline
    
    def generate_complete_report(self):
        """Generate complete system report"""
        print("\n" + "="*120)
        print("COMPLETE SYSTEM ANALYSIS REPORT")
        print("="*120)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # System Overview
        print("\n📊 SYSTEM OVERVIEW:")
        total_files = sum(self.analysis["file_count"].values())
        total_components = len(self.analysis["system_components"])
        print(f"   Total Components: {total_components}")
        print(f"   Total Files: {total_files}")
        print(f"   Migration Components: {len(self.analysis['migration_components'])}")
        
        # Component Breakdown
        print("\n📁 COMPONENT BREAKDOWN:")
        for name, info in self.analysis["system_components"].items():
            if "status" not in info:
                print(f"   {name}: {info['total_files']} files, {info['total_subdirs']} subdirs")
                if info['file_types']:
                    top_types = sorted(info['file_types'].items(), key=lambda x: x[1], reverse=True)[:3]
                    print(f"      Top file types: {', '.join([f'{ext}({count})' for ext, count in top_types])}")
            else:
                print(f"   {name}: {info['status']}")
        
        # Categories
        print("\n📂 SYSTEM CATEGORIES:")
        for category, components in sorted(self.analysis["categories"].items()):
            if components:
                total_files = sum(comp["files"] for comp in components)
                print(f"   {category}: {len(components)} components, {total_files} files")
                for comp in components:
                    print(f"      • {comp['name']}: {comp['files']} files")
        
        # Migration Components
        print("\n🔄 MIGRATION COMPONENTS:")
        for comp in self.analysis["migration_components"]:
            print(f"   {comp['component']} ({comp['priority']}): {comp['description']}")
            print(f"      Type: {comp['migration_type']}")
        
        # Critical Paths
        print("\n⚠️  CRITICAL PATHS:")
        for path_info in self.analysis["critical_paths"]:
            print(f"   {path_info['path']} ({path_info['criticality']}): {path_info['description']}")
        
        # Dependencies
        print("\n📦 DEPENDENCIES:")
        for dep_type, deps in self.analysis["dependencies"].items():
            print(f"   {dep_type}: {len(deps)} files")
            for path, desc in list(deps.items())[:3]:
                print(f"      • {path}: {desc}")
            if len(deps) > 3:
                print(f"      ... and {len(deps) - 3} more")
        
        # Timeline
        print("\n⏰ MIGRATION TIMELINE:")
        total_duration = 0
        for phase, details in self.analysis["timeline"].items():
            # Parse duration like "1-2 days" to get average
            duration_str = details["duration"].split()[0]
            if '-' in duration_str:
                min_days, max_days = map(int, duration_str.split('-'))
                avg_duration = (min_days + max_days) / 2
            else:
                avg_duration = int(duration_str)
            total_duration += avg_duration
            print(f"   {phase.upper()}: {details['duration']} ({details['risk_level']} risk)")
            print(f"      Components: {', '.join(details['components'])}")
        
        print(f"\n📈 TOTAL ESTIMATED DURATION: {total_duration:.1f} days")
        
        # Migration Impact
        print(f"\n📈 MIGRATION IMPACT:")
        print(f"   Files to migrate: {total_files}")
        print(f"   Components to consolidate: {len(self.analysis['migration_components'])}")
        print(f"   Critical paths to preserve: {len(self.analysis['critical_paths'])}")
        print(f"   Dependencies to manage: {sum(len(deps) for deps in self.analysis['dependencies'].values())}")
        
        # Save complete analysis
        with open('complete_system_analysis.json', 'w') as f:
            json.dump(self.analysis, f, indent=2)
        
        print(f"\n💾 Complete analysis saved to: complete_system_analysis.json")
        print("="*120)
    
    def run_complete_analysis(self):
        """Run complete system analysis"""
        self.scan_all_system_components()
        self.categorize_all_components()
        self.identify_migration_components()
        self.identify_critical_paths()
        self.analyze_dependencies()
        self.generate_migration_timeline()
        self.generate_complete_report()

def main():
    analyzer = CompleteSystemAnalyzer()
    analyzer.run_complete_analysis()

if __name__ == "__main__":
    main() 