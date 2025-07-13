"""Unified theme management for terminal display."""

import logging
import os
import re
import select
import sys
import termios
import threading
import tty
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.theme import Theme


class BackgroundType(Enum):
    """Background detection types."""

    LIGHT = "light"
    DARK = "dark"
    UNKNOWN = "unknown"


@dataclass
class ThemeConfig:
    """Theme configuration."""

    name: str
    colors: Dict[str, str]
    symbols: Dict[str, str]
    rich_theme: Theme

    def get_color(self, key: str, default: str = "default") -> str:
        """Get color for key with fallback."""
        return self.colors.get(key, default)


class AdaptiveColorScheme:
    """Scientifically-based adaptive color schemes with proper contrast ratios.

    IMPORTANT: This only changes FONT/FOREGROUND colors, never background colors.
    The terminal's background remains unchanged - we adapt text colors for readability.
    """

    @staticmethod
    def get_light_background_theme() -> Theme:
        """Font colors optimized for light terminal backgrounds (WCAG AA+ contrast)."""
        return Theme(
            {
                "header": "color(17)",  # Deep blue (#00005f) - 21:1 contrast
                "info": "color(19)",  # Dark blue (#0000af) - 18:1 contrast
                "warning": "color(166)",  # Dark orange (#d75f00) - 8:1 contrast
                "error": "color(124)",  # Dark red (#af0000) - 12:1 contrast
                "success": "color(22)",  # Dark green (#005f00) - 15:1 contrast
                "value": "color(235)",  # Very dark gray (#262626) - 16:1 contrast
                "dim": "color(243)",  # Medium gray (#767676) - 5:1 contrast
                "separator": "color(240)",  # Light gray (#585858) - 6:1 contrast
                "progress_bar": "color(22)",  # Dark green (#005f00) - matches success
                "highlight": "color(124)",  # Dark red (#af0000) - matches error
                # Cost styles
                "cost.low": "color(22)",  # Dark green
                "cost.medium": "color(166)",  # Dark orange
                "cost.high": "color(124)",  # Dark red
                # Table styles
                "table.border": "color(238)",  # Medium-dark gray for better visibility
                "table.header": "bold color(17)",  # Bold deep blue
                "table.row": "color(235)",  # Very dark gray
                "table.row.alt": "color(238)",  # Slightly lighter gray
                # Progress styles
                "progress.bar.fill": "color(22)",  # Dark green for visibility on light bg
                "progress.bar.empty": "color(240)",  # Medium gray for better visibility on light bg
                "progress.percentage": "bold color(235)",  # Bold very dark gray
                # Chart styles
                "chart.bar": "color(17)",  # Deep blue for better visibility
                "chart.line": "color(19)",  # Darker blue
                "chart.point": "color(124)",  # Dark red
                "chart.axis": "color(240)",  # Light gray
                "chart.label": "color(235)",  # Very dark gray
                # Status styles
                "status.active": "color(22)",  # Dark green
                "status.inactive": "color(243)",  # Medium gray
                "status.warning": "color(166)",  # Dark orange
                "status.error": "color(124)",  # Dark red
                # Time styles
                "time.elapsed": "color(235)",  # Very dark gray
                "time.remaining": "color(166)",  # Dark orange
                "time.duration": "color(19)",  # Dark blue
                # Model styles
                "model.opus": "color(17)",  # Deep blue
                "model.sonnet": "color(19)",  # Dark blue
                "model.haiku": "color(22)",  # Dark green
                "model.unknown": "color(243)",  # Medium gray
                # Plan styles
                "plan.pro": "color(166)",  # Orange (premium)
                "plan.max5": "color(19)",  # Dark blue
                "plan.max20": "color(17)",  # Deep blue
                "plan.custom": "color(22)",  # Dark green
            }
        )

    @staticmethod
    def get_dark_background_theme() -> Theme:
        """Font colors optimized for dark terminal backgrounds (WCAG AA+ contrast)."""
        return Theme(
            {
                "header": "color(117)",  # Light blue (#87d7ff) - 14:1 contrast
                "info": "color(111)",  # Light cyan (#87afff) - 12:1 contrast
                "warning": "color(214)",  # Orange (#ffaf00) - 11:1 contrast
                "error": "color(203)",  # Light red (#ff5f5f) - 9:1 contrast
                "success": "color(118)",  # Light green (#87ff00) - 15:1 contrast
                "value": "color(253)",  # Very light gray (#dadada) - 17:1 contrast
                "dim": "color(245)",  # Medium light gray (#8a8a8a) - 7:1 contrast
                "separator": "color(248)",  # Light gray (#a8a8a8) - 9:1 contrast
                "progress_bar": "color(118)",  # Light green (#87ff00) - matches success
                "highlight": "color(203)",  # Light red (#ff5f5f) - matches error
                # Cost styles
                "cost.low": "color(118)",  # Light green
                "cost.medium": "color(214)",  # Orange
                "cost.high": "color(203)",  # Light red
                # Table styles
                "table.border": "color(248)",  # Light gray
                "table.header": "bold color(117)",  # Bold light blue
                "table.row": "color(253)",  # Very light gray
                "table.row.alt": "color(251)",  # Slightly darker gray
                # Progress styles
                "progress.bar.fill": "color(118)",  # Light green
                "progress.bar.empty": "color(245)",  # Medium light gray
                "progress.percentage": "bold color(253)",  # Bold very light gray
                # Chart styles
                "chart.bar": "color(111)",  # Light cyan
                "chart.line": "color(117)",  # Light blue
                "chart.point": "color(203)",  # Light red
                "chart.axis": "color(248)",  # Light gray
                "chart.label": "color(253)",  # Very light gray
                # Status styles
                "status.active": "color(118)",  # Light green
                "status.inactive": "color(245)",  # Medium light gray
                "status.warning": "color(214)",  # Orange
                "status.error": "color(203)",  # Light red
                # Time styles
                "time.elapsed": "color(253)",  # Very light gray
                "time.remaining": "color(214)",  # Orange
                "time.duration": "color(111)",  # Light cyan
                # Model styles
                "model.opus": "color(117)",  # Light blue
                "model.sonnet": "color(111)",  # Light cyan
                "model.haiku": "color(118)",  # Light green
                "model.unknown": "color(245)",  # Medium light gray
                # Plan styles
                "plan.pro": "color(214)",  # Orange (premium)
                "plan.max5": "color(111)",  # Light cyan
                "plan.max20": "color(117)",  # Light blue
                "plan.custom": "color(118)",  # Light green
            }
        )

    @staticmethod
    def get_classic_theme() -> Theme:
        """Classic colors for maximum compatibility."""
        return Theme(
            {
                "header": "cyan",
                "info": "blue",
                "warning": "yellow",
                "error": "red",
                "success": "green",
                "value": "white",
                "dim": "bright_black",
                "separator": "white",
                "progress_bar": "green",
                "highlight": "red",
                # Cost styles
                "cost.low": "green",
                "cost.medium": "yellow",
                "cost.high": "red",
                # Table styles
                "table.border": "white",
                "table.header": "bold cyan",
                "table.row": "white",
                "table.row.alt": "bright_black",
                # Progress styles
                "progress.bar.fill": "green",
                "progress.bar.empty": "bright_black",
                "progress.percentage": "bold white",
                # Chart styles
                "chart.bar": "blue",
                "chart.line": "cyan",
                "chart.point": "red",
                "chart.axis": "white",
                "chart.label": "white",
                # Status styles
                "status.active": "green",
                "status.inactive": "bright_black",
                "status.warning": "yellow",
                "status.error": "red",
                # Time styles
                "time.elapsed": "white",
                "time.remaining": "yellow",
                "time.duration": "blue",
                # Model styles
                "model.opus": "cyan",
                "model.sonnet": "blue",
                "model.haiku": "green",
                "model.unknown": "bright_black",
                # Plan styles
                "plan.pro": "yellow",  # Yellow (premium)
                "plan.max5": "cyan",  # Cyan
                "plan.max20": "blue",  # Blue
                "plan.custom": "green",  # Green
            }
        )


