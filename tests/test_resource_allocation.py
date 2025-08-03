# tests/test_resource_allocation.py - Following test1.md Blueprint  
# verifies GPU binding and failover cases

import subprocess, json, pytest, os, time

def test_vision_gpu_has_visible_device():
    output = subprocess.check_output(["docker", "exec", "pc2_vision_dream_gpu", "nvidia-smi", "--query-gpu=index", "--format=csv,noheader"]).decode()
    assert output.strip() != ""

@pytest.mark.skipif(os.environ.get("E2E_FAILOVER") != "1", reason="run in failover pipeline only") 
def test_failover_cpu_takes_over():
    # simulate GPU container death
    subprocess.call(["docker", "kill", "pc2_vision_dream_gpu"])
    time.sleep(5)
    # assert cpu fallback alive
    import requests
    r = requests.get("http://localhost:50400/health", timeout=5)
    assert r.status_code == 200
