#!/usr/bin/env python3
"""
🚀 CONSOLIDATION PROPOSAL GENERATOR
Automated tool para sa paggawa ng system consolidation proposals
Based on the methodology used in 4_proposal.md
"""

import yaml
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set

class ConsolidationProposalGenerator:
    def __init__(self):
        self.agents = []
        self.dependency_graph = defaultdict(list)
        self.fan_out_counts = Counter()
        self.logical_domains = {
            'Core Orchestration': ['ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator', 'UnifiedSystemAgent'],
            'Memory & Knowledge': ['MemoryClient', 'KnowledgeBase', 'MemoryOrchestratorService', 'CacheManager', 'ContextManager'],
            'Model Lifecycle': ['GGUFModelManager', 'ModelManagerAgent', 'PredictiveLoader', 'ModelEvaluationFramework'],
            'Learning & Adaptation': ['SelfTrainingOrchestrator', 'LocalFineTunerAgent', 'LearningManager', 'ActiveLearningMonitor'],
            'Reasoning & Dialogue': ['ChainOfThoughtAgent', 'CognitiveModelAgent', 'NLUAgent', 'AdvancedCommandHandler'],
            'Speech & Audio': ['STTService', 'StreamingSpeechRecognition', 'StreamingTTSAgent', 'AudioCapture'],
            'Vision': ['FaceRecognitionAgent', 'VisionProcessingAgent'],
            'Emotion & Social': ['EmotionEngine', 'MoodTrackerAgent', 'HumanAwarenessAgent', 'EmpathyAgent'],
            'Infrastructure': ['PerformanceMonitor', 'HealthMonitor', 'ResourceManager', 'SystemHealthManager'],
            'Utilities': ['CodeGenerator', 'Executor', 'TinyLlamaServiceEnhanced', 'NLLBAdapter'],
            'Web & External': ['RemoteConnectorAgent', 'AdvancedRouter', 'UnifiedWebAgent', 'NetGateway']
        }
    
    def load_config_file(self, config_path: str, machine_name: str) -> None:
        """Load at mag-parse ng YAML configuration file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            print(f"📁 Loading config from {machine_name}: {config_path}")
            
            if 'agent_groups' in config:
                for group_name, group_config in config['agent_groups'].items():
                    if isinstance(group_config, dict):
                        for agent_name, agent_config in group_config.items():
                            if isinstance(agent_config, dict):
                                agent_info = {
                                    'name': agent_name,
                                    'port': agent_config.get('port', 'N/A'),
                                    'health_port': agent_config.get('health_port', 'N/A'),
                                    'required': agent_config.get('required', False),
                                    'dependencies': agent_config.get('depends_on', []),
                                    'machine': machine_name,
                                    'group': group_name
                                }
                                self.agents.append(agent_info)
                                
                                # Build dependency graph
                                for dep in agent_info['dependencies']:
                                    self.dependency_graph[dep].append(agent_name)
                                    self.fan_out_counts[dep] += 1
                                    
        except Exception as e:
            print(f"❌ Error loading {config_path}: {e}")
    
    def analyze_dependencies(self) -> Dict:
        """Analyze dependency patterns and identify high-fan-out services"""
        analysis = {
            'high_fan_out_hubs': [],
            'isolated_agents': [],
            'dependency_chains': [],
            'cross_machine_dependencies': []
        }
        
        # High fan-out hubs (services with many dependents)
        for service, count in self.fan_out_counts.most_common(10):
            analysis['high_fan_out_hubs'].append({
                'service': service,
                'dependent_count': count,
                'dependents': self.dependency_graph[service]
            })
        
        # Isolated agents (no dependencies)
        agent_names = {agent['name'] for agent in self.agents}
        for agent in self.agents:
            if not agent['dependencies'] and agent['name'] not in self.fan_out_counts:
                analysis['isolated_agents'].append(agent['name'])
        
        # Cross-machine dependencies
        for agent in self.agents:
            for dep in agent['dependencies']:
                dep_agent = next((a for a in self.agents if a['name'] == dep), None)
                if dep_agent and dep_agent['machine'] != agent['machine']:
                    analysis['cross_machine_dependencies'].append({
                        'from': f"{agent['name']} ({agent['machine']})",
                        'to': f"{dep} ({dep_agent['machine']})"
                    })
        
        return analysis
    
    def categorize_by_domain(self) -> Dict:
        """Categorize agents by logical domain"""
        categorized = defaultdict(list)
        uncategorized = []
        
        for agent in self.agents:
            categorized_flag = False
            for domain, domain_agents in self.logical_domains.items():
                if any(pattern in agent['name'] for pattern in domain_agents):
                    categorized[domain].append(agent)
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                uncategorized.append(agent)
        
        return dict(categorized), uncategorized
    
    def generate_consolidation_groups(self) -> List[Dict]:
        """Generate consolidation groupings based on domain and hardware requirements"""
        categorized, uncategorized = self.categorize_by_domain()
        consolidation_groups = []
        
        # GPU-heavy groups (MainPC)
        gpu_domains = ['Model Lifecycle', 'Reasoning & Dialogue', 'Speech & Audio', 'Vision', 'Learning & Adaptation']
        
        # CPU-heavy groups (PC2)  
        cpu_domains = ['Memory & Knowledge', 'Infrastructure', 'Web & External']
        
        # Mixed groups
        mixed_domains = ['Core Orchestration', 'Emotion & Social', 'Utilities']
        
        group_id = 1
        base_port = 7000
        
        for domain, agents in categorized.items():
            if not agents:
                continue
                
            hardware = 'MainPC' if domain in gpu_domains else 'PC2'
            if domain in mixed_domains:
                # Decide based on majority of current agents
                mainpc_count = sum(1 for a in agents if a['machine'] == 'MainPC')
                hardware = 'MainPC' if mainpc_count >= len(agents) / 2 else 'PC2'
            
            port = base_port if hardware == 'MainPC' else 9000
            base_port += 1
            
            group = {
                'id': group_id,
                'name': f"{domain.replace(' ', '')}Suite",
                'domain': domain,
                'source_agents': [a['name'] for a in agents],
                'agent_count': len(agents),
                'target_port': port,
                'health_port': port + 100,
                'hardware': hardware,
                'integration_complexity': self._assess_integration_complexity(agents),
                'dependencies': list(set(dep for agent in agents for dep in agent['dependencies']))
            }
            
            consolidation_groups.append(group)
            group_id += 1
        
        return consolidation_groups
    
    def _assess_integration_complexity(self, agents: List[Dict]) -> str:
        """Assess integration complexity based on dependency patterns"""
        total_deps = sum(len(agent['dependencies']) for agent in agents)
        avg_deps = total_deps / len(agents) if agents else 0
        
        if avg_deps > 3:
            return 'HIGH'
        elif avg_deps > 1.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def generate_risk_assessment(self, consolidation_groups: List[Dict]) -> List[Dict]:
        """Generate risk assessment for consolidation plan"""
        risks = []
        
        # Large service risk
        large_groups = [g for g in consolidation_groups if g['agent_count'] > 8]
        if large_groups:
            risks.append({
                'area': 'Large Unified Services',
                'risk': 'Deployment size increase, harder to debug',
                'mitigation': 'Docker multi-stage builds, modular architecture',
                'affected_groups': [g['name'] for g in large_groups]
            })
        
        # GPU over-commitment risk
        gpu_groups = [g for g in consolidation_groups if g['hardware'] == 'MainPC']
        if len(gpu_groups) > 6:
            risks.append({
                'area': 'GPU Over-commitment',
                'risk': 'VRAM exhaustion on RTX 4090',
                'mitigation': 'Resource quotas, GPU memory pools',
                'affected_groups': [g['name'] for g in gpu_groups]
            })
        
        # Cross-machine communication
        cross_deps = sum(1 for g in consolidation_groups if 
                        any(dep not in [gg['name'] for gg in consolidation_groups if gg['hardware'] == g['hardware']] 
                            for dep in g['dependencies']))
        if cross_deps > 0:
            risks.append({
                'area': 'Cross-machine Latency',
                'risk': 'Increased network latency between MainPC and PC2',
                'mitigation': 'gRPC connection pooling, compression',
                'affected_groups': 'Multiple'
            })
        
        return risks
    
    def generate_proposal_report(self) -> str:
        """Generate complete consolidation proposal report"""
        analysis = self.analyze_dependencies()
        consolidation_groups = self.generate_consolidation_groups()
        risks = self.generate_risk_assessment(consolidation_groups)
        
        total_agents = len(self.agents)
        target_services = len(consolidation_groups)
        reduction_percentage = round((1 - target_services / total_agents) * 100, 1)
        
        report = f"""
