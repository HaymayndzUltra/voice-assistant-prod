from src.core.base_agent import BaseAgent
import time
import json
import zmq
import os
import logging
from datetime import datetime
import psutil
from datetime import datetime

USER_PROFILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'user_profile.json')
ZMQ_RESPONDER_PORT = 5558
REMINDER_CHECK_INTERVAL = 10  # seconds

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'proactive_agent.log')
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class ProactiveAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Proactive")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.connect(f"tcp://127.0.0.1:{zmq_port}")
        self.running = True
        logging.info(f"[Proactive] Ready. Checking reminders every {REMINDER_CHECK_INTERVAL} seconds.")

    def load_reminders(self):
        try:
            if not os.path.exists(USER_PROFILE_PATH):
                logging.warning("[Proactive] User profile not found for loading reminders.")
                return []
            with open(USER_PROFILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            reminders = []
            users = data.get('users', {})
            for user, info in users.items():
                for reminder in info.get('reminders', []):
                    reminders.append({**reminder, 'user': user})
            return reminders
        except Exception as e:
            logging.error(f"[Proactive] Error loading reminders: {e}")
            return []

    def mark_reminder_done(self, reminder):
        try:
            if not os.path.exists(USER_PROFILE_PATH):
                logging.warning("[Proactive] User profile not found for marking reminder done.")
                return
            with open(USER_PROFILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            user = reminder['user']
            reminders = data['users'].get(user, {}).get('reminders', [])
            reminders = [r for r in reminders if r['id'] != reminder['id']]
            data['users'][user]['reminders'] = reminders
            with open(USER_PROFILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"[Proactive] Marked reminder as done for user '{user}': {reminder.get('message','')} (ID: {reminder['id']})")
        except Exception as e:
            logging.error(f"[Proactive] Error marking reminder done: {e}")

    def check_and_announce_reminders(self):
        now = datetime.now().isoformat(timespec='minutes')
        reminders = self.load_reminders()
        for reminder in reminders:
            try:
                # Expect reminder to have 'time' (ISO format, up to minutes), 'message', and 'id'
                if reminder['time'] <= now:
                    msg = {
                        'text': f"Reminder for {reminder['user']}: {reminder['message']}",
                        'emotion': 'neutral',
                        'proactive': True
                    }
                    self.socket.send_string(json.dumps(msg))
                    logging.info(f"[Proactive] Announced reminder: {msg['text']}")
                    self.mark_reminder_done(reminder)
            except Exception as e:
                logging.error(f"[Proactive] Error announcing reminder: {e}")

    def get_active_user(self):
        # Placeholder: Integrate with face recognition or digital twin
        # Return the active user's name or ID
        try:
            # Example: Read from a file or service
            user_file = os.path.join(os.path.dirname(__file__), '..', 'active_user.txt')
            if os.path.exists(user_file):
                with open(user_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            logging.error(f"[Proactive] Error getting active user: {e}")
        return None

    def get_contextual_suggestion(self, user):
        # Placeholder: Integrate with digital twin, learning mode, or context engine
        # Return a suggestion string and emotion (for TTS)
        # Example: Suggest coffee if it's morning, or hydration if afternoon
        now = datetime.now()
        if now.hour < 12:
            return (f"Good morning {user}, would you like some coffee?", "cheerful")
        elif now.hour < 18:
            return (f"Hi {user}, remember to stay hydrated!", "encouraging")
        else:
            return (f"Good evening {user}, time to wind down and relax.", "calm")

    def check_and_announce_suggestions(self):
        user = self.get_active_user()
        if user:
            suggestion, emotion = self.get_contextual_suggestion(user)
            msg = {
                'text': suggestion,
                'emotion': emotion,
                'proactive': True,
                'type': 'suggestion',
                'user': user
            }
            self.socket.send_string(json.dumps(msg))
            logging.info(f"[Proactive] Announced suggestion: {suggestion} (Emotion: {emotion})")

    def run(self):
        logging.info("[Proactive] Proactive agent running.")
        try:
            while self.running:
                self.check_and_announce_reminders()
                self.check_and_announce_suggestions()
                time.sleep(REMINDER_CHECK_INTERVAL)
        except KeyboardInterrupt:
            logging.info("[Proactive] Shutting down.")
        except Exception as e:
            logging.error(f"[Proactive] Unexpected error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        try:
            self.running = False
            self.socket.close(0)
            self.context.term()
            logging.info("[Proactive] Cleaned up resources.")
        except Exception as e:
            logging.error(f"[Proactive] Error during cleanup: {e}")


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    agent = ProactiveAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise