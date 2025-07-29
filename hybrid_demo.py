#!/usr/bin/env python3
"""
Hybrid ActionItemExtractor Demo
Demonstrates the intelligent routing between rule-based and LLM parsing
"""

import sys
from workflow_memory_intelligence_fixed import ActionItemExtractor

def main():
    print("🎯 HYBRID ACTIONITEMEXTRACTOR DEMONSTRATION")
    print("=" * 60)
    
    # Initialize the extractor
    extractor = ActionItemExtractor()
    
    # Demo tasks
    demo_tasks = [
        {
            "name": "Simple Task (Rule-Based)",
            "task": "Fix typo in the documentation",
            "expected": "Rule-Based"
        },
        {
            "name": "Complex Task (LLM)",  
            "task": "Create authentication system with login validation. If credentials are correct, redirect to dashboard.",
            "expected": "LLM"
        },
        {
            "name": "API Task (LLM)",
            "task": "Create REST API endpoint for user management",
            "expected": "LLM"
        },
        {
            "name": "Database Task (LLM)",
            "task": "Implement database migration system with rollback capability",
            "expected": "LLM"
        }
    ]
    
    for i, demo in enumerate(demo_tasks, 1):
        print(f"\n📋 Demo {i}: {demo['name']}")
        print(f"Task: {demo['task']}")
        
        # Get complexity score and engine
        complexity = extractor._calculate_complexity_score(demo['task'])
        engine = extractor.get_parsing_engine_name(demo['task'])
        
        print(f"Complexity Score: {complexity}/10")
        print(f"Selected Engine: {engine}")
        print(f"Expected Engine: {demo['expected']}")
        
        # Check if routing is correct
        if engine == demo['expected']:
            print("✅ Correct engine selected!")
        else:
            print("❌ Unexpected engine selection")
        
        # Extract steps
        steps = extractor.extract_action_items(demo['task'])
        print(f"Extracted {len(steps)} steps:")
        for j, step in enumerate(steps, 1):
            print(f"  {j}. {step}")
        
        print("-" * 60)
    
    print("\n🎉 Hybrid system demonstration complete!")
    print("✅ System intelligently routes tasks based on complexity")
    print("⚡ Simple tasks → Fast rule-based parsing")  
    print("🧠 Complex tasks → Powerful LLM parsing (with fallback)")

if __name__ == "__main__":
    main()
