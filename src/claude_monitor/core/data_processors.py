"""Centralized data processing utilities for Claude Monitor.

This module provides unified data processing functionality to eliminate
code duplication across different components.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from claude_monitor.utils.time_utils import TimezoneHandler


class TimestampProcessor:
    """Unified timestamp parsing and processing utilities."""

    def __init__(self, timezone_handler: Optional[TimezoneHandler] = None):
        """
        Initialize a TimestampProcessor with an optional TimezoneHandler.
        
        If no timezone handler is provided, a default TimezoneHandler instance is created.
        """
        self.timezone_handler = timezone_handler or TimezoneHandler()

    def parse_timestamp(self, timestamp_value: Any) -> Optional[datetime]:
        """
        Parses a timestamp value from various formats into a UTC-aware datetime object.
        
        Accepts strings (ISO 8601, with or without 'Z' suffix), integers, floats (as Unix timestamps), or datetime objects. Returns a timezone-aware UTC datetime if parsing succeeds, or None if the input is invalid or cannot be parsed.
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
        """
        Extracts standardized token counts from a data dictionary, handling various possible key names and nested structures.
        
        Searches for token counts in multiple locations and key variants within the input data, prioritizing assistant-type structures. Returns a dictionary with standardized keys: "input_tokens", "output_tokens", "cache_creation_tokens", "cache_read_tokens", and "total_tokens", each representing the corresponding token count or zero if not found.
         
        Returns:
            Dict[str, int]: Dictionary containing standardized token counts.
        """
        import logging

        logger = logging.getLogger(__name__)

        tokens = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
        }

        token_sources = []

        is_assistant = data.get("type") == "assistant"

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
        """
        Recursively flattens a nested dictionary into a single-level dictionary with dot-separated keys.
        
        Parameters:
            data (Dict[str, Any]): The nested dictionary to flatten.
            prefix (str, optional): String to prepend to each key in the flattened dictionary.
        
        Returns:
            Dict[str, Any]: A flat dictionary where nested keys are concatenated with dots.
        """
        result = {}

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
        """
        Extracts the model name string from multiple possible locations within a data dictionary.
        
        Searches for a model name in nested keys such as "message.model", "model", "Model", "usage.model", and "request.model". Returns the first valid string found, or the provided default if none are present.
        
        Parameters:
            data (dict): Dictionary potentially containing model information.
            default (str): Model name to return if none is found in the data.
        
        Returns:
            str: The extracted model name or the default value.
        """
        model_candidates = [
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
        """
        Convert an object into a JSON-serializable format.
        
        Recursively processes dictionaries, lists, and tuples, and converts datetime objects to ISO 8601 strings. Returns the original object if it is already serializable.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: DataConverter.to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [DataConverter.to_serializable(item) for item in obj]
        return obj
