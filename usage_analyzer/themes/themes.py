"""Rich theme definitions for light and dark terminals."""

from enum import Enum
from rich.theme import Theme


class ThemeType(Enum):
    """Theme type enumeration."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


# Dark theme - optimized for dark terminals
DARK_THEME = Theme({
    # Status and feedback colors
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold cyan",
    
    # Data presentation
    "header": "bold magenta",
    "subheader": "bold blue",
    "value": "bright_white",
    "label": "cyan",
    "timestamp": "dim white",
    
    # Cost and usage colors
    "cost.high": "bold red",
    "cost.medium": "yellow", 
    "cost.low": "green",
    "usage.input": "bright_blue",
    "usage.output": "bright_magenta",
    "usage.total": "bright_white",
    
    # Table formatting
    "table.header": "bold cyan",
    "table.border": "dim white",
    "table.row_even": "white",
    "table.row_odd": "dim white",
    
    # Progress and status
    "progress.bar": "bright_green",
    "progress.percentage": "cyan",
    "status.active": "bold green",
    "status.inactive": "dim red",
})

# Light theme - optimized for light terminals  
LIGHT_THEME = Theme({
    # Status and feedback colors
    "success": "bold green",
    "error": "bold red", 
    "warning": "bold dark_orange",
    "info": "bold blue",
    
    # Data presentation
    "header": "bold purple",
    "subheader": "bold blue",
    "value": "black",
    "label": "blue",
    "timestamp": "dim black",
    
    # Cost and usage colors
    "cost.high": "bold red",
    "cost.medium": "dark_orange",
    "cost.low": "dark_green", 
    "usage.input": "blue",
    "usage.output": "purple",
    "usage.total": "black",
    
    # Table formatting
    "table.header": "bold blue",
    "table.border": "dim black",
    "table.row_even": "black",
    "table.row_odd": "dim black",
    
    # Progress and status
    "progress.bar": "green",
    "progress.percentage": "blue",
    "status.active": "bold green",
    "status.inactive": "dim red",
})


def get_theme(theme_type: ThemeType) -> Theme:
    """Get Rich theme based on theme type.
    
    Args:
        theme_type: The theme type to get
        
    Returns:
        Rich Theme object
    """
    if theme_type == ThemeType.LIGHT:
        return LIGHT_THEME
    elif theme_type == ThemeType.DARK:
        return DARK_THEME
    else:
        # AUTO case - will be resolved by detector
        return DARK_THEME  # Default fallback