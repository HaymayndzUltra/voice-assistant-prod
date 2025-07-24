#!/usr/bin/env python3
"""
Safe Terminal Operations Wrapper
Provides timeout-protected terminal operations with automatic recovery
"""

import os
import sys
import time
import signal
import subprocess
import threading
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path

class TimeoutError(Exception):
    """Raised when operation times out"""
    pass

class SafeTerminalOps:
    def __init__(self, default_timeout: float = 30.0, max_retries: int = 3):
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.session_healthy = True
        self.operation_count = 0
        
    def _timeout_handler(self, signum, frame):
        """Signal handler for timeout"""
        raise TimeoutError("Operation timed out")
    
    def safe_run_command(self, 
                        command: str, 
                        timeout: Optional[float] = None,
                        retries: Optional[int] = None,
                        background: bool = False,
                        shell: bool = True) -> Dict[str, Any]:
        """
        Run command with timeout protection and retry logic
        
        Returns:
            Dict with 'success', 'returncode', 'stdout', 'stderr', 'error'
        """
        timeout = timeout or self.default_timeout
        retries = retries if retries is not None else self.max_retries
        
        for attempt in range(retries + 1):
            try:
                if background:
                    return self._run_background_command(command, timeout, shell)
                else:
                    return self._run_foreground_command(command, timeout, shell)
                    
            except TimeoutError:
                if attempt < retries:
                    print(f"⚠️ Command timed out (attempt {attempt + 1}/{retries + 1}), retrying...")
                    time.sleep(min(2 ** attempt, 10))  # Exponential backoff
                    continue
                else:
                    self.session_healthy = False
                    return {
                        'success': False,
                        'returncode': -1,
                        'stdout': '',
                        'stderr': f'Command timed out after {timeout}s',
                        'error': 'TIMEOUT'
                    }
            except Exception as e:
                if attempt < retries:
                    print(f"⚠️ Command failed (attempt {attempt + 1}/{retries + 1}): {e}")
                    time.sleep(min(2 ** attempt, 10))
                    continue
                else:
                    return {
                        'success': False,
                        'returncode': -1,
                        'stdout': '',
                        'stderr': str(e),
                        'error': 'EXCEPTION'
                    }
        
        return {
            'success': False,
            'returncode': -1,
            'stdout': '',
            'stderr': 'Max retries exceeded',
            'error': 'MAX_RETRIES'
        }
    
    def _run_foreground_command(self, command: str, timeout: float, shell: bool) -> Dict[str, Any]:
        """Run command in foreground with timeout"""
        self.operation_count += 1
        
        try:
            # Set up timeout handler
            old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(int(timeout))
            
            try:
                if shell:
                    result = subprocess.run(command, 
                                          shell=True, 
                                          capture_output=True, 
                                          text=True,
                                          timeout=timeout)
                else:
                    result = subprocess.run(command.split(), 
                                          capture_output=True, 
                                          text=True,
                                          timeout=timeout)
                
                return {
                    'success': result.returncode == 0,
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'error': None
                }
                
            finally:
                signal.alarm(0)  # Cancel timeout
                signal.signal(signal.SIGALRM, old_handler)  # Restore handler
                
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out after {timeout}s")
        except Exception as e:
            raise e
    
    def _run_background_command(self, command: str, timeout: float, shell: bool) -> Dict[str, Any]:
        """Run command in background with timeout monitoring"""
        result_container = {}
        
        def target():
            try:
                if shell:
                    proc = subprocess.Popen(command, 
                                          shell=True, 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE,
                                          text=True)
                else:
                    proc = subprocess.Popen(command.split(), 
                                          stdout=subprocess.PIPE, 
                                          stderr=subprocess.PIPE,
                                          text=True)
                
                stdout, stderr = proc.communicate()
                result_container['result'] = {
                    'success': proc.returncode == 0,
                    'returncode': proc.returncode,
                    'stdout': stdout,
                    'stderr': stderr,
                    'error': None
                }
            except Exception as e:
                result_container['result'] = {
                    'success': False,
                    'returncode': -1,
                    'stdout': '',
                    'stderr': str(e),
                    'error': 'EXCEPTION'
                }
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Thread is still running, command timed out
            raise TimeoutError(f"Background command timed out after {timeout}s")
        
        return result_container.get('result', {
            'success': False,
            'returncode': -1,
            'stdout': '',
            'stderr': 'Unknown error',
            'error': 'UNKNOWN'
        })
    
    def test_session_health(self) -> Dict[str, Any]:
        """Test if current session is healthy"""
        tests = {
            'echo_test': self.safe_run_command('echo "health_check"', timeout=5),
            'pwd_test': self.safe_run_command('pwd', timeout=5),
            'date_test': self.safe_run_command('date', timeout=5)
        }
        
        healthy = all(test['success'] for test in tests.values())
        
        return {
            'healthy': healthy,
            'session_healthy': self.session_healthy,
            'operation_count': self.operation_count,
            'tests': tests
        }
    
    def force_session_recovery(self) -> bool:
        """Attempt to recover unhealthy session"""
        print("🔄 Attempting session recovery...")
        
        recovery_commands = [
            'stty sane',  # Reset terminal settings
            'reset',      # Reset terminal state
            'clear',      # Clear screen
        ]
        
        recovered = False
        for cmd in recovery_commands:
            try:
                result = self.safe_run_command(cmd, timeout=10, retries=1)
                if result['success']:
                    recovered = True
                    break
            except Exception:
                continue
        
        if recovered:
            self.session_healthy = True
            print("✅ Session recovery successful")
        else:
            print("❌ Session recovery failed")
        
        return recovered
    
    def safe_git_operation(self, git_command: str, timeout: float = 60.0) -> Dict[str, Any]:
        """Special wrapper for git operations which are prone to hanging"""
        print(f"🔧 Git operation: {git_command}")
        
        # Test session health first
        health = self.test_session_health()
        if not health['healthy']:
            print("⚠️ Session unhealthy, attempting recovery...")
            if not self.force_session_recovery():
                return {
                    'success': False,
                    'returncode': -1,
                    'stdout': '',
                    'stderr': 'Session unhealthy and recovery failed',
                    'error': 'SESSION_UNHEALTHY'
                }
        
        # Run git command with extended timeout
        return self.safe_run_command(f"git {git_command}", timeout=timeout, retries=2)
    
    def safe_python_script(self, script_path: str, args: List[str] = None, timeout: float = 300.0) -> Dict[str, Any]:
        """Special wrapper for Python scripts which might consume resources"""
        args = args or []
        command = f"python3 {script_path} {' '.join(args)}"
        
        print(f"🐍 Python script: {script_path}")
        
        # Monitor resources before running
        try:
            import psutil
            memory_before = psutil.virtual_memory().percent
            if memory_before > 80:
                print(f"⚠️ High memory usage before script: {memory_before:.1f}%")
                return {
                    'success': False,
                    'returncode': -1,
                    'stdout': '',
                    'stderr': f'Memory usage too high: {memory_before:.1f}%',
                    'error': 'HIGH_MEMORY'
                }
        except ImportError:
            pass  # psutil not available
        
        return self.safe_run_command(command, timeout=timeout, retries=1)

def main():
    """Command line interface for safe terminal operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Safe Terminal Operations")
    parser.add_argument("command", nargs='?', help="Command to run")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries")
    parser.add_argument("--background", action="store_true", help="Run in background")
    parser.add_argument("--test-health", action="store_true", help="Test session health")
    parser.add_argument("--recover", action="store_true", help="Attempt session recovery")
    
    args = parser.parse_args()
    
    ops = SafeTerminalOps(default_timeout=args.timeout, max_retries=args.retries)
    
    if args.test_health:
        health = ops.test_session_health()
        print(f"Session Health: {'✅ HEALTHY' if health['healthy'] else '❌ UNHEALTHY'}")
        print(f"Operations run: {health['operation_count']}")
        for test_name, result in health['tests'].items():
            status = '✅' if result['success'] else '❌'
            print(f"  {test_name}: {status}")
    
    elif args.recover:
        ops.force_session_recovery()
    
    elif args.command:
        result = ops.safe_run_command(args.command, 
                                    timeout=args.timeout, 
                                    retries=args.retries,
                                    background=args.background)
        
        if result['success']:
            print("✅ Command successful")
            if result['stdout']:
                print("STDOUT:", result['stdout'])
        else:
            print(f"❌ Command failed: {result['error']}")
            if result['stderr']:
                print("STDERR:", result['stderr'])
        
        sys.exit(0 if result['success'] else 1)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 