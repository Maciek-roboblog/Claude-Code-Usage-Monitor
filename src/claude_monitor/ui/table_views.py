"""Table views for daily and monthly statistics display.

This module provides UI components for displaying aggregated usage data
in table format using Rich library.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Removed theme import - using direct styles
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

    def create_daily_table(
        self, daily_data: List[Dict[str, Any]], totals: Dict[str, Any], timezone: str = "UTC"
    ) -> Table:
        """Create a daily statistics table.

        Args:
            daily_data: List of daily aggregated data
            totals: Total statistics
            timezone: Timezone for display

        Returns:
            Rich Table object
        """
        # Create table with title
        table = Table(
            title=f"Claude Code Token Usage Report - Daily ({timezone})",
            title_style="bold cyan",
            show_header=True,
            header_style="bold",
            border_style="bright_blue",
            expand=True,
            show_lines=True,
        )

        # Add columns
        table.add_column("Date", style=self.key_style, width=12)
        table.add_column("Models", style=self.value_style, width=20)
        table.add_column("Input", style=self.value_style, justify="right", width=12)
        table.add_column("Output", style=self.value_style, justify="right", width=12)
        table.add_column("Cache Create", style=self.value_style, justify="right", width=12)
        table.add_column("Cache Read", style=self.value_style, justify="right", width=12)
        table.add_column("Total Tokens", style=self.accent_style, justify="right", width=12)
        table.add_column("Cost (USD)", style=self.success_style, justify="right", width=10)

        # Add data rows
        for data in daily_data:
            models_text = self._format_models(data["models_used"])
            total_tokens = (
                data["input_tokens"]
                + data["output_tokens"]
                + data["cache_creation_tokens"]
                + data["cache_read_tokens"]
            )

            table.add_row(
                data["date"],
                models_text,
                format_number(data["input_tokens"]),
                format_number(data["output_tokens"]),
                format_number(data["cache_creation_tokens"]),
                format_number(data["cache_read_tokens"]),
                format_number(total_tokens),
                format_currency(data["total_cost"]),
            )

        # Add separator
        table.add_row("", "", "", "", "", "", "", "")

        # Add totals row
        table.add_row(
            Text("Total", style=self.accent_style),
            "",
            Text(format_number(totals["input_tokens"]), style=self.accent_style),
            Text(format_number(totals["output_tokens"]), style=self.accent_style),
            Text(format_number(totals["cache_creation_tokens"]), style=self.accent_style),
            Text(format_number(totals["cache_read_tokens"]), style=self.accent_style),
            Text(format_number(totals["total_tokens"]), style=self.accent_style),
            Text(format_currency(totals["total_cost"]), style=self.success_style),
        )

        return table

    def create_monthly_table(
        self, monthly_data: List[Dict[str, Any]], totals: Dict[str, Any], timezone: str = "UTC"
    ) -> Table:
        """Create a monthly statistics table.

        Args:
            monthly_data: List of monthly aggregated data
            totals: Total statistics
            timezone: Timezone for display

        Returns:
            Rich Table object
        """
        # Create table with title
        table = Table(
            title=f"Claude Code Token Usage Report - Monthly ({timezone})",
            title_style="bold cyan",
            show_header=True,
            header_style="bold",
            border_style="bright_blue",
            expand=True,
            show_lines=True,
        )

        # Add columns
        table.add_column("Month", style=self.key_style, width=10)
        table.add_column("Models", style=self.value_style, width=20)
        table.add_column("Input", style=self.value_style, justify="right", width=12)
        table.add_column("Output", style=self.value_style, justify="right", width=12)
        table.add_column("Cache Create", style=self.value_style, justify="right", width=12)
        table.add_column("Cache Read", style=self.value_style, justify="right", width=12)
        table.add_column("Total Tokens", style=self.accent_style, justify="right", width=12)
        table.add_column("Cost (USD)", style=self.success_style, justify="right", width=10)

        # Add data rows
        for data in monthly_data:
            models_text = self._format_models(data["models_used"])
            total_tokens = (
                data["input_tokens"]
                + data["output_tokens"]
                + data["cache_creation_tokens"]
                + data["cache_read_tokens"]
            )

            table.add_row(
                data["month"],
                models_text,
                format_number(data["input_tokens"]),
                format_number(data["output_tokens"]),
                format_number(data["cache_creation_tokens"]),
                format_number(data["cache_read_tokens"]),
                format_number(total_tokens),
                format_currency(data["total_cost"]),
            )

        # Add separator
        table.add_row("", "", "", "", "", "", "", "")

        # Add totals row
        table.add_row(
            Text("Total", style=self.accent_style),
            "",
            Text(format_number(totals["input_tokens"]), style=self.accent_style),
            Text(format_number(totals["output_tokens"]), style=self.accent_style),
            Text(format_number(totals["cache_creation_tokens"]), style=self.accent_style),
            Text(format_number(totals["cache_read_tokens"]), style=self.accent_style),
            Text(format_number(totals["total_tokens"]), style=self.accent_style),
            Text(format_currency(totals["total_cost"]), style=self.success_style),
        )

        return table

    def create_summary_panel(self, view_type: str, totals: Dict[str, Any], period: str) -> Panel:
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
        else:
            return "\n".join([f"• {model}" for model in models])

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
        """Create a table for either daily or monthly aggregated data.

        Args:
            aggregate_data: List of aggregated data (daily or monthly)
            totals: Total statistics
            view_type: Type of view ('daily' or 'monthly')
            timezone: Timezone for display

        Returns:
            Rich Table object

        Raises:
            ValueError: If view_type is not 'daily' or 'monthly'
        """
        if view_type == "daily":
            return self.create_daily_table(aggregate_data, totals, timezone)
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
    ) -> None:
        """Display aggregated view with table and summary.
        
        Args:
            data: Aggregated data
            view_mode: View type ('daily' or 'monthly')
            timezone: Timezone string
            plan: Plan type
            token_limit: Token limit for the plan
            console: Optional Console instance
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
                d["input_tokens"] + d["output_tokens"] + 
                d["cache_creation_tokens"] + d["cache_read_tokens"] 
                for d in data
            ),
            "total_cost": sum(d["total_cost"] for d in data),
            "entries_count": len(data),
        }
        
        # Determine period for summary
        if view_mode == "daily":
            period = f"{data[0]['date']} to {data[-1]['date']}" if data else "No data"
        else:  # monthly
            period = f"{data[0]['month']} to {data[-1]['month']}" if data else "No data"
        
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

