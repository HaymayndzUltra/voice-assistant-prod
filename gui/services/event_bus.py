from __future__ import annotations

"""Lightweight in-process event bus for GUI components.

Views/components can subscribe to named events.  Publishers simply call
`bus.publish("event_name", **payload)`.

Callbacks are executed in the Tkinter main thread by scheduling through the
provided `tk_root`'s `after` method ensuring thread safety.
"""
from collections import defaultdict
from typing import Callable, Dict, List, Any


class EventBus:
    """Very small pub-sub helper."""

    def __init__(self, tk_root):
        self._tk_root = tk_root
        self._subscribers: Dict[str, List[Callable[..., None]]] = defaultdict(list)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Register *callback* for *event_name*."""
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Remove callback."""
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, payload=None, **kwargs) -> None:
        """Fire event and schedule callbacks on main thread."""
        # Handle both dictionary and keyword arguments
        if payload is None:
            payload = kwargs
        elif isinstance(payload, dict):
            payload.update(kwargs)
        else:
            payload = kwargs
            
        for cb in list(self._subscribers.get(event_name, [])):
            # Ensure callbacks run in Tk thread
            if self._tk_root:
                try:
                    self._tk_root.after(0, lambda c=cb, p=payload: c(**p))
                except RuntimeError:
                    # Main loop not running, call directly
                    try:
                        cb(**payload)
                    except Exception as e:
                        print(f"Event callback error: {e}")
            else:
                # Fallback for when no Tk root is available
                try:
                    cb(**payload)
                except Exception as e:
                    print(f"Event callback error: {e}")