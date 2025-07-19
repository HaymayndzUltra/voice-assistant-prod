#!/usr/bin/env python3
"""
Test script for batch processing in STT service.
This script compares the performance of single vs. batch processing for audio transcription.
"""

import sys
import os
import time
import numpy as np
import json
import random
from pathlib import Path
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor

# Add the project's main_pc_code directory to the Python path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent / "main_pc_code"
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

from main_pc_code.utils import model_client

# Configuration
NUM_SAMPLES = 20  # Number of audio samples to generate
SAMPLE_RATE = 16000  # Sample rate in Hz
DURATION_SECONDS = 3  # Duration of each audio sample in seconds
BATCH_SIZES = [1, 2, 4, 8]  # Batch sizes to test

def generate_synthetic_audio(duration_seconds=3, sample_rate=16000):
    """Generate synthetic audio data (white noise with some structure)."""
    num_samples = int(duration_seconds * sample_rate)
    
    # Generate white noise
    audio = np.random.normal(0, 0.1, num_samples)
    
    # Add some structure (sine waves at different frequencies)
    for freq in [100, 200, 500, 1000]:
        t = np.arange(num_samples) / sample_rate
        audio += 0.1 * np.sin(2 * np.pi * freq * t)
    
    # Normalize
    audio = audio / np.max(np.abs(audio))
    
    return audio

def test_single_processing():
    """Test processing audio samples one by one."""
    print("Testing single processing...")
    
    # Generate audio samples
    audio_samples = [generate_synthetic_audio(DURATION_SECONDS, SAMPLE_RATE) for _ in range(NUM_SAMPLES)]
    
    # Process each sample individually
    start_time = time.time()
    results = []
    
    for i, audio in enumerate(audio_samples):
        print(f"Processing sample {i+1}/{NUM_SAMPLES}...")
        response = model_client.generate(
            prompt="Transcribe audio to text",
            quality="quality",
            audio_data=audio.tolist(),
            sample_rate=SAMPLE_RATE,
            model_type="stt"
        )
        results.append(response)
    
    total_time = time.time() - start_time
    avg_time = total_time / NUM_SAMPLES
    
    print(f"Single processing results:")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per sample: {avg_time:.4f} seconds")
    
    return total_time, avg_time, results

def test_batch_processing(batch_size):
    """Test processing audio samples in batches."""
    print(f"Testing batch processing with batch size {batch_size}...")
    
    # Generate audio samples
    audio_samples = [generate_synthetic_audio(DURATION_SECONDS, SAMPLE_RATE) for _ in range(NUM_SAMPLES)]
    
    # Create batches
    batches = [audio_samples[i:i+batch_size] for i in range(0, len(audio_samples), batch_size)]
    
    # Process each batch
    start_time = time.time()
    results = []
    
    for i, batch in enumerate(batches):
        print(f"Processing batch {i+1}/{len(batches)}...")
        
        # Prepare batch data
        batch_data = [
            {
                "audio_data": audio.tolist(),
                "sample_rate": SAMPLE_RATE,
                "request_id": f"batch_{i}_item_{j}"
            }
            for j, audio in enumerate(batch)
        ]
        
        # Send batch request
        response = model_client.generate(
            prompt="Batch transcribe audio to text",
            quality="quality",
            batch_mode=True,
            batch_data=batch_data,
            model_type="stt"
        )
        
        if response.get("status") == "success":
            results.extend(response.get("results", []))
        else:
            print(f"Error in batch {i+1}: {response.get('message', 'Unknown error')}")
    
    total_time = time.time() - start_time
    avg_time = total_time / NUM_SAMPLES
    
    print(f"Batch processing results (size={batch_size}):")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per sample: {avg_time:.4f} seconds")
    
    return total_time, avg_time, results

def test_concurrent_single_processing(num_workers=4):
    """Test processing audio samples concurrently but individually."""
    print(f"Testing concurrent single processing with {num_workers} workers...")
    
    # Generate audio samples
    audio_samples = [generate_synthetic_audio(DURATION_SECONDS, SAMPLE_RATE) for _ in range(NUM_SAMPLES)]
    
    # Process samples concurrently
    start_time = time.time()
    results = []
    
    def process_sample(audio):
        response = model_client.generate(
            prompt="Transcribe audio to text",
            quality="quality",
            audio_data=audio.tolist(),
            sample_rate=SAMPLE_RATE,
            model_type="stt"
        )
        return response
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_sample, audio) for audio in audio_samples]
        for future in futures:
            results.append(future.result())
    
    total_time = time.time() - start_time
    avg_time = total_time / NUM_SAMPLES
    
    print(f"Concurrent single processing results ({num_workers} workers):")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per sample: {avg_time:.4f} seconds")
    
    return total_time, avg_time, results

def plot_results(results):
    """Plot performance comparison results."""
    batch_sizes = [result["batch_size"] for result in results]
    avg_times = [result["avg_time"] for result in results]
    total_times = [result["total_time"] for result in results]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot average time per sample
    ax1.bar(range(len(batch_sizes)), avg_times, tick_label=[str(bs) for bs in batch_sizes])
    ax1.set_xlabel("Batch Size")
    ax1.set_ylabel("Average Time per Sample (s)")
    ax1.set_title("Average Processing Time per Sample")
    
    # Plot total processing time
    ax2.bar(range(len(batch_sizes)), total_times, tick_label=[str(bs) for bs in batch_sizes])
    ax2.set_xlabel("Batch Size")
    ax2.set_ylabel("Total Processing Time (s)")
    ax2.set_title("Total Processing Time")
    
    # Add speedup annotations
    baseline = total_times[0]  # Single processing is the baseline
    for i, total_time in enumerate(total_times):
        speedup = baseline / total_time if total_time > 0 else 0
        ax2.text(i, total_time + 0.5, f"{speedup:.2f}x", ha='center')
    
    plt.tight_layout()
    plt.savefig("batch_processing_results.png")
    print(f"Results saved to batch_processing_results.png")

def main():
    """Main function to run the tests."""
    print("Starting batch processing tests...")
    
    # Check if STT service is available
    try:
        status = model_client.get_status()
        if status.get("status") != "ok":
            print("Error: ModelManagerAgent is not available.")
            return
    except Exception as e:
        print(f"Error connecting to ModelManagerAgent: {e}")
        return
    
    results = []
    
    # Test single processing
    single_total, single_avg, _ = test_single_processing()
    results.append({
        "batch_size": 1,
        "total_time": single_total,
        "avg_time": single_avg
    })
    
    # Test batch processing with different batch sizes
    for batch_size in BATCH_SIZES[1:]:  # Skip batch size 1 as we already tested it
        batch_total, batch_avg, _ = test_batch_processing(batch_size)
        results.append({
            "batch_size": batch_size,
            "total_time": batch_total,
            "avg_time": batch_avg
        })
    
    # Test concurrent single processing
    concurrent_total, concurrent_avg, _ = test_concurrent_single_processing(4)
    results.append({
        "batch_size": "4 (concurrent)",
        "total_time": concurrent_total,
        "avg_time": concurrent_avg
    })
    
    # Print summary
    print("\nSummary of Results:")
    print("-" * 50)
    print(f"{'Batch Size':<15} {'Total Time (s)':<15} {'Avg Time (s)':<15} {'Speedup':<10}")
    print("-" * 50)
    
    baseline = results[0]["total_time"]
    for result in results:
        batch_size = result["batch_size"]
        total_time = result["total_time"]
        avg_time = result["avg_time"]
        speedup = baseline / total_time if total_time > 0 else 0
        
        print(f"{batch_size:<15} {total_time:<15.2f} {avg_time:<15.4f} {speedup:<10.2f}x")
    
    # Save results to file
    with open("batch_processing_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Plot results
    try:
        plot_results(results)
    except Exception as e:
        print(f"Error plotting results: {e}")
    
    print("\nBatch processing tests completed.")

if __name__ == "__main__":
    main() 