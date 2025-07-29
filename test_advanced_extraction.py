#!/usr/bin/env python3
"""
Comprehensive test for Advanced Intelligent Task Extraction
Tests multilingual support, conditional logic, parallelism, and dependencies
"""

import json
import logging
from test_complete_system import (
    ActionItemExtractor, 
    TaskComplexityAnalyzer,
    IntelligentTaskChunker,
    execute_task_intelligently
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_multilingual_conditional_logic():
    """Test Filipino/English conditional logic extraction"""
    print("\n🧪 Testing Multilingual Conditional Logic...")
    
    extractor = ActionItemExtractor()
    
    test_cases = [
        {
            "name": "Filipino Conditional",
            "task": "Kung walang error sa login, then redirect sa dashboard. Pero kung may error, ipakita ang error message at stay sa login page.",
            "expected_keywords": ["kung", "then", "pero", "conditional"]
        },
        {
            "name": "English Conditional", 
            "task": "If user authentication succeeds, then grant access to admin panel. Otherwise, show error message and redirect to login.",
            "expected_keywords": ["if", "then", "otherwise", "conditional"]
        },
        {
            "name": "Mixed Code-switching",
            "task": "I-check muna kung valid ang user credentials. If valid, then proceed sa main application. Kung hindi, balik sa login form.",
            "expected_keywords": ["kung", "if", "then", "conditional"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        print(f"Task: {test_case['task']}")
        
        action_items = extractor.extract_action_items(test_case['task'])
        print(f"✅ Extracted {len(action_items)} action items:")
        for i, item in enumerate(action_items, 1):
            print(f"   {i}. {item}")
        
        # Check if conditional patterns were detected
        has_conditional = any("[CONDITIONAL]" in item for item in action_items)
        print(f"🎯 Conditional logic detected: {'Yes' if has_conditional else 'No'}")


def test_parallelism_detection():
    """Test parallel task detection in multiple languages"""
    print("\n🧪 Testing Parallelism Detection...")
    
    extractor = ActionItemExtractor()
    
    test_cases = [
        {
            "name": "English Parallel Tasks",
            "task": "Execute these tasks in parallel: setup database connection, initialize cache system, and configure logging. These can be done simultaneously for faster startup.",
            "expected_parallel": True
        },
        {
            "name": "Filipino Parallel Tasks", 
            "task": "Gawin nang sabay-sabay: i-setup ang database, i-configure ang authentication, at i-initialize ang cache. Pwedeng magkasabay para mabilis.",
            "expected_parallel": True
        },
        {
            "name": "Mixed Language Parallel",
            "task": "Maaaring gawin nang sabay-sabay (in parallel): create API endpoints, setup middleware, at implement error handling.",
            "expected_parallel": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing: {test_case['name']}")
        print(f"Task: {test_case['task']}")
        
        action_items = extractor.extract_action_items(test_case['task'])
        print(f"✅ Extracted {len(action_items)} action items:")
        for i, item in enumerate(action_items, 1):
            print(f"   {i}. {item}")
        
        # Check if parallel patterns were detected
        has_parallel = any("[PARALLEL]" in item for item in action_items)
        print(f"🎯 Parallel tasks detected: {'Yes' if has_parallel else 'No'}")


def test_complex_ci_cd_workflow():
    """Test complex CI/CD workflow with conditionals and parallelism"""
    print("\n🧪 Testing Complex CI/CD Workflow...")
    
    task_description = """
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
    """
    
    print(f"📋 Complex Task: {task_description[:100]}...")
    
    # Test with ActionItemExtractor
    extractor = ActionItemExtractor()
    action_items = extractor.extract_action_items(task_description)
    
    print(f"\n✅ Extracted {len(action_items)} action items:")
    for i, item in enumerate(action_items, 1):
        print(f"   {i}. {item}")
    
    # Test complexity analysis
    analyzer = TaskComplexityAnalyzer()
    complexity = analyzer.analyze_complexity(task_description)
    
    print(f"\n📊 Complexity Analysis:")
    print(f"   Score: {complexity.score}")
    print(f"   Level: {complexity.level}")
    print(f"   Should Chunk: {complexity.should_chunk}")
    print(f"   Estimated Subtasks: {complexity.estimated_subtasks}")
    print(f"   Reasoning: {', '.join(complexity.reasoning)}")


def test_task_chunking_integration():
    """Test full intelligent task chunking with multilingual support"""
    print("\n🧪 Testing Task Chunking Integration...")
    
    chunker = IntelligentTaskChunker()
    
    test_task = """
    User Authentication Feature:
    1. I-design ang login form with username/password fields
    2. Kung valid ang credentials, create session token  
    3. Implement password hashing at validation
    4. I-setup ang rate limiting para sa security
    5. Create logout functionality na mag-invalidate ng session
    6. Add remember me option (optional)
    """
    
    print(f"📋 Chunking Task: {test_task[:80]}...")
    
    chunked_task = chunker.chunk_task(test_task)
    
    print(f"\n✅ Task chunked successfully:")
    print(f"   Task ID: {chunked_task.task_id}")
    print(f"   Complexity: {chunked_task.complexity.level} (score: {chunked_task.complexity.score})")
    print(f"   Number of subtasks: {len(chunked_task.subtasks)}")
    print(f"   Status: {chunked_task.status}")
    
    print(f"\n📋 Subtasks:")
    for i, subtask in enumerate(chunked_task.subtasks, 1):
        print(f"   {i}. {subtask.description}")
        print(f"      Priority: {subtask.priority}, Duration: {subtask.estimated_duration}min")


def test_full_system_integration():
    """Test end-to-end intelligent task execution"""
    print("\n🧪 Testing Full System Integration...")
    
    complex_task = """
    Complete Backend API Development:
    
    Phase 1 - Foundation (parallel execution possible):
    - Setup mo ang database schema at migrations
    - Configure authentication middleware 
    - I-implement ang basic CRUD operations
    
    Phase 2 - Features (conditional on Phase 1):
    Kung successful ang foundation setup:
    - Add advanced search functionality
    - Implement caching layer
    - Create API documentation
    
    Phase 3 - Testing & Deployment:
    Una, run comprehensive test suite.
    Kung lahat ng tests ay passing, deploy sa staging.
    Panghuli, if staging validation succeeds, deploy to production.
    """
    
    print(f"📋 Executing Complex Task: {complex_task[:80]}...")
    
    result = execute_task_intelligently(complex_task)
    
    print(f"\n✅ Execution Result:")
    print(f"   Execution Type: {result.get('execution_type', 'Unknown')}")
    print(f"   Task ID: {result.get('task_id', 'None')}")
    print(f"   Status: {result.get('status', 'Unknown')}")
    print(f"   TODOs Added: {result.get('todos_added', 0)}")
    
    if 'complexity' in result:
        complexity = result['complexity']
        print(f"   Complexity: {complexity.get('level')} (score: {complexity.get('score')})")
    
    if 'subtasks' in result:
        print(f"   Subtasks: {len(result['subtasks'])} created")


if __name__ == "__main__":
    print("🚀 Starting Comprehensive Advanced Task Extraction Tests...\n")
    
    try:
        test_multilingual_conditional_logic()
        test_parallelism_detection()
        test_complex_ci_cd_workflow()
        test_task_chunking_integration()
        test_full_system_integration()
        
        print("\n🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
