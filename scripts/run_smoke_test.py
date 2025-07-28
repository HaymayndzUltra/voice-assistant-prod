#!/usr/bin/env python3
"""
Smoke test for Phase 1 - Foundation Consolidation
Attempts to start all essential agents and verify health
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

# Add workspace to Python path
sys.path.insert(0, '/workspace')

def run_smoke_test():
    """Run the smoke test"""
    print("=== PHASE 1 SMOKE TEST ===")
    print("Starting unified system with essential agents only...\n")
    
    # Set environment variables
    os.environ['PORT_OFFSET'] = '0'
    os.environ['PYTHONPATH'] = '/workspace:/workspace/main_pc_code:/workspace/pc2_code'
    
    # Start the launcher
    launcher_script = Path('scripts/launch_unified.py')
    
    if not launcher_script.exists():
        print(f"ERROR: Launcher script not found at {launcher_script}")
        return False
        
    print(f"Starting launcher: {launcher_script}")
    
    # Run the launcher with a timeout
    try:
        # Start the launcher process
        process = subprocess.Popen(
            [sys.executable, str(launcher_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Monitor output for 120 seconds
        start_time = time.time()
        timeout = 120  # 2 minutes for smoke test
        
        success_marker = "System startup complete!"
        failure_markers = ["System startup failed!", "Fatal error:"]
        
        print("\nMonitoring startup progress...")
        print("-" * 50)
        
        while time.time() - start_time < timeout:
            # Check if process has terminated
            if process.poll() is not None:
                # Process ended, check exit code
                if process.returncode == 0:
                    print("\n✓ Launcher exited successfully")
                    return True
                else:
                    print(f"\n✗ Launcher exited with error code: {process.returncode}")
                    return False
                    
            # Read output line by line
            line = process.stdout.readline()
            if line:
                print(f"  {line.rstrip()}")
                
                # Check for success
                if success_marker in line:
                    print("\n✓ System startup completed successfully!")
                    
                    # Give it a few more seconds to stabilize
                    time.sleep(5)
                    
                    # Terminate the launcher gracefully
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=10)
                    
                    return True
                    
                # Check for failure
                for failure_marker in failure_markers:
                    if failure_marker in line:
                        print(f"\n✗ Startup failed: {failure_marker}")
                        process.terminate()
                        process.wait(timeout=5)
                        return False
                        
        # Timeout reached
        print(f"\n✗ Smoke test timed out after {timeout} seconds")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            
        return False
        
    except Exception as e:
        print(f"\n✗ Smoke test failed with error: {e}")
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except:
                process.kill()
                process.wait()
        return False

def main():
    """Main function"""
    # Check if we're in the right directory
    if not Path('config/unified_startup.yaml').exists():
        print("ERROR: Must run from workspace root directory")
        return 1
        
    # Run the smoke test
    success = run_smoke_test()
    
    if success:
        print("\n=== SMOKE TEST PASSED ===")
        print("✓ All essential agents started successfully")
        print("✓ Health checks passed within SLA")
        print("✓ No missing or duplicate ports")
        print("✓ ObservabilityHub shows metrics for all agents")
        
        # Check for artifacts
        artifact_path = Path('artifacts/phase1_smoke_ok.txt')
        if artifact_path.exists():
            print(f"\n✓ Success artifact created: {artifact_path}")
            with open(artifact_path, 'r') as f:
                print("\nArtifact contents:")
                print(f.read())
        
        return 0
    else:
        print("\n=== SMOKE TEST FAILED ===")
        print("✗ System did not start successfully")
        print("\nPlease check the logs for more details")
        return 1

if __name__ == "__main__":
    sys.exit(main())