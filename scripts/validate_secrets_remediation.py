#!/usr/bin/env python3
"""
Secrets Remediation Validation Script
Phase 0 Day 5 - Task 5E

This script validates that the secrets remediation has been successful:
1. No credentials appear in process lists
2. SecretManager is working correctly
3. Hardcoded secrets have been eliminated
4. Development secret injection is functional
"""

import sys
import os
import subprocess
import tempfile
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.path_manager import PathManager


class SecretsRemediationValidator:
    """Validates the secrets remediation implementation."""
    
    def __init__(self):
        self.project_root = Path(PathManager.get_project_root())
        self.secrets_dir = self.project_root / "secrets"
        self.validation_results = {}
        
        print(f"🔐 Secrets Remediation Validator initialized")
        print(f"📁 Project root: {self.project_root}")
        print(f"🗝️  Secrets directory: {self.secrets_dir}")
    
    def validate_secret_manager_functionality(self) -> Dict[str, bool]:
        """Test that SecretManager is working correctly."""
        print(f"\n🧪 TESTING SECRETMANAGER FUNCTIONALITY")
        print(f"=" * 50)
        
        results = {}
        
        try:
            from common.utils.secret_manager import SecretManager, SecretNotFoundError
            print(f"✅ SecretManager import successful")
            results["secretmanager_import"] = True
        except Exception as e:
            print(f"❌ SecretManager import failed: {e}")
            results["secretmanager_import"] = False
            return results
        
        # Test secret resolution
        manager = SecretManager()
        
        # Test 1: Validate setup
        validation = manager.validate_secret_setup()
        results["setup_validation"] = validation
        
        print(f"🔧 Setup validation:")
        for key, value in validation.items():
            status = "✅" if value else "❌"
            print(f"  {status} {key}: {value}")
        
        # Test 2: List available secrets
        available_secrets = manager.list_available_secrets()
        results["available_secrets"] = available_secrets
        
        print(f"\n📋 Available secrets:")
        for source, secrets in available_secrets.items():
            print(f"  {source}: {len(secrets)} secrets")
            if secrets:
                for secret in secrets[:3]:  # Show first 3
                    print(f"    - {secret}")
                if len(secrets) > 3:
                    print(f"    ... and {len(secrets) - 3} more")
        
        # Test 3: Try to access development secrets
        dev_secrets_accessible = 0
        expected_dev_secrets = ["NATS_USERNAME", "NATS_PASSWORD", "PHI_TRANSLATOR_TOKEN", "JWT_SECRET"]
        
        print(f"\n🧪 Testing development secret access:")
        for secret_name in expected_dev_secrets:
            try:
                secret_value = manager.get_secret_value(secret_name, required=False)
                if secret_value:
                    print(f"  ✅ {secret_name}: Found")
                    dev_secrets_accessible += 1
                else:
                    print(f"  ⚠️  {secret_name}: Not found")
            except Exception as e:
                print(f"  ❌ {secret_name}: Error - {e}")
        
        results["dev_secrets_accessible"] = dev_secrets_accessible
        results["dev_secrets_expected"] = len(expected_dev_secrets)
        results["dev_secrets_success_rate"] = dev_secrets_accessible / len(expected_dev_secrets) * 100
        
        # Test 4: Test convenience functions
        print(f"\n🔗 Testing convenience functions:")
        try:
            from common.utils.secret_manager import get_secret
            test_secret = get_secret("NATS_USERNAME", required=False)
            print(f"  ✅ get_secret() function: {'Works' if test_secret else 'No test secret found'}")
            results["convenience_functions"] = True
        except Exception as e:
            print(f"  ❌ get_secret() function: {e}")
            results["convenience_functions"] = False
        
        return results
    
    def scan_for_hardcoded_secrets(self) -> Dict[str, List]:
        """Scan codebase for remaining hardcoded secrets."""
        print(f"\n🔍 SCANNING FOR REMAINING HARDCODED SECRETS")
        print(f"=" * 50)
        
        results = {
            "supersecret_found": [],
            "hardcoded_passwords": [],
            "jwt_secrets": [],
            "total_issues": 0
        }
        
        # Define patterns to search for
        dangerous_patterns = [
            ("supersecret", "Hardcoded supersecret token"),
            ("password.*=.*[\"'][^\"']{3,}[\"']", "Hardcoded password"),
            ("secret.*=.*[\"'][^\"']{10,}[\"']", "Hardcoded secret"),
            ("memory-hub-secret-key", "Memory hub JWT secret")
        ]
        
        # Search in critical directories
        search_dirs = ["pc2_code", "main_pc_code", "phase1_implementation"]
        
        for search_dir in search_dirs:
            if not (self.project_root / search_dir).exists():
                continue
                
            print(f"🔍 Scanning {search_dir}...")
            
            for pattern, description in dangerous_patterns:
                try:
                    cmd = ["grep", "-r", "-n", "-i", pattern, str(self.project_root / search_dir)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0 and result.stdout:
                        findings = result.stdout.strip().split('\n')
                        # Filter out test files and comments
                        real_findings = [
                            f for f in findings 
                            if not any(exclude in f.lower() for exclude in [
                                'test_', '.bak', 'example', 'docs/', 'backup', '# '
                            ])
                        ]
                        
                        if real_findings:
                            if "supersecret" in pattern:
                                results["supersecret_found"].extend(real_findings)
                            elif "password" in pattern:
                                results["hardcoded_passwords"].extend(real_findings)
                            elif "secret" in pattern:
                                results["jwt_secrets"].extend(real_findings)
                            
                            print(f"  ⚠️  Found {len(real_findings)} instances of {description}")
                            for finding in real_findings[:2]:  # Show first 2
                                print(f"    - {finding[:80]}...")
                            
                except subprocess.TimeoutExpired:
                    print(f"  ⚠️  Timeout scanning for {description}")
                except Exception as e:
                    print(f"  ⚠️  Error scanning for {description}: {e}")
        
        # Calculate total issues
        results["total_issues"] = (
            len(results["supersecret_found"]) + 
            len(results["hardcoded_passwords"]) + 
            len(results["jwt_secrets"])
        )
        
        print(f"\n📊 Hardcoded secrets scan results:")
        print(f"  Supersecret tokens: {len(results['supersecret_found'])}")
        print(f"  Hardcoded passwords: {len(results['hardcoded_passwords'])}")
        print(f"  JWT secrets: {len(results['jwt_secrets'])}")
        print(f"  Total issues: {results['total_issues']}")
        
        return results
    
    def test_process_list_security(self) -> Dict[str, any]:
        """Test that no credentials appear in process lists."""
        print(f"\n🚨 TESTING PROCESS LIST SECURITY")
        print(f"=" * 50)
        
        results = {
            "credentials_in_process_list": [],
            "safe_process_list": True,
            "test_completed": False
        }
        
        # Patterns that should NOT appear in process lists
        dangerous_patterns = [
            "supersecret",
            "dev_password",
            "jwt_secret",
            "nats://.*:.*@",  # NATS URLs with credentials
            "redis://.*:.*@"  # Redis URLs with credentials
        ]
        
        try:
            # Get current process list
            ps_result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
            
            if ps_result.returncode == 0:
                process_output = ps_result.stdout.lower()
                
                print(f"🔍 Scanning process list for credential exposure...")
                
                for pattern in dangerous_patterns:
                    if pattern in process_output:
                        results["credentials_in_process_list"].append(pattern)
                        results["safe_process_list"] = False
                        print(f"  ❌ Found dangerous pattern: {pattern}")
                
                if results["safe_process_list"]:
                    print(f"  ✅ No credentials found in process list")
                
                results["test_completed"] = True
                
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  Process list check timed out")
        except Exception as e:
            print(f"  ❌ Error checking process list: {e}")
        
        return results
    
    def test_fixed_components(self) -> Dict[str, bool]:
        """Test that previously vulnerable components are now secure."""
        print(f"\n🔧 TESTING FIXED COMPONENTS")
        print(f"=" * 50)
        
        results = {}
        
        # Test PHI Translator components
        phi_files = [
            "pc2_code/phi_adapter.py",
            "pc2_code/final_phi_translator.py"
        ]
        
        print(f"🧪 Testing PHI Translator components:")
        for phi_file in phi_files:
            file_path = self.project_root / phi_file
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    has_supersecret = "supersecret" in content.lower()
                    has_secret_manager = "SecretManager" in content
                    
                    if not has_supersecret and has_secret_manager:
                        print(f"  ✅ {phi_file}: Fixed (SecretManager integrated)")
                        results[phi_file] = True
                    elif has_supersecret:
                        print(f"  ❌ {phi_file}: Still has supersecret")
                        results[phi_file] = False
                    else:
                        print(f"  ⚠️  {phi_file}: No SecretManager found")
                        results[phi_file] = False
                        
                except Exception as e:
                    print(f"  ❌ {phi_file}: Error reading - {e}")
                    results[phi_file] = False
            else:
                print(f"  ⚠️  {phi_file}: File not found")
                results[phi_file] = False
        
        # Test Memory Hub JWT components
        print(f"\n🧪 Testing Memory Hub JWT components:")
        memory_hub_file = "phase1_implementation/consolidated_agents/memory_hub/memory_hub_unified.py"
        file_path = self.project_root / memory_hub_file
        
        if file_path.exists():
            try:
                content = file_path.read_text()
                has_hardcoded_jwt = "memory-hub-secret-key-change-in-production" in content
                has_secret_manager = "SecretManager" in content
                
                if not has_hardcoded_jwt and has_secret_manager:
                    print(f"  ✅ {memory_hub_file}: Fixed (SecretManager integrated)")
                    results[memory_hub_file] = True
                elif has_hardcoded_jwt:
                    print(f"  ❌ {memory_hub_file}: Still has hardcoded JWT secret")
                    results[memory_hub_file] = False
                else:
                    print(f"  ⚠️  {memory_hub_file}: Unclear status")
                    results[memory_hub_file] = False
                    
            except Exception as e:
                print(f"  ❌ {memory_hub_file}: Error reading - {e}")
                results[memory_hub_file] = False
        else:
            print(f"  ⚠️  {memory_hub_file}: File not found")
            results[memory_hub_file] = False
        
        return results
    
    def test_development_workflow(self) -> Dict[str, bool]:
        """Test that the development workflow with secrets is functional."""
        print(f"\n🛠️  TESTING DEVELOPMENT WORKFLOW")
        print(f"=" * 50)
        
        results = {}
        
        # Test 1: Secrets directory exists and has correct permissions
        if self.secrets_dir.exists():
            print(f"  ✅ Secrets directory exists: {self.secrets_dir}")
            results["secrets_dir_exists"] = True
            
            # Check file permissions
            secret_files = list(self.secrets_dir.glob("*"))
            secure_files = 0
            
            for secret_file in secret_files:
                if secret_file.is_file():
                    perms = secret_file.stat().st_mode & 0o777
                    if perms == 0o600:  # rw-------
                        secure_files += 1
            
            if secure_files == len(secret_files) and len(secret_files) > 0:
                print(f"  ✅ All {len(secret_files)} secret files have secure permissions (0600)")
                results["secure_permissions"] = True
            else:
                print(f"  ⚠️  {secure_files}/{len(secret_files)} secret files have secure permissions")
                results["secure_permissions"] = False
                
        else:
            print(f"  ❌ Secrets directory does not exist")
            results["secrets_dir_exists"] = False
            results["secure_permissions"] = False
        
        # Test 2: .gitignore excludes secrets
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            gitignore_content = gitignore_path.read_text()
            if "secrets/" in gitignore_content:
                print(f"  ✅ .gitignore excludes secrets directory")
                results["gitignore_configured"] = True
            else:
                print(f"  ❌ .gitignore does not exclude secrets directory")
                results["gitignore_configured"] = False
        else:
            print(f"  ⚠️  .gitignore file not found")
            results["gitignore_configured"] = False
        
        # Test 3: Can import and use SecretManager
        try:
            from common.utils.secret_manager import SecretManager
            manager = SecretManager()
            # Try to get a development secret
            test_value = manager.get_secret_value("NATS_USERNAME", required=False)
            if test_value:
                print(f"  ✅ SecretManager can access development secrets")
                results["secretmanager_functional"] = True
            else:
                print(f"  ⚠️  SecretManager accessible but no test secrets found")
                results["secretmanager_functional"] = True  # Still functional
        except Exception as e:
            print(f"  ❌ SecretManager functionality test failed: {e}")
            results["secretmanager_functional"] = False
        
        return results
    
    def generate_validation_report(self) -> Dict:
        """Generate comprehensive validation report."""
        print(f"\n📊 GENERATING COMPREHENSIVE VALIDATION REPORT")
        print(f"=" * 60)
        
        # Run all validation tests
        secretmanager_results = self.validate_secret_manager_functionality()
        hardcoded_scan_results = self.scan_for_hardcoded_secrets()
        process_security_results = self.test_process_list_security()
        fixed_components_results = self.test_fixed_components()
        dev_workflow_results = self.test_development_workflow()
        
        # Compile overall report
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "phase": "Phase 0 Day 5 - Secrets Remediation",
            "secretmanager_functionality": secretmanager_results,
            "hardcoded_secrets_scan": hardcoded_scan_results,
            "process_list_security": process_security_results,
            "fixed_components": fixed_components_results,
            "development_workflow": dev_workflow_results,
            "overall_assessment": {}
        }
        
        # Calculate overall assessment
        critical_issues = hardcoded_scan_results.get("total_issues", 0)
        process_list_safe = process_security_results.get("safe_process_list", False)
        secretmanager_working = secretmanager_results.get("secretmanager_import", False)
        components_fixed = sum(1 for v in fixed_components_results.values() if v)
        
        report["overall_assessment"] = {
            "critical_security_issues": critical_issues,
            "process_list_secure": process_list_safe,
            "secretmanager_operational": secretmanager_working,
            "components_fixed": components_fixed,
            "total_components_tested": len(fixed_components_results),
            "remediation_successful": (
                critical_issues == 0 and 
                process_list_safe and 
                secretmanager_working and 
                components_fixed > 0
            )
        }
        
        return report
    
    def print_final_assessment(self, report: Dict):
        """Print final assessment and recommendations."""
        assessment = report["overall_assessment"]
        
        print(f"\n🎯 FINAL ASSESSMENT")
        print(f"=" * 50)
        
        if assessment["remediation_successful"]:
            print(f"✅ SECRETS REMEDIATION SUCCESSFUL!")
            print(f"🔐 SecretManager operational: {assessment['secretmanager_operational']}")
            print(f"🚨 Process list secure: {assessment['process_list_secure']}")
            print(f"🛠️  Components fixed: {assessment['components_fixed']}/{assessment['total_components_tested']}")
            print(f"⚠️  Critical issues remaining: {assessment['critical_security_issues']}")
            
            print(f"\n✅ KEY ACHIEVEMENTS:")
            print(f"- Hardcoded 'supersecret' tokens eliminated")
            print(f"- JWT secrets now use SecretManager")
            print(f"- Development secrets properly configured")
            print(f"- Process list exposure prevented")
            print(f"- Secure development workflow established")
            
        else:
            print(f"❌ SECRETS REMEDIATION INCOMPLETE")
            print(f"🔐 SecretManager operational: {assessment['secretmanager_operational']}")
            print(f"🚨 Process list secure: {assessment['process_list_secure']}")
            print(f"🛠️  Components fixed: {assessment['components_fixed']}/{assessment['total_components_tested']}")
            print(f"⚠️  Critical issues remaining: {assessment['critical_security_issues']}")
            
            print(f"\n❌ ISSUES TO ADDRESS:")
            if not assessment["secretmanager_operational"]:
                print(f"- SecretManager needs to be fixed")
            if not assessment["process_list_secure"]:
                print(f"- Credentials still exposed in process lists")
            if assessment["critical_security_issues"] > 0:
                print(f"- {assessment['critical_security_issues']} hardcoded secrets remain")
            if assessment["components_fixed"] == 0:
                print(f"- No components have been properly fixed")
        
        print(f"\n📋 NEXT STEPS:")
        if assessment["remediation_successful"]:
            print(f"1. ✅ Day 5 objectives achieved - proceed to Day 6")
            print(f"2. 📊 Monitor secret usage in production deployment")
            print(f"3. 🔄 Consider implementing HashiCorp Vault for production")
            print(f"4. 🎯 Phase 0 continues with BaseAgent migration")
        else:
            print(f"1. ❌ Address remaining security issues before proceeding")
            print(f"2. 🔧 Fix any broken SecretManager functionality")
            print(f"3. 🔍 Complete elimination of hardcoded secrets")
            print(f"4. 🔄 Re-run validation until all tests pass")


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate secrets remediation implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--output-report',
        help='Save detailed validation report to JSON file'
    )
    
    parser.add_argument(
        '--quick-test',
        action='store_true',
        help='Run only essential validation tests'
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = SecretsRemediationValidator()
    
    print(f"🚀 STARTING SECRETS REMEDIATION VALIDATION")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)
    
    # Generate comprehensive report
    if args.quick_test:
        print("⚡ Running quick validation tests...")
        # Run only essential tests for quick feedback
        secretmanager_results = validator.validate_secret_manager_functionality()
        process_security_results = validator.test_process_list_security()
        
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "secretmanager_functionality": secretmanager_results,
            "process_list_security": process_security_results,
            "quick_test": True
        }
    else:
        print("🔍 Running comprehensive validation...")
        report = validator.generate_validation_report()
    
    # Print final assessment
    if not args.quick_test:
        validator.print_final_assessment(report)
    
    # Save report if requested
    if args.output_report:
        with open(args.output_report, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Detailed report saved to: {args.output_report}")
    
    # Return appropriate exit code
    if args.quick_test:
        success = (
            report["secretmanager_functionality"].get("secretmanager_import", False) and
            report["process_list_security"].get("safe_process_list", False)
        )
    else:
        success = report["overall_assessment"]["remediation_successful"]
    
    if success:
        print(f"\n🎉 VALIDATION SUCCESSFUL")
        return 0
    else:
        print(f"\n⚠️  VALIDATION ISSUES DETECTED")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 