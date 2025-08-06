#!/usr/bin/env python3
"""
Agent Group Scanner for Dockerization Compliance

This script scans agents by container group to verify compliance with architectural standards
before dockerization. It uses the compliance checking functionality from enhanced_system_audit.py
and organizes results by container group.

Usage:
    python3 scripts/scan_agents_by_group.py --system [mainpc|pc2|all] --phase [1-5] --output [path]
"""

import os
import sys
import yaml
import argparse
import logging
import datetime
import ast
import py_compile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_group_scan.log')
    ]
)
logger = logging.getLogger("AgentGroupScanner")

# Add parent directory to path to import from enhanced_system_audit.py
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.append(str(SCRIPT_DIR))

try:
    from enhanced_system_audit import check_compliance
except ImportError:
    logger.error("Error: Could not import check_compliance from enhanced_system_audit.py")
    sys.exit(1)

# Define paths
MAIN_CONFIG_PATH = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'
CONTAINER_GROUPS_PATH_MAINPC = PROJECT_ROOT / 'main_pc_code' / 'config' / 'container_groups.yaml'
CONTAINER_GROUPS_PATH_PC2 = PROJECT_ROOT / 'pc2_code' / 'config' / 'container_grouping.yaml'
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / 'documentation' / 'standards' / 'CONTINUATIONREPORT.MD'

# Define phases for scanning
PHASES = {
    1: {
        'mainpc': ['core_services', 'memory_system'],
        'pc2': ['TieredResponder', 'AsyncProcessor', 'CacheManager', 'PerformanceMonitor', 'VisionProcessingAgent']
    },
    2: {
        'mainpc': ['utility_services', 'ai_models_gpu_services'],
        'pc2': ['DreamWorldAgent', 'UnifiedMemoryReasoningAgent', 'TutorAgent', 'TutoringServiceAgent', 'ContextManager']
    },
    3: {
        'mainpc': ['vision_system', 'learning_knowledge'],
        'pc2': ['ExperienceTracker', 'ResourceManager', 'HealthMonitor', 'TaskScheduler']
    },
    4: {
        'mainpc': ['language_processing', 'audio_processing'],
        'pc2': ['AuthenticationAgent', 'SystemHealthManager', 'UnifiedUtilsAgent', 'ProactiveContextMonitor']
    },
    5: {
        'mainpc': ['emotion_system', 'utilities_support', 'reasoning_services'],
        'pc2': ['AgentTrustScorer', 'FileSystemAssistantAgent', 'RemoteConnectorAgent', 'UnifiedWebAgent', 'DreamingModeAgent', 'PerformanceLoggerAgent', 'AdvancedRouter', 'TutoringAgent', 'MemoryOrchestratorService']
    }
}

def load_config(config_path: Path) -> Dict:
    """Load YAML configuration file."""
    try:
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return {}
            
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

def get_mainpc_groups() -> Dict[str, Dict]:
    """Get agent groups from MainPC configuration."""
    config = load_config(MAIN_CONFIG_PATH)
    if not config or "agent_groups" not in config:
        logger.error("No agent_groups found in MainPC config")
        return {}
    
    return config.get("agent_groups", {})

def get_pc2_agents() -> List[Dict]:
    """Get agents from PC2 configuration."""
    config = load_config(PC2_CONFIG_PATH)
    if not config:
        logger.error("Failed to load PC2 config")
        return []
    
    pc2_services = config.get("pc2_services", [])
    core_services = config.get("core_services", [])
    
    # Combine pc2_services and core_services
    return pc2_services + core_services

def filter_agents_by_phase(system: str, phase: int) -> Dict[str, Any]:
    """Filter agents by phase."""
    if phase not in PHASES:
        logger.error(f"Invalid phase: {phase}")
        return {}
    
    result = {}
    
    if system in ['mainpc', 'all']:
        mainpc_groups = get_mainpc_groups()
        phase_groups = PHASES[phase]['mainpc']
        
        mainpc_phase_agents = {}
        for group_name in phase_groups:
            if group_name in mainpc_groups:
                mainpc_phase_agents[group_name] = mainpc_groups[group_name]
        
        result['mainpc'] = mainpc_phase_agents
    
    if system in ['pc2', 'all']:
        pc2_agents = get_pc2_agents()
        phase_agent_names = PHASES[phase]['pc2']
        
        pc2_phase_agents = []
        for agent in pc2_agents:
            if isinstance(agent, dict) and 'name' in agent and agent['name'] in phase_agent_names:
                pc2_phase_agents.append(agent)
        
        result['pc2'] = pc2_phase_agents
    
    return result

