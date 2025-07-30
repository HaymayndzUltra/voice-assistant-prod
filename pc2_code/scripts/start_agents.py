import subprocess
import time
import os
import zmq
import argparse

def start_agent(script, args=None, port=None, dry_run=False):
    """Start an agent with proper parameters and check health"""
    try:
        cmd = ["python3", script]
        if args:
            cmd.extend(args)
        print(f"\n=== Starting {script} ===")
        print(f"Command: {' '.join(cmd)}")
        
        # Use the correct path for PC2 agents
        working_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
        print(f"Working directory: {working_dir}")
        
        if dry_run:
            return True
            
        # Start the process with more detailed error capture
        process = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Read and display startup output
        stdout, stderr = process.communicate()
        if stdout:
            print("\n=== Agent Output ===")
            print(stdout)
        if stderr:
            print("\n=== Error Output ===")
            print(stderr)
        
        # Give some time for initialization
        time.sleep(2)
        
        if process.returncode != 0:
            print(f"✗ Failed to start {script}: Process exited with code {process.returncode}")
            return False
        
        if port:
            print(f"\nChecking health on port {port}...")
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.connect(f"tcp://0.0.0.0:{port}")
            socket.setsockopt(zmq.RCVTIMEO, 10000)  # Increased timeout to 10 seconds
            
            try:
                socket.send_json({"action": "health_check"})
                response = socket.recv_json()
                print(f"✓ Health check passed: {response}")
                return True
            except Exception as e:
                print(f"✗ Health check failed: {e}")
                return False
            finally:
                socket.close()
                context.term()
        else:
            print("✓ Agent started successfully")
            return True
    except Exception as e:
        print(f"✗ Failed to start {script}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Start PC2 agents")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    args = parser.parse_args()
    
    print("\n=== Starting PC2 Agents in Order ===\n")
    
    # 1. Start TinyLlama Service first since it's needed by other agents
    print("=== Starting TinyLlama Service ===")
    if start_agent("tinyllama_service_enhanced.py", port=5615, dry_run=args.dry_run):
        print("✓ TinyLlama Service started successfully")
    else:
        print("✗ Failed to start TinyLlama Service")
    
    # 2. Start Unified Memory Reasoning Agent
    print("\n=== Starting Unified Memory Reasoning ===")
    if start_agent("UnifiedMemoryReasoningAgent.py", port=7105, dry_run=args.dry_run):
        print("✓ Unified Memory Reasoning started successfully")
    else:
        print("✗ Failed to start Unified Memory Reasoning")
    
    # 3. Start Consolidated Translator (needs --server parameter)
    print("\n=== Starting Consolidated Translator ===")
    if start_agent("consolidated_translator.py", ["--server"], port=5563, dry_run=args.dry_run):
        print("✓ Consolidated Translator started successfully")
    else:
        print("✗ Failed to start Consolidated Translator")
    
    # 4. Start DreamWorld Agent
    print("\n=== Starting DreamWorld Agent ===")
    if start_agent("DreamWorldAgent.py", port=7104, dry_run=args.dry_run):
        print("✓ DreamWorld Agent started successfully")
    else:
        print("✗ Failed to start DreamWorld Agent")
    
    # 5. Start Learning Adjuster
    print("\n=== Starting Learning Adjuster ===")
    if start_agent("LearningAdjusterAgent.py", port=7107, dry_run=args.dry_run):
        print("✓ Learning Adjuster started successfully")
    else:
        print("✗ Failed to start Learning Adjuster")
    
    # 6. Start Cognitive Model Agent
    print("\n=== Starting Cognitive Model Agent ===")
    if start_agent("CognitiveModelAgent.py", port=5644, dry_run=args.dry_run):
        print("✓ Cognitive Model Agent started successfully")
    else:
        print("✗ Failed to start Cognitive Model Agent")
    
    # 7. Start Episodic Memory Agent
    print("\n=== Starting Episodic Memory Agent ===")
    if start_agent("EpisodicMemoryAgent.py", port=7106, dry_run=args.dry_run):
        print("✓ Episodic Memory Agent started successfully")
    else:
        print("✗ Failed to start Episodic Memory Agent")
    
    # 8. Start Remote Connector Agent
    print("\n=== Starting Remote Connector Agent ===")
    if start_agent("remote_connector_agent.py", port=7124, dry_run=args.dry_run):
        print("✓ Remote Connector Agent started successfully")
    else:
        print("✗ Failed to start Remote Connector Agent")

if __name__ == "__main__":
    main()
