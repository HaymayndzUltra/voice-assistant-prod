import sys
from common.utils.env_standardizer import get_env
from common.core.base_agent import BaseAgent
from common.utils.log_setup import configure_logging
from main_pc_code.agents.error_publisher import ErrorPublisher

# Configure logging
logger = configure_logging(__name__)

def get_project_root():
    return pathlib.Path(__file__).resolve().parent.parent

def get_main_pc_code():
    return pathlib.Path(__file__).resolve().parent.parent.parent

PROJECT_ROOT = get_project_root()
MAIN_PC_CODE = get_main_pc_code()
if PROJECT_ROOT not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if MAIN_PC_CODE not in sys.path:
    sys.path.append(str(MAIN_PC_CODE))

def _get_health_status(self):
    # Default health status: Agent is running if its main loop is active.
    status = "HEALTHY" if getattr(self, 'running', True) else "UNHEALTHY"
    details = {
        "status": status,
        "timestamp": time.time()
    }
    return {"status": status, "details": details}
