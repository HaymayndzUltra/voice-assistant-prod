from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import os
from langdetect import detect
from textblob import TextBlob
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
import logging
import threading
import time
from difflib import get_close_matches
import re
try:
    import dateparser
except ImportError:
    import subprocess
    import sys
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "dateparser"])
    import dateparser
import uuid
import numpy as np
from collections import deque


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path
# Import the advanced context manager
try:
from main_pc_code.agents.context_manager import ContextManager, create_context_manager
    except ImportError as e:
        print(f"Import error: {e}")
    has_advanced_context = True
    logging.info("[Interpreter] Advanced context management loaded successfully")
except ImportError as e:
    has_advanced_context = False
    logging.warning(f"[Interpreter] Advanced context management not available: {e}")

import importlib.util

# Updated to use the new unified contextual memory agent
MEMORY_AGENT_PORT = 5596  # Changed from 5590 to use the new unified memory agent

# Settings
ZMQ_LISTENER_PORT = 5555
ZMQ_FACE_PORT = 5556  # Port for face recognition agent
MODEL_PATH = join_path("models", "mistral")  # Change to your local LLM path
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
LOG_PATH = "interpreter_agent.log"
USER_PROFILE_PATH = "user_profile.json"
CONTEXT_WINDOW_SIZE = 10  # Number of recent interactions to keep in context
EMOTION_MEMORY_SIZE = 5  # Number of recent emotions to track for mood analysis

# Add the same COMMAND_MAP as in executor.py for command extraction
COMMAND_MAP = {
    "open notepad": None,
    "open calculator": None,
    "shutdown": None,
    "open edge": None,
    "lock computer": None,
    # Add more mappings here if needed
}

# Intent classifier (simple, can be replaced with ML model)
INTENT_KEYWORDS = {
    "open_notepad": ["notepad", "note"],
    "open_calculator": ["calculator", "calc"],
    "shutdown": ["shutdown", "turn off", "power off"],
    "open_edge": ["edge", "browser", "internet"],
    "lock_computer": ["lock", "secure"],
}

# Logging setup
# Centralized logging: Forward logs to orchestrator
import zmq
ZMQ_LOG_PORT = 5600  # Central log collector port
log_context = zmq.Context()
log_socket = log_context.socket(zmq.PUB)
log_socket.connect(f"tcp://127.0.0.1:{ZMQ_LOG_PORT}")

def send_log(level, msg):
    log_msg = json.dumps({"agent": "interpreter", "level": level, "message": msg, "timestamp": time.time()})
    try:
        log_socket.send_string(log_msg)
    except Exception as e:
        # Fallback to local logging if ZMQ fails
        logging.error(f"[Interpreter] Failed to send log to orchestrator: {e}")
        logging.log(getattr(logging, level.upper(), logging.INFO), msg)


class InterpreterAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Interpreter")
        self.context = zmq.Context()
        
        # Set up listener socket for speech input
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f"tcp://127.0.0.1:{zmq_port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Set up face recognition socket
        self.face_socket = self.context.socket(zmq.SUB)
        self.face_socket.connect(f"tcp://127.0.0.1:{zmq_face_port}")
        self.face_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Initialize LLM
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path).to(device)
        self.device = device
        
        # Try to load emotion classifier
        try:
            self.emotion_classifier = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                top_k=3
            )
            self.has_emotion_classifier = True
            logging.info("[Interpreter] Advanced emotion classifier loaded successfully")
        except Exception as e:
            logging.warning(f"[Interpreter] Advanced emotion classifier not loaded: {e}")
            self.has_emotion_classifier = False
        
        # Set up output sockets
        self.executor_socket = self.context.socket(zmq.PUB)
        self.executor_socket.connect(f"tcp://127.0.0.1:{zmq_executor_port}")
        self.responder_socket = self.context.socket(zmq.PUB)
        self.responder_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5558")
        
        # Set up Memory Agent REQ socket
        self.memory_socket = self.context.socket(zmq.REQ)
        self.memory_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.memory_socket.connect(f"tcp://127.0.0.1:{MEMORY_AGENT_PORT}")
        
        # Cached memory data
        self.memory_reminders = []
        self.memory_profile = None
        self.memory_context = []
        
        # Load history and user profiles
        self.history_path = history_path
        self.history = self.load_history()
        self.user_profile = self.load_user_profile()
        
        # Set active user or prompt for new user if none
        if not self.user_profile.get(
                "active_user") or self.user_profile["active_user"] not in self.user_profile["users"]:
            self.set_active_user()
        self.active_user = self.user_profile["active_user"]
        
        # Load user data from Memory Agent at startup
        self.load_memory_agent_user_data(self.active_user)
        
        # Initialize context management system
        if has_advanced_context:
            # Use advanced context manager if available
            self.context_manager = create_context_manager()
            logging.info("[Interpreter] Using advanced context management")
        else:
            # Fallback to simple context window
            self.context_window = deque(maxlen=CONTEXT_WINDOW_SIZE)
            logging.info("[Interpreter] Using simple context management")
        
        # Emotion tracking with improved memory
        self.emotion_memory = deque(maxlen=EMOTION_MEMORY_SIZE)
        self.emotion_trends = {}  # Track emotion trends over time
        
        # Face recognition integration
        self.detected_faces = {}  # Track detected faces from face recognition agent
        self.current_speaker = None  # Currently speaking person detected by face recognition
        self.speaker_context = {}  # Separate context for each detected speaker
        
        # Set up persona and command map
        self.persona = (
            "You are Jarvis, a helpful, witty, privacy-focused, and emotionally intelligent AI assistant. "
            "Always respect user privacy and adapt your tone to the user's mood. "
            "Use the detected user's name and emotional state to personalize your responses."
        )
        self.command_map = COMMAND_MAP.copy()
        
        # Set up monitoring
        self.last_health_check = time.time()
        self.health_status = "OK"
        
        # Start background threads
        self.face_thread = threading.Thread(target=self.face_recognition_listener, daemon=True)
        self.face_thread.start()
        
        self.hot_reload_thread = threading.Thread(
            target=self.hot_reload_watcher,
            daemon=True)
        self.hot_reload_thread.start()

    def load_history(self):
        # Load only the last 100 entries for memory efficiency
        if os.path.exists(self.history_path):
            with open(self.history_path, "r", encoding="utf-8") as f:
                all_history = json.load(f)
                return all_history[-100:] if isinstance(all_history, list) else []
        return []

    def save_history(self):
        # Only keep the last 100 entries in memory and on disk
        self.history = self.history[-100:]
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def load_user_profile(self):
        """
        Loads user profiles from disk. Supports migration from single to multi-user format.
        Returns a dictionary keyed by user name, each containing preferences, history, etc.
        """
        if os.path.exists(USER_PROFILE_PATH):
            with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                profile = json.load(f)
                # Migrate old format if needed
                if isinstance(
                        profile,
                        dict) and "name" not in profile and "users" not in profile:
                    # Legacy single-user format, wrap in multi-user
                    profile = {
                        "users": {
                            "default": {
                                "name": "default",
                                "preferences": profile.get(
                                    "preferences",
                                    {}),
                                "taught_commands": profile.get(
                                    "taught_commands",
                                    {}),
                                "interaction_history": [],
                                "last_seen": None}},
                        "active_user": "default"}
                return profile
        # New file: create empty multi-user structure
        return {"users": {}, "active_user": None}

    def save_user_profile(self):
        """Save user profiles to disk."""
        with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.user_profile, f, ensure_ascii=False, indent=2)

    # Filipino language keywords and patterns
    FILIPINO_KEYWORDS = [
        'ako', 'ikaw', 'siya', 'kami', 'tayo', 'kayo', 'sila',  # Pronouns
        'ang', 'ng', 'sa', 'na', 'ay',  # Common particles
        'kumusta', 'salamat', 'po', 'opo', 'hindi',  # Common words
        'gusto', 'ayaw', 'pwede', 'kailangan',  # Modal verbs
        'mahal', 'maganda', 'masaya', 'malungkot',  # Adjectives
        'umaga', 'tanghali', 'hapon', 'gabi',  # Time of day
        'paki', 'pakiusap', 'tulungan', 'buksan', 'isara'  # Commands
    ]
    
    # English keywords for comparison
    ENGLISH_KEYWORDS = [
        'i', 'you', 'he', 'she', 'we', 'they',  # Pronouns
        'the', 'a', 'an', 'of', 'in', 'on', 'at',  # Articles and prepositions
        'hello', 'thanks', 'please', 'yes', 'no',  # Common words
        'want', 'need', 'can', 'must', 'should',  # Modal verbs
        'love', 'beautiful', 'happy', 'sad',  # Adjectives
        'morning', 'noon', 'afternoon', 'evening',  # Time of day
        'help', 'open', 'close', 'turn'  # Commands
    ]
    
    def detect_language(self, text):
        """Enhanced language detection with special handling for Filipino"""
        # Normalize text for analysis
        text_lower = text.lower()
        words = text_lower.split()
        
        # Count Filipino and English keywords
        filipino_count = sum(1 for word in words if word in self.FILIPINO_KEYWORDS)
        english_count = sum(1 for word in words if word in self.ENGLISH_KEYWORDS)
        
        # Calculate keyword density (percentage of words that match keywords)
        if len(words) > 0:
            filipino_density = filipino_count / len(words)
            english_density = english_count / len(words)
        else:
            filipino_density = english_density = 0
        
        # Check for code-switching (mixed Filipino and English)
        is_code_switching = filipino_count > 0 and english_count > 0
        
        # Try standard language detection first
        try:
            detected_lang = detect(text)
            
            # Override standard detection in certain cases
            if detected_lang == "tl" or filipino_density > 0.2:
                return "Filipino"
            elif detected_lang == "en" or english_density > 0.2:
                return "English"
            elif is_code_switching:
                # Determine dominant language in code-switching
                if filipino_density > english_density:
                    return "Filipino-English"
                else:
                    return "English-Filipino"
            else:
                # Use the standard detection result
                return detected_lang.capitalize()
                
        except Exception as e:
            logging.warning(f"[Interpreter] Language detection error: {e}")
            
            # Fallback to keyword-based detection
            if filipino_count > english_count:
                return "Filipino"
            elif english_count > filipino_count:
                return "English"
            elif filipino_count > 0:
                return "Filipino"
            else:
                return "Unknown"

    def face_recognition_listener(self):
        """Background thread to listen for face recognition events"""
        logging.info("[Interpreter] Face recognition listener started")
        while True:
            try:
                msg = self.face_socket.recv_string(flags=zmq.NOBLOCK)
                data = json.loads(msg)
                
                # Handle different event types from face recognition agent
                event_type = data.get("event")
                
                if event_type == "face_detected":
                    name = data.get("name")
                    timestamp = data.get("timestamp")
                    emotion = data.get("emotion", "neutral")
                    confidence = data.get("confidence", 0.0)
                    
                    # Update detected faces
                    self.detected_faces[name] = {
                        "last_seen": timestamp,
                        "emotion": emotion,
                        "confidence": confidence
                    }
                    
                    # If high confidence, set as current speaker
                    if confidence > 0.8 and name != "Unknown":
                        self.current_speaker = name
                        # Auto-switch user if needed
                        if name != self.active_user and name in self.user_profile["users"]:
                            logging.info(f"[Interpreter] Auto-switching to detected user: {name}")
                            self.active_user = name
                            self.user_profile["active_user"] = name
                            self.save_user_profile()
                            # Load user data from Memory Agent on user switch
                            self.load_memory_agent_user_data(name)
                    
                    logging.info(f"[Interpreter] Face detected: {name} with emotion {emotion}")
                    
                elif event_type == "face_enrolled":
                    name = data.get("name")
                    # Create user profile if it doesn't exist
                    if name not in self.user_profile["users"]:
                        self.user_profile["users"][name] = {
                            "name": name,
                            "preferences": {},
                            "taught_commands": {},
                            "interaction_history": [],
                            "last_seen": time.time()
                        }
                        self.save_user_profile()
                        logging.info(f"[Interpreter] New user profile created for {name}")
            
            except zmq.Again:
                # No message available, continue
                pass
            except Exception as e:
                logging.error(f"[Interpreter] Error in face recognition listener: {e}")
            
            time.sleep(0.1)  # Small sleep to prevent CPU hogging

    def load_memory_agent_user_data(self, user_id):
        """Fetch user profile, reminders, and memory from Memory Agent."""
        try:
            # Get profile
            self.memory_socket.send_string(json.dumps({"action": "get_profile", "user_id": user_id}))
            profile_resp = json.loads(self.memory_socket.recv_string())
            self.memory_profile = profile_resp.get("profile")
            # Get reminders
            self.memory_socket.send_string(json.dumps({"action": "list_reminders", "user_id": user_id}))
            reminders_resp = json.loads(self.memory_socket.recv_string())
            self.memory_reminders = reminders_resp.get("reminders", [])
            # Get recent memory
            self.memory_socket.send_string(json.dumps({"action": "get_memory", "user_id": user_id, "limit": 10}))
            memory_resp = json.loads(self.memory_socket.recv_string())
            self.memory_context = memory_resp.get("memory", [])
            logging.info(f"[Interpreter] Loaded memory agent data for user: {user_id}")
        except Exception as e:
            logging.error(f"[Interpreter] Error loading memory agent data for {user_id}: {e}")

    def detect_emotion(self, text):
        """Enhanced emotion detection using multiple methods"""
        try:
            # Start with basic TextBlob sentiment analysis
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Use advanced emotion classifier if available
            if self.has_emotion_classifier:
                try:
                    # Get top 3 emotions with confidence scores
                    emotions = self.emotion_classifier(text)
                    # Extract the top emotion
                    top_emotion = emotions[0][0]["label"]
                    confidence = emotions[0][0]["score"]
                    
                    # Store in emotion memory for trend analysis
                    self.emotion_memory.append({
                        "emotion": top_emotion,
                        "confidence": confidence,
                        "timestamp": time.time()
                    })
                    
                    # Return detailed emotion with confidence
                    return f"{top_emotion} ({confidence:.2f})"
                except Exception as e:
                    logging.warning(f"[Interpreter] Advanced emotion detection failed: {e}")
            
            # Fallback to basic sentiment analysis
            if polarity > 0.2:
                mood = "positive"
            elif polarity < -0.2:
                mood = "negative"
            else:
                mood = "neutral"
                
            if subjectivity > 0.5:
                mood += ", subjective"
            else:
                mood += ", objective"
                
            return mood
        except Exception as e:
            logging.error(f"[Interpreter] Emotion detection failed: {e}")
            return "neutral, objective"

    def send_command(self, command):
        msg = json.dumps({"command": command})
        self.executor_socket.send_string(msg)
        logging.info(f"Sent command to Executor: {command}")

    def extract_command(self, response):
        # Fuzzy and intent-based matching
        response_lower = response.lower()
        for cmd in self.command_map:
            if all(word in response_lower for word in cmd.split()):
                return cmd
        # Fuzzy match
        close = get_close_matches(
            response_lower,
            self.command_map.keys(),
            n=1,
            cutoff=0.7)
        if close:
            return close[0]
        # Intent-based
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(word in response_lower for word in keywords):
                for cmd in self.command_map:
                    if intent.replace("_", " ") in cmd:
                        return cmd
        # User-taught commands (now per user)
        user = self.active_user
        taught_commands = self.user_profile["users"].get(
            user, {}).get("taught_commands", {})
        for taught, phrase in taught_commands.items():
            if phrase in response_lower:
                return taught
        return None

    import threading
    ANALYTICS_PATH = "usage_analytics.json"
    analytics_lock = threading.Lock()

    def log_usage_analytics(self, user, text, command, response):
        entry = {
            "timestamp": time.time(),
            "user": user,
            "text": text,
            "command": command,
            "response": response
        }
        with analytics_lock:
            try:
                if os.path.exists(ANALYTICS_PATH):
                    with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = []
                data.append(entry)
                with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                logging.error(f"[Analytics] Failed to log usage: {e}")

    def clear_usage_analytics(self, user):
        """Remove all analytics entries for the specified user from usage_analytics.json."""
        with analytics_lock:
            try:
                if os.path.exists(ANALYTICS_PATH):
                    with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data = [entry for entry in data if entry.get("user") != user]
                    with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                logging.error(f"[Analytics] Failed to clear analytics for {user}: {e}")

    def clear_history(self):
        """Clear conversation history for the active user."""
        self.history = []
        self.save_history()

    def clear_reminders(self, user=None):
        """Clear all reminders for the specified user via MemoryAgent."""
        user = user or self.active_user
        try:
            self.memory_socket.send_string(json.dumps({
                "action": "delete_all_reminders",
                "user_id": user
            }))
            resp = json.loads(self.memory_socket.recv_string())
            if resp.get("status") == "ok":
                logging.info(f"[Interpreter] Cleared reminders for {user}")
        except Exception as e:
            logging.error(f"[Interpreter] Failed to clear reminders for {user}: {e}")

    def process_text(self, text, speaker_data=None):
        """Process text input with enhanced context awareness and face recognition integration"""
        # Taglish detection integration
