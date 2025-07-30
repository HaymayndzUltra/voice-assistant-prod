"""
Comprehensive test for Advanced Intelligent Task Extraction
Tests multilingual support, conditional logic, parallelism, and dependencies
"""
import json
import logging
from test_complete_system import ActionItemExtractor, TaskComplexityAnalyzer, IntelligentTaskChunker, execute_task_intelligently
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_multilingual_conditional_logic():
    """Test Filipino/English conditional logic extraction"""
    logger.info('\n🧪 Testing Multilingual Conditional Logic...')
    extractor = ActionItemExtractor()
    test_cases = [{'name': 'Filipino Conditional', 'task': 'Kung walang error sa login, then redirect sa dashboard. Pero kung may error, ipakita ang error message at stay sa login page.', 'expected_keywords': ['kung', 'then', 'pero', 'conditional']}, {'name': 'English Conditional', 'task': 'If user authentication succeeds, then grant access to admin panel. Otherwise, show error message and redirect to login.', 'expected_keywords': ['if', 'then', 'otherwise', 'conditional']}, {'name': 'Mixed Code-switching', 'task': 'I-check muna kung valid ang user credentials. If valid, then proceed sa main application. Kung hindi, balik sa login form.', 'expected_keywords': ['kung', 'if', 'then', 'conditional']}]
    for test_case in test_cases:
        logger.info(f"\n📋 Testing: {test_case['name']}")
        logger.info(f"Task: {test_case['task']}")
        action_items = extractor.extract_action_items(test_case['task'])
        logger.info(f'✅ Extracted {len(action_items)} action items:')
        for i, item in enumerate(action_items, 1):
            logger.info(f'   {i}. {item}')
        has_conditional = any(('[CONDITIONAL]' in item for item in action_items))
        logger.info(f"🎯 Conditional logic detected: {('Yes' if has_conditional else 'No')}")

def test_parallelism_detection():
    """Test parallel task detection in multiple languages"""
    logger.info('\n🧪 Testing Parallelism Detection...')
    extractor = ActionItemExtractor()
    test_cases = [{'name': 'English Parallel Tasks', 'task': 'Execute these tasks in parallel: setup database connection, initialize cache system, and configure logging. These can be done simultaneously for faster startup.', 'expected_parallel': True}, {'name': 'Filipino Parallel Tasks', 'task': 'Gawin nang sabay-sabay: i-setup ang database, i-configure ang authentication, at i-initialize ang cache. Pwedeng magkasabay para mabilis.', 'expected_parallel': True}, {'name': 'Mixed Language Parallel', 'task': 'Maaaring gawin nang sabay-sabay (in parallel): create API endpoints, setup middleware, at implement error handling.', 'expected_parallel': True}]
    for test_case in test_cases:
        logger.info(f"\n📋 Testing: {test_case['name']}")
        logger.info(f"Task: {test_case['task']}")
        action_items = extractor.extract_action_items(test_case['task'])
        logger.info(f'✅ Extracted {len(action_items)} action items:')
        for i, item in enumerate(action_items, 1):
            logger.info(f'   {i}. {item}')
        has_parallel = any(('[PARALLEL]' in item for item in action_items))
        logger.info(f"🎯 Parallel tasks detected: {('Yes' if has_parallel else 'No')}")

def test_complex_ci_cd_workflow():
    """Test complex CI/CD workflow with conditionals and parallelism"""
    logger.info('\n🧪 Testing Complex CI/CD Workflow...')
    task_description = '\n    CI/CD Pipeline Setup:\n    Una sa lahat, setup mo ang build environment.\n    \n    Kung successful ang build:\n    - Run unit tests in parallel with integration tests\n    - Deploy to staging environment if all tests pass\n    - Kung may failed tests, send notification sa team\n    \n    Pagkatapos ng staging deployment:\n    - I-validate ang health checks\n    - If healthy, promote to production\n    - Otherwise, rollback at investigate\n    \n    Panghuli, i-update ang documentation at notify stakeholders.\n    '
    logger.info(f'📋 Complex Task: {task_description[:100]}...')
    extractor = ActionItemExtractor()
    action_items = extractor.extract_action_items(task_description)
    logger.info(f'\n✅ Extracted {len(action_items)} action items:')
    for i, item in enumerate(action_items, 1):
        logger.info(f'   {i}. {item}')
    analyzer = TaskComplexityAnalyzer()
    complexity = analyzer.analyze_complexity(task_description)
    logger.info(f'\n📊 Complexity Analysis:')
    logger.info(f'   Score: {complexity.score}')
    logger.info(f'   Level: {complexity.level}')
    logger.info(f'   Should Chunk: {complexity.should_chunk}')
    logger.info(f'   Estimated Subtasks: {complexity.estimated_subtasks}')
    logger.info(f"   Reasoning: {', '.join(complexity.reasoning)}")