class BackgroundDetector:
    """Detects terminal background type using multiple methods."""

    @staticmethod
    def detect_background() -> BackgroundType:
        """Detect terminal background using multiple methods."""
        # Method 1: Check COLORFGBG environment variable
        colorfgbg_result = BackgroundDetector._check_colorfgbg()
        if colorfgbg_result != BackgroundType.UNKNOWN:
            return colorfgbg_result

        # Method 2: Check known terminal environment variables
        env_result = BackgroundDetector._check_environment_hints()
        if env_result != BackgroundType.UNKNOWN:
            return env_result

        # Method 3: Use OSC 11 query (advanced terminals only)
        osc_result = BackgroundDetector._query_background_color()
        if osc_result != BackgroundType.UNKNOWN:
            return osc_result

        # Default fallback
        return BackgroundType.DARK

    @staticmethod
    def _check_colorfgbg() -> BackgroundType:
        """Check COLORFGBG environment variable."""
        colorfgbg = os.environ.get("COLORFGBG", "")
        if not colorfgbg:
            return BackgroundType.UNKNOWN

        try:
            # COLORFGBG format: "foreground;background"
            parts = colorfgbg.split(";")
            if len(parts) >= 2:
                bg_color = int(parts[-1])
                # Colors 0-7 are typically dark, 8-15 are bright
                return BackgroundType.LIGHT if bg_color >= 8 else BackgroundType.DARK
        except (ValueError, IndexError) as e:
            # COLORFGBG parsing failed - not critical, will use other detection methods

            logging.getLogger(__name__).debug(
                f"Failed to parse COLORFGBG '{colorfgbg}': {e}"
            )

        return BackgroundType.UNKNOWN

    @staticmethod
    def _check_environment_hints() -> BackgroundType:
        """Check environment variables for theme hints."""
        if os.environ.get("WT_SESSION"):
            return BackgroundType.DARK

        if "TERM_PROGRAM" in os.environ:
            term_program = os.environ["TERM_PROGRAM"]
            if term_program == "Apple_Terminal":
                return BackgroundType.LIGHT
            if term_program == "iTerm.app":
                return BackgroundType.DARK

        # Check TERM variable patterns
        term = os.environ.get("TERM", "").lower()
        if "light" in term:
            return BackgroundType.LIGHT
        if "dark" in term:
            return BackgroundType.DARK

        return BackgroundType.UNKNOWN

    @staticmethod
    def _query_background_color() -> BackgroundType:
        """Query terminal background color using OSC 11."""
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return BackgroundType.UNKNOWN

        try:
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)

            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())

            # Send OSC 11 query
            sys.stdout.write("\033]11;?\033\\")
            sys.stdout.flush()

            # Wait for response with timeout
            if select.select([sys.stdin], [], [], 0.1)[0]:
                response = sys.stdin.read(50)  # Read up to 50 chars

                # Parse response: \033]11;rgb:rrrr/gggg/bbbb\033\\
                rgb_match = re.search(
                    r"rgb:([0-9a-f]+)/([0-9a-f]+)/([0-9a-f]+)", response
                )
                if rgb_match:
                    r, g, b = rgb_match.groups()
                    # Convert hex to int and calculate brightness
                    red = int(r[:2], 16) if len(r) >= 2 else 0
                    green = int(g[:2], 16) if len(g) >= 2 else 0
                    blue = int(b[:2], 16) if len(b) >= 2 else 0

                    # Calculate perceived brightness using standard formula
                    brightness = (red * 299 + green * 587 + blue * 114) / 1000

                    # Restore terminal settings
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

                    return (
                        BackgroundType.LIGHT
                        if brightness > 127
                        else BackgroundType.DARK
                    )

            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        except (OSError, termios.error, AttributeError):
            # Restore terminal settings on any error
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except (OSError, termios.error, AttributeError) as e:
                # Terminal settings restoration failed - log but continue
                # This is non-critical as the terminal will be cleaned up on process exit
                logging.getLogger(__name__).warning(
                    f"Failed to restore terminal settings during OSC query: {e}"
                )

        return BackgroundType.UNKNOWN


