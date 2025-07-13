"""Advanced notification management utilities with cross-platform support."""

import asyncio
import json
import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    TypedDict,
)
from weakref import WeakSet


class NotificationPriority(Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels."""

    SYSTEM = "system"  # OS-level notifications
    TERMINAL = "terminal"  # Terminal/console notifications
    LOG = "log"  # Log file notifications
    EMAIL = "email"  # Email notifications (future)
    WEBHOOK = "webhook"  # Webhook notifications (future)


class NotificationState(TypedDict, total=False):
    """Type-safe notification state structure."""

    triggered: bool
    timestamp: Optional[datetime]
    priority: NotificationPriority
    channels: List[NotificationChannel]
    count: int
    cooldown_hours: int


class NotificationEvent(TypedDict):
    """Type-safe notification event structure."""

    key: str
    title: str
    message: str
    priority: NotificationPriority
    channels: List[NotificationChannel]
    metadata: Dict[str, Any]


class UserPreferences(TypedDict, total=False):
    """Type-safe user notification preferences."""

    enabled_channels: Set[NotificationChannel]
    priority_threshold: NotificationPriority
    default_cooldown_hours: int
    system_notifications_enabled: bool
    quiet_hours_start: Optional[int]  # Hour (0-23)
    quiet_hours_end: Optional[int]  # Hour (0-23)
    max_notifications_per_hour: int


class NotificationHandler(Protocol):
    """Protocol for notification delivery handlers."""

    async def send_notification(self, event: NotificationEvent) -> bool:
        """Send a notification event.

        Returns:
            True if notification was sent successfully, False otherwise.
        """
        ...

    def supports_channel(self, channel: NotificationChannel) -> bool:
        """Check if handler supports the given channel."""
        ...


class NotificationBackend(ABC):
    """Abstract base for cross-platform notification backends."""

    @abstractmethod
    async def send_system_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """Send a system-level notification."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available on the current system."""
        pass


class LinuxNotificationBackend(NotificationBackend):
    """Linux notification backend using notify-send."""

    async def send_system_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """Send notification via notify-send."""
        if not self.is_available():
            return False

        urgency_map = {
            NotificationPriority.LOW: "low",
            NotificationPriority.NORMAL: "normal",
            NotificationPriority.HIGH: "normal",
            NotificationPriority.CRITICAL: "critical",
        }

        try:
            process = await asyncio.create_subprocess_exec(
                "notify-send",
                "--urgency",
                urgency_map[priority],
                "--app-name",
                "Claude Monitor",
                title,
                message,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()
            return process.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def is_available(self) -> bool:
        """Check if notify-send is available."""
        try:
            subprocess.run(["which", "notify-send"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


class MacOSNotificationBackend(NotificationBackend):
    """macOS notification backend using osascript."""

    async def send_system_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """Send notification via AppleScript."""
        if not self.is_available():
            return False

        script = f'''
        display notification "{message}" with title "{title}" sound name "default"
        '''

        try:
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()
            return process.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def is_available(self) -> bool:
        """Check if osascript is available."""
        return platform.system() == "Darwin"


class WindowsNotificationBackend(NotificationBackend):
    """Windows notification backend using PowerShell."""

    async def send_system_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> bool:
        """Send notification via PowerShell."""
        if not self.is_available():
            return False

        # Use Windows 10+ toast notifications
        script = f'''
        Add-Type -AssemblyName System.Windows.Forms
        $global:balloon = New-Object System.Windows.Forms.NotifyIcon
        $path = (Get-Process -id $pid).Path
        $balloon.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon($path)
        $balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
        $balloon.BalloonTipText = "{message}"
        $balloon.BalloonTipTitle = "{title}"
        $balloon.Visible = $true
        $balloon.ShowBalloonTip(5000)
        '''

        try:
            process = await asyncio.create_subprocess_exec(
                "powershell",
                "-Command",
                script,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.wait()
            return process.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def is_available(self) -> bool:
        """Check if PowerShell is available."""
        return platform.system() == "Windows"


@dataclass
class NotificationQueueItem:
    """Represents an item in the notification priority queue."""

    event: NotificationEvent
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3

    def __lt__(self, other: "NotificationQueueItem") -> bool:
        """Compare for priority queue ordering."""
        priority_order = {
            NotificationPriority.CRITICAL: 0,
            NotificationPriority.HIGH: 1,
            NotificationPriority.NORMAL: 2,
            NotificationPriority.LOW: 3,
        }
        return (
            priority_order[self.event["priority"]]
            < priority_order[other.event["priority"]]
        )


class AsyncNotificationHandler:
    """Async notification handler with queue management."""

    def __init__(self) -> None:
        self.backends: List[NotificationBackend] = self._initialize_backends()
        self.queue: asyncio.PriorityQueue[NotificationQueueItem] = (
            asyncio.PriorityQueue()
        )
        self.processing = False
        self.event_listeners: WeakSet[Callable[[NotificationEvent], None]] = WeakSet()

    def _initialize_backends(self) -> List[NotificationBackend]:
        """Initialize available notification backends."""
        backends = [
            LinuxNotificationBackend(),
            MacOSNotificationBackend(),
            WindowsNotificationBackend(),
        ]
        return [backend for backend in backends if backend.is_available()]

    async def queue_notification(self, event: NotificationEvent) -> None:
        """Add notification to priority queue."""
        item = NotificationQueueItem(event)
        await self.queue.put(item)

        # Notify event listeners
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception:
                pass  # Don't let listener errors break notification flow

    async def process_queue(self) -> None:
        """Process notifications from the priority queue."""
        if self.processing:
            return

        self.processing = True
        try:
            while True:
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    await self._process_notification_item(item)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    break
        finally:
            self.processing = False

    async def _process_notification_item(self, item: NotificationQueueItem) -> None:
        """Process a single notification item."""
        event = item.event

        # Try to send via available backends
        for backend in self.backends:
            if NotificationChannel.SYSTEM in event["channels"]:
                try:
                    success = await backend.send_system_notification(
                        event["title"], event["message"], event["priority"]
                    )
                    if success:
                        return
                except Exception:
                    continue

        # If all backends failed and we have retries left
        if item.retry_count < item.max_retries:
            item.retry_count += 1
            await asyncio.sleep(2**item.retry_count)  # Exponential backoff
            await self.queue.put(item)

    def add_event_listener(self, listener: Callable[[NotificationEvent], None]) -> None:
        """Add an event listener for notification events."""
        self.event_listeners.add(listener)


class NotificationManager:
    """Advanced notification manager with cross-platform support and event handling."""

    def __init__(self, config_dir: Path, preferences: Optional[UserPreferences] = None):
        self.config_dir = config_dir
        self.notification_file = config_dir / "notification_states.json"
        self.preferences_file = config_dir / "notification_preferences.json"

        # Default notification configurations (must be set before _load_states)
        self.default_states: Dict[str, NotificationState] = {
            "switch_to_custom": {
                "triggered": False,
                "timestamp": None,
                "priority": NotificationPriority.NORMAL,
                "channels": [NotificationChannel.SYSTEM, NotificationChannel.TERMINAL],
                "count": 0,
                "cooldown_hours": 24,
            },
            "exceed_max_limit": {
                "triggered": False,
                "timestamp": None,
                "priority": NotificationPriority.HIGH,
                "channels": [NotificationChannel.SYSTEM, NotificationChannel.TERMINAL],
                "count": 0,
                "cooldown_hours": 6,
            },
            "tokens_will_run_out": {
                "triggered": False,
                "timestamp": None,
                "priority": NotificationPriority.CRITICAL,
                "channels": [
                    NotificationChannel.SYSTEM,
                    NotificationChannel.TERMINAL,
                    NotificationChannel.LOG,
                ],
                "count": 0,
                "cooldown_hours": 1,
            },
        }

        # Load states and preferences (after default_states is defined)
        self.states: Dict[str, NotificationState] = self._load_states()
        self.preferences = preferences or self._load_preferences()

        # Initialize async handler
        self.async_handler = AsyncNotificationHandler()

        # Rate limiting tracking
        self.notification_history: List[datetime] = []

    def _load_preferences(self) -> UserPreferences:
        """Load user notification preferences."""
        default_preferences: UserPreferences = {
            "enabled_channels": {
                NotificationChannel.SYSTEM,
                NotificationChannel.TERMINAL,
            },
            "priority_threshold": NotificationPriority.NORMAL,
            "default_cooldown_hours": 24,
            "system_notifications_enabled": True,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "max_notifications_per_hour": 10,
        }

        if not self.preferences_file.exists():
            self._save_preferences(default_preferences)
            return default_preferences

        try:
            with open(self.preferences_file) as f:
                data = json.load(f)
                # Convert channel strings back to enums
                if "enabled_channels" in data:
                    data["enabled_channels"] = {
                        NotificationChannel(ch) for ch in data["enabled_channels"]
                    }
                if "priority_threshold" in data:
                    data["priority_threshold"] = NotificationPriority(
                        data["priority_threshold"]
                    )
                # Merge with proper typing
                result: UserPreferences = {**default_preferences}
                result.update(data)
                return result
        except (json.JSONDecodeError, FileNotFoundError, ValueError, TypeError):
            return default_preferences

    def _save_preferences(self, preferences: UserPreferences) -> None:
        """Save user notification preferences."""
        try:
            data = dict(preferences)
            # Convert enums to strings for JSON serialization
            if "enabled_channels" in data and data["enabled_channels"] is not None:
                channels = data["enabled_channels"]
                if isinstance(channels, set):
                    data["enabled_channels"] = [ch.value for ch in channels]
            if "priority_threshold" in data and data["priority_threshold"] is not None:
                threshold = data["priority_threshold"]
                if hasattr(threshold, "value"):
                    data["priority_threshold"] = threshold.value

            with open(self.preferences_file, "w") as f:
                json.dump(data, f, indent=2)
        except (OSError, TypeError) as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to save notification preferences: {e}"
            )

    def _load_states(self) -> Dict[str, NotificationState]:
        """Load notification states from file."""
        if not self.notification_file.exists():
            return self.default_states.copy()

        try:
            with open(self.notification_file) as f:
                data = json.load(f)
                states: Dict[str, NotificationState] = {}

                for key, state_data in data.items():
                    state: NotificationState = {
                        "triggered": state_data.get("triggered", False),
                        "timestamp": (
                            datetime.fromisoformat(state_data["timestamp"])
                            if state_data.get("timestamp")
                            else None
                        ),
                        "priority": NotificationPriority(
                            state_data.get("priority", "normal")
                        ),
                        "channels": [
                            NotificationChannel(ch)
                            for ch in state_data.get("channels", ["system", "terminal"])
                        ],
                        "count": state_data.get("count", 0),
                        "cooldown_hours": state_data.get("cooldown_hours", 24),
                    }
                    states[key] = state

                return states
        except (
            json.JSONDecodeError,
            FileNotFoundError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return self.default_states.copy()

    def _save_states(self) -> None:
        """Save notification states to file."""
        try:
            states_to_save = {}
            for key, state in self.states.items():
                states_to_save[key] = {
                    "triggered": state["triggered"],
                    "timestamp": (
                        state["timestamp"].isoformat() if state["timestamp"] else None
                    ),
                    "priority": state["priority"].value,
                    "channels": [ch.value for ch in state["channels"]],
                    "count": state["count"],
                    "cooldown_hours": state["cooldown_hours"],
                }

            with open(self.notification_file, "w") as f:
                json.dump(states_to_save, f, indent=2)
        except (OSError, TypeError, ValueError) as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to save notification states to {self.notification_file}: {e}"
            )

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within user-defined quiet hours."""
        start = self.preferences.get("quiet_hours_start")
        end = self.preferences.get("quiet_hours_end")

        if start is None or end is None:
            return False

        current_hour = datetime.now().hour

        if start <= end:
            return start <= current_hour < end
        else:  # Quiet hours span midnight
            return current_hour >= start or current_hour < end

    def _check_rate_limit(self) -> bool:
        """Check if we're within the hourly notification rate limit."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)

        # Clean old entries
        self.notification_history = [
            timestamp for timestamp in self.notification_history if timestamp > hour_ago
        ]

        max_per_hour = self.preferences.get("max_notifications_per_hour", 10)
        return len(self.notification_history) < max_per_hour

    def should_notify(
        self,
        key: str,
        priority: Optional[NotificationPriority] = None,
        cooldown_hours: Optional[int] = None,
    ) -> bool:
        """Check if notification should be shown with advanced filtering."""
        # Initialize state if not exists
        if key not in self.states:
            default_state = self.default_states.get(
                key,
                {
                    "triggered": False,
                    "timestamp": None,
                    "priority": NotificationPriority.NORMAL,
                    "channels": [NotificationChannel.SYSTEM],
                    "count": 0,
                    "cooldown_hours": 24,
                },
            )
            self.states[key] = default_state

        state = self.states[key]
        effective_priority = priority or state["priority"]
        effective_cooldown = cooldown_hours or state["cooldown_hours"]

        # Check priority threshold
        priority_values = {
            NotificationPriority.LOW: 0,
            NotificationPriority.NORMAL: 1,
            NotificationPriority.HIGH: 2,
            NotificationPriority.CRITICAL: 3,
        }

        threshold = self.preferences.get(
            "priority_threshold", NotificationPriority.NORMAL
        )
        if priority_values[effective_priority] < priority_values[threshold]:
            return False

        # Check quiet hours (except for critical notifications)
        if (
            effective_priority != NotificationPriority.CRITICAL
            and self._is_quiet_hours()
        ):
            return False

        # Check rate limiting
        if not self._check_rate_limit():
            return False

        # Check cooldown
        if not state["triggered"]:
            return True

        if state["timestamp"] is None:
            return True

        now = datetime.now()
        time_since_last = now - state["timestamp"]
        return bool(time_since_last.total_seconds() >= (effective_cooldown * 3600))

    def mark_notified(
        self, key: str, priority: Optional[NotificationPriority] = None
    ) -> None:
        """Mark notification as shown with enhanced tracking."""
        now = datetime.now()

        if key not in self.states:
            self.states[key] = self.default_states.get(
                key,
                {
                    "triggered": False,
                    "timestamp": None,
                    "priority": NotificationPriority.NORMAL,
                    "channels": [NotificationChannel.SYSTEM],
                    "count": 0,
                    "cooldown_hours": 24,
                },
            )

        state = self.states[key]
        state["triggered"] = True
        state["timestamp"] = now
        state["count"] = state.get("count", 0) + 1

        if priority:
            state["priority"] = priority

        # Track for rate limiting
        self.notification_history.append(now)

        self._save_states()

    def get_notification_state(self, key: str) -> NotificationState:
        """Get current notification state with type safety."""
        default_state: NotificationState = {
            "triggered": False,
            "timestamp": None,
            "priority": NotificationPriority.NORMAL,
            "channels": [NotificationChannel.SYSTEM],
            "count": 0,
            "cooldown_hours": 24,
        }
        return self.states.get(key, default_state)

    def is_notification_active(self, key: str) -> bool:
        """Check if notification is currently active."""
        state = self.get_notification_state(key)
        return state["triggered"] and state["timestamp"] is not None

    async def send_notification(
        self,
        key: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification through the async handler."""
        if not self.should_notify(key, priority):
            return False

        effective_channels = channels or self.states.get(key, {}).get(
            "channels", [NotificationChannel.SYSTEM, NotificationChannel.TERMINAL]
        )

        # Filter channels based on user preferences
        enabled_channels = self.preferences.get(
            "enabled_channels",
            {NotificationChannel.SYSTEM, NotificationChannel.TERMINAL},
        )
        effective_channels = [ch for ch in effective_channels if ch in enabled_channels]

        if not effective_channels:
            return False

        event: NotificationEvent = {
            "key": key,
            "title": title,
            "message": message,
            "priority": priority,
            "channels": effective_channels,
            "metadata": metadata or {},
        }

        await self.async_handler.queue_notification(event)
        self.mark_notified(key, priority)
        return True

    async def process_notification_queue(self) -> None:
        """Process pending notifications in the queue."""
        await self.async_handler.process_queue()

    def update_preferences(self, preferences: UserPreferences) -> None:
        """Update user notification preferences."""
        self.preferences.update(preferences)
        self._save_preferences(self.preferences)

    def get_preferences(self) -> UserPreferences:
        """Get current user preferences."""
        return self.preferences.copy()

    def add_event_listener(self, listener: Callable[[NotificationEvent], None]) -> None:
        """Add an event listener for notification events."""
        self.async_handler.add_event_listener(listener)

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics and analytics."""
        total_notifications = sum(
            state.get("count", 0) for state in self.states.values()
        )
        active_notifications = sum(
            1
            for state in self.states.values()
            if state["triggered"] and state["timestamp"]
        )

        return {
            "total_sent": total_notifications,
            "active_notifications": active_notifications,
            "configured_keys": list(self.states.keys()),
            "recent_notifications_count": len(self.notification_history),
            "rate_limit_status": {
                "current_count": len(self.notification_history),
                "max_per_hour": self.preferences.get("max_notifications_per_hour", 10),
                "can_send_more": self._check_rate_limit(),
            },
            "quiet_hours_active": self._is_quiet_hours(),
        }
