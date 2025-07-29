#!/usr/bin/env python3
"""
Debug test to see what patterns are being detected
"""

import re
from test_complete_system import ActionItemExtractor

def debug_pattern_detection():
    """Debug what patterns are detected"""
    extractor = ActionItemExtractor()
    
    test_cases = [
        "Kung walang error sa login, then redirect sa dashboard.",
        "If user authentication succeeds, then grant access to admin panel.", 
        "Execute these tasks in parallel: setup database connection, initialize cache system.",
        "Gawin nang sabay-sabay: i-setup ang database, i-configure ang authentication."
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case}")
        
        # Test pattern detection
        analysis = extractor._analyze_task_structure(test_case)
        print(f"📊 Analysis Result:")
        print(f"   Has Conditional: {analysis['has_conditional_logic']}")
        print(f"   Has Parallelism: {analysis['has_parallelism']}")  
        print(f"   Has Dependencies: {analysis['has_dependencies']}")
        print(f"   Conditional Patterns: {analysis['conditional_patterns']}")
        print(f"   Parallel Sections: {analysis['parallel_sections']}")
        
        # Test individual patterns
        print(f"🔍 Individual Pattern Tests:")
        
        # Test conditional patterns
        for pattern_name, pattern in extractor.conditional_patterns.items():
            matches = re.findall(pattern, test_case, re.IGNORECASE)
            if matches:
                print(f"   ✅ {pattern_name}: {matches}")
        
        # Test parallelism indicators  
        text_lower = test_case.lower()
        for indicator in extractor.parallelism_indicators:
            if indicator in text_lower:
                print(f"   🔀 Parallelism: '{indicator}' found")
        
        # Test extraction result
        result = extractor.extract_action_items(test_case)
        print(f"📋 Final Extraction ({len(result)} items):")
        for j, item in enumerate(result, 1):
            print(f"   {j}. {item}")

if __name__ == "__main__":
    debug_pattern_detection()
