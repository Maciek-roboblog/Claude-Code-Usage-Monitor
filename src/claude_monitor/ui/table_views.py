"""Table views for daily and monthly statistics display.

This module provides UI components for displaying aggregated usage data
in table format using Rich library.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pytz
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Removed theme import - using direct styles
from claude_monitor.ui.progress_bars import create_dot_sparkline
from claude_monitor.utils.formatting import (
    format_currency,
    format_number,
    format_number_abbreviated,
)
from claude_monitor.utils.model_utils import get_model_display_name

logger = logging.getLogger(__name__)


class TableViewsController:
    """Controller for table-based views (daily, monthly)."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the table views controller.

        Args:
            console: Optional Console instance for rich output
        """
        self.console = console
        # Define simple styles
        self.key_style = "cyan"
        self.value_style = "white"
        self.accent_style = "yellow"
        self.success_style = "green"
        self.warning_style = "yellow"
        self.header_style = "bold cyan"
        self.table_header_style = "bold"
        self.border_style = "bright_blue"

    def _create_base_table(
        self, title: str, period_column_name: str, period_column_width: int
    ) -> Table:
        """Create a base table with common structure.

        Args:
            title: Table title
            period_column_name: Name for the period column ('Date' or 'Month')
            period_column_width: Width for the period column

        Returns:
            Rich Table object with columns added
        """
        table = Table(
            title=title,
            title_style="bold cyan",
            show_header=True,
            header_style="bold",
            border_style="bright_blue",
            expand=True,
            show_lines=True,
        )

        # Add columns
        table.add_column(
            period_column_name, style=self.key_style, width=period_column_width
        )
        table.add_column("Models", style=self.value_style, width=20)
        table.add_column("Input", style=self.value_style, justify="right", width=12)
        table.add_column("Output", style=self.value_style, justify="right", width=12)
        table.add_column(
            "Cache Create", style=self.value_style, justify="right", width=12
        )
        table.add_column(
            "Cache Read", style=self.value_style, justify="right", width=12
        )
        table.add_column(
            "Total Tokens", style=self.accent_style, justify="right", width=12
        )
        table.add_column(
            "Cost (USD)", style=self.success_style, justify="right", width=10
        )

        return table

    def _format_period_value(
        self,
        period_value: str,
        period_key: str,
        date_format: Optional[str] = None,
        timezone: str = "UTC",
    ) -> str:
        """Format period value (date or month) using optional date_format.

        Args:
            period_value: The period value string (e.g., "2024-01" or "2024-01-15")
            period_key: The period key type ('date' or 'month')
            date_format: Optional strftime format string
            timezone: Timezone for date conversion

        Returns:
            Formatted period string
        """
        if not date_format:
            return period_value

        try:
            # Parse the period value based on its format
            if period_key == "month":
                # Format: "YYYY-MM" - parse as first day of month
                year, month = period_value.split("-")
                dt = datetime(int(year), int(month), 1)
            elif period_key == "date":
                # Format: "YYYY-MM-DD"
                dt = datetime.strptime(period_value, "%Y-%m-%d")
            else:
                return period_value

            # Convert to specified timezone
            try:
                tz = pytz.timezone(timezone)
                # For naive datetime, localize to target timezone directly
                # This ensures the date represents the correct day in that timezone
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                else:
                    dt = dt.astimezone(tz)
            except Exception as e:
                # If timezone conversion fails, use naive datetime
                logger.debug(f"Timezone conversion failed: {e}")
                pass

            # Format using strftime
            return dt.strftime(date_format)
        except Exception as e:
            logger.debug(f"Failed to format period value '{period_value}': {e}")
            return period_value

    def _add_data_rows(
        self,
        table: Table,
        data_list: List[Dict[str, Any]],
        period_key: str,
        date_format: Optional[str] = None,
        timezone: str = "UTC",
        abbreviate_tokens: bool = False,
    ) -> None:
        """Add data rows to the table.

        Args:
            table: Table to add rows to
            data_list: List of data dictionaries
            period_key: Key to use for period column ('date' or 'month')
            date_format: Optional strftime format string for period display
            timezone: Timezone for date formatting
            abbreviate_tokens: Whether to abbreviate token counts with 'k' suffix
        """
        # Choose formatting function based on abbreviate_tokens flag
        format_func = format_number_abbreviated if abbreviate_tokens else format_number

        # Calculate max TOTAL tokens across all rows for universal sparkline scaling
        # This allows comparison across rows AND columns (Tufte principle: same scale)
        max_total_tokens = max(
            (
                d["input_tokens"]
                + d["output_tokens"]
                + d["cache_creation_tokens"]
                + d["cache_read_tokens"]
            )
            for d in data_list
        ) if data_list else 1

        for data in data_list:
            models_text = self._format_models(data["models_used"])
            total_tokens = (
                data["input_tokens"]
                + data["output_tokens"]
                + data["cache_creation_tokens"]
                + data["cache_read_tokens"]
            )

            # Format period value if date_format is provided
            period_display = self._format_period_value(
                data[period_key], period_key, date_format, timezone
            )

            # Create dot sparklines using universal scale (max_total_tokens)
            # This allows comparing Input vs Output within a row AND across rows
            input_sparkline = create_dot_sparkline(
                data["input_tokens"], max_total_tokens, width=12
            )
            output_sparkline = create_dot_sparkline(
                data["output_tokens"], max_total_tokens, width=12
            )
            cache_create_sparkline = create_dot_sparkline(
                data["cache_creation_tokens"], max_total_tokens, width=12
            )
            cache_read_sparkline = create_dot_sparkline(
                data["cache_read_tokens"], max_total_tokens, width=12
            )
            total_sparkline = create_dot_sparkline(
                total_tokens, max_total_tokens, width=12
            )

            # Combine formatted number with sparkline on new line
            input_display = f"{format_func(data['input_tokens'])}\n{input_sparkline}"
            output_display = f"{format_func(data['output_tokens'])}\n{output_sparkline}"
            cache_create_display = (
                f"{format_func(data['cache_creation_tokens'])}\n{cache_create_sparkline}"
            )
            cache_read_display = (
                f"{format_func(data['cache_read_tokens'])}\n{cache_read_sparkline}"
            )
            total_display = f"{format_func(total_tokens)}\n{total_sparkline}"

            table.add_row(
                period_display,
                models_text,
                input_display,
                output_display,
                cache_create_display,
                cache_read_display,
                total_display,
                format_currency(data["total_cost"]),
            )

    def _add_totals_row(
        self, table: Table, totals: Dict[str, Any], abbreviate_tokens: bool = False
    ) -> None:
        """Add totals row to the table.

        Args:
            table: Table to add totals to
            totals: Dictionary with total statistics
            abbreviate_tokens: Whether to abbreviate token counts with 'k' suffix
        """
        # Choose formatting function based on abbreviate_tokens flag
        format_func = format_number_abbreviated if abbreviate_tokens else format_number

        # Add separator
        table.add_row("", "", "", "", "", "", "", "")

        # Add totals row
        table.add_row(
            Text("Total", style=self.accent_style),
            "",
            Text(format_func(totals["input_tokens"]), style=self.accent_style),
            Text(format_func(totals["output_tokens"]), style=self.accent_style),
            Text(format_func(totals["cache_creation_tokens"]), style=self.accent_style),
            Text(format_func(totals["cache_read_tokens"]), style=self.accent_style),
            Text(format_func(totals["total_tokens"]), style=self.accent_style),
            Text(format_currency(totals["total_cost"]), style=self.success_style),
        )

    def create_daily_table(
        self,
        daily_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
        date_format: Optional[str] = None,
        abbreviate_tokens: bool = False,
    ) -> Table:
        """Create a daily statistics table.

        Args:
            daily_data: List of daily aggregated data
            totals: Total statistics
            timezone: Timezone for display
            date_format: Optional strftime format string for date display
            abbreviate_tokens: Whether to abbreviate token counts with 'k' suffix

        Returns:
            Rich Table object
        """
        # Create base table
        table = self._create_base_table(
            title=f"Claude Code Token Usage Report - Daily ({timezone})",
            period_column_name="Date",
            period_column_width=12,
        )

        # Add data rows
        self._add_data_rows(
            table, daily_data, "date", date_format, timezone, abbreviate_tokens
        )

        # Add totals
        self._add_totals_row(table, totals, abbreviate_tokens)

        return table

    def create_monthly_table(
        self,
        monthly_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
        date_format: Optional[str] = None,
        abbreviate_tokens: bool = False,
    ) -> Table:
        """Create a monthly statistics table.

        Args:
            monthly_data: List of monthly aggregated data
            totals: Total statistics
            timezone: Timezone for display
            date_format: Optional strftime format string for month display
            abbreviate_tokens: Whether to abbreviate token counts with 'k' suffix

        Returns:
            Rich Table object
        """
        # Create base table
        # Use smaller width for date column (12 chars fits "01 Oct - Wed")
        period_width = 12 if date_format else 10
        table = self._create_base_table(
            title=f"Claude Code Token Usage Report - Monthly ({timezone})",
            period_column_name="Month",
            period_column_width=period_width,
        )

        # Add data rows
        self._add_data_rows(
            table, monthly_data, "month", date_format, timezone, abbreviate_tokens
        )

        # Add totals
        self._add_totals_row(table, totals, abbreviate_tokens)

        return table

    def create_summary_panel(
        self, view_type: str, totals: Dict[str, Any], period: str
    ) -> Panel:
        """Create a summary panel for the table view.

        Args:
            view_type: Type of view ('daily' or 'monthly')
            totals: Total statistics
            period: Period description

        Returns:
            Rich Panel object
        """
        # Create summary text
        summary_lines = [
            f"📊 {view_type.capitalize()} Usage Summary - {period}",
            "",
            f"Total Tokens: {format_number(totals['total_tokens'])}",
            f"Total Cost: {format_currency(totals['total_cost'])}",
            f"Entries: {format_number(totals['entries_count'])}",
        ]

        summary_text = Text("\n".join(summary_lines), style=self.value_style)

        # Create panel
        panel = Panel(
            Align.center(summary_text),
            title="Summary",
            title_align="center",
            border_style=self.border_style,
            expand=False,
            padding=(1, 2),
        )

        return panel

    def _format_models(self, models: List[str]) -> str:
        """Format model names for display using normalized display names.

        Args:
            models: List of model names (can be full model strings)

        Returns:
            Formatted string of model names using display-friendly names
        """
        if not models:
            return "No models"

        # Convert to display names and remove duplicates
        display_names = []
        seen = set()
        for model in models:
            display_name = get_model_display_name(model)
            if display_name and display_name not in seen:
                display_names.append(display_name)
                seen.add(display_name)

        if not display_names:
            return "No models"

        # Create bullet list with display names
        if len(display_names) == 1:
            return display_names[0]
        elif len(display_names) <= 3:
            return "\n".join([f"• {name}" for name in display_names])
        else:
            # Show first two and count of remaining
            first_two = display_names[:2]
            remaining_count = len(display_names) - 2
            formatted = "\n".join([f"• {name}" for name in first_two])
            formatted += f"\n• +{remaining_count} more"
            return formatted

    def create_no_data_display(self, view_type: str) -> Panel:
        """Create a display for when no data is available.

        Args:
            view_type: Type of view ('daily' or 'monthly')

        Returns:
            Rich Panel object
        """
        message = Text(
            f"No {view_type} data found.\n\nTry using Claude Code to generate some usage data.",
            style=self.warning_style,
            justify="center",
        )

        panel = Panel(
            Align.center(message, vertical="middle"),
            title=f"No {view_type.capitalize()} Data",
            title_align="center",
            border_style=self.warning_style,
            expand=True,
            height=10,
        )

        return panel

    def create_aggregate_table(
        self,
        aggregate_data: Union[List[Dict[str, Any]], List[Dict[str, Any]]],
        totals: Dict[str, Any],
        view_type: str,
        timezone: str = "UTC",
        date_format: Optional[str] = None,
        abbreviate_tokens: bool = False,
    ) -> Table:
        """Create a table for either daily or monthly aggregated data.

        Args:
            aggregate_data: List of aggregated data (daily or monthly)
            totals: Total statistics
            view_type: Type of view ('daily' or 'monthly')
            timezone: Timezone for display
            date_format: Optional strftime format string for period display
            abbreviate_tokens: Whether to abbreviate token counts with 'k' suffix

        Returns:
            Rich Table object

        Raises:
            ValueError: If view_type is not 'daily' or 'monthly'
        """
        if view_type == "daily":
            return self.create_daily_table(
                aggregate_data, totals, timezone, date_format, abbreviate_tokens
            )
        elif view_type == "monthly":
            return self.create_monthly_table(
                aggregate_data, totals, timezone, date_format, abbreviate_tokens
            )
        else:
            raise ValueError(f"Invalid view type: {view_type}")

    def display_aggregated_view(
        self,
        data: List[Dict[str, Any]],
        view_mode: str,
        timezone: str,
        plan: str,
        token_limit: int,
        console: Optional[Console] = None,
        date_format: Optional[str] = None,
        abbreviate_tokens: bool = False,
    ) -> None:
        """Display aggregated view with table and summary.

        Args:
            data: Aggregated data
            view_mode: View type ('daily' or 'monthly')
            timezone: Timezone string
            plan: Plan type
            token_limit: Token limit for the plan
            console: Optional Console instance
            date_format: Optional strftime format string for period display
            abbreviate_tokens: Whether to abbreviate token counts with 'k' suffix
        """
        if not data:
            no_data_display = self.create_no_data_display(view_mode)
            if console:
                console.print(no_data_display)
            else:
                print(no_data_display)
            return

        # Calculate totals
        totals = {
            "input_tokens": sum(d["input_tokens"] for d in data),
            "output_tokens": sum(d["output_tokens"] for d in data),
            "cache_creation_tokens": sum(d["cache_creation_tokens"] for d in data),
            "cache_read_tokens": sum(d["cache_read_tokens"] for d in data),
            "total_tokens": sum(
                d["input_tokens"]
                + d["output_tokens"]
                + d["cache_creation_tokens"]
                + d["cache_read_tokens"]
                for d in data
            ),
            "total_cost": sum(d["total_cost"] for d in data),
            "entries_count": sum(d.get("entries_count", 0) for d in data),
        }

        # Determine period for summary
        if view_mode == "daily":
            period = f"{data[0]['date']} to {data[-1]['date']}" if data else "No data"
        else:  # monthly
            period = f"{data[0]['month']} to {data[-1]['month']}" if data else "No data"

        # Create and display summary panel
        summary_panel = self.create_summary_panel(view_mode, totals, period)

        # Create and display table
        table = self.create_aggregate_table(
            data, totals, view_mode, timezone, date_format, abbreviate_tokens
        )

        # Display using console if provided
        if console:
            console.print(summary_panel)
            console.print()
            console.print(table)
        else:
            from rich import print as rprint

            rprint(summary_panel)
            rprint()
            rprint(table)
