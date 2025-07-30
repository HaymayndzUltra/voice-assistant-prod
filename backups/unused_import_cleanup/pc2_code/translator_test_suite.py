"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
Comprehensive Test Suite for Phi Translator Service
--------------------------------------------------
Evaluates translation quality, reliability, and performance metrics
across various input types and contexts.
"""

import zmq
import json
import time
import random
import argparse
import colorama
from colorama import Fore, Style
from datetime import datetime
from common.env_helpers import get_env

# Initialize colorama for colored output
colorama.init()

# Test configuration
DEFAULT_PHI_PORT = 5581
DEFAULT_PHI_HOST = get_env("BIND_ADDRESS", "0.0.0.0")  # Use localhost for local testing

# Comprehensive test suite organized by categories
TEST_CASES = {
    "Basic Commands": [
        ("Buksan mo ang file na ito", "Open this file"),
        ("Isara mo ang window", "Close the window"),
        ("I-save mo ang document", "Save the document"),
        ("Mag-back up ng data", "Back up the data"),
        ("I-refresh mo ang page", "Refresh the page"),
        ("Mag-logout ka na", "Log out now")
    ],
    
    "Technical Instructions": [
        ("I-debug mo yung authentication flow", "Debug the authentication flow"),
        ("Gumawa ka ng function para sa validation", "Create a function for validation"),
        ("Pakicheck kung may duplicate entries", "Check if there are duplicate entries"),
        ("I-optimize mo yung database query", "Optimize the database query"),
        ("Maglipat ka ng files sa encrypted folder", "Move files to the encrypted folder")
    ],
    
    "Taglish Mixed": [
        ("Download mo yung file tapos i-analyze", "Download the file then analyze it"),
        ("I-backup mo yung database bago mag-update", "Back up the database before updating"),
        ("Check mo yung logs para sa errors", "Check the logs for errors"),
        ("Mag-create ka ng new branch sa Git", "Create a new branch in Git"),
        ("I-verify mo yung SSL certificate expiry", "Verify the SSL certificate expiry")
    ],
    
    "Complex Sentences": [
        ("Kapag nag-crash ang system, i-restart mo agad at i-log ang error", 
         "When the system crashes, restart it immediately and log the error"),
        ("Mag-create ka ng temporary directory para sa mga extracted files",
         "Create a temporary directory for the extracted files"),
        ("Kailangan i-update ang lahat ng dependencies bago mag-deploy",
         "Need to update all dependencies before deploying"),
        ("Gumamit ka ng try-catch block para hindi mag-crash kapag may error",
         "Use a try-catch block to prevent crashing when there's an error")
    ],
    
    "Common Voice Commands": [
        ("Ano ang oras ngayon?", "What time is it now?"),
        ("Pakibasa ang bagong messages ko", "Please read my new messages"),
        ("Ipadala mo ang email kay boss", "Send an email to boss"),
        ("Magsearch ka ng restaurants na malapit dito", "Search for restaurants nearby"),
        ("Tumawag ka kay Juan", "Call Juan")
    ]
}


class TranslatorTester:
    def __init__(self, host=DEFAULT_PHI_HOST, port=DEFAULT_PHI_PORT):
        """Initialize the tester with connection parameters"""
        self.host = host
        self.port = port
        self.connection_string = f"tcp://{host}:{port}"
        
        # Performance tracking
        self.results = {
            "total_tests": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0,
            "categories": {},
            "issues": []
        }
        
        # Initialize ZMQ
        self.context = zmq.Context()
        self.socket = None
    
    def connect(self):
        """Establish connection to Phi Translator"""
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
            self.socket.connect(self.connection_string)
            print(f"{Fore.GREEN}Connected to Phi Translator at {self.connection_string}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}Failed to connect: {e}{Style.RESET_ALL}")
            return False
    
    def run_health_check(self):
        """Run a health check on the Phi Translator service"""
        if not self.socket:
            return False
            
        try:
            print(f"{Fore.CYAN}Performing health check...{Style.RESET_ALL}")
            request = {"action": "health"}
            self.socket.send_json(request)
            
            response = self.socket.recv_json()
            if response.get("success"):
                print(f"{Fore.GREEN}Health check passed{Style.RESET_ALL}")
                stats = response.get("stats", {})
                print(f"  {Fore.CYAN}Requests processed: {stats.get('requests', 0)}{Style.RESET_ALL}")
                print(f"  {Fore.CYAN}Success rate: {stats.get('successful', 0)}/{stats.get('requests', 0)}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}Health check failed: {response.get('message', 'Unknown error')}{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"{Fore.RED}Health check error: {e}{Style.RESET_ALL}")
            return False
    
    def evaluate_translation(self, translation, expected):
        """Evaluate the quality of a translation against expected output"""
        if not translation or not expected:
            return 0.0
        
        # Normalize both strings
        trans_norm = translation.lower().strip().strip('.!?')
        expect_norm = expected.lower().strip().strip('.!?')
        
        if trans_norm == expect_norm:
            # Perfect match
            return 1.0
        
        # Calculate word overlap ratio
        trans_words = set(trans_norm.split())
        expect_words = set(expect_norm.split())
        
        if not expect_words:
            return 0.0
        
        # Intersection of words
        common_words = trans_words.intersection(expect_words)
        # Word overlap score
        overlap_ratio = len(common_words) / len(expect_words)
        
        return overlap_ratio
    
    def run_translation_tests(self):
        """Run translation tests using various test cases"""
        if not self.socket:
            return False
        
        print(f"\n{Fore.CYAN}Running translation tests...{Style.RESET_ALL}")
        
        # Run tests by category
        for category, cases in TEST_CASES.items():
            print(f"\n{Fore.YELLOW}{category}:{Style.RESET_ALL}")
            self.results["categories"][category] = {
                "tests": 0,
                "successful": 0,
                "score": 0.0,
                "time": 0
            }
            
            for original, expected in cases:
                self.results["total_tests"] += 1
                self.results["categories"][category]["tests"] += 1
                
                try:
                    # Prepare request
                    request = {
                        "action": "translate",
                        "text": original,
                    }
                    
                    # Time the request
                    start_time = time.time()
                    self.socket.send_json(request)
                    
                    # Get response
                    response = self.socket.recv_json()
                    elapsed = time.time() - start_time
                    
                    # Process results
                    self.results["total_time"] += elapsed
                    self.results["categories"][category]["time"] += elapsed
                    
                    # Get the translation
                    translation = response.get("translated", "")
                    translation_model = response.get("model", "unknown")
                    
                    # Evaluate translation quality
                    quality_score = self.evaluate_translation(translation, expected)
                    self.results["categories"][category]["score"] += quality_score
                    
                    # Determine if test passed
                    translation_success = response.get("success", False) and quality_score > 0.5
                    
                    if translation_success:
                        self.results["successful"] += 1
                        self.results["categories"][category]["successful"] += 1
                        status = f"{Fore.GREEN}PASS"
                        quality_color = Fore.GREEN if quality_score > 0.8 else (Fore.YELLOW if quality_score > 0.5 else Fore.RED)
                    else:
                        self.results["failed"] += 1
                        status = f"{Fore.RED}FAIL"
                        quality_color = Fore.RED
                        self.results["issues"].append({
                            "original": original,
                            "expected": expected,
                            "actual": translation,
                            "model": translation_model,
                            "score": quality_score,
                            "category": category
                        })
                    
                    # Print result
                    print(f"{status}{Style.RESET_ALL} [{translation_model}] {Fore.CYAN}\"{original}\"{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Expected: {Fore.YELLOW}\"{expected}\"{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Actual:   {quality_color}\"{translation}\"{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Quality:  {quality_color}{quality_score:.2f}{Style.RESET_ALL} | {Fore.WHITE}Time: {elapsed:.2f}s{Style.RESET_ALL}")
                    
                except Exception as e:
                    self.results["failed"] += 1
                    self.results["issues"].append({
                        "original": original,
                        "expected": expected,
                        "error": str(e),
                        "category": category
                    })
                    print(f"{Fore.RED}ERROR{Style.RESET_ALL} \"{original}\"")
                    print(f"  {Fore.RED}Error: {e}{Style.RESET_ALL}")
        
        # Print summary
        self._print_summary()
        
        # Check if test is successful (80%+ success rate)
        success_rate = (self.results["successful"] / max(1, self.results["total_tests"])) * 100
        return success_rate >= 80.0
    
    def run_stress_test(self, iterations=20):
        """Run a stress test with rapid requests"""
        if not self.socket:
            return False
        
        print(f"\n{Fore.MAGENTA}Running stress test ({iterations} iterations)...{Style.RESET_ALL}")
        
        # Flatten all test cases
        all_cases = []
        for cases in TEST_CASES.values():
            all_cases.extend(cases)
        
        successful = 0
        total_time = 0
        
        for i in range(iterations):
            test_case = random.choice(all_cases)
            original = test_case[0]
            
            try:
                # Prepare request
                request = {
                    "action": "translate",
                    "text": original
                }
                
                # Time the request
                start_time = time.time()
                self.socket.send_json(request)
                
                # Get response
                response = self.socket.recv_json()
                elapsed = time.time() - start_time
                total_time += elapsed
                
                if response.get("success", False):
                    successful += 1
                    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {elapsed:.2f}s ({response.get('model', 'unknown')})", end=" ")
                else:
                    print(f"{Fore.RED}✗{Style.RESET_ALL} {elapsed:.2f}s", end=" ")
                
                # Flush output to show progress
                import sys
                sys.stdout.flush()
                
            except Exception as e:
                print(f"{Fore.RED}✗{Style.RESET_ALL} Error", end=" ")
        
        print("\n")
        avg_time = total_time / iterations if iterations > 0 else 0
        success_rate = (successful / iterations) * 100 if iterations > 0 else 0
        
        print(f"{Fore.CYAN}Stress test results: {successful}/{iterations} successful ({success_rate:.1f}%){Style.RESET_ALL}")
        print(f"{Fore.CYAN}Average response time: {avg_time:.2f}s{Style.RESET_ALL}")
        
        return successful >= iterations * 0.8  # 80% success rate
    
    def _print_summary(self):
        """Print a summary of test results"""
        success_rate = (self.results["successful"] / max(1, self.results["total_tests"])) * 100
        avg_time = self.results["total_time"] / max(1, self.results["total_tests"])
        
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}PHI TRANSLATOR TEST RESULTS{Style.RESET_ALL}")
        print("=" * 60)
        print(f"{Fore.WHITE}Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Connection: {self.connection_string}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Total tests: {self.results['total_tests']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Successful: {self.results['successful']} ({success_rate:.1f}%){Style.RESET_ALL}")
        print(f"{Fore.WHITE}Failed: {self.results['failed']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Average response time: {avg_time:.2f}s{Style.RESET_ALL}")
        
        # Category breakdown
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}Category Performance:{Style.RESET_ALL}")
        for category, stats in self.results["categories"].items():
            if stats["tests"] > 0:
                cat_success_rate = (stats["successful"] / stats["tests"]) * 100
                cat_avg_time = stats["time"] / stats["tests"]
                cat_avg_score = stats["score"] / stats["tests"]
                score_color = Fore.GREEN if cat_avg_score > 0.8 else (Fore.YELLOW if cat_avg_score > 0.5 else Fore.RED)
                
                print(f"  {Fore.CYAN}{category}{Style.RESET_ALL}: {stats['successful']}/{stats['tests']} " + 
                      f"({cat_success_rate:.1f}%), Avg score: {score_color}{cat_avg_score:.2f}{Style.RESET_ALL}, " + 
                      f"Time: {cat_avg_time:.2f}s")
        
        # Top issues
        if self.results["issues"]:
            print(f"\n{Fore.RED}{Style.BRIGHT}Top Issues:{Style.RESET_ALL}")
            for i, issue in enumerate(self.results["issues"][:5]):  # Show top 5 issues
                if "error" in issue:
                    print(f"  {Fore.RED}{i+1}. Error: {issue['error']}{Style.RESET_ALL}")
                    print(f"     Input: \"{issue['original']}\"")
                else:
                    print(f"  {Fore.RED}{i+1}. Low quality translation (score: {issue['score']:.2f}){Style.RESET_ALL}")
                    print(f"     Input:    \"{issue['original']}\"")
                    print(f"     Expected: \"{issue['expected']}\"")
                    print(f"     Actual:   \"{issue['actual']}\" (using {issue['model']})")
                    
        # Final verdict
        if success_rate >= 90:
            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ TEST PASSED EXCELLENTLY ({success_rate:.1f}%){Style.RESET_ALL}")
        elif success_rate >= 80:
            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ TEST PASSED ({success_rate:.1f}%){Style.RESET_ALL}")
        elif success_rate >= 60:
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠ TEST PASSED WITH ISSUES ({success_rate:.1f}%){Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}{Style.BRIGHT}✗ TEST FAILED ({success_rate:.1f}%){Style.RESET_ALL}")
        
    def run_all_tests(self):
        """Run all tests in sequence"""
        # Connect to service
        if not self.connect():
            return False
        
        # Run health check
        self.run_health_check()
        
        # Run translation tests
        translation_success = self.run_translation_tests()
        
        # Run stress test
        stress_success = self.run_stress_test(iterations=10)
        
        return translation_success and stress_success
    
    def cleanup(self):
        """Clean up resources"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
            
def main():
    """Main function to run the tester"""
    parser = argparse.ArgumentParser(description="Phi Translator Test Suite")
    parser.add_argument("--host", default=DEFAULT_PHI_HOST, help=f"Phi Translator host (default: {DEFAULT_PHI_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PHI_PORT, help=f"Phi Translator port (default: {DEFAULT_PHI_PORT})")
    args = parser.parse_args()
    
    print(f"{Fore.CYAN}{Style.BRIGHT}PHI TRANSLATOR TEST SUITE{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Testing connection to {args.host}:{args.port}{Style.RESET_ALL}")
    
    # Create and run tester
    tester = TranslatorTester(host=args.host, port=args.port)
    
    try:
        tester.run_all_tests()
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()
