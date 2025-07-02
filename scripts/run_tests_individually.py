#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to execute tests one by one and save results after each test.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

# Define colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def find_test_files():
    """Find all test files in the repository."""
    main_pc_tests = []
    pc2_tests = []
    
    # Find all test files in main_pc_code
    for root, _, files in os.walk('main_pc_code'):
        # Skip archive and backup directories
        if any(x in root for x in ['MAINPCRESTOREFROMPC2', '_trash', 'archive']):
            continue
        
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                main_pc_tests.append(os.path.join(root, file))
    
    # Find all test files in pc2_code
    for root, _, files in os.walk('pc2_code'):
        # Skip archive directories
        if 'archive' in root:
            continue
        
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                pc2_tests.append(os.path.join(root, file))
    
    return sorted(main_pc_tests), sorted(pc2_tests)

def run_test(test_file):
    """Run a single test file and return the result."""
    print(f"{Colors.BLUE}Running test: {test_file}{Colors.ENDC}")
    
    try:
        # Run the test using unittest
        result = subprocess.run(
            [sys.executable, '-m', 'unittest', test_file],
            capture_output=True,
            text=True,
            timeout=20  # Set a timeout of 20 seconds per test
        )
        
        if result.returncode == 0:
            status = "PASSED"
            output = result.stdout
            color = Colors.GREEN
            print(f"{Colors.GREEN}✓ PASSED{Colors.ENDC}")
        else:
            status = "FAILED"
            output = result.stderr if result.stderr else result.stdout
            color = Colors.RED
            print(f"{Colors.RED}✗ FAILED{Colors.ENDC}")
            
        return {
            'file': test_file,
            'status': status,
            'output': output,
            'color': color
        }
    except subprocess.TimeoutExpired:
        print(f"{Colors.YELLOW}⚠ TIMEOUT{Colors.ENDC}")
        return {
            'file': test_file,
            'status': "TIMEOUT",
            'output': "Test execution timed out after 20 seconds",
            'color': Colors.YELLOW
        }
    except Exception as e:
        print(f"{Colors.RED}✗ ERROR: {str(e)}{Colors.ENDC}")
        return {
            'file': test_file,
            'status': "ERROR",
            'output': str(e),
            'color': Colors.RED
        }

def save_intermediate_results(results, timestamp):
    """Save intermediate results to a JSON file."""
    results_dir = Path('test_reports')
    results_dir.mkdir(exist_ok=True)
    
    # Convert results to a serializable format
    serializable_results = []
    for result in results:
        serializable_results.append({
            'file': result['file'],
            'status': result['status'],
            'output': result['output']
        })
    
    # Save to JSON file
    results_file = results_dir / f'test_results_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    return results_file

def run_all_tests():
    """Run all tests and generate a report."""
    main_pc_tests, pc2_tests = find_test_files()
    
    print(f"{Colors.HEADER}Found {len(main_pc_tests)} tests in main_pc_code{Colors.ENDC}")
    print(f"{Colors.HEADER}Found {len(pc2_tests)} tests in pc2_code{Colors.ENDC}")
    print(f"{Colors.HEADER}Total: {len(main_pc_tests) + len(pc2_tests)} tests{Colors.ENDC}")
    print("\nStarting test execution...\n")
    
    results = []
    start_time = time.time()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Run main_pc_code tests
    print(f"{Colors.HEADER}Running main_pc_code tests...{Colors.ENDC}")
    for i, test_file in enumerate(main_pc_tests):
        result = run_test(test_file)
        results.append(result)
        
        # Save intermediate results after every 5 tests
        if (i + 1) % 5 == 0 or i == len(main_pc_tests) - 1:
            save_intermediate_results(results, timestamp)
            print(f"Intermediate results saved. Progress: {i+1}/{len(main_pc_tests) + len(pc2_tests)}")
    
    # Run pc2_code tests
    print(f"\n{Colors.HEADER}Running pc2_code tests...{Colors.ENDC}")
    for i, test_file in enumerate(pc2_tests):
        result = run_test(test_file)
        results.append(result)
        
        # Save intermediate results after every 5 tests
        if (i + 1) % 5 == 0 or i == len(pc2_tests) - 1:
            save_intermediate_results(results, timestamp)
            print(f"Intermediate results saved. Progress: {len(main_pc_tests) + i+1}/{len(main_pc_tests) + len(pc2_tests)}")
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return results, execution_time, timestamp

