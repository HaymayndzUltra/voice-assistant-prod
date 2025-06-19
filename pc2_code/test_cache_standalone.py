#!/usr/bin/env python3
"""
Standalone test for the text normalization and caching improvements.
This script doesn't require the full translator agent to be running.
"""

import re
import time
import logging
import random
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_cache")

# Normalization functions from our enhancement
def normalize_text(text: str) -> str:
    """Basic normalization function"""
    # Trim whitespace
    text = text.strip()
    # Remove excess spaces
    text = re.sub(r'\s+', ' ', text)
    # Handle common Taglish contractions
    text = text.replace("i-on", "i-turn on")
    text = text.replace("i-off", "i-turn off")
    return text
    
def normalize_text_for_cache(text: str) -> str:
    """Enhanced normalization for cache key generation"""
    # Start with basic normalization
    text = normalize_text(text)
    # Convert to lowercase for case-insensitive matching
    text = text.lower()
    # Remove punctuation that doesn't affect meaning
    text = re.sub(r'[.,;!?]', '', text)
    # Standardize common Filipino markers that don't affect translation
    text = re.sub(r'\bba\b', '', text)  # Remove 'ba' question marker
    text = re.sub(r'\bpo\b', '', text)  # Remove 'po' politeness marker
    text = re.sub(r'\bnga\b', '', text)  # Remove 'nga' emphasis marker
    text = re.sub(r'\bnaman\b', '', text)  # Remove 'naman' comparative marker
    # Standardize articles that are often optional
    text = re.sub(r'\bang\b', '', text)  # 'ang' (the) is often optional
    text = re.sub(r'\bng\b', '', text)   # 'ng' (of) is often optional
    # Remove excess spaces again after our transformations
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

# Simple translation cache implementation
class TranslationCache:
    def __init__(self, max_size=500):
        self.cache = {}
        self.keys_order = []
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        
    def get(self, text, source_lang="tl", target_lang="en"):
        """Get a translation from cache using normalized key"""
        normalized_text = normalize_text_for_cache(text)
        key = f"{normalized_text}|{source_lang}|{target_lang}"
        
        if key in self.cache:
            self.hits += 1
            # Update access order (LRU)
            if key in self.keys_order:
                self.keys_order.remove(key)
            self.keys_order.append(key)
            return self.cache[key], True
        else:
            self.misses += 1
            return None, False
            
    def put(self, text, translation, source_lang="tl", target_lang="en"):
        """Store a translation in cache using normalized key"""
        normalized_text = normalize_text_for_cache(text)
        key = f"{normalized_text}|{source_lang}|{target_lang}"
        
        # Evict oldest item if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            if self.keys_order:
                oldest_key = self.keys_order[0]
                if oldest_key in self.cache:
                    del self.cache[oldest_key]
                    self.keys_order.remove(oldest_key)
        
        # Store the translation
        self.cache[key] = translation
        
        # Update access order
        if key in self.keys_order:
            self.keys_order.remove(key)
        self.keys_order.append(key)
        
    def stats(self):
        """Return cache statistics"""
        hit_ratio = (self.hits / (self.hits + self.misses)) * 100 if (self.hits + self.misses) > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": hit_ratio
        }

def test_normalization_effectiveness():
    """Test how well our normalization functions help with cache hits"""
    logger.info("Testing normalization effectiveness for caching")
    
    # Create test cache
    cache = TranslationCache(max_size=100)
    
    # Define test phrases with slight variations
    original_phrases = [
        "buksan mo ang file",
        "i-save mo ang document",
        "magsimula ng bagong project",
        "isara mo ang window",
        "i-maximize mo ang browser",
    ]
    
    translations = [
        "open the file",
        "save the document",
        "start a new project",
        "close the window",
        "maximize the browser",
    ]
    
    variations = [
        # Capitalization
        "Buksan mo ang file",
        "I-save mo ang document",
        "Magsimula ng bagong project",
        "Isara mo ang window",
        "I-maximize mo ang browser",
        
        # Punctuation
        "buksan mo ang file.",
        "i-save mo ang document!",
        "magsimula ng bagong project?",
        "isara mo ang window;",
        "i-maximize mo ang browser,",
        
        # Politeness markers
        "buksan mo po ang file",
        "i-save mo po ang document",
        "magsimula po ng bagong project",
        "isara mo po ang window",
        "i-maximize mo po ang browser",
        
        # Question markers
        "buksan mo ba ang file",
        "i-save mo ba ang document",
        "magsimula ba ng bagong project",
        "isara mo ba ang window",
        "i-maximize mo ba ang browser",
        
        # Emphasis markers
        "buksan mo nga ang file",
        "i-save mo nga ang document",
        "magsimula nga ng bagong project",
        "isara mo nga ang window",
        "i-maximize mo nga ang browser",
        
        # Article variations
        "buksan mo file",  # No 'ang'
        "i-save mo document",
        "magsimula bagong project",  # No 'ng'
        "isara mo window",
        "i-maximize mo browser",
        
        # Combined variations
        "Buksan mo po ba ang file?",
        "I-save mo nga ang document!",
        "Magsimula po ng bagong project.",
        "Isara mo ba nga ang window,",
        "I-maximize mo po nga ang browser;"
    ]
    
    # First, populate the cache with original phrases
    for i, (phrase, translation) in enumerate(zip(original_phrases, translations)):
        cache.put(phrase, translation)
        logger.info(f"Added to cache: '{phrase}' -> '{translation}'")
    
    # Now test all variations
    total_variations = len(variations)
    hits = 0
    
    logger.info("\nTesting variations:")
    for i, variation in enumerate(variations):
        # Try to get from cache
        translation, found = cache.get(variation)
        
        if found:
            hits += 1
            logger.info(f"[{i+1}/{total_variations}] ✅ HIT: '{variation}' -> '{translation}'")
            
            # Find the normalized form
            normalized = normalize_text_for_cache(variation)
            logger.info(f"   Normalized: '{normalized}'")
        else:
            logger.info(f"[{i+1}/{total_variations}] ❌ MISS: '{variation}'")
            
            # Find the normalized form
            normalized = normalize_text_for_cache(variation)
            logger.info(f"   Normalized: '{normalized}'")
            
            # For demonstration, add the missed variation
            simulated_translation = f"SIMULATED: {variation}"
            cache.put(variation, simulated_translation)
    
    # Calculate hit rate for variations
    hit_rate = (hits / total_variations) * 100 if total_variations > 0 else 0
    
    # Get overall cache stats
    stats = cache.stats()
    
    # Display results
    logger.info("\n=== Results ===")
    logger.info(f"Original phrases: {len(original_phrases)}")
    logger.info(f"Variations tested: {total_variations}")
    logger.info(f"Variation hit rate: {hit_rate:.1f}%")
    logger.info(f"\nCache stats:")
    logger.info(f"Size: {stats['size']}/{stats['max_size']}")
    logger.info(f"Total hits: {stats['hits']}")
    logger.info(f"Total misses: {stats['misses']}")
    logger.info(f"Overall hit ratio: {stats['hit_ratio']:.1f}%")
    
    # Test success criteria
    success = hit_rate >= 80  # Consider successful if 80% or more variations hit cache
    logger.info(f"\nTest {'PASSED' if success else 'FAILED'} - Normalization effectiveness: {hit_rate:.1f}%")
    return success

if __name__ == "__main__":
    logger.info("Starting standalone cache normalization test")
    test_normalization_effectiveness()
