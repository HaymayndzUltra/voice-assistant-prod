#!/usr/bin/env python3
"""
Test full intelligent execution for the three auth feature versions
"""

import json
from test_complete_system import execute_task_intelligently

def test_full_execution():
    """Test full intelligent execution for all three versions"""
    
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
    
    print("🚀 FULL INTELLIGENT EXECUTION TEST - USER AUTHENTICATION FEATURES\n")
    print("=" * 100)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{test_case['name']}")
        print("=" * 100)
        
        print(f"📋 Executing Task:")
        print(f"   {test_case['task'][:100]}...")
        
        print(f"\n🎯 INTELLIGENT EXECUTION RESULT:")
        print("─" * 50)
        
        try:
            result = execute_task_intelligently(test_case['task'])
            
            print(f"✅ Execution Type: {result.get('execution_type', 'Unknown')}")
            print(f"📝 Task ID: {result.get('task_id', 'None')}")
            print(f"📊 Status: {result.get('status', 'Unknown')}")
            print(f"📋 TODOs Added: {result.get('todos_added', 0)}")
            
            if 'complexity' in result:
                complexity = result['complexity']
                print(f"🧠 Complexity: {complexity.get('level')} (score: {complexity.get('score')})")
                print(f"💭 Reasoning: {', '.join(complexity.get('reasoning', []))}")
            
            if 'subtasks' in result:
                print(f"📋 Subtasks: {len(result['subtasks'])} created")
                for j, subtask in enumerate(result['subtasks'], 1):
                    print(f"   {j}. {subtask['description'][:60]}...")
                    print(f"      Status: {subtask['status']}, Duration: {subtask['duration']}min")
            
            if 'total_duration' in result:
                print(f"⏱️ Total Estimated Duration: {result['total_duration']} minutes")
            
            if 'message' in result:
                print(f"💬 Message: {result['message']}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print(f"\n" + "─" * 100)
    
    print(f"\n📊 SUMMARY COMPARISON:")
    print("=" * 100)
    print("This test shows how our intelligent system handles:")
    print("• Different language patterns (Filipino vs English vs Mixed)")
    print("• Sequential indicators (Una/First, Pagkatapos/Afterwards, Panghuli/Finally)")
    print("• Conditional logic (Kung/If, tama/correct, mali/incorrect)")
    print("• Complex task decomposition and TODO generation")
    print("• Multilingual task complexity analysis")

if __name__ == "__main__":
    test_full_execution()
