"""Centralized data processing utilities for Claude Monitor.

This module provides unified data processing functionality to eliminate
code duplication across different components.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, TypedDict, Union

from claude_monitor.utils.time_utils import TimezoneHandler

# Type definitions for data processing pipeline
TimestampInput = Union[str, int, float, datetime, None]
TokenCount = int
ModelName = str


class TokenData(TypedDict, total=False):
    """Typed dictionary for standardized token information."""

    input_tokens: TokenCount
    output_tokens: TokenCount
    cache_creation_tokens: TokenCount
    cache_read_tokens: TokenCount
    total_tokens: TokenCount


class UsageData(TypedDict, total=False):
    """Typed dictionary for usage information extraction."""

    input_tokens: TokenCount
    inputTokens: TokenCount
    prompt_tokens: TokenCount
    output_tokens: TokenCount
    outputTokens: TokenCount
    completion_tokens: TokenCount
    cache_creation_tokens: TokenCount
    cache_creation_input_tokens: TokenCount
    cacheCreationInputTokens: TokenCount
    cache_read_input_tokens: TokenCount
    cache_read_tokens: TokenCount
    cacheReadInputTokens: TokenCount


class MessageData(TypedDict, total=False):
    """Typed dictionary for message data structure."""

    type: str
    model: ModelName
    usage: UsageData
    message: Dict[str, Any]


class DataProcessor(Protocol):
    """Protocol for data processing operations."""

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return processed result."""
        ...


class Serializable(Protocol):
    """Protocol for serializable objects."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary representation."""
        ...


class TimestampProcessor:
    """Unified timestamp parsing and processing utilities."""

    def __init__(self, timezone_handler: Optional[TimezoneHandler] = None) -> None:
        """Initialize with optional timezone handler."""
        self.timezone_handler: TimezoneHandler = timezone_handler or TimezoneHandler()

    def parse_timestamp(self, timestamp_value: TimestampInput) -> Optional[datetime]:
        """Parse timestamp from various formats to UTC datetime.

        Args:
            timestamp_value: Timestamp in various formats (str, int, float, datetime)

        Returns:
            Parsed UTC datetime or None if parsing fails
        """
        if timestamp_value is None:
            return None

        try:
            if isinstance(timestamp_value, datetime):
                return self.timezone_handler.ensure_timezone(timestamp_value)

            if isinstance(timestamp_value, str):
                if timestamp_value.endswith("Z"):
                    timestamp_value = timestamp_value[:-1] + "+00:00"

                try:
                    dt = datetime.fromisoformat(timestamp_value)
                    return self.timezone_handler.ensure_timezone(dt)
                except ValueError:
                    pass

                for fmt in ["%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        dt = datetime.strptime(timestamp_value, fmt)
                        return self.timezone_handler.ensure_timezone(dt)
                    except ValueError:
                        continue

            if isinstance(timestamp_value, (int, float)):
                dt = datetime.fromtimestamp(timestamp_value)
                return self.timezone_handler.ensure_timezone(dt)

        except Exception:
            pass

        return None


class TokenExtractor:
    """Unified token extraction utilities."""

    @staticmethod
    def extract_tokens(data: Dict[str, Any]) -> TokenData:
        """Extract token counts from data in standardized format.

        Args:
            data: Data dictionary with token information

        Returns:
            TokenData with standardized token keys and counts
        """
        import logging

        logger = logging.getLogger(__name__)

        tokens: TokenData = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
        }

        token_sources: List[Any] = []

        is_assistant: bool = data.get("type") == "assistant"

        if is_assistant:
            if (
                "message" in data
                and isinstance(data["message"], dict)
                and "usage" in data["message"]
            ):
                token_sources.append(data["message"]["usage"])
            if "usage" in data:
                token_sources.append(data["usage"])
            token_sources.append(data)
        else:
            if "usage" in data:
                token_sources.append(data["usage"])
            if (
                "message" in data
                and isinstance(data["message"], dict)
                and "usage" in data["message"]
            ):
                token_sources.append(data["message"]["usage"])
            token_sources.append(data)

        logger.debug(f"TokenExtractor: Checking {len(token_sources)} token sources")

        for source in token_sources:
            if not isinstance(source, dict):
                continue

            input_tokens: TokenCount = (
                source.get("input_tokens", 0)
                or source.get("inputTokens", 0)
                or source.get("prompt_tokens", 0)
                or 0
            )

            output_tokens: TokenCount = (
                source.get("output_tokens", 0)
                or source.get("outputTokens", 0)
                or source.get("completion_tokens", 0)
                or 0
            )

            cache_creation: TokenCount = (
                source.get("cache_creation_tokens", 0)
                or source.get("cache_creation_input_tokens", 0)
                or source.get("cacheCreationInputTokens", 0)
                or 0
            )

            cache_read: TokenCount = (
                source.get("cache_read_input_tokens", 0)
                or source.get("cache_read_tokens", 0)
                or source.get("cacheReadInputTokens", 0)
                or 0
            )

            if input_tokens > 0 or output_tokens > 0:
                tokens.update(
                    {
                        "input_tokens": int(input_tokens),
                        "output_tokens": int(output_tokens),
                        "cache_creation_tokens": int(cache_creation),
                        "cache_read_tokens": int(cache_read),
                        "total_tokens": int(
                            input_tokens + output_tokens + cache_creation + cache_read
                        ),
                    }
                )
                logger.debug(
                    "TokenExtractor: Found tokens - input=%d, output=%d, cache_creation=%d, cache_read=%d",
                    input_tokens,
                    output_tokens,
                    cache_creation,
                    cache_read,
                )
                break
            source_info: str = (
                str(list(source.keys())) if isinstance(source, dict) else "not a dict"
            )
            logger.debug("TokenExtractor: No valid tokens in source: %s", source_info)

        return tokens


class DataConverter:
    """Unified data conversion utilities."""

    @staticmethod
    def flatten_nested_dict(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary structure.

        Args:
            data: Nested dictionary
            prefix: Prefix for flattened keys

        Returns:
            Flattened dictionary
        """
        result: Dict[str, Any] = {}

        for key, value in data.items():
            new_key: str = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                nested_result: Dict[str, Any] = DataConverter.flatten_nested_dict(
                    value, new_key
                )
                result.update(nested_result)
            else:
                result[new_key] = value

        return result

    @staticmethod
    def extract_model_name(
        data: Dict[str, Any], default: ModelName = "claude-3-5-sonnet"
    ) -> ModelName:
        """Extract model name from various data sources.

        Args:
            data: Data containing model information
            default: Default model name if not found

        Returns:
            Extracted model name
        """
        message_dict: Dict[str, Any] = data.get("message", {})
        usage_dict: Dict[str, Any] = data.get("usage", {})
        request_dict: Dict[str, Any] = data.get("request", {})

        model_candidates: List[Any] = [
            message_dict.get("model"),
            data.get("model"),
            data.get("Model"),
            usage_dict.get("model"),
            request_dict.get("model"),
        ]

        for candidate in model_candidates:
            if candidate and isinstance(candidate, str):
                return str(candidate)

        return default

    @staticmethod
    def to_serializable(obj: Any) -> Union[str, Dict[str, Any], List[Any], Any]:
        """Convert object to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            serialized_dict: Dict[str, Any] = {
                k: DataConverter.to_serializable(v) for k, v in obj.items()
            }
            return serialized_dict
        if isinstance(obj, (list, tuple)):
            serialized_list: List[Any] = [
                DataConverter.to_serializable(item) for item in obj
            ]
            return serialized_list
        return obj