def generate_report(results, execution_time, timestamp):
    """Generate a comprehensive test report."""
    passed = [r for r in results if r['status'] == 'PASSED']
    failed = [r for r in results if r['status'] == 'FAILED']
    timeout = [r for r in results if r['status'] == 'TIMEOUT']
    error = [r for r in results if r['status'] == 'ERROR']
    
    # Create report directory if it doesn't exist
    report_dir = Path('test_reports')
    report_dir.mkdir(exist_ok=True)
    
    # Generate report filename
    report_file = report_dir / f'test_report_{timestamp}.txt'
    
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("SYSTEM REMEDIATION - PHASE 3.1: TEST-FIX CYCLE (ITERATION 1)\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Test Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Execution Time: {execution_time:.2f} seconds\n\n")
        
        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Tests: {len(results)}\n")
        f.write(f"Passed: {len(passed)}\n")
        f.write(f"Failed: {len(failed)}\n")
        f.write(f"Timeout: {len(timeout)}\n")
        f.write(f"Error: {len(error)}\n\n")
        
        f.write("DETAILED RESULTS\n")
        f.write("-" * 80 + "\n")
        
        # Write all test results
        for result in results:
            f.write(f"{result['file']} - [STATUS: {result['status']}]\n")
            
            # Include output for failed tests
            if result['status'] != 'PASSED':
                f.write("\nError Details:\n")
                f.write("-" * 40 + "\n")
                f.write(result['output'])
                f.write("\n" + "-" * 40 + "\n\n")
    
    # Print summary to console
    print(f"\n{Colors.HEADER}TEST EXECUTION COMPLETE{Colors.ENDC}")
    print(f"Total Tests: {len(results)}")
    print(f"{Colors.GREEN}Passed: {len(passed)}{Colors.ENDC}")
    print(f"{Colors.RED}Failed: {len(failed)}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Timeout: {len(timeout)}{Colors.ENDC}")
    print(f"{Colors.RED}Error: {len(error)}{Colors.ENDC}")
    print(f"\nExecution Time: {execution_time:.2f} seconds")
    print(f"\nDetailed report saved to: {report_file}")
    
    return report_file

def print_test_results(results):
    """Print test results to the console in a format suitable for copying."""
    print("\n" + "=" * 80)
    print("TEST RESULTS - COPY-FRIENDLY FORMAT")
    print("=" * 80 + "\n")
    
    # Count results by status
    passed = [r for r in results if r['status'] == 'PASSED']
    failed = [r for r in results if r['status'] == 'FAILED']
    timeout = [r for r in results if r['status'] == 'TIMEOUT']
    error = [r for r in results if r['status'] == 'ERROR']
    
    print(f"SUMMARY: {len(passed)} PASSED, {len(failed)} FAILED, {len(timeout)} TIMEOUT, {len(error)} ERROR\n")
    
    # Print failed tests first for visibility
    if failed or timeout or error:
        print("FAILING TESTS:")
        for result in results:
            if result['status'] != 'PASSED':
                print(f"{result['file']} - [STATUS: {result['status']}]")
        print("\n")
    
    # Print all results
    print("ALL TEST RESULTS:")
    for result in results:
        print(f"{result['file']} - [STATUS: {result['status']}]")

def main():
    """Main function."""
    print(f"{Colors.HEADER}Starting System Remediation - Phase 3.1: Test-Fix Cycle (Iteration 1){Colors.ENDC}")
    
    results, execution_time, timestamp = run_all_tests()
    report_file = generate_report(results, execution_time, timestamp)
    print_test_results(results)
    
    # Return success if all tests passed
    passed = all(r['status'] == 'PASSED' for r in results)
    return 0 if passed else 1

if __name__ == '__main__':
    sys.exit(main()) 