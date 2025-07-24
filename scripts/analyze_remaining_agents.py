#!/usr/bin/env python3
"""
Analyze Remaining Agents - Phase 1 Week 3 Day 4
Enhanced agent discovery with improved path resolution for optimization deployment
Addresses Day 3 path detection challenges
"""

import sys
import os
import time
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

@dataclass
class AgentDiscoveryResult:
    """Enhanced agent discovery result with path resolution"""
    name: str
    environment: str
    script_path: str
    resolved_path: Path
    exists: bool
    optimization_ready: bool
    issues: List[str]
    recommended_action: str

class EnhancedAgentAnalyzer:
    """Enhanced agent analyzer with improved path resolution"""
    
    def __init__(self):
        self.project_root = Path(PathManager.get_project_root())
        self.discovery_results = []
        self.path_patterns = [
            # Standard agent locations
            "main_pc_code/agents/{agent_name}.py",
            "pc2_code/agents/{agent_name}.py",
            
            # Consolidated agents
            "phase1_implementation/consolidated_agents/{agent_name}/{agent_name}.py",
            "phase1_implementation/consolidated_agents/{agent_name}/{agent_name}_unified.py",
            
            # Specialized directories
            "main_pc_code/FORMAINPC/{agent_name}.py",
            "pc2_code/agents/ForPC2/{agent_name}.py",
            "pc2_code/agents/core_agents/{agent_name}.py",
            
            # Alternative naming patterns
            "main_pc_code/agents/{agent_name_lower}.py",
            "pc2_code/agents/{agent_name_lower}.py",
            "main_pc_code/agents/{agent_name}_agent.py",
            "pc2_code/agents/{agent_name}_agent.py",
            
            # Legacy locations
            "agents/{agent_name}.py",
            "src/agents/{agent_name}.py"
        ]
        
        # Already optimized agents from previous days
        self.optimized_agents = {
            "face_recognition_agent", "streaming_tts_agent", "model_manager_agent",
            "vram_optimizer_agent", "noise_reduction_agent"
        }
        
        # Infrastructure agents to skip
        self.infrastructure_agents = {
            "EnhancedObservabilityHub", "ObservabilityHub", "MemoryHub",
            "ModelManagerSuite", "CoreOrchestrator", "BaseAgent"
        }
    
    def analyze_remaining_agents(self) -> Dict[str, Any]:
        """Analyze all remaining agents for optimization readiness"""
        print("🔍 ENHANCED AGENT DISCOVERY & ANALYSIS")
        print("=" * 50)
        
        # Discover agents from both environments
        all_agents = self._discover_all_agents()
        print(f"✅ Discovered {len(all_agents)} total agents")
        
        # Filter for optimization candidates
        remaining_agents = self._filter_remaining_agents(all_agents)
        print(f"✅ {len(remaining_agents)} agents remaining for optimization")
        
        # Enhanced path resolution
        resolved_agents = self._resolve_agent_paths(remaining_agents)
        print(f"✅ {len([a for a in resolved_agents if a.exists])} agents with valid paths found")
        
        # Analyze optimization readiness
        optimization_ready = self._analyze_optimization_readiness(resolved_agents)
        
        # Generate comprehensive report
        report = self._generate_analysis_report(optimization_ready)
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   🎯 Optimization Ready: {report['optimization_ready_count']}")
        print(f"   ⚠️  Path Issues: {report['path_issues_count']}")
        print(f"   📝 Manual Review: {report['manual_review_count']}")
        
        return report
    
    def _discover_all_agents(self) -> List[Dict[str, Any]]:
        """Enhanced agent discovery from both startup configs"""
        agents = []
        
        # MainPC agents
        main_config = self._load_startup_config("mainpc")
        if main_config:
            agents.extend(self._extract_mainpc_agents(main_config))
        
        # PC2 agents
        pc2_config = self._load_startup_config("pc2")
        if pc2_config:
            agents.extend(self._extract_pc2_agents(pc2_config))
        
        return agents
    
    def _load_startup_config(self, environment: str) -> Dict[str, Any]:
        """Load startup configuration for environment"""
        try:
            if environment == "pc2":
                config_path = self.project_root / "pc2_code" / "config" / "startup_config.yaml"
            else:
                config_path = self.project_root / "main_pc_code" / "config" / "startup_config.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                print(f"⚠️  Config not found: {config_path}")
                
        except Exception as e:
            print(f"❌ Error loading {environment} config: {e}")
        
        return {}
    
    def _extract_mainpc_agents(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract agents from MainPC configuration"""
        agents = []
        
        agent_groups = config.get('agent_groups', {})
        for group_name, group_data in agent_groups.items():
            if isinstance(group_data, dict) and 'agents' in group_data:
                for agent_name, agent_config in group_data['agents'].items():
                    agents.append({
                        'name': agent_name,
                        'environment': 'mainpc',
                        'group': group_name,
                        'script_path': agent_config.get('script_path', ''),
                        'port': agent_config.get('port'),
                        'config': agent_config
                    })
        
        return agents
    
    def _extract_pc2_agents(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract agents from PC2 configuration"""
        agents = []
        
        pc2_services = config.get('pc2_services', [])
        for service in pc2_services:
            if isinstance(service, dict) and 'name' in service:
                agents.append({
                    'name': service['name'],
                    'environment': 'pc2',
                    'script_path': service.get('script_path', ''),
                    'port': service.get('port'),
                    'config': service
                })
        
        return agents
    
    def _filter_remaining_agents(self, all_agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter agents that need optimization"""
        remaining = []
        
        for agent in all_agents:
            agent_name = agent['name']
            
            # Skip already optimized agents
            if agent_name in self.optimized_agents:
                continue
            
            # Skip infrastructure agents
            if agent_name in self.infrastructure_agents:
                continue
            
            # Skip agents without script paths
            if not agent.get('script_path'):
                continue
            
            remaining.append(agent)
        
        return remaining
    
    def _resolve_agent_paths(self, agents: List[Dict[str, Any]]) -> List[AgentDiscoveryResult]:
        """Enhanced path resolution for agents"""
        results = []
        
        for agent in agents:
            agent_name = agent['name']
            declared_path = agent.get('script_path', '')
            
            # Try to resolve the declared path first
            resolved_path, exists = self._resolve_single_path(declared_path)
            
            issues = []
            recommended_action = "ready"
            
            if not exists:
                # Try alternative paths
                resolved_path, exists = self._try_alternative_paths(agent_name)
                if not exists:
                    issues.append(f"Script not found: {declared_path}")
                    recommended_action = "fix_path"
                else:
                    issues.append(f"Using alternative path instead of declared: {declared_path}")
                    recommended_action = "update_config"
            
            # Validate script content if file exists
            if exists:
                content_issues = self._validate_script_content(resolved_path)
                issues.extend(content_issues)
                if content_issues:
                    recommended_action = "fix_content"
            
            results.append(AgentDiscoveryResult(
                name=agent_name,
                environment=agent['environment'],
                script_path=declared_path,
                resolved_path=resolved_path,
                exists=exists,
                optimization_ready=(exists and not issues),
                issues=issues,
                recommended_action=recommended_action
            ))
        
        return results
    
    def _resolve_single_path(self, script_path: str) -> Tuple[Path, bool]:
        """Resolve a single script path"""
        if not script_path:
            return Path(), False
        
        # Try absolute path from project root
        abs_path = self.project_root / script_path
        if abs_path.exists():
            return abs_path, True
        
        # Try relative path as-is
        rel_path = Path(script_path)
        if rel_path.exists():
            return rel_path.resolve(), True
        
        return abs_path, False
    
    def _try_alternative_paths(self, agent_name: str) -> Tuple[Path, bool]:
        """Try alternative paths for agent"""
        variations = [
            agent_name,
            agent_name.lower(),
            agent_name.replace('Agent', ''),
            agent_name.lower().replace('agent', ''),
            f"{agent_name.lower()}_agent"
        ]
        
        for pattern in self.path_patterns:
            for variation in variations:
                try:
                    path_str = pattern.format(
                        agent_name=variation,
                        agent_name_lower=variation.lower()
                    )
                    full_path = self.project_root / path_str
                    
                    if full_path.exists():
                        return full_path, True
                        
                except (KeyError, ValueError):
                    continue
        
        return Path(), False
    
    def _validate_script_content(self, script_path: Path) -> List[str]:
        """Validate script content for optimization readiness"""
        issues = []
        
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for Python syntax
            try:
                compile(content, str(script_path), 'exec')
            except SyntaxError as e:
                issues.append(f"Syntax error: {e}")
            
            # Check for BaseAgent inheritance
            if 'BaseAgent' not in content:
                issues.append("Does not inherit from BaseAgent - requires migration")
            
            # Check for main execution block
            if 'if __name__ == "__main__"' not in content:
                issues.append("Missing main execution block")
            
            # Check for heavy imports that could benefit from lazy loading
            heavy_imports = ['torch', 'transformers', 'cv2', 'tensorflow', 'numpy']
            found_heavy = [lib for lib in heavy_imports if lib in content]
            if len(found_heavy) >= 2:
                # This is actually good for optimization, not an issue
                pass
            
        except Exception as e:
            issues.append(f"Could not validate content: {e}")
        
        return issues
    
    def _analyze_optimization_readiness(self, agents: List[AgentDiscoveryResult]) -> List[AgentDiscoveryResult]:
        """Analyze optimization readiness for each agent"""
        ready_agents = []
        
        for agent in agents:
            if agent.exists and not agent.issues:
                agent.optimization_ready = True
                ready_agents.append(agent)
            elif agent.exists and len(agent.issues) == 1 and "BaseAgent" in agent.issues[0]:
                # Agent exists but needs BaseAgent migration - still optimizable
                agent.optimization_ready = True
                agent.recommended_action = "migrate_then_optimize"
                ready_agents.append(agent)
        
        return ready_agents
    
    def _generate_analysis_report(self, ready_agents: List[AgentDiscoveryResult]) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        all_results = self.discovery_results + ready_agents
        
        # Categorize results
        optimization_ready = [a for a in all_results if a.optimization_ready]
        path_issues = [a for a in all_results if not a.exists]
        manual_review = [a for a in all_results if a.exists and not a.optimization_ready]
        
        # Save detailed results
        self._save_detailed_report(optimization_ready, path_issues, manual_review)
        
        return {
            "analysis_timestamp": time.time(),
            "total_agents_analyzed": len(all_results),
            "optimization_ready_count": len(optimization_ready),
            "path_issues_count": len(path_issues),
            "manual_review_count": len(manual_review),
            "optimization_ready_agents": [a.name for a in optimization_ready],
            "path_issues_agents": [{"name": a.name, "issues": a.issues} for a in path_issues],
            "manual_review_agents": [{"name": a.name, "issues": a.issues} for a in manual_review],
            "ready_for_optimization": len(optimization_ready) > 0
        }
    
    def _save_detailed_report(self, ready: List[AgentDiscoveryResult], path_issues: List[AgentDiscoveryResult], manual: List[AgentDiscoveryResult]):
        """Save detailed analysis report"""
        try:
            results_dir = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN"
            
            # Save optimization-ready agents
            ready_file = results_dir / "PHASE_1_WEEK_3_DAY_4_OPTIMIZATION_READY.json"
            ready_data = {
                "timestamp": time.time(),
                "optimization_ready_agents": [
                    {
                        "name": agent.name,
                        "environment": agent.environment,
                        "script_path": agent.script_path,
                        "resolved_path": str(agent.resolved_path),
                        "recommended_action": agent.recommended_action
                    }
                    for agent in ready
                ]
            }
            
            with open(ready_file, 'w') as f:
                json.dump(ready_data, f, indent=2)
            
            # Save agents with path issues
            issues_file = results_dir / "PHASE_1_WEEK_3_DAY_4_PATH_ISSUES.json"
            issues_data = {
                "timestamp": time.time(),
                "agents_with_path_issues": [
                    {
                        "name": agent.name,
                        "environment": agent.environment,
                        "script_path": agent.script_path,
                        "issues": agent.issues,
                        "recommended_action": agent.recommended_action
                    }
                    for agent in path_issues
                ]
            }
            
            with open(issues_file, 'w') as f:
                json.dump(issues_data, f, indent=2)
            
            # Save simple text file for script consumption
            ready_agents_file = results_dir / "optimization_ready_agents.txt"
            with open(ready_agents_file, 'w') as f:
                for agent in ready:
                    f.write(f"{agent.name}\n")
            
            print(f"\n✅ Analysis reports saved:")
            print(f"   📊 Ready agents: {ready_file}")
            print(f"   ⚠️  Path issues: {issues_file}")
            print(f"   📝 Ready list: {ready_agents_file}")
            
        except Exception as e:
            print(f"❌ Error saving analysis reports: {e}")

def main():
    """Main analysis execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze remaining agents for optimization")
    parser.add_argument("--optimization-readiness", action="store_true", help="Analyze optimization readiness")
    parser.add_argument("--fix-paths", action="store_true", help="Attempt to fix path issues")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    analyzer = EnhancedAgentAnalyzer()
    
    if args.optimization_readiness:
        report = analyzer.analyze_remaining_agents()
        
        print(f"\n🎯 OPTIMIZATION READINESS ANALYSIS COMPLETE")
        print(f"   📊 Ready for optimization: {report['optimization_ready_count']} agents")
        print(f"   ⚠️  Need path fixes: {report['path_issues_count']} agents")
        print(f"   📝 Need manual review: {report['manual_review_count']} agents")
        
        if report['ready_for_optimization']:
            print(f"\n✅ System ready for Day 4 optimization deployment!")
        else:
            print(f"\n⚠️  System needs path resolution before optimization")
        
        return report['ready_for_optimization']
    else:
        print("❌ Please specify --optimization-readiness for Day 4 analysis")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 