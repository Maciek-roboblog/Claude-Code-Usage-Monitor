"""Notification management utilities."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union


class NotificationManager:
    """Manages notification states and persistence."""

    def __init__(self, config_dir: Path) -> None:
        self.notification_file: Path = config_dir / "notification_states.json"
        self.states: Dict[str, Dict[str, Union[bool, Optional[datetime]]]] = (
            self._load_states()
        )

        self.default_states: Dict[str, Dict[str, Union[bool, Optional[datetime]]]] = {
            "switch_to_custom": {"triggered": False, "timestamp": None},
            "exceed_max_limit": {"triggered": False, "timestamp": None},
            "tokens_will_run_out": {"triggered": False, "timestamp": None},
        }

    def _load_states(self) -> Dict[str, Dict[str, Union[bool, Optional[datetime]]]]:
        """Load notification states from file."""
        if not self.notification_file.exists():
            return {
                "switch_to_custom": {"triggered": False, "timestamp": None},
                "exceed_max_limit": {"triggered": False, "timestamp": None},
                "tokens_will_run_out": {"triggered": False, "timestamp": None},
            }

        try:
            with open(self.notification_file) as f:
                states: Dict[str, Dict[str, Any]] = json.load(f)
                # Convert timestamp strings back to datetime objects
                parsed_states: Dict[
                    str, Dict[str, Union[bool, Optional[datetime]]]
                ] = {}
                for key, state in states.items():
                    parsed_state: Dict[str, Union[bool, Optional[datetime]]] = {
                        "triggered": bool(state.get("triggered", False)),
                        "timestamp": None,
                    }
                    if state.get("timestamp"):
                        parsed_state["timestamp"] = datetime.fromisoformat(
                            state["timestamp"]
                        )
                    parsed_states[key] = parsed_state
                return parsed_states
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            return self.default_states.copy()

    def _save_states(self) -> None:
        """Save notification states to file."""
        try:
            states_to_save: Dict[str, Dict[str, Union[bool, Optional[str]]]] = {}
            for key, state in self.states.items():
                timestamp_str: Optional[str] = None
                timestamp_value = state["timestamp"]
                if isinstance(timestamp_value, datetime):
                    timestamp_str = timestamp_value.isoformat()

                states_to_save[key] = {
                    "triggered": bool(state["triggered"]),
                    "timestamp": timestamp_str,
                }

            with open(self.notification_file, "w") as f:
                json.dump(states_to_save, f, indent=2)
        except (OSError, TypeError, ValueError) as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to save notification states to {self.notification_file}: {e}"
            )

    def should_notify(self, key: str, cooldown_hours: Union[int, float] = 24) -> bool:
        """Check if notification should be shown."""
        if key not in self.states:
            self.states[key] = {"triggered": False, "timestamp": None}
            return True

        state = self.states[key]
        if not state["triggered"]:
            return True

        timestamp_value = state["timestamp"]
        if timestamp_value is None:
            return True

        if not isinstance(timestamp_value, datetime):
            return True

        now: datetime = datetime.now()
        time_since_last: timedelta = now - timestamp_value
        cooldown_seconds: float = cooldown_hours * 3600
        return time_since_last.total_seconds() >= cooldown_seconds

    def mark_notified(self, key: str) -> None:
        """Mark notification as shown."""
        now: datetime = datetime.now()
        self.states[key] = {"triggered": True, "timestamp": now}
        self._save_states()

    def get_notification_state(
        self, key: str
    ) -> Dict[str, Union[bool, Optional[datetime]]]:
        """Get current notification state."""
        default_state: Dict[str, Union[bool, Optional[datetime]]] = {
            "triggered": False,
            "timestamp": None,
        }
        return self.states.get(key, default_state)

    def is_notification_active(self, key: str) -> bool:
        """Check if notification is currently active."""
        state = self.get_notification_state(key)
        triggered_value = state["triggered"]
        timestamp_value = state["timestamp"]
        return bool(triggered_value) and timestamp_value is not None
