"""
Performance Pattern Validation Checklist
Dynamic validation checks for performance-related patterns in agents
"""

from typing import List, Dict, Any
from agent_validation_checklist import ValidationResult, AgentInfo
import os
import ast

def validate_agent(agent_info: AgentInfo, all_agents: Dict[str, AgentInfo]) -> List[ValidationResult]:
    """Validate performance patterns in agent code"""
    results = []
    
    if not agent_info.script_path or not os.path.exists(agent_info.script_path):
        return results
    
    try:
        with open(agent_info.script_path, 'r') as f:
            content = f.read()
        
        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content)
        except SyntaxError:
            results.append(ValidationResult(
                check_name="Syntax Analysis",
                status="ERROR",
                message="Syntax error in agent code",
                severity="HIGH"
            ))
            return results
        
        # Check for memory leaks - long-running loops without cleanup
        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                # Check for infinite loops
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    results.append(ValidationResult(
                        check_name="Infinite Loop",
                        status="WARNING",
                        message="Potential infinite loop detected",
                        severity="MEDIUM"
                    ))
        
        # Check for resource management
        resource_patterns = [
            'open(', 'socket(', 'zmq.Context', 'zmq.Socket',
            'threading.Thread', 'multiprocessing.Process'
        ]
        
        for pattern in resource_patterns:
            if pattern in content:
                # Check for proper cleanup
                cleanup_patterns = [
                    'close()', 'terminate()', 'join()', 'context.term()'
                ]
                has_cleanup = any(cleanup in content for cleanup in cleanup_patterns)
                
                if not has_cleanup:
                    results.append(ValidationResult(
                        check_name="Resource Cleanup",
                        status="WARNING",
                        message=f"Resource {pattern} may not be properly cleaned up",
                        severity="MEDIUM"
                    ))
        
        # Check for blocking operations in async code
        if 'async def' in content:
            blocking_patterns = [
                'time.sleep(', 'requests.get(', 'requests.post(',
                'subprocess.call(', 'subprocess.run('
            ]
            
            for pattern in blocking_patterns:
                if pattern in content:
                    results.append(ValidationResult(
                        check_name="Blocking Operations",
                        status="WARNING",
                        message=f"Blocking operation {pattern} in async code",
                        severity="MEDIUM"
                    ))
        
        # Check for inefficient data structures
        inefficient_patterns = [
            'list.append(' in content and 'for' in content,  # List concatenation in loops
            'str + ' in content and 'for' in content,  # String concatenation in loops
        ]
        
        if any(inefficient_patterns):
            results.append(ValidationResult(
                check_name="Data Structure Efficiency",
                status="WARNING",
                message="Potential inefficient data structure usage",
                severity="LOW"
            ))
        
        # Check for proper caching
        if 'requests.' in content or 'urllib.' in content:
            if 'cache' not in content and 'Cache' not in content:
                results.append(ValidationResult(
                    check_name="HTTP Caching",
                    status="WARNING",
                    message="HTTP requests detected without caching",
                    severity="LOW"
                ))
        
        # Check for proper error handling in performance-critical sections
        if 'zmq.' in content or 'socket.' in content:
            if 'try:' not in content or 'except' not in content:
                results.append(ValidationResult(
                    check_name="Network Error Handling",
                    status="WARNING",
                    message="Network operations without error handling",
                    severity="MEDIUM"
                ))
        
        # Check for proper timeout handling
        timeout_patterns = ['timeout', 'TIMEOUT']
        if any(pattern in content for pattern in ['zmq.', 'socket.', 'requests.']):
            if not any(timeout in content for timeout in timeout_patterns):
                results.append(ValidationResult(
                    check_name="Timeout Handling",
                    status="WARNING",
                    message="Network operations without timeout handling",
                    severity="MEDIUM"
                ))
        
        # Check for proper batch processing
        if 'for' in content and ('requests.' in content or 'zmq.' in content):
            if 'batch' not in content and 'Batch' not in content:
                results.append(ValidationResult(
                    check_name="Batch Processing",
                    status="INFO",
                    message="Consider batch processing for network operations",
                    severity="LOW"
                ))
        
        if not results:
            results.append(ValidationResult(
                check_name="Performance Patterns",
                status="PASS",
                message="No obvious performance issues detected",
                severity="LOW"
            ))
            
    except Exception as e:
        results.append(ValidationResult(
            check_name="Performance Analysis",
            status="ERROR",
            message=f"Failed to analyze performance patterns: {e}",
            severity="HIGH"
        ))
    
    return results 