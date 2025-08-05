# Para sa Primary Translator - diagnostic checker
import os, sys, subprocess

def check_primary_translator():
    script_path = "agents/translator_agent.py"
    if not os.path.exists(script_path):
        print(f"ERROR: Script doesn't exist at {script_path}")
        return False # Indicate failure
    print(f"SUCCESS: Script found at {script_path}")

    try:
        # Check if importable
        # Ensure the command correctly reflects how you'd import it in the project context
        # Assuming the script is in 'agents' and project root is in sys.path
        import_command = f"import sys; sys.path.insert(0, '.'); import agents.translator_agent"
        result = subprocess.run([sys.executable, "-c", import_command],
                            check=False, capture_output=True, text=True, timeout=10) # Increased timeout, added text=True
        if result.returncode == 0:
            print("Script can be imported successfully.")
        else:
            print(f"Import error (stdout): {result.stdout}")
            print(f"Import error (stderr): {result.stderr}")
            return False # Indicate failure
    except Exception as e:
        print(f"Exception during import check: {e}")
        return False # Indicate failure
    
    # Check port availability
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', 5563)
        print("Port 5563 is available.")
    except OSError as e: # More specific exception
        print(f"Port 5563 is already in use or not bindable. Error: {e}")
        # If it's in use, it might mean the service *tried* to start or another process has it.
        # This part of the script might not be conclusive if the service is meant to be running.
    finally:
        sock.close()
    
    # Check if the execution would work by examining the script's content
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
            print("\nScript content overview analysis:")
            
            # Check for common issues
            if "if __name__ == '__main__'" not in script_content:
                print("WARNING: Script doesn't have a main block that would execute on direct run")
            
            # Check for ZMQ bindings
            if "bind(f'tcp://0.0.0.0:5563')" not in script_content and "bind('tcp://0.0.0.0:5563')" not in script_content:
                print("WARNING: Script doesn't appear to bind to TCP port 5563 on 0.0.0.0")
            
            # Check for potential import errors
            required_imports = ["zmq", "json", "time", "sys", "os"]
            for imp in required_imports:
                if f"import {imp}" not in script_content and f"from {imp}" not in script_content:
                    print(f"WARNING: Script may be missing required import: {imp}")
    except Exception as e:
        print(f"Error analyzing script content: {e}")
    
    return True # Indicate potential for script to run if no import errors

if __name__ == "__main__":
    print("=== PRIMARY TRANSLATOR DIAGNOSTIC CHECK ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print("=========================================")
    
    if check_primary_translator():
        print("\nPrimary Translator diagnostic check suggests script is okay. Further checks needed if service still fails to start.")
    else:
        print("\nPrimary Translator diagnostic check FAILED. Review errors above.")
