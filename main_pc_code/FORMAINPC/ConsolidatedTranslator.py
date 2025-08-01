import sys
PROJECT_ROOT = get_project_root()
MAIN_PC_CODE = get_main_pc_code()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from main_pc_code.utils.config_parser import parse_agent_args
args = parse_agent_args()
import time

def _get_health_status(self):
    # Default health status: Agent is running if its main loop is active.
    # This can be expanded with more specific checks later.
    status = "HEALTHY" if self.running else "UNHEALTHY"
    details = {
        "status_message": "Agent is operational.",
        "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
    }
    return {"status": status, "details": details}

# ... existing code ... 