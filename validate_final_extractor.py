#!/usr/bin/env python3
"""
Hybrid-Aware Validation Script for ActionItemExtractor
Tests both fast rule-based parsing and powerful LLM-based parsing engines
"""

import json
import logging
import sys
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the hybrid extractor
try:
    from workflow_memory_intelligence_fixed import ActionItemExtractor
    logger.info("✅ Successfully imported ActionItemExtractor")
except ImportError as e:
    logger.error(f"❌ Failed to import ActionItemExtractor: {e}")
    sys.exit(1)

class HybridValidationTester:
    """Comprehensive tester for hybrid ActionItemExtractor"""
    
    def __init__(self):
        self.extractor = ActionItemExtractor()
        self.test_results = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive validation tests"""
        
        logger.info("🚀 Starting Hybrid ActionItemExtractor Validation...")
        
        # Define test cases with expected complexity
        test_cases = [
            # Simple tasks (should use Rule-Based engine)
            {
                "name": "Code Cleanup",
                "task": "Fix typo in the documentation",
                "expected_engine": "Rule-Based",
                "min_steps": 1,
                "category": "simple"
            },
            {
                "name": "Simple Update",
                "task": "Update comment in the header file",
                "expected_engine": "Rule-Based", 
                "min_steps": 1,
                "category": "simple"
            },
            {
                "name": "Quick Fix",
                "task": "Remove unused import statements",
                "expected_engine": "Rule-Based",
                "min_steps": 1,  
                "category": "simple"
            },
            
            # Complex tasks (should use LLM engine)
            {
                "name": "CI/CD Pipeline",
                "task": "Create a CI/CD pipeline with testing and deployment. If tests pass, deploy to staging. If tests fail, notify the team.",
                "expected_engine": "LLM",
                "min_steps": 3,
                "category": "complex"
            },
            {
                "name": "Database Migration", 
                "task": "Implement database migration system with rollback capability. If migration succeeds, update schema version. If migration fails, restore backup.",
                "expected_engine": "LLM",
                "min_steps": 4,
                "category": "complex"
            },
            {
                "name": "Authentication System",
                "task": "Build authentication system with login, registration, and password reset. Kung tama ang credentials, redirect sa dashboard. Kung mali, show error message.",
                "expected_engine": "LLM", 
                "min_steps": 5,
                "category": "complex"
            },
            {
                "name": "Parallel Processing",
                "task": "Implement data processing pipeline that runs validation and transformation simultaneously while logging progress",
                "expected_engine": "LLM",
                "min_steps": 3,
                "category": "complex"
            },
            
            # Medium complexity tasks (could go either way)
            {
                "name": "API Endpoint",
                "task": "Create REST API endpoint for user management",
                "expected_engine": "LLM",  # Due to 'create' complexity
                "min_steps": 2,
                "category": "medium"
            }
        ]
        
        # Run tests
        passed = 0
        failed = 0
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n📋 Test {i}/{len(test_cases)}: {test_case['name']}")
            result = self.run_single_test(test_case)
            
            if result["passed"]:
                passed += 1
                print(f"✅ PASS: {test_case['name']}")
            else:
                failed += 1
                print(f"❌ FAIL: {test_case['name']}")
                print(f"   Reason: {result['failure_reason']}")
            
            # Store detailed results
            self.test_results.append(result)
        
        # Summary
        total = len(test_cases)
        success_rate = (passed / total) * 100
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{success_rate:.1f}%",
            "test_results": self.test_results
        }
        
        logger.info(f"\n📊 VALIDATION SUMMARY:")
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        return summary
    
    def run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test case"""
        
        task = test_case["task"]
        expected_engine = test_case["expected_engine"]
        min_steps = test_case["min_steps"]
        
        try:
            # Get the engine that would be used
            actual_engine = self.extractor.get_parsing_engine_name(task)
            
            # Extract action items
            steps = self.extractor.extract_action_items(task)
            
            # Validate results
            passed = True
            failure_reasons = []
            
            # Check engine selection
            if actual_engine != expected_engine:
                passed = False
                failure_reasons.append(f"Expected {expected_engine} engine, got {actual_engine}")
            
            # Check minimum steps
            if len(steps) < min_steps:
                passed = False
                failure_reasons.append(f"Expected at least {min_steps} steps, got {len(steps)}")
            
            # Check that steps are not empty
            if not steps:
                passed = False
                failure_reasons.append("No steps extracted")
            
            # Check for meaningful steps
            empty_steps = [s for s in steps if not s.strip() or len(s.strip()) < 5]
            if empty_steps:
                passed = False
                failure_reasons.append(f"Found {len(empty_steps)} empty or too short steps")
            
            return {
                "test_name": test_case["name"],
                "task": task,
                "expected_engine": expected_engine,
                "actual_engine": actual_engine,
                "expected_min_steps": min_steps,
                "actual_steps": len(steps),
                "extracted_steps": steps,
                "passed": passed,
                "failure_reason": "; ".join(failure_reasons) if failure_reasons else None,
                "engine_match": actual_engine == expected_engine,
                "step_count_ok": len(steps) >= min_steps
            }
            
        except Exception as e:
            return {
                "test_name": test_case["name"],
                "task": task,
                "passed": False,
                "failure_reason": f"Exception during extraction: {str(e)}",
                "extracted_steps": [],
                "engine_match": False,
                "step_count_ok": False
            }
    
    def print_detailed_results(self):
        """Print detailed test results"""
        
        print("\n" + "="*80)
        print("DETAILED TEST RESULTS")
        print("="*80)
        
        for result in self.test_results:
            print(f"\n📋 {result['test_name']}")
            print(f"Task: {result['task'][:60]}...")
            
            if 'actual_engine' in result:
                engine_status = "✅" if result['engine_match'] else "❌"
                print(f"Engine: {engine_status} {result.get('expected_engine', 'N/A')} → {result.get('actual_engine', 'N/A')}")
            
            if 'actual_steps' in result:
                steps_status = "✅" if result['step_count_ok'] else "❌"
                print(f"Steps: {steps_status} {result.get('actual_steps', 0)} (min: {result.get('expected_min_steps', 0)})")
            
            if result.get('extracted_steps'):
                print("Extracted Steps:")
                for i, step in enumerate(result['extracted_steps'], 1):
                    print(f"  {i}. {step}")
            
            if not result['passed']:
                print(f"❌ FAILURE: {result.get('failure_reason', 'Unknown error')}")


def main():
    """Main validation function"""
    
    print("🧪 HYBRID ACTIONITEMEXTRACTOR VALIDATION")
    print("=" * 50)
    
    # Initialize tester
    tester = HybridValidationTester()
    
    # Run validation
    summary = tester.run_all_tests()
    
    # Print detailed results
    tester.print_detailed_results()
    
    # Final report
    print(f"\n🎯 FINAL VALIDATION REPORT")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Tests Passed: {summary['passed']}/{summary['total_tests']}")
    
    # Check if validation passed
    if summary['success_rate'] == "100.0%":
        print("🎉 ALL TESTS PASSED! Hybrid system is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Review the results above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
