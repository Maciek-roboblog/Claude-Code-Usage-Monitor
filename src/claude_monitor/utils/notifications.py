"""Notification management utilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class NotificationManager:
    """Manages notification states and persistence."""

    def __init__(self, config_dir: Path):
        self.notification_file = config_dir / "notification_states.json"
        self.states = self._load_states()

        self.default_states = {
            "switch_to_custom": {"triggered": False, "timestamp": None},
            "exceed_max_limit": {"triggered": False, "timestamp": None},
            "tokens_will_run_out": {"triggered": False, "timestamp": None},
        }

    def _load_states(self) -> Dict[str, Dict]:
        """Load notification states from file."""
        if not self.notification_file.exists():
            return {
                "switch_to_custom": {"triggered": False, "timestamp": None},
                "exceed_max_limit": {"triggered": False, "timestamp": None},
                "tokens_will_run_out": {"triggered": False, "timestamp": None},
            }

        try:
            with open(self.notification_file) as f:
                states = json.load(f)
                for state in states.values():
                    if state.get("timestamp"):
                        state["timestamp"] = datetime.fromisoformat(state["timestamp"])
                return states
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            return self.default_states.copy()

    def _save_states(self):
        """Save notification states to file."""
        try:
            states_to_save = {}
            for key, state in self.states.items():
                states_to_save[key] = {
                    "triggered": state["triggered"],
                    "timestamp": (
                        state["timestamp"].isoformat() if state["timestamp"] else None
                    ),
                }

            with open(self.notification_file, "w") as f:
                json.dump(states_to_save, f, indent=2)
        except (OSError, TypeError, ValueError) as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to save notification states to {self.notification_file}: {e}"
            )

    def should_notify(self, key: str, cooldown_hours: int = 24) -> bool:
        """Check if notification should be shown."""
        if key not in self.states:
            self.states[key] = {"triggered": False, "timestamp": None}
            return True

        state = self.states[key]
        if not state["triggered"]:
            return True

        if state["timestamp"] is None:
            return True

        now = datetime.now()
        time_since_last = now - state["timestamp"]
        return time_since_last.total_seconds() >= (cooldown_hours * 3600)

    def mark_notified(self, key: str):
        """Mark notification as shown."""
        self.states[key] = {"triggered": True, "timestamp": datetime.now()}
        self._save_states()

    def get_notification_state(self, key: str) -> Dict:
        """Get current notification state."""
        return self.states.get(key, {"triggered": False, "timestamp": None})

    def is_notification_active(self, key: str) -> bool:
        """Check if notification is currently active."""
        state = self.get_notification_state(key)
        return state["triggered"] and state["timestamp"] is not None
