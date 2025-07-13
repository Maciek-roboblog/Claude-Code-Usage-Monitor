"""Notification management utilities."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class NotificationManager:
    """Manages notification states and persistence."""

    def __init__(self, config_dir: Path):
        """
        Initialize the NotificationManager with a configuration directory.
        
        Sets up the path for the notification states file, loads existing notification states, and defines default states for known notification keys.
        """
        self.notification_file = config_dir / "notification_states.json"
        self.states = self._load_states()

        self.default_states = {
            "switch_to_custom": {"triggered": False, "timestamp": None},
            "exceed_max_limit": {"triggered": False, "timestamp": None},
            "tokens_will_run_out": {"triggered": False, "timestamp": None},
        }

    def _load_states(self) -> Dict[str, Dict]:
        """
        Load notification states from the JSON file, converting timestamps to datetime objects.
        
        Returns:
            A dictionary mapping notification keys to their state dictionaries. If the file does not exist or cannot be parsed, returns a copy of the default notification states.
        """
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
        """
        Persist the current notification states to the JSON file, converting datetime timestamps to ISO-format strings. Logs a warning if saving fails due to file or serialization errors.
        """
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
        """
        Determine whether a notification for the given key should be shown, based on its triggered state and cooldown period.
        
        Parameters:
            key (str): The identifier for the notification.
            cooldown_hours (int): The minimum number of hours to wait before showing the notification again if it was previously triggered. Defaults to 24.
        
        Returns:
            bool: True if the notification should be shown, False otherwise.
        """
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
        """
        Marks the specified notification as triggered and updates its timestamp to the current time, persisting the change to storage.
        """
        self.states[key] = {"triggered": True, "timestamp": datetime.now()}
        self._save_states()

    def get_notification_state(self, key: str) -> Dict:
        """
        Retrieve the current state of a notification by its key.
        
        Returns:
            dict: The state dictionary for the specified notification key, containing 'triggered' (bool) and 'timestamp' (datetime or None). If the key does not exist, returns a default state with 'triggered' set to False and 'timestamp' as None.
        """
        return self.states.get(key, {"triggered": False, "timestamp": None})

    def is_notification_active(self, key: str) -> bool:
        """
        Return whether the specified notification is currently active.
        
        A notification is considered active if it has been triggered and has a valid timestamp.
        
        Parameters:
            key (str): The notification key to check.
        
        Returns:
            bool: True if the notification is active, False otherwise.
        """
        state = self.get_notification_state(key)
        return state["triggered"] and state["timestamp"] is not None