from main_pc_code.agents.taglish_detector import detect_taglish
from common.env_helpers import get_env
        is_taglish, fil_ratio, eng_ratio = detect_taglish(text)
        if is_taglish:
            logging.info(f"[Interpreter] Taglish detected: Filipino={fil_ratio:.2f}, English={eng_ratio:.2f}")
        # Check for user switching or profile update commands
        if self.check_user_profile_commands(text):
            self.log_usage_analytics(self.active_user, text, "profile_command", "Profile updated.")
            return "Profile updated."
        
        # Privacy: Clear data/history/reminders commands
        lowered = text.lower().strip()
        if lowered in ["clear my data", "clear my history", "clear my reminders"]:
            user = self.active_user
            if lowered == "clear my data":
                # Clear all user data
                if user in self.user_profile["users"]:
                    self.user_profile["users"][user] = {
                        "name": user,
                        "preferences": {},
                        "taught_commands": {},
                        "interaction_history": [],
                        "last_seen": time.time()
                    }
                    self.save_user_profile()
                    # Clear context using appropriate method
                    if has_advanced_context:
                        self.context_manager.clear_context(speaker=user)
                    else:
                        self.context_window.clear()
                    return "All your data has been cleared."
            elif lowered == "clear my history":
                # Clear conversation history only
                if user in self.user_profile["users"]:
                    self.user_profile["users"][user]["interaction_history"] = []
                    self.save_user_profile()
                    # Clear context using appropriate method
                    if has_advanced_context:
                        self.context_manager.clear_context(speaker=user)
                    else:
                        self.context_window.clear()
                    return "Your conversation history has been cleared."
            elif lowered == "clear my reminders":
                # Clear reminders only
                if user in self.user_profile["users"]:
                    self.user_profile["users"][user]["reminders"] = []
                    self.save_user_profile()
                    return "Your reminders have been cleared."

        # Add to context using appropriate method
        speaker = speaker_data["name"] if speaker_data else self.active_user
        language = self.detect_language(text)
        emotion = self.detect_emotion(text)
        
        # Add metadata for context tracking
        metadata = {
            "language": language,
            "emotion": emotion,
            "timestamp": time.time()
        }
        
        # Use advanced context manager if available
        if has_advanced_context:
            self.context_manager.add_to_context(text, speaker=speaker, metadata=metadata)
        else:
            # Fallback to simple context window
            self.context_window.append({
                "text": text,
                "speaker": speaker,
                "timestamp": time.time(),
                "language": language,
                "emotion": emotion
            })

        # Get face recognition context if available
        face_context = ""
        if self.current_speaker and self.current_speaker in self.detected_faces:
            face_data = self.detected_faces[self.current_speaker]
            face_emotion = face_data.get("emotion", "neutral")
            face_context = f"\nDetected user: {self.current_speaker} with facial emotion: {face_emotion}"

            # If speaker is different from active user, consider switching
            if self.current_speaker != self.active_user and self.current_speaker in self.user_profile["users"]:
                # Check if we should auto-switch based on confidence
                if face_data.get("confidence", 0) > 0.8:
                    self.active_user = self.current_speaker
                    self.user_profile["active_user"] = self.current_speaker
                    self.save_user_profile()
                    logging.info(f"[Interpreter] Switched to user: {self.current_speaker} based on face recognition")

        # NLU for reminders
        reminder_match = re.search(
            r"remind me to (.+?) (?:at|on|by|in|tomorrow|today|tonight|this|next|after|before)? (.+)?",
            text,
            re.IGNORECASE)
        set_reminder_match = re.search(
            r"set a reminder[:]? (.+)", text, re.IGNORECASE)
        if reminder_match or set_reminder_match:
            # Try to extract message and time
            if reminder_match:
                message = reminder_match.group(1).strip()
                time_str = reminder_match.group(2) or ""
            else:
                # Try to split message and time
                msg = set_reminder_match.group(1).strip()
                # Try to find ' at ', ' on ', etc.
                split = re.split(
                    r" at | on | by | in | tomorrow| today| tonight| this | next | after | before ",
                    msg,
                    maxsplit=1,
                    flags=re.IGNORECASE)
                message = split[0].strip()
                time_str = split[1].strip() if len(split) > 1 else ""
            # Parse time
            dt = dateparser.parse(
                time_str, settings={
                    "PREFER_DATES_FROM": "future"}) if time_str else None
            if not dt:
                # Try to parse from whole text if time_str failed
                dt = dateparser.parse(
                    text, settings={
                        "PREFER_DATES_FROM": "future"})
            if not dt:
                response = "Sorry, I couldn't understand the reminder time. Please try again."
                self.responder_socket.send_string(json.dumps(
                    {"text": response, "emotion": "neutral"}))
                return response
            iso_time = dt.replace(second=0, microsecond=0).isoformat()
            user = self.active_user
            reminder_id = str(uuid.uuid4())
            # Send to Memory Agent
            try:
                self.memory_socket.send_string(json.dumps({
                    "action": "add_reminder",
                    "user_id": user,
                    "reminder": {
                        "id": reminder_id,
                        "time": iso_time,
                        "message": message
                    }
                }))
                _ = self.memory_socket.recv_string()
                # Update local cache
                self.memory_reminders.append({
                    "id": reminder_id,
                    "time": iso_time,
                    "message": message
                })
            except Exception as e:
                logging.error(f"[Interpreter] Failed to send reminder to Memory Agent: {e}")
            response = f"Okay, reminder set for {dt.strftime('%A, %B %d at %I:%M %p')}: '{message}'"
            self.responder_socket.send_string(json.dumps(
                {"text": response, "emotion": "positive"}))
            return response
        # Check for 'show my reminders' intent
        if re.search(r"show (me|my)? ?reminders|what are my reminders|list reminders", text, re.IGNORECASE):
            user = self.active_user
            # Query Memory Agent for reminders
            try:
                self.memory_socket.send_string(json.dumps({
                    "action": "list_reminders",
                    "user_id": user
                }))
                resp = json.loads(self.memory_socket.recv_string())
                reminders = resp.get("reminders", [])
                if not reminders:
                    response = "You have no reminders."
                else:
                    lines = [f"- {r['message']} at {r['time']}" for r in reminders]
                    response = "Here are your reminders:\n" + "\n".join(lines)
            except Exception as e:
                response = f"Sorry, I couldn't fetch your reminders. Error: {e}"
            self.responder_socket.send_string(json.dumps(
                {"text": response, "emotion": "neutral"}))
            return response

        # Web search intent detection (simple:
        # who/what/when/where/why/how/question mark)
        web_search_triggers = [
            r"^who ",
            r"^what ",
            r"^when ",
            r"^where ",
            r"^why ",
            r"^how ",
            r"\?"]
        if any(re.search(trigger, text.strip().lower())
               for trigger in web_search_triggers):
            try:
                # Dynamically import web_search.duckduckgo_search
                spec = importlib.util.spec_from_file_location(
                    "web_search", os.path.join(
                        os.path.dirname(__file__), "web_search.py"))
                web_search = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(web_search)
                answer = web_search.duckduckgo_search(text)
            except Exception as e:
                answer = f"Web search error: {e}"
            self.responder_socket.send_string(
                json.dumps({"text": answer, "emotion": "neutral"}))
            return answer
            
        # Detect language and emotion
        language = self.detect_language(text)
        text_emotion = self.detect_emotion(text)
        
        # Combine text and facial emotion for more accurate emotional context
        combined_emotion = text_emotion
        if self.current_speaker and self.current_speaker in self.detected_faces:
            face_emotion = self.detected_faces[self.current_speaker].get("emotion", "neutral")
            combined_emotion = f"text: {text_emotion}, face: {face_emotion}"
        
        # Build context from recent conversation
        context_str = ""
        
        # Get context using appropriate method
        if has_advanced_context:
            # Use advanced context manager with importance-based retrieval

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
            context_str = "Recent conversation:\n"
            context_str += self.context_manager.get_context_text(speaker=self.current_speaker, max_items=5)
        elif len(self.context_window) > 0:
            # Fallback to simple context window
            context_str = "Recent conversation:\n"
            for i, ctx in enumerate(list(self.context_window)[-5:]):
                speaker = ctx.get("speaker", "User")
                context_str += f"{speaker}: {ctx['text']}\n"
        
        # Add recent history for continuity
        history_context = "\n".join(
            [f"User: {h['user']}\nJarvis: {h['jarvis']}" for h in self.history[-3:]])
        
        # Build enhanced prompt with rich context
        prompt = (
            f"{self.persona}\n\n"
            f"Recent context:\n{chr(10).join(recent_context)}\n\n"
            f"Conversation history:\n{history_context}\n\n"
            f"Current user: {self.active_user}{face_context}\n"
            f"User said ({language}, {combined_emotion}): '{text}'\n"
            "What is the intent and action? Respond as Jarvis in a natural, conversational way. "
            "If the user wants to teach a new command, ask for the trigger phrase and action."
        )
        
        try:
            # Generate response using LLM
            inputs = self.tokenizer(
                prompt, return_tensors="pt").to(
                self.device)
            outputs = self.model.generate(**inputs, max_new_tokens=128)
            response = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
        except Exception as e:
            logging.error(f"LLM failed: {e}. Using fallback.")
            response = self.fallback_response(text, language, text_emotion)
        # After each interaction, save to Memory Agent
        try:
            self.memory_socket.send_string(json.dumps({
                "action": "add_memory",
                "user_id": self.active_user,
                "entry": {
                    "timestamp": time.time(),
                    "text": text,
                    "response": response,
                    "emotion": combined_emotion
                }
            }))
            _ = self.memory_socket.recv_string()
        except Exception as e:
            logging.error(f"[Interpreter] Failed to save memory to Memory Agent: {e}")
        logging.info(f"Raw LLM Response: {response}")
        
        # Command extraction
        command = self.extract_command(response)
        if command:
            self.send_command(command)
        else:
            # Check for teach command intent
            if "teach" in response.lower() and "command" in response.lower():
                self.handle_teach_command(text)
                
        # Send response to Responder Agent for TTS with enhanced metadata
        self.responder_socket.send_string(json.dumps({
            "text": response,
            "emotion": text_emotion,
            "language": language,
            "user": self.active_user,
            "face_emotion": self.detected_faces.get(self.active_user, {}).get("emotion", "neutral") if self.active_user in self.detected_faces else "unknown"
        }))

        # Save to history with enhanced metadata
        self.history.append({
            "user": text, 
            "jarvis": response,
            "timestamp": time.time(),
            "user_name": self.active_user,
            "emotion": text_emotion,
            "face_data": self.detected_faces.get(self.active_user, {})
        })
        self.save_history()
        return response

    def fallback_response(self, text, language, emotion):
        # Simple rule-based fallback
        if "notepad" in text.lower():
            return "Opening Notepad."
        if "calculator" in text.lower():
            return "Opening Calculator."
        if "shutdown" in text.lower():
            return "Shutting down the computer."
        return "Sorry, I couldn't process your request due to a technical issue."

    def handle_teach_command(self, text):
        # Expects 'teach command: trigger phrase = action'
        if ":" in text and "=" in text:
            try:
                trigger = text.split(":")[1].split("=")[0].strip()
                action = text.split("=")[1].strip()
                user = self.active_user
                self.user_profile["users"][user]["taught_commands"][action] = trigger
                self.save_user_profile()
                self.responder_socket.send_string(json.dumps(
                    {"text": f"Learned new command: '{trigger}' will trigger '{action}'."}))
                logging.info(
                    f"Learned new command for {user}: {trigger} -> {action}")
            except Exception as e:
                logging.error(f"Failed to teach command: {e}")

    def hot_reload_watcher(self):
        # Watch for changes in command map or persona
        last_cmd_map = self.command_map.copy()
        last_persona = self.persona
        while True:
            time.sleep(5)
            # Hot reload command map
            try:
                # Could load from file in future
                if self.command_map != last_cmd_map:
                    logging.info("Command map hot reloaded.")
                    last_cmd_map = self.command_map.copy()
                if self.persona != last_persona:
                    logging.info("Persona hot reloaded.")
                    last_persona = self.persona
            except Exception as e:
                logging.error(f"Hot reload watcher error: {e}")  # noqa: F541

    def health_check(self):
        # Simple health check
        now = time.time()
        if now - self.last_health_check > 60:
            self.last_health_check = now
            return {"status": self.health_status, "uptime": now}
        return {"status": self.health_status}

    def run(self):
        """Enhanced run method with improved message handling and periodic tasks"""
        logging.info("[Interpreter] Agent started. Waiting for transcriptions...")
        self.greet_user()
        
        # Set up periodic task tracking
        last_reminder_check = time.time()
        last_health_check = time.time()
        
        while True:
            try:
                # Non-blocking receive to allow for periodic tasks
                try:
                    msg = self.socket.recv_string(flags=zmq.NOBLOCK)
                    data = json.loads(msg)
                    text = data.get("text", "")
                    
                    if text:
                        # Get additional metadata if available
                        audio_emotion = data.get("audio_emotion", None)
                        confidence = data.get("confidence", 1.0)
                        
                        logging.info(f"[Interpreter] Received: {text}")
                        
                        # Check for user profile commands first
                        if self.check_user_profile_commands(text):
                            logging.info(f"[Interpreter] Profile updated for '{self.active_user}'.")
                            continue
                            
                        # Process text with enhanced context
                        speaker_data = {
                            "audio_emotion": audio_emotion,
                            "confidence": confidence,
                            "face_data": self.detected_faces.get(self.current_speaker, {})
                        }
                        
                        response = self.process_text(text, speaker_data)
                        logging.info(f"[Interpreter] LLM Response: {response}")
                except zmq.Again:
                    # No message available, continue with periodic tasks
                    pass
                
                # Periodic tasks
                current_time = time.time()
                
                # Check for due reminders every minute
                if current_time - last_reminder_check > 60:
                    self.check_reminders()
                    last_reminder_check = current_time
                
                # Health check every 5 minutes
                if current_time - last_health_check > 300:
                    status = self.health_check()
                    logging.info(f"[Interpreter] Health status: {status}")
                    last_health_check = current_time
                    
                # Small sleep to prevent CPU hogging
                time.sleep(0.05)
                
            except Exception as e:
                logging.error(f"[Interpreter] Error in main loop: {e}")
                traceback.print_exc()
                # Continue running despite errors
                time.sleep(1)
    
    def check_reminders(self):
        """Check for due reminders and send notifications"""
        current_time = time.time()
        user = self.active_user
        
        if user not in self.user_profile["users"]:
            return
            
        user_data = self.user_profile["users"][user]
        reminders = user_data.get("reminders", [])
        
        if not reminders:
            return
            
        now = time.strftime("%Y-%m-%dT%H:%M", time.localtime())
        due_reminders = []
        remaining_reminders = []
        
        for reminder in reminders:
            reminder_time = reminder["time"].split(":")[0] + ":" + reminder["time"].split(":")[1]
            if reminder_time <= now:
                due_reminders.append(reminder)
            else:
                remaining_reminders.append(reminder)
        
        # Update reminders list
        if due_reminders:
            self.user_profile["users"][user]["reminders"] = remaining_reminders
            self.save_user_profile()
            
            # Send notifications for due reminders
            for reminder in due_reminders:
                message = reminder["message"]
                notification = f"Reminder: {message}"
                
                # Send to responder for TTS
                self.responder_socket.send_string(json.dumps({
                    "text": notification,
                    "emotion": "neutral",
                    "is_reminder": True
                }))
                
                logging.info(f"[Interpreter] Sent reminder notification: {notification}")
                
                # Small delay between multiple reminders
                time.sleep(0.5)

    def set_active_user(self):
        """
        Prompts for user name if not set, or allows switching users.
        """
        print("[Jarvis] No active user detected. Please enter your name:")
        name = input("Enter your name: ").strip()
        if not name:
            name = "default"
        if "users" not in self.user_profile:
            self.user_profile["users"] = {}
        if name not in self.user_profile["users"]:
            self.user_profile["users"][name] = {
                "name": name,
                "preferences": {},
                "taught_commands": {},
                "interaction_history": [],
                "last_seen": None
            }
        self.user_profile["active_user"] = name
        self.save_user_profile()

    def greet_user(self):
        user = self.active_user
        profile = self.user_profile["users"].get(user, {})
        now = time.localtime()
        hour = now.tm_hour
        if hour < 12:
            tod = "morning"
        elif hour < 18:
            tod = "afternoon"
        else:
            tod = "evening"
        greeting = profile.get(
            "preferences",
            {}).get(
            "greeting",
            f"Good {tod}")
        name = profile.get("name", user)
        greet_text = f"{greeting}, {name}! Welcome back to Jarvis."
        print(f"[Jarvis] {greet_text}")
        # Send greeting to Responder for TTS
        self.responder_socket.send_string(json.dumps(
            {"text": greet_text, "emotion": "positive", "language": "English"}))
        # Update last_seen
        profile["last_seen"] = time.time()
        self.user_profile["users"][user] = profile
        self.save_user_profile()

    def check_user_profile_commands(self, text):
        """
        Checks for profile management commands (e.g., change name, update preferences).
        Returns True if a profile command was processed.
        """
        lowered = text.lower()
        user = self.active_user
        updated = False
        if "change my name to" in lowered:
            name = lowered.split("change my name to")[-1].strip().capitalize()
            if name:
                self.user_profile["users"][name] = self.user_profile["users"].pop(
                    user)
                self.user_profile["users"][name]["name"] = name
                self.user_profile["active_user"] = name
                self.active_user = name
                updated = True
        elif "set greeting to" in lowered:
            greeting = lowered.split(
                "set greeting to")[-1].strip().capitalize()
            self.user_profile["users"][user]["preferences"]["greeting"] = greeting
            updated = True
        elif "set voice to" in lowered:
            voice = lowered.split("set voice to")[-1].strip()
            self.user_profile["users"][user]["preferences"]["voice"] = voice
            updated = True
        elif "switch user to" in lowered:
            name = lowered.split("switch user to")[-1].strip().capitalize()
            if name in self.user_profile["users"]:
                self.user_profile["active_user"] = name
                self.active_user = name
                updated = True
            else:
                # Create new user profile
                self.user_profile["users"][name] = {
                    "name": name,
                    "preferences": {},
                    "taught_commands": {},
                    "interaction_history": [],
                    "last_seen": None
                }
                self.user_profile["active_user"] = name
                self.active_user = name
                updated = True
        if updated:
            self.save_user_profile()
            self.greet_user()
        return updated


if __name__ == "__main__":
    agent = InterpreterAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise