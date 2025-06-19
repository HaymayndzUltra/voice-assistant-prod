#!/usr/bin/env python3
"""
NLLB Adapter Integration Test Script

This script tests the integration of the NLLB adapter with the translator agent,
focusing on pattern matching priority, confidence scoring, and fallback mechanisms.
"""
import sys
import os
import json
import zmq
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from tabulate import tabulate

# Add the parent directory to the path to import the agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NLLBIntegrationTest")

# Test categories
test_categories = {
    "commands": [
        # Command phrases (should use pattern matching with high confidence)
        {"text": "buksan mo ang file", "expected": "open the file", "expected_method": "pattern", "note": "Common command - should use pattern matching"},
        {"text": "i-save mo ang document", "expected": "save the document", "expected_method": "pattern", "note": "Common command with i- prefix"},
        {"text": "isara mo ang window", "expected": "close the window", "expected_method": "pattern", "note": "Common command"},
        {"text": "i-download mo ang file na iyon", "expected": "download that file", "expected_method": "pattern", "note": "Special case command"},
        {"text": "i-delete mo ang file na ito", "expected": "delete this file", "expected_method": "pattern", "note": "Command with 'ito'"},
    ],
    "complex": [
        # Complex sentences (should use NLLB with high confidence)
        {"text": "Ang teknolohiya ay mabilis na umuunlad sa ating panahon", "expected": "Technology is rapidly advancing in our time", "expected_method": "nllb", "note": "Complex sentence - should use NLLB"},
        {"text": "Mahalaga ang pag-aaral ng mga wika para sa komunikasyon", "expected": "Learning languages is important for communication", "expected_method": "nllb", "note": "Complex sentence - should use NLLB"},
        {"text": "Ang artificial intelligence ay nagbibigay ng maraming oportunidad", "expected": "Artificial intelligence provides many opportunities", "expected_method": "nllb", "note": "Technical sentence - should use NLLB"},
    ],
    "taglish": [
        # Taglish phrases (mixed Filipino and English)
        {"text": "Pwede mo ba i-check ang email ko?", "expected": "Can you check my email?", "expected_method": "nllb", "note": "Taglish with English words"},
        {"text": "I-download mo yung file na yan", "expected": "Download that file", "expected_method": "pattern", "note": "Taglish with English verb"},
        {"text": "Na-receive mo ba ang message ko?", "expected": "Did you receive my message?", "expected_method": "nllb", "note": "Taglish with English verb root"},
    ],
    "english": [
        # Already English phrases (should be skipped)
        {"text": "Hello, how are you today?", "expected": "Hello, how are you today?", "expected_method": "skipped", "note": "Already English - should be skipped"},
        {"text": "Can you help me with this?", "expected": "Can you help me with this?", "expected_method": "skipped", "note": "Already English - should be skipped"},
        {"text": "Open the document please", "expected": "Open the document please", "expected_method": "skipped", "note": "Already English command - should be skipped"},
    ],
    "edge_cases": [
        # Edge cases
        {"text": "", "expected": "", "expected_method": "none", "note": "Empty string - should return empty"},
        {"text": "   ", "expected": "   ", "expected_method": "none", "note": "Whitespace only - should return as is"},
        {"text": "123456", "expected": "123456", "expected_method": "none", "note": "Numbers only - should return as is"},
    ]
}

def test_nllb_integration(categories=None, zmq_port=5563, detailed=False):
    """Test the NLLB adapter integration with the translator agent"""
    print("=== Testing NLLB Adapter Integration ===\n")
    
    # Connect to the translator agent
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{zmq_port}")  # Translator agent REQ/REP port
    socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
    
    print(f"Connected to Translator Agent on port {zmq_port}\n")
    
    # If no categories specified, test all
    if not categories:
        categories = list(test_categories.keys())
    
    results = {
        "total": 0,
        "passed": 0,
        "skipped": 0,
        "failed": 0,
        "method_match": 0,  # Count of tests where the method used matches expected method
        "by_method": {},
        "by_category": {},
        "tests": []
    }
    
    # Run tests for each selected category
    for category in categories:
        if category not in test_categories:
            print(f"Warning: Category '{category}' not found. Skipping.")
            continue
            
        print(f"\n=== Testing Category: {category} ===\n")
        results["by_category"][category] = {
            "total": 0,
            "passed": 0,
            "skipped": 0,
            "failed": 0,
            "method_match": 0
        }
        
        for i, test_case in enumerate(test_categories[category]):
            text = test_case["text"]
            expected = test_case["expected"]
            expected_method = test_case.get("expected_method", "any")
            note = test_case.get("note", "")
            
            print(f"Test {i+1}: '{text}' ({note})")
            
            # Create request
            request = {
                "action": "translate",
                "text": text,
                "source_lang": "tl",
                "target_lang": "en",
                "request_id": f"test_{category}_{i+1}"
            }
            
            # Send request
            try:
                socket.send_json(request)
                
                # Wait for response
                response = socket.recv_json()
                
                # Extract results
                translated = response.get('text', 'ERROR')
                method = response.get('translation_method', 'unknown')
                confidence = response.get('confidence_score', 0)
                status = response.get('translation_status', 'unknown')
                time_ms = response.get('translation_time_ms', 0)
                
                # Track method statistics
                if method not in results["by_method"]:
                    results["by_method"][method] = {
                        "count": 0,
                        "avg_confidence": 0,
                        "avg_time_ms": 0,
                        "passed": 0,
                        "failed": 0
                    }
                
                results["by_method"][method]["count"] += 1
                prev_avg_conf = results["by_method"][method]["avg_confidence"]
                prev_avg_time = results["by_method"][method]["avg_time_ms"]
                count = results["by_method"][method]["count"]
                
                # Update running averages
                results["by_method"][method]["avg_confidence"] = (prev_avg_conf * (count - 1) + confidence) / count
                results["by_method"][method]["avg_time_ms"] = (prev_avg_time * (count - 1) + time_ms) / count
                
                # Determine test result
                if method.startswith("skipped_"):
                    test_result = "SKIPPED"
                    results["skipped"] += 1
                    results["by_category"][category]["skipped"] += 1
                    results["by_method"][method]["passed"] += 1
                elif translated.lower().strip() == expected.lower().strip():
                    test_result = "PASSED"
                    results["passed"] += 1
                    results["by_category"][category]["passed"] += 1
                    results["by_method"][method]["passed"] += 1
                else:
                    test_result = "FAILED"
                    results["failed"] += 1
                    results["by_category"][category]["failed"] += 1
                    results["by_method"][method]["failed"] += 1
                
                # Check if the method used matches the expected method
                method_match = False
                if expected_method == "any" or method.startswith(expected_method):
                    method_match = True
                    results["method_match"] += 1
                    results["by_category"][category]["method_match"] += 1
                
                results["total"] += 1
                results["by_category"][category]["total"] += 1
                
                # Print results
                print(f"  Original: {text}")
                print(f"  Translated: {translated}")
                print(f"  Expected: {expected}")
                print(f"  Method: {method}")
                print(f"  Expected Method: {expected_method}")
                print(f"  Method Match: {'✓' if method_match else '✗'}")
                print(f"  Confidence: {confidence:.2f}")
                print(f"  Time: {time_ms:.2f}ms")
                print(f"  Result: {test_result}\n")
                
                # Store test details
                results["tests"].append({
                    "category": category,
                    "text": text,
                    "translated": translated,
                    "expected": expected,
                    "method": method,
                    "expected_method": expected_method,
                    "method_match": method_match,
                    "confidence": confidence,
                    "time_ms": time_ms,
                    "result": test_result
                })
                
                # Small delay between requests
                time.sleep(0.5)
                
            except zmq.error.Again:
                print(f"  ERROR: Timeout waiting for response")
                results["failed"] += 1
                results["by_category"][category]["failed"] += 1
                results["total"] += 1
                results["by_category"][category]["total"] += 1
                
                # Store test details
                results["tests"].append({
                    "category": category,
                    "text": text,
                    "translated": "TIMEOUT",
                    "expected": expected,
                    "method": "timeout",
                    "expected_method": expected_method,
                    "method_match": False,
                    "confidence": 0,
                    "time_ms": 0,
                    "result": "FAILED"
                })
                
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                results["failed"] += 1
                results["by_category"][category]["failed"] += 1
                results["total"] += 1
                results["by_category"][category]["total"] += 1
                
                # Store test details
                results["tests"].append({
                    "category": category,
                    "text": text,
                    "translated": f"ERROR: {str(e)}",
                    "expected": expected,
                    "method": "error",
                    "expected_method": expected_method,
                    "method_match": False,
                    "confidence": 0,
                    "time_ms": 0,
                    "result": "FAILED"
                })
    
    # Print summary
    print("\n=== Test Summary ===\n")
    print(f"Total Tests: {results['total']}")
    print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Skipped: {results['skipped']} ({results['skipped']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)")
    print(f"Method Match: {results['method_match']} ({results['method_match']/results['total']*100:.1f}%)\n")
    
    print("=== Results by Category ===\n")
    category_table = []
    for category, stats in results["by_category"].items():
        if stats["total"] > 0:
            pass_rate = stats["passed"] / stats["total"] * 100
            method_match_rate = stats["method_match"] / stats["total"] * 100
            category_table.append([category, f"{stats['passed']}/{stats['total']}", f"{pass_rate:.1f}%", f"{stats['method_match']}/{stats['total']}", f"{method_match_rate:.1f}%"])
    
    print(tabulate(category_table, headers=["Category", "Passed", "Pass Rate", "Method Match", "Match Rate"], tablefmt="grid"))
    
    print("\n=== Results by Translation Method ===\n")
    method_table = []
    for method, stats in results["by_method"].items():
        if stats["count"] > 0:
            pass_rate = stats["passed"] / stats["count"] * 100
            method_table.append([method, stats["count"], f"{stats['passed']}/{stats['count']}", f"{pass_rate:.1f}%", f"{stats['avg_confidence']:.2f}", f"{stats['avg_time_ms']:.2f}ms"])
    
    print(tabulate(method_table, headers=["Method", "Count", "Passed", "Pass Rate", "Avg Confidence", "Avg Time"], tablefmt="grid"))
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"nllb_integration_test_{timestamp}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to {results_file}")
    
    # Generate detailed report if requested
    if detailed:
        detailed_file = f"nllb_integration_report_{timestamp}.txt"
        with open(detailed_file, "w", encoding="utf-8") as f:
            f.write("=== NLLB Integration Test Detailed Report ===\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Tests: {results['total']}\n")
            f.write(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)\n")
            f.write(f"Method Match: {results['method_match']} ({results['method_match']/results['total']*100:.1f}%)\n\n")
            
            f.write("=== Test Results ===\n\n")
            for test in results["tests"]:
                f.write(f"Category: {test['category']}\n")
                f.write(f"Original: {test['text']}\n")
                f.write(f"Translated: {test['translated']}\n")
                f.write(f"Expected: {test['expected']}\n")
                f.write(f"Method: {test['method']}\n")
                f.write(f"Expected Method: {test['expected_method']}\n")
                f.write(f"Method Match: {test['method_match']}\n")
                f.write(f"Confidence: {test['confidence']:.2f}\n")
                f.write(f"Time: {test['time_ms']:.2f}ms\n")
                f.write(f"Result: {test['result']}\n\n")
            
            f.write("=== Recommendations ===\n\n")
            # Generate recommendations based on results
            if results['method_match'] < results['total'] * 0.8:
                f.write("- Improve method selection logic to better prioritize pattern matching for commands\n")
            if any(stats["passed"] / stats["total"] < 0.7 for category, stats in results["by_category"].items() if category == "commands"):
                f.write("- Expand pattern matching dictionary with more command patterns\n")
            if any(stats["passed"] / stats["total"] < 0.7 for category, stats in results["by_category"].items() if category == "complex"):
                f.write("- Improve NLLB adapter translation quality for complex sentences\n")
            if any(stats["passed"] / stats["total"] < 0.7 for category, stats in results["by_category"].items() if category == "taglish"):
                f.write("- Enhance Taglish detection and handling\n")
        
        print(f"Detailed report saved to {detailed_file}")
    
    print("\n=== Test Complete ===\n")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the NLLB adapter integration with the translator agent.")
    parser.add_argument('--port', type=int, default=5563, help='ZMQ port for the translator agent')
    parser.add_argument('--categories', nargs='+', help='Test categories to run (default: all)')
    parser.add_argument('--detailed', action='store_true', help='Generate detailed report')
    args = parser.parse_args()
    
    test_nllb_integration(categories=args.categories, zmq_port=args.port, detailed=args.detailed)
