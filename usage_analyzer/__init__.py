"""Usage Analyzer - Advanced session blocks analysis for Claude API usage tracking."""

__version__ = "1.0.0"
__author__ = "Usage Analyzer Team"
__email__ = "support@usage-analyzer.dev"

# Import main components for programmatic usage
from .cli import main
from .core.analyzer import SessionBlocksAnalyzer
from .core.data_loader import DataLoader, CostMode
from .core.calculator import BurnRateCalculator
from .core.filtering import BlockFilter
from .core.identifier import SessionBlockIdentifier
from .models.data_structures import (
    SessionBlock,
    TokenCounts,
    ModelBreakdown,
    MessageStats,
    BurnRate,
)
from .models.usage_entry import UsageEntry
from .utils.message_counter import MessageCounter
from .utils.path_discovery import (
    discover_claude_data_paths,
    parse_path_list,
)
from .utils.pricing_fetcher import ClaudePricingFetcher
from .output.json_formatter import JSONFormatter

__all__ = [
    # CLI entry point
    "main",
    # Core classes
    "SessionBlocksAnalyzer",
    "DataLoader",
    "BurnRateCalculator",
    "BlockFilter",
    "SessionBlockIdentifier",
    # Data models
    "SessionBlock",
    "TokenCounts",
    "ModelBreakdown",
    "MessageStats",
    "BurnRate",
    "UsageEntry",
    # Utilities
    "MessageCounter",
    "ClaudePricingFetcher",
    "JSONFormatter",
    # Functions
    "discover_claude_data_paths",
    "parse_path_list",
    # Enums
    "CostMode",
    # Version info
    "__version__",
    "__author__",
    "__email__",
]