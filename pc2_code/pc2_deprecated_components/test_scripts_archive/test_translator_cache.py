#!/usr/bin/env python3
"""
Test script for translation cache system in the TranslatorAgent.
This demonstrates the enhanced caching capabilities with lower thresholds,
text normalization, and persistent storage.
"""

import sys
import time
import logging
import json
import zmq
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_translator_cache")

def test_cache_performance():
    """Test the translator agent's caching system with slight text variations"""
    # Connect to translator agent
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5563")  # Default translator agent port
    
    # Create a session ID for this test
    session_id = f"cache_test_{int(time.time())}"
    
    # Define test phrases with slight variations
    test_phrases = [
        # Group 1: Original phrases that should be cached
        "buksan mo ang file",
        "i-save mo ang document",
        "magsimula ng bagong project",
        "isara mo ang window",
        "i-maximize mo ang browser",
        
        # Group 2: Variations that should hit cache due to normalization
        "Buksan mo ang file",  # Capitalization
        "i-save mo ang document.",  # Punctuation
        "magsimula ng bagong project po",  # Politeness marker
        "isara mo ang window ba?",  # Question marker
        "i-maximize mo nga ang browser",  # Emphasis marker
    ]
    
    # Track metrics
    cache_hits = 0
    cache_misses = 0
    total_time_ms = 0
    
    # First pass: Cache should be mostly misses
    logger.info("\n=== First Pass (Cache Building) ===")
    for i, phrase in enumerate(test_phrases[:5]):  # Only use original phrases
        start_time = time.time()
        
        # Prepare request
        request = {
            "action": "translate",
            "text": phrase,
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": session_id
        }
        
        # Send request
        socket.send_json(request)
        
        # Get response
        response = socket.recv_json()
        
        # Calculate time
        time_ms = (time.time() - start_time) * 1000
        total_time_ms += time_ms
        
        # Log result
        if response.get("status") == "success":
            translation = response.get("translated_text", "")
            method = response.get("method", "unknown")
            confidence = response.get("confidence", 0)
            
            logger.info(f"[{i+1}/5] '{phrase}' -> '{translation}'")
            logger.info(f"   Method: {method}, Confidence: {confidence:.2f}, Time: {time_ms:.1f}ms")
            
            # Update metrics based on method
            if method == "cache":
                cache_hits += 1
            else:
                cache_misses += 1
        else:
            logger.error(f"Error: {response.get('error', 'Unknown error')}")
            cache_misses += 1
        
        # Wait a bit between requests
        time.sleep(0.5)
    
    # Get cache stats from the agent
    socket.send_json({"action": "health_check"})
    health_response = socket.recv_json()
    
    # Display initial cache stats
    logger.info("\nCache Statistics After First Pass:")
    if "cache_size" in health_response:
        logger.info(f"Cache size: {health_response.get('cache_size', 0)}/{health_response.get('cache_max_size', 0)}")
        logger.info(f"Cache hits: {health_response.get('cache_hits', 0)}")
        logger.info(f"Cache misses: {health_response.get('cache_misses', 0)}")
        hit_ratio = health_response.get('cache_hit_ratio', 0)
        logger.info(f"Hit ratio: {hit_ratio:.1f}%")
    
    # Second pass: Test variations that should hit cache
    logger.info("\n=== Second Pass (Testing Normalization) ===")
    second_pass_hits = 0
    second_pass_total = 0
    second_pass_time_ms = 0
    
    for i, phrase in enumerate(test_phrases[5:]):  # Use variations
        start_time = time.time()
        
        # Prepare request
        request = {
            "action": "translate",
            "text": phrase,
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": session_id
        }
        
        # Send request
        socket.send_json(request)
        
        # Get response
        response = socket.recv_json()
        
        # Calculate time
        time_ms = (time.time() - start_time) * 1000
        second_pass_time_ms += time_ms
        second_pass_total += 1
        
        # Log result
        if response.get("status") == "success":
            translation = response.get("translated_text", "")
            method = response.get("method", "unknown")
            confidence = response.get("confidence", 0)
            
            logger.info(f"[{i+1}/5] '{phrase}' -> '{translation}'")
            logger.info(f"   Method: {method}, Confidence: {confidence:.2f}, Time: {time_ms:.1f}ms")
            
            # Check if cache hit
            if method == "cache":
                second_pass_hits += 1
                logger.info(f"   ✅ Cache hit!")
            else:
                logger.info(f"   ❌ Cache miss!")
        else:
            logger.error(f"Error: {response.get('error', 'Unknown error')}")
        
        # Wait a bit between requests
        time.sleep(0.5)
    
    # Get final cache stats
    socket.send_json({"action": "health_check"})
    final_health = socket.recv_json()
    
    # Display final cache stats
    logger.info("\n=== Final Cache Statistics ===")
    if "cache_size" in final_health:
        logger.info(f"Cache size: {final_health.get('cache_size', 0)}/{final_health.get('cache_max_size', 0)}")
        logger.info(f"Cache hits: {final_health.get('cache_hits', 0)}")
        logger.info(f"Cache misses: {final_health.get('cache_misses', 0)}")
        final_hit_ratio = final_health.get('cache_hit_ratio', 0)
        logger.info(f"Hit ratio: {final_hit_ratio:.1f}%")
    
    # Calculate normalization effectiveness
    norm_effectiveness = (second_pass_hits / second_pass_total) * 100 if second_pass_total > 0 else 0
    logger.info(f"\nNormalization Effectiveness: {norm_effectiveness:.1f}%")
    logger.info(f"Avg Time First Pass: {total_time_ms/5:.1f}ms")
    logger.info(f"Avg Time Second Pass: {second_pass_time_ms/5:.1f}ms")
    if total_time_ms > 0:
        speedup = (total_time_ms - second_pass_time_ms) / total_time_ms * 100
        logger.info(f"Cache Speedup: {speedup:.1f}%")
    
    # Close ZMQ socket
    socket.close()
    context.term()
    
    return norm_effectiveness > 80  # Success if 80% of normalized variations hit cache

if __name__ == "__main__":
    logger.info("Starting translation cache test")
    try:
        success = test_cache_performance()
        if success:
            logger.info("✅ Cache test passed! Normalization working effectively.")
            sys.exit(0)
        else:
            logger.error("❌ Cache test failed. Normalization needs improvement.")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Error during testing: {str(e)}")
        sys.exit(2)
