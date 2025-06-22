"""
Test script to demonstrate the translation cache functionality
"""
import sys
import time
from agents.translator_agent import TranslatorAgent

def main():
    print("Translation Cache Test")
    print("-" * 50)
    
    # Create translator agent
    agent = TranslatorAgent()
    
    # Test phrases (some repeated)
    test_phrases = [
        "buksan mo ang file",
        "i-save mo ang document",
        "magsimula ng bagong project",
        "Kumusta ka na?",
        "buksan mo ang file",  # Repeated to test cache
        "i-save mo ang document",  # Repeated to test cache
        "Mahalaga ang pamilya sa ating kultura.",
        "Hello, can you help me?",
        "Kumusta ka na?",  # Repeated to test cache
        "Pwede mo ba i-translate ito?",
        "Can you please i-open ang file na ito?",
        "magsimula ng bagong project"  # Repeated to test cache
    ]
    
    # Translate each phrase and measure time
    for i, phrase in enumerate(test_phrases):
        print(f"\nTest {i+1}: '{phrase}'")
        start_time = time.time()
        translated = agent.translate_command(phrase)
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"Result: '{translated}'")
        print(f"Time: {elapsed_ms:.2f}ms")
    
    # Print cache stats
    hit_ratio = (agent.cache_hits / (agent.cache_hits + agent.cache_misses)) * 100 if (agent.cache_hits + agent.cache_misses) > 0 else 0
    print("\nCache Statistics:")
    print(f"Cache size: {len(agent.translation_cache)}/{agent.cache_max_size}")
    print(f"Cache hits: {agent.cache_hits}")
    print(f"Cache misses: {agent.cache_misses}")
    print(f"Hit ratio: {hit_ratio:.1f}%")
    
    # Print some entries from the cache
    print("\nSample Cache Entries:")
    for i, (key, value) in enumerate(agent.translation_cache.items()):
        if i >= 5:  # Show at most 5 entries
            break
        print(f"Key: {key[:40]}...")
        print(f"Value: {value[:40]}...")
        print("-" * 30)

if __name__ == "__main__":
    main()
