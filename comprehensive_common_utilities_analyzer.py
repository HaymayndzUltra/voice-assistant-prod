#!/usr/bin/env python3
"""
Comprehensive Common Utilities Analyzer - Complete analysis of ALL common utilities
Includes all subdirectories and provides complete migration mapping
"""
import pathlib
import json
from collections import defaultdict

class ComprehensiveCommonUtilitiesAnalyzer:
    def __init__(self):
        self.common_dirs = {
            "common": "common/",
            "common_utils": "common_utils/",
            "common/utils": "common/utils/"
        }
        self.analysis = {
            "structure": {},
            "file_count": {},
            "categories": defaultdict(list),
            "potential_duplicates": [],
            "optimization_opportunities": [],
            "complete_file_mapping": {},
            "import_usage": {}
        }
    
    def scan_all_directories(self):
        """Scan all directories recursively"""
        print("🔍 Scanning ALL Common Utilities Directories...")
        
        for name, path in self.common_dirs.items():
            dir_path = pathlib.Path(path)
            if dir_path.exists():
                all_files = []
                all_subdirs = []
                
                # Recursively scan all subdirectories
                for item in dir_path.rglob("*.py"):
                    if item.is_file():
                        relative_path = item.relative_to(dir_path)
                        all_files.append(str(relative_path))
                
                for item in dir_path.iterdir():
                    if item.is_dir() and not item.name.startswith('__'):
                        all_subdirs.append(item.name)
                
                self.analysis["structure"][name] = {
                    "path": str(dir_path.absolute()),
                    "files": all_files,
                    "subdirectories": all_subdirs,
                    "total_files": len(all_files),
                    "total_subdirs": len(all_subdirs)
                }
                self.analysis["file_count"][name] = len(all_files)
                
                # Create complete file mapping
                for file_path in all_files:
                    full_path = f"{path}{file_path}"
                    self.analysis["complete_file_mapping"][full_path] = {
                        "directory": name,
                        "relative_path": file_path,
                        "module_path": file_path.replace('/', '.').replace('.py', '')
                    }
            else:
                self.analysis["structure"][name] = {
                    "path": str(dir_path.absolute()),
                    "status": "MISSING"
                }
    
    def categorize_all_utilities(self):
        """Categorize ALL utilities by function"""
        print("🔍 Categorizing ALL Utilities...")
        
        categories = {
            "Core": ["core", "base", "enhanced"],
            "Configuration": ["config", "env", "path", "docker", "unified_config"],
            "Networking": ["network", "zmq", "port", "hostname", "http"],
            "Logging": ["log", "logger"],
            "Health": ["health", "monitoring", "standardized"],
            "Security": ["secret", "security"],
            "Data": ["data", "json", "fast_json"],
            "Async": ["async", "io"],
            "Error Handling": ["error", "error_bus", "unified_error"],
            "Agent Helpers": ["agent"],
            "Performance": ["performance", "prometheus"],
            "Lifecycle": ["lifecycle", "ready"],
            "Validation": ["validation"],
            "Learning": ["learning"],
            "Service": ["service", "discovery", "mesh"],
            "Observability": ["observability"],
            "Resiliency": ["resiliency"],
            "Factories": ["factories"],
            "Resources": ["resources"],
            "Pools": ["pools", "redis", "sql"],
            "Backends": ["backends"],
            "Audit": ["audit"],
            "API": ["api"],
            "Monitoring": ["monitoring"],
            "Lazy Loading": ["lazy"]
        }
        
        for name, path in self.common_dirs.items():
            if name in self.analysis["structure"] and "files" in self.analysis["structure"][name]:
                files = self.analysis["structure"][name]["files"]
                
                for file_path in files:
                    file_lower = file_path.lower()
                    categorized = False
                    
                    for category, keywords in categories.items():
                        if any(keyword in file_lower for keyword in keywords):
                            self.analysis["categories"][category].append({
                                "file": file_path,
                                "directory": name,
                                "path": f"{path}{file_path}"
                            })
                            categorized = True
                            break
                    
                    if not categorized:
                        self.analysis["categories"]["Other"].append({
                            "file": file_path,
                            "directory": name,
                            "path": f"{path}{file_path}"
                        })
    
    def identify_all_duplicates(self):
        """Identify ALL potential duplicate functionality"""
        print("🔍 Identifying ALL Potential Duplicates...")
        
        all_files = defaultdict(list)
        
        for name, path in self.common_dirs.items():
            if name in self.analysis["structure"] and "files" in self.analysis["structure"][name]:
                for file_path in self.analysis["structure"][name]["files"]:
                    base_name = file_path.replace('.py', '').split('/')[-1].lower()
                    all_files[base_name].append({
                        "file": file_path,
                        "directory": name,
                        "path": f"{path}{file_path}"
                    })
        
        # Find potential duplicates
        for base_name, files in all_files.items():
            if len(files) > 1:
                self.analysis["potential_duplicates"].append({
                    "base_name": base_name,
                    "files": files
                })
    
    def generate_comprehensive_mapping(self):
        """Generate comprehensive mapping for migration"""
        print("🔍 Generating Comprehensive Migration Mapping...")
        
        # Proposed unified structure with ALL modules
        proposed_structure = {
            "root": "common_lib/",
            "modules": {
                "core": {
                    "description": "Core utilities and base classes",
                    "files": [
                        "core/base_agent.py",
                        "core/enhanced_base_agent.py", 
                        "core/unified_config_manager.py",
                        "core/advanced_health_monitoring.py",
                        "base_health_mixin.py",
                        "data_models.py",
                        "lazy_loader.py"
                    ]
                },
                "config": {
                    "description": "Configuration management and environment handling",
                    "files": [
                        "config_manager.py",
                        "env_helpers.py", 
                        "env_loader.py",
                        "env_standardizer.py",
                        "unified_config_loader.py",
                        "docker_paths.py",
                        "path_env.py"
                    ]
                },
                "networking": {
                    "description": "Network utilities, ZMQ, ports, and service discovery",
                    "files": [
                        "zmq_helper.py",
                        "port_registry.py",
                        "network_util.py",
                        "hostname_resolver.py",
                        "pools/zmq_pool.py",
                        "pools/async_zmq_pool.py",
                        "pools/http_pool.py"
                    ]
                },
                "observability": {
                    "description": "Logging, monitoring, and observability tools",
                    "files": [
                        "logger_util.py",
                        "prometheus_exporter.py",
                        "health.py",
                        "health/standardized_health.py",
                        "health/unified_health.py",
                        "monitoring/",
                        "observability/"
                    ]
                },
                "security": {
                    "description": "Security and secret management",
                    "files": [
                        "secret_manager.py",
                        "security/"
                    ]
                },
                "data": {
                    "description": "Data handling and JSON utilities",
                    "files": [
                        "fast_json.py",
                        "data_models.py"
                    ]
                },
                "async": {
                    "description": "Asynchronous utilities",
                    "files": [
                        "async_io.py"
                    ]
                },
                "agents": {
                    "description": "Agent-specific utilities",
                    "files": [
                        "agent_helpers.py",
                        "agent_ready_signal.py"
                    ]
                },
                "error": {
                    "description": "Error handling and resilience",
                    "files": [
                        "error_handling.py",
                        "error_bus/unified_error_handler.py",
                        "error_bus/nats_error_bus.py",
                        "error_bus/nats_client.py",
                        "error_bus/dashboard.py",
                        "resiliency/"
                    ]
                },
                "learning": {
                    "description": "Learning and ML utilities",
                    "files": [
                        "learning_models.py"
                    ]
                },
                "path": {
                    "description": "Path management utilities",
                    "files": [
                        "path_manager.py"
                    ]
                },
                "pools": {
                    "description": "Connection pools and resource management",
                    "files": [
                        "pools/redis_pool.py",
                        "pools/sql_pool.py",
                        "pools/__init__.py"
                    ]
                },
                "factories": {
                    "description": "Factory patterns and object creation",
                    "files": [
                        "factories/"
                    ]
                },
                "resources": {
                    "description": "Resource management utilities",
                    "files": [
                        "resources/"
                    ]
                },
                "backends": {
                    "description": "Backend service utilities",
                    "files": [
                        "backends/"
                    ]
                },
                "audit": {
                    "description": "Audit and compliance utilities",
                    "files": [
                        "audit/"
                    ]
                },
                "api": {
                    "description": "API utilities and helpers",
                    "files": [
                        "api/"
                    ]
                },
                "validation": {
                    "description": "Validation utilities",
                    "files": [
                        "validation/"
                    ]
                },
                "service": {
                    "description": "Service discovery and mesh utilities",
                    "files": [
                        "service_discovery/",
                        "service_mesh/"
                    ]
                },
                "performance": {
                    "description": "Performance monitoring utilities",
                    "files": [
                        "performance/"
                    ]
                },
                "lifecycle": {
                    "description": "Lifecycle management utilities",
                    "files": [
                        "lifecycle/"
                    ]
                }
            }
        }
        
        self.analysis["proposed_structure"] = proposed_structure
    
    def generate_comprehensive_report(self):
        """Generate comprehensive report"""
        print("\n" + "="*100)
        print("COMPREHENSIVE COMMON UTILITIES ANALYSIS REPORT")
        print("="*100)
        
        # Complete Directory Structure
        print("\n📁 COMPLETE DIRECTORY STRUCTURE:")
        for name, info in self.analysis["structure"].items():
            if "status" in info:
                print(f"   {name}: {info['status']}")
            else:
                print(f"   {name}: {info['total_files']} files, {info['total_subdirs']} subdirs")
                print(f"      Path: {info['path']}")
                if info['subdirectories']:
                    print(f"      Subdirs: {', '.join(info['subdirectories'])}")
        
        # File Count Summary
        print(f"\n📊 COMPLETE FILE COUNT SUMMARY:")
        total_files = sum(self.analysis["file_count"].values())
        print(f"   Total utility files: {total_files}")
        for name, count in self.analysis["file_count"].items():
            print(f"   {name}: {count} files")
        
        # Complete Categories
        print(f"\n📂 COMPLETE UTILITY CATEGORIES:")
        for category, files in sorted(self.analysis["categories"].items()):
            if files:
                print(f"   {category}: {len(files)} files")
                for file_info in files[:5]:  # Show first 5 files
                    print(f"      • {file_info['file']} ({file_info['directory']})")
                if len(files) > 5:
                    print(f"      ... and {len(files) - 5} more")
        
        # All Potential Duplicates
        if self.analysis["potential_duplicates"]:
            print(f"\n🔄 ALL POTENTIAL DUPLICATES:")
            for duplicate in self.analysis["potential_duplicates"]:
                print(f"   {duplicate['base_name']}:")
                for file_info in duplicate['files']:
                    print(f"      • {file_info['file']} ({file_info['directory']})")
        
        # Proposed Structure
        if "proposed_structure" in self.analysis:
            print(f"\n🏗️  COMPREHENSIVE PROPOSED STRUCTURE:")
            proposed = self.analysis["proposed_structure"]
            print(f"   Root: {proposed['root']}")
            for module, info in proposed["modules"].items():
                print(f"   {module}/: {info['description']}")
                print(f"      Files: {len(info['files'])} utilities")
        
        # Migration Impact
        print(f"\n📈 MIGRATION IMPACT:")
        print(f"   Files to migrate: {total_files}")
        print(f"   Directories to consolidate: {len(self.analysis['file_count'])}")
        print(f"   Categories to organize: {len(self.analysis['categories'])}")
        if self.analysis["potential_duplicates"]:
            print(f"   Duplicates to resolve: {len(self.analysis['potential_duplicates'])}")
        
        # Save comprehensive analysis
        with open('comprehensive_common_utilities_analysis.json', 'w') as f:
            json.dump(self.analysis, f, indent=2)
        
        print(f"\n💾 Comprehensive analysis saved to: comprehensive_common_utilities_analysis.json")
        print("="*100)
    
    def run_comprehensive_analysis(self):
        """Run complete comprehensive analysis"""
        self.scan_all_directories()
        self.categorize_all_utilities()
        self.identify_all_duplicates()
        self.generate_comprehensive_mapping()
        self.generate_comprehensive_report()

def main():
    analyzer = ComprehensiveCommonUtilitiesAnalyzer()
    analyzer.run_comprehensive_analysis()

if __name__ == "__main__":
    main() 