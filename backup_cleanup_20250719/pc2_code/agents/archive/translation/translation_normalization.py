from common.core.base_agent import BaseAgent
"""
Utility functions for text normalization to improve translation caching and context handling.
These functions help maintain consistent cache keys and improve translation quality.
"""

import re

def normalize_text(text: str) -> str:
    """Normalize text for basic processing.
    
    Args:
        text (str): Raw input text
        
    Returns:
        str: Normalized text with consistent spacing and common contractions expanded
    """
    # Trim whitespace
    text = text.strip()
    
    # Remove excess spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Handle common Taglish contractions
    text = text.replace("i-on", "i-turn on")
    text = text.replace("i-off", "i-turn off")
    
    return text

def normalize_text_for_cache(text: str) -> str:
    """Normalize text specifically for cache key generation.
    
    This creates more consistent keys by removing variations that don't affect meaning,
    enabling better cache hit rates even when phrases have minor differences.
    
    Args:
        text (str): Raw input text
        
    Returns:
        str: Highly normalized text suitable for cache key generation
    """
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
