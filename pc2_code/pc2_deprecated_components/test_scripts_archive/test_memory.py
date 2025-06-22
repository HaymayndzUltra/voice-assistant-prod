import threading
import time
import pytest
import importlib

# Import the memory agent (reload to pick up recent changes)
memory_module = importlib.import_module("agents.memory")
importlib.reload(memory_module)
MemoryAgent = memory_module.MemoryAgent

class DummyProactiveEventReceiver:
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
    def receive(self, event):
        with self.lock:
            self.events.append(event)
    def get_events(self):
        with self.lock:
            return list(self.events)

def test_reminder_broadcast_enabled(monkeypatch):
    """Test that reminders are broadcast proactively when enabled."""
    agent = MemoryAgent()
    # Patch send_proactive_event to capture broadcasts
    receiver = DummyProactiveEventReceiver()
    monkeypatch.setattr(memory_module, "send_proactive_event", lambda event_type, text, user=None, emotion="neutral": receiver.receive({"event_type": event_type, "text": text, "user": user, "emotion": emotion}))
    # Enable proactive broadcast
    memory_module.config["proactive_reminder_broadcast"] = True
    reminder = {"type": "reminder", "text": "Test reminder", "emotion": "neutral"}
    agent.handle_query({"action": "add_reminder", "user_id": "test_user", "reminder": reminder})
    time.sleep(0.1)  # Allow thread to process
    events = receiver.get_events()
    assert any(e["event_type"] == "reminder" and e["text"] == "Test reminder" for e in events)

def test_reminder_broadcast_disabled(monkeypatch):
    """Test that reminders are NOT broadcast when proactive flag is disabled."""
    agent = MemoryAgent()
    receiver = DummyProactiveEventReceiver()
    monkeypatch.setattr(memory_module, "send_proactive_event", lambda event_type, text, user=None, emotion="neutral": receiver.receive({"event_type": event_type, "text": text, "user": user, "emotion": emotion}))
    memory_module.config["proactive_reminder_broadcast"] = False
    reminder = {"type": "reminder", "text": "Should not broadcast", "emotion": "neutral"}
    agent.handle_query({"action": "add_reminder", "user_id": "test_user", "reminder": reminder})
    time.sleep(0.1)
    events = receiver.get_events()
    assert not any(e["event_type"] == "reminder" and e["text"] == "Should not broadcast" for e in events)

def test_no_duplicate_reminders(monkeypatch):
    """Test that duplicate reminders are not broadcast."""
    agent = MemoryAgent()
    receiver = DummyProactiveEventReceiver()
    monkeypatch.setattr(memory_module, "send_proactive_event", lambda event_type, text, user=None, emotion="neutral": receiver.receive({"event_type": event_type, "text": text, "user": user, "emotion": emotion}))
    memory_module.config["proactive_reminder_broadcast"] = True
    reminder = {"type": "reminder", "text": "No duplicates", "emotion": "neutral"}
    # Add the same reminder twice
    agent.handle_query({"action": "add_reminder", "user_id": "test_user", "reminder": reminder})
    agent.handle_query({"action": "add_reminder", "user_id": "test_user", "reminder": reminder})
    time.sleep(0.2)
    events = receiver.get_events()
    # Should only broadcast once if deduplication is implemented
    assert sum(e["event_type"] == "reminder" and e["text"] == "No duplicates" for e in events) <= 1

def test_thread_safety_reminder(monkeypatch):
    """Test that concurrent reminder additions are thread-safe and no duplicate broadcasts occur."""
    agent = MemoryAgent()
    receiver = DummyProactiveEventReceiver()
    monkeypatch.setattr(memory_module, "send_proactive_event", lambda event_type, text, user=None, emotion="neutral": receiver.receive({"event_type": event_type, "text": text, "user": user, "emotion": emotion}))
    memory_module.config["proactive_reminder_broadcast"] = True
    reminder = {"type": "reminder", "text": "Threaded reminder", "emotion": "neutral"}
    def add_reminder():
        agent.handle_query({"action": "add_reminder", "user_id": "thread_user", "reminder": reminder})
    threads = [threading.Thread(target=add_reminder) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    time.sleep(0.2)
    events = receiver.get_events()
    # Only one broadcast should occur
    assert sum(e["event_type"] == "reminder" and e["text"] == "Threaded reminder" for e in events) <= 1
