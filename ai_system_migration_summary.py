#!/usr/bin/env python3
"""
AI System Migration Summary - Comprehensive analysis and recommendations
Combines all validation results and provides actionable migration guidance
"""
import json, pathlib
from datetime import datetime

def load_analysis_files():
    """Load all analysis files"""
    files = {
        'agent_analysis': 'agent_analysis_results.json',
        'docker_groups': 'docker_groups_analysis.json', 
        'migration_validation': 'migration_validation_report.json'
    }
    
    data = {}
    for name, filename in files.items():
        try:
            with open(filename, 'r') as f:
                data[name] = json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Warning: {filename} not found")
            data[name] = {}
    
    return data

def generate_migration_summary():
    """Generate comprehensive migration summary"""
    data = load_analysis_files()
    
    print("=" * 100)
    print("🤖 AI SYSTEM MIGRATION ANALYSIS & RECOMMENDATIONS")
    print("=" * 100)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # System Overview
    print("\n📊 SYSTEM OVERVIEW:")
    if 'agent_analysis' in data and 'stats' in data['agent_analysis']:
        stats = data['agent_analysis']['stats']
        print(f"   Total Agents: {stats.get('total_agents', 'N/A')}")
        print(f"   MainPC Agents: {stats.get('main_pc_agents', 'N/A')}")
        print(f"   PC2 Agents: {stats.get('pc2_agents', 'N/A')}")
    
    # Docker Groups Validation
    print("\n🐳 DOCKER GROUPS VALIDATION:")
    if 'docker_groups' in data and 'validation' in data['docker_groups']:
        for config_file, validation in data['docker_groups']['validation'].items():
            system = validation.get('system', 'Unknown')
            coverage = validation.get('coverage_percentage', 0)
            print(f"   {system}: {coverage:.1f}% coverage")
            
            if validation.get('missing_agents'):
                print(f"      Missing: {', '.join(validation['missing_agents'])}")
    
    # Repository Structure Status
    print("\n📁 REPOSITORY STRUCTURE:")
    if 'migration_validation' in data and 'repository_structure' in data['migration_validation']:
        structure = data['migration_validation']['repository_structure']
        all_exist = all(info['status'] == '✅ EXISTS' for info in structure.values())
        print(f"   Status: {'✅ COMPLETE' if all_exist else '❌ INCOMPLETE'}")
        
        for dir_name, info in structure.items():
            print(f"      {dir_name}: {info['status']}")
    
    # Agent Script Paths
    print("\n🤖 AGENT SCRIPT PATHS:")
    if 'migration_validation' in data and 'agent_paths' in data['migration_validation']:
        paths = data['migration_validation']['agent_paths']
        for system, info in paths.items():
            total = info.get('total_agents', 0)
            valid = info.get('valid_paths', 0)
            missing = info.get('missing_paths', 0)
            print(f"   {system}: {valid}/{total} valid paths")
            if missing > 0:
                print(f"      Missing: {missing} agents")
    
    # Critical Issues
    print("\n⚠️  CRITICAL ISSUES TO ADDRESS:")
    if 'migration_validation' in data and 'potential_issues' in data['migration_validation']:
        issues = data['migration_validation']['potential_issues']
        if issues:
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        else:
            print("   ✅ No critical issues detected!")
    
    # Migration Checklist
    print("\n📋 MIGRATION CHECKLIST STATUS:")
    checklist_items = [
        ("Repository skeleton", "migration_validation", "repository_structure"),
        ("Configuration assets", "migration_validation", "configuration_files"),
        ("Agent source trees", "migration_validation", "agent_paths"),
        ("Shared resources", "migration_validation", "shared_resources"),
        ("Docker environment", "migration_validation", "docker_environment"),
        ("Python dependencies", "migration_validation", "dependencies")
    ]
    
    for item_name, data_key, section_key in checklist_items:
        if data_key in data and section_key in data[data_key]:
            section = data[data_key][section_key]
            if isinstance(section, dict):
                all_good = all(
                    info.get('status', '').startswith('✅') 
                    for info in section.values()
                )
                status = "✅ COMPLETE" if all_good else "❌ INCOMPLETE"
            else:
                status = "✅ COMPLETE"
        else:
            status = "❓ UNKNOWN"
        
        print(f"   {item_name}: {status}")
    
    # Optimization Recommendations
    print("\n🛠️  OPTIMIZATION RECOMMENDATIONS:")
    optimizations = [
        "Merge ObservabilityHub for both machines into single container with multi-tenant mode",
        "Consolidate STT/TTS pipeline - Speech agents could share a base image",
        "Extract common utilities into common_lib/ to avoid code duplication",
        "Build unified requirements lock-file to guarantee identical versions",
        "Consider sidecar-less service-mesh (gRPC + xDS) to simplify port mapping"
    ]
    
    for i, optimization in enumerate(optimizations, 1):
        print(f"   {i}. {optimization}")
    
    # Next Steps
    print("\n🎯 IMMEDIATE NEXT STEPS:")
    next_steps = [
        "Pin all unpinned dependencies to exact versions",
        "Verify PORT_OFFSET environment variable strategy",
        "Test Docker image builds for both MainPC and PC2",
        "Run foundation services health checks",
        "Update documentation with new repository structure"
    ]
    
    for i, step in enumerate(next_steps, 1):
        print(f"   {i}. {step}")
    
    # Risk Assessment
    print("\n⚠️  RISK ASSESSMENT:")
    risks = [
        "Port collision risk: Ensure ${PORT_OFFSET} differs per container instance",
        "CUDA version mismatch: Host driver must match 12.1 runtime images",
        "Large model files: GGUF models often .gitignored - use artifact storage",
        "Permission issues: Ensure logs/, data/ have container-write permissions",
        "Environment variable leakage: Don't bake API keys into images"
    ]
    
    for i, risk in enumerate(risks, 1):
        print(f"   {i}. {risk}")
    
    print("\n" + "=" * 100)
    print("📄 Detailed reports available:")
    print("   • agent_analysis_results.json - Agent script path analysis")
    print("   • docker_groups_analysis.json - Docker groups validation")
    print("   • migration_validation_report.json - Complete migration validation")
    print("=" * 100)

def main():
    generate_migration_summary()

if __name__ == "__main__":
    main() 