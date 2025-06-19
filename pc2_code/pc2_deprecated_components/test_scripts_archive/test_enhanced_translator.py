#!/usr/bin/env python3
"""
Enhanced Translator Test Script
Tests all major features of the enhanced translator system
"""
import zmq
import json
import time
import logging
from pathlib import Path
import sys
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translator_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TranslatorTest")

class TranslatorTester:
    def __init__(self, host="localhost", port=5563, health_port=5559):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{host}:{port}")
        
        self.health_socket = self.context.socket(zmq.REQ)
        self.health_socket.connect(f"tcp://{host}:{health_port}")
        
        self.test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }

    def test_basic_translation(self):
        """Test basic translation functionality"""
        test_cases = [
            ("buksan mo ang file", "open file"),
            ("i-save mo ang document", "save document"),
            ("magsimula ng bagong project", "start new project"),
            ("i-download mo ang file na iyon", "download that file"),
            ("i-save mo ito", "save this"),
            ("Can you please i-open ang file na ito?", "Can you please open this file?")
        ]
        
        logger.info("Testing basic translations...")
        for filipino, expected in test_cases:
            self.test_results["total"] += 1
            try:
                result = self._send_translation_request(filipino)
                if result.get("status") == "ok":
                    translation = result.get("translation", "").lower()
                    if expected.lower() in translation:
                        logger.info(f"[PASS] '{filipino}' -> '{translation}'")
                        self.test_results["passed"] += 1
                    else:
                        logger.error(f"[FAIL] '{filipino}' -> '{translation}' (Expected: '{expected}')")
                        self.test_results["failed"] += 1
                        self.test_results["errors"].append(f"Translation mismatch: {filipino}")
                else:
                    logger.error(f"[ERROR] {result.get('error', 'Unknown error')}")
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"Request failed: {filipino}")
            except Exception as e:
                logger.error(f"[EXCEPTION] {str(e)}")
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"Exception: {str(e)}")

    def test_context_awareness(self):
        """Test context-aware translation"""
        test_cases = [
            ("technical", "i-debug mo ang code", "debug code"),
            ("file_ops", "buksan mo ang folder", "open folder"),
            ("system_ops", "i-restart mo ang computer", "restart computer"),
            ("app_ops", "i-update mo ang program", "update program")
        ]
        
        logger.info("\nTesting context awareness...")
        for context, filipino, expected in test_cases:
            self.test_results["total"] += 1
            try:
                result = self._send_translation_request(filipino, context=context)
                if result.get("status") == "ok":
                    translation = result.get("translation", "").lower()
                    if expected.lower() in translation:
                        logger.info(f"[PASS] [{context}] '{filipino}' -> '{translation}'")
                        self.test_results["passed"] += 1
                    else:
                        logger.error(f"[FAIL] [{context}] '{filipino}' -> '{translation}' (Expected: '{expected}')")
                        self.test_results["failed"] += 1
                        self.test_results["errors"].append(f"Context mismatch [{context}]: {filipino}")
                else:
                    logger.error(f"[ERROR] [{context}] {result.get('error', 'Unknown error')}")
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"Request failed [{context}]: {filipino}")
            except Exception as e:
                logger.error(f"[EXCEPTION] [{context}] {str(e)}")
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"Exception [{context}]: {str(e)}")

    def test_error_recovery(self):
        """Test error recovery and circuit breaker"""
        logger.info("\nTesting error recovery...")
        
        # Test invalid input
        self.test_results["total"] += 1
        try:
            result = self._send_translation_request("")
            if result.get("status") == "error":
                logger.info("[PASS] Properly handled empty input")
                self.test_results["passed"] += 1
            else:
                logger.error("[FAIL] Should have rejected empty input")
                self.test_results["failed"] += 1
                self.test_results["errors"].append("Empty input not rejected")
        except Exception as e:
            logger.error(f"[EXCEPTION] {str(e)}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"Exception: {str(e)}")

    def test_performance(self):
        """Test performance with multiple requests"""
        logger.info("\nTesting performance...")
        
        # Send multiple requests quickly
        start_time = time.time()
        requests = 10
        self.test_results["total"] += requests
        
        for i in range(requests):
            try:
                result = self._send_translation_request(f"test request {i}")
                if result.get("status") in ["ok", "queued"]:
                    self.test_results["passed"] += 1
                else:
                    self.test_results["failed"] += 1
                    self.test_results["errors"].append(f"Performance test request {i} failed")
            except Exception as e:
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"Exception in performance test: {str(e)}")
        
        duration = time.time() - start_time
        logger.info(f"Processed {requests} requests in {duration:.2f} seconds")
        logger.info(f"Average time per request: {duration/requests:.2f} seconds")

    def test_health_check(self):
        """Test health check functionality"""
        logger.info("\nTesting health check...")
        self.test_results["total"] += 1
        
        try:
            self.health_socket.send_string(json.dumps({"action": "health_check"}))
            if self.health_socket.poll(5000) == 0:
                logger.error("[FAIL] Health check timeout")
                self.test_results["failed"] += 1
                self.test_results["errors"].append("Health check timeout")
                return
                
            response = json.loads(self.health_socket.recv_string())
            if response.get("status") == "ok":
                logger.info("[PASS] Health check successful")
                logger.info(f"Health metrics: {json.dumps(response, indent=2)}")
                self.test_results["passed"] += 1
            else:
                logger.error(f"[FAIL] Health check returned error: {response.get('error')}")
                self.test_results["failed"] += 1
                self.test_results["errors"].append(f"Health check error: {response.get('error')}")
        except Exception as e:
            logger.error(f"[EXCEPTION] {str(e)}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"Health check exception: {str(e)}")

    def _send_translation_request(self, text, context=None):
        """Send translation request to the translator"""
        request = {
            "action": "translate",
            "text": text,
            "source_lang": "tl",
            "target_lang": "en"
        }
        if context:
            request["context"] = context
            
        self.socket.send_string(json.dumps(request))
        if self.socket.poll(5000) == 0:
            return {"status": "error", "error": "Request timeout"}
        return json.loads(self.socket.recv_string())

    def run_all_tests(self):
        """Run all test cases"""
        logger.info("Starting comprehensive translator tests...")
        
        self.test_basic_translation()
        self.test_context_awareness()
        self.test_error_recovery()
        self.test_performance()
        self.test_health_check()
        
        # Print summary
        logger.info("\n=== Test Summary ===")
        logger.info(f"Total tests: {self.test_results['total']}")
        logger.info(f"Passed: {self.test_results['passed']}")
        logger.info(f"Failed: {self.test_results['failed']}")
        
        if self.test_results["errors"]:
            logger.info("\nErrors encountered:")
            for error in self.test_results["errors"]:
                logger.error(f"- {error}")
        
        return self.test_results["failed"] == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default="localhost", help='Translator host')
    parser.add_argument('--port', type=int, default=5563, help='Translator port')
    parser.add_argument('--health-port', type=int, default=5559, help='Health check port')
    args = parser.parse_args()
    
    tester = TranslatorTester(args.host, args.port, args.health_port)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1) 