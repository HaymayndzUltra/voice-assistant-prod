#!/usr/bin/env python3
"""
SAMPLE VERIFICATION DEMO
Demo script showing how to verify CoreOrchestrator consolidation
"""

import os
import sys
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Any

class ConsolidationVerifier:
    """Demo verification tool for consolidated agents"""
    
    def __init__(self, target_path: str, source_agents: List[str]):
        self.target_path = Path(target_path)
        self.source_agents = source_agents
        self.verification_results = {
            'source_mapping': {},
            'api_endpoints': {},
            'core_functions': {},
            'dependencies': {},
            'overall_score': 0
        }
    
    def run_verification(self) -> Dict:
        """Run complete verification process"""
        print(f"🔍 VERIFYING: {self.target_path.name}")
        print(f"📝 SOURCE AGENTS: {', '.join(self.source_agents)}")
        print("=" * 60)
        
        # Step 1: Check source agent mapping
        self.verify_source_mapping()
        
        # Step 2: Analyze API endpoints
        self.analyze_api_endpoints()
        
        # Step 3: Check core functions
        self.verify_core_functions()
        
        # Step 4: Validate dependencies
        self.check_dependencies()
        
        # Step 5: Calculate overall score
        self.calculate_score()
        
        return self.verification_results
    
    def verify_source_mapping(self):
        """Check if source agents are properly referenced"""
        print("📋 1. SOURCE AGENT MAPPING VERIFICATION")
        
        found_references = {}
        main_file = self.target_path / f"{self.target_path.name}.py"
        
        if main_file.exists():
            content = main_file.read_text()
            
            for agent in self.source_agents:
                # Check for class references, imports, or comments
                patterns = [
                    rf"class.*{agent}",
                    rf"from.*{agent}",
                    rf"import.*{agent}",
                    rf"# .*{agent}",
                    rf'"{agent}"',
                    rf"'{agent}'"
                ]
                
                found = any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
                found_references[agent] = found
                
                status = "✅" if found else "❌"
                print(f"   {status} {agent}: {'Found' if found else 'NOT FOUND'}")
        
        self.verification_results['source_mapping'] = found_references
        
    def analyze_api_endpoints(self):
        """Extract and analyze API endpoints"""
        print("\n🌐 2. API ENDPOINTS ANALYSIS")
        
        endpoints = []
        main_file = self.target_path / f"{self.target_path.name}.py"
        
        if main_file.exists():
            content = main_file.read_text()
            
            # Find FastAPI/Flask routes
            route_patterns = [
                r'@app\.(get|post|put|delete|patch)\(["\']([^"\']*)["\']',
                r'@.*\.route\(["\']([^"\']*)["\']',
                r'app\.add_api_route\(["\']([^"\']*)["\']'
            ]
            
            for pattern in route_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        endpoints.append(match[-1])  # Get the route path
                    else:
                        endpoints.append(match)
        
        print(f"   📡 Found {len(endpoints)} API endpoints:")
        for endpoint in endpoints[:5]:  # Show first 5
            print(f"      • {endpoint}")
        if len(endpoints) > 5:
            print(f"      ... and {len(endpoints) - 5} more")
            
        self.verification_results['api_endpoints'] = {
            'count': len(endpoints),
            'endpoints': endpoints
        }
    
    def verify_core_functions(self):
        """Check for core functions and classes"""
        print("\n⚙️ 3. CORE FUNCTIONS VERIFICATION") 
        
        functions = []
        classes = []
        main_file = self.target_path / f"{self.target_path.name}.py"
        
        if main_file.exists():
            try:
                content = main_file.read_text()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        functions.append(node.name)
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                        
            except Exception as e:
                print(f"   ⚠️  Could not parse Python file: {e}")
        
        print(f"   🏗️  Found {len(classes)} classes:")
        for cls in classes[:3]:
            print(f"      • {cls}")
        if len(classes) > 3:
            print(f"      ... and {len(classes) - 3} more")
            
        print(f"   🔧 Found {len(functions)} functions:")
        for func in functions[:5]:
            print(f"      • {func}")
        if len(functions) > 5:
            print(f"      ... and {len(functions) - 5} more")
            
        self.verification_results['core_functions'] = {
            'classes': classes,
            'functions': functions
        }
    
    def check_dependencies(self):
        """Check dependency imports and configurations"""
        print("\n📦 4. DEPENDENCIES CHECK")
        
        imports = []
        main_file = self.target_path / f"{self.target_path.name}.py"
        
        if main_file.exists():
            content = main_file.read_text()
            
            # Find import statements
            import_patterns = [
                r'^import\s+([^\s#]+)',
                r'^from\s+([^\s#]+)\s+import'
            ]
            
            for line in content.split('\n'):
                for pattern in import_patterns:
                    match = re.match(pattern, line.strip())
                    if match:
                        imports.append(match.group(1))
        
        print(f"   📥 Found {len(imports)} imports:")
        for imp in imports[:5]:
            print(f"      • {imp}")
        if len(imports) > 5:
            print(f"      ... and {len(imports) - 5} more")
            
        self.verification_results['dependencies'] = {
            'imports': imports,
            'count': len(imports)
        }
    
    def calculate_score(self):
        """Calculate overall verification score"""
        print("\n📊 5. OVERALL VERIFICATION SCORE")
        
        # Source mapping score (40% weight)
        mapped_agents = sum(1 for found in self.verification_results['source_mapping'].values() if found)
        total_agents = len(self.source_agents)
        mapping_score = (mapped_agents / total_agents) * 40 if total_agents > 0 else 0
        
        # API endpoints score (25% weight)
        endpoint_count = self.verification_results['api_endpoints']['count']
        endpoint_score = min(endpoint_count * 5, 25)  # Max 25 points
        
        # Core functions score (25% weight)
        function_count = len(self.verification_results['core_functions']['functions'])
        function_score = min(function_count * 2, 25)  # Max 25 points
        
        # Dependencies score (10% weight)
        import_count = self.verification_results['dependencies']['count']
        dependency_score = min(import_count * 1, 10)  # Max 10 points
        
        total_score = mapping_score + endpoint_score + function_score + dependency_score
        
        print(f"   🎯 Source Mapping: {mapped_agents}/{total_agents} agents ({mapping_score:.1f}/40 points)")
        print(f"   🌐 API Endpoints: {endpoint_count} endpoints ({endpoint_score:.1f}/25 points)")
        print(f"   ⚙️  Core Functions: {function_count} functions ({function_score:.1f}/25 points)")
        print(f"   📦 Dependencies: {import_count} imports ({dependency_score:.1f}/10 points)")
        print(f"   🏆 TOTAL SCORE: {total_score:.1f}/100")
        
        # Determine grade
        if total_score >= 95:
            grade = "EXCELLENT ✅"
        elif total_score >= 85:
            grade = "GOOD ✅"
        elif total_score >= 70:
            grade = "ACCEPTABLE ⚠️"
        else:
            grade = "NEEDS WORK ❌"
            
        print(f"   📋 GRADE: {grade}")
        
        self.verification_results['overall_score'] = total_score
        self.verification_results['grade'] = grade

