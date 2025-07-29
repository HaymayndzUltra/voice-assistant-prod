#!/usr/bin/env python3
"""
Debug workflow extraction to see which methods are called
"""

from test_complete_system import ActionItemExtractor

def debug_workflow_extraction():
    """Debug which extraction methods are actually called"""
    extractor = ActionItemExtractor()
    
    test_cases = [
        {
            "name": "Simple Conditional",
            "task": "Kung walang error sa login, then redirect sa dashboard."
        },
        {
            "name": "Simple Parallel", 
            "task": "Execute these tasks in parallel: setup database connection, initialize cache system."
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"Task: {test_case['task']}")
        
        # Step 1: Analyze structure
        analysis = extractor._analyze_task_structure(test_case['task'])
        print(f"\n📊 Structure Analysis:")
        print(f"   Has Conditional: {analysis['has_conditional_logic']}")
        print(f"   Has Parallelism: {analysis['has_parallelism']}")
        print(f"   Has Dependencies: {analysis['has_dependencies']}")
        
        # Step 2: Test individual extraction methods
        print(f"\n🔍 Testing Individual Extractors:")
        
        if analysis['has_conditional_logic']:
            print("   📋 Calling _extract_conditional_workflow...")
            conditional_result = extractor._extract_conditional_workflow(test_case['task'], analysis)
            print(f"   ✅ Conditional Result ({len(conditional_result)} items):")
            for i, item in enumerate(conditional_result, 1):
                print(f"      {i}. {item}")
        
        if analysis['has_parallelism']:
            print("   🔀 Calling _extract_parallel_workflow...")
            parallel_result = extractor._extract_parallel_workflow(test_case['task'], analysis)
            print(f"   ✅ Parallel Result ({len(parallel_result)} items):")
            for i, item in enumerate(parallel_result, 1):
                print(f"      {i}. {item}")
        
        # Step 3: Test main extraction method
        print(f"\n📋 Main Extract Action Items:")
        main_result = extractor.extract_action_items(test_case['task'])
        print(f"   ✅ Main Result ({len(main_result)} items):")
        for i, item in enumerate(main_result, 1):
            print(f"      {i}. {item}")

if __name__ == "__main__":
    debug_workflow_extraction()
