#!/usr/bin/env python3
"""
Memory System Performance Test

This script benchmarks the memory system under various load conditions
to identify performance bottlenecks and validate system scalability.
"""

import os
import sys
import time
import json
import logging
import random
import string
import threading
import statistics
import argparse
import zmq
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MemoryPerformanceTest")

# Import memory components (adjust paths as needed)
try:
    from main_pc_code.agents.memory_client import MemoryClient
except ImportError:
    logger.error("Could not import MemoryClient. Tests cannot run.")
    sys.exit(1)

class MemoryPerformanceTest:
    """
    Performance tests for the memory system.
    Tests system performance under various load conditions.
    """
    
    def __init__(self, num_clients=5, test_iterations=100):
        """Initialize the performance test harness"""
        self.num_clients = num_clients
        self.test_iterations = test_iterations
        self.clients = []
        self.results = {
            "add_memory": [],
            "get_memory": [],
            "search_memory": [],
            "batch_operations": []
        }
        self.test_data = {
            "memory_ids": [],
            "search_term": None
        }
    
    def setup(self):
        """Set up test environment with multiple clients"""
        try:
            logger.info(f"Initializing {self.num_clients} MemoryClient instances...")
            
            for i in range(self.num_clients):
                client = MemoryClient(agent_name=f"PerfTestClient{i}", port=5790 + i)
                client.set_agent_id(f"perf_test_{i}")
                
                # Check connection
                status = client.get_circuit_breaker_status()
                if status["status"] != "success":
                    logger.error(f"Failed to connect client {i} to MemoryOrchestratorService")
                    return False
                
                self.clients.append(client)
            
            logger.info(f"Successfully initialized {len(self.clients)} clients")
            
            # Create search test data
            unique_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            self.test_data["search_term"] = f"PERFTEST_{unique_id}"
            
            # Create some test memories for search and retrieval tests
            client = self.clients[0]
            for i in range(20):
                result = client.add_memory(
                    content=f"{self.test_data['search_term']} Performance test memory {i}",
                    memory_type="perf_test",
                    tags=["performance", "test"]
                )
                if result["status"] == "success":
                    self.test_data["memory_ids"].append(result["memory_id"])
            
            logger.info(f"Created {len(self.test_data['memory_ids'])} test memories")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up test environment"""
        logger.info("Cleaning up test environment...")
        
        # Delete test memories
        if self.clients and self.test_data["memory_ids"]:
            client = self.clients[0]
            for memory_id in self.test_data["memory_ids"]:
                try:
                    client.delete_memory(memory_id)
                except Exception:
                    pass
        
        # Clean up clients
        for client in self.clients:
            try:
                client.cleanup()
            except Exception:
                pass
        
        logger.info("Cleanup complete")
    
    def run_tests(self):
        """Run all performance tests"""
        if not self.setup():
            logger.error("Test setup failed. Cannot continue.")
            return False
        
        try:
            logger.info(f"Starting performance tests with {self.num_clients} clients and {self.test_iterations} iterations...")
            
            # Run the performance tests
            self.test_add_memory_performance()
            self.test_get_memory_performance()
            self.test_search_memory_performance()
            self.test_concurrent_operations()
            self.test_batch_vs_individual()
            
            # Report results
            self.report_results()
            return True
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return False
        finally:
            self.cleanup()
    
    def test_add_memory_performance(self):
        """Test add_memory performance under load"""
        logger.info("Testing add_memory performance...")
        
        latencies = []
        
        # Use ThreadPoolExecutor to simulate concurrent users
        with ThreadPoolExecutor(max_workers=self.num_clients) as executor:
            futures = []
            
            for i in range(self.test_iterations):
                client = random.choice(self.clients)
                content = f"Performance test memory {i} with some additional content to make it realistic"
                
                futures.append(
                    executor.submit(
                        self._measure_add_memory,
                        client,
                        content,
                        f"perf_test_{i % 5}",  # Vary memory types
                        random.uniform(0.3, 0.9)  # Vary importance
                    )
                )
            
            for future in as_completed(futures):
                try:
                    latency, memory_id = future.result()
                    latencies.append(latency)
                    if memory_id:
                        self.test_data["memory_ids"].append(memory_id)
                except Exception as e:
                    logger.error(f"Error in add_memory test: {e}")
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p50_latency = sorted(latencies)[int(len(latencies) * 0.5)]
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            
            self.results["add_memory"] = {
                "avg_ms": avg_latency,
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency,
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "operations_per_second": 1000 / avg_latency if avg_latency > 0 else 0
            }
            
            logger.info(f"Add Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms, P99={p99_latency:.2f}ms")
    
    def _measure_add_memory(self, client, content, memory_type, importance):
        """Helper method to measure add_memory performance"""
        start_time = time.time()
        result = client.add_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=["performance", "test"]
        )
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000  # Convert to ms
        memory_id = result.get("memory_id") if result.get("status") == "success" else None
        
        return latency, memory_id
    
    def test_get_memory_performance(self):
        """Test get_memory performance under load"""
        logger.info("Testing get_memory performance...")
        
        if not self.test_data["memory_ids"]:
            logger.warning("No memory IDs available for get_memory test")
            return
        
        latencies = []
        
        # Use ThreadPoolExecutor to simulate concurrent users
        with ThreadPoolExecutor(max_workers=self.num_clients) as executor:
            futures = []
            
            for i in range(self.test_iterations):
                client = random.choice(self.clients)
                memory_id = random.choice(self.test_data["memory_ids"])
                
                futures.append(
                    executor.submit(
                        self._measure_get_memory,
                        client,
                        memory_id
                    )
                )
            
            for future in as_completed(futures):
                try:
                    latency = future.result()
                    latencies.append(latency)
                except Exception as e:
                    logger.error(f"Error in get_memory test: {e}")
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p50_latency = sorted(latencies)[int(len(latencies) * 0.5)]
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            
            self.results["get_memory"] = {
                "avg_ms": avg_latency,
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency,
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "operations_per_second": 1000 / avg_latency if avg_latency > 0 else 0
            }
            
            logger.info(f"Get Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms, P99={p99_latency:.2f}ms")
    
    def _measure_get_memory(self, client, memory_id):
        """Helper method to measure get_memory performance"""
        start_time = time.time()
        client.get_memory(memory_id)
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000  # Convert to ms
        return latency
    
    def test_search_memory_performance(self):
        """Test search_memory performance under load"""
        logger.info("Testing search_memory performance...")
        
        if not self.test_data["search_term"]:
            logger.warning("No search term available for search_memory test")
            return
        
        latencies = []
        
        # Use ThreadPoolExecutor to simulate concurrent users
        with ThreadPoolExecutor(max_workers=self.num_clients) as executor:
            futures = []
            
            for i in range(self.test_iterations):
                client = random.choice(self.clients)
                
                futures.append(
                    executor.submit(
                        self._measure_search_memory,
                        client,
                        self.test_data["search_term"]
                    )
                )
            
            for future in as_completed(futures):
                try:
                    latency = future.result()
                    latencies.append(latency)
                except Exception as e:
                    logger.error(f"Error in search_memory test: {e}")
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p50_latency = sorted(latencies)[int(len(latencies) * 0.5)]
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
            
            self.results["search_memory"] = {
                "avg_ms": avg_latency,
                "p50_ms": p50_latency,
                "p95_ms": p95_latency,
                "p99_ms": p99_latency,
                "min_ms": min(latencies),
                "max_ms": max(latencies),
                "operations_per_second": 1000 / avg_latency if avg_latency > 0 else 0
            }
            
            logger.info(f"Search Memory Performance: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms, P99={p99_latency:.2f}ms")
    
    def _measure_search_memory(self, client, query):
        """Helper method to measure search_memory performance"""
        start_time = time.time()
        client.search_memory(query)
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000  # Convert to ms
        return latency
    
    def test_concurrent_operations(self):
        """Test system performance with mixed concurrent operations"""
        logger.info("Testing mixed concurrent operations...")
        
        operations = [
            "add", "add", "add",  # More adds to generate data
            "get", "get",
            "search"
        ]
        
        latencies = {
            "add": [],
            "get": [],
            "search": []
        }
        
        # Use ThreadPoolExecutor to simulate concurrent users with mixed operations
        with ThreadPoolExecutor(max_workers=self.num_clients * 2) as executor:
            futures = []
            
            for i in range(self.test_iterations * 2):  # Double iterations for mixed load
                client = random.choice(self.clients)
                operation = random.choice(operations)
                
                if operation == "add":
                    content = f"Concurrent test memory {i}"
                    futures.append(
                        executor.submit(
                            self._measure_add_memory,
                            client,
                            content,
                            "concurrent_test",
                            0.5
                        )
                    )
                elif operation == "get" and self.test_data["memory_ids"]:
                    memory_id = random.choice(self.test_data["memory_ids"])
                    futures.append(
                        executor.submit(
                            self._measure_get_memory,
                            client,
                            memory_id
                        )
                    )
                elif operation == "search":
                    futures.append(
                        executor.submit(
                            self._measure_search_memory,
                            client,
                            self.test_data["search_term"]
                        )
                    )
            
            for future, operation in zip(as_completed(futures), operations * (self.test_iterations * 2 // len(operations) + 1)):
                try:
                    if operation == "add":
                        latency, memory_id = future.result()
                        latencies["add"].append(latency)
                        if memory_id:
                            self.test_data["memory_ids"].append(memory_id)
                    else:
                        latency = future.result()
                        latencies[operation].append(latency)
                except Exception as e:
                    logger.error(f"Error in concurrent operations test: {e}")
        
        # Report results for each operation type
        for op_type, op_latencies in latencies.items():
            if op_latencies:
                avg_latency = statistics.mean(op_latencies)
                p95_latency = sorted(op_latencies)[int(len(op_latencies) * 0.95)]
                
                logger.info(f"Concurrent {op_type} operations: Avg={avg_latency:.2f}ms, P95={p95_latency:.2f}ms")
    
    def test_batch_vs_individual(self):
        """Compare batch operations vs individual operations"""
        logger.info("Testing batch vs individual operations...")
        
        batch_sizes = [5, 10, 20]
        
        for batch_size in batch_sizes:
            # Prepare batch data
            batch_memories = []
            for i in range(batch_size):
                batch_memories.append({
                    "content": f"Batch comparison test memory {i}",
                    "memory_type": "batch_comparison",
                    "memory_tier": "short",
                    "importance": 0.5,
                    "tags": ["performance", "batch_test"]
                })
            
            # Measure batch operation
            client = self.clients[0]
            batch_start_time = time.time()
            batch_result = client.batch_add_memories(batch_memories)
            batch_end_time = time.time()
            
            batch_latency = (batch_end_time - batch_start_time) * 1000  # ms
            
            # Measure individual operations
            individual_latencies = []
            for i in range(batch_size):
                start_time = time.time()
                client.add_memory(
                    content=f"Individual comparison test memory {i}",
                    memory_type="batch_comparison",
                    memory_tier="short",
                    importance=0.5,
                    tags=["performance", "individual_test"]
                )
                end_time = time.time()
                individual_latencies.append((end_time - start_time) * 1000)  # ms
            
            total_individual_latency = sum(individual_latencies)
            avg_individual_latency = statistics.mean(individual_latencies)
            
            # Store results
            self.results["batch_operations"].append({
                "batch_size": batch_size,
                "batch_latency_ms": batch_latency,
                "total_individual_latency_ms": total_individual_latency,
                "avg_individual_latency_ms": avg_individual_latency,
                "speedup_factor": total_individual_latency / batch_latency if batch_latency > 0 else 0
            })
            
            logger.info(f"Batch size {batch_size}: Batch={batch_latency:.2f}ms, Individual total={total_individual_latency:.2f}ms, Speedup={total_individual_latency/batch_latency:.2f}x")
    
    def report_results(self):
        """Generate a comprehensive performance report"""
        logger.info("==== Memory System Performance Report ====")
        logger.info(f"Test configuration: {self.num_clients} clients, {self.test_iterations} iterations per test")
        
        # Report add_memory performance
        if self.results["add_memory"]:
            logger.info("\n--- add_memory Performance ---")
            logger.info(f"Average latency: {self.results['add_memory']['avg_ms']:.2f} ms")
            logger.info(f"P50 latency: {self.results['add_memory']['p50_ms']:.2f} ms")
            logger.info(f"P95 latency: {self.results['add_memory']['p95_ms']:.2f} ms")
            logger.info(f"P99 latency: {self.results['add_memory']['p99_ms']:.2f} ms")
            logger.info(f"Min latency: {self.results['add_memory']['min_ms']:.2f} ms")
            logger.info(f"Max latency: {self.results['add_memory']['max_ms']:.2f} ms")
            logger.info(f"Operations per second: {self.results['add_memory']['operations_per_second']:.2f}")
        
        # Report get_memory performance
        if self.results["get_memory"]:
            logger.info("\n--- get_memory Performance ---")
            logger.info(f"Average latency: {self.results['get_memory']['avg_ms']:.2f} ms")
            logger.info(f"P50 latency: {self.results['get_memory']['p50_ms']:.2f} ms")
            logger.info(f"P95 latency: {self.results['get_memory']['p95_ms']:.2f} ms")
            logger.info(f"P99 latency: {self.results['get_memory']['p99_ms']:.2f} ms")
            logger.info(f"Min latency: {self.results['get_memory']['min_ms']:.2f} ms")
            logger.info(f"Max latency: {self.results['get_memory']['max_ms']:.2f} ms")
            logger.info(f"Operations per second: {self.results['get_memory']['operations_per_second']:.2f}")
        
        # Report search_memory performance
        if self.results["search_memory"]:
            logger.info("\n--- search_memory Performance ---")
            logger.info(f"Average latency: {self.results['search_memory']['avg_ms']:.2f} ms")
            logger.info(f"P50 latency: {self.results['search_memory']['p50_ms']:.2f} ms")
            logger.info(f"P95 latency: {self.results['search_memory']['p95_ms']:.2f} ms")
            logger.info(f"P99 latency: {self.results['search_memory']['p99_ms']:.2f} ms")
            logger.info(f"Min latency: {self.results['search_memory']['min_ms']:.2f} ms")
            logger.info(f"Max latency: {self.results['search_memory']['max_ms']:.2f} ms")
            logger.info(f"Operations per second: {self.results['search_memory']['operations_per_second']:.2f}")
        
        # Report batch vs individual performance
        if self.results["batch_operations"]:
            logger.info("\n--- Batch vs Individual Operations ---")
            for result in self.results["batch_operations"]:
                logger.info(f"Batch size: {result['batch_size']}")
                logger.info(f"  Batch latency: {result['batch_latency_ms']:.2f} ms")
                logger.info(f"  Total individual latency: {result['total_individual_latency_ms']:.2f} ms")
                logger.info(f"  Average individual latency: {result['avg_individual_latency_ms']:.2f} ms")
                logger.info(f"  Speedup factor: {result['speedup_factor']:.2f}x")
        
        logger.info("\n==== End of Performance Report ====")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Memory System Performance Test")
    parser.add_argument("--clients", type=int, default=5, help="Number of concurrent clients to simulate")
    parser.add_argument("--iterations", type=int, default=100, help="Number of test iterations per client")
    return parser.parse_args()

def main():
    """Run the performance tests"""
    args = parse_args()
    
    logger.info(f"Starting memory system performance test with {args.clients} clients and {args.iterations} iterations...")
    
    test = MemoryPerformanceTest(num_clients=args.clients, test_iterations=args.iterations)
    success = test.run_tests()
    
    if success:
        logger.info("✅ Performance tests completed successfully!")
        return 0
    else:
        logger.error("❌ Performance tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 