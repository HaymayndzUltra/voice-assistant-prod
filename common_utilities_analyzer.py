#!/usr/bin/env python3
"""
Common Utilities Analyzer - Identifies shared utilities and optimization opportunities
Helps consolidate duplicate code and improve the common library structure
"""
import pathlib
import json
from collections import defaultdict

class CommonUtilitiesAnalyzer:
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
            "optimization_opportunities": []
        }
    
    def analyze_directory_structure(self):
        """Analyze the structure of common utility directories"""
        print("🔍 Analyzing Common Utilities Structure...")
        
        for name, path in self.common_dirs.items():
            dir_path = pathlib.Path(path)
            if dir_path.exists():
                files = []
                subdirs = []
                
                for item in dir_path.iterdir():
                    if item.is_file() and item.suffix == '.py':
                        files.append(item.name)
                    elif item.is_dir() and not item.name.startswith('__'):
                        subdirs.append(item.name)
                
                self.analysis["structure"][name] = {
                    "path": str(dir_path.absolute()),
                    "files": files,
                    "subdirectories": subdirs,
                    "total_files": len(files),
                    "total_subdirs": len(subdirs)
                }
                self.analysis["file_count"][name] = len(files)
            else:
                self.analysis["structure"][name] = {
                    "path": str(dir_path.absolute()),
                    "status": "MISSING"
                }
    
    def categorize_utilities(self):
        """Categorize utilities by function"""
        print("🔍 Categorizing Utilities...")
        
        categories = {
            "Configuration": ["config", "env", "path", "docker"],
            "Networking": ["network", "zmq", "port", "hostname"],
            "Logging": ["log", "logger"],
            "Health": ["health", "monitoring"],
            "Security": ["secret", "security"],
            "Data": ["data", "json", "fast_json"],
            "Async": ["async", "io"],
            "Error Handling": ["error"],
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
            "Pools": ["pools"],
            "Backends": ["backends"],
            "Audit": ["audit"],
            "API": ["api"]
        }
        
        for name, path in self.common_dirs.items():
            if name in self.analysis["structure"] and "files" in self.analysis["structure"][name]:
                files = self.analysis["structure"][name]["files"]
                
                for file_name in files:
                    file_lower = file_name.lower()
                    categorized = False
                    
                    for category, keywords in categories.items():
                        if any(keyword in file_lower for keyword in keywords):
                            self.analysis["categories"][category].append({
                                "file": file_name,
                                "directory": name,
                                "path": f"{path}{file_name}"
                            })
                            categorized = True
                            break
                    
                    if not categorized:
                        self.analysis["categories"]["Other"].append({
                            "file": file_name,
                            "directory": name,
                            "path": f"{path}{file_name}"
                        })
    
    def identify_potential_duplicates(self):
        """Identify potential duplicate functionality"""
        print("🔍 Identifying Potential Duplicates...")
        
        # Look for similar file names across directories
        all_files = defaultdict(list)
        
        for name, path in self.common_dirs.items():
            if name in self.analysis["structure"] and "files" in self.analysis["structure"][name]:
                for file_name in self.analysis["structure"][name]["files"]:
                    base_name = file_name.replace('.py', '').lower()
                    all_files[base_name].append({
                        "file": file_name,
                        "directory": name,
                        "path": f"{path}{file_name}"
                    })
        
        # Find potential duplicates
        for base_name, files in all_files.items():
            if len(files) > 1:
                self.analysis["potential_duplicates"].append({
                    "base_name": base_name,
                    "files": files
                })
    
    def generate_optimization_recommendations(self):
        """Generate optimization recommendations"""
        print("🔍 Generating Optimization Recommendations...")
        
        recommendations = []
        
        # Consolidation opportunities
        if len(self.analysis["file_count"]) > 1:
            recommendations.append({
                "type": "consolidation",
                "description": "Multiple common utility directories detected",
                "action": "Consider consolidating into single common_lib/ structure",
                "impact": "Reduce code duplication and improve maintainability"
            })
        
        # Duplicate detection
        if self.analysis["potential_duplicates"]:
            recommendations.append({
                "type": "duplicates",
                "description": f"Found {len(self.analysis['potential_duplicates'])} potential duplicate utilities",
                "action": "Review and merge duplicate functionality",
                "impact": "Eliminate redundant code and reduce maintenance overhead"
            })
        
        # Category organization
        large_categories = {cat: len(files) for cat, files in self.analysis["categories"].items() if len(files) > 5}
        if large_categories:
            recommendations.append({
                "type": "organization",
                "description": f"Large categories detected: {list(large_categories.keys())}",
                "action": "Consider subdividing large categories into more specific modules",
                "impact": "Improve code organization and discoverability"
            })
        
        self.analysis["optimization_opportunities"] = recommendations
    
    def generate_report(self):
        """Generate comprehensive report"""
        print("\n" + "="*80)
        print("COMMON UTILITIES ANALYSIS REPORT")
        print("="*80)
        
        # Directory Structure
        print("\n📁 DIRECTORY STRUCTURE:")
        for name, info in self.analysis["structure"].items():
            if "status" in info:
                print(f"   {name}: {info['status']}")
            else:
                print(f"   {name}: {info['total_files']} files, {info['total_subdirs']} subdirs")
                print(f"      Path: {info['path']}")
        
        # File Count Summary
        print(f"\n📊 FILE COUNT SUMMARY:")
        total_files = sum(self.analysis["file_count"].values())
        print(f"   Total utility files: {total_files}")
        for name, count in self.analysis["file_count"].items():
            print(f"   {name}: {count} files")
        
        # Categories
        print(f"\n📂 UTILITY CATEGORIES:")
        for category, files in sorted(self.analysis["categories"].items()):
            if files:
                print(f"   {category}: {len(files)} files")
                for file_info in files[:3]:  # Show first 3 files
                    print(f"      • {file_info['file']} ({file_info['directory']})")
                if len(files) > 3:
                    print(f"      ... and {len(files) - 3} more")
        
        # Potential Duplicates
        if self.analysis["potential_duplicates"]:
            print(f"\n🔄 POTENTIAL DUPLICATES:")
            for duplicate in self.analysis["potential_duplicates"]:
                print(f"   {duplicate['base_name']}:")
                for file_info in duplicate['files']:
                    print(f"      • {file_info['file']} ({file_info['directory']})")
        
        # Optimization Recommendations
        if self.analysis["optimization_opportunities"]:
            print(f"\n🛠️  OPTIMIZATION RECOMMENDATIONS:")
            for i, rec in enumerate(self.analysis["optimization_opportunities"], 1):
                print(f"   {i}. {rec['type'].upper()}: {rec['description']}")
                print(f"      Action: {rec['action']}")
                print(f"      Impact: {rec['impact']}")
        
        # Save detailed report
        with open('common_utilities_analysis.json', 'w') as f:
            json.dump(self.analysis, f, indent=2)
        
        print(f"\n💾 Detailed analysis saved to: common_utilities_analysis.json")
    
    def run_analysis(self):
        """Run complete analysis"""
        self.analyze_directory_structure()
        self.categorize_utilities()
        self.identify_potential_duplicates()
        self.generate_optimization_recommendations()
        self.generate_report()

def main():
    analyzer = CommonUtilitiesAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main() 