def check_syntax_errors(file_path: str) -> Tuple[bool, str]:
    """Check if a Python file has syntax errors."""
    try:
        py_compile.compile(file_path, doraise=True)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def scan_mainpc_agents(agents_by_group: Dict[str, Dict]) -> Dict[str, Dict]:
    """Scan MainPC agents for compliance."""
    results = {}
    
    for group_name, agents in agents_by_group.items():
        logger.info(f"Scanning MainPC group: {group_name} ({len(agents)} agents)")
        
        group_results = {}
        for agent_name, agent_config in agents.items():
            script_path = agent_config.get("script_path")
            if not script_path:
                logger.warning(f"No script_path for agent {agent_name}")
                continue
            
            # Build full path to agent script
            full_path = PROJECT_ROOT / script_path
            
            if not full_path.exists():
                logger.warning(f"Agent script not found: {full_path}")
                group_results[agent_name] = {
                    "path": str(full_path),
                    "status": "FAIL",
                    "issues": {"0": "File not found"}
                }
                continue
            
            # Check for syntax errors first
            syntax_valid, syntax_error = check_syntax_errors(str(full_path))
            if not syntax_valid:
                logger.error(f"Syntax error in {agent_name}: {syntax_error}")
                group_results[agent_name] = {
                    "path": str(full_path),
                    "status": "FAIL",
                    "issues": {"0": f"Syntax error: {syntax_error}"}
                }
                continue
            
            # Check compliance
            try:
                status, issues = check_compliance(str(full_path))
                
                # Convert issues to rule-based format
                rule_issues = {}
                for issue in issues:
                    if "C1/C2" in issue:
                        rule_issues["1"] = issue
                    elif "C3" in issue:
                        rule_issues["2"] = issue
                    elif "C4" in issue:
                        rule_issues["6"] = issue
                    elif "C6/C7" in issue:
                        rule_issues["2"] = issue
                    elif "C10" in issue:
                        rule_issues["5"] = issue
                
                group_results[agent_name] = {
                    "path": str(full_path),
                    "status": "PASS" if isinstance(status, str) and "✅" in status else "FAIL",
                    "issues": rule_issues
                }
            except Exception as e:
                logger.error(f"Error checking compliance for {agent_name}: {e}")
                group_results[agent_name] = {
                    "path": str(full_path),
                    "status": "FAIL",
                    "issues": {"0": f"Error: {str(e)}"}
                }
        
        results[group_name] = group_results
    
    return results

def scan_pc2_agents(agents: List[Dict]) -> Dict[str, Dict]:
    """Scan PC2 agents for compliance."""
    results = {}
    
    for agent in agents:
        name = agent.get("name", "")
        script_path = agent.get("script_path", "")
        
        if not name or not script_path:
            logger.warning(f"Invalid agent configuration: {agent}")
            continue
        
        # Build full path to agent script
        full_path = PROJECT_ROOT / script_path
        
        if not full_path.exists():
            logger.warning(f"Agent script not found: {full_path}")
            results[name] = {
                "path": str(full_path),
                "status": "FAIL",
                "issues": {"0": "File not found"}
            }
            continue
        
        # Check for syntax errors first
        syntax_valid, syntax_error = check_syntax_errors(str(full_path))
        if not syntax_valid:
            logger.error(f"Syntax error in {name}: {syntax_error}")
            results[name] = {
                "path": str(full_path),
                "status": "FAIL",
                "issues": {"0": f"Syntax error: {syntax_error}"}
            }
            continue
        
        # Check compliance
        try:
            status, issues = check_compliance(str(full_path))
            
            # Convert issues to rule-based format
            rule_issues = {}
            for issue in issues:
                if "C1/C2" in issue:
                    rule_issues["1"] = issue
                elif "C3" in issue:
                    rule_issues["2"] = issue
                elif "C4" in issue:
                    rule_issues["6"] = issue
                elif "C6/C7" in issue:
                    rule_issues["2"] = issue
                elif "C10" in issue:
                    rule_issues["5"] = issue
            
            results[name] = {
                "path": str(full_path),
                "status": "PASS" if isinstance(status, str) and "✅" in status else "FAIL",
                "issues": rule_issues
            }
        except Exception as e:
            logger.error(f"Error checking compliance for {name}: {e}")
            results[name] = {
                "path": str(full_path),
                "status": "FAIL",
                "issues": {"0": f"Error: {str(e)}"}
            }
    
    return results