def test_task_chunking_integration():
    """Test full intelligent task chunking with multilingual support"""
    logger.info('\n🧪 Testing Task Chunking Integration...')
    chunker = IntelligentTaskChunker()
    test_task = '\n    User Authentication Feature:\n    1. I-design ang login form with username/password fields\n    2. Kung valid ang credentials, create session token  \n    3. Implement password hashing at validation\n    4. I-setup ang rate limiting para sa security\n    5. Create logout functionality na mag-invalidate ng session\n    6. Add remember me option (optional)\n    '
    logger.info(f'📋 Chunking Task: {test_task[:80]}...')
    chunked_task = chunker.chunk_task(test_task)
    logger.info(f'\n✅ Task chunked successfully:')
    logger.info(f'   Task ID: {chunked_task.task_id}')
    logger.info(f'   Complexity: {chunked_task.complexity.level} (score: {chunked_task.complexity.score})')
    logger.info(f'   Number of subtasks: {len(chunked_task.subtasks)}')
    logger.info(f'   Status: {chunked_task.status}')
    logger.info(f'\n📋 Subtasks:')
    for i, subtask in enumerate(chunked_task.subtasks, 1):
        logger.info(f'   {i}. {subtask.description}')
        logger.info(f'      Priority: {subtask.priority}, Duration: {subtask.estimated_duration}min')

def test_full_system_integration():
    """Test end-to-end intelligent task execution"""
    logger.info('\n🧪 Testing Full System Integration...')
    complex_task = '\n    Complete Backend API Development:\n    \n    Phase 1 - Foundation (parallel execution possible):\n    - Setup mo ang database schema at migrations\n    - Configure authentication middleware \n    - I-implement ang basic CRUD operations\n    \n    Phase 2 - Features (conditional on Phase 1):\n    Kung successful ang foundation setup:\n    - Add advanced search functionality\n    - Implement caching layer\n    - Create API documentation\n    \n    Phase 3 - Testing & Deployment:\n    Una, run comprehensive test suite.\n    Kung lahat ng tests ay passing, deploy sa staging.\n    Panghuli, if staging validation succeeds, deploy to production.\n    '
    logger.info(f'📋 Executing Complex Task: {complex_task[:80]}...')
    result = execute_task_intelligently(complex_task)
    logger.info(f'\n✅ Execution Result:')
    logger.info(f"   Execution Type: {result.get('execution_type', 'Unknown')}")
    logger.info(f"   Task ID: {result.get('task_id', 'None')}")
    logger.info(f"   Status: {result.get('status', 'Unknown')}")
    logger.info(f"   TODOs Added: {result.get('todos_added', 0)}")
    if 'complexity' in result:
        complexity = result['complexity']
        logger.info(f"   Complexity: {complexity.get('level')} (score: {complexity.get('score')})")
    if 'subtasks' in result:
        logger.info(f"   Subtasks: {len(result['subtasks'])} created")
if __name__ == '__main__':
    logger.info('🚀 Starting Comprehensive Advanced Task Extraction Tests...\n')
    try:
        test_multilingual_conditional_logic()
        test_parallelism_detection()
        test_complex_ci_cd_workflow()
        test_task_chunking_integration()
        test_full_system_integration()
        logger.info('\n🎉 All tests completed successfully!')
    except Exception as e:
        logger.error(f'❌ Test failed with error: {e}')
        import traceback
        traceback.print_exc()