def demo_core_orchestrator_verification():
    """Demo verification of CoreOrchestrator"""
    print("🚀 CONSOLIDATION VERIFICATION DEMO")
    print("=" * 60)
    
    # CoreOrchestrator verification
    target_path = "phase0_implementation/group_01_core_observability/core_orchestrator"
    source_agents = ["ServiceRegistry", "SystemDigitalTwin", "RequestCoordinator", "UnifiedSystemAgent"]
    
    verifier = ConsolidationVerifier(target_path, source_agents)
    results = verifier.run_verification()
    
    print("\n" + "=" * 60)
    print("📋 VERIFICATION COMPLETE!")
    print(f"📊 Final Score: {results['overall_score']:.1f}/100")
    print(f"🏆 Grade: {results['grade']}")
    
    return results

def demo_memory_hub_verification():
    """Demo verification of MemoryHub"""
    print("\n🚀 MEMORY HUB VERIFICATION DEMO")
    print("=" * 60)
    
    # MemoryHub verification  
    target_path = "phase1_implementation/group_01_memory_hub/memory_hub"
    source_agents = [
        "MemoryClient", "SessionMemoryAgent", "KnowledgeBase", 
        "MemoryOrchestratorService", "UnifiedMemoryReasoningAgent",
        "ContextManager", "ExperienceTracker", "CacheManager"
    ]
    
    verifier = ConsolidationVerifier(target_path, source_agents)
    results = verifier.run_verification()
    
    print("\n" + "=" * 60)
    print("📋 MEMORY HUB VERIFICATION COMPLETE!")
    print(f"📊 Final Score: {results['overall_score']:.1f}/100")
    print(f"🏆 Grade: {results['grade']}")
    
    return results

if __name__ == "__main__":
    print("🔍 CONSOLIDATION VERIFICATION DEMO TOOL")
    print("This tool demonstrates how to verify consolidated agents")
    print("=" * 80)
    
    # Run demos
    core_results = demo_core_orchestrator_verification()
    memory_results = demo_memory_hub_verification()
    
    print("\n🎯 SUMMARY REPORT")
    print("=" * 60)
    print(f"CoreOrchestrator: {core_results['grade']} ({core_results['overall_score']:.1f}/100)")
    print(f"MemoryHub: {memory_results['grade']} ({memory_results['overall_score']:.1f}/100)")
    
    print("\n💡 HOW TO USE THIS STRATEGY:")
    print("1. Run verification for each consolidated agent")
    print("2. Review detailed findings and fix issues")
    print("3. Re-run verification until 95%+ score achieved")
    print("4. Proceed to integration testing")
    print("5. Deploy with confidence!") 