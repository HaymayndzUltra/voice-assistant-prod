#!/usr/bin/env python3
"""
CORRECTED Language Robustness Test - Using ADVANCED intelligent extraction
"""

# Import from the CORRECT/FIXED file with advanced logic
from workflow_memory_intelligence_fixed import ActionItemExtractor, TaskComplexityAnalyzer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_corrected_language_test():
    """Test with the CORRECT advanced intelligent extraction logic"""
    
    print("🧠 CORRECTED LANGUAGE ROBUSTNESS & CONSISTENCY TEST")
    print("=" * 75)
    
    # Use the ADVANCED extractor with intelligent routing
    extractor = ActionItemExtractor()
    analyzer = TaskComplexityAnalyzer()
    
    test_cases = [
        {
            "name": "🇵🇭 PURONG FILIPINO",
            "task": "Gawin natin ang bagong user authentication feature. Una sa lahat, i-update ang schema ng database para magkaroon ng 'users' table na may 'username' at 'password_hash' na mga column. Pagkatapos, bumuo ka ng isang API endpoint na '/login' na tumatanggap ng POST requests. Kung tama ang credentials, dapat itong magbalik ng isang JWT. Kung mali, dapat itong magbalik ng 401 Unauthorized error. Panghuli, gumawa ka ng isang simpleng login form sa frontend para i-test ang bagong endpoint."
        },
        {
            "name": "🇺🇸 PURONG ENGLISH", 
            "task": "Let's build the new user authentication feature. First of all, update the database schema to include a 'users' table with 'username' and 'password_hash' columns. Afterwards, create an API endpoint at '/login' that accepts POST requests. If the credentials are correct, it must return a JWT. If they are incorrect, it must return a 401 Unauthorized error. Finally, create a simple login form on the frontend to test the new endpoint."
        },
        {
            "name": "🔀 TAGLISH",
            "task": "I-build natin ang bagong user auth feature. First, i-update mo ang database schema, magdagdag ka ng 'users' table na may 'username' at 'password_hash' columns. Then, gawa ka ng API endpoint, sa '/login', na tatanggap ng POST requests. Kapag tama ang credentials, kailangan mag-return ito ng JWT. Kung mali naman, dapat 401 Unauthorized error ang i-return. Lastly, gawa ka ng simpleng login form sa frontend para ma-test natin yung endpoint."
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🎯 TEST {i}: {test_case['name']}")
        print("-" * 50)
        
        # Test structure analysis FIRST
        analysis = extractor._analyze_task_structure(test_case['task'])
        
        print(f"🔍 INTELLIGENT ANALYSIS:")
        print(f"   • Conditional Logic: {analysis['has_conditional_logic']}")
        print(f"   • Parallelism: {analysis['has_parallelism']}")
        print(f"   • Dependencies: {analysis['has_dependencies']}")
        print(f"   • Complexity Score: {analysis['complexity_score']}")
        
        # Test the ADVANCED extraction
        action_items = extractor.extract_action_items(test_case['task'])
        
        print(f"📊 ANALYSIS: Extracted {len(action_items)} actionable steps.")
        
        # Check for proper tagging
        conditional_count = sum(1 for item in action_items if "[CONDITIONAL]" in item)
        parallel_count = sum(1 for item in action_items if "[PARALLEL]" in item)
        dependency_count = sum(1 for item in action_items if "[DEPENDENCY]" in item)
        
        print(f"🏷️ INTELLIGENT TAGS:")
        print(f"   • [CONDITIONAL]: {conditional_count}")
        print(f"   • [PARALLEL]: {parallel_count}")
        print(f"   • [DEPENDENCY]: {dependency_count}")
        
        print(f"✅ INTELLIGENT DECOMPOSED PLAN:")
        for j, item in enumerate(action_items, 1):
            print(f"  {j}. {item}")
    
    print(f"\n" + "=" * 75)
    print("✅ CORRECTED LANGUAGE TEST COMPLETE")
    print("📌 This version uses ADVANCED intelligent extraction with:")
    print("   • Conditional logic detection ([CONDITIONAL] tags)")
    print("   • Parallel task detection ([PARALLEL] tags)")
    print("   • Dependency analysis ([DEPENDENCY] tags)")
    print("   • Multilingual pattern matching (Filipino + English)")
    print("   • Intelligent routing based on task structure analysis")

if __name__ == "__main__":
    run_corrected_language_test()
