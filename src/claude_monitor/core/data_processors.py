"""Centralized data processing utilities for Claude Monitor.

This module provides unified data processing functionality to eliminate
code duplication across different components.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from claude_monitor.utils.time_utils import TimezoneHandler


class TimestampProcessor:
    """Unified timestamp parsing and processing utilities."""

    def __init__(self, timezone_handler: Optional[TimezoneHandler] = None) -> None:
        """Initialize with optional timezone handler."""
        self.timezone_handler: TimezoneHandler = timezone_handler or TimezoneHandler()

    def parse_timestamp(
        self, timestamp_value: Union[str, int, float, datetime, None]
    ) -> Optional[datetime]:
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
    def extract_tokens(data: Dict[str, Any]) -> Dict[str, int]:
        """Extract token counts from data in standardized format.

        Args:
            data: Data dictionary with token information

        Returns:
            Dictionary with standardized token keys and counts
        """
        import logging

        logger = logging.getLogger(__name__)

        tokens: Dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
        }

        token_sources: List[Dict[str, Any]] = []

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

            input_tokens = (
                source.get("input_tokens", 0)
                or source.get("inputTokens", 0)
                or source.get("prompt_tokens", 0)
                or 0
            )

            output_tokens = (
                source.get("output_tokens", 0)
                or source.get("outputTokens", 0)
                or source.get("completion_tokens", 0)
                or 0
            )

            cache_creation = (
                source.get("cache_creation_tokens", 0)
                or source.get("cache_creation_input_tokens", 0)
                or source.get("cacheCreationInputTokens", 0)
                or 0
            )

            cache_read = (
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
                    f"TokenExtractor: Found tokens - input={input_tokens}, output={output_tokens}, cache_creation={cache_creation}, cache_read={cache_read}"
                )
                break
            logger.debug(
                f"TokenExtractor: No valid tokens in source: {list(source.keys()) if isinstance(source, dict) else 'not a dict'}"
            )

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
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(DataConverter.flatten_nested_dict(value, new_key))
            else:
                result[new_key] = value

        return result

    @staticmethod
    def extract_model_name(
        data: Dict[str, Any], default: str = "claude-3-5-sonnet"
    ) -> str:
        """Extract model name from various data sources.

        Args:
            data: Data containing model information
            default: Default model name if not found

        Returns:
            Extracted model name
        """
        model_candidates: List[Optional[Any]] = [
            data.get("message", {}).get("model"),
            data.get("model"),
            data.get("Model"),
            data.get("usage", {}).get("model"),
            data.get("request", {}).get("model"),
        ]

        for candidate in model_candidates:
            if candidate and isinstance(candidate, str):
                return candidate

        return default

    @staticmethod
    def to_serializable(obj: Any) -> Any:
        """Convert object to JSON-serializable format.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable representation
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: DataConverter.to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [DataConverter.to_serializable(item) for item in obj]
        return obj