def generate_report(results: Dict[str, Dict], system: str, phase: int, output_path: Path):
    """Generate a markdown report of the scan results."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Count statistics
    total_agents = 0
    agents_with_critical_issues = 0
    total_violations = 0
    violation_counts = {}
    
    # For MainPC
    if 'mainpc' in results:
        for group_name, group_results in results['mainpc'].items():
            for agent_name, agent_result in group_results.items():
                total_agents += 1
                if agent_result['status'] == 'FAIL':
                    if any(rule in ['0', '2', '3', '5'] for rule in agent_result['issues']):
                        agents_with_critical_issues += 1
                
                total_violations += len(agent_result['issues'])
                for rule in agent_result['issues']:
                    violation_counts[rule] = violation_counts.get(rule, 0) + 1
    
    # For PC2
    if 'pc2' in results:
        for agent_name, agent_result in results['pc2'].items():
            total_agents += 1
            if agent_result['status'] == 'FAIL':
                if any(rule in ['0', '2', '3', '5'] for rule in agent_result['issues']):
                    agents_with_critical_issues += 1
            
            total_violations += len(agent_result['issues'])
            for rule in agent_result['issues']:
                violation_counts[rule] = violation_counts.get(rule, 0) + 1
    
    # Sort violation counts
    most_common_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)
    most_common_rules = [rule for rule, _ in most_common_violations[:3]]
    
    # Generate report
    with open(output_path, 'w') as f:
        f.write(f"# Agent Audit Report: {today}\n\n")
        f.write("## 1. Executive Summary\n\n")
        f.write(f"- **Agents Scanned:** {total_agents}\n")
        f.write(f"- **Agents with Critical Issues (Violations of Rule 0, 2, 3, 5):** {agents_with_critical_issues}\n")
        f.write(f"- **Total Violations Found:** {total_violations}\n")
        f.write(f"- **Most Common Violations:** {', '.join(most_common_rules)}\n\n")
        f.write("---\n\n")
        f.write("## 2. Detailed Agent Breakdown\n\n")
        
        # Write MainPC results
        if 'mainpc' in results:
            f.write("### MainPC Agents\n\n")
            
            for group_name, group_results in results['mainpc'].items():
                f.write(f"#### Group: {group_name}\n\n")
                
                for agent_name, agent_result in group_results.items():
                    f.write(f"### Agent: `{agent_result['path']}`\n\n")
                    f.write("| Rule ID | Status | Findings (Line # and Issue) |\n")
                    f.write("|:---|:---|:---|\n")
                    
                    # Rule 0: Code Correctness
                    if "0" in agent_result['issues']:
                        f.write(f"| **0** | `[FAIL]` | {agent_result['issues']['0']} |\n")
                    else:
                        f.write("| **0** | `[PASS]` | No syntax errors found. |\n")
                    
                    # Rule 1: Core Foundation
                    if "1" in agent_result['issues']:
                        f.write(f"| **1** | `[FAIL]` | {agent_result['issues']['1']} |\n")
                    else:
                        f.write("| **1** | `[PASS]` | Properly inherits from BaseAgent. |\n")
                    
                    # Rule 2: Configuration Management
                    if "2" in agent_result['issues']:
                        f.write(f"| **2** | `[FAIL]` | {agent_result['issues']['2']} |\n")
                    else:
                        f.write("| **2** | `[PASS]` | No hardcoded values found. |\n")
                    
                    # Rule 3: Networking & Service Discovery
                    if "3" in agent_result['issues']:
                        f.write(f"| **3** | `[FAIL]` | {agent_result['issues']['3']} |\n")
                    else:
                        f.write("| **3** | `[PASS]` | Properly uses service discovery. |\n")
                    
                    # Rule 4: State Management
                    if "4" in agent_result['issues']:
                        f.write(f"| **4** | `[FAIL]` | {agent_result['issues']['4']} |\n")
                    else:
                        f.write("| **4** | `[PASS]` | Does not rely on local files for critical state. |\n")
                    
                    # Rule 5: Lifecycle & Resource Cleanup
                    if "5" in agent_result['issues']:
                        f.write(f"| **5** | `[FAIL]` | {agent_result['issues']['5']} |\n")
                    else:
                        f.write("| **5** | `[PASS]` | Has proper _shutdown() method. |\n")
                    
                    # Rule 6: Health Monitoring
                    if "6" in agent_result['issues']:
                        f.write(f"| **6** | `[FAIL]` | {agent_result['issues']['6']} |\n")
                    else:
                        f.write("| **6** | `[PASS]` | Has standardized health_check() method. |\n")
                    
                    # Rule 7: Logging
                    if "7" in agent_result['issues']:
                        f.write(f"| **7** | `[FAIL]` | {agent_result['issues']['7']} |\n")
                    else:
                        f.write("| **7** | `[PASS]` | Logs to stdout/stderr. |\n")
                    
                    # Rule 8: Error Reporting
                    if "8" in agent_result['issues']:
                        f.write(f"| **8** | `[FAIL]` | {agent_result['issues']['8']} |\n")
                    else:
                        f.write("| **8** | `[PASS]` | Uses central Error Bus. |\n")
                    
                    # Rule 9: Dependency Imports
                    if "9" in agent_result['issues']:
                        f.write(f"| **9** | `[FAIL]` | {agent_result['issues']['9']} |\n")
                    else:
                        f.write("| **9** | `[PASS]` | Clean imports. |\n")
                    
                    f.write("\n---\n\n")
        
        # Write PC2 results
        if 'pc2' in results:
            f.write("### PC2 Agents\n\n")
            
            for agent_name, agent_result in results['pc2'].items():
                f.write(f"### Agent: `{agent_result['path']}`\n\n")
                f.write("| Rule ID | Status | Findings (Line # and Issue) |\n")
                f.write("|:---|:---|:---|\n")
                
                # Rule 0: Code Correctness
                if "0" in agent_result['issues']:
                    f.write(f"| **0** | `[FAIL]` | {agent_result['issues']['0']} |\n")
                else:
                    f.write("| **0** | `[PASS]` | No syntax errors found. |\n")
                
                # Rule 1: Core Foundation
                if "1" in agent_result['issues']:
                    f.write(f"| **1** | `[FAIL]` | {agent_result['issues']['1']} |\n")
                else:
                    f.write("| **1** | `[PASS]` | Properly inherits from BaseAgent. |\n")
                
                # Rule 2: Configuration Management
                if "2" in agent_result['issues']:
                    f.write(f"| **2** | `[FAIL]` | {agent_result['issues']['2']} |\n")
                else:
                    f.write("| **2** | `[PASS]` | No hardcoded values found. |\n")
                
                # Rule 3: Networking & Service Discovery
                if "3" in agent_result['issues']:
                    f.write(f"| **3** | `[FAIL]` | {agent_result['issues']['3']} |\n")
                else:
                    f.write("| **3** | `[PASS]` | Properly uses service discovery. |\n")
                
                # Rule 4: State Management
                if "4" in agent_result['issues']:
                    f.write(f"| **4** | `[FAIL]` | {agent_result['issues']['4']} |\n")
                else:
                    f.write("| **4** | `[PASS]` | Does not rely on local files for critical state. |\n")
                
                # Rule 5: Lifecycle & Resource Cleanup
                if "5" in agent_result['issues']:
                    f.write(f"| **5** | `[FAIL]` | {agent_result['issues']['5']} |\n")
                else:
                    f.write("| **5** | `[PASS]` | Has proper _shutdown() method. |\n")
                
                # Rule 6: Health Monitoring
                if "6" in agent_result['issues']:
                    f.write(f"| **6** | `[FAIL]` | {agent_result['issues']['6']} |\n")
                else:
                    f.write("| **6** | `[PASS]` | Has standardized health_check() method. |\n")
                
                # Rule 7: Logging
                if "7" in agent_result['issues']:
                    f.write(f"| **7** | `[FAIL]` | {agent_result['issues']['7']} |\n")
                else:
                    f.write("| **7** | `[PASS]` | Logs to stdout/stderr. |\n")
                
                # Rule 8: Error Reporting
                if "8" in agent_result['issues']:
                    f.write(f"| **8** | `[FAIL]` | {agent_result['issues']['8']} |\n")
                else:
                    f.write("| **8** | `[PASS]` | Uses central Error Bus. |\n")
                
                # Rule 9: Dependency Imports
                if "9" in agent_result['issues']:
                    f.write(f"| **9** | `[FAIL]` | {agent_result['issues']['9']} |\n")
                else:
                    f.write("| **9** | `[PASS]` | Clean imports. |\n")
                
                f.write("\n---\n\n")
        
        # Add next steps and recommendations
        f.write("## 3. Recommendations and Next Steps\n\n")
        f.write("Based on the audit results, here are the recommended next steps:\n\n")
        
        if agents_with_critical_issues > 0:
            f.write("### Critical Issues to Address First:\n")
            f.write("1. Fix syntax errors (Rule 0 violations)\n")
            f.write("2. Remove hardcoded values (Rule 2 violations)\n")
            f.write("3. Implement proper service discovery (Rule 3 violations)\n")
            f.write("4. Add proper resource cleanup (Rule 5 violations)\n\n")
        
        f.write("### General Recommendations:\n")
        f.write("1. Create standardized templates for agents\n")
        f.write("2. Implement automated compliance checking in CI/CD\n")
        f.write("3. Refactor agents in phases, starting with the most critical ones\n")
        f.write("4. Verify each agent after refactoring\n\n")
        
        f.write("### Next Phase:\n")
        if phase < 5:
            next_phase = phase + 1
            f.write(f"Proceed to Phase {next_phase} audit after addressing critical issues in this phase.\n\n")
        else:
            f.write("This was the final phase. Proceed to containerization after addressing all critical issues.\n\n")
        
        f.write("## 4. Suggested Commands for Next Steps\n\n")
        f.write("```bash\n")
        if phase < 5:
            f.write(f"# Run next phase audit\n")
            f.write(f"python3 scripts/scan_agents_by_group.py --system {system} --phase {phase + 1}\n\n")
        
        f.write("# Fix critical issues in agents\n")
        f.write("python3 scripts/fix_agent_compliance.py --agent [agent_path]\n\n")
        
        f.write("# Verify fixed agents\n")
        f.write("python3 scripts/scan_agents_by_group.py --system {system} --phase {phase} --verify-only\n")
        f.write("```\n")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Scan agents by container group for dockerization compliance")
    parser.add_argument("--system", choices=["mainpc", "pc2", "all"], default="all", help="System to scan (mainpc, pc2, or all)")
    parser.add_argument("--phase", type=int, choices=range(1, 6), default=1, help="Phase to scan (1-5)")
    parser.add_argument("--output", type=str, help="Output path for the report")
    parser.add_argument("--verify-only", action="store_true", help="Only verify previously scanned agents")
    args = parser.parse_args()
    
    logger.info(f"Starting agent group scan for dockerization compliance - System: {args.system}, Phase: {args.phase}")
    
    # Determine output path
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT_PATH
    
    # Filter agents by phase
    filtered_agents = filter_agents_by_phase(args.system, args.phase)
    
    results = {}
    
    # Scan MainPC agents
    if 'mainpc' in filtered_agents:
        logger.info(f"Scanning {len(filtered_agents['mainpc'])} MainPC agent groups")
        results['mainpc'] = scan_mainpc_agents(filtered_agents['mainpc'])
    
    # Scan PC2 agents
    if 'pc2' in filtered_agents:
        logger.info(f"Scanning {len(filtered_agents['pc2'])} PC2 agents")
        results['pc2'] = scan_pc2_agents(filtered_agents['pc2'])
    
    # Generate report
    generate_report(results, args.system, args.phase, output_path)
    
    logger.info(f"Scan completed. Report saved to {output_path}")
    print(f"Scan completed. Report saved to {output_path}")

if __name__ == "__main__":
    main() 