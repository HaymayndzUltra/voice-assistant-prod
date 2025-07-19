from main_pc_code.src.core.base_agent import BaseAgent
import requests
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# import json
import logging

LOG_PATH = "web_search_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


def duckduckgo_search(query, max_results=3):
    """
    Performs a DuckDuckGo Instant Answer API search and returns a summary.
    """
    if not query or not query.strip():
        logging.warning('[WebSearch] No query provided for DuckDuckGo search (skipped).')
        return 'No query provided (skipped).'
    url = (
        f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}"
        f"&format=json&no_redirect=1&no_html=1&skip_disambig=1"
    )
    logging.info(f"[WebSearch] Searching DuckDuckGo: {query}")
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200 or not resp.content:
            logging.error(
                f'[WebSearch] DuckDuckGo API returned status {resp.status_code}')
            return f'DuckDuckGo API error: {resp.status_code}'
        data = resp.json()
        if data.get("AbstractText"):
            logging.info(
                f"[WebSearch] Found AbstractText result for query '{query}'")
            return data["AbstractText"]
        elif data.get("Answer"):
            logging.info(
                f"[WebSearch] Found Answer result for query '{query}'")
            return data["Answer"]
        elif data.get("RelatedTopics"):
            for topic in data["RelatedTopics"]:
                if isinstance(topic, dict) and topic.get("Text"):
                    logging.info(
                        f"[WebSearch] Found RelatedTopics result for query '{query}'")
                    return topic["Text"]
        logging.warning(
            f"[WebSearch] No relevant answer found for query '{query}'")
        return "Sorry, I couldn't find an answer."
    except Exception as e:
        logging.error(f"[WebSearch] Error during search: {e}")
        return f"Web search error: {e}"


import zmq
import json
from common.env_helpers import get_env

ZMQ_WEBSEARCH_PORT = 5592

if __name__ == "__main__":
    import sys

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(duckduckgo_search(query))
    else:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        socket.bind(f"tcp://127.0.0.1:{ZMQ_WEBSEARCH_PORT}")
        logging.info(f"[WebSearch] Agent started on port {ZMQ_WEBSEARCH_PORT}.")
        try:
            while True:
                try:
                    msg = socket.recv_string()
                    req = json.loads(msg)
                    query = req.get("query", "")
                    logging.info(f"[WebSearch] Received query: '{query}'")
                    result = duckduckgo_search(query)
                    resp = json.dumps({"result": result})
                    socket.send_string(resp)
                except Exception as e:
                    logging.error(f"[WebSearch] Error handling request: {e}")
                    socket.send_string(json.dumps({"result": f"[ERROR] {e}"}))
        except KeyboardInterrupt:
            logging.info("[WebSearch] KeyboardInterrupt received. Exiting...")
        finally:
            socket.close(0)
            context.term()
            logging.info("[WebSearch] Agent stopped.")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise