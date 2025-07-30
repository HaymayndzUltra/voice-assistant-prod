from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import os
import json
import logging
import threading
import time
from playwright.sync_api import sync_playwright

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = str(PathManager.get_logs_dir() / "browser_automation_agent.log")
ZMQ_BROWSER_PORT = 5588

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)


class BrowserAutomationAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="BrowserAutomation")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        self.running = True
        self.browser = None
        self.page = None
        self.thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.thread.start()
        logging.info("[BrowserAutomation] Agent started.")

    def listen_loop(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=False)
            self.page = self.browser.new_page()
            while self.running:
                try:
                    msg = self.socket.recv_string()
                    command = json.loads(msg)
                    result = self.handle_command(command)
                except Exception as e:
                    result = {"status": "error", "reason": str(e)}
                self.socket.send_string(json.dumps(result))

    def handle_command(self, command):
        action = command.get("action")
        try:
            logging.info(f"[BrowserAutomation] Received action: {action}")
            if action == "goto":
                url = command["url"]
                self.page.goto(url)
                logging.info(f"Navigated to {url}")
                return {"status": "ok", "msg": f"Navigated to {url}"}
            elif action == "login":
                url = command["url"]
                username = command["username"]
                password = command["password"]
                username_selector = command["username_selector"]
                password_selector = command["password_selector"]
                submit_selector = command["submit_selector"]
                self.page.goto(url)
                self.page.fill(username_selector, username)
                self.page.fill(password_selector, password)
                self.page.click(submit_selector)
                logging.info(f"Login attempted at {url}")
                return {"status": "ok", "msg": "Login attempted"}
            elif action == "fill_form":
                url = command["url"]
                fields = command["fields"]
                self.page.goto(url)
                for selector, value in fields.items():
                    self.page.fill(selector, value)
                logging.info(f"Form filled at {url}")
                return {"status": "ok", "msg": "Form filled"}
            elif action == "click":
                selector = command["selector"]
                self.page.click(selector)
                logging.info(f"Clicked {selector}")
                return {"status": "ok", "msg": f"Clicked {selector}"}
            elif action == "scrape":
                selector = command["selector"]
                content = self.page.inner_text(selector)
                logging.info(f"Scraped content from {selector}")
                return {"status": "ok", "content": content}
            elif action == "download":
                url = command["url"]
                save_path = command["save_path"]
                self.page.goto(url)
                with self.page.expect_download() as download_info:
                    self.page.click(command["download_selector"])
                download = download_info.value
                download.save_as(save_path)
                logging.info(f"Downloaded file to {save_path}")
                return {"status": "ok", "msg": f"Downloaded to {save_path}"}
            elif action == "upload":
                url = command["url"]
                file_selector = command["file_selector"]
                file_path = command["file_path"]
                self.page.goto(url)
                if not os.path.exists(file_path):
                    logging.error(
                        f"Upload failed: file not found: {file_path}")
                    return {"status": "error",
                            "reason": f"File not found: {file_path}"}
                self.page.set_input_files(file_selector, file_path)
                logging.info(f"Uploaded {file_path}")
                return {"status": "ok", "msg": f"Uploaded {file_path}"}
            elif action == "submit_form":
                selector = command["selector"]
                self.page.click(selector)
                logging.info(f"Form submitted via {selector}")
                return {"status": "ok", "msg": "Form submitted"}
            elif action == "paste_output":
                app = command["app"]
                output = command["output"]
                # Security: sanitize app name
                safe_app = ''.join(
                    c for c in app if c.isalnum() or c in (
                        '_', '-'))
                output_file = f"output_to_{safe_app}.txt"
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output)
                logging.info(f"Output saved for {app} -> {output_file}")
                return {"status": "ok", "msg": f"Output saved for {app}"}
            else:
                logging.warning(f"Unknown action: {action}")
                return {"status": "error", "reason": "Unknown action"}
        except Exception as e:
            logging.error(
                f"[BrowserAutomation] Error handling action '{action}': {e}")
            return {"status": "error", "reason": str(e)}

    def stop(self):
        self.running = False
        if self.browser:
            self.browser.close()
        self.socket.close()
        self.context.term()
        logging.info("[BrowserAutomation] Stopped.")


if __name__ == "__main__":
    agent = BrowserAutomationAgent()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise