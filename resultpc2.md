<tee /home/kali/AI_SYSTEM_MONOREPO/pc2_diag.out | cat
===== IDENT =====
===== Hostname/IPs =====
DESKTOP-HDP663G.localdomain
172.18.220.229 

===== OS =====
Linux DESKTOP-HDP663G 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x
86_64 x86_64 x86_64 GNU/Linux
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy

===== REPO =====
===== Path =====
/home/kali/AI_SYSTEM_MONOREPO
AI_CURSOR_INTELLIGENCE_INTEGRATION_GUIDE.md
AI_SYSTEM_CODEBASE_AUDIT_REPORT.md
BAFINDINGS.MD
Blueprint.md
COMPLETE_GUIDE.md
COMPREHENSIVE_TESTING_RESULTS.md
COMPREHENSIVE_TESTING_SUITE_README.md
CONTRIBUTING.md
CURSOR_QUICK_START.md
DECOMMISSION_SUMMARY.md
DEPLOYMENT_GUIDE.md
DEPLOYMENT_SUCCESS_SUMMARY.md
DOCUMENTS_SOT
Dockerfile
Dockerfile.uoc
GUI_INTEGRATION_SUMMARY.md
HYBRID_SYSTEM_REPORT.md
High-minds_en_linux_v3_0_0.ppn
IMMEDIATE_ACTION_PLAN.md
IMPLEMENTATION_ACTION_PLAN.md
INTELLIGENT_CLEANUP_STRATEGY.md
MAIN_PC_TESTING_MISSION.md
MMA_TO_MMS_MIGRATION_EXECUTION_REPORT.md
MainPCAgentsDescription.md
MainPcDocs
Makefile
NEWPLAN
O3_DETAILED_IMPLEMENTATION_PROMPT.md
PC2_AGENT_STATUS_TEST.py
PC2_FAILURE_ANALYSIS.py
PC2_OPTIMIZATION_QUICKSTART.md
PC2_PULL_GUIDE.md
PLAN.MD
PRACTICAL_CURRENT_ANALYSIS.py
Procfile
README.md
README_CONTAINERIZED_SETUP.md
README_UOC.md
SESSION_CONSISTENCY_SOLUTION.md
SIMPLE_CURRENT_CHECK.py
SYSTEM_BLIND_SPOTS_EXECUTIVE_SUMMARY.md
UNUSED_IMPORT_CLEANUP_REPORT.md
WP-01_COMPLETION_REPORT.md
WP-02_COMPLETION_REPORT.md
WP-03_COMPLETION_REPORT.md
WP-04_COMPLETION_REPORT.md
WP-05_COMPLETION_REPORT.md
WP-06_COMPLETION_REPORT.md
WP-07_COMPLETION_REPORT.md
WP-07_HEALTH_UNIFICATION_REPORT.json

===== Git =====
true
dce9768223ffde7c210ec09bf98d2a29b56736dd
## main...origin/main
?? docker-compose.pc2.override.yaml
?? pc2_diag.out
?? pc2_diag.sh

===== Dirs =====
memory_fusion_hub
unified_observability_center
model_ops_coordinator

===== RUNTIME =====
===== Docker =====
Docker version 28.3.2, build 578ccf6
Docker Compose version v2.38.2-desktop.1

===== Containers =====
NAMES     IMAGE     PORTS     STATUS

===== Images (filtered) =====
ai_system_monorepo-rtap-pre          latest    13GB
ai_system_monorepo-mfh               latest    335MB
ai_system_monorepo-uoc-edge          latest    719MB

===== NETWORK =====
===== Listening ports =====

===== Firewall =====
[sudo] password for kali: 
Status: inactive

===== Ping MAINPC =====
MAINPC_IP not set

===== PYTHON =====
===== Python =====
Python 3.10.12
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)

===== Key packages =====
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1004, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'grpcio'
grpcio MISSING
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1004, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'grpcio_tools'
grpcio-tools MISSING
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1004, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'protobuf'
protobuf MISSING
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/usr/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1004, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'pyzmq'
pyzmq MISSING

===== GPU (optional) =====
===== nvidia-smi =====
Sat Aug  9 03:15:24 2025       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 575.57.04              Driver Version: 576.52         CUDA Version: 12.9     |
|-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 3060        On  |   00000000:01:00.0  On |                  N/A |
| 34%   53C    P0             37W /  170W |     857MiB /  12288MiB |      2%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
                                                                                         
+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+

===== RESOURCES =====
===== Disk =====
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdd       1007G  4.9G  951G   1% /

===== Memory =====
               total        used        free      shared  buff/cache   available
Mem:            23Gi       1.4Gi        21Gi       5.0Mi       966Mi        21Gi
Swap:          6.0Gi       1.0Mi       6.0Gi

DONE 2025-08-08T19:15:24Z
DESKTOP-HDP663G%


Quick notes
Docker/Compose present; no containers running. MFH/UOC/RTAP-pre images exist.
No NATS/RTAP/UOC ports currently listening.
Firewall inactive.
Python present, but grpcio, grpcio-tools, protobuf, pyzmq missing.
GPU visible via nvidia-smi.
MAINPC_IP not set; set it and rerun if you want ping verification.
Confidence: 98%
