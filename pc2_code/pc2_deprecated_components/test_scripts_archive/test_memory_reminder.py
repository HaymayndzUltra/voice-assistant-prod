#!/usr/bin/env python
"""
End-to-end test for memory.py reminder functionality.
Tests adding, listing, and deleting reminders.
Also verifies that proactive events (broadcasts) are controlled by the config flag.
"""
import sys
import time
import json
import zmq
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
MEMORY_AGENT_PORT = 5590
PROACTIVE_EVENT_PORT = 5595  # Port for proactive events (broadcasts)

class MemoryTester:
    def __init__(self):
        self.context = zmq.Context()
        self.memory_socket = self._connect_socket(MEMORY_AGENT_PORT)
        self.test_user = f"test_user_{int(time.time())}"
        self.event_socket = None
        self.received_events = []
        
    def _connect_socket(self, port: int) -> zmq.Socket:
        """Connect to a ZeroMQ REQ socket."""
        socket = self.context.socket(zmq.REQ)
        socket.connect(f"tcp://localhost:{port}")
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        return socket
        
    def _setup_event_listener(self):
        """Setup a listener for proactive events."""
        self.event_socket = self.context.socket(zmq.SUB)
        self.event_socket.connect(f"tcp://localhost:{PROACTIVE_EVENT_PORT}")
        self.event_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.event_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
        
    def _listen_for_events(self, duration=2):
        """Listen for proactive events for a specified duration."""
        if not self.event_socket:
            self._setup_event_listener()
            
        self.received_events = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            try:
                event = self.event_socket.recv_json()
                self.received_events.append(event)
                logger.info(f"Received proactive event: {event}")
            except zmq.error.Again:
                # Timeout, continue listening
                pass
            except Exception as e:
                logger.error(f"Error receiving event: {e}")
                break
                
        return self.received_events
        
    def add_reminder(self, text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a reminder for a user."""
        if user_id is None:
            user_id = self.test_user
            
        reminder = {
            "type": "reminder",
            "text": text,
            "emotion": "neutral",
            "timestamp": time.time()
        }
        
        request = {
            "action": "add_memory",
            "user_id": user_id,
            "memory": reminder
        }
        
        self.memory_socket.send_json(request)
        try:
            response = self.memory_socket.recv_json()
            logger.info(f"Add reminder response: {response}")
            return response
        except zmq.error.Again:
            logger.error("Timeout waiting for add_reminder response")
            return {"status": "error", "message": "Timeout"}
    
    def list_reminders(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """List all reminders for a user."""
        if user_id is None:
            user_id = self.test_user
            
        request = {
            "action": "get_memories",
            "user_id": user_id
        }
        
        self.memory_socket.send_json(request)
        try:
            response = self.memory_socket.recv_json()
            logger.info(f"List reminders response: {response}")
            return response
        except zmq.error.Again:
            logger.error("Timeout waiting for list_reminders response")
            return {"status": "error", "message": "Timeout"}
    
    def delete_reminder(self, index: int, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete a reminder for a user by index."""
        if user_id is None:
            user_id = self.test_user
            
        request = {
            "action": "clear_memory",
            "user_id": user_id,
            "index": index
        }
        
        self.memory_socket.send_json(request)
        try:
            response = self.memory_socket.recv_json()
            logger.info(f"Delete reminder response: {response}")
            return response
        except zmq.error.Again:
            logger.error("Timeout waiting for delete_reminder response")
            return {"status": "error", "message": "Timeout"}
    
    def run_reminder_tests(self):
        """Run a complete set of reminder tests."""
        results = {}
        
        # Test 1: Adding a reminder
        logger.info("\n=== TEST 1: ADDING A REMINDER ===")
        reminder_text = f"Test reminder at {time.strftime('%H:%M:%S')}"
        add_response = self.add_reminder(reminder_text)
        results["add_reminder"] = add_response.get("status") == "ok"
        
        # Test 2: Listen for proactive events (broadcast)
        logger.info("\n=== TEST 2: CHECKING FOR PROACTIVE BROADCASTS ===")
        logger.info("Listening for proactive events for 2 seconds...")
        events = self._listen_for_events(2)
        results["proactive_events_received"] = len(events) > 0
        results["events_count"] = len(events)
        
        # Test 3: Listing reminders
        logger.info("\n=== TEST 3: LISTING REMINDERS ===")
        list_response = self.list_reminders()
        reminders = list_response.get("memories", [])
        results["list_reminders"] = list_response.get("status") == "ok"
        results["reminders_count"] = len(reminders)
        
        # Test 4: Verify the reminder was added
        logger.info("\n=== TEST 4: VERIFYING REMINDER CONTENT ===")
        found_reminder = False
        for memory in reminders:
            if memory.get("memory", {}).get("text") == reminder_text:
                found_reminder = True
                break
        results["reminder_found"] = found_reminder
        
        # Test 5: Delete the reminder if found
        if found_reminder and reminders:
            logger.info("\n=== TEST 5: DELETING REMINDER ===")
            delete_response = self.delete_reminder(0)  # Delete the first reminder
            results["delete_reminder"] = delete_response.get("status") == "ok"
            
            # Verify deletion
            list_response_after = self.list_reminders()
            reminders_after = list_response_after.get("memories", [])
            results["deletion_verified"] = len(reminders_after) < len(reminders)
        
        return results
    
    def close(self):
        """Clean up resources."""
        if self.memory_socket:
            self.memory_socket.close()
        if self.event_socket:
            self.event_socket.close()
        self.context.term()

def main():
    logger.info("Starting memory reminder functionality test")
    tester = MemoryTester()
    
    try:
        results = tester.run_reminder_tests()
        
        # Display results
        print("\n" + "=" * 50)
        print("REMINDER FUNCTIONALITY TEST RESULTS")
        print("=" * 50)
        
        for test, result in results.items():
            print(f"{test:<25}: {result}")
            
        if all(v is True for k, v in results.items() if k not in ["events_count", "reminders_count"]):
            print("\n✅ All reminder tests PASSED!")
        else:
            print("\n❌ Some reminder tests FAILED!")
            
        # Additional summary based on proactive events
        if results.get("proactive_events_received"):
            print("\n📢 Proactive event broadcasting is ENABLED")
            print(f"   Received {results.get('events_count', 0)} proactive events")
        else:
            print("\n🔇 Proactive event broadcasting is DISABLED or not working")
            
    finally:
        tester.close()
        
if __name__ == "__main__":
    main()
