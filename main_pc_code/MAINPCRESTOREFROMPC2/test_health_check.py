"""
Test script for checking agent health check functionality
"""

import time
import zmq
import json
import logging
from agents.knowledge_base import KnowledgeBase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_health_check():
    """Test the health check functionality of KnowledgeBase agent."""
    
    # Initialize agent
    logger.info("Starting KnowledgeBase agent...")
    agent = KnowledgeBase(port=5578)
    
    # Start agent in background thread
    import threading
    agent_thread = threading.Thread(target=agent.run, daemon=True)
    agent_thread.start()
    
    # Give agent a moment to start
    time.sleep(2)
    
    # Initialize ZMQ context for health check
    context = zmq.Context()
    health_socket = context.socket(zmq.REQ)
    health_socket.connect("tcp://localhost:5579")  # Health check port is main port + 1
    
    # Test health check multiple times
    for i in range(5):
        try:
            logger.info(f"Health check attempt {i+1}")
            
            # Send health check request
            health_socket.send_json({"action": "health"})
            
            # Wait for response
            response = health_socket.recv_json()
            
            # Log response
            logger.info(f"Health check response: {json.dumps(response, indent=2)}")
            
            # Check if agent is initialized
            if response.get("initialized"):
                logger.info("Agent is initialized!")
            else:
                logger.info("Agent is still initializing...")
            
            # Wait before next check
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
    
    # Test knowledge base operations
    try:
        logger.info("Testing knowledge base operations...")
        main_socket = context.socket(zmq.REQ)
        main_socket.connect("tcp://localhost:5578")
        
        # Try to add a fact
        main_socket.send_json({
            "action": "add_fact",
            "fact": {
                "subject": "test",
                "predicate": "is",
                "object": "working",
                "confidence": 1.0
            }
        })
        response = main_socket.recv_json()
        logger.info(f"Add fact response: {json.dumps(response, indent=2)}")
        
        # Try to query facts
        main_socket.send_json({
            "action": "query",
            "query": {
                "subject": "test"
            }
        })
        response = main_socket.recv_json()
        logger.info(f"Query response: {json.dumps(response, indent=2)}")
        
        main_socket.close()
    except Exception as e:
        logger.error(f"Error during knowledge base operations: {e}")
    
    # Cleanup
    health_socket.close()
    context.term()
    agent.stop()
    logger.info("Test completed")

if __name__ == "__main__":
    test_health_check() 