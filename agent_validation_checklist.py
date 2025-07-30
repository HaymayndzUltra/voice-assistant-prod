#!/usr/bin/env python3
"""
Agent Validation Checklist System for MainPC Agents
Comprehensive validation patterns for imports, logic, dependencies, communication, etc.
Supports dynamic loading of new checks as needed.
"""

import os
import sys
import importlib
import inspect
import ast
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    status: str  # "PASS", "WARNING", "FAIL", "ERROR"
    message: str
    details: Optional[Dict[str, Any]] = None
    severity: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"

@dataclass
class AgentInfo:
    """Information about an agent"""
    name: str
    script_path: str
    port: str
    health_check_port: str
    required: bool
    dependencies: List[str]
    config: Optional[Dict[str, Any]] = None
    group: str = ""

class AgentValidator:
    """Main validator class for agent analysis"""

    def __init__(self, config_path: str = "main_pc_code/config/startup_config.yaml"):
        """TODO: Add description for __init__."""
        self.config_path = config_path
        self.agents: Dict[str, AgentInfo] = {}
        self.validation_results: Dict[str, List[ValidationResult]] = {}
        self.checklist_modules: Dict[str, Any] = {}

        # Load validation checklists
        self._load_validation_checklists()

    def _load_validation_checklists(self):
        """Load all validation checklist modules"""
        checklist_dir = Path("validation_checklists")
        if checklist_dir.exists():
            for file in checklist_dir.glob("*.py"):
                if file.name.startswith("check_"):
                    module_name = file.stem
                    try:
                        spec = importlib.util.spec_from_file_location(module_name, file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self.checklist_modules[module_name] = module
                        logger.info(f"Loaded validation checklist: {module_name}")
                    except Exception as e:
                        logger.error(f"Failed to load checklist {module_name}: {e}")

    def extract_agents_from_config(self) -> Dict[str, AgentInfo]:
        """Extract all agents from startup configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            if not config:
                logger.error("Failed to load YAML configuration")
                return {}

            agents = {}

            agent_groups = config.get('agent_groups', {})
            if not agent_groups:
                logger.error("No agent_groups found in configuration")
                return {}

            for group_name, group_config in agent_groups.items():
                if not isinstance(group_config, dict):
                    continue

                for agent_name, agent_config in group_config.items():
                    if isinstance(agent_config, dict):
                        agent_info = AgentInfo(
                            name=agent_name,
                            script_path=agent_config.get('script_path', ''),
                            port=str(agent_config.get('port', '')),
                            health_check_port=str(agent_config.get('health_check_port', '')),
                            required=agent_config.get('required', False),
                            dependencies=agent_config.get('dependencies', []),
                            config=agent_config.get('config', {}),
                            group=group_name
                        )
                        agents[agent_name] = agent_info

            self.agents = agents
            logger.info(f"Extracted {len(agents)} agents from configuration")
            return agents

        except Exception as e:
            logger.error(f"Failed to extract agents from config: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def validate_agent_imports(self, agent_info: AgentInfo) -> List[ValidationResult]:
        """Validate agent imports and dependencies"""
        results = []

        if not os.path.exists(agent_info.script_path):
            results.append(ValidationResult(
                check_name="File Existence",
                status="FAIL",
                message=f"Agent script not found: {agent_info.script_path}",
                severity="CRITICAL"
            ))
            return results

        try:
            with open(agent_info.script_path, 'r') as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Check imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")

            # Validate critical imports
            critical_imports = [
                'zmq', 'asyncio', 'logging', 'json', 'yaml',
                'typing', 'dataclasses', 'pathlib'
            ]

            for imp in critical_imports:
                if not any(imp in import_name for import_name in imports):
                    results.append(ValidationResult(
                        check_name="Critical Import Check",
                        status="WARNING",
                        message=f"Missing critical import: {imp}",
                        severity="MEDIUM"
                    ))

            # Check for potential import issues
            for imp in imports:
                if imp.startswith('main_pc_code'):
                    # Check if the import path exists
                    import_path = imp.replace('.', '/') + '.py'
                    if not os.path.exists(import_path):
                        results.append(ValidationResult(
                            check_name="Import Path Validation",
                            status="WARNING",
                            message=f"Import path may not exist: {imp}",
                            severity="MEDIUM"
                        ))

            if not results:
                results.append(ValidationResult(
                    check_name="Import Validation",
                    status="PASS",
                    message="All imports validated successfully",
                    severity="LOW"
                ))

        except Exception as e:
            results.append(ValidationResult(
                check_name="Import Analysis",
                status="ERROR",
                message=f"Failed to analyze imports: {e}",
                severity="HIGH"
            ))

        return results

    def validate_agent_dependencies(self, agent_info: AgentInfo) -> List[ValidationResult]:
        """Validate agent dependencies"""
        results = []

        # Check if dependencies exist in config
        for dep in agent_info.dependencies:
            if dep not in self.agents:
                results.append(ValidationResult(
                    check_name="Dependency Existence",
                    status="FAIL",
                    message=f"Dependency not found in config: {dep}",
                    severity="HIGH"
                ))

        # Check for circular dependencies
        visited = set()
        rec_stack = set()

 """TODO: Add description for has_circular_dependency."""
        def has_circular_dependency(agent_name: str) -> bool:
            if agent_name in rec_stack:
                return True
            if agent_name in visited:
                return False

            visited.add(agent_name)
            rec_stack.add(agent_name)

            if agent_name in self.agents:
                for dep in self.agents[agent_name].dependencies:
                    if has_circular_dependency(dep):
                        return True

            rec_stack.remove(agent_name)
            return False

        if has_circular_dependency(agent_info.name):
            results.append(ValidationResult(
                check_name="Circular Dependency",
                status="FAIL",
                message=f"Circular dependency detected for agent: {agent_info.name}",
                severity="CRITICAL"
            ))

        if not results:
            results.append(ValidationResult(
                check_name="Dependency Validation",
                status="PASS",
                message="Dependencies validated successfully",
                severity="LOW"
            ))

        return results

    def validate_agent_communication(self, agent_info: AgentInfo) -> List[ValidationResult]:
        """Validate agent communication patterns"""
        results = []

        if not os.path.exists(agent_info.script_path):
            return results

        try:
            with open(agent_info.script_path, 'r') as f:
                content = f.read()

            # Check for ZMQ patterns
            zmq_patterns = [
                'zmq.Context', 'zmq.Socket', 'zmq.REQ', 'zmq.REP',
                'zmq.PUB', 'zmq.SUB', 'zmq.PUSH', 'zmq.PULL'
            ]

            zmq_found = any(pattern in content for pattern in zmq_patterns)

            if zmq_found:
                # Check for proper socket cleanup
                if 'socket.close()' not in content and 'context.term()' not in content:
                    results.append(ValidationResult(
                        check_name="ZMQ Cleanup",
                        status="WARNING",
                        message="ZMQ sockets may not be properly cleaned up",
                        severity="MEDIUM"
                    ))

                # Check for error handling in ZMQ operations
                if 'try:' in content and 'except' in content:
                    results.append(ValidationResult(
                        check_name="ZMQ Error Handling",
                        status="PASS",
                        message="ZMQ operations have error handling",
                        severity="LOW"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="ZMQ Error Handling",
                        status="WARNING",
                        message="ZMQ operations may lack error handling",
                        severity="MEDIUM"
                    ))

            # Check for async patterns
            if 'async def' in content:
                if 'await' in content:
                    results.append(ValidationResult(
                        check_name="Async Pattern",
                        status="PASS",
                        message="Proper async/await pattern detected",
                        severity="LOW"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="Async Pattern",
                        status="WARNING",
                        message="Async function without await calls",
                        severity="MEDIUM"
                    ))

            # Check for logging
            if 'logging' in content or 'logger' in content:
                results.append(ValidationResult(
                    check_name="Logging",
                    status="PASS",
                    message="Logging implementation detected",
                    severity="LOW"
                ))
            else:
                results.append(ValidationResult(
                    check_name="Logging",
                    status="WARNING",
                    message="No logging implementation detected",
                    severity="MEDIUM"
                ))

        except Exception as e:
            results.append(ValidationResult(
                check_name="Communication Analysis",
                status="ERROR",
                message=f"Failed to analyze communication patterns: {e}",
                severity="HIGH"
            ))

        return results

    def validate_agent_configuration(self, agent_info: AgentInfo) -> List[ValidationResult]:
        """Validate agent configuration"""
        results = []

        # Check port configuration
        if agent_info.port:
            try:
                port_value = agent_info.port.replace("${PORT_OFFSET}+", "")
                port_num = int(port_value)
                if port_num < 1024 or port_num > 65535:
                    results.append(ValidationResult(
                        check_name="Port Range",
                        status="WARNING",
                        message=f"Port {port_num} may be outside recommended range (1024-65535)",
                        severity="MEDIUM"
                    ))
            except ValueError:
                results.append(ValidationResult(
                    check_name="Port Format",
                    status="WARNING",
                    message=f"Port format may be invalid: {agent_info.port}",
                    severity="MEDIUM"
                ))

        # Check health check port
        if agent_info.health_check_port:
            try:
                hc_port_value = agent_info.health_check_port.replace("${PORT_OFFSET}+", "")
                hc_port_num = int(hc_port_value)
                if hc_port_num < 1024 or hc_port_num > 65535:
                    results.append(ValidationResult(
                        check_name="Health Check Port Range",
                        status="WARNING",
                        message=f"Health check port {hc_port_num} may be outside recommended range",
                        severity="MEDIUM"
                    ))
            except ValueError:
                results.append(ValidationResult(
                    check_name="Health Check Port Format",
                    status="WARNING",
                    message=f"Health check port format may be invalid: {agent_info.health_check_port}",
                    severity="MEDIUM"
                ))

        # Check for port conflicts
        all_ports = []
        for agent in self.agents.values():
            if agent.port:
                all_ports.append(agent.port)
            if agent.health_check_port:
                all_ports.append(agent.health_check_port)

        if len(all_ports) != len(set(all_ports)):
            results.append(ValidationResult(
                check_name="Port Conflicts",
                status="FAIL",
                message="Potential port conflicts detected",
                severity="HIGH"
            ))

        if not results:
            results.append(ValidationResult(
                check_name="Configuration Validation",
                status="PASS",
                message="Configuration validated successfully",
                severity="LOW"
            ))

        return results

    def run_dynamic_checks(self, agent_info: AgentInfo) -> List[ValidationResult]:
        """Run dynamically loaded validation checks"""
        results = []

        for module_name, module in self.checklist_modules.items():
            if hasattr(module, 'validate_agent'):
                try:
                    module_results = module.validate_agent(agent_info, self.agents)
                    if isinstance(module_results, list):
                        results.extend(module_results)
                    elif isinstance(module_results, ValidationResult):
                        results.append(module_results)
                except Exception as e:
                    results.append(ValidationResult(
                        check_name=f"Dynamic Check: {module_name}",
                        status="ERROR",
                        message=f"Dynamic check failed: {e}",
                        severity="HIGH"
                    ))

        return results

    def validate_agent(self, agent_name: str) -> List[ValidationResult]:
        """Validate a single agent comprehensively"""
        if agent_name not in self.agents:
            return [ValidationResult(
                check_name="Agent Existence",
                status="FAIL",
                message=f"Agent {agent_name} not found in configuration",
                severity="CRITICAL"
            )]

        agent_info = self.agents[agent_name]
        results = []

        # Run all validation checks
        results.extend(self.validate_agent_imports(agent_info))
        results.extend(self.validate_agent_dependencies(agent_info))
        results.extend(self.validate_agent_communication(agent_info))
        results.extend(self.validate_agent_configuration(agent_info))
        results.extend(self.run_dynamic_checks(agent_info))

        self.validation_results[agent_name] = results
        return results

    def validate_critical_agents(self) -> Dict[str, List[ValidationResult]]:
        """Validate critical agents first"""
        critical_agents = [
            'ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator',
            'ModelManagerSuite', 'VRAMOptimizerAgent', 'ObservabilityHub'
        ]

        results = {}
        for agent_name in critical_agents:
            if agent_name in self.agents:
                logger.info(f"Validating critical agent: {agent_name}")
                results[agent_name] = self.validate_agent(agent_name)

        return results

    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        report = []
        report.append("# MainPC Agent Validation Report")
        report.append(f"Generated: {__import__('datetime').datetime.now()}")
        report.append(f"Total Agents: {len(self.agents)}")
        report.append("")

        # Summary statistics
        total_checks = 0
        passed_checks = 0
        warning_checks = 0
        failed_checks = 0
        error_checks = 0

        for agent_name, results in self.validation_results.items():
            report.append(f"## {agent_name}")
            report.append(f"**Group:** {self.agents[agent_name].group}")
            report.append(f"**Script:** {self.agents[agent_name].script_path}")
            report.append(f"**Port:** {self.agents[agent_name].port}")
            report.append(f"**Required:** {self.agents[agent_name].required}")
            report.append("")

            for result in results:
                total_checks += 1
                status_emoji = {
                    "PASS": "✅",
                    "WARNING": "⚠️",
                    "FAIL": "❌",
                    "ERROR": "🚨"
                }.get(result.status, "❓")

                report.append(f"{status_emoji} **{result.check_name}** ({result.severity})")
                report.append(f"   {result.message}")
                report.append("")

                if result.status == "PASS":
                    passed_checks += 1
                elif result.status == "WARNING":
                    warning_checks += 1
                elif result.status == "FAIL":
                    failed_checks += 1
                elif result.status == "ERROR":
                    error_checks += 1

            report.append("---")
            report.append("")

        # Summary
        report.append("## Summary")
        report.append(f"- ✅ Passed: {passed_checks}")
        report.append(f"- ⚠️ Warnings: {warning_checks}")
        report.append(f"- ❌ Failed: {failed_checks}")
        report.append(f"- 🚨 Errors: {error_checks}")
        report.append(f"- 📊 Total: {total_checks}")

        return "\n".join(report)

def main():
    """Main function to run agent validation"""
    validator = AgentValidator()

    # Extract agents
    agents = validator.extract_agents_from_config()
    print(f"Extracted {len(agents)} agents from configuration")

    # Validate critical agents first
    print("\nValidating critical agents...")
    critical_results = validator.validate_critical_agents()

    # Generate report
    report = validator.generate_report()

    # Save report
    with open("agent_validation_report.md", "w") as f:
        f.write(report)

    print("\nValidation complete! Report saved to agent_validation_report.md")

    # Print summary
    total_agents = len(validator.validation_results)
    total_checks = sum(len(results) for results in validator.validation_results.values())
    passed_checks = sum(
        sum(1 for r in results if r.status == "PASS")
        for results in validator.validation_results.values()
    )

    print(f"\nSummary: {total_agents} agents analyzed, {total_checks} checks performed, {passed_checks} passed")

if __name__ == "__main__":
    main()
