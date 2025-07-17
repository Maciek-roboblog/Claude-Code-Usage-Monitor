"""Enhanced compact formatter with customizable fields and coloring support.

This module contains the EnhancedCompactFormatter class that provides advanced
formatting capabilities for compact display mode.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from claude_monitor.ui.session_display import SessionDisplayData

from claude_monitor.compact.color_manager import CompactColorManager
from claude_monitor.compact.field_selector import CompactFieldSelector
from claude_monitor.core.models import CompactColorThresholds


class EnhancedCompactFormatter:
    """Enhanced compact formatter with customizable fields and coloring support.

    This formatter extends the basic compact display with:
    - Customizable field selection via CompactFieldSelector
    - Contextual coloring via CompactColorManager
    - Optimized segment construction for different field combinations
    """

    def __init__(self, field_selector=None, color_manager=None):
        """Initialize enhanced compact formatter with optional components.

        Args:
            field_selector: CompactFieldSelector instance for field management
            color_manager: CompactColorManager instance for coloring
        """
        self.field_selector = field_selector or CompactFieldSelector()
        self.color_manager = color_manager or CompactColorManager(
            CompactColorThresholds(), no_color=False
        )

        # Maximum line length for compact display (tmux compatibility)
        self.max_line_length = 120

        # Separator used between segments
        self.segment_separator = " | "

    def format_compact_line(self, session_data: "SessionDisplayData") -> str:
        """Format compact display with selected fields and colors.

        Args:
            session_data: SessionDisplayData object containing all display information

        Returns:
            Single formatted line for compact display
        """
        # Build field segments based on selected fields
        segments = self._build_field_segments(session_data)

        # Apply contextual colors to segments
        colored_segments = self._apply_colors(segments, session_data)

        # Join segments with separator
        compact_line = self.segment_separator.join(colored_segments)

        # Optimize length if needed
        if len(compact_line) > self.max_line_length:
            compact_line = self._optimize_line_length(colored_segments)

        return compact_line

    def _build_field_segments(self, session_data: "SessionDisplayData") -> list[str]:
        """Build individual field segments for display.

        Args:
            session_data: SessionDisplayData object

        Returns:
            List of formatted field segments
        """
        segments = []
        selected_fields = self.field_selector.get_display_fields()

        for field in selected_fields:
            try:
                field_data = self.field_selector.get_field_data(session_data, field)
                segment = self._format_field_segment(field, field_data, session_data)
                segments.append(segment)
            except Exception:
                # Handle field extraction errors gracefully
                segments.append(f"{field}: N/A")

        return segments

    def _format_field_segment(
        self, field: str, field_data: str, session_data: "SessionDisplayData"
    ) -> str:
        """Format individual field segment with appropriate labels and formatting.

        Args:
            field: Field name
            field_data: Extracted field data
            session_data: Full session data for context

        Returns:
            Formatted field segment
        """
        # Field formatters mapping for cleaner code
        formatters = {
            "tokens": lambda data: f"Claude: {data}",
            "percentage": lambda data: f"({data})",
            "burn_rate": lambda data: data,  # Already includes emoji and units
            "predicted_end": lambda data: f"End: {data}",
            "reset_time": lambda data: f"Reset: {data}",
            "current_time": lambda data: data,  # Just the time, no label needed
        }

        # Use formatter if available, otherwise use generic format
        formatter = formatters.get(field, lambda data: f"{field}: {data}")
        return formatter(field_data)

    def _apply_colors(
        self, segments: list[str], session_data: "SessionDisplayData"
    ) -> list[str]:
        """Apply contextual colors to segments.

        Args:
            segments: List of field segments
            session_data: SessionDisplayData for color context

        Returns:
            List of colorized segments
        """
        if not self.color_manager._should_use_colors():
            return segments

        colored_segments = []
        selected_fields = self.field_selector.get_display_fields()

        # Calculate max burn rate for color context (estimate based on usage)
        max_burn_rate = self._estimate_max_burn_rate(session_data)

        # Get contextual colors for the current state
        contextual_colors = self.color_manager.get_contextual_colors(
            session_data.usage_percentage, session_data.burn_rate, max_burn_rate
        )

        for i, segment in enumerate(segments):
            if i < len(selected_fields):
                field = selected_fields[i]
                colored_segment = self._apply_field_color(
                    segment, field, session_data, max_burn_rate, contextual_colors
                )
                colored_segments.append(colored_segment)
            else:
                colored_segments.append(segment)

        return colored_segments

    def _apply_field_color(
        self,
        segment: str,
        field: str,
        session_data: "SessionDisplayData",
        max_burn_rate: float,
        contextual_colors: dict,
    ) -> str:
        """Apply color to a specific field segment.

        Args:
            segment: Field segment text
            field: Field name
            session_data: Session data for color context
            max_burn_rate: Estimated maximum burn rate
            contextual_colors: Pre-calculated contextual colors

        Returns:
            Colorized segment
        """
        if field in ["tokens", "percentage"]:
            # Apply usage-based coloring
            return self.color_manager.apply_usage_color(
                segment, session_data.usage_percentage
            )
        elif field == "burn_rate":
            # Apply burn rate-based coloring
            return self.color_manager.apply_burn_rate_color(
                segment, session_data.burn_rate, max_burn_rate
            )
        elif field == "predicted_end":
            # Apply warning color if predicted end is soon or critical state
            if self._is_predicted_end_critical(session_data):
                return f"{contextual_colors.get('warning', '[yellow]')}{segment}{contextual_colors.get('close', '[/]')}"
            elif contextual_colors.get("critical"):
                return f"{contextual_colors['critical']}{segment}{contextual_colors['close']}"
            return segment
        elif field == "reset_time":
            # Apply subtle coloring for reset time
            return f"[dim]{segment}[/]"
        elif field == "current_time":
            # Apply timestamp coloring
            return f"[dim]{segment}[/]"
        else:
            # No special coloring for other fields
            return segment

    def _estimate_max_burn_rate(self, session_data: "SessionDisplayData") -> float:
        """Estimate maximum expected burn rate for color scaling.

        Args:
            session_data: SessionDisplayData object

        Returns:
            Estimated maximum burn rate
        """
        # Base estimate on token limit and session duration
        if session_data.total_session_minutes > 0:
            # Assume maximum sustainable rate is using all tokens in session
            max_rate = session_data.token_limit / session_data.total_session_minutes
            return max_rate
        else:
            # Default estimate for unknown session duration
            return 1000.0  # tokens per minute

    def _is_predicted_end_critical(self, session_data: "SessionDisplayData") -> bool:
        """Check if predicted end time indicates critical situation.

        Args:
            session_data: SessionDisplayData object

        Returns:
            True if predicted end is critical (soon or problematic)
        """
        predicted_end = session_data.predicted_end_str.lower()

        # Check for critical indicators
        critical_indicators = ["soon", "minutes", "hour", "critical", "warning"]
        return any(indicator in predicted_end for indicator in critical_indicators)

    def _optimize_line_length(self, segments: list[str]) -> str:
        """Optimize line length by truncating or abbreviating segments.

        Args:
            segments: List of field segments

        Returns:
            Optimized compact line within length limits
        """
        # Try different optimization strategies

        # Strategy 1: Use shorter separator
        short_sep = " | "
        compact_line = short_sep.join(segments)
        if len(compact_line) <= self.max_line_length:
            return compact_line

        # Strategy 2: Abbreviate field labels
        abbreviated_segments = []
        for segment in segments:
            abbreviated = self._abbreviate_segment(segment)
            abbreviated_segments.append(abbreviated)

        compact_line = short_sep.join(abbreviated_segments)
        if len(compact_line) <= self.max_line_length:
            return compact_line

        # Strategy 3: Remove less critical fields
        essential_segments = self._get_essential_segments(abbreviated_segments)
        compact_line = short_sep.join(essential_segments)

        # Final truncation if still too long
        if len(compact_line) > self.max_line_length:
            compact_line = compact_line[: self.max_line_length - 3] + "..."

        return compact_line

    def _abbreviate_segment(self, segment: str) -> str:
        """Abbreviate segment labels to save space.

        Args:
            segment: Original segment text

        Returns:
            Abbreviated segment
        """
        # Common abbreviations for compact display
        abbreviations = {
            "Claude:": "C:",
            "End:": "E:",
            "Reset:": "R:",
            "tokens": "tok",
            "minutes": "min",
            "hours": "h",
        }

        abbreviated = segment
        for full, abbrev in abbreviations.items():
            abbreviated = abbreviated.replace(full, abbrev)

        return abbreviated

    def _get_essential_segments(self, segments: list[str]) -> list[str]:
        """Get essential segments when space is limited.

        Args:
            segments: All available segments

        Returns:
            List of essential segments only
        """
        # Priority order for essential fields

        essential_segments = []
        selected_fields = self.field_selector.get_display_fields()

        # Always include tokens and percentage if available
        for i, segment in enumerate(segments):
            if i < len(selected_fields):
                field = selected_fields[i]
                if field in ["tokens", "percentage", "burn_rate"]:
                    essential_segments.append(segment)
                elif field == "current_time" and len(essential_segments) < 4:
                    essential_segments.append(segment)

        # Ensure we have at least some segments
        if not essential_segments and segments:
            essential_segments = segments[:3]  # Take first 3 segments

        return essential_segments

    def format_compact_no_active_session_line(
        self, plan: str, timezone: str, token_limit: int, current_time_str: str
    ) -> str:
        """Format compact line for no active session state.

        Args:
            plan: Current plan name
            timezone: Display timezone
            token_limit: Token limit for the plan
            current_time_str: Formatted current time string

        Returns:
            Single formatted line for no active session
        """
        # Create basic segments for no active session
        limit_str = self._format_tokens(token_limit)

        segments = []
        selected_fields = self.field_selector.get_display_fields()

        for field in selected_fields:
            if field == "tokens":
                segments.append(f"Claude: 0/{limit_str}")
            elif field == "percentage":
                segments.append("(0.0%)")
            elif field == "burn_rate":
                segments.append("⚫0.0/min")
            elif field == "predicted_end":
                segments.append("End: Inactive")
            elif field == "reset_time":
                segments.append("Reset: N/A")
            elif field == "current_time":
                segments.append(current_time_str)
            else:
                segments.append(f"{field}: N/A")

        return self.segment_separator.join(segments)

    def _format_tokens(self, num: int) -> str:
        """Format token numbers with K (thousands) or M (millions) suffixes.

        Args:
            num: Number of tokens to format

        Returns:
            Formatted string with appropriate suffix
        """
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        else:
            return str(num)
