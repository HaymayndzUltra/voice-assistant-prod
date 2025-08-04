# tests/test_mainpc_gpu_allocation.py
import subprocess, pytest, time, requests, os

GPU_SERVICES = ["learning_gpu", "reasoning_gpu", "speech_gpu", "vision_gpu"]

@pytest.mark.parametrize("svc", GPU_SERVICES)
def test_gpu_visible(svc):
    out = subprocess.check_output(["docker", "exec", svc, "nvidia-smi", "-L"]).decode()
    assert "GPU" in out

@pytest.mark.skipif(os.getenv("FAILOVER") != "1", reason="run only in chaos stage")
def test_gpu_failover():
    subprocess.call(["docker", "kill", "vision_gpu"])
    time.sleep(4)
    r = requests.post("http://localhost:51100/coord/fallback_check", timeout=6)
    assert r.status_code == 200
