from common.core.base_agent import BaseAgent
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url
class DummyArgs:
    host = 'localhost'

def parse_agent_args():
    return DummyArgs() 