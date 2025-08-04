# tests/conftest_mainpc.py
import pytest, subprocess, time, socket

COMPOSE_FILE = "docker-compose.mainpc-local.yml"
TIMEOUT = 150
PORTS = list(range(51100, 52101, 100)) + [4318, 5601]  # service + observability

@pytest.fixture(scope="session", autouse=True)
def mainpc_stack():
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "pull"], check=True)
    up = subprocess.Popen(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"])
    up.wait(TIMEOUT)
    _wait_for_ports()
    yield
    subprocess.call(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"])

def _wait_for_ports():
    t0 = time.time()
    while time.time() - t0 < TIMEOUT:
        if all(_open("localhost", p) for p in PORTS):
            return
        time.sleep(2)
    raise RuntimeError("Main-PC services failed to expose required ports")

def _open(host, port):
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex((host, port)) == 0
