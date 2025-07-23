#!/usr/bin/env python3
"""
Analyze Optimization Candidates - Phase 1 Week 3 Day 3
Identify agents for lazy loading and performance optimization deployment
"""

import sys
import os
import time
import yaml
import json
import requests
import psutil
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager

@dataclass
class AgentAnalysis:
    """Agent optimization analysis results"""
    name: str
    environment: str
    port: int
    script_path: str
    startup_time_estimate: float
    memory_usage_mb: float
    optimization_potential: str  # high, medium, low
    optimization_score: float
    recommended_patterns: List[str]
    dependencies: List[str]
    risk_level: str  # low, medium, high

class OptimizationCandidateAnalyzer:
    """Analyze agents for optimization opportunities"""
    
    def __init__(self):
        self.analyzed_agents = {}
        self.optimization_patterns = {
            "lazy_loading": {
                "description": "Defer heavy imports and initialization",
                "impact": "40-95% startup improvement",
                "complexity": "medium",
                "risk": "low"
            },
            "cache_optimization": {
                "description": "Implement intelligent caching for expensive operations",
                "impact": "30-60% runtime improvement",
                "complexity": "high", 
                "risk": "medium"
            },
            "dependency_reduction": {
                "description": "Remove or defer unnecessary dependencies",
                "impact": "20-50% startup improvement",
                "complexity": "low",
                "risk": "low"
            },
            "async_initialization": {
                "description": "Non-blocking initialization patterns",
                "impact": "50-80% perceived startup improvement",
                "complexity": "high",
                "risk": "medium"
            }
        }
        
        # Week 2 proven optimization results for reference
        self.proven_optimizations = {
            "face_recognition_agent": {"improvement": 93.6, "patterns": ["lazy_loading", "cache_optimization"]},
            "streaming_tts_agent": {"improvement": 75.0, "patterns": ["lazy_loading", "dependency_reduction"]},
            "model_manager_agent": {"improvement": 60.0, "patterns": ["cache_optimization", "async_initialization"]},
            "vram_optimizer_agent": {"improvement": 55.0, "patterns": ["lazy_loading"]},
            "noise_reduction_agent": {"improvement": 45.0, "patterns": ["dependency_reduction", "lazy_loading"]}
        }
    
    def analyze_all_agents(self, batch_size: int = 25) -> List[AgentAnalysis]:
        """Analyze all agents and identify optimization candidates"""
        print(f"🔍 ANALYZING AGENTS FOR OPTIMIZATION OPPORTUNITIES")
        print("=" * 60)
        
        # Load agent configurations
        agents = self._load_agent_configurations()
        print(f"✅ Found {len(agents)} total agents to analyze")
        
        # Filter out already optimized agents from Week 2
        unoptimized_agents = self._filter_unoptimized_agents(agents)
        print(f"✅ {len(unoptimized_agents)} agents remaining for optimization")
        
        # Analyze each agent
        analyses = []
        for agent in unoptimized_agents:
            try:
                analysis = self._analyze_agent(agent)
                analyses.append(analysis)
                print(f"   📊 {analysis.name}: {analysis.optimization_potential} potential ({analysis.optimization_score:.1f}/10)")
            except Exception as e:
                print(f"   ❌ {agent.get('name', 'unknown')}: Analysis failed - {e}")
        
        # Sort by optimization score (highest first)
        analyses.sort(key=lambda x: x.optimization_score, reverse=True)
        
        # Select top candidates for Batch 1
        batch1_candidates = analyses[:batch_size]
        
        print(f"\n🎯 BATCH 1 OPTIMIZATION CANDIDATES ({len(batch1_candidates)} agents):")
        for i, analysis in enumerate(batch1_candidates, 1):
            print(f"   {i:2d}. {analysis.name:<25} | Score: {analysis.optimization_score:4.1f} | Potential: {analysis.optimization_potential:6s} | Risk: {analysis.risk_level}")
        
        # Save analysis results
        self._save_analysis_results(batch1_candidates, analyses)
        
        return batch1_candidates
    
    def _load_agent_configurations(self) -> List[Dict[str, Any]]:
        """Load agent configurations from startup files"""
        agents = []
        
        # Load MainPC agents
        main_config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
        if main_config_path.exists():
            with open(main_config_path, 'r') as f:
                main_config = yaml.safe_load(f)
            
            agent_groups = main_config.get('agent_groups', {})
            for group_name, group_data in agent_groups.items():
                if 'agents' in group_data:
                    for agent_name, agent_config in group_data['agents'].items():
                        agent_config['name'] = agent_name
                        agent_config['environment'] = 'mainpc'
                        agent_config['group'] = group_name
                        agents.append(agent_config)
        
        # Load PC2 agents
        pc2_config_path = Path(PathManager.get_project_root()) / "pc2_code" / "config" / "startup_config.yaml"
        if pc2_config_path.exists():
            with open(pc2_config_path, 'r') as f:
                pc2_config = yaml.safe_load(f)
            
            pc2_services = pc2_config.get('pc2_services', [])
            for service in pc2_services:
                if isinstance(service, dict) and 'name' in service:
                    service['environment'] = 'pc2'
                    agents.append(service)
        
        return agents
    
    def _filter_unoptimized_agents(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out agents that were already optimized in Week 2"""
        optimized_agents = set(self.proven_optimizations.keys())
        
        # Also filter out infrastructure agents that shouldn't be optimized
        infrastructure_agents = {
            'EnhancedObservabilityHub', 'ObservabilityHub', 'MemoryHub', 
            'ModelManagerSuite', 'CoreOrchestrator'
        }
        
        unoptimized = []
        for agent in agents:
            agent_name = agent.get('name', '')
            if (agent_name not in optimized_agents and 
                agent_name not in infrastructure_agents and
                agent_name and
                agent.get('script_path')):  # Must have valid script path
                unoptimized.append(agent)
        
        return unoptimized
    
    def _analyze_agent(self, agent_config: Dict[str, Any]) -> AgentAnalysis:
        """Analyze individual agent for optimization opportunities"""
        agent_name = agent_config['name']
        script_path = agent_config.get('script_path', '')
        
        # Analyze script complexity and startup characteristics
        startup_analysis = self._analyze_startup_characteristics(script_path)
        memory_analysis = self._estimate_memory_usage(agent_config)
        dependency_analysis = self._analyze_dependencies(script_path)
        
        # Calculate optimization score
        optimization_score = self._calculate_optimization_score(
            startup_analysis, memory_analysis, dependency_analysis
        )
        
        # Determine optimization potential
        if optimization_score >= 8.0:
            potential = "high"
            risk = "low"
        elif optimization_score >= 6.0:
            potential = "medium"
            risk = "low"
        elif optimization_score >= 4.0:
            potential = "medium"
            risk = "medium"
        else:
            potential = "low"
            risk = "high"
        
        # Recommend optimization patterns
        recommended_patterns = self._recommend_patterns(
            startup_analysis, dependency_analysis, optimization_score
        )
        
        return AgentAnalysis(
            name=agent_name,
            environment=agent_config.get('environment', 'unknown'),
            port=agent_config.get('port', 0),
            script_path=script_path,
            startup_time_estimate=startup_analysis.get('estimated_startup_time', 1.0),
            memory_usage_mb=memory_analysis.get('estimated_memory_mb', 50),
            optimization_potential=potential,
            optimization_score=optimization_score,
            recommended_patterns=recommended_patterns,
            dependencies=dependency_analysis.get('heavy_dependencies', []),
            risk_level=risk
        )
    
    def _analyze_startup_characteristics(self, script_path: str) -> Dict[str, Any]:
        """Analyze script for startup time characteristics"""
        try:
            full_path = Path(PathManager.get_project_root()) / script_path
            if not full_path.exists():
                return {"estimated_startup_time": 1.0, "complexity": "unknown"}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Analyze import complexity
            import_count = content.count('import ')
            from_import_count = content.count('from ')
            total_imports = import_count + from_import_count
            
            # Look for heavy libraries
            heavy_libraries = [
                'torch', 'tensorflow', 'transformers', 'opencv', 'cv2',
                'numpy', 'pandas', 'sklearn', 'scipy', 'matplotlib',
                'requests', 'aiohttp', 'fastapi', 'flask'
            ]
            
            heavy_import_count = sum(1 for lib in heavy_libraries if lib in content)
            
            # Look for immediate initialization patterns
            immediate_init_patterns = [
                'model = ', 'tokenizer = ', '.load(', '.from_pretrained(',
                'cv2.', 'torch.', 'tf.', 'initialize(', 'setup('
            ]
            
            immediate_init_count = sum(1 for pattern in immediate_init_patterns if pattern in content)
            
            # Estimate startup time based on complexity
            base_time = 0.5
            import_penalty = total_imports * 0.05
            heavy_penalty = heavy_import_count * 0.3
            init_penalty = immediate_init_count * 0.2
            
            estimated_time = base_time + import_penalty + heavy_penalty + init_penalty
            
            return {
                "estimated_startup_time": estimated_time,
                "total_imports": total_imports,
                "heavy_imports": heavy_import_count,
                "immediate_inits": immediate_init_count,
                "complexity": "high" if estimated_time > 2.0 else "medium" if estimated_time > 1.0 else "low"
            }
            
        except Exception as e:
            return {"estimated_startup_time": 1.0, "complexity": "unknown", "error": str(e)}
    
    def _estimate_memory_usage(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate memory usage based on agent characteristics"""
        # Base memory for Python process
        base_memory = 30
        
        # Add memory based on agent type/functionality
        agent_name = agent_config.get('name', '').lower()
        
        if any(keyword in agent_name for keyword in ['model', 'ai', 'ml', 'neural']):
            base_memory += 200  # ML models are memory intensive
        elif any(keyword in agent_name for keyword in ['vision', 'image', 'video']):
            base_memory += 150  # Vision processing
        elif any(keyword in agent_name for keyword in ['audio', 'tts', 'speech']):
            base_memory += 100  # Audio processing
        elif any(keyword in agent_name for keyword in ['web', 'scraper', 'http']):
            base_memory += 50   # Web services
        else:
            base_memory += 25   # Standard service
        
        return {"estimated_memory_mb": base_memory}
    
    def _analyze_dependencies(self, script_path: str) -> Dict[str, Any]:
        """Analyze script dependencies for optimization opportunities"""
        try:
            full_path = Path(PathManager.get_project_root()) / script_path
            if not full_path.exists():
                return {"heavy_dependencies": [], "dependency_count": 0}
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Identify heavy dependencies
            heavy_deps = []
            if 'torch' in content or 'pytorch' in content:
                heavy_deps.append('pytorch')
            if 'transformers' in content:
                heavy_deps.append('transformers')
            if 'cv2' in content or 'opencv' in content:
                heavy_deps.append('opencv')
            if 'tensorflow' in content or 'tf.' in content:
                heavy_deps.append('tensorflow')
            if 'numpy' in content:
                heavy_deps.append('numpy')
            if 'pandas' in content:
                heavy_deps.append('pandas')
            if 'requests' in content:
                heavy_deps.append('requests')
            if 'fastapi' in content or 'uvicorn' in content:
                heavy_deps.append('fastapi')
            
            return {
                "heavy_dependencies": heavy_deps,
                "dependency_count": len(heavy_deps)
            }
            
        except Exception as e:
            return {"heavy_dependencies": [], "dependency_count": 0, "error": str(e)}
    
    def _calculate_optimization_score(self, startup_analysis: Dict, memory_analysis: Dict, dependency_analysis: Dict) -> float:
        """Calculate optimization score (0-10, higher = better candidate)"""
        score = 0.0
        
        # Startup time impact (0-4 points)
        startup_time = startup_analysis.get('estimated_startup_time', 1.0)
        if startup_time > 3.0:
            score += 4.0
        elif startup_time > 2.0:
            score += 3.0
        elif startup_time > 1.5:
            score += 2.0
        elif startup_time > 1.0:
            score += 1.0
        
        # Heavy dependencies impact (0-3 points)
        heavy_deps = len(dependency_analysis.get('heavy_dependencies', []))
        score += min(heavy_deps * 0.5, 3.0)
        
        # Memory usage impact (0-2 points)
        memory_mb = memory_analysis.get('estimated_memory_mb', 50)
        if memory_mb > 200:
            score += 2.0
        elif memory_mb > 100:
            score += 1.0
        
        # Immediate initialization penalty/opportunity (0-1 points)
        immediate_inits = startup_analysis.get('immediate_inits', 0)
        score += min(immediate_inits * 0.2, 1.0)
        
        return min(score, 10.0)
    
    def _recommend_patterns(self, startup_analysis: Dict, dependency_analysis: Dict, score: float) -> List[str]:
        """Recommend optimization patterns based on analysis"""
        patterns = []
        
        # Always recommend lazy loading for high-scoring agents
        if score >= 6.0:
            patterns.append("lazy_loading")
        
        # Recommend cache optimization for dependency-heavy agents
        if len(dependency_analysis.get('heavy_dependencies', [])) >= 2:
            patterns.append("cache_optimization")
        
        # Recommend dependency reduction for heavily dependent agents
        if len(dependency_analysis.get('heavy_dependencies', [])) >= 3:
            patterns.append("dependency_reduction")
        
        # Recommend async initialization for complex startup patterns
        if startup_analysis.get('immediate_inits', 0) >= 3:
            patterns.append("async_initialization")
        
        # Ensure at least one pattern is recommended
        if not patterns:
            patterns.append("lazy_loading")
        
        return patterns
    
    def _save_analysis_results(self, batch1_candidates: List[AgentAnalysis], all_analyses: List[AgentAnalysis]):
        """Save analysis results to files"""
        try:
            results_dir = Path(PathManager.get_project_root()) / "implementation_roadmap" / "PHASE1_ACTION_PLAN"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Save Batch 1 candidates
            batch1_file = results_dir / "PHASE_1_WEEK_3_DAY_3_BATCH1_CANDIDATES.json"
            batch1_data = {
                "timestamp": time.time(),
                "total_candidates": len(batch1_candidates),
                "optimization_target": ">40% improvement",
                "candidates": [
                    {
                        "name": analysis.name,
                        "environment": analysis.environment,
                        "port": analysis.port,
                        "script_path": analysis.script_path,
                        "optimization_score": analysis.optimization_score,
                        "optimization_potential": analysis.optimization_potential,
                        "recommended_patterns": analysis.recommended_patterns,
                        "startup_time_estimate": analysis.startup_time_estimate,
                        "risk_level": analysis.risk_level
                    }
                    for analysis in batch1_candidates
                ]
            }
            
            with open(batch1_file, 'w') as f:
                json.dump(batch1_data, f, indent=2)
            
            # Save simplified text file for script consumption
            candidates_file = results_dir / "batch1_candidates.txt"
            with open(candidates_file, 'w') as f:
                for analysis in batch1_candidates:
                    f.write(f"{analysis.name}\n")
            
            # Save comprehensive analysis report
            report_file = results_dir / "PHASE_1_WEEK_3_DAY_3_OPTIMIZATION_ANALYSIS.json"
            report_data = {
                "analysis_timestamp": time.time(),
                "total_agents_analyzed": len(all_analyses),
                "batch1_candidates": len(batch1_candidates),
                "optimization_patterns": self.optimization_patterns,
                "proven_optimizations": self.proven_optimizations,
                "all_analyses": [
                    {
                        "name": analysis.name,
                        "environment": analysis.environment,
                        "optimization_score": analysis.optimization_score,
                        "optimization_potential": analysis.optimization_potential,
                        "recommended_patterns": analysis.recommended_patterns,
                        "risk_level": analysis.risk_level
                    }
                    for analysis in all_analyses
                ]
            }
            
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n✅ Analysis results saved:")
            print(f"   📊 Batch 1 candidates: {batch1_file}")
            print(f"   📝 Candidates list: {candidates_file}")
            print(f"   📋 Full analysis: {report_file}")
            
        except Exception as e:
            print(f"❌ Error saving analysis results: {e}")

def main():
    """Main analysis execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze agents for optimization opportunities")
    parser.add_argument("--batch-1", action="store_true", help="Analyze for Batch 1 deployment")
    parser.add_argument("--count", type=int, default=25, help="Number of candidates for Batch 1")
    parser.add_argument("--environment", choices=["mainpc", "pc2", "all"], default="all", help="Environment to analyze")
    
    args = parser.parse_args()
    
    analyzer = OptimizationCandidateAnalyzer()
    
    if args.batch_1:
        candidates = analyzer.analyze_all_agents(batch_size=args.count)
        
        print(f"\n🎯 OPTIMIZATION ANALYSIS COMPLETE")
        print(f"   📊 {len(candidates)} Batch 1 candidates identified")
        print(f"   🎯 Target: >40% improvement per agent")
        print(f"   📈 Expected system-wide impact: Significant performance gains")
        
        return len(candidates) > 0
    else:
        print("❌ Please specify --batch-1 for Batch 1 analysis")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 