#!/usr/bin/env python3
"""
Test client for interacting with the translator server
"""
import sys
import json
import time
import zmq
import logging
import argparse
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
    ]
)
logger = logging.getLogger("translator_client")

# Constants
ZMQ_PORT = 5563
ZMQ_SERVER = "localhost"

def send_translation_request(text, source_lang="tl", target_lang="en", session_id=None):
    """Send a translation request to the translator server"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    try:
        # Connect to the server
        server_address = f"tcp://{ZMQ_SERVER}:{ZMQ_PORT}"
        logger.info(f"Connecting to translator server at {server_address}")
        socket.connect(server_address)
        
        # Set a timeout for the request
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Prepare the request
        request = {
            "action": "translate",
            "text": text,
            "source_lang": source_lang,
            "target_lang": target_lang
        }
        
        if session_id:
            request["session_id"] = session_id
        
        # Send the request
        logger.info(f"Sending request: {json.dumps(request)}")
        socket.send_string(json.dumps(request)
        
        # Wait for response
        response_json = socket.recv_string()
        response = json.loads(response_json)
        
        return response
    except zmq.error.Again:
        logger.error("Request timed out - server not responding")
        return {"status": "error", "error": "Request timed out"}
    except Exception as e:
        logger.error(f"Error sending request: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        socket.close()
        context.term()

def send_health_check():
    """Send a health check request to the translator server"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    try:
        # Connect to the server
        server_address = f"tcp://{ZMQ_SERVER}:{ZMQ_PORT}"
        logger.info(f"Connecting to translator server at {server_address}")
        socket.connect(server_address)
        
        # Set a timeout for the request
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Prepare the request
        request = {
            "action": "health_check"
        }
        
        # Send the request
        logger.info("Sending health check request")
        socket.send_string(json.dumps(request)
        
        # Wait for response
        response_json = socket.recv_string()
        response = json.loads(response_json)
        
        return response
    except zmq.error.Again:
        logger.error("Health check timed out - server not responding")
        return {"status": "error", "error": "Request timed out"}
    except Exception as e:
        logger.error(f"Error sending health check: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        socket.close()
        context.term()

def run_interactive_session():
    """Run an interactive session with the translator server"""
    logger.info("Starting interactive session with translator server")
    logger.info("Type 'exit' to quit, 'health' for a health check")
    
    session_id = f"interactive_{int(time.time()}"
    logger.info(f"Using session ID: {session_id}")
    
    try:
        while True:
            text = input("\nEnter text to translate (or command): ")
            
            if text.lower() == 'exit':
                logger.info("Exiting interactive session")
                break
                
            if text.lower() == 'health':
                response = send_health_check()
                logger.info(f"Health check response: {json.dumps(response, indent=2)}")
                continue
            
            # Send translation request
            start_time = time.time()
            response = send_translation_request(text, session_id=session_id)
            processing_time = (time.time() - start_time) * 1000  # ms
            
            # Print the response
            if response.get("status") == "success":
                logger.info(f"Translation: '{response.get('original_text')}' -> '{response.get('translated_text')}'")
                logger.info(f"Method: {response.get('method')}, Confidence: {response.get('confidence')}")
                logger.info(f"Processing time: {processing_time:.2f}ms")
            else:
                logger.error(f"Error: {response.get('error')}")
    
    except KeyboardInterrupt:
        logger.info("Interactive session interrupted by user")
    except Exception as e:
        logger.error(f"Error in interactive session: {str(e)}")

def run_test_suite():
    """Run a test suite against the translator server"""
    logger.info("Running test suite against translator server")
    
    # First, do a health check
    health = send_health_check()
    if health.get("status") != "success":
        logger.error(f"Health check failed: {health.get('error')}")
        return
    
    logger.info(f"Health check passed: {json.dumps(health, indent=2)}")
    
    # Test translations with a consistent session
    session_id = f"test_suite_{int(time.time()}"
    
    test_phrases = [
        "buksan mo ang file",
        "i-save mo ang document",
        "magsimula ng bagong project",
        "isara mo ang window",
        "i-maximize mo ang browser",
        "Kumusta ka na?",
        "Mahalaga ang pamilya sa ating kultura.",
        "Hello, can you help me?",  # Already English
        "Pwede mo ba i-translate ito?",  # Should be translated
        "Can you please i-open ang file na ito?"  # Taglish
    ]
    
    # First pass - initial translations
    logger.info("\n=== First pass translations ===")
    for phrase in test_phrases:
        response = send_translation_request(phrase, session_id=session_id)
        if response.get("status") == "success":
            logger.info(f"✅ '{phrase}' -> '{response.get('translated_text')}'")
        else:
            logger.error(f"❌ Error translating '{phrase}': {response.get('error')}")
    
    # Second pass - should hit cache
    logger.info("\n=== Second pass (should hit cache) ===")
    for phrase in test_phrases:
        response = send_translation_request(phrase, session_id=session_id)
        if response.get("status") == "success":
            logger.info(f"✅ '{phrase}' -> '{response.get('translated_text')}'")
        else:
            logger.error(f"❌ Error translating '{phrase}': {response.get('error')}")
    
    # Context test
    logger.info("\n=== Testing contextual translation ===")
    # First establish context with a file reference
    send_translation_request("buksan mo ang file", session_id=session_id)
    
    # Then test a follow-up with a pronoun reference
    context_tests = [
        "i-save mo ito",  # "save this" (should refer to file)
        "i-delete mo iyon"  # "delete that" (should refer to file)
    ]
    
    for phrase in context_tests:
        response = send_translation_request(phrase, session_id=session_id)
        if response.get("status") == "success":
            logger.info(f"✅ Context test: '{phrase}' -> '{response.get('translated_text')}'")
        else:
            logger.error(f"❌ Error in context test: '{phrase}': {response.get('error')}")
    
    # Final health check to see cache stats
    health = send_health_check()
    logger.info(f"\nFinal health check: {json.dumps(health, indent=2)}")
    logger.info("Test suite complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test client for the translator server")
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('--test', action='store_true', help='Run a test suite')
    parser.add_argument('--translate', type=str, help='Translate a single phrase')
    args = parser.parse_args()
    
    if args.interactive:
        run_interactive_session()
    elif args.test:
        run_test_suite()
    elif args.translate:
        response = send_translation_request(args.translate)
        if response.get("status") == "success":
            print(f"Translation: {response.get('translated_text')}")
        else:
            print(f"Error: {response.get('error')}")
    else:
        # Default to test suite
        run_test_suite()
