from common.core.base_agent import BaseAgent
from common.env_helpers import get_env
class DummyArgs:
    host = 'localhost'

def parse_agent_args():
    return DummyArgs() 