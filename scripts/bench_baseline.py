import time
import statistics
from main_pc_code.utils import model_client

# Define a set of prompts to test different scenarios
TEST_PROMPTS = [
    {"id": "short_greeting", "prompt": "Hello"},
    {"id": "simple_question", "prompt": "What is the capital of France?"},
    {"id": "code_generation", "prompt": "Write a python function to calculate the factorial of a number."},
    {"id": "long_reasoning", "prompt": "Explain the theory of relativity in three paragraphs."},
]

def run_benchmark():
    """
    Runs the performance benchmark and prints the results.
    """
    print("--- Starting Performance Benchmark ---")
    results = []

    for test in TEST_PROMPTS:
        prompt_id = test["id"]
        prompt_text = test["prompt"]
        
        print(f"\n[Testing: {prompt_id}]")
        
        try:
            start_time = time.perf_counter()
            
            # Use the model_client to call the MMA router
            response = model_client.generate(prompt_text, quality="fast")
            
            end_time = time.perf_counter()

            # Handle different response formats
            if isinstance(response, dict):
                status_val = response.get("status")
                if status_val not in ("ok", "SUCCESS", "success"):
                    # Something went wrong according to the MMA
                    print(f"  ERROR: model_client returned error status → {response}")
                    continue
                response_text = response.get("response_text") or response.get("text") or ""
            elif isinstance(response, str):
                response_text = response
            else:
                print("  ERROR: Unsupported response type from model_client.")
                continue

            if not response_text:
                print("  ERROR: Empty response_text from model_client.")
                continue

            latency = end_time - start_time
            response_tokens = len(response_text.split())  # Simple token count by splitting words
            tokens_per_second = response_tokens / latency if latency > 0 else float('inf')

            result_data = {
                "id": prompt_id,
                "latency_s": latency,
                "tokens_per_s": tokens_per_second,
                "response_length_tokens": response_tokens
            }
            results.append(result_data)
            
            print(f"  Latency: {latency:.4f} s")
            print(f"  Tokens/s: {tokens_per_second:.2f}")
            print(f"  Response Length: {response_tokens} tokens")

        except Exception as e:
            print(f"  ERROR during benchmark for '{prompt_id}': {e}")

    if not results:
        print("\n--- Benchmark finished with no successful results. ---")
        return

    # Calculate and print summary statistics
    avg_latency = statistics.mean([r["latency_s"] for r in results])
    avg_tps = statistics.mean([r["tokens_per_s"] for r in results])

    print("\n--- Benchmark Summary ---")
    print(f"Average Latency: {avg_latency:.4f} s")
    print(f"Average Tokens/s: {avg_tps:.2f}")
    print("-----------------------")


if __name__ == "__main__":
    run_benchmark() 