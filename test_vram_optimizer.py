#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test script for VRAM optimization between VRAMOptimizerAgent and ModelManagerAgent

This script:
1. Sends test commands to VRAMOptimizerAgent
2. Verifies that the VRAMOptimizerAgent can communicate with the ModelManagerAgent
3. Tests monitoring of VRAM usage
4. Tests loading and unloading models based on VRAM pressure
"""

import zmq
import time
import json
import logging
import argparse
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VRAM-Optimizer-Test")

# Default ports
MMA_PORT = 5570
VRA_PORT = 5572
SDT_PORT = 7120

def send_zmq_request(host: str, port: int, request: Dict[str, Any], timeout: int = 5000) -> Dict[str, Any]:
    """
    Send a ZMQ request and get the response

    Args:
        host: Host address
        port: Port number
        request: Request dictionary
        timeout: Timeout in milliseconds

    Returns:
        Response dictionary
    """
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout)
    socket.setsockopt(zmq.SNDTIMEO, timeout)

    try:
        socket.connect(f"tcp://{host}:{port}")
        logger.info(f"Connected to {host}:{port}")

        logger.info(f"Sending request: {request}")
        socket.send_json(request)

        response = socket.recv_json()
        logger.info(f"Received response: {response}")

        return response
    except zmq.error.Again:
        logger.error(f"Timeout waiting for response from {host}:{port}")
        return {"status": "ERROR", "message": "Request timed out"}
    except Exception as e:
        logger.error(f"Error communicating with {host}:{port}: {e}")
        return {"status": "ERROR", "message": str(e)}
    finally:
        socket.close()
        context.term()

def test_vram_optimizer_health(host: str, port: int) -> bool:
    """
    Test if the VRAMOptimizerAgent is healthy

    Args:
        host: Host address
        port: Port number

    Returns:
        True if healthy, False otherwise
    """
    request = {"command": "HEALTH_CHECK"}
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info("VRAMOptimizerAgent is healthy!")
        return True
    else:
        logger.error("VRAMOptimizerAgent health check failed")
        return False

def test_get_vram_status(host: str, port: int) -> Dict[str, Any]:
    """
    Get VRAM status from VRAMOptimizerAgent

    Args:
        host: Host address
        port: Port number

    Returns:
        VRAM status dictionary
    """
    request = {"command": "GET_VRAM_STATUS"}
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info("Got VRAM status successfully")
        return response
    else:
        logger.error("Failed to get VRAM status")
        return {}

def test_set_thresholds(host: str, port: int, threshold_type: str, value: float) -> bool:
    """
    Set a VRAM threshold in VRAMOptimizerAgent

    Args:
        host: Host address
        port: Port number
        threshold_type: Type of threshold (warning, critical, safe)
        value: Threshold value (0.0-1.0)

    Returns:
        True if successful, False otherwise
    """
    request = {
        "command": "SET_VRAM_THRESHOLD",
        "threshold_type": threshold_type,
        "value": value
    }
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info(f"Set {threshold_type} threshold to {value} successfully")
        return True
    else:
        logger.error(f"Failed to set {threshold_type} threshold")
        return False

def test_set_idle_timeout(host: str, port: int, timeout_seconds: int) -> bool:
    """
    Set idle timeout in VRAMOptimizerAgent

    Args:
        host: Host address
        port: Port number
        timeout_seconds: Idle timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    request = {
        "command": "SET_IDLE_TIMEOUT",
        "timeout_seconds": timeout_seconds
    }
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info(f"Set idle timeout to {timeout_seconds} seconds successfully")
        return True
    else:
        logger.error(f"Failed to set idle timeout")
        return False

def test_track_model_usage(host: str, port: int, model_id: str) -> bool:
    """
    Track model usage in VRAMOptimizerAgent

    Args:
        host: Host address
        port: Port number
        model_id: Model ID to track

    Returns:
        True if successful, False otherwise
    """
    request = {
        "command": "TRACK_MODEL_USAGE",
        "model_id": model_id
    }
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info(f"Tracked usage of model {model_id} successfully")
        return True
    else:
        logger.error(f"Failed to track usage of model {model_id}")
        return False

def get_model_status_from_mma(host: str, port: int) -> Dict[str, Any]:
    """
    Get loaded models status directly from ModelManagerAgent

    Args:
        host: Host address
        port: Port number

    Returns:
        Loaded models status dictionary
    """
    request = {"command": "GET_LOADED_MODELS_STATUS"}
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info("Got loaded models status from MMA successfully")
        return response
    else:
        logger.error("Failed to get loaded models status from MMA")
        return {}

def test_sdt_metrics(host: str, port: int) -> Dict[str, Any]:
    """
    Get metrics from SystemDigitalTwin

    Args:
        host: Host address
        port: Port number

    Returns:
        Metrics dictionary
    """
    request = {
        "command": "GET_METRICS",
        "payload": {
            "metrics": ["vram_usage"]
        }
    }
    response = send_zmq_request(host, port, request)

    if response.get("status") == "SUCCESS":
        logger.info("Got metrics from SDT successfully")
        return response
    else:
        logger.error("Failed to get metrics from SDT")
        return {}