class ThemeManager:
    """Manages themes with auto-detection and thread safety."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current_theme: Optional[ThemeConfig] = None
        self._forced_theme: Optional[str] = None
        self.themes = self._load_themes()

    def _load_themes(self) -> Dict[str, ThemeConfig]:
        """Load all available themes."""
        themes = {}

        # Load themes with Rich theme objects
        light_rich = AdaptiveColorScheme.get_light_background_theme()
        dark_rich = AdaptiveColorScheme.get_dark_background_theme()
        classic_rich = AdaptiveColorScheme.get_classic_theme()

        themes["light"] = ThemeConfig(
            name="light",
            colors={},  # No longer using color mappings from defaults.py
            symbols=self._get_symbols_for_theme("light"),
            rich_theme=light_rich,
        )

        themes["dark"] = ThemeConfig(
            name="dark",
            colors={},  # No longer using color mappings from defaults.py
            symbols=self._get_symbols_for_theme("dark"),
            rich_theme=dark_rich,
        )

        themes["classic"] = ThemeConfig(
            name="classic",
            colors={},  # No longer using color mappings from defaults.py
            symbols=self._get_symbols_for_theme("classic"),
            rich_theme=classic_rich,
        )

        return themes

    def _get_symbols_for_theme(self, theme_name: str) -> Dict[str, str]:
        """Get symbols based on theme."""
        if theme_name == "classic":
            return {
                "progress_empty": "-",
                "progress_full": "#",
                "bullet": "*",
                "arrow": "->",
                "check": "[OK]",
                "cross": "[X]",
                "spinner": ["|", "/", "-", "\\"],
            }
        return {
            "progress_empty": "░",
            "progress_full": "█",
            "bullet": "•",
            "arrow": "→",
            "check": "✓",
            "cross": "✗",
            "spinner": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        }

    def auto_detect_theme(self) -> str:
        """Auto-detect appropriate theme based on terminal."""
        background = BackgroundDetector.detect_background()

        if background == BackgroundType.LIGHT:
            return "light"
        if background == BackgroundType.DARK:
            return "dark"
        # Default to dark if unknown
        return "dark"

    def get_theme(
        self, name: Optional[str] = None, force_detection: bool = False
    ) -> ThemeConfig:
        """Get theme by name or auto-detect."""
        with self._lock:
            if name == "auto" or name is None:
                if force_detection or self._forced_theme is None:
                    detected_name = self.auto_detect_theme()
                    theme = self.themes.get(detected_name, self.themes["dark"])
                    if not force_detection:
                        self._forced_theme = detected_name
                else:
                    theme = self.themes.get(self._forced_theme, self.themes["dark"])
            else:
                theme = self.themes.get(name, self.themes["dark"])
                self._forced_theme = name if name in self.themes else None

            self._current_theme = theme
            return theme

    def get_console(
        self, theme_name: Optional[str] = None, force_detection: bool = False
    ) -> Console:
        """Get themed console instance."""
        theme = self.get_theme(theme_name, force_detection)
        return Console(theme=theme.rich_theme, force_terminal=True)

    def get_current_theme(self) -> Optional[ThemeConfig]:
        """Get currently active theme."""
        return self._current_theme


# Cost-based styles with thresholds (moved from ui/styles.py)
COST_STYLES = {
    "low": "cost.low",  # Green - costs under $1
    "medium": "cost.medium",  # Yellow - costs $1-$10
    "high": "cost.high",  # Red - costs over $10
}

# Cost thresholds for automatic style selection
COST_THRESHOLDS: List[Tuple[float, str]] = [
    (10.0, COST_STYLES["high"]),
    (1.0, COST_STYLES["medium"]),
    (0.0, COST_STYLES["low"]),
]

# Velocity/burn rate emojis and labels
VELOCITY_INDICATORS = {
    "slow": {"emoji": "🐌", "label": "Slow", "threshold": 50},
    "normal": {"emoji": "➡️", "label": "Normal", "threshold": 150},
    "fast": {"emoji": "🚀", "label": "Fast", "threshold": 300},
    "very_fast": {"emoji": "⚡", "label": "Very fast", "threshold": float("inf")},
}


# Helper functions for style selection
def get_cost_style(cost: float) -> str:
    """Get appropriate style for a cost value."""
    for threshold, style in COST_THRESHOLDS:
        if cost >= threshold:
            return style
    return COST_STYLES["low"]


def get_velocity_indicator(burn_rate: float) -> Dict[str, str]:
    """Get velocity indicator based on burn rate."""
    for key, indicator in VELOCITY_INDICATORS.items():
        if burn_rate < indicator["threshold"]:
            return {"emoji": indicator["emoji"], "label": indicator["label"]}
    return VELOCITY_INDICATORS["very_fast"]


# Global theme manager instance
_theme_manager = ThemeManager()


def get_themed_console(force_theme=None) -> Console:
    """Get themed console - backward compatibility wrapper."""
    if force_theme and isinstance(force_theme, str):
        return _theme_manager.get_console(force_theme)
    return _theme_manager.get_console(force_theme)


def print_themed(text: str, style: str = "info") -> None:
    """Print text with themed styling - backward compatibility."""
    console = _theme_manager.get_console()
    console.print(f"[{style}]{text}[/]")
