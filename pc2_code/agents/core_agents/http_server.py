from common.core.base_agent import BaseAgent
def setup_health_check_server():
    class DummyServer:
        @staticmethod
        def stop():
            pass
    return DummyServer() 