#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Comprehensive Memory System Test

This script tests both the memory service functionality and its health check.
"""

import zmq
import sys
import uuid
from typing import Dict, Any, Optional, Union, cast

class MemorySystemTester:
    """Tests the memory orchestrator service and its health check"""

    def __init__(self, main_port=7140, health_port=7141):
        self.main_port = main_port
        self.health_port = health_port
            """TODO: Add description for __init__."""
        self.context = zmq.Context()
        self.main_socket = None
        self.health_socket = None
        self.setup()

    def setup(self):
        """Set up the sockets"""
        # Main service socket
        self.main_socket = self.context.socket(zmq.REQ)
        self.main_socket.setsockopt(zmq.LINGER, 0)
        self.main_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        self.main_socket.connect(f"tcp://localhost:{self.main_port}")

        # Health check socket
        self.health_socket = self.context.socket(zmq.REQ)
        self.health_socket.setsockopt(zmq.LINGER, 0)
        self.health_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        self.health_socket.connect(f"tcp://localhost:{self.health_port}")

    def cleanup(self):
        """Clean up resources"""
        if self.main_socket:
            self.main_socket.close()
        if self.health_socket:
            self.health_socket.close()
        self.context.term()

    def check_health(self) -> bool:
        """Check the health of the service"""
        print("\n=== Testing Health Check ===")
        if not self.health_socket:
            print("❌ Health socket not initialized")
            return False

        try:
            request = {"action": "health_check"}
            self.health_socket.send_json(request)
            response = self.health_socket.recv_json()

            if isinstance(response, dict) and response.get("status") == "ok":
                print("✅ Health check passed!")
                print(f"   - Ready: {response.get('ready', False)}")
                print(f"   - Uptime: {response.get('uptime', 0):.2f} seconds")
                print(f"   - Message: {response.get('message', 'No message')}")
                return True
            else:
                print("❌ Health check failed!")
                print(f"   - Response: {response}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def test_add_memory(self) -> Optional[str]:
        """Test adding a memory"""
        print("\n=== Testing Add Memory ===")
        if not self.main_socket:
            print("❌ Main socket not initialized")
            return None

        try:
            test_id = str(uuid.uuid4())[:8]
            request = {
                "action": "add_memory",
                "data": {
                    "content": f"Test memory {test_id}",
                    "memory_type": "test",
                    "importance": 0.7,
                    "metadata": {"test_id": test_id},
                    "tags": ["test", "automated"]
                }
            }

            self.main_socket.send_json(request)
            response = self.main_socket.recv_json()

            if isinstance(response, dict) and response.get("status") == "success":
                memory_id = response.get("memory_id")
                if isinstance(memory_id, str):
                    print(f"✅ Memory added successfully with ID: {memory_id}")
                    return memory_id
                else:
                    print("❌ Invalid memory_id in response")
                    return None
            else:
                print(f"❌ Failed to add memory: {response}")
                return None
        except Exception as e:
            print(f"❌ Error adding memory: {e}")
            return None

    def test_get_memory(self, memory_id: Optional[str]) -> bool:
        """Test retrieving a memory"""
        print("\n=== Testing Get Memory ===")
        if not self.main_socket:
            print("❌ Main socket not initialized")
            return False

        if not memory_id:
            print("❌ No memory ID provided")
            return False

        try:
            request = {
                "action": "get_memory",
                "data": {"memory_id": memory_id}
            }

            self.main_socket.send_json(request)
            response = self.main_socket.recv_json()

            if isinstance(response, dict) and response.get("status") == "success":
                memory = response.get("memory", {})
                if isinstance(memory, dict):
                    print(f"✅ Memory retrieved successfully:")
                    print(f"   - Content: {memory.get('content', 'No content')}")
                    print(f"   - Type: {memory.get('memory_type', 'No type')}")
                    print(f"   - Importance: {memory.get('importance', 0)}")
                    return True
                else:
                    print("❌ Invalid memory format in response")
                    return False
            else:
                print(f"❌ Failed to retrieve memory: {response}")
                return False
        except Exception as e:
            print(f"❌ Error retrieving memory: {e}")
            return False

    def test_delete_memory(self, memory_id: Optional[str]) -> bool:
        """Test deleting a memory"""
        print("\n=== Testing Delete Memory ===")
        if not self.main_socket:
            print("❌ Main socket not initialized")
            return False

        if not memory_id:
            print("❌ No memory ID provided")
            return False

        try:
            request = {
                "action": "delete_memory",
                "data": {"memory_id": memory_id}
            }

            self.main_socket.send_json(request)
            response = self.main_socket.recv_json()

            if isinstance(response, dict) and response.get("status") == "success":
                print(f"✅ Memory deleted successfully")
                return True
            else:
                print(f"❌ Failed to delete memory: {response}")
                return False
        except Exception as e:
            print(f"❌ Error deleting memory: {e}")
            return False

    def run_tests(self) -> bool:
        """Run all tests"""
        try:
            # Test health check
            health_ok = self.check_health()

            # Test memory operations
            memory_id = self.test_add_memory()
            get_ok = self.test_get_memory(memory_id)
            delete_ok = self.test_delete_memory(memory_id)

            # Final health check
            final_health_ok = self.check_health()

            # Print summary
            print("\n=== Test Summary ===")
            print(f"Initial Health Check: {'✅ Passed' if health_ok else '❌ Failed'}")
            print(f"Add Memory: {'✅ Passed' if memory_id else '❌ Failed'}")
            print(f"Get Memory: {'✅ Passed' if get_ok else '❌ Failed'}")
            print(f"Delete Memory: {'✅ Passed' if delete_ok else '❌ Failed'}")
            print(f"Final Health Check: {'✅ Passed' if final_health_ok else '❌ Failed'}")

            # Ensure we have a boolean result
            all_passed = bool(health_ok and memory_id and get_ok and delete_ok and final_health_ok)
            print(f"\nOverall Test Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

            return all_passed
        finally:
            self.cleanup()

if __name__ == "__main__":
    tester = MemorySystemTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)
