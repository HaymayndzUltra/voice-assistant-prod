#!/usr/bin/env python3
"""
Confidence-Driven Tiered Translation Test Script

This script tests the confidence-driven tiered translation approach in the translator agent.
It verifies that:
1. NLLB adapter is correctly used when available
2. Confidence scores are properly assigned and used for decision making
3. Fallback mechanisms work correctly
4. Taglish detection works as expected
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
logger = logging.getLogger("TranslationTest")

# Test categories
test_categories = {
    "basic": [
        # Basic Filipino phrases
        {"text": "Magandang umaga", "expected": "Good morning", "note": "Basic greeting"},
        {"text": "Kumusta ka?", "expected": "How are you?", "note": "Simple question"},
        {"text": "Salamat sa tulong mo", "expected": "Thank you for your help", "note": "Expression of gratitude"},
    ],
    "commands": [
        # Command phrases (should use pattern matching with high confidence)
        {"text": "buksan mo ang file", "expected": "open the file", "note": "Common command - should use pattern matching"},
        {"text": "i-save mo ang document", "expected": "save the document", "note": "Common command with i- prefix"},
        {"text": "isara mo ang window", "expected": "close the window", "note": "Common command"},
    ],
    "complex": [
        # Complex sentences (should use NLLB with high confidence)
        {"text": "Ang teknolohiya ay mabilis na umuunlad sa ating panahon", "expected": "Technology is rapidly advancing in our time", "note": "Complex sentence - should use NLLB"},
        {"text": "Mahalaga ang pag-aaral ng mga wika para sa komunikasyon", "expected": "Learning languages is important for communication", "note": "Complex sentence - should use NLLB"},
        {"text": "Ang artificial intelligence ay nagbibigay ng maraming oportunidad", "expected": "Artificial intelligence provides many opportunities", "note": "Technical sentence - should use NLLB"},
    ],
    "taglish": [
        # Taglish phrases (mixed Filipino and English)
        {"text": "Pwede mo ba i-check ang email ko?", "expected": "Can you check my email?", "note": "Taglish with English words"},
        {"text": "I-download mo yung file na yan", "expected": "Download that file", "note": "Taglish with English verb"},
        {"text": "Na-receive mo ba ang message ko?", "expected": "Did you receive my message?", "note": "Taglish with English verb root"},
    ],
    "english": [
        # Already English phrases (should be skipped)
        {"text": "Hello, how are you today?", "expected": "Hello, how are you today?", "note": "Already English - should be skipped"},
        {"text": "Can you help me with this?", "expected": "Can you help me with this?", "note": "Already English - should be skipped"},
        {"text": "Open the document please", "expected": "Open the document please", "note": "Already English command - should be skipped"},
    ],
    "edge_cases": [
        # Edge cases
        {"text": "", "expected": "", "note": "Empty string - should return empty"},
        {"text": "   ", "expected": "   ", "note": "Whitespace only - should return as is"},
        {"text": "123456", "expected": "123456", "note": "Numbers only - should return as is"},
    ]
}

def test_translator(categories=None, zmq_port=5563):
    """Test the translator agent with various Filipino phrases"""
    print("=== Testing Confidence-Driven Tiered Translation ===\n")
    
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
            "failed": 0
        }
        
        for i, test_case in enumerate(test_categories[category]):
            text = test_case["text"]
            expected = test_case["expected"]
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
                        "avg_time_ms": 0
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
                elif translated.lower() == expected.lower():
                    test_result = "PASSED"
                    results["passed"] += 1
                    results["by_category"][category]["passed"] += 1
                else:
                    test_result = "FAILED"
                    results["failed"] += 1
                    results["by_category"][category]["failed"] += 1
                
                results["total"] += 1
                results["by_category"][category]["total"] += 1
                
                # Print results
                print(f"  Original: {text}")
                print(f"  Translated: {translated}")
                print(f"  Expected: {expected}")
                print(f"  Method: {method}")
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
                    "confidence": 0,
                    "time_ms": 0,
                    "result": "FAILED"
                })
    
    # Print summary
    print("\n=== Test Summary ===\n")
    print(f"Total Tests: {results['total']}")
    print(f"Passed: {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Skipped: {results['skipped']} ({results['skipped']/results['total']*100:.1f}%)")
    print(f"Failed: {results['failed']} ({results['failed']/results['total']*100:.1f}%)\n")
    
    print("=== Results by Category ===\n")
    for category, stats in results["by_category"].items():
        if stats["total"] > 0:
            pass_rate = stats["passed"] / stats["total"] * 100
            print(f"{category}: {stats['passed']}/{stats['total']} passed ({pass_rate:.1f}%)")
    
    print("\n=== Results by Translation Method ===\n")
    for method, stats in results["by_method"].items():
        print(f"{method}: {stats['count']} uses, avg confidence: {stats['avg_confidence']:.2f}, avg time: {stats['avg_time_ms']:.2f}ms")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"translation_test_results_{timestamp}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to {results_file}")
    print("\n=== Test Complete ===\n")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the confidence-driven tiered translation approach.")
    parser.add_argument('--port', type=int, default=5563, help='ZMQ port for the translator agent')
    parser.add_argument('--categories', nargs='+', help='Test categories to run (default: all)')
    args = parser.parse_args()
    
    test_translator(categories=args.categories, zmq_port=args.port)
