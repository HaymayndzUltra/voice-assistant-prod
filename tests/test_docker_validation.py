"""
Test to validate the Docker environment is working correctly.
This is a simple test that should always pass.
"""

import os
import sys
import pytest

def test_docker_environment():
    """Test that the Docker environment is set up correctly."""
    # Check that PYTHONPATH is set correctly
    assert "/app" in sys.path, "PYTHONPATH should include /app"
    
    # Check that TEST_MODE environment variable is set
    assert os.environ.get("TEST_MODE") == "true", "TEST_MODE environment variable should be set to 'true'"
    
    # Check that we can import key modules
    import numpy
    import yaml
    import requests
    import psutil
    import zmq
    
    # Check that we can access the file system
    assert os.path.exists("/app/common"), "Should be able to access /app/common directory"
    assert os.path.exists("/app/main_pc_code"), "Should be able to access /app/main_pc_code directory"
    assert os.path.exists("/app/tests"), "Should be able to access /app/tests directory"
    
    # This test should always pass
    assert True, "Docker environment validation test" 