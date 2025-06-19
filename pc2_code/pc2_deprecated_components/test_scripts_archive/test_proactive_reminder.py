#!/usr/bin/env python
"""
Dedicated test for proactive reminder broadcasting.
This script tests specifically that the memory.py agent properly broadcasts 
reminders as proactive events when adding reminders.
"""
import zmq
import json
import time
import logging
import threading
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
MEMORY_AGENT_PORT = 5590
PROACTIVE_EVENT_PORT = 5595

class ProactiveReminderTester:
    def __init__(self):
        self.context = zmq.Context()
        self.memory_socket = self.context.socket(zmq.REQ)
        self.memory_socket.connect(f"tcp://localhost:{MEMORY_AGENT_PORT}")
        self.memory_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Event listening variables
        self.events = []
        self.listening = False
        self.listener_thread = None
    
    def start_event_listener(self):
        """Start a background thread listening for proactive events."""
        self.listening = True
        self.events = []
        self.listener_thread = threading.Thread(target=self._listen_for_events)
        self.listener_thread.daemon = True
        self.listener_thread.start()
        logger.info("Started proactive event listener thread")
        # Give a moment for the thread to start
        time.sleep(0.5)
    
    def stop_event_listener(self):
        """Stop the background listener thread."""
        self.listening = False
        if self.listener_thread:
            self.listener_thread.join(timeout=1.0)
            logger.info("Stopped proactive event listener thread")
    
    def _listen_for_events(self):
        """Background thread function to listen for events."""
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect(f"tcp://localhost:{PROACTIVE_EVENT_PORT}")
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        logger.info(f"Listening for proactive events on port {PROACTIVE_EVENT_PORT}")
        
        # Use a poller for timeout control
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        
        try:
            while self.listening:
                socks = dict(poller.poll(timeout=1000))  # 1 second timeout
                if socket in socks and socks[socket] == zmq.POLLIN:
                    try:
                        event = socket.recv_json(flags=zmq.NOBLOCK)
                        self.events.append(event)
                        logger.info(f"Received proactive event: {json.dumps(event, indent=2)}")
                    except zmq.error.Again:
                        pass
                    except Exception as e:
                        logger.error(f"Error receiving event: {e}")
        finally:
            socket.close()
            context.term()
    
    def add_reminder(self, text, user_id="test_user"):
        """Add a reminder through the memory agent."""
        reminder = {
            "text": text,
            "timestamp": time.time(),
            "type": "reminder",
            "emotion": "neutral"
        }
        
        request = {
            "action": "add_reminder",
            "user_id": user_id,
            "reminder": reminder
        }
        
        logger.info(f"Sending add_reminder request: {request}")
        self.memory_socket.send_json(request)
        
        try:
            response = self.memory_socket.recv_json()
            logger.info(f"Add reminder response: {response}")
            return response
        except zmq.error.Again:
            logger.error("Timeout waiting for add_reminder response")
            return {"status": "error", "reason": "Timeout"}

def run_test():
    """Run the comprehensive proactive reminder test."""
    tester = ProactiveReminderTester()
    
    # Start listening for events before adding any reminders
    tester.start_event_listener()
    logger.info("Waiting 1 second before adding reminder...")
    time.sleep(1)
    
    # Add a reminder which should trigger a proactive broadcast
    reminder_text = f"Test proactive reminder at {time.strftime('%H:%M:%S')}"
    add_result = tester.add_reminder(reminder_text)
    
    # Wait a moment for any broadcasts to be received
    logger.info("Waiting 3 seconds to collect any broadcast events...")
    time.sleep(3)
    
    # Stop the listener and report results
    tester.stop_event_listener()
    
    # Print test results
    print("\n" + "="*50)
    print("PROACTIVE REMINDER TEST RESULTS")
    print("="*50)
    print(f"Add reminder successful: {add_result.get('status') == 'ok'}")
    print(f"Proactive events received: {len(tester.events) > 0}")
    print(f"Number of events: {len(tester.events)}")
    
    if tester.events:
        print("\nEvent details:")
        for i, event in enumerate(tester.events):
            print(f"\nEvent #{i+1}:")
            for k, v in event.items():
                print(f"  {k}: {v}")
    
    if len(tester.events) > 0:
        print("\n✅ Proactive reminder broadcasting is WORKING!")
    else:
        print("\n❌ Proactive reminder broadcasting is NOT WORKING!")

if __name__ == "__main__":
    run_test()
