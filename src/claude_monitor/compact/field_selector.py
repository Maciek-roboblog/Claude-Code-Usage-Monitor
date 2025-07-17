"""Compact field selector for customizable compact display mode.

Manages field selection, validation, and data extraction for compact mode display.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from claude_monitor.ui.session_display import SessionDisplayData


class CompactFieldValidationError(Exception):
    """Exception raised when compact field validation fails."""

    def __init__(self, invalid_fields: list[str], available_fields: list[str]):
        """Initialize with invalid and available fields.

        Args:
            invalid_fields: List of invalid field names
            available_fields: List of available field names
        """
        self.invalid_fields = invalid_fields
        self.available_fields = available_fields
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """Build error message with invalid and available fields."""
        return (
            f"Invalid fields: {', '.join(self.invalid_fields)}. "
            f"Available: {', '.join(sorted(self.available_fields))}"
        )


class CompactFieldSelector:
    """Manages field selection and data extraction for compact display mode."""

    # Available fields with descriptions
    AVAILABLE_FIELDS: dict[str, str] = {
        "tokens": "Token usage (used/limit)",
        "percentage": "Usage percentage",
        "burn_rate": "Current burn rate",
        "predicted_end": "Predicted session end",
        "reset_time": "Next reset time",
        "current_time": "Current timestamp",
        "time_remaining": "Time remaining until reset",
        "cost": "Current session cost",
        "plan_info": "Plan information",
    }

    # Default fields when none specified
    DEFAULT_FIELDS: list[str] = [
        "tokens",
        "percentage",
        "burn_rate",
        "predicted_end",
        "current_time",
    ]

    def __init__(self, selected_fields: Optional[list[str]] = None):
        """Initialize field selector with optional field list.

        Args:
            selected_fields: List of field names to display, None for default

        Raises:
            CompactFieldValidationError: If any selected fields are invalid
        """
        self.selected_fields = self._validate_fields(selected_fields)

    def _validate_fields(self, fields: Optional[list[str]]) -> list[str]:
        """Validate and return list of fields to display.

        Args:
            fields: List of field names to validate, None for default

        Returns:
            Validated list of field names

        Raises:
            CompactFieldValidationError: If any fields are invalid
        """
        if fields is None:
            return self.DEFAULT_FIELDS.copy()

        # Check if fields is iterable
        try:
            iter(fields)
        except TypeError:
            return self.DEFAULT_FIELDS.copy()

        if not fields:
            raise CompactFieldValidationError([], list(self.AVAILABLE_FIELDS.keys()))

        # Check for invalid fields
        invalid_fields = [
            field for field in fields if field not in self.AVAILABLE_FIELDS
        ]

        if invalid_fields:
            raise CompactFieldValidationError(
                invalid_fields, list(self.AVAILABLE_FIELDS.keys())
            )

        # Remove duplicates while preserving order
        seen = set()
        unique_fields = []
        for field in fields:
            if field not in seen:
                seen.add(field)
                unique_fields.append(field)

        return unique_fields

    def get_display_fields(self) -> list[str]:
        """Return validated list of fields for display.

        Returns:
            List of field names to display
        """
        return self.selected_fields.copy()

    def get_field_data(self, session_data: "SessionDisplayData", field: str) -> str:
        """Extract specific field data for display.

        Args:
            session_data: Session data container
            field: Field name to extract

        Returns:
            Formatted field data string

        Raises:
            ValueError: If field is not available
        """
        if field not in self.AVAILABLE_FIELDS:
            raise ValueError(
                f"Unknown field '{field}'. Available: "
                f"{', '.join(sorted(self.AVAILABLE_FIELDS.keys()))}"
            )

        # Extract data based on field type
        if field == "tokens":
            return self._extract_tokens_data(session_data)
        elif field == "percentage":
            return self._extract_percentage_data(session_data)
        elif field == "burn_rate":
            return self._extract_burn_rate_data(session_data)
        elif field == "predicted_end":
            return self._extract_predicted_end_data(session_data)
        elif field == "reset_time":
            return self._extract_reset_time_data(session_data)
        elif field == "current_time":
            return self._extract_current_time_data(session_data)
        elif field == "time_remaining":
            return self._extract_time_remaining_data(session_data)
        elif field == "cost":
            return self._extract_cost_data(session_data)
        elif field == "plan_info":
            return self._extract_plan_info_data(session_data)
        else:
            return "N/A"

    def _extract_tokens_data(self, session_data: "SessionDisplayData") -> str:
        """Extract token usage data with K/M formatting.

        Args:
            session_data: Session data container

        Returns:
            Formatted token usage string (e.g., "12.5K/44K")
        """
        # Handle case where data is not available
        if not hasattr(session_data, "tokens_used") or session_data.tokens_used is None:
            return "0/0"
        if not hasattr(session_data, "token_limit") or session_data.token_limit is None:
            return f"{self._format_tokens(session_data.tokens_used)}/N/A"

        used_str = self._format_tokens(session_data.tokens_used)
        limit_str = self._format_tokens(session_data.token_limit)
        return f"{used_str}/{limit_str}"

    def _extract_percentage_data(self, session_data: "SessionDisplayData") -> str:
        """Extract usage percentage data.

        Args:
            session_data: Session data container

        Returns:
            Formatted percentage string (e.g., "28.5%")
        """
        # Handle case where data is not available
        if (
            not hasattr(session_data, "usage_percentage")
            or session_data.usage_percentage is None
        ):
            return "0.0%"

        return f"{session_data.usage_percentage:.1f}%"

    def _extract_burn_rate_data(self, session_data: "SessionDisplayData") -> str:
        """Extract burn rate data with appropriate formatting.

        Args:
            session_data: Session data container

        Returns:
            Formatted burn rate string (e.g., "🔥125.5/min")
        """
        # Handle case where data is not available
        if not hasattr(session_data, "burn_rate") or session_data.burn_rate is None:
            return "🔥0.0/min"

        # Format burn rate with appropriate precision
        burn_rate = session_data.burn_rate
        if burn_rate >= 1000:
            # Use K suffix for large burn rates
            return f"🔥{burn_rate / 1000:.1f}K/min"
        elif burn_rate >= 100:
            # No decimal for rates >= 100
            return f"🔥{burn_rate:.0f}/min"
        else:
            # One decimal for smaller rates
            return f"🔥{burn_rate:.1f}/min"

    def _extract_predicted_end_data(self, session_data: "SessionDisplayData") -> str:
        """Extract predicted end time data with fallback handling.

        Args:
            session_data: Session data container

        Returns:
            Formatted predicted end string
        """
        # Handle case where data is not available
        if not hasattr(session_data, "predicted_end_str"):
            return "N/A"

        predicted_end = session_data.predicted_end_str
        if not predicted_end or predicted_end.strip() == "":
            return "N/A"

        # Clean up the string if it contains extra formatting
        cleaned = predicted_end.strip()
        if cleaned.lower() in ["never", "n/a", "unknown", "--"]:
            return "Never"

        return cleaned

    def _extract_reset_time_data(self, session_data: "SessionDisplayData") -> str:
        """Extract reset time data with fallback handling.

        Args:
            session_data: Session data container

        Returns:
            Formatted reset time string
        """
        # Handle case where data is not available
        if not hasattr(session_data, "reset_time_str"):
            return "N/A"

        reset_time = session_data.reset_time_str
        if not reset_time or reset_time.strip() == "":
            return "N/A"

        # Clean up the string if it contains extra formatting
        cleaned = reset_time.strip()
        if cleaned.lower() in ["n/a", "unknown", "--"]:
            return "N/A"

        return cleaned

    def _extract_current_time_data(self, session_data: "SessionDisplayData") -> str:
        """Extract current time data with fallback handling.

        Args:
            session_data: Session data container

        Returns:
            Formatted current time string
        """
        # Handle case where data is not available
        if not hasattr(session_data, "current_time_str"):
            return "--:--:--"

        current_time = session_data.current_time_str
        if not current_time or current_time.strip() == "":
            return "--:--:--"

        # Clean up the string if it contains extra formatting
        cleaned = current_time.strip()
        if cleaned.lower() in ["n/a", "unknown", "--"]:
            return "--:--:--"

        return cleaned

    def _extract_time_remaining_data(self, session_data: "SessionDisplayData") -> str:
        """Extract time remaining data for compact display.

        Args:
            session_data: Session data containing time remaining information

        Returns:
            Formatted time remaining string
        """
        try:
            if (
                not hasattr(session_data, "time_remaining")
                or session_data.time_remaining is None
            ):
                return "N/A"

            time_remaining = session_data.time_remaining
            if isinstance(time_remaining, str):
                return time_remaining
            elif hasattr(time_remaining, "total_seconds"):
                # Handle timedelta objects
                total_seconds = int(time_remaining.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours:02d}:{minutes:02d}"
            else:
                return str(time_remaining)
        except Exception:
            return "N/A"

    def _extract_cost_data(self, session_data: "SessionDisplayData") -> str:
        """Extract cost data for compact display.

        Args:
            session_data: Session data containing cost information

        Returns:
            Formatted cost string
        """
        try:
            if not hasattr(session_data, "cost") or session_data.cost is None:
                return "N/A"

            cost = session_data.cost
            if isinstance(cost, (int, float)):
                return f"${cost:.4f}"
            else:
                return str(cost)
        except Exception:
            return "N/A"

    def _extract_plan_info_data(self, session_data: "SessionDisplayData") -> str:
        """Extract plan info data for compact display.

        Args:
            session_data: Session data containing plan information

        Returns:
            Formatted plan info string
        """
        try:
            if not hasattr(session_data, "plan_info") or session_data.plan_info is None:
                return "N/A"

            plan_info = session_data.plan_info
            if isinstance(plan_info, dict):
                # Extract relevant plan information
                plan_name = plan_info.get("name", "Unknown")
                return plan_name
            else:
                return str(plan_info)
        except Exception:
            return "N/A"

    def _format_tokens(self, num: int) -> str:
        """Format token numbers with K (thousands) or M (millions) suffixes.

        Args:
            num: Number of tokens to format

        Returns:
            Formatted string with appropriate suffix
        """
        if num >= 1_000_000:
            # Format with one decimal and 'M' suffix
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            # Format with one decimal and 'K' suffix
            return f"{num / 1_000:.1f}K"
        else:
            return str(num)
