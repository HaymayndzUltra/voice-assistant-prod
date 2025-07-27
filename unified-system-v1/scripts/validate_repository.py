#!/usr/bin/env python3
"""
Repository Validation Script
Validates the unified system repository structure and components
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import List, Dict, Tuple

class RepositoryValidator:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.errors = []
        self.warnings = []
        self.passed = []
        
    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🔍 Validating Unified System Repository...")
        print("=" * 60)
        
        checks = [
            self.check_directory_structure,
            self.check_essential_files,
            self.check_configurations,
            self.check_scripts,
            self.check_documentation,
            self.check_dependencies,
            self.check_docker_setup,
            self.check_ci_cd,
            self.check_monitoring,
            self.check_tests
        ]
        
        for check in checks:
            check()
            
        self._print_results()
        return len(self.errors) == 0
        
    def check_directory_structure(self):
        """Validate directory structure"""
        print("\n📁 Checking directory structure...")
        
        required_dirs = [
            "src/agents",
            "src/core",
            "src/utils",
            "config/profiles",
            "config/environments",
            "scripts/deployment",
            "scripts/testing",
            "scripts/maintenance",
            "docs/api",
            "docs/guides",
            "docs/architecture",
            "tests/unit",
            "tests/integration",
            "tests/e2e",
            "monitoring/prometheus",
            "monitoring/grafana",
            ".github/workflows"
        ]
        
        for dir_path in required_dirs:
            full_path = self.repo_path / dir_path
            if full_path.exists():
                self.passed.append(f"Directory exists: {dir_path}")
            else:
                self.errors.append(f"Missing directory: {dir_path}")
                
    def check_essential_files(self):
        """Check for essential files"""
        print("\n📄 Checking essential files...")
        
        essential_files = [
            ("main.py", "Main entry point"),
            ("requirements.txt", "Python dependencies"),
            ("README.md", "Documentation"),
            (".env.example", "Environment template"),
            (".gitignore", "Git ignore rules"),
            ("Dockerfile", "Container definition"),
            ("docker-compose.yml", "Compose configuration"),
            ("config/startup_config.yaml", "Main configuration")
        ]
        
        for file_path, description in essential_files:
            full_path = self.repo_path / file_path
            if full_path.exists():
                self.passed.append(f"{description}: {file_path}")
            else:
                self.errors.append(f"Missing {description}: {file_path}")
                
    def check_configurations(self):
        """Validate configuration files"""
        print("\n⚙️  Checking configurations...")
        
        # Check main config
        config_path = self.repo_path / "config/startup_config.yaml"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    
                if "global_settings" in config:
                    self.passed.append("Main config has global_settings")
                else:
                    self.errors.append("Main config missing global_settings")
                    
                if "agent_groups" in config:
                    agent_count = sum(len(agents) for agents in config["agent_groups"].values())
                    self.passed.append(f"Main config has {agent_count} agents defined")
                else:
                    self.errors.append("Main config missing agent_groups")
                    
            except Exception as e:
                self.errors.append(f"Invalid main config: {e}")
                
        # Check profiles
        profiles = ["core", "vision", "learning", "tutoring", "full"]
        for profile in profiles:
            profile_path = self.repo_path / f"config/profiles/{profile}.yaml"
            if profile_path.exists():
                self.passed.append(f"Profile exists: {profile}")
            else:
                self.errors.append(f"Missing profile: {profile}")
                
    def check_scripts(self):
        """Check for required scripts"""
        print("\n📜 Checking scripts...")
        
        required_scripts = [
            ("scripts/deployment/launch.py", "Launch script"),
            ("scripts/testing/chaos_test.py", "Chaos testing"),
            ("scripts/testing/routing_benchmark_simple.py", "Routing benchmark"),
            ("scripts/maintenance/validate_config.py", "Config validator"),
            ("src/core/lazy_loader_service.py", "LazyLoader service"),
            ("src/core/hybrid_llm_router.py", "Hybrid LLM router"),
            ("src/utils/resilience_enhancements.py", "Resilience utilities")
        ]
        
        for script_path, description in required_scripts:
            full_path = self.repo_path / script_path
            if full_path.exists():
                self.passed.append(f"{description}: {script_path}")
            else:
                self.errors.append(f"Missing {description}: {script_path}")
                
    def check_documentation(self):
        """Check documentation completeness"""
        print("\n📚 Checking documentation...")
        
        docs = [
            ("README.md", "Main README"),
            ("docs/guides/operational_runbook.md", "Runbook"),
            ("docs/guides/quick_start.md", "Quick start guide"),
            ("docs/architecture/phase1_completion_report.md", "Phase 1 report"),
            ("docs/architecture/phase2_completion_report.md", "Phase 2 report"),
            ("docs/architecture/phase3_completion_report.md", "Phase 3 report")
        ]
        
        for doc_path, description in docs:
            full_path = self.repo_path / doc_path
            if full_path.exists():
                # Check if file has content
                size = full_path.stat().st_size
                if size > 100:
                    self.passed.append(f"{description} exists ({size} bytes)")
                else:
                    self.warnings.append(f"{description} exists but seems empty")
            else:
                self.errors.append(f"Missing {description}: {doc_path}")
                
    def check_dependencies(self):
        """Validate dependencies file"""
        print("\n📦 Checking dependencies...")
        
        req_path = self.repo_path / "requirements.txt"
        if req_path.exists():
            with open(req_path) as f:
                lines = f.readlines()
                
            deps = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
            
            essential_deps = ["pyyaml", "flask", "prometheus-client", "pytest"]
            for dep in essential_deps:
                if any(dep in d.lower() for d in deps):
                    self.passed.append(f"Has dependency: {dep}")
                else:
                    self.warnings.append(f"Missing recommended dependency: {dep}")
                    
            self.passed.append(f"Total dependencies: {len(deps)}")
            
    def check_docker_setup(self):
        """Check Docker configuration"""
        print("\n🐳 Checking Docker setup...")
        
        # Check Dockerfile
        dockerfile = self.repo_path / "Dockerfile"
        if dockerfile.exists():
            with open(dockerfile) as f:
                content = f.read()
                
            checks = [
                ("FROM python", "Base image"),
                ("WORKDIR", "Working directory"),
                ("COPY requirements", "Requirements copy"),
                ("EXPOSE", "Port exposure"),
                ("HEALTHCHECK", "Health check")
            ]
            
            for pattern, description in checks:
                if pattern in content:
                    self.passed.append(f"Dockerfile has {description}")
                else:
                    self.warnings.append(f"Dockerfile missing {description}")
                    
        # Check docker-compose
        compose_file = self.repo_path / "docker-compose.yml"
        if compose_file.exists():
            self.passed.append("Docker Compose file exists")
            
    def check_ci_cd(self):
        """Check CI/CD configuration"""
        print("\n🔄 Checking CI/CD setup...")
        
        ci_file = self.repo_path / ".github/workflows/ci.yml"
        if ci_file.exists():
            with open(ci_file) as f:
                content = f.read()
                
            checks = ["lint", "test", "security", "build", "chaos-test"]
            for check in checks:
                if f"name: {check}" in content.lower() or f"job: {check}" in content.lower():
                    self.passed.append(f"CI has {check} job")
                else:
                    self.warnings.append(f"CI might be missing {check} job")
                    
    def check_monitoring(self):
        """Check monitoring configuration"""
        print("\n📊 Checking monitoring setup...")
        
        alerts_file = self.repo_path / "monitoring/prometheus/alerts.yaml"
        if alerts_file.exists():
            self.passed.append("Prometheus alerts configured")
            
            with open(alerts_file) as f:
                content = yaml.safe_load(f)
                
            if "groups" in content:
                alert_count = sum(len(g.get("rules", [])) for g in content["groups"])
                self.passed.append(f"Total alert rules: {alert_count}")
                
    def check_tests(self):
        """Check test files"""
        print("\n🧪 Checking tests...")
        
        test_files = [
            "tests/integration/test_phase2_integration.py"
        ]
        
        for test_file in test_files:
            full_path = self.repo_path / test_file
            if full_path.exists():
                self.passed.append(f"Test file exists: {test_file}")
            else:
                self.warnings.append(f"Missing test file: {test_file}")
                
    def _print_results(self):
        """Print validation results"""
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        if self.passed:
            print(f"\n✅ PASSED ({len(self.passed)} checks):")
            for item in self.passed[:10]:  # Show first 10
                print(f"   • {item}")
            if len(self.passed) > 10:
                print(f"   ... and {len(self.passed) - 10} more")
                
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
                
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
                
        print("\n" + "=" * 60)
        
        if not self.errors:
            print("✅ Repository validation PASSED!")
            print("   The unified system repository is ready for use.")
        else:
            print("❌ Repository validation FAILED!")
            print(f"   Please fix the {len(self.errors)} errors before proceeding.")
            
        print("=" * 60)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate unified system repository")
    parser.add_argument("--path", default=".", help="Repository path to validate")
    args = parser.parse_args()
    
    validator = RepositoryValidator(args.path)
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()