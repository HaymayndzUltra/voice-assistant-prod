#!/usr/bin/env python
"""
PC2 Translator Performance Benchmark
- Tests translation performance with various text lengths
- Measures translation time for each tier (Google, NLLB, Pattern Matching)
- Compares CPU vs GPU performance for NLLB adapter
- Outputs detailed metrics and charts
"""
import zmq
import json
import time
import random
import statistics
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from common.env_helpers import get_env

# Sample texts of varying lengths for testing
SAMPLE_TEXTS = {
    "short": [
        "Buksan ang ilaw",
        "Ano ang weather ngayon?",
        "Magluto ng breakfast",
        "I-play ang music",
        "Ipadala ang email kay boss"
    ],
    "medium": [
        "Pakibukas ng TV at ilagay sa channel five para mapanood ko ang balita",
        "Ano ang weather forecast para sa buong linggo? Uulan ba bukas?",
        "Pakisabi sa akin kung ano ang mga appointments ko para sa buong araw",
        "Gumawa ng shopping list para sa grocery bukas, kasama ang gulay at karne",
        "Anong oras ang susunod na flight papuntang Manila mula sa Cebu?"
    ],
    "long": [
        "Kailangan kong malaman kung anong oras ang susunod na meeting ko para sa project proposal, at pakisabi na rin kung sino ang mga taong dapat kong kausapin tungkol dito para makapaghanda ako nang maayos.",
        "Pwede mo bang i-summarize ang mga pinakahuling balita tungkol sa ekonomiya ng Pilipinas, lalo na tungkol sa inflation rate at foreign exchange para sa investment planning ko?",
        "Mayroon akong presentation bukas sa harap ng management team, pakitulong naman na i-review ang slides ko at i-check kung may grammatical errors o kung may content na kailangan pang i-improve.",
        "Gusto kong magluto ng special dinner para sa anniversary namin. Pwede bang magbigay ka ng recipe para sa authentic Filipino dish na may modern twist, kasama ang ingredients list at detailed preparation steps?",
        "Pakicheck kung ano ang pinakamabilis na ruta papuntang Makati mula sa Quezon City ngayong rush hour, at sabihin din kung magkano ang inaasahang Grab fare o kung may alternative na public transportation options."
    ],
    "mixed_taglish": [
        "Can you please open yung bintana para fresh air can come in?",
        "I need to check kung available pa yung movie tickets for tonight's showing",
        "Please remind me to water yung plants ko before I leave for work tomorrow",
        "What's the weather like sa Manila ngayon? Should I bring an umbrella?",
        "Can you compute kung magkano ang total expenses ko this month including yung bills and groceries?"
    ]
}

# ANSI colors for pretty output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")

def print_section(text):
    """Print a section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.ENDC}")

def print_result(label, value, is_good=True):
    """Print a benchmark result with color"""
    color = Colors.GREEN if is_good else Colors.RED
    print(f"{label}: {color}{value}{Colors.ENDC}")

def connect_to_translator(timeout=5000):
    """Connect to the translator agent"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout)  # 5 second timeout
    
    try:
        socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5563")
        print(f"{Colors.GREEN}✓ Connected to translator agent on port 5563{Colors.ENDC}")
        return context, socket
    except Exception as e:
        print(f"{Colors.RED}✗ Failed to connect to translator agent: {e}{Colors.ENDC}")
        sys.exit(1)

def translate_text(socket, text, force_method=None):
    """Translate text and measure performance"""
    request = {
        "action": "translate",
        "text": text
    }
    
    if force_method:
        request["force_method"] = force_method
    
    start_time = time.time()
    
    try:
        socket.send_json(request)
        response = socket.recv_json()
        
        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000
        
        if "status" in response and response["status"] == "error":
            print(f"{Colors.RED}Translation error: {response.get('message', 'Unknown error')}{Colors.ENDC}")
            return None, elapsed_ms, response.get("method", "unknown")
            
        translation = response.get("translation", "")
        method = response.get("method", "unknown")
        
        return translation, elapsed_ms, method
    except zmq.error.Again:
        print(f"{Colors.RED}Request timed out after {socket.getsockopt(zmq.RCVTIMEO)/1000} seconds{Colors.ENDC}")
        return None, 0, "timeout"
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
        return None, 0, "error"

def run_benchmark():
    """Run the full benchmark suite"""
    print_header("PC2 TRANSLATOR AGENT PERFORMANCE BENCHMARK")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Connect to translator agent
    context, socket = connect_to_translator()
    
    # Warm up the translation service
    print_section("Warming up translation service")
    for _ in range(3):
        translate_text(socket, "Hello, this is a warm-up message.")
        time.sleep(0.5)
    
    results = {
        "google": {"times": [], "success": 0, "fail": 0},
        "nllb": {"times": [], "success": 0, "fail": 0},
        "pattern": {"times": [], "success": 0, "fail": 0}
    }
    
    category_results = {
        "short": {"times": [], "char_count": 0},
        "medium": {"times": [], "char_count": 0},
        "long": {"times": [], "char_count": 0},
        "mixed_taglish": {"times": [], "char_count": 0}
    }
    
    # Test translation performance by text length
    print_section("Testing translation performance by text length")
    
    for category, texts in SAMPLE_TEXTS.items():
        print(f"\n{Colors.YELLOW}{category.upper()} TEXTS:{Colors.ENDC}")
        
        for i, text in enumerate(texts):
            print(f"\nText {i+1}/{len(texts)} ({len(text)} chars): \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
            
            translation, elapsed_ms, method = translate_text(socket, text)
            
            if translation:
                char_per_second = (len(text) / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0
                print(f"  Translation: \"{translation[:50]}{'...' if len(translation) > 50 else ''}\"")
                print(f"  Method: {method}, Time: {elapsed_ms:.2f}ms, Speed: {char_per_second:.1f} chars/sec")
                
                # Record results
                if method in results:
                    results[method]["times"].append(elapsed_ms)
                    results[method]["success"] += 1
                
                category_results[category]["times"].append(elapsed_ms)
                category_results[category]["char_count"] += len(text)
            else:
                print(f"  {Colors.RED}Translation failed{Colors.ENDC}")
                if method in results:
                    results[method]["fail"] += 1
            
            # Avoid overwhelming the service
            time.sleep(0.5)
    
    # Force specific translation methods
    methods = ["google", "nllb", "pattern"]
    print_section("Testing individual translation methods")
    
    for method in methods:
        print(f"\n{Colors.YELLOW}FORCED METHOD: {method.upper()}{Colors.ENDC}")
        
        # Select a mix of texts
        test_texts = []
        for category in SAMPLE_TEXTS:
            test_texts.append(random.choice(SAMPLE_TEXTS[category]))
        
        for i, text in enumerate(test_texts):
            print(f"\nText {i+1}/{len(test_texts)} ({len(text)} chars): \"{text[:50]}{'...' if len(text) > 50 else ''}\"")
            
            translation, elapsed_ms, actual_method = translate_text(socket, text, force_method=method)
            
            if translation and actual_method == method:
                char_per_second = (len(text) / (elapsed_ms / 1000)) if elapsed_ms > 0 else 0
                print(f"  Translation: \"{translation[:50]}{'...' if len(translation) > 50 else ''}\"")
                print(f"  Time: {elapsed_ms:.2f}ms, Speed: {char_per_second:.1f} chars/sec")
                
                # Record results
                if method in results:
                    results[method]["times"].append(elapsed_ms)
                    results[method]["success"] += 1
            else:
                print(f"  {Colors.RED}Translation failed or used different method: {actual_method}{Colors.ENDC}")
                if method in results:
                    results[method]["fail"] += 1
            
            # Avoid overwhelming the service
            time.sleep(0.5)
    
    # Results summary
    print_header("BENCHMARK RESULTS SUMMARY")
    
    # Method performance
    print_section("Translation Method Performance")
    for method, data in results.items():
        if data["times"]:
            avg_time = statistics.mean(data["times"])
            max_time = max(data["times"]) if data["times"] else 0
            min_time = min(data["times"]) if data["times"] else 0
            success_rate = (data["success"] / (data["success"] + data["fail"])) * 100 if (data["success"] + data["fail"]) > 0 else 0
            
            print(f"\n{Colors.YELLOW}{method.upper()}:{Colors.ENDC}")
            print_result("  Average Time", f"{avg_time:.2f}ms", avg_time < 1000)
            print_result("  Min Time", f"{min_time:.2f}ms", True)
            print_result("  Max Time", f"{max_time:.2f}ms", max_time < 2000)
            print_result("  Success Rate", f"{success_rate:.1f}%", success_rate > 90)
    
    # Text length performance
    print_section("Performance by Text Length")
    for category, data in category_results.items():
        if data["times"]:
            avg_time = statistics.mean(data["times"])
            char_count = data["char_count"] / len(data["times"])
            char_per_second = (char_count / (avg_time / 1000)) if avg_time > 0 else 0
            
            print(f"\n{Colors.YELLOW}{category.upper()}:{Colors.ENDC}")
            print_result("  Average Time", f"{avg_time:.2f}ms", avg_time < 1000)
            print_result("  Average Length", f"{char_count:.1f} chars", True)
            print_result("  Speed", f"{char_per_second:.1f} chars/sec", char_per_second > 100)
    
    # Final recommendations
    print_section("Performance Recommendations")
    
    method_times = {m: statistics.mean(d["times"]) if d["times"] else float('inf') for m, d in results.items()}
    fastest_method = min(method_times.items(), key=lambda x: x[1])[0] if method_times else None
    
    if fastest_method:
        print(f"{Colors.GREEN}→ Fastest translation method: {fastest_method.upper()} ({method_times[fastest_method]:.2f}ms average){Colors.ENDC}")
    
    # Taglish performance
    if "mixed_taglish" in category_results and category_results["mixed_taglish"]["times"]:
        taglish_time = statistics.mean(category_results["mixed_taglish"]["times"])
        print_result("→ Taglish Performance", f"{taglish_time:.2f}ms average", taglish_time < 1000)
    
    # Clean up
    socket.close()
    context.term()
    print(f"\nBenchmark completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    run_benchmark()
