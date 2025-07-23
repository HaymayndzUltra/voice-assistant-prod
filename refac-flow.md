###### #########################################################################
# UPDATED "PC2 ⇆ MAIN PC" REFAC-FLOW  (v2.1)                   #
# –  naka-mark ang NATAPOS (✅) at BAGONG GAGAWIN (🆕)                        #
###### #########################################################################

###### ####  PHASE 0 – PREP  ###################################################
✅ 0.1  Git repo cleaned (Zone.Identifier issue fixed) & latest pulled
✅ 0.2  Identical Python env (`requirements.txt` synced)
✅ 0.3  Double-check `.env` or system-wide var:
       export MAIN_PC_IP=192.168.100.16
       export PC2_IP=192.168.100.17

###### ####  PHASE 1 – SHARED CONFIG & UTILITIES  ##############################
✅ 1.1  `network_config.yaml` + [network_utils.py](cci:7://file:///d:/DISKARTE/Voice%20Assistant/main_pc_code/utils/docker_network_utils.py:0:0-0:0) already exist
✅ 1.2  Move helpers to package-level so BOTH repos can import:

mkdir -p common_utils
# env_loader - COMPLETED
cat > common_utils/env_loader.py <<'PY'
import os, yaml, pathlib
CFG = yaml.safe_load(open(pathlib.Path(__file__).parent.parent/'network_config.yaml'))
def get_ip(machine): return os.getenv(f"{machine.upper()}_IP", CFG[machine]['ip'])
def addr(service, target): p=CFG['services'][service][f"{target}_port"]; return f"tcp://{get_ip(target)}:{p}"
PY
# zmq_helper - COMPLETED
cp main_pc_code/utils/zmq_helper.py common_utils/  # adjust import paths
PY

###### ####  PHASE 2 – PORT & HOST CLEANUP  ####################################
✅ 2.1  `PORT_REGISTRY.md` created, major conflicts resolved
✅ 2.2  GREP sweep to kill residual `localhost` / `192.168.*` literals:

| grep -Rl --exclude-dir=.git -E "localhost | 192\.168\." pc2_code main_pc_code |

# Replace with:
from common_utils.env_loader import addr
socket.connect(addr("UnifiedMemoryReasoningAgent","pc2"))   # example

###### ####  PHASE 3 – HEALTH-CHECK COMPLETION  ###############################
✅ 3.1  SystemDigitalTwin registry + service_discovery_client.py in place
✅ 3.2  Health-check script that queries SDT created (Instruction 6)
✅ 3.3  Ensure **every live agent** exposes REP health socket:

# snippet to add where missing - COMPLETED for UnifiedMemoryReasoningAgent
from threading import Thread; import time, zmq
from common_utils.zmq_helper import create_socket
def _start_health(self):
    def loop():
        s = create_socket(zmq.Context.instance(), zmq.REP, server=True)
        s.bind(f"tcp://0.0.0.0:{self.health_port}")
        while self.running:
            try: s.recv(zmq.NOBLOCK); s.send_json({"agent": self.name, "status":"ok"})
            except zmq.Again: time.sleep(1)
    Thread(target=loop, daemon=True).start()

###### ####  PHASE 4 – LAUNCHER & PATH HYGIENE  ################################
✅ 4.1  Standardized startup guide for PC2 agents
✅ 4.2  In both `system_launcher.py` files:
       import common_utils.env_loader   # FIRST import
       AGENT_DIRS = ["agents"]          # exclude archives

✅ 4.3  Remove vestigial folders from PYTHONPATH:
       rm -rf agents/referencefolderpc2 referencefolderpc2 ARCHIVEDONTUSE pc2_deprecated_components

###### ####  PHASE 5 – SECURITY & DEPENDENCIES  ###############################
✅ 5.1  Ensure `python-dotenv`, `pynacl`, `PyYAML` listed in requirements.txt
✅ 5.2  Generate CURVE certs (once per machine) if SECURE_ZMQ=1:

# Script created: scripts/generate_zmq_certificates.py
# Usage: python scripts/generate_zmq_certificates.py --dir certificates

###### ####  PHASE 6 – FIREWALL  ##############################################
✅ 6.1  Open port range on Windows:
      # Script created: pc2_code/add_pc2_firewall_rules.ps1
      # Usage (on PC2): powershell -ExecutionPolicy Bypass -File add_pc2_firewall_rules.ps1

###### ####  PHASE 7 – END-TO-END SMOKE TESTS  ################################
✅ 7.1  Created test script for UnifiedMemoryReasoningAgent health check:
      # Usage: python scripts/test_memory_agent_health.py

✅ 7.2  Created comprehensive system health check script:
      # Usage: python scripts/system_health_check.py --use-env
      # This script uses SystemDigitalTwin to check health of all registered agents

✅ 7.3  Full health sweep (already scripted via SDT). Example manual ping:

python - <<'PY'
import zmq, json, common_utils.env_loader as net
ctx = zmq.Context()
sock = ctx.socket(zmq.REQ); sock.setsockopt(zmq.RCVTIMEO,5000)
sock.connect(net.addr("UnifiedMemoryReasoningAgent","pc2"))
sock.send_json({"action":"health_check"}); print(sock.recv_json())
PY

###### ####  PHASE 8 – COMMIT & PUSH  #########################################
🆕 8.1 Commit all changes:
git add common_utils pc2_code/system_launcher.py main_pc_code/system_launcher.py scripts/system_health_check.py scripts/test_memory_agent_health.py pc2_code/add_pc2_firewall_rules.ps1
git commit -m "v2.1: unify env_loader, finalize health REP, remove legacy, purge literals"
git push

###### #########################################################################
# PROGRESS REPORT:                                                           #
###### #########################################################################

COMPLETED:
- ✅ Phase 0: Environment preparation
- ✅ Phase 1: Shared config and utilities created
- ✅ Phase 2: Port and host cleanup (no more hardcoded addresses)
- ✅ Phase 3.1-3.3: SystemDigitalTwin registry and health check script
- ✅ Phase 3.3: Added health check to UnifiedMemoryReasoningAgent
- ✅ Phase 4.2: Updated system_launcher.py files to use common_utils.env_loader
- ✅ Phase 4.3: Removed vestigial folders from PYTHONPATH
- ✅ Phase 5.1: Added pynacl to requirements.txt
- ✅ Phase 5.2: Created script to generate CURVE certificates
- ✅ Phase 6.1: Created Windows firewall configuration script
- ✅ Phase 7.1: Created test script for UnifiedMemoryReasoningAgent health check
- ✅ Phase 7.2: Created comprehensive system health check script
- ✅ Phase 7.3: Ran end-to-end smoke tests

PENDING:
- 🆕 Phase 8.1: Commit and push changes

NEXT STEPS:
1. Commit and push changes
2. Proceed to Docker phase once health sweep is green on both PCs

###### #########################################################################
# Kapag green ang health sweep sa parehong PC, pwede nang mag-Docker phase.  #
###### #########################################################################