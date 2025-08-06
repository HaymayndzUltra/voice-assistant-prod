import zmq
import json
import time
import logging
from datetime import datetime
from common.env_helpers import get_env
from common.utils.log_setup import configure_logging

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

def test_learning_analysis():
    """Test learning analysis functionality."""
    context = None  # Using pool
    socket = get_req_socket(endpoint).socket
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5630")
    
    # Test data
    test_data = {
        "action": "analyze_learning",
        "data": {
            "confidence": 0.85,
            "performance": 0.92,
            "context": {
                "task_type": "translation",
                "language_pair": "en-tl",
                "complexity": "medium"
            }
        }
    }
    
    try:
        socket.send_json(test_data)
        response = socket.recv_json()
        logger.info(f"Learning Analysis Response: {json.dumps(response, indent=2)}")
        return response.get('status') == 'success'
    except Exception as e:
        logger.error(f"Error testing learning analysis: {str(e)}")
        return False
    finally:
def test_memory_optimization():
    """Test memory optimization functionality."""
    context = None  # Using pool
    socket = get_req_socket(endpoint).socket
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5630")
    
    # Test data
    test_data = {
        "action": "optimize_memory",
        "threshold": 0.8,
        "cache_size": 1000
    }
    
    try:
        socket.send_json(test_data)
        response = socket.recv_json()
        logger.info(f"Memory Optimization Response: {json.dumps(response, indent=2)}")
        return response.get('status') in ['normal', 'optimized']
    except Exception as e:
        logger.error(f"Error testing memory optimization: {str(e)}")
        return False
    finally:
def test_system_monitoring():
    """Test system monitoring functionality."""
    context = None  # Using pool
    socket = get_req_socket(endpoint).socket
    socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
    socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5630")
    
    # Test data
    test_data = {
        "action": "monitor_system"
    }
    
    try:
        socket.send_json(test_data)
        response = socket.recv_json()
        logger.info(f"System Monitoring Response: {json.dumps(response, indent=2)}")
        return response.get('status') == 'success'
    except Exception as e:
        logger.error(f"Error testing system monitoring: {str(e)}")
        return False
    finally:
def run_tests():
    """Run all tests and generate report."""
    logger.info("Starting MetaCognition Agent Tests...")
    
    tests = {
        "Learning Analysis": test_learning_analysis,
        "Memory Optimization": test_memory_optimization,
        "System Monitoring": test_system_monitoring
    }
    
    results = {}
    for test_name, test_func in tests.items():
        logger.info(f"\nRunning {test_name} test...")
        start_time = time.time()
        success = test_func()
        duration = time.time() - start_time
        
        results[test_name] = {
            "status": "✅ PASS" if success else "❌ FAIL",
            "duration": f"{duration:.2f}s"
        }
    
    # Print test report
    logger.info("\n=== Test Report ===")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    for test_name, result in results.items():
        logger.info(f"{test_name}: {result['status']} ({result['duration']})")
    
    # Calculate overall status
    all_passed = all("PASS" in result["status"] for result in results.values())
    logger.info("=" * 50)
    logger.info(f"Overall Status: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

if __name__ == "__main__":
    run_tests() 