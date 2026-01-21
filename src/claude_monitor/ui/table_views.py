"""Table views for daily, weekly, and monthly statistics display.

This module provides UI components for displaying aggregated usage data
in table format using Rich library, including weekly quota tracking.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from claude_monitor.core.models import WeeklyUsage
from claude_monitor.utils.formatting import format_currency, format_number

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

    def _add_data_rows(
        self, table: Table, data_list: List[Dict[str, Any]], period_key: str
    ) -> None:
        """Add data rows to the table.

        Args:
            table: Table to add rows to
            data_list: List of data dictionaries
            period_key: Key to use for period column ('date' or 'month')
        """
        for data in data_list:
            models_text = self._format_models(data["models_used"])
            total_tokens = (
                data["input_tokens"]
                + data["output_tokens"]
                + data["cache_creation_tokens"]
                + data["cache_read_tokens"]
            )

            table.add_row(
                data[period_key],
                models_text,
                format_number(data["input_tokens"]),
                format_number(data["output_tokens"]),
                format_number(data["cache_creation_tokens"]),
                format_number(data["cache_read_tokens"]),
                format_number(total_tokens),
                format_currency(data["total_cost"]),
            )

    def _add_totals_row(self, table: Table, totals: Dict[str, Any]) -> None:
        """Add totals row to the table.

        Args:
            table: Table to add totals to
            totals: Dictionary with total statistics
        """
        # Add separator
        table.add_row("", "", "", "", "", "", "", "")

        # Add totals row
        table.add_row(
            Text("Total", style=self.accent_style),
            "",
            Text(format_number(totals["input_tokens"]), style=self.accent_style),
            Text(format_number(totals["output_tokens"]), style=self.accent_style),
            Text(
                format_number(totals["cache_creation_tokens"]), style=self.accent_style
            ),
            Text(format_number(totals["cache_read_tokens"]), style=self.accent_style),
            Text(format_number(totals["total_tokens"]), style=self.accent_style),
            Text(format_currency(totals["total_cost"]), style=self.success_style),
        )

    def create_daily_table(
        self,
        daily_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
    ) -> Table:
        """Create a daily statistics table.

        Args:
            daily_data: List of daily aggregated data
            totals: Total statistics
            timezone: Timezone for display

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
        self._add_data_rows(table, daily_data, "date")

        # Add totals
        self._add_totals_row(table, totals)

        return table

    def create_monthly_table(
        self,
        monthly_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
    ) -> Table:
        """Create a monthly statistics table.

        Args:
            monthly_data: List of monthly aggregated data
            totals: Total statistics
            timezone: Timezone for display

        Returns:
            Rich Table object
        """
        # Create base table
        table = self._create_base_table(
            title=f"Claude Code Token Usage Report - Monthly ({timezone})",
            period_column_name="Month",
            period_column_width=10,
        )

        # Add data rows
        self._add_data_rows(table, monthly_data, "month")

        # Add totals
        self._add_totals_row(table, totals)

        return table

    def create_weekly_table(
        self,
        weekly_data: List[Dict[str, Any]],
        totals: Dict[str, Any],
        timezone: str = "UTC",
    ) -> Table:
        """Create a weekly statistics table (ISO weeks).

        Args:
            weekly_data: List of weekly aggregated data
            totals: Total statistics
            timezone: Timezone for display

        Returns:
            Rich Table object
        """
        # Create base table
        table = self._create_base_table(
            title=f"Claude Code Token Usage Report - Weekly ({timezone})",
            period_column_name="Week",
            period_column_width=12,
        )

        # Add data rows
        self._add_data_rows(table, weekly_data, "week")

        # Add totals
        self._add_totals_row(table, totals)

        return table

    def create_weekly_quota_panel(
        self,
        weekly_usage: WeeklyUsage,
        plan_name: str = "custom",
    ) -> Panel:
        """Create a panel showing rolling 7-day weekly quota usage.

        Args:
            weekly_usage: WeeklyUsage data object
            plan_name: Name of the plan for display

        Returns:
            Rich Panel object with quota visualization
        """
        lines = []

        # Header
        lines.append(
            Text("📅 Rolling 7-Day Weekly Quota", style="bold cyan")
        )
        lines.append(Text(""))

        # Progress bar visualization
        pct = weekly_usage.usage_percentage
        bar_width = 30
        filled = int(bar_width * min(pct, 100) / 100)
        empty = bar_width - filled

        # Color based on usage level
        if pct < 50:
            bar_color = "green"
        elif pct < 80:
            bar_color = "yellow"
        else:
            bar_color = "red"

        bar = Text()
        bar.append("   ")
        bar.append("█" * filled, style=bar_color)
        bar.append("░" * empty, style="dim")
        bar.append(f" {pct:.1f}%", style=bar_color)
        lines.append(bar)
        lines.append(Text(""))

        # Token stats
        def format_tokens(n: int) -> str:
            if n >= 1_000_000_000:
                return f"{n / 1_000_000_000:.1f}B"
            if n >= 1_000_000:
                return f"{n / 1_000_000:.1f}M"
            if n >= 1_000:
                return f"{n / 1_000:.0f}K"
            return str(n)

        lines.append(
            Text(
                f"   Used: {format_tokens(weekly_usage.tokens_used)} / "
                f"{format_tokens(weekly_usage.token_limit)} tokens",
                style=self.value_style,
            )
        )
        lines.append(
            Text(
                f"   Remaining: {format_tokens(weekly_usage.tokens_remaining)}",
                style=self.success_style,
            )
        )
        lines.append(
            Text(
                f"   Cost: {format_currency(weekly_usage.cost_used)}",
                style=self.value_style,
            )
        )
        lines.append(Text(""))

        # Burn rate and projections
        if weekly_usage.daily_burn_rate > 0:
            lines.append(Text("📊 Burn Rate", style="bold cyan"))
            lines.append(
                Text(
                    f"   {format_tokens(int(weekly_usage.daily_burn_rate))}/day",
                    style=self.value_style,
                )
            )
            lines.append(
                Text(
                    f"   Projected weekly: {format_tokens(weekly_usage.projected_weekly_total)}",
                    style=self.accent_style,
                )
            )
            lines.append(Text(""))

        # Model breakdown
        if weekly_usage.per_model_tokens:
            lines.append(Text("🤖 By Model", style="bold cyan"))
            total = weekly_usage.tokens_used or 1
            for model, tokens in sorted(
                weekly_usage.per_model_tokens.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                model_pct = (tokens / total) * 100
                # Shorten model name
                short_name = model.replace("claude-", "").replace("-20", "")
                lines.append(
                    Text(
                        f"   {short_name}: {format_tokens(tokens)} ({model_pct:.0f}%)",
                        style=self.value_style,
                    )
                )
            lines.append(Text(""))

        # Warnings
        if pct >= 80:
            lines.append(
                Text(
                    "⚠️  Approaching weekly limit! Consider using Haiku for lighter tasks.",
                    style="yellow",
                )
            )
        elif pct >= 100:
            lines.append(
                Text(
                    "🚨 Weekly quota exceeded - expect rate limiting",
                    style="red bold",
                )
            )

        # Combine all lines
        content = Text()
        for line in lines:
            content.append(line)
            content.append("\n")

        panel = Panel(
            content,
            title=f"Weekly Quota ({plan_name.upper()})",
            title_align="left",
            border_style=self.border_style,
            expand=True,
            padding=(1, 2),
        )

        return panel

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
        """Format model names for display.

        Args:
            models: List of model names

        Returns:
            Formatted string of model names
        """
        if not models:
            return "No models"

        # Create bullet list
        if len(models) == 1:
            return models[0]
        elif len(models) <= 3:
            return "\n".join([f"• {model}" for model in models])
        else:
            # Truncate long lists
            first_two = models[:2]
            remaining_count = len(models) - 2
            formatted = "\n".join([f"• {model}" for model in first_two])
            formatted += f"\n• ...and {remaining_count} more"
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
    ) -> Table:
        """Create a table for aggregated data (daily, weekly, or monthly).

        Args:
            aggregate_data: List of aggregated data
            totals: Total statistics
            view_type: Type of view ('daily', 'weekly', or 'monthly')
            timezone: Timezone for display

        Returns:
            Rich Table object

        Raises:
            ValueError: If view_type is not valid
        """
        if view_type == "daily":
            return self.create_daily_table(aggregate_data, totals, timezone)
        elif view_type == "weekly":
            return self.create_weekly_table(aggregate_data, totals, timezone)
        elif view_type == "monthly":
            return self.create_monthly_table(aggregate_data, totals, timezone)
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
        weekly_usage: Optional[WeeklyUsage] = None,
    ) -> None:
        """Display aggregated view with table and summary.

        Args:
            data: Aggregated data
            view_mode: View type ('daily', 'weekly', or 'monthly')
            timezone: Timezone string
            plan: Plan type
            token_limit: Token limit for the plan
            console: Optional Console instance
            weekly_usage: Optional WeeklyUsage for quota panel (weekly view)
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
        elif view_mode == "weekly":
            period = f"{data[0]['week']} to {data[-1]['week']}" if data else "No data"
        else:  # monthly
            period = f"{data[0]['month']} to {data[-1]['month']}" if data else "No data"

        # For weekly view, show quota panel first if available
        if view_mode == "weekly" and weekly_usage:
            quota_panel = self.create_weekly_quota_panel(weekly_usage, plan)
            if console:
                console.print(quota_panel)
                console.print()
            else:
                from rich import print as rprint
                rprint(quota_panel)
                rprint()

        # Create and display summary panel
        summary_panel = self.create_summary_panel(view_mode, totals, period)

        # Create and display table
        table = self.create_aggregate_table(data, totals, view_mode, timezone)

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
