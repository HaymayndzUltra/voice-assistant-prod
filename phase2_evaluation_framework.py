#!/usr/bin/env python3
"""
Phase 2: Agent Evaluation Framework
Defines worthiness criteria and analyzes resource usage patterns
for 54 MainPC + 23 PC2 agents across dual GPU systems.

Hardware Context:
- MainPC: RTX 4090, Ryzen 9 7900, 32GB RAM
- PC2: RTX 3060, lower CPU configuration
"""

import json
import yaml
from pathlib import Path
from collections import defaultdict
import re

class AgentEvaluationFramework:
    def __init__(self):
        self.evaluation_criteria = {
            'usage_frequency': {
                'critical': 0.9,      # Used in 90%+ scenarios  
                'high': 0.7,          # Used in 70%+ scenarios
                'medium': 0.4,        # Used in 40%+ scenarios
                'low': 0.2,           # Used in 20%+ scenarios
                'minimal': 0.05       # Used in 5%+ scenarios
            },
            'resource_impact': {
                'gpu_intensive': 1.0,    # Requires GPU resources
                'memory_heavy': 0.8,     # High memory usage
                'cpu_intensive': 0.6,    # High CPU usage  
                'network_heavy': 0.4,    # High network I/O
                'io_bound': 0.2         # Disk I/O operations
            },
            'dependency_criticality': {
                'foundation': 1.0,       # Core infrastructure
                'critical_path': 0.8,    # In critical execution path
                'shared_service': 0.6,   # Used by multiple agents
                'specialized': 0.4,      # Specialized functionality
                'optional': 0.2         # Optional/enhancement features
            },
            'performance_requirements': {
                'real_time': 1.0,        # Real-time processing needed
                'low_latency': 0.8,      # Low latency required
                'standard': 0.6,         # Standard processing
                'batch_ok': 0.4,         # Batch processing acceptable
                'async_ok': 0.2         # Async processing acceptable
            }
        }
        
        self.hardware_profiles = {
            'MainPC': {
                'gpu': 'RTX_4090',
                'gpu_memory': 24576,     # 24GB VRAM
                'cpu': 'Ryzen_9_7900',
                'cpu_cores': 12,
                'ram': 32768,            # 32GB RAM
                'nvme_storage': True,
                'optimization_focus': 'AI_processing'
            },
            'PC2': {
                'gpu': 'RTX_3060',
                'gpu_memory': 12288,     # 12GB VRAM (assumption)
                'cpu': 'lower_spec',
                'cpu_cores': 8,          # Assumption
                'ram': 16384,            # 16GB RAM (assumption)
                'optimization_focus': 'memory_and_cache'
            }
        }

    def load_agent_data(self, json_file_path):
        """Load agent data from Phase 1 analysis"""
        with open(json_file_path, 'r') as f:
            return json.load(f)

    def evaluate_agent_usage(self, agent):
        """
        Evaluate agent usage frequency based on dependencies and function
        
        Args:
            agent (dict): Agent information
            
        Returns:
            dict: Usage evaluation
        """
        agent_name = agent['name'].lower()
        group = agent['group'].lower()
        dependencies = agent.get('dependencies', [])
        
        # Foundation services are critical
        if 'foundation' in group or agent_name in ['serviceregistry', 'systemdigitaltwin']:
            usage_score = self.evaluation_criteria['usage_frequency']['critical']
            usage_level = 'critical'
            reasoning = 'Foundation service - critical infrastructure'
            
        # Memory and core communication services
        elif any(keyword in agent_name for keyword in ['memory', 'coordinator', 'orchestrator']):
            usage_score = self.evaluation_criteria['usage_frequency']['high'] 
            usage_level = 'high'
            reasoning = 'Core system service with high usage'
            
        # AI processing and language services
        elif any(keyword in agent_name for keyword in ['model', 'nlu', 'reasoning', 'llm']):
            usage_score = self.evaluation_criteria['usage_frequency']['high']
            usage_level = 'high' 
            reasoning = 'AI processing service - high demand'
            
        # Audio/speech services (frequent user interaction)
        elif any(keyword in agent_name for keyword in ['audio', 'speech', 'stt', 'tts', 'streaming']):
            usage_score = self.evaluation_criteria['usage_frequency']['medium']
            usage_level = 'medium'
            reasoning = 'User interface service - moderate usage'
            
        # Specialized services 
        elif any(keyword in agent_name for keyword in ['emotion', 'translation', 'learning']):
            usage_score = self.evaluation_criteria['usage_frequency']['medium']
            usage_level = 'medium'
            reasoning = 'Specialized service - contextual usage'
            
        # Utility and monitoring services
        elif any(keyword in agent_name for keyword in ['utility', 'monitor', 'health', 'optimizer']):
            usage_score = self.evaluation_criteria['usage_frequency']['low']
            usage_level = 'low'
            reasoning = 'Utility service - background usage'
            
        else:
            usage_score = self.evaluation_criteria['usage_frequency']['minimal']
            usage_level = 'minimal'
            reasoning = 'Specialized/optional service'

        return {
            'usage_score': usage_score,
            'usage_level': usage_level,
            'reasoning': reasoning
        }

    def evaluate_resource_impact(self, agent, system):
        """
        Evaluate resource impact based on agent function and system capabilities
        
        Args:
            agent (dict): Agent information  
            system (str): System name (MainPC or PC2)
            
        Returns:
            dict: Resource impact evaluation
        """
        agent_name = agent['name'].lower()
        hardware = self.hardware_profiles[system]
        
        # GPU-intensive agents (AI models, vision processing)
        if any(keyword in agent_name for keyword in ['model', 'vision', 'face', 'gpu', 'vram']):
            if system == 'MainPC':
                impact_score = self.evaluation_criteria['resource_impact']['gpu_intensive']
                impact_level = 'gpu_intensive'
                reasoning = f'GPU processing on {hardware["gpu"]} with {hardware["gpu_memory"]//1024}GB VRAM'
            else:
                impact_score = self.evaluation_criteria['resource_impact']['gpu_intensive'] * 0.7
                impact_level = 'gpu_intensive_limited' 
                reasoning = f'GPU processing on {hardware["gpu"]} with limited VRAM'
                
        # Memory-heavy agents (knowledge, cache, memory services)
        elif any(keyword in agent_name for keyword in ['memory', 'knowledge', 'cache']):
            impact_score = self.evaluation_criteria['resource_impact']['memory_heavy']
            impact_level = 'memory_heavy'
            reasoning = f'Memory operations on {hardware["ram"]//1024}GB RAM'
            
        # CPU-intensive agents (processing, reasoning, learning)
        elif any(keyword in agent_name for keyword in ['processor', 'reasoning', 'learning', 'training']):
            impact_score = self.evaluation_criteria['resource_impact']['cpu_intensive']
            impact_level = 'cpu_intensive' 
            reasoning = f'CPU processing on {hardware["cpu"]} ({hardware["cpu_cores"]} cores)'
            
        # Network-heavy agents (communication, streaming, coordination)
        elif any(keyword in agent_name for keyword in ['coordinator', 'streaming', 'network', 'service']):
            impact_score = self.evaluation_criteria['resource_impact']['network_heavy']
            impact_level = 'network_heavy'
            reasoning = 'Network I/O operations and communication'
            
        # I/O-bound agents (storage, file operations)
        else:
            impact_score = self.evaluation_criteria['resource_impact']['io_bound']
            impact_level = 'io_bound'
            reasoning = 'Standard I/O and processing operations'

        return {
            'resource_score': impact_score,
            'impact_level': impact_level,
            'reasoning': reasoning,
            'hardware_match': self._evaluate_hardware_match(agent, system)
        }

    def _evaluate_hardware_match(self, agent, system):
        """Evaluate how well agent matches system hardware capabilities"""
        agent_name = agent['name'].lower()
        hardware = self.hardware_profiles[system]
        
        if system == 'MainPC':
            # RTX 4090 optimized for AI processing
            if any(keyword in agent_name for keyword in ['model', 'ai', 'reasoning', 'llm']):
                return 'optimal'
            elif any(keyword in agent_name for keyword in ['audio', 'speech', 'processing']):
                return 'good' 
            else:
                return 'acceptable'
        else:  # PC2
            # RTX 3060 optimized for memory/cache operations
            if any(keyword in agent_name for keyword in ['memory', 'cache', 'storage']):
                return 'optimal'
            elif any(keyword in agent_name for keyword in ['vision', 'processing']):
                return 'limited'
            else:
                return 'acceptable'

    def evaluate_dependency_criticality(self, agent, all_agents):
        """
        Evaluate criticality based on dependency relationships
        
        Args:
            agent (dict): Agent information
            all_agents (list): List of all agents for dependency analysis
            
        Returns:
            dict: Dependency criticality evaluation
        """
        agent_name = agent['name']
        
        # Count how many other agents depend on this agent
        dependent_count = 0
        for other_agent in all_agents:
            if agent_name in other_agent.get('dependencies', []):
                dependent_count += 1
        
        # Foundation services with no dependencies but many dependents
        if len(agent.get('dependencies', [])) == 0 and dependent_count > 10:
            criticality_score = self.evaluation_criteria['dependency_criticality']['foundation']
            criticality_level = 'foundation'
            reasoning = f'Foundation service with {dependent_count} dependents'
            
        # Critical path services (high dependent count)
        elif dependent_count >= 5:
            criticality_score = self.evaluation_criteria['dependency_criticality']['critical_path']
            criticality_level = 'critical_path'
            reasoning = f'Critical path service with {dependent_count} dependents'
            
        # Shared services (moderate dependent count)  
        elif dependent_count >= 2:
            criticality_score = self.evaluation_criteria['dependency_criticality']['shared_service']
            criticality_level = 'shared_service'
            reasoning = f'Shared service with {dependent_count} dependents'
            
        # Specialized services (few dependents but specific function)
        elif dependent_count == 1 or len(agent.get('dependencies', [])) > 3:
            criticality_score = self.evaluation_criteria['dependency_criticality']['specialized']
            criticality_level = 'specialized'
            reasoning = f'Specialized service in dependency chain'
            
        # Optional services
        else:
            criticality_score = self.evaluation_criteria['dependency_criticality']['optional']
            criticality_level = 'optional'
            reasoning = 'Optional or leaf service'

        return {
            'criticality_score': criticality_score,
            'criticality_level': criticality_level,
            'reasoning': reasoning,
            'dependent_count': dependent_count,
            'dependency_count': len(agent.get('dependencies', []))
        }

    def calculate_overall_score(self, evaluations):
        """Calculate weighted overall score for agent worthiness"""
        weights = {
            'usage_score': 0.35,           # 35% - How often used
            'resource_score': 0.25,       # 25% - Resource efficiency  
            'criticality_score': 0.30,    # 30% - System criticality
            'performance_score': 0.10     # 10% - Performance requirements
        }
        
        overall_score = (
            evaluations['usage']['usage_score'] * weights['usage_score'] +
            evaluations['resource']['resource_score'] * weights['resource_score'] + 
            evaluations['criticality']['criticality_score'] * weights['criticality_score'] +
            0.6 * weights['performance_score']  # Default performance score
        )
        
        # Determine overall rating
        if overall_score >= 0.8:
            rating = 'CRITICAL'
        elif overall_score >= 0.6:
            rating = 'HIGH_VALUE' 
        elif overall_score >= 0.4:
            rating = 'MODERATE_VALUE'
        elif overall_score >= 0.2:
            rating = 'LOW_VALUE'
        else:
            rating = 'CANDIDATE_FOR_REMOVAL'

        return {
            'overall_score': overall_score,
            'rating': rating,
            'recommendation': self._get_recommendation(overall_score, evaluations)
        }

    def _get_recommendation(self, score, evaluations):
        """Generate optimization recommendation based on score and evaluations"""
        if score >= 0.8:
            return 'KEEP - Critical system component'
        elif score >= 0.6:
            return 'KEEP - High value service'
        elif score >= 0.4:
            if evaluations['resource']['hardware_match'] == 'limited':
                return 'CONSIDER_RELOCATION - Move to more suitable hardware'
            else:
                return 'KEEP - Moderate value, optimize if possible'
        elif score >= 0.2:
            return 'OPTIMIZE - Low efficiency, consider consolidation'
        else:
            return 'REMOVE - Candidate for removal or major consolidation'

    def run_full_evaluation(self, agent_data_path):
        """
        Run complete evaluation on all agents
        
        Args:
            agent_data_path (str): Path to Phase 1 agent data JSON
            
        Returns:
            dict: Complete evaluation results
        """
        print("🔍 Starting Phase 2: Agent Evaluation & Resource Analysis...")
        print("=" * 60)
        
        # Load agent data
        agent_data = self.load_agent_data(agent_data_path)
        
        results = {
            'mainpc_evaluations': [],
            'pc2_evaluations': [],
            'summary_stats': {},
            'optimization_recommendations': []
        }
        
        # Evaluate MainPC agents
        print("📊 Evaluating MainPC agents...")
        mainpc_agents = agent_data['mainpc']['agents_info']['agents_list']
        all_agents = mainpc_agents + agent_data['pc2']['agents_info']['agents_list']
        
        for agent in mainpc_agents:
            evaluation = {
                'agent': agent,
                'system': 'MainPC',
                'usage': self.evaluate_agent_usage(agent),
                'resource': self.evaluate_resource_impact(agent, 'MainPC'),
                'criticality': self.evaluate_dependency_criticality(agent, all_agents)
            }
            evaluation['overall'] = self.calculate_overall_score(evaluation)
            results['mainpc_evaluations'].append(evaluation)
        
        # Evaluate PC2 agents  
        print("📊 Evaluating PC2 agents...")
        pc2_agents = agent_data['pc2']['agents_info']['agents_list']
        
        for agent in pc2_agents:
            evaluation = {
                'agent': agent,
                'system': 'PC2', 
                'usage': self.evaluate_agent_usage(agent),
                'resource': self.evaluate_resource_impact(agent, 'PC2'),
                'criticality': self.evaluate_dependency_criticality(agent, all_agents)
            }
            evaluation['overall'] = self.calculate_overall_score(evaluation)
            results['pc2_evaluations'].append(evaluation)
        
        # Generate summary statistics
        results['summary_stats'] = self._generate_summary_stats(results)
        results['optimization_recommendations'] = self._generate_optimization_recommendations(results)
        
        return results

    def _generate_summary_stats(self, results):
        """Generate summary statistics from evaluation results"""
        all_evaluations = results['mainpc_evaluations'] + results['pc2_evaluations']
        
        # Count by rating
        rating_counts = defaultdict(int)
        for eval in all_evaluations:
            rating_counts[eval['overall']['rating']] += 1
        
        # Resource distribution
        resource_distribution = defaultdict(int)
        for eval in all_evaluations:
            resource_distribution[eval['resource']['impact_level']] += 1
            
        return {
            'total_agents': len(all_evaluations),
            'mainpc_agents': len(results['mainpc_evaluations']),
            'pc2_agents': len(results['pc2_evaluations']),
            'rating_distribution': dict(rating_counts),
            'resource_distribution': dict(resource_distribution),
            'avg_scores': {
                'overall': sum(e['overall']['overall_score'] for e in all_evaluations) / len(all_evaluations),
                'usage': sum(e['usage']['usage_score'] for e in all_evaluations) / len(all_evaluations),
                'resource': sum(e['resource']['resource_score'] for e in all_evaluations) / len(all_evaluations),
                'criticality': sum(e['criticality']['criticality_score'] for e in all_evaluations) / len(all_evaluations)
            }
        }

    def _generate_optimization_recommendations(self, results):
        """Generate system-wide optimization recommendations"""
        recommendations = []
        
        # Find removal candidates
        removal_candidates = []
        for eval in results['mainpc_evaluations'] + results['pc2_evaluations']:
            if eval['overall']['rating'] == 'CANDIDATE_FOR_REMOVAL':
                removal_candidates.append(eval['agent']['name'])
        
        if removal_candidates:
            recommendations.append({
                'type': 'REMOVAL',
                'title': 'Agent Removal Candidates', 
                'agents': removal_candidates,
                'impact': f'Potential removal of {len(removal_candidates)} agents'
            })
        
        # Find relocation candidates
        relocation_candidates = []
        for eval in results['mainpc_evaluations'] + results['pc2_evaluations']:
            if 'RELOCATION' in eval['overall']['recommendation']:
                relocation_candidates.append({
                    'agent': eval['agent']['name'],
                    'from': eval['system'],
                    'reason': eval['resource']['reasoning']
                })
        
        if relocation_candidates:
            recommendations.append({
                'type': 'RELOCATION',
                'title': 'Agent Relocation Candidates',
                'candidates': relocation_candidates,
                'impact': f'Optimize {len(relocation_candidates)} agents through relocation'
            })
        
        return recommendations

def main():
    """Main execution function"""
    evaluator = AgentEvaluationFramework()
    
    # Run evaluation
    agent_data_path = "/home/haymayndz/AI_System_Monorepo/agent_audit_phase1_results.json"
    results = evaluator.run_full_evaluation(agent_data_path)
    
    # Save results
    output_path = "/home/haymayndz/AI_System_Monorepo/phase2_evaluation_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Evaluation results saved to: {output_path}")
    
    # Print summary
    stats = results['summary_stats']
    print(f"\n📊 EVALUATION SUMMARY:")
    print(f"Total Agents: {stats['total_agents']}")
    print(f"Average Overall Score: {stats['avg_scores']['overall']:.3f}")
    print(f"Rating Distribution: {stats['rating_distribution']}")
    
    print("\n🎯 Phase 2 Evaluation Complete!")
    
    return results

if __name__ == "__main__":
    main()