# 🚀 AUTOMATED CONSOLIDATION PROPOSAL

## Executive Summary
- **Current State**: {total_agents} individual agents
- **Target State**: {target_services} consolidated services  
- **Reduction**: {reduction_percentage}% consolidation ratio
- **Generated**: {self.__class__.__name__}

## 1️⃣ CURRENT SYSTEM INVENTORY

### Agent Distribution by Machine
"""
        
        # Agent distribution
        mainpc_agents = [a for a in self.agents if a['machine'] == 'MainPC']
        pc2_agents = [a for a in self.agents if a['machine'] == 'PC2']
        
        report += f"- **MainPC (RTX 4090)**: {len(mainpc_agents)} agents\n"
        report += f"- **PC2 (RTX 3060)**: {len(pc2_agents)} agents\n\n"
        
        # High fan-out services
        report += "### High Fan-Out Hub Services\n"
        for hub in analysis['high_fan_out_hubs'][:5]:
            report += f"- **{hub['service']}**: {hub['dependent_count']} dependents\n"
        
        report += "\n## 2️⃣ CONSOLIDATION PLAN\n\n"
        
        # Consolidation groups
        for group in consolidation_groups:
            report += f"### {group['name']}\n"
            report += f"- **Domain**: {group['domain']}\n"
            report += f"- **Source Agents**: {group['agent_count']} agents\n"
            report += f"- **Port**: {group['target_port']} (Health: {group['health_port']})\n"
            report += f"- **Hardware**: {group['hardware']}\n"
            report += f"- **Complexity**: {group['integration_complexity']}\n"
            report += f"- **Agents**: {', '.join(group['source_agents'][:5])}{'...' if len(group['source_agents']) > 5 else ''}\n\n"
        
        # Port allocation
        report += "## 3️⃣ PORT ALLOCATION\n\n"
        report += "| Service | Port | Health | Hardware |\n"
        report += "|---------|------|--------|---------|\n"
        
        for group in sorted(consolidation_groups, key=lambda x: x['target_port']):
            report += f"| {group['name']} | {group['target_port']} | {group['health_port']} | {group['hardware']} |\n"
        
        # Risk assessment
        report += "\n## 4️⃣ RISK ASSESSMENT\n\n"
        for risk in risks:
            report += f"### {risk['area']}\n"
            report += f"- **Risk**: {risk['risk']}\n"
            report += f"- **Mitigation**: {risk['mitigation']}\n\n"
        
        # Implementation phases
        report += "## 5️⃣ IMPLEMENTATION PHASES\n\n"
        phases = [
            ("Phase 1: Core Infrastructure", [g for g in consolidation_groups if 'Core' in g['domain'] or 'Infrastructure' in g['domain']]),
            ("Phase 2: Data & Memory Layer", [g for g in consolidation_groups if 'Memory' in g['domain'] or 'Knowledge' in g['domain']]),
            ("Phase 3: Intelligence Services", [g for g in consolidation_groups if any(kw in g['domain'] for kw in ['Reasoning', 'Learning', 'Model'])])
        ]
        
        for phase_name, phase_groups in phases:
            if phase_groups:
                report += f"### {phase_name}\n"
                for group in phase_groups:
                    report += f"- {group['name']} ({group['agent_count']} agents → 1 service)\n"
                report += "\n"
        
        return report

def main():
    """Main function para sa command line usage"""
    generator = ConsolidationProposalGenerator()
    
    # Load configuration files
    config_files = [
        ('main_pc_code/config/startup_config.yaml', 'MainPC'),
        ('pc2_code/config/startup_config.yaml', 'PC2')
    ]
    
    for config_path, machine_name in config_files:
        if Path(config_path).exists():
            generator.load_config_file(config_path, machine_name)
        else:
            print(f"⚠️  Config file not found: {config_path}")
    
    if not generator.agents:
        print("❌ No agents loaded. Check config file paths.")
        return
    
    print(f"✅ Loaded {len(generator.agents)} agents from configuration files")
    
    # Generate and save report
    report = generator.generate_proposal_report()
    
    output_file = 'generated_consolidation_proposal.md'
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"📄 Consolidation proposal saved to: {output_file}")
    print("\n🎯 Key Metrics:")
    print(f"   - Total Agents: {len(generator.agents)}")
    print(f"   - Proposed Services: {len(generator.generate_consolidation_groups())}")
    print(f"   - Cross-machine Dependencies: {len(generator.analyze_dependencies()['cross_machine_dependencies'])}")

if __name__ == "__main__":
    main() 