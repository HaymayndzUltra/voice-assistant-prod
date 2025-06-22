#!/usr/bin/env python3
"""
End-to-End Communication Flow Test
---------------------------------
This script simulates a request from the Translator Agent and traces it
through the entire architecture, logging all ZMQ messages between components.

Flow to test:
1. Translator Agent (simulated) -> EMR (port 7602)
2. EMR consults:
   - Contextual Memory (port 5596)
   - Model Manager (port 5556) for model selection
   - Chain of Thought (port 5612) for complex tasks
3. Chain of Thought -> Remote Connector (port 5557)
4. Remote Connector -> Model Services
5. Response returns through the chain
6. EMR publishes response on PUB port (7701)
"""
import zmq
import json
import time
import logging
import sys
import threading
from pathlib import Path

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_end_to_end_flow.log")
    ]
)
logger = logging.getLogger("EndToEndTest")

# Current discovered ports
EMR_REP_PORT = 7602  # Enhanced Model Router REP socket
EMR_PUB_PORT = 7701  # Enhanced Model Router PUB socket
TRANSLATOR_PORT = 5559  # Translator Agent port

class MessageSubscriber(threading.Thread):
    """Thread to subscribe to PUB messages from EMR"""
    def __init__(self, pub_port):
        threading.Thread.__init__(self, daemon=True)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://localhost:{pub_port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.running = True
        logger.info(f"Message subscriber connected to EMR publisher on port {pub_port}")
        
    def run(self):
        """Listen for published messages"""
        logger.info("Starting to listen for published messages...")
        while self.running:
            try:
                if self.socket.poll(1000) == 0:  # 1 second timeout
                    continue
                    
                # Receive and log message
                message = self.socket.recv_string()
                try:
                    data = json.loads(message)
                    logger.info(f"🔔 PUBLISHED MESSAGE from EMR: {json.dumps(data, indent=2)}")
                except:
                    logger.info(f"🔔 PUBLISHED MESSAGE (non-JSON): {message[:100]}")
            except zmq.Again:
                continue
            except Exception as e:
                logger.error(f"Error in subscriber thread: {str(e)}")

class EndToEndTester:
    """Simulates the flow of a request through the entire architecture"""
    def __init__(self):
        # Setup ZMQ context
        self.context = zmq.Context()
        
        # Simulate Translator Agent - connect to EMR
        self.translator_socket = self.context.socket(zmq.REQ)
        self.translator_socket.connect(f"tcp://localhost:{EMR_REP_PORT}")
        logger.info(f"Connected to EMR on port {EMR_REP_PORT} (simulating Translator Agent)")
        
        # Start subscriber to monitor EMR's published messages
        self.subscriber = MessageSubscriber(EMR_PUB_PORT)
        self.subscriber.start()
        
    def test_general_query(self):
        """Test a general query that flows through the system"""
        logger.info("\n🔍 TEST: General Query - 'Summarize the benefits of artificial intelligence in healthcare'")
        logger.info("🔄 FLOW: Translator -> EMR -> Model Manager -> Remote Connector -> Model -> Response")
        
        # Create a request as if from Translator Agent
        request = {
            "request": "process_task",
            "text": "Summarize the benefits of artificial intelligence in healthcare",
            "original_text": "Ibuod ang mga benepisyo ng artificial intelligence sa healthcare",
            "source": "translator_agent",
            "request_id": f"translator_{time.time()}",
            "context": {
                "user_id": "test_user",
                "session_id": "test_session"
            }
        }
        
        # Log the request
        logger.info(f"📤 SENDING from Translator to EMR: {json.dumps(request, indent=2)}")
        
        # Send request to EMR
        self.translator_socket.send_string(json.dumps(request))
        
        # Wait for response with timeout
        poller = zmq.Poller()
        poller.register(self.translator_socket, zmq.POLLIN)
        
        if poller.poll(30000):  # 30 second timeout
            # Receive response
            response = self.translator_socket.recv_string()
            try:
                response_data = json.loads(response)
                logger.info(f"📥 RECEIVED by Translator from EMR: {json.dumps(response_data, indent=2)}")
                return response_data
            except:
                logger.info(f"📥 RECEIVED by Translator from EMR (non-JSON): {response[:100]}")
                return response
        else:
            logger.error("⚠️ TIMEOUT waiting for EMR response")
            return None
            
    def test_complex_reasoning(self):
        """Test a complex reasoning task that should trigger Chain of Thought"""
        logger.info("\n🔍 TEST: Complex Reasoning - 'Explain how to implement a secure authentication system'")
        logger.info("🔄 FLOW: Translator -> EMR -> CoT -> Remote Connector -> Model -> Response")
        
        # Create a request as if from Translator Agent
        request = {
            "request": "process_task",
            "text": "Explain how to implement a secure authentication system with multi-factor authentication",
            "original_text": "Ipaliwanag kung paano mag-implement ng secure authentication system na may multi-factor authentication",
            "source": "translator_agent",
            "request_id": f"translator_cot_{time.time()}",
            "context": {
                "user_id": "test_user",
                "session_id": "test_session"
            },
            "use_chain_of_thought": True
        }
        
        # Log the request
        logger.info(f"📤 SENDING from Translator to EMR: {json.dumps(request, indent=2)}")
        
        # Send request to EMR
        self.translator_socket.send_string(json.dumps(request))
        
        # Wait for response with timeout
        poller = zmq.Poller()
        poller.register(self.translator_socket, zmq.POLLIN)
        
        if poller.poll(60000):  # 60 second timeout for complex reasoning
            # Receive response
            response = self.translator_socket.recv_string()
            try:
                response_data = json.loads(response)
                logger.info(f"📥 RECEIVED by Translator from EMR: {json.dumps(response_data, indent=2)}")
                return response_data
            except:
                logger.info(f"📥 RECEIVED by Translator from EMR (non-JSON): {response[:100]}")
                return response
        else:
            logger.error("⚠️ TIMEOUT waiting for EMR response")
            return None
    
    def cleanup(self):
        """Clean up ZMQ resources"""
        logger.info("Cleaning up resources...")
        self.translator_socket.close()
        self.subscriber.running = False
        self.subscriber.join(timeout=1)
        self.context.term()
        logger.info("Test complete")

def main():
    logger.info("=================================================")
    logger.info("🚀 STARTING END-TO-END ARCHITECTURE FLOW TEST")
    logger.info("=================================================")
    logger.info("This test simulates the complete request flow through all components")
    logger.info("Expected flow:")
    logger.info("1. Translator Agent -> EMR (port 7602)")
    logger.info("2. EMR -> Contextual Memory, Model Manager, Chain of Thought")
    logger.info("3. Chain of Thought -> Remote Connector")
    logger.info("4. Remote Connector -> Model Services")
    logger.info("5. Response returns through the chain")
    logger.info("6. EMR publishes response on PUB port (7701)")
    logger.info("=================================================")
    
    tester = EndToEndTester()
    
    try:
        # Test 1: General query
        general_result = tester.test_general_query()
        
        # Wait between tests
        logger.info("Waiting 5 seconds before next test...")
        time.sleep(5)
        
        # Test 2: Complex reasoning
        complex_result = tester.test_complex_reasoning()
        
        # Summary
        logger.info("\n=================================================")
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=================================================")
        logger.info(f"General Query Test: {'✅ Completed' if general_result else '❌ Failed'}")
        logger.info(f"Complex Reasoning Test: {'✅ Completed' if complex_result else '❌ Failed'}")
        logger.info("=================================================")
        logger.info("Review logs for detailed message flow between components")
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()
