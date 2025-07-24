#!/usr/bin/env python3
"""
Port Linter and Audit Tool for AI Agent System.

This script analyzes port usage across MainPC and PC2 configurations
to detect conflicts, gaps, and optimization opportunities.
"""

import sys
import yaml
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager


class PortAuditor:
    """Comprehensive port usage analyzer."""
    
    def __init__(self):
        self.project_root = Path(PathManager.get_project_root())
        self.port_allocations = defaultdict(list)  # port -> [(agent_name, system, port_type)]
        self.port_ranges = {
            'mainpc_primary': (5600, 5699),
            'mainpc_secondary': (5700, 5799), 
            'mainpc_tertiary': (7200, 7299),
            'pc2_primary': (7100, 7199),
            'system_reserved': (1, 1023),
            'ephemeral': (32768, 65535)
        }
    
    def load_config(self, config_path: Path) -> Dict:
        """Load YAML configuration file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading {config_path}: {e}")
            return {}
    
    def extract_ports_mainpc(self, config: Dict) -> List[Tuple[str, int, int, str]]:
        """
        Extract port information from MainPC hierarchical config.
        Returns: List of (agent_name, main_port, health_port, group)
        """
        ports = []
        agent_groups = config.get('agent_groups', {})
        
        for group_name, group_agents in agent_groups.items():
            for agent_name, agent_config in group_agents.items():
                main_port = agent_config.get('port')
                health_port = agent_config.get('health_check_port')
                
                if main_port:
                    ports.append((agent_name, main_port, health_port or 0, group_name))
        
        return ports
    
    def extract_ports_pc2(self, config: Dict) -> List[Tuple[str, int, int, str]]:
        """
        Extract port information from PC2 flat list config.
        Returns: List of (agent_name, main_port, health_port, service_type)
        """
        ports = []
        pc2_services = config.get('pc2_services', [])
        
        for service in pc2_services:
            agent_name = service.get('name', 'unknown')
            main_port = service.get('port')
            health_port = service.get('health_check_port')
            
            if main_port:
                ports.append((agent_name, main_port, health_port or 0, 'pc2_service'))
        
        return ports
    
    def audit_system_ports(self, system_name: str, config_path: Path) -> Dict:
        """Audit ports for a specific system (MainPC or PC2)."""
        print(f"\n🔍 Auditing {system_name} ports: {config_path}")
        
        if not config_path.exists():
            print(f"⚠️  Config file not found: {config_path}")
            return {}
        
        config = self.load_config(config_path)
        if not config:
            return {}
        
        # Extract ports based on system type
        if system_name.lower() == 'mainpc':
            port_info = self.extract_ports_mainpc(config)
        else:
            port_info = self.extract_ports_pc2(config)
        
        # Analyze port usage
        main_ports = []
        health_ports = []
        port_conflicts = []
        range_usage = defaultdict(int)
        
        for agent_name, main_port, health_port, group in port_info:
            # Track main ports
            if main_port:
                main_ports.append((agent_name, main_port, group))
                self.port_allocations[main_port].append((agent_name, system_name, 'main'))
                
                # Categorize by range
                for range_name, (start, end) in self.port_ranges.items():
                    if start <= main_port <= end:
                        range_usage[range_name] += 1
                        break
                else:
                    range_usage['unclassified'] += 1
            
            # Track health check ports
            if health_port and health_port != 0:
                health_ports.append((agent_name, health_port, group))
                self.port_allocations[health_port].append((agent_name, system_name, 'health'))
        
        # Find conflicts within this system
        port_counter = Counter([port for _, port, _ in main_ports])
        port_counter.update([port for _, port, _ in health_ports])
        
        for port, count in port_counter.items():
            if count > 1:
                agents = [name for name, p, _ in main_ports + health_ports if p == port]
                port_conflicts.append((port, agents))
        
        return {
            'system': system_name,
            'total_agents': len(port_info),
            'main_ports': main_ports,
            'health_ports': health_ports,
            'port_conflicts': port_conflicts,
            'range_usage': dict(range_usage),
            'port_count': len(main_ports) + len(health_ports)
        }
    
    def find_cross_system_conflicts(self, mainpc_audit: Dict, pc2_audit: Dict) -> List[Tuple[int, List[str]]]:
        """Find port conflicts between MainPC and PC2 systems."""
        conflicts = []
        
        for port, allocations in self.port_allocations.items():
            if len(allocations) > 1:
                systems = set(alloc[1] for alloc in allocations)
                if len(systems) > 1:  # Conflict across systems
                    agent_info = [f"{alloc[0]} ({alloc[1]}:{alloc[2]})" for alloc in allocations]
                    conflicts.append((port, agent_info))
        
        return conflicts
    
    def analyze_port_ranges(self, mainpc_audit: Dict, pc2_audit: Dict) -> Dict:
        """Analyze port range utilization and suggest optimizations."""
        analysis = {}
        
        for range_name, (start, end) in self.port_ranges.items():
            total_ports = end - start + 1
            used_ports = 0
            
            # Count usage from both systems
            for system_audit in [mainpc_audit, pc2_audit]:
                used_ports += system_audit.get('range_usage', {}).get(range_name, 0)
            
            utilization = (used_ports / total_ports) * 100 if total_ports > 0 else 0
            
            analysis[range_name] = {
                'range': f"{start}-{end}",
                'total_ports': total_ports,
                'used_ports': used_ports,
                'utilization': utilization,
                'available_ports': total_ports - used_ports
            }
        
        return analysis
    
    def generate_recommendations(self, mainpc_audit: Dict, pc2_audit: Dict, 
                               cross_conflicts: List, range_analysis: Dict) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Check for conflicts
        if cross_conflicts:
            recommendations.append("🚨 CRITICAL: Cross-system port conflicts detected!")
            for port, agents in cross_conflicts:
                recommendations.append(f"  Port {port}: {', '.join(agents)}")
        
        # Check range utilization
        for range_name, info in range_analysis.items():
            if info['utilization'] > 80:
                recommendations.append(f"⚠️  {range_name} range is {info['utilization']:.1f}% full")
            elif info['utilization'] < 10 and info['used_ports'] > 0:
                recommendations.append(f"💡 {range_name} range is underutilized ({info['utilization']:.1f}%)")
        
        # Check for scattered ports
        mainpc_ranges = set()
        for range_name, usage in mainpc_audit.get('range_usage', {}).items():
            if usage > 0:
                mainpc_ranges.add(range_name)
        
        if len(mainpc_ranges) > 2:
            recommendations.append("💡 MainPC ports are scattered across multiple ranges - consider consolidation")
        
        # Check for proper separation
        pc2_in_mainpc_ranges = pc2_audit.get('range_usage', {}).get('mainpc_primary', 0)
        if pc2_in_mainpc_ranges > 0:
            recommendations.append("⚠️  PC2 agents using MainPC port ranges - check separation")
        
        if not recommendations:
            recommendations.append("✅ No major port allocation issues detected")
        
        return recommendations
    
    def print_detailed_report(self, mainpc_audit: Dict, pc2_audit: Dict, 
                            cross_conflicts: List, range_analysis: Dict) -> None:
        """Print comprehensive port audit report."""
        print(f"\n" + "="*60)
        print(f"🔍 COMPREHENSIVE PORT AUDIT REPORT")
        print(f"="*60)
        
        # System summaries
        for audit in [mainpc_audit, pc2_audit]:
            if audit:
                system = audit['system']
                print(f"\n📊 {system.upper()} SYSTEM:")
                print(f"  Agents: {audit['total_agents']}")
                print(f"  Total ports used: {audit['port_count']}")
                
                if audit['port_conflicts']:
                    print(f"  ❌ Internal conflicts: {len(audit['port_conflicts'])}")
                    for port, agents in audit['port_conflicts']:
                        print(f"    Port {port}: {', '.join(agents)}")
                else:
                    print(f"  ✅ No internal conflicts")
        
        # Cross-system conflicts
        print(f"\n🔀 CROSS-SYSTEM ANALYSIS:")
        if cross_conflicts:
            print(f"  ❌ Cross-system conflicts: {len(cross_conflicts)}")
            for port, agents in cross_conflicts:
                print(f"    Port {port}: {', '.join(agents)}")
        else:
            print(f"  ✅ No cross-system conflicts")
        
        # Range analysis
        print(f"\n📈 PORT RANGE UTILIZATION:")
        for range_name, info in range_analysis.items():
            status = "🔴" if info['utilization'] > 80 else "🟡" if info['utilization'] > 50 else "🟢"
            print(f"  {status} {range_name}: {info['used_ports']}/{info['total_ports']} "
                  f"({info['utilization']:.1f}%) - Range {info['range']}")
        
        # Recommendations
        recommendations = self.generate_recommendations(mainpc_audit, pc2_audit, cross_conflicts, range_analysis)
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"  {rec}")
        
        print(f"\n" + "="*60)


def main():
    """Main port audit function."""
    parser = argparse.ArgumentParser(
        description="Port allocation auditor for AI agent systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run full audit
  %(prog)s --fail-on-conflict       # Exit with error code if conflicts found
  %(prog)s --json                   # Output results in JSON format
  %(prog)s --range-only             # Show only range utilization
        """
    )
    
    parser.add_argument(
        '--fail-on-conflict',
        action='store_true',
        help='Exit with error code if port conflicts are detected'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    parser.add_argument(
        '--range-only',
        action='store_true',
        help='Show only port range utilization'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Initialize auditor
    auditor = PortAuditor()
    project_root = Path(auditor.project_root)
    
    # Audit both systems
    mainpc_config = project_root / "main_pc_code" / "config" / "startup_config.yaml"
    pc2_config = project_root / "pc2_code" / "config" / "startup_config.yaml"
    
    mainpc_audit = auditor.audit_system_ports("MainPC", mainpc_config)
    pc2_audit = auditor.audit_system_ports("PC2", pc2_config)
    
    # Analyze cross-system conflicts
    cross_conflicts = auditor.find_cross_system_conflicts(mainpc_audit, pc2_audit)
    
    # Analyze port ranges
    range_analysis = auditor.analyze_port_ranges(mainpc_audit, pc2_audit)
    
    if args.json:
        import json
        result = {
            'mainpc': mainpc_audit,
            'pc2': pc2_audit,
            'cross_conflicts': cross_conflicts,
            'range_analysis': range_analysis,
            'recommendations': auditor.generate_recommendations(
                mainpc_audit, pc2_audit, cross_conflicts, range_analysis
            )
        }
        print(json.dumps(result, indent=2))
    elif args.range_only:
        print("\n📈 PORT RANGE UTILIZATION:")
        for range_name, info in range_analysis.items():
            status = "🔴" if info['utilization'] > 80 else "🟡" if info['utilization'] > 50 else "🟢"
            print(f"  {status} {range_name}: {info['used_ports']}/{info['total_ports']} "
                  f"({info['utilization']:.1f}%) - Range {info['range']}")
    else:
        auditor.print_detailed_report(mainpc_audit, pc2_audit, cross_conflicts, range_analysis)
    
    # Handle fail-on-conflict option
    if args.fail_on_conflict:
        total_conflicts = len(cross_conflicts)
        if mainpc_audit.get('port_conflicts'):
            total_conflicts += len(mainpc_audit['port_conflicts'])
        if pc2_audit.get('port_conflicts'):
            total_conflicts += len(pc2_audit['port_conflicts'])
        
        if total_conflicts > 0:
            print(f"\n❌ CONFLICT DETECTED: {total_conflicts} port conflicts found")
            sys.exit(1)
        else:
            print(f"\n✅ NO CONFLICTS: Port allocation is clean")
            sys.exit(0)


if __name__ == "__main__":
    main() 