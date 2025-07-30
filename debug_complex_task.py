#!/usr/bin/env python3
"""Debug script to test complex tasks that trigger LLM parsing"""

import logging
import traceback
from workflow_memory_intelligence_fixed import execute_task_intelligently

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

def test_complex_tasks():
    """Test complex tasks that should trigger LLM parsing"""

    complex_tasks = [
        "Build a comprehensive microservices architecture with load balancing, service discovery, and distributed logging",
        "Implement a machine learning pipeline with data preprocessing, model training, validation, and deployment to production",
        "Create a real-time chat application with WebSocket connections, message persistence, user authentication, and file sharing capabilities",
        # Test with the Docker task from earlier
        """- Phase 1: System Analysis & Cleanup
        - Inventory all existing Docker/Podman containers, images, and compose files.
        - Delete all old containers/images/compose files.
        - Identify all agent groups, dependencies, and required libraries.
    - Phase 2: Logical Grouping & Compose Generation
        - Design optimal container groupings (by function, dependency, resource needs).
        - Generate new docker-compose SoT with correct build contexts, volumes, networks, and healthchecks.
        - Ensure requirements.txt per container is minimal and correct.
    - Phase 3: Validation & Optimization
        - Build and start all containers in dependency-correct order.
        - Validate agent startup, health, and inter-container communication.
        - Optimize for image size, startup time, and resource usage.
        - Document the new architecture and compose setup."""
    ]

    for i, task in enumerate(complex_tasks, 1):
        print(f"\n=== Testing Complex Task {i} ===")
        print(f"Task: {task[:100]}...")

        try:
            result = execute_task_intelligently(task)
            print(f"✅ Success: {result.get('execution_type', 'Unknown')}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            print(f"ERROR TYPE: {type(e)}")
            print("FULL TRACEBACK:")
            traceback.print_exc()
            # Continue to next task instead of stopping
            continue

if __name__ == "__main__":
    test_complex_tasks()
