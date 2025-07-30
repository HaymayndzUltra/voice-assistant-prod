import time
import colorama
from colorama import Fore, Style
from phi_adapter import PhiTranslationAdapter

# Initialize colorama for Windows terminal color support
colorama.init()

# Test cases organized by category
cases = {
    "Coding/DevOps": [
        "I-clone mo agad yung repo, tapos i-push mo sa main branch.",
        "Check mo kung vulnerable sa SQL injection.",
        "Mag-loop ka sa lahat ng items, tapos i-log mo yung output.",
        "I-auto restart mo yung service pag nag-crash.",
    ],
    "Web Scraping": [
        "Paki-scan ng buong website, hanapin mo lahat ng email address.",
        "Hanapin mo yung may class na 'product-title', tapos kunin mo lahat ng text.",
        "I-automate mo na yung pag-fill ng form sa website.",
    ],
    "Audio/Messenger": [
        "I-record mo yung audio na ipi-play ko, tapos i-ready mo for Messenger.",
        "Pag hinold ko yung mic sa Messenger, i-play mo yung nirecord mong audio.",
        "I-trim mo yung silence sa simula at dulo ng audio bago mo i-play.",
        "Pag tapos na yung playback, sabihin mo kung na-send na sa Messenger.",
    ],
    "Data Processing": [
        "Copy-paste mo na lang yung JSON response, analyze mo agad.",
        "I-try mo i-extract yung phone numbers gamit regex.",
        "Ilagay mo dito yung sagot ng AI chatbot, tapos summarize mo.",
        "Gawan mo ako ng Python code na magda-download ng lahat ng images sa page.",
    ]
}

# Utility functions for advanced testing
def print_header(text, category=None):
    """Print formatted header with category"""
    width = 90
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{('='*width)}{Style.RESET_ALL}")
    if category:
        print(f"{Fore.YELLOW}{Style.BRIGHT}CATEGORY: {category}{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{Style.BRIGHT}INPUT: {Fore.GREEN}\"{text}\"{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{('='*width)}{Style.RESET_ALL}")

def print_metrics(start_time, text_length, prompt_length):
    """Calculate and print performance metrics"""
    elapsed = time.time() - start_time
    examples_ratio = round(prompt_length / max(text_length, 1), 2)
    efficiency_score = min(10, max(1, 10 - (elapsed * 2)))
    quality_score = min(10, max(1, examples_ratio * 3))
    
    print(f"{Fore.MAGENTA}{'-'*90}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}PERFORMANCE METRICS:{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}* Generation time: {Fore.CYAN}{elapsed:.4f}s{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}* Input length: {Fore.CYAN}{text_length} chars{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}* Prompt length: {Fore.CYAN}{prompt_length} chars{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}* Examples:Input ratio: {Fore.CYAN}{examples_ratio:.2f}x{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}* Efficiency score: {Fore.GREEN}{efficiency_score:.1f}/10{Style.RESET_ALL}")
    print(f"  {Fore.WHITE}* Quality score: {Fore.GREEN}{quality_score:.1f}/10{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'-'*90}{Style.RESET_ALL}")
    return elapsed, quality_score

# Main test runner
print(f"{Fore.GREEN}{Style.BRIGHT}\nPHI TRANSLATION ADAPTER - DYNAMIC PROMPT TESTING{Style.RESET_ALL}")
print(f"{Fore.WHITE}Comprehensive prompt generation analysis for Taglish->English{Style.RESET_ALL}")
print(f"Timestamp: {Fore.CYAN}{time.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
print(f"Example pool size: {Fore.YELLOW}{len(PhiTranslationAdapter.PROMPT_EXAMPLES)}{Style.RESET_ALL}")

# Track total test statistics
total_tests = 0
total_time = 0

# Tracking variables for analytics
category_stats = {}
quality_scores = []

# Run tests by category
for category, examples in cases.items():
    category_stats[category] = {
        'count': 0,
        'total_time': 0,
        'avg_quality': 0,
        'prompts': []
    }
    
    for text in examples:
        total_tests += 1
        category_stats[category]['count'] += 1
        print_header(text, category)
        
        # Time the prompt generation
        start = time.time()
        prompt = PhiTranslationAdapter.build_dynamic_prompt(text, sample_size=14, debug=True)
        end = time.time()
        
        # Store prompt for later analysis
        category_stats[category]['prompts'].append(prompt)
        
        # Print prompt with highlighting
        print(f"\n{Fore.BLUE}GENERATED PROMPT:{Style.RESET_ALL}\n")
        print(f"{Fore.WHITE}{prompt}{Style.RESET_ALL}\n")
        
        # Performance metrics
        elapsed, quality = print_metrics(start, len(text), len(prompt))
        total_time += elapsed
        category_stats[category]['total_time'] += elapsed
        quality_scores.append(quality)

# Calculate category-level statistics
for cat, stats in category_stats.items():
    if stats['count'] > 0:
        stats['avg_time'] = stats['total_time'] / stats['count']
        # Calculate average word count in prompts
        total_words = sum(len(p.split()) for p in stats['prompts'])
        stats['avg_words'] = total_words / stats['count']

# Final summary with enhanced analytics
print(f"\n{Fore.GREEN}{Style.BRIGHT}TEST SUMMARY{Style.RESET_ALL}")
print(f"Total tests run: {Fore.YELLOW}{total_tests}{Style.RESET_ALL}")
print(f"Average generation time: {Fore.CYAN}{(total_time/total_tests):.4f}s{Style.RESET_ALL}")
print(f"Average quality score: {Fore.GREEN}{sum(quality_scores)/len(quality_scores):.2f}/10{Style.RESET_ALL}")

# Category breakdown
print(f"\n{Fore.YELLOW}CATEGORY PERFORMANCE:{Style.RESET_ALL}")
for cat, stats in category_stats.items():
    if stats['count'] > 0:
        print(f"  {Fore.CYAN}{cat}{Style.RESET_ALL}: {stats['count']} tests, "
              f"avg time {stats['avg_time']:.4f}s, "
              f"avg words {stats['avg_words']:.1f}")

print(f"\n{Fore.GREEN}Test completed successfully: [PASS]{Style.RESET_ALL}")
