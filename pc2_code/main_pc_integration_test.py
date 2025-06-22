"""
Phi-3 Translator Integration Test
---------------------------------
Comprehensive test script for validating the connection and performance
of the Phi-3 Translator service running on PC2.

This script simulates the Main PC's connection to PC2's translation service
and conducts a series of tests to verify functionality, performance, and reliability.
"""

import zmq
import json
import time
import random
import argparse
import colorama
from colorama import Fore, Style
from datetime import datetime

# Initialize colorama
colorama.init()

# Test configuration
DEFAULT_PHI_PORT = 5581
DEFAULT_PHI_HOST = "192.168.1.2"  # PC2 IP address

# Test cases organized by category for comprehensive testing
TEST_CASES = {
    "Technical Commands": [
        "I-optimize mo yung database query para mas mabilis.",
        "Mag-setup ka ng cron job para sa daily backups.",
        "I-debug mo yung authentication flow sa website.",
        "Gumawa ka ng function para sa data validation."
    ],
    "Voice Assistant Commands": [
        "Buksan mo yung browser tapos search mo ang latest tech news.",
        "Makinig ka sa mga bagong messages sa Messenger.",
        "Pakibasa yung notifications ko mula kahapon.",
        "I-check mo kung may available updates para sa system."
    ],
    "Automation Requests": [
        "Gumawa ka ng script para mag-download ng lahat ng images sa page.",
        "I-automate mo yung pag-fill sa form kapag may bagong entry.",
        "Mag-extract ka ng data mula sa PDF files sa folder.",
        "I-monitor mo yung server load at mag-notify kapag mataas na."
    ],
    "Mixed Language": [
        "I-check mo yung logs then analyze mo for patterns of errors.",
        "Download the latest update tapos i-install mo agad.",
        "Create a database backup before implementing yung bagong feature.",
        "Can you verify the connection status tapos i-reset kung needed?"
    ]
}

class PhiTranslatorTester:
    def __init__(self, host=DEFAULT_PHI_HOST, port=DEFAULT_PHI_PORT, verbose=True):
        """Initialize the tester with connection parameters"""
        self.host = host
        self.port = port
        self.verbose = verbose
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
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            self.socket.connect(self.connection_string)
            self._print_status(f"Connected to Phi Translator at {self.connection_string}", Fore.GREEN)
            return True
        except Exception as e:
            self._print_status(f"Failed to connect: {e}", Fore.RED)
            return False
            
    def run_health_check(self):
        """Run a health check on the Phi Translator service"""
        if not self.socket:
            return False
            
        try:
            self._print_status("Performing health check...", Fore.CYAN)
            request = {"action": "health"}
            self.socket.send_json(request)
            
            response = self.socket.recv_json()
            if response.get("success"):
                self._print_status("Health check passed", Fore.GREEN)
                if self.verbose:
                    stats = response.get("stats", {})
                    print(f"  {Fore.CYAN}Requests processed: {stats.get('requests', 0)}{Style.RESET_ALL}")
                    print(f"  {Fore.CYAN}Success rate: {stats.get('successful', 0)}/{stats.get('requests', 0)}{Style.RESET_ALL}")
                return True
            else:
                self._print_status(f"Health check failed: {response.get('message', 'Unknown error')}", Fore.RED)
                return False
        except Exception as e:
            self._print_status(f"Health check error: {e}", Fore.RED)
            return False
    
    def run_translation_tests(self):
        """Run translation tests using various test cases"""
        if not self.socket:
            return False
        
        self._print_status("\nRunning translation tests...", Fore.CYAN)
        
        # Run tests by category
        for category, cases in TEST_CASES.items():
            self._print_status(f"\n{category}:", Fore.YELLOW)
            self.results["categories"][category] = {
                "tests": 0,
                "successful": 0,
                "time": 0
            }
            
            for text in cases:
                self.results["total_tests"] += 1
                self.results["categories"][category]["tests"] += 1
                
                try:
                    # Prepare request
                    request = {
                        "action": "translate",
                        "text": text,
                        "source_lang": "tl",
                        "target_lang": "en"
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
                    
                    if response.get("success", False):
                        self.results["successful"] += 1
                        self.results["categories"][category]["successful"] += 1
                        status_color = Fore.GREEN
                        status = "SUCCESS"
                    else:
                        status_color = Fore.RED
                        status = "FAILED"
                        self.results["failed"] += 1
                        self.results["issues"].append({
                            "text": text,
                            "error": response.get("message", "Unknown error")
                        })
                    
                    # Print result
                    print(f"{status_color}[{status}]{Style.RESET_ALL} {Fore.WHITE}Input: {Fore.CYAN}\"{text}\"{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Output: {Fore.YELLOW}\"{response.get('translated', 'No translation')}\"{Style.RESET_ALL}")
                    print(f"  {Fore.WHITE}Time: {elapsed:.4f}s{Style.RESET_ALL}")
                    
                except Exception as e:
                    self.results["failed"] += 1
                    self.results["issues"].append({
                        "text": text,
                        "error": str(e)
                    })
                    self._print_status(f"Error: {e}", Fore.RED)
        
        # Print summary
        self._print_summary()
        
        return self.results["successful"] == self.results["total_tests"]
    
    def stress_test(self, iterations=10, parallel=False):
        """Run a stress test with rapid requests"""
        if not self.socket:
            return False
        
        self._print_status(f"\nRunning stress test ({iterations} iterations)...", Fore.MAGENTA)
        
        # Flatten all test cases
        all_cases = []
        for cases in TEST_CASES.values():
            all_cases.extend(cases)
        
        successful = 0
        total_time = 0
        
        for i in range(iterations):
            test_text = random.choice(all_cases)
            
            try:
                # Prepare request
                request = {
                    "action": "translate",
                    "text": test_text,
                    "source_lang": "tl",
                    "target_lang": "en"
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
                    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {elapsed:.4f}s", end=" ")
                else:
                    print(f"{Fore.RED}✗{Style.RESET_ALL} {elapsed:.4f}s", end=" ")
                
                # Flush output to show progress
                import sys
                sys.stdout.flush()
                
            except Exception as e:
                print(f"{Fore.RED}✗{Style.RESET_ALL} Error", end=" ")
        
        print("\n")
        avg_time = total_time / iterations
        self._print_status(f"Stress test results: {successful}/{iterations} successful", Fore.CYAN)
        self._print_status(f"Average response time: {avg_time:.4f}s", Fore.CYAN)
        
        return successful == iterations
    
    def _print_status(self, message, color=Fore.WHITE):
        """Print a status message with color"""
        print(f"{color}{message}{Style.RESET_ALL}")
    
    def _print_summary(self):
        """Print a summary of test results"""
        success_rate = (self.results["successful"] / max(1, self.results["total_tests"])) * 100
        avg_time = self.results["total_time"] / max(1, self.results["total_tests"])
        
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}{Style.BRIGHT}PHI-3 TRANSLATOR INTEGRATION TEST RESULTS{Style.RESET_ALL}")
        print("=" * 60)
        print(f"{Fore.WHITE}Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Connection: {self.connection_string}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Total tests: {self.results['total_tests']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Successful: {self.results['successful']} ({success_rate:.1f}%){Style.RESET_ALL}")
        print(f"{Fore.WHITE}Failed: {self.results['failed']}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}Average response time: {avg_time:.4f}s{Style.RESET_ALL}")
        
        # Category breakdown
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}Category Performance:{Style.RESET_ALL}")
        for category, stats in self.results["categories"].items():
            if stats["tests"] > 0:
                cat_success_rate = (stats["successful"] / stats["tests"]) * 100
                cat_avg_time = stats["time"] / stats["tests"]
                print(f"  {Fore.CYAN}{category}{Style.RESET_ALL}: {stats['successful']}/{stats['tests']} " + 
                      f"({cat_success_rate:.1f}%), {cat_avg_time:.4f}s avg")
        
        # Issues list
        if self.results["issues"]:
            print(f"\n{Fore.RED}{Style.BRIGHT}Issues Found:{Style.RESET_ALL}")
            for issue in self.results["issues"]:
                print(f"  {Fore.RED}• Input: \"{issue['text']}\"{Style.RESET_ALL}")
                print(f"    {Fore.RED}Error: {issue['error']}{Style.RESET_ALL}")
        
        # Final verdict
        if self.results["successful"] == self.results["total_tests"]:
            print(f"\n{Fore.GREEN}{Style.BRIGHT}✓ INTEGRATION TEST PASSED{Style.RESET_ALL}")
            print(f"{Fore.GREEN}The Phi-3 Translator is ready for production use.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚠ INTEGRATION TEST COMPLETED WITH ISSUES{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Phi-3 Translator is operational but some tests failed.{Style.RESET_ALL}")
            
    def run_all_tests(self):
        """Run all tests in sequence"""
        # Connect to service
        if not self.connect():
            return False
        
        # Run health check
        if not self.run_health_check():
            return False
        
        # Run translation tests
        translation_success = self.run_translation_tests()
        
        # Run stress test
        stress_success = self.stress_test(iterations=20)
        
        return translation_success and stress_success
    
    def cleanup(self):
        """Clean up resources"""
        if self.socket:
            self.socket.close()
        if self.context:
            self.context.term()
        self._print_status("Test client cleaned up", Fore.CYAN)


def main():
    """Main function to run the tester"""
    parser = argparse.ArgumentParser(description="Phi-3 Translator Integration Test")
    parser.add_argument("--host", default=DEFAULT_PHI_HOST, help=f"Phi Translator host (default: {DEFAULT_PHI_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PHI_PORT, help=f"Phi Translator port (default: {DEFAULT_PHI_PORT})")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--stress", action="store_true", help="Run stress test only")
    args = parser.parse_args()
    
    print(f"{Fore.CYAN}{Style.BRIGHT}PHI-3 TRANSLATOR INTEGRATION TEST{Style.RESET_ALL}")
    print(f"{Fore.WHITE}Testing connection to {args.host}:{args.port}{Style.RESET_ALL}")
    
    # Create and run tester
    tester = PhiTranslatorTester(host=args.host, port=args.port, verbose=args.verbose)
    
    try:
        if args.stress:
            tester.connect()
            tester.stress_test(iterations=50)
        else:
            tester.run_all_tests()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
