#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test script for the Memory Orchestrator
"""

import sys
import json
import zmq
import uuid
from datetime import datetime

# Add project root to path
sys.path.append('/home/haymayndz/AI_System_Monorepo')

# Import the memory orchestrator
from main_pc_code.src.memory.memory_orchestrator import MemoryOrchestrator

def test_memory_operations():
    """Test basic memory operations"""
    # Create a test memory
    memory_id = create_memory()
    print(f"Created memory with ID: {memory_id}")
    
    # Read the memory
    memory = read_memory(memory_id)
    print(f"Read memory: {memory}")
    
    # Update the memory
    update_memory(memory_id, "Updated content")
    print(f"Updated memory")
    
    # Read the updated memory
    updated_memory = read_memory(memory_id)
    print(f"Read updated memory: {updated_memory}")
    
    # Delete the memory
    delete_memory(memory_id)
    print(f"Deleted memory")
    
    # Try to read the deleted memory (should fail)
    try:
        deleted_memory = read_memory(memory_id)
        print(f"Unexpectedly read deleted memory: {deleted_memory}")
    except Exception as e:
        print(f"As expected, could not read deleted memory: {e}")

def create_memory():
    """Create a test memory"""
    # Connect to the memory orchestrator
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5576")
    
    # Prepare request
    request = {
        "action": "create",
        "request_id": str(uuid.uuid4()),
        "session_id": "test-session",
        "payload": {
            "memory_type": "test",
            "content": {
                "text": "This is a test memory",
                "source_agent": "test_script"
            },
            "tags": ["test", "verification"],
            "priority": 3
        }
    }
    
    # Send request
    socket.send(json.dumps(request).encode('utf-8'))
    
    # Receive response
    response = json.loads(socket.recv().decode('utf-8'))
    
    # Check for success
    if response.get("status") != "success":
        raise Exception(f"Failed to create memory: {response}")
    
    # Return the memory ID
    memory_id = response.get("data", {}).get("memory_id")
    return memory_id

def read_memory(memory_id):
    """Read a memory by ID"""
    # Connect to the memory orchestrator
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5576")
    
    # Prepare request
    request = {
        "action": "read",
        "request_id": str(uuid.uuid4()),
        "session_id": "test-session",
        "payload": {
            "memory_id": memory_id
        }
    }
    
    # Send request
    socket.send(json.dumps(request).encode('utf-8'))
    
    # Receive response
    response = json.loads(socket.recv().decode('utf-8'))
    
    # Check for success
    if response.get("status") != "success":
        raise Exception(f"Failed to read memory: {response}")
    
    # Return the memory data
    return response.get("data", {})

def update_memory(memory_id, new_content):
    """Update a memory"""
    # Connect to the memory orchestrator
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5576")
    
    # Prepare request
    request = {
        "action": "update",
        "request_id": str(uuid.uuid4()),
        "session_id": "test-session",
        "payload": {
            "memory_id": memory_id,
            "content": {
                "text": new_content,
                "source_agent": "test_script",
                "updated": True
            },
            "tags": ["test", "verification", "updated"],
            "priority": 4
        }
    }
    
    # Send request
    socket.send(json.dumps(request).encode('utf-8'))
    
    # Receive response
    response = json.loads(socket.recv().decode('utf-8'))
    
    # Check for success
    if response.get("status") != "success":
        raise Exception(f"Failed to update memory: {response}")
    
    # Return the updated timestamp
    return response.get("data", {}).get("updated_at")

def delete_memory(memory_id):
    """Delete a memory"""
    # Connect to the memory orchestrator
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5576")
    
    # Prepare request
    request = {
        "action": "delete",
        "request_id": str(uuid.uuid4()),
        "session_id": "test-session",
        "payload": {
            "memory_id": memory_id
        }
    }
    
    # Send request
    socket.send(json.dumps(request).encode('utf-8'))
    
    # Receive response
    response = json.loads(socket.recv().decode('utf-8'))
    
    # Check for success
    if response.get("status") != "success":
        raise Exception(f"Failed to delete memory: {response}")
    
    # Return whether it was deleted
    return response.get("data", {}).get("deleted", False)

def main():
    """Main entry point"""
    print("Starting Memory Orchestrator test...")
    
    # Start the memory orchestrator in a separate process
    import multiprocessing
    import time
    
    # Create and start the memory orchestrator process
    orchestrator_process = multiprocessing.Process(
        target=lambda: MemoryOrchestrator().start()
    )
    orchestrator_process.start()
    
    # Wait for the orchestrator to start
    time.sleep(1)
    
    try:
        # Run the tests
        test_memory_operations()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Terminate the orchestrator process
        orchestrator_process.terminate()
        orchestrator_process.join()

if __name__ == "__main__":
    main() 