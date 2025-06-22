#!/usr/bin/env python3
"""
Test script for contextual translation capabilities in the TranslatorAgent.
This tests how the agent handles context-dependent translations like pronoun resolution
and follow-up questions.
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
logger = logging.getLogger("test_contextual_translation")

def test_contextual_translation():
    """Test the translator agent's contextual translation capabilities"""
    # Connect to translator agent
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5563")  # Default translator agent port
    
    # Create a session ID for this conversation to maintain context
    session_id = f"test_session_{int(time.time())}"
    
    # Define test conversation flow
    # This is designed to test how context is maintained between translations
    conversation = [
        # First set up context about a file
        {
            "text": "buksan mo ang file na spreadsheet",
            "expected_contains": "open the spreadsheet file",
            "description": "Initial command establishes context about a file"
        },
        # Follow-up using "ito" (this) which should resolve to the file
        {
            "text": "i-save mo ito",
            "expected_contains": "save this",
            "description": "Follow-up with pronoun 'ito' (this) should reference the file"
        },
        # Another follow-up with "iyon" (that)
        {
            "text": "i-close mo iyon pagkatapos",
            "expected_contains": "close that",
            "description": "Follow-up with pronoun 'iyon' (that) should reference the file"
        },
        # Context switch to a new topic
        {
            "text": "buksan mo ang browser",
            "expected_contains": "open the browser",
            "description": "New command establishes new context"
        },
        # Follow-up referencing the new context
        {
            "text": "i-maximize mo ito",
            "expected_contains": "maximize this",
            "description": "Follow-up should now reference the browser, not the previous file"
        }
    ]
    
    # Run the test conversation
    success_count = 0
    for i, test_case in enumerate(conversation):
        logger.info(f"\n[{i+1}/{len(conversation)}] Testing: {test_case['description']}")
        logger.info(f"Input: '{test_case['text']}'")
        
        # Prepare request
        request = {
            "action": "translate",
            "text": test_case["text"],
            "source_lang": "tl",
            "target_lang": "en",
            "session_id": session_id
        }
        
        # Send request
        socket.send_json(request)
        
        # Get response
        response = socket.recv_json()
        
        # Check if the translation is successful and contains expected text
        if response.get("status") == "success":
            translation = response.get("translated_text", "")
            logger.info(f"Received: '{translation}'")
            logger.info(f"Method: {response.get('method', 'unknown')}, Confidence: {response.get('confidence', 0):.2f}")
            
            if test_case["expected_contains"].lower() in translation.lower():
                logger.info(f"✅ PASS: Translation contains expected content")
                success_count += 1
            else:
                logger.error(f"❌ FAIL: Translation does not contain expected content")
                logger.error(f"Expected to contain: '{test_case['expected_contains']}'")
        else:
            logger.error(f"❌ FAIL: Translation failed with status {response.get('status')}")
            logger.error(f"Error: {response.get('error', 'Unknown error')}")
        
        # Wait a bit between requests to simulate real conversation pacing
        time.sleep(1)
    
    # Print test summary
    logger.info(f"\n=== Test Summary ===")
    logger.info(f"Passed: {success_count}/{len(conversation)} tests ({success_count/len(conversation)*100:.1f}%)")
    
    # Close ZMQ socket
    socket.close()
    context.term()
    
    return success_count == len(conversation)

if __name__ == "__main__":
    logger.info("Starting contextual translation test")
    try:
        success = test_contextual_translation()
        if success:
            logger.info("All tests passed! Contextual translation is working correctly.")
            sys.exit(0)
        else:
            logger.error("Some tests failed. See log for details.")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Error during testing: {str(e)}")
        sys.exit(2)
