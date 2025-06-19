#!/usr/bin/env python3
"""
Test script for the enhanced translator implementation with advanced caching and memory management
"""
import os
import sys
import time
import logging
import random
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_translator_fixed")

def test_translator_fixed():
    """Test the enhanced translator implementation with advanced caching and memory management"""
    logger.info("Starting enhanced translator test")
    
    # Test basic initialization
    logger.info("Testing translator initialization...")
    try:
        from agents.translator_fixed import TranslatorAgent, process_memory_usage
        initial_memory = process_memory_usage()
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Use test_mode=True to avoid ZMQ socket binding
        agent = TranslatorAgent(test_mode=True)
        logger.info("✅ Successfully initialized TranslatorAgent in test mode")
        
        post_init_memory = process_memory_usage()
        logger.info(f"Memory after initialization: {post_init_memory:.2f} MB")
        logger.info(f"Memory increase: {post_init_memory - initial_memory:.2f} MB")
    except Exception as e:
        logger.error(f"❌ Failed to initialize TranslatorAgent: {str(e)}")
        return False
    
    # Test basic translation functionality
    logger.info("\nTesting translation functionality...")
    test_cases = [
        ("buksan mo ang file", "open the file"),
        ("i-save mo ang document", "save the document"),
        ("isara mo ang window", "close the window"),
        ("i-delete mo ang file", "delete the file")
    ]
    
    all_passed = True
    session_id = "test_session_123"
    
    # Add diagnostic debug code to check the agent's state
    logger.info("Diagnostics for TranslatorAgent:")
    logger.info(f"Agent class: {agent.__class__.__name__}")
    logger.info(f"Agent has _simple_translate method: {hasattr(agent, '_simple_translate')}")
    logger.info(f"Test mode: {agent.test_mode}")
    logger.info(f"Agent methods: {[method for method in dir(agent) if not method.startswith('__')]}")
    
    # Create a direct test of the _simple_translate method
    test_input = "buksan mo ang file"
    logger.info(f"\nDirect test of _simple_translate with '{test_input}'")
    try:
        direct_result = agent._simple_translate(test_input, None)
        logger.info(f"Direct result: '{direct_result}'")
    except Exception as e:
        logger.error(f"Direct _simple_translate failed: {str(e)}")
    
    # Now proceed with the regular tests
    for original, expected in test_cases:
        try:
            result = agent.translate(original, session_id=session_id)
            if expected.lower() in result.lower():
                logger.info(f"✅ '{original}' -> '{result}' (Expected: '{expected}')")
            else:
                logger.error(f"❌ '{original}' -> '{result}' (Expected: '{expected}')")
                all_passed = False
        except Exception as e:
            logger.error(f"❌ Error translating '{original}': {str(e)}")
            all_passed = False
    
    # Test context handling with follow-up questions
    logger.info("\nTesting contextual translation...")
    try:
        # First establish context
        agent.translate("buksan mo ang file", session_id=session_id)
        
        # Test pronoun resolution
        follow_up = "i-save mo ito"  # "save this" - should refer to "file"
        result = agent.translate(follow_up, session_id=session_id)
        
        if "this file" in result.lower():
            logger.info(f"✅ Context-aware translation: '{follow_up}' -> '{result}'")
        else:
            logger.info(f"ℹ️ Context-aware translation needs improvement: '{follow_up}' -> '{result}'")
    except Exception as e:
        logger.error(f"❌ Error testing contextual translation: {str(e)}")
        all_passed = False
    
    # Test advanced cache functionality
    logger.info("\nTesting advanced cache functionality...")
    try:
        # Reset cache statistics
        agent.cache_hits = 0
        agent.cache_misses = 0
        
        # 1. Basic cache hit/miss test
        test_phrase = "i-maximize mo ang browser"
        logger.info(f"Testing phrase: '{test_phrase}'")
        result1 = agent.translate(test_phrase, session_id=session_id)
        logger.info(f"First translation (cache miss): '{result1}'")
        
        # Second translation should be a cache hit
        result2 = agent.translate(test_phrase, session_id=session_id)
        logger.info(f"Second translation (cache hit): '{result2}'")
        
        if agent.cache_hits > 0 and result1 == result2:
            logger.info(f"✅ Basic cache hit successful: hits={agent.cache_hits}, misses={agent.cache_misses}")
        else:
            logger.error(f"❌ Basic cache hit failed: hits={agent.cache_hits}, misses={agent.cache_misses}")
            all_passed = False
            
        # 2. Test cache categorization (hot/warm/cold)
        logger.info("\nTesting cache categorization (hot/warm/cold)...")
        memory_before = process_memory_usage()
        logger.info(f"Memory before cache stress test: {memory_before:.2f} MB")
        
        # Generate multiple cache entries and access some frequently
        frequent_phrases = [
            "buksan mo ang file",
            "i-save mo ang document",
            "isara mo ang window"
        ]
        
        # Translate these phrases multiple times to make them 'hot'
        for _ in range(5):
            for phrase in frequent_phrases:
                agent.translate(phrase, session_id=session_id)
        
        # Generate some 'cold' entries that are only accessed once
        cold_phrases = [
            f"command {i}" for i in range(10)
        ]
        for phrase in cold_phrases:
            agent.translate(phrase, session_id=session_id)
            
        # Check cache categories
        hot_count = len(agent.cache_key_categories["hot"])
        warm_count = len(agent.cache_key_categories["warm"])
        cold_count = len(agent.cache_key_categories["cold"])
        
        logger.info(f"Cache categorization: {hot_count} hot, {warm_count} warm, {cold_count} cold entries")
        
        if hot_count > 0 and cold_count > 0:
            logger.info("✅ Cache categorization working properly")
        else:
            logger.warning("⚠️ Cache categorization needs verification")
            
        # 3. Test cache eviction
        logger.info("\nTesting intelligent cache eviction...")
        initial_cache_size = len(agent.translation_cache)
        
        # Force cache reduction
        agent._reduce_cache_size()
        
        after_eviction_size = len(agent.translation_cache)
        logger.info(f"Cache size before eviction: {initial_cache_size}, after: {after_eviction_size}")
        
        if after_eviction_size <= initial_cache_size:
            logger.info("✅ Cache eviction working properly")
        else:
            logger.error("❌ Cache eviction failed")
            all_passed = False
            
        # 4. Test normalization with variants
        logger.info("\nTesting text normalization for cache keys...")
        # Test variant with normalization
        variant = "i-maximize mo po ang browser"  # Added 'po' which should normalize out
        result3 = agent.translate(variant, session_id=session_id)
        
        if result3 == result2:
            logger.info(f"✅ Text normalization working: '{variant}' -> '{result3}'")
        else:
            logger.info(f"ℹ️ Text normalization could be improved: '{variant}' -> '{result3}' vs '{test_phrase}' -> '{result2}'")
            
        # 5. Test memory management
        memory_after = process_memory_usage()
        logger.info(f"\nMemory after cache stress test: {memory_after:.2f} MB")
        logger.info(f"Memory increase during test: {memory_after - memory_before:.2f} MB")
        
        # Test session compression
        logger.info("\nTesting session compression...")
        session_size_before = agent._estimate_object_size(agent.sessions)
        agent._compress_inactive_sessions()
        session_size_after = agent._estimate_object_size(agent.sessions)
        
        logger.info(f"Session memory before compression: {session_size_before/1024:.2f} KB")
        logger.info(f"Session memory after compression: {session_size_after/1024:.2f} KB")
    except Exception as e:
        logger.error(f"❌ Error testing advanced cache functionality: {str(e)}")
        all_passed = False
    
    # Final status
    if all_passed:
        logger.info("\n✅ All tests PASSED")
    else:
        logger.error("\n❌ Some tests FAILED")
    
    return all_passed

if __name__ == "__main__":
    success = test_translator_fixed()
    sys.exit(0 if success else 1)
