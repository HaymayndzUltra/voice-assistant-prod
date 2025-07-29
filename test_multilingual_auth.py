#!/usr/bin/env python3
"""
Test multilingual user authentication feature extraction
"""

import json
from test_complete_system import ActionItemExtractor, TaskComplexityAnalyzer, execute_task_intelligently

def test_multilingual_auth_features():
    """Test the three language versions of user auth feature"""
    
    extractor = ActionItemExtractor()
    analyzer = TaskComplexityAnalyzer()
    
    test_cases = [
        {
            "name": "🇵🇭 FILIPINO VERSION",
            "task": "Gawin natin ang bagong user authentication feature. Una sa lahat, i-update ang schema ng database para magkaroon ng 'users' table na may 'username' at 'password_hash' na mga column. Pagkatapos, bumuo ka ng isang API endpoint na '/login' na tumatanggap ng POST requests. Kung tama ang credentials, dapat itong magbalik ng isang JWT. Kung mali, dapat itong magbalik ng 401 Unauthorized error. Panghuli, gumawa ka ng isang simpleng login form sa frontend para i-test ang bagong endpoint."
        },
        {
            "name": "🇺🇸 ENGLISH VERSION", 
            "task": "Let's build the new user authentication feature. First of all, update the database schema to include a 'users' table with 'username' and 'password_hash' columns. Afterwards, create an API endpoint at '/login' that accepts POST requests. If the credentials are correct, it must return a JWT. If they are incorrect, it must return a 401 Unauthorized error. Finally, create a simple login form on the frontend to test the new endpoint."
        },
        {
            "name": "🔀 MIXED/CODE-SWITCHING VERSION",
            "task": "I-build natin ang bagong user auth feature. First, i-update mo ang database schema, magdagdag ka ng 'users' table na may 'username' at 'password_hash' columns. Then, gawa ka ng API endpoint, sa '/login', na tatanggap ng POST requests. Kapag tama ang credentials, kailangan mag-return ito ng JWT. Kung mali naman, dapat 401 Unauthorized error ang i-return. Lastly, gawa ka ng simpleng login form sa frontend para ma-test natin yung endpoint."
        }
    ]
    
    print("🧪 MULTILINGUAL USER AUTHENTICATION FEATURE EXTRACTION TEST\n")
    print("=" * 80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print("=" * 80)
        print(f"📋 Task Description:")
        print(f"   {test_case['task'][:100]}...")
        
        # Test structure analysis
        print(f"\n🔍 STRUCTURE ANALYSIS:")
        analysis = extractor._analyze_task_structure(test_case['task'])
        print(f"   • Has Conditional Logic: {analysis['has_conditional_logic']}")
        print(f"   • Has Parallelism: {analysis['has_parallelism']}")
        print(f"   • Has Dependencies: {analysis['has_dependencies']}")
        print(f"   • Complexity Score: {analysis['complexity_score']}")
        
        if analysis['conditional_patterns']:
            print(f"   • Conditional Patterns Found:")
            for pattern in analysis['conditional_patterns']:
                print(f"     - {pattern['type']}: {len(pattern['matches'])} matches")
        
        # Test complexity analysis
        print(f"\n📊 COMPLEXITY ANALYSIS:")
        complexity = analyzer.analyze_complexity(test_case['task'])
        print(f"   • Score: {complexity.score}")
        print(f"   • Level: {complexity.level}")
        print(f"   • Should Chunk: {complexity.should_chunk}")
        print(f"   • Estimated Subtasks: {complexity.estimated_subtasks}")
        print(f"   • Reasoning: {', '.join(complexity.reasoning)}")
        
        # Test action item extraction
        print(f"\n📋 ACTION ITEM EXTRACTION:")
        action_items = extractor.extract_action_items(test_case['task'])
        print(f"   ✅ Extracted {len(action_items)} action items:")
        for j, item in enumerate(action_items, 1):
            print(f"      {j}. {item}")
        
        # Check for special tags
        conditional_count = sum(1 for item in action_items if "[CONDITIONAL]" in item)
        parallel_count = sum(1 for item in action_items if "[PARALLEL]" in item)
        dependency_count = sum(1 for item in action_items if "[DEPENDENCY]" in item)
        
        print(f"\n🏷️ TAG ANALYSIS:")
        print(f"   • [CONDITIONAL] tags: {conditional_count}")
        print(f"   • [PARALLEL] tags: {parallel_count}")
        print(f"   • [DEPENDENCY] tags: {dependency_count}")
        
        print(f"\n" + "─" * 80)
    
    print(f"\n🎯 COMPARATIVE ANALYSIS:")
    print("=" * 80)
    
    results = []
    for test_case in test_cases:
        action_items = extractor.extract_action_items(test_case['task'])
        complexity = analyzer.analyze_complexity(test_case['task'])
        analysis = extractor._analyze_task_structure(test_case['task'])
        
        results.append({
            "version": test_case['name'],
            "total_items": len(action_items),
            "complexity_score": complexity.score,
            "complexity_level": complexity.level,
            "has_conditional": analysis['has_conditional_logic'],
            "has_dependencies": analysis['has_dependencies'],
            "conditional_tags": sum(1 for item in action_items if "[CONDITIONAL]" in item),
            "dependency_tags": sum(1 for item in action_items if "[DEPENDENCY]" in item)
        })
    
    print(f"{'Version':<35} {'Items':<6} {'Score':<6} {'Level':<8} {'Cond':<5} {'Deps':<5} {'[COND]':<7} {'[DEP]':<6}")
    print("─" * 80)
    for result in results:
        print(f"{result['version']:<35} {result['total_items']:<6} {result['complexity_score']:<6} {result['complexity_level']:<8} {str(result['has_conditional']):<5} {str(result['has_dependencies']):<5} {result['conditional_tags']:<7} {result['dependency_tags']:<6}")
    
    print(f"\n💡 INSIGHTS:")
    print("=" * 80)
    print("• All three versions should extract similar logical structure")
    print("• Filipino sequential indicators: 'Una sa lahat', 'Pagkatapos', 'Panghuli'")
    print("• English sequential indicators: 'First of all', 'Afterwards', 'Finally'")
    print("• Mixed version combines both language patterns")
    print("• Conditional logic: 'Kung tama/mali' vs 'If correct/incorrect' vs 'Kapag tama/mali'")
    print("• All should detect dependencies and sequential workflow structure")

if __name__ == "__main__":
    test_multilingual_auth_features()