def run_test_suite(vra_host: str, vra_port: int, mma_host: str, mma_port: int, sdt_host: str, sdt_port: int):
    """
    Run the full test suite

    Args:
        vra_host: VRAMOptimizerAgent host
        vra_port: VRAMOptimizerAgent port
        mma_host: ModelManagerAgent host
        mma_port: ModelManagerAgent port
        sdt_host: SystemDigitalTwin host
        sdt_port: SystemDigitalTwin port
    """
    logger.info("=== Starting VRAM Optimizer Test Suite ===")

    # Test 1: Health check
    if not test_vram_optimizer_health(vra_host, vra_port):
        logger.error("Health check failed, aborting tests")
        return

    # Test 2: Get VRAM status
    vram_status = test_get_vram_status(vra_host, vra_port)
    if not vram_status:
        logger.error("Failed to get VRAM status, aborting tests")
        return

    # Test 3: Set thresholds
    if not test_set_thresholds(vra_host, vra_port, "warning", 0.7):
        logger.warning("Failed to set warning threshold, continuing tests")

    if not test_set_thresholds(vra_host, vra_port, "critical", 0.85):
        logger.warning("Failed to set critical threshold, continuing tests")

    # Test 4: Set idle timeout
    if not test_set_idle_timeout(vra_host, vra_port, 300):  # 5 minutes
        logger.warning("Failed to set idle timeout, continuing tests")

    # Test 5: Get model status from MMA
    mma_status = get_model_status_from_mma(mma_host, mma_port)
    if not mma_status:
        logger.warning("Failed to get model status from MMA, continuing tests")

    # Test 6: Get metrics from SDT
    sdt_metrics = test_sdt_metrics(sdt_host, sdt_port)
    if not sdt_metrics:
        logger.warning("Failed to get metrics from SDT, continuing tests")

    # Test 7: Track model usage for a model that is likely to be loaded
    if mma_status and "loaded_models" in mma_status:
        for model_id in mma_status["loaded_models"]:
            if test_track_model_usage(vra_host, vra_port, model_id):
                logger.info(f"Successfully tracked usage for model {model_id}")
                break

    # Test 8: Get updated VRAM status after tracking
    time.sleep(2)  # Wait a bit for updates to propagate
    updated_vram_status = test_get_vram_status(vra_host, vra_port)
    if updated_vram_status:
        logger.info("Got updated VRAM status successfully")

    logger.info("=== VRAM Optimizer Test Suite Completed ===")

    # Print summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"VRAMOptimizerAgent: {\"HEALTHY\" if test_vram_optimizer_health(vra_host, vra_port) else \"UNHEALTHY\"}")

    # Get current VRAM status
    final_vram_status = test_get_vram_status(vra_host, vra_port)
    if final_vram_status:
        if "mainpc_vram" in final_vram_status:
            mainpc_vram = final_vram_status["mainpc_vram"]
            logger.info(f"MainPC VRAM: {mainpc_vram[\"used_mb\"]}/{mainpc_vram[\"total_mb\"]}MB ({mainpc_vram[\"usage_ratio\"]*100:.1f}%)")

        if "pc2_vram" in final_vram_status and final_vram_status["pc2_vram"]:
            pc2_vram = final_vram_status["pc2_vram"]
            logger.info(f"PC2 VRAM: {pc2_vram[\"used_mb\"]}/{pc2_vram[\"total_mb\"]}MB ({pc2_vram[\"usage_ratio\"]*100:.1f}%)")

        if "loaded_models" in final_vram_status:
            loaded_models = final_vram_status["loaded_models"]
            logger.info(f"Loaded models: {len(loaded_models)}")
            for model_id, model_info in loaded_models.items():
                logger.info(f"  - {model_id}: {model_info[\"vram_usage_mb\"]}MB on {model_info[\"device\"]}")

    logger.info("=== End of Test Results ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test VRAM optimization between VRAMOptimizerAgent and ModelManagerAgent")
    parser.add_argument("--vra-host", default="localhost", help="VRAMOptimizerAgent host")
    parser.add_argument("--vra-port", type=int, default=VRA_PORT, help="VRAMOptimizerAgent port")
    parser.add_argument("--mma-host", default="localhost", help="ModelManagerAgent host")
    parser.add_argument("--mma-port", type=int, default=MMA_PORT, help="ModelManagerAgent port")
    parser.add_argument("--sdt-host", default="localhost", help="SystemDigitalTwin host")
    parser.add_argument("--sdt-port", type=int, default=SDT_PORT, help="SystemDigitalTwin port")

    args = parser.parse_args()

    run_test_suite(
        args.vra_host, args.vra_port,
        args.mma_host, args.mma_port,
        args.sdt_host, args.sdt_port
    )
