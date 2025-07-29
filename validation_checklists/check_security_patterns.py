"""
Security Pattern Validation Checklist
Dynamic validation checks for security-related patterns in agents
"""

from typing import List, Dict, Any
from agent_validation_checklist import ValidationResult, AgentInfo
import os

def validate_agent(agent_info: AgentInfo, all_agents: Dict[str, AgentInfo]) -> List[ValidationResult]:
    """Validate security patterns in agent code"""
    results = []
    
    if not agent_info.script_path or not os.path.exists(agent_info.script_path):
        return results
    
    try:
        with open(agent_info.script_path, 'r') as f:
            content = f.read()
        
        # Check for hardcoded secrets
        secret_patterns = [
            'password', 'secret', 'token', 'key', 'credential',
            'api_key', 'private_key', 'access_token'
        ]
        
        for pattern in secret_patterns:
            if pattern in content.lower():
                # Check if it's hardcoded (not from env or config)
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if pattern in line.lower() and '=' in line:
                        # Check if it's not from environment or config
                        if not any(env_pattern in line.lower() for env_pattern in ['os.environ', 'getenv', 'config']):
                            results.append(ValidationResult(
                                check_name="Hardcoded Secrets",
                                status="FAIL",
                                message=f"Potential hardcoded secret on line {i}: {line.strip()}",
                                severity="CRITICAL"
                            ))
        
        # Check for proper input validation
        if 'input(' in content or 'raw_input(' in content:
            results.append(ValidationResult(
                check_name="Input Validation",
                status="WARNING",
                message="Direct input() calls detected - ensure proper validation",
                severity="MEDIUM"
            ))
        
        # Check for SQL injection patterns
        sql_patterns = ['execute(', 'executemany(', 'cursor.execute(']
        for pattern in sql_patterns:
            if pattern in content:
                # Check if parameters are used properly
                if '?' not in content and '%s' not in content and 'format(' not in content:
                    results.append(ValidationResult(
                        check_name="SQL Injection Prevention",
                        status="WARNING",
                        message="SQL execution detected without parameterized queries",
                        severity="HIGH"
                    ))
        
        # Check for file path validation
        file_operations = ['open(', 'file(', 'os.path.join(']
        for operation in file_operations:
            if operation in content:
                # Check for path traversal prevention
                if '..' in content and 'os.path.abspath(' not in content:
                    results.append(ValidationResult(
                        check_name="Path Traversal Prevention",
                        status="WARNING",
                        message="File operations detected without path validation",
                        severity="MEDIUM"
                    ))
        
        # Check for proper exception handling
        if 'except:' in content or 'except Exception:' in content:
            results.append(ValidationResult(
                check_name="Exception Handling",
                status="WARNING",
                message="Broad exception handling detected - consider specific exceptions",
                severity="MEDIUM"
            ))
        
        # Check for logging of sensitive data
        sensitive_patterns = ['password', 'token', 'secret', 'key']
        if 'logging.' in content or 'logger.' in content:
            for pattern in sensitive_patterns:
                if pattern in content:
                    results.append(ValidationResult(
                        check_name="Sensitive Data Logging",
                        status="WARNING",
                        message=f"Potential logging of sensitive data containing '{pattern}'",
                        severity="HIGH"
                    ))
        
        if not results:
            results.append(ValidationResult(
                check_name="Security Patterns",
                status="PASS",
                message="No obvious security issues detected",
                severity="LOW"
            ))
            
    except Exception as e:
        results.append(ValidationResult(
            check_name="Security Analysis",
            status="ERROR",
            message=f"Failed to analyze security patterns: {e}",
            severity="HIGH"
        ))
    
    return results 