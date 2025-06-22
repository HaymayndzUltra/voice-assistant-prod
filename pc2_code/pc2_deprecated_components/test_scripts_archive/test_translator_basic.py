#!/usr/bin/env python3
"""
Basic diagnostic test for the translator agent.
This script attempts to import and initialize the TranslatorAgent class
without starting the ZMQ socket server.
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_translator_basic")

def test_translator_agent_init():
    """Test if the TranslatorAgent class can be imported and initialized"""
    try:
        logger.info("Attempting to import TranslatorAgent class...")
        
        # Add parent directory to path if needed
        current_dir = Path(__file__).resolve().parent
        if str(current_dir) not in sys.path:
            sys.path.append(str(current_dir))
        
        # First try the fixed version if it exists
        try:
            logger.info("Trying to import from translator_agent_fixed.py...")
            from agents.translator_agent_fixed import TranslatorAgent
            logger.info("Successfully imported TranslatorAgent from fixed version")
            agent_source = "fixed"
        except ImportError:
            # If that fails, try the regular version
            logger.info("Fixed version import failed, trying regular translator_agent.py...")
            from agents.translator_agent import TranslatorAgent
            logger.info("Successfully imported TranslatorAgent from regular version")
            agent_source = "regular"
        
        # Try to initialize the agent without starting ZMQ
        logger.info("Attempting to initialize TranslatorAgent instance...")
        agent = TranslatorAgent()
        logger.info("Successfully initialized TranslatorAgent instance")
        
        # Get basic info from the agent
        logger.info("Agent information:")
        logger.info(f"Source: {agent_source}")
        if hasattr(agent, 'stats'):
            logger.info(f"Cache size: {len(agent.translation_cache) if hasattr(agent, 'translation_cache') else 'N/A'}")
            logger.info(f"Cache persistence: {agent.stats.get('cache_persistence', {}).get('total_loads', 'Not found')}")
            logger.info(f"NLLB adapter configured: {agent.nllb_adapter is not None}")
        
        return True, f"Successfully initialized TranslatorAgent from {agent_source} version"
    
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}", exc_info=True)
        return False, f"Failed to initialize TranslatorAgent: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting basic translator agent test")
    success, message = test_translator_agent_init()
    
    if success:
        logger.info(f"✅ Test PASSED: {message}")
        sys.exit(0)
    else:
        logger.error(f"❌ Test FAILED: {message}")
        sys.exit(1)
