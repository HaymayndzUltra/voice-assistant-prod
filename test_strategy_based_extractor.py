#!/usr/bin/env python3
"""
Comprehensive Test Suite for Strategy-Based ActionItemExtractor
Tests all command types and validates robustness across different scenarios
"""

import json
import logging
from typing import List, Dict, Any

# Import the new robust implementation
from workflow_memory_intelligence_robust import ActionItemExtractor, TaskComplexityAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestResult:
    """Holds test results for reporting"""
    def __init__(self, name: str, task: str, expected_count: int = None):
        self.name = name
        self.task = task
        self.expected_count = expected_count
        self.action_items: List[str] = []
        self.passed = False
        self.error = None
        self.analysis = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'passed': self.passed,
            'action_count': len(self.action_items),
            'expected_count': self.expected_count,
            'error': self.error,
            'analysis': self.analysis,
            'actions': self.action_items
        }


def run_comprehensive_test_suite():
    """Run comprehensive test suite for all command types"""
    
    print("🧠 COMPREHENSIVE TEST SUITE - ROBUST STRATEGY-BASED EXTRACTOR")
    print("=" * 80)
    
    extractor = ActionItemExtractor()
    analyzer = TaskComplexityAnalyzer()
    
    # Define all test cases
    test_cases = [
        # ========== USER AUTHENTICATION (3 LANGUAGES) ==========
        TestResult(
            name="🇵🇭 User Auth - Pure Filipino",
            task="""Gawin natin ang bagong user authentication feature. Una sa lahat, i-update ang schema ng database para magkaroon ng 'users' table na may 'username' at 'password_hash' na mga column. Pagkatapos, bumuo ka ng isang API endpoint na '/login' na tumatanggap ng POST requests. Kung tama ang credentials, dapat itong magbalik ng isang JWT. Kung mali, dapat itong magbalik ng 401 Unauthorized error. Panghuli, gumawa ka ng isang simpleng login form sa frontend para i-test ang bagong endpoint.""",
            expected_count=5  # 3 main steps + 2 conditionals
        ),
        
        TestResult(
            name="🇺🇸 User Auth - Pure English", 
            task="""Let's build the new user authentication feature. First of all, update the database schema to include a 'users' table with 'username' and 'password_hash' columns. Afterwards, create an API endpoint at '/login' that accepts POST requests. If the credentials are correct, it must return a JWT. If they are incorrect, it must return a 401 Unauthorized error. Finally, create a simple login form on the frontend to test the new endpoint.""",
            expected_count=5
        ),
        
        TestResult(
            name="🔀 User Auth - Taglish",
            task="""I-build natin ang bagong user auth feature. First, i-update mo ang database schema, magdagdag ka ng 'users' table na may 'username' at 'password_hash' columns. Then, gawa ka ng API endpoint, sa '/login', na tatanggap ng POST requests. Kapag tama ang credentials, kailangan mag-return ito ng JWT. Kung mali naman, dapat 401 Unauthorized error ang i-return. Lastly, gawa ka ng simpleng login form sa frontend para ma-test natin yung endpoint.""",
            expected_count=5
        ),
        
        # ========== CI/CD PIPELINE ==========
        TestResult(
            name="🚀 CI/CD Pipeline - Complex Mixed",
            task="""
            CI/CD Pipeline Setup:
            Una sa lahat, setup mo ang build environment.
            
            Kung successful ang build:
            - Run unit tests in parallel with integration tests
            - Deploy to staging environment if all tests pass
            - Kung may failed tests, send notification sa team
            
            Pagkatapos ng staging deployment:
            - I-validate ang health checks
            - If healthy, promote to production
            - Otherwise, rollback at investigate
            
            Panghuli, i-update ang documentation at notify stakeholders.
            """,
            expected_count=10  # Complex with conditionals and parallel tasks
        ),
        
        # ========== CODE CLEANUP ==========
        TestResult(
            name="🧹 Code Cleanup - Simple Sequential",
            task="""Perform comprehensive code cleanup. First, run the linter to identify all code style violations. Then, fix all linting errors and warnings. Next, remove all unused imports and dead code. Afterwards, update all deprecated function calls to their modern equivalents. Finally, run the test suite to ensure nothing broke during cleanup.""",
            expected_count=5
        ),
        
        TestResult(
            name="🧹 Code Cleanup - With Conditions",
            task="""Execute code cleanup workflow. Start by analyzing the codebase for issues. If there are linting errors, fix them automatically where possible. For complex violations that can't be auto-fixed, create a report for manual review. When all issues are resolved, commit the changes with a descriptive message. If any tests fail after cleanup, revert the changes and investigate.""",
            expected_count=6
        ),
        
        # ========== DATABASE MIGRATION ==========
        TestResult(
            name="🗄️ Database Migration - Hierarchical",
            task="""
            Database Migration Plan:
            1. Prepare migration scripts
               - Create backup of current database
               - Generate migration files for schema changes
               - Validate migration scripts syntax
            
            2. Execute migration in stages
               - Run migrations on development database first
               - If successful, proceed to staging
               - Monitor for any errors during execution
            
            3. Production deployment
               - Schedule maintenance window
               - Execute migrations with transaction support
               - Verify data integrity post-migration
               - Rollback if any critical errors occur
            """,
            expected_count=11
        ),
        
        # ========== PARALLEL EXECUTION ==========
        TestResult(
            name="⚡ Parallel Tasks",
            task="""Deploy microservices architecture. Build all services in parallel: user service, payment service, and notification service. While services are building, also set up the message queue and cache layer simultaneously. Once all components are ready, configure the API gateway to route between services. Run integration tests across all services in parallel. Finally, deploy everything to Kubernetes cluster.""",
            expected_count=7
        ),
        
        # ========== COMPLEX NESTED CONDITIONALS ==========
        TestResult(
            name="🔀 Complex Nested Logic",
            task="""
            Implement feature flag system:
            First, design the feature flag schema in the database.
            
            If using Redis:
                - Configure Redis cluster for high availability
                - If cluster setup fails, fall back to single instance
                - Set up cache invalidation strategy
            Else if using database:
                - Create feature_flags table with proper indexes
                - Implement caching layer to reduce DB load
                - If performance is poor, consider migrating to Redis
            
            Then implement the API:
                - Create endpoints for flag management
                - If admin role, allow full CRUD operations
                - If regular user, only allow read operations
                - Add rate limiting to prevent abuse
            
            Finally, integrate with frontend and add monitoring.
            """,
            expected_count=12
        )
    ]
    
    # Run all tests
    results = []
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"🎯 TEST: {test.name}")
        print(f"📋 Task: {test.task[:100]}...")
        
        try:
            # Analyze task structure
            analysis = extractor._analyze_task_structure(test.task)
            test.analysis = analysis
            
            # Extract action items
            action_items = extractor.extract_action_items(test.task)
            test.action_items = action_items
            
            # Analyze complexity
            complexity = analyzer.analyze_complexity(test.task)
            
            print(f"\n📊 ANALYSIS:")
            print(f"   • Type: {analysis}")
            print(f"   • Complexity: {complexity.level} (score: {complexity.score})")
            print(f"   • Action Items: {len(action_items)}")
            
            if test.expected_count:
                if len(action_items) == test.expected_count:
                    test.passed = True
                    print(f"   ✅ PASSED: Expected {test.expected_count} items, got {len(action_items)}")
                else:
                    test.passed = False
                    print(f"   ❌ FAILED: Expected {test.expected_count} items, got {len(action_items)}")
            else:
                test.passed = len(action_items) > 0
            
            print(f"\n📝 EXTRACTED ACTIONS:")
            for i, item in enumerate(action_items, 1):
                print(f"   {i}. {item}")
                
        except Exception as e:
            test.error = str(e)
            test.passed = False
            print(f"   ❌ ERROR: {e}")
        
        results.append(test)
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY REPORT")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"❌ Failed: {total-passed}/{total} ({(total-passed)/total*100:.1f}%)")
    
    # Detailed results table
    print("\n📋 DETAILED RESULTS:")
    print("-" * 80)
    print(f"{'Test Name':<30} {'Status':<10} {'Actions':<10} {'Expected':<10} {'Error':<20}")
    print("-" * 80)
    
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        actions = str(len(result.action_items))
        expected = str(result.expected_count) if result.expected_count else "N/A"
        error = result.error[:17] + "..." if result.error and len(result.error) > 20 else (result.error or "")
        
        print(f"{result.name:<30} {status:<10} {actions:<10} {expected:<10} {error:<20}")
    
    # Language consistency check for authentication tests
    print("\n🔍 LANGUAGE CONSISTENCY CHECK (User Authentication):")
    auth_results = [r for r in results if "User Auth" in r.name]
    
    if len(auth_results) == 3:
        filipino_items = auth_results[0].action_items
        english_items = auth_results[1].action_items
        taglish_items = auth_results[2].action_items
        
        # Normalize for comparison
        def normalize_for_comparison(items):
            return [item.lower().replace("create", "").replace("update", "").replace("build", "") 
                   for item in items]
        
        filipino_norm = normalize_for_comparison(filipino_items)
        english_norm = normalize_for_comparison(english_items)
        taglish_norm = normalize_for_comparison(taglish_items)
        
        if len(filipino_items) == len(english_items) == len(taglish_items):
            print("   ✅ All three languages produced the same number of action items")
            
            # Check for same logical steps
            core_steps_match = True
            for i in range(min(3, len(filipino_items))):  # Check first 3 core steps
                if "[CONDITIONAL]" not in filipino_items[i]:
                    # Very loose similarity check
                    if not (("database" in filipino_items[i].lower() and "database" in english_items[i].lower()) or
                           ("endpoint" in filipino_items[i].lower() and "endpoint" in english_items[i].lower()) or
                           ("form" in filipino_items[i].lower() and "form" in english_items[i].lower())):
                        core_steps_match = False
                        break
            
            if core_steps_match:
                print("   ✅ Core logical steps are consistent across languages")
            else:
                print("   ⚠️  Core logical steps may differ between languages")
        else:
            print(f"   ❌ Different item counts: Filipino={len(filipino_items)}, "
                  f"English={len(english_items)}, Taglish={len(taglish_items)}")
    
    # Export results to JSON
    results_json = {
        'summary': {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': f"{passed/total*100:.1f}%"
        },
        'tests': [r.to_dict() for r in results]
    }
    
    with open('test_results_robust.json', 'w') as f:
        json.dump(results_json, f, indent=2)
    
    print(f"\n💾 Results saved to: test_results_robust.json")
    
    return results


if __name__ == "__main__":
    results = run_comprehensive_test_suite()
    
    # Final verdict
    all_passed = all(r.passed for r in results)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! The robust strategy-based extractor is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Review the results above for details.")