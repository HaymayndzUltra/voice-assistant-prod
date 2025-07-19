"""
NLLB Translation Quality Tester
------------------------------
Comprehensive test suite for evaluating the NLLB translation adapter quality.
Performs systematic testing of different types of text and generates a quality report.
"""
import zmq
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from colorama import init, Fore, Style
from common.env_helpers import get_env

# Initialize colorama for colored console output
init()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nllb_test_results.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("NLLBTranslationTester")

# Default server settings
DEFAULT_SERVER = "localhost"
DEFAULT_PORT = 5581

# Test categories
TEST_CATEGORIES = {
    "Basic Phrases": [
        "Magandang umaga",
        "Kumusta ka?",
        "Salamat sa tulong mo",
        "Saan ka pupunta?",
        "Anong oras na?",
        "Masarap ang pagkain",
        "Mahal kita",
        "Hindi ko maintindihan",
        "Pakiulit mo",
        "Tulog na ako"
    ],
    "Complex Sentences": [
        "Kapag dumating ang panahon, malalaman mo rin ang katotohanan tungkol sa iyong nakaraan.",
        "Ang mga kabataan ngayon ay mas technologically advanced kaysa sa nakaraang henerasyon.",
        "Hindi lahat ng nakikita mo sa social media ay totoo, kaya dapat maging mapanuri.",
        "Kahit anong mangyari, hinding-hindi kita iiwan sa gitna ng iyong mga pagsubok.",
        "Ang tunay na kaibigan ay siyang nananatili sa tabi mo kahit sa pinakamahirap na panahon."
    ],
    "Idiomatic Expressions": [
        "Bahala na si Batman",
        "Nagpapakawala ng mga kalapati",
        "Isang kahig, isang tuka",
        "Aanhin pa ang damo kung patay na ang kabayo",
        "Ang hindi marunong lumingon sa pinanggalingan ay hindi makakarating sa paroroonan"
    ],
    "Code-Switched Taglish": [
        "Na-check mo na ba yung files na sinend ko sayo?",
        "I-download mo muna yung latest version bago mag-update",
        "Mag-open ka ng new tab para sa website na yan",
        "Paki-explain naman kung paano gumawa ng query sa database",
        "Na-save mo ba yung changes sa document bago mag-shutdown?"
    ],
    "Technical Phrases": [
        "Kailangan i-upgrade ang memory ng computer para mas bumilis",
        "I-restart mo muna ang system bago i-install ang bagong software",
        "Paki-configure ang network settings para ma-access ang server",
        "May problema sa graphics card kaya nagla-lag ang display",
        "I-backup mo muna ang data bago mag-format ng hard drive"
    ],
    "Commands": [
        "Buksan mo ang bintana",
        "Isara ang pinto",
        "I-play mo ang music",
        "Patahimikin mo ang volume",
        "Buksan mo ang ilaw"
    ],
    "Context-Dependent": [
        "Alin dito ang mas maganda?",
        "Kailan ka babalik?",
        "Nakita mo ba?",
        "Alam mo na ba?",
        "Sino yun?"
    ]
}

# Ground truth translations for comparison (for automated evaluation)
GROUND_TRUTH = {
    "Magandang umaga": "Good morning",
    "Kumusta ka?": "How are you?",
    "Salamat sa tulong mo": "Thank you for your help",
    "Buksan mo ang bintana": "Open the window",
    "Isara ang pinto": "Close the door",
    "I-play mo ang music": "Play the music",
    "Alin dito ang mas maganda?": "Which one of these is more beautiful?",
    "Kailan ka babalik?": "When will you return?",
    "Nakita mo ba?": "Did you see it?",
    "Sino yun?": "Who is that?"
}

class TranslationTester:
    def __init__(self, server=DEFAULT_SERVER, port=DEFAULT_PORT):
        """Initialize the translation tester"""
        self.server = server
        self.port = port
        
        # Connection setup
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.connect_endpoint()
        
        # Results storage
        self.results = []
        
        logger.info(f"Initialized tester for {server}:{port}")
    
    def connect_endpoint(self):
        """Connect to the translation endpoint"""
        try:
            endpoint = f"tcp://{self.server}:{self.port}"
            logger.info(f"Connecting to {endpoint}")
            self.socket.connect(endpoint)
            logger.info("Connected successfully")
            return True
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False
    
    def translate(self, text, src_lang="tl", tgt_lang="en", timeout=10):
        """Request translation from the adapter"""
        try:
            # Create request with action parameter
            request = {
                "action": "translate",
                "text": text,
                "src_lang": src_lang,
                "tgt_lang": tgt_lang
            }
            
            # Record start time for latency measurement
            start_time = time.time()
            
            # Send request
            self.socket.send_json(request)
            
            # Set timeout
            poller = zmq.Poller()
            poller.register(self.socket, zmq.POLLIN)
            
            # Wait for response with timeout
            if poller.poll(timeout * 1000):  # milliseconds
                response = self.socket.recv_json()
                elapsed = time.time() - start_time
                
                # Extract translation
                if response.get("status") == "success":
                    return {
                        "text": text,
                        "translated": response.get("translated_text", ""),
                        "success": True,
                        "latency": elapsed,
                        "model": response.get("model", "unknown")
                    }
                else:
                    error_msg = response.get("message", "Unknown error")
                    logger.error(f"Translation error: {error_msg}")
                    return {
                        "text": text,
                        "translated": None,
                        "success": False,
                        "latency": elapsed,
                        "error": error_msg
                    }
            else:
                logger.error(f"Timeout waiting for response after {timeout}s")
                return {
                    "text": text,
                    "translated": None,
                    "success": False,
                    "latency": timeout,
                    "error": "Timeout"
                }
                
        except Exception as e:
            logger.error(f"Translation request error: {str(e)}")
            return {
                "text": text,
                "translated": None,
                "success": False,
                "error": str(e)
            }
    
    def test_category(self, category_name, phrases, wait_between=0.5):
        """Test all phrases in a category"""
        logger.info(f"Testing category: {category_name} ({len(phrases)} phrases)")
        
        category_results = []
        
        for i, phrase in enumerate(phrases, 1):
            print(f"  [{i}/{len(phrases)}] Testing: '{phrase}'")
            
            # Request translation
            result = self.translate(phrase)
            
            # Add category to result
            result["category"] = category_name
            category_results.append(result)
            
            # Display result
            if result["success"]:
                print(f"    {Fore.GREEN}✓{Style.RESET_ALL} Translated: '{result['translated']}' ({result['latency']:.2f}s)")
            else:
                print(f"    {Fore.RED}✗{Style.RESET_ALL} Error: {result.get('error', 'Unknown')}")
            
            # Add to overall results
            self.results.append(result)
            
            # Wait between requests to avoid overwhelming the service
            if i < len(phrases):
                time.sleep(wait_between)
        
        return category_results
    
    def run_all_tests(self, wait_between_categories=1.0):
        """Run tests for all categories"""
        logger.info(f"Starting comprehensive test suite ({len(TEST_CATEGORIES)} categories)")
        
        # Reset results
        self.results = []
        start_time = time.time()
        
        for category_name, phrases in TEST_CATEGORIES.items():
            print(f"\n{Fore.CYAN}Testing Category: {category_name}{Style.RESET_ALL}")
            self.test_category(category_name, phrases)
            
            # Wait between categories
            if wait_between_categories > 0:
                time.sleep(wait_between_categories)
        
        # Calculate overall stats
        total_time = time.time() - start_time
        logger.info(f"Completed all tests in {total_time:.2f} seconds")
        
        return self.results
    
    def evaluate_quality(self):
        """Evaluate translation quality based on test results"""
        if not self.results:
            logger.warning("No test results to evaluate")
            return None
        
        # Basic metrics
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        success_rate = successful / total if total > 0 else 0
        
        # Latency stats
        latencies = [r["latency"] for r in self.results if r["success"] and "latency" in r]
        avg_latency = np.mean(latencies) if latencies else 0
        max_latency = np.max(latencies) if latencies else 0
        min_latency = np.min(latencies) if latencies else 0
        
        # Category success rates
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = {"total": 0, "success": 0}
            
            categories[cat]["total"] += 1
            if r["success"]:
                categories[cat]["success"] += 1
        
        category_rates = {
            cat: stats["success"] / stats["total"] if stats["total"] > 0 else 0
            for cat, stats in categories.items()
        }
        
        # Quality evaluation for phrases where we have ground truth
        quality_scores = []
        for r in self.results:
            if r["text"] in GROUND_TRUTH and r["success"]:
                ground_truth = GROUND_TRUTH[r["text"]]
                translation = r["translated"]
                
                # Simple character-level similarity (just for demo)
                # In a real system, you'd use more sophisticated NLP metrics
                similarity = self._calculate_similarity(translation, ground_truth)
                quality_scores.append(similarity)
        
        avg_quality = np.mean(quality_scores) if quality_scores else 0
        
        # Compile results
        evaluation = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total,
            "success_rate": success_rate,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
            "category_success_rates": category_rates,
            "quality_score": avg_quality
        }
        
        return evaluation
    
    def _calculate_similarity(self, text1, text2):
        """Calculate a simple similarity score between two strings"""
        # Convert to lowercase for comparison
        text1 = text1.lower()
        text2 = text2.lower()
        
        # Count common words
        words1 = set(text1.split())
        words2 = set(text2.split())
        common_words = words1.intersection(words2)
        
        # Calculate Jaccard similarity
        if not words1 or not words2:
            return 0
            
        similarity = len(common_words) / len(words1.union(words2))
        return similarity
    
    def generate_report(self):
        """Generate and display a comprehensive report"""
        if not self.results:
            print("No test results available. Run tests first.")
            return
        
        # Get quality evaluation
        evaluation = self.evaluate_quality()
        
        # Convert results to DataFrame for analysis
        df = pd.DataFrame(self.results)
        
        # Print report header
        print("\n" + "="*80)
        print(f"{Fore.YELLOW}NLLB Translation Quality Report{Style.RESET_ALL}")
        print("="*80)
        
        # Overall stats
        print(f"\n{Fore.CYAN}Overall Statistics:{Style.RESET_ALL}")
        print(f"  Total phrases tested: {evaluation['total_tests']}")
        print(f"  Success rate: {evaluation['success_rate']*100:.1f}%")
        print(f"  Average latency: {evaluation['avg_latency']*1000:.1f}ms")
        print(f"  Latency range: {evaluation['min_latency']*1000:.1f}ms - {evaluation['max_latency']*1000:.1f}ms")
        
        if evaluation['quality_score'] > 0:
            quality_pct = evaluation['quality_score'] * 100
            print(f"  Overall quality score: {quality_pct:.1f}%")
        
        # Category performance
        print(f"\n{Fore.CYAN}Category Performance:{Style.RESET_ALL}")
        for category, rate in evaluation['category_success_rates'].items():
            status = f"{Fore.GREEN}GOOD{Style.RESET_ALL}" if rate >= 0.8 else f"{Fore.YELLOW}FAIR{Style.RESET_ALL}" if rate >= 0.5 else f"{Fore.RED}POOR{Style.RESET_ALL}"
            print(f"  {category}: {rate*100:.1f}% success rate - {status}")
        
        # Sample translations
        print(f"\n{Fore.CYAN}Sample Translations:{Style.RESET_ALL}")
        
        # Get one successful translation from each category
        samples = {}
        for r in self.results:
            if r["success"] and r["category"] not in samples:
                samples[r["category"]] = r
        
        for category, sample in samples.items():
            print(f"  {category}:")
            print(f"    Original: '{sample['text']}'")
            print(f"    Translated: '{sample['translated']}'")
            
            # If we have ground truth, show comparison
            if sample['text'] in GROUND_TRUTH:
                ground_truth = GROUND_TRUTH[sample['text']]
                print(f"    Expected: '{ground_truth}'")
                similarity = self._calculate_similarity(sample['translated'], ground_truth)
                quality = "Good" if similarity > 0.7 else "Fair" if similarity > 0.4 else "Poor"
                print(f"    Quality: {quality} ({similarity*100:.1f}% match)")
            
            print()
        
        # Recommendations section
        print(f"\n{Fore.CYAN}Recommendations:{Style.RESET_ALL}")
        
        # Generate recommendations based on results
        if evaluation['success_rate'] < 0.9:
            print("  • Improve error handling to increase success rate")
        
        if evaluation['avg_latency'] > 1.0:
            print("  • Optimize performance to reduce translation latency")
        
        if evaluation.get('quality_score', 0) < 0.7:
            print("  • Enhance translation quality through better prompting or model fine-tuning")
        
        # Find worst-performing category
        worst_category = min(evaluation['category_success_rates'].items(), key=lambda x: x[1])
        if worst_category[1] < 0.8:
            print(f"  • Focus improvements on '{worst_category[0]}' category ({worst_category[1]*100:.1f}% success rate)")
        
        # Save results to CSV
        csv_filename = f"nllb_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(csv_filename, index=False)
        print(f"\nDetailed results saved to {csv_filename}")
        
        return evaluation

def main():
    """Main function to run the test suite"""
    import argparse
    parser = argparse.ArgumentParser(description="Test NLLB Translation Adapter")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Server hostname/IP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    args = parser.parse_args()
    
    print(f"{Fore.YELLOW}=== NLLB Translation Quality Tester ==={Style.RESET_ALL}")
    print(f"Server: {args.server}:{args.port}")
    print(f"Test categories: {len(TEST_CATEGORIES)}")
    print(f"Total test phrases: {sum(len(phrases) for phrases in TEST_CATEGORIES.values())}")
    print()
    
    # Initialize tester
    tester = TranslationTester(server=args.server, port=args.port)
    
    # Run all tests
    tester.run_all_tests()
    
    # Generate report
    tester.generate_report()

if __name__ == "__main__":
    main()
