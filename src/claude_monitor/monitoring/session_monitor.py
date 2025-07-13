"""Unified session monitoring - combines tracking and validation.

Provides sophisticated type-safe session monitoring with:
- Real-time session lifecycle tracking
- Advanced performance metrics collection
- Event-driven state management
- Type-safe callback system
- Session persistence and analytics
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypedDict,
    Union,
)

from claude_monitor.monitoring.data_manager import AnalysisResult, SessionBlockDict

logger = logging.getLogger(__name__)


class SessionEvent(Enum):
    """Enumeration of session monitoring events."""

    SESSION_START = auto()
    SESSION_END = auto()
    SESSION_UPDATE = auto()
    SESSION_LIMIT_REACHED = auto()
    SESSION_ERROR = auto()
    SESSION_VALIDATION_FAILED = auto()


class SessionState(Enum):
    """Enumeration of session states."""

    INACTIVE = auto()
    ACTIVE = auto()
    LIMITED = auto()
    ERROR = auto()
    VALIDATING = auto()


class SessionPerformanceMetrics(TypedDict):
    """Type-safe structure for session performance metrics."""

    tokens_per_minute: float
    cost_per_hour: float
    average_response_time: float
    total_duration_minutes: float
    messages_count: int
    efficiency_score: float


class SessionValidationResult(TypedDict):
    """Type-safe structure for session validation results."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validation_timestamp: str
    data_quality_score: float


class SessionAnalytics(TypedDict):
    """Type-safe structure for session analytics data."""

    session_id: str
    start_time: str
    end_time: Optional[str]
    duration_minutes: float
    state: str
    performance_metrics: SessionPerformanceMetrics
    validation_result: SessionValidationResult
    token_usage: Dict[str, int]
    cost_breakdown: Dict[str, float]


class SessionCallbackProtocol(Protocol):
    """Protocol for type-safe session monitoring callbacks."""

    def __call__(
        self,
        event: SessionEvent,
        session_id: str,
        session_data: Optional[SessionBlockDict],
        analytics: Optional[SessionAnalytics] = None,
    ) -> None:
        """Session callback interface.

        Args:
            event: Type of session event
            session_id: Session identifier
            session_data: Current session block data
            analytics: Optional session analytics data
        """
        ...


@dataclass
class SessionTrackingState:
    """Internal state tracking for session monitoring."""

    current_session_id: Optional[str] = None
    current_state: SessionState = SessionState.INACTIVE
    session_start_time: Optional[float] = None
    last_update_time: Optional[float] = None
    total_tokens_tracked: int = 0
    total_cost_tracked: float = 0.0
    validation_errors: List[str] = field(default_factory=list)
    performance_history: List[SessionPerformanceMetrics] = field(default_factory=list)


class SessionMonitor:
    """Advanced session monitoring with real-time analytics and type safety.

    Provides comprehensive session lifecycle management with:
    - Type-safe data validation and processing
    - Real-time performance metrics calculation
    - Event-driven callback system
    - Session state management
    - Analytics and reporting capabilities
    """

    def __init__(
        self,
        enable_analytics: bool = True,
        performance_window_minutes: int = 5,
        max_history_entries: int = 1000,
    ) -> None:
        """Initialize advanced session monitor.

        Args:
            enable_analytics: Enable detailed analytics collection
            performance_window_minutes: Time window for performance calculations
            max_history_entries: Maximum session history entries to retain
        """
        self._state = SessionTrackingState()
        self._callbacks: List[SessionCallbackProtocol] = []
        self._session_history: List[SessionAnalytics] = []

        # Configuration
        self._enable_analytics = enable_analytics
        self._performance_window_minutes = performance_window_minutes
        self._max_history_entries = max_history_entries

        # Performance tracking
        self._response_times: List[Tuple[float, float]] = []  # (timestamp, duration)
        self._token_rates: List[Tuple[float, int]] = []  # (timestamp, tokens)

        logger.info(
            f"SessionMonitor initialized with analytics={'on' if enable_analytics else 'off'}, "
            f"performance_window={performance_window_minutes}min"
        )

    def update(self, data: AnalysisResult) -> Tuple[bool, List[str]]:
        """Update session tracking with new analysis data and perform validation.

        Args:
            data: Type-safe analysis result with session blocks

        Returns:
            Tuple of (is_valid, error_messages)
        """
        update_start_time = time.time()

        # Update tracking state
        self._state.last_update_time = update_start_time
        self._state.current_state = SessionState.VALIDATING

        # Validate data structure and content
        validation_result = self._validate_analysis_result(data)
        if not validation_result["is_valid"]:
            self._state.current_state = SessionState.ERROR
            self._state.validation_errors.extend(validation_result["errors"])
            logger.warning(
                f"Analysis data validation failed: {validation_result['errors']}"
            )

            # Notify callbacks about validation failure
            self._notify_callbacks(
                SessionEvent.SESSION_VALIDATION_FAILED,
                self._state.current_session_id or "unknown",
                None,
            )
            return False, validation_result["errors"]

        # Process session blocks
        blocks = data["blocks"]
        active_session = self._find_active_session(blocks)

        if active_session:
            session_id = active_session["id"]

            # Track performance metrics
            if self._enable_analytics:
                self._update_performance_metrics(active_session, update_start_time)

            # Handle session state changes
            if session_id != self._state.current_session_id:
                self._handle_session_change(session_id, active_session)
            else:
                self._handle_session_update(active_session)

        elif self._state.current_session_id is not None:
            self._handle_session_end()

        # Update state
        self._state.current_state = (
            SessionState.ACTIVE if active_session else SessionState.INACTIVE
        )

        return True, []

    def _validate_analysis_result(
        self, data: AnalysisResult
    ) -> SessionValidationResult:
        """Validate analysis result structure and content with detailed scoring.

        Args:
            data: Type-safe analysis result to validate

        Returns:
            Comprehensive validation result with quality scoring
        """
        errors: List[str] = []
        warnings: List[str] = []
        quality_factors: List[float] = []

        # Validate top-level structure - AnalysisResult is TypedDict so it's always a dict
        quality_factors.append(1.0)

        # Check required fields
        required_fields = [
            "blocks",
            "metadata",
            "entries_count",
            "total_tokens",
            "total_cost",
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            errors.extend(
                [f"Missing required field: {field}" for field in missing_fields]
            )
            quality_factors.append(0.5)
        else:
            quality_factors.append(1.0)

        # Validate blocks - AnalysisResult guarantees blocks is List[SessionBlockDict]
        if "blocks" in data:
            blocks = data["blocks"]
            block_quality_scores = []
            for i, block in enumerate(blocks):
                block_validation = self._validate_session_block(block, i)
                errors.extend(block_validation["errors"])
                warnings.extend(block_validation["warnings"])
                block_quality_scores.append(block_validation["quality_score"])

            # Calculate average block quality
            avg_block_quality = (
                sum(block_quality_scores) / len(block_quality_scores)
                if block_quality_scores
                else 0.0
            )
            quality_factors.append(avg_block_quality)

        # Validate metadata consistency
        if "metadata" in data and "entries_count" in data:
            metadata_entries = data["metadata"].get("entries_processed", 0)
            declared_entries = data["entries_count"]
            if metadata_entries != declared_entries:
                warnings.append(
                    f"Metadata entries ({metadata_entries}) != declared entries ({declared_entries})"
                )
                quality_factors.append(0.8)
            else:
                quality_factors.append(1.0)

        # Calculate overall quality score
        data_quality_score = (
            sum(quality_factors) / len(quality_factors) if quality_factors else 0.0
        )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "data_quality_score": data_quality_score,
        }

    def _validate_session_block(self, block: Any, index: int) -> Dict[str, Any]:
        """Validate individual session block with quality assessment.

        Args:
            block: Session block to validate
            index: Block index for error messages

        Returns:
            Validation result with errors, warnings, and quality score
        """
        errors: List[str] = []
        warnings: List[str] = []
        quality_checks = 0
        passed_checks = 0

        if not isinstance(block, dict):
            errors.append(f"Block {index} must be a dictionary")
            return {"errors": errors, "warnings": warnings, "quality_score": 0.0}

        # Required fields validation
        required_fields = [
            "id",
            "isActive",
            "totalTokens",
            "costUSD",
            "startTime",
            "durationMinutes",
        ]
        for field_name in required_fields:
            quality_checks += 1
            if field_name not in block:
                errors.append(f"Block {index} missing required field: {field_name}")
            else:
                passed_checks += 1

        # Type validation with quality scoring
        type_validations = [
            ("totalTokens", (int, float), "numeric"),
            ("costUSD", (int, float), "numeric"),
            ("isActive", bool, "boolean"),
            ("durationMinutes", (int, float), "numeric"),
            ("sentMessagesCount", int, "integer"),
        ]

        for field, expected_type, type_name in type_validations:
            quality_checks += 1
            if field in block:
                if isinstance(block[field], expected_type):  # type: ignore[arg-type]
                    passed_checks += 1

                    # Additional quality checks
                    if field == "totalTokens" and block[field] < 0:
                        warnings.append(f"Block {index} {field} is negative")
                    elif field == "costUSD" and block[field] < 0:
                        warnings.append(f"Block {index} {field} is negative")
                    elif field == "durationMinutes" and block[field] <= 0:
                        warnings.append(f"Block {index} {field} should be positive")
                else:
                    errors.append(f"Block {index} {field} must be {type_name}")

        # Advanced validation checks
        if "tokenCounts" in block:
            quality_checks += 1
            token_counts = block["tokenCounts"]
            if isinstance(token_counts, dict):
                passed_checks += 1
                expected_token_fields = ["inputTokens", "outputTokens"]
                for field in expected_token_fields:
                    if field not in token_counts:
                        warnings.append(f"Block {index} tokenCounts missing {field}")
            else:
                warnings.append(f"Block {index} tokenCounts should be a dictionary")

        # Calculate quality score
        quality_score = passed_checks / quality_checks if quality_checks > 0 else 0.0

        return {"errors": errors, "warnings": warnings, "quality_score": quality_score}

    def _find_active_session(
        self, blocks: List[SessionBlockDict]
    ) -> Optional[SessionBlockDict]:
        """Find the currently active session from blocks.

        Args:
            blocks: List of session blocks

        Returns:
            Active session block or None
        """
        for block in blocks:
            if block.get("isActive", False):
                return block
        return None

    def _update_performance_metrics(
        self, session_data: SessionBlockDict, timestamp: float
    ) -> None:
        """Update performance tracking metrics.

        Args:
            session_data: Current session data
            timestamp: Current timestamp
        """
        # Track token rates
        total_tokens = session_data.get("totalTokens", 0)
        self._token_rates.append((timestamp, total_tokens))

        # Clean old data outside window
        window_seconds = self._performance_window_minutes * 60
        cutoff_time = timestamp - window_seconds
        self._token_rates = [
            (t, tokens) for t, tokens in self._token_rates if t > cutoff_time
        ]

        # Track response time estimation based on duration
        duration = session_data.get("durationMinutes", 0) * 60  # Convert to seconds
        messages = session_data.get("sentMessagesCount", 1)
        if messages > 0:
            avg_response_time = duration / messages
            self._response_times.append((timestamp, avg_response_time))
            # Clean old response times
            self._response_times = [
                (t, rt) for t, rt in self._response_times if t > cutoff_time
            ]

    def _calculate_performance_metrics(
        self, session_data: SessionBlockDict
    ) -> SessionPerformanceMetrics:
        """Calculate current performance metrics.

        Args:
            session_data: Current session data

        Returns:
            Performance metrics
        """
        duration_minutes = session_data.get("durationMinutes", 0)
        total_tokens = session_data.get("totalTokens", 0)
        total_cost = session_data.get("costUSD", 0.0)
        messages_count = session_data.get("sentMessagesCount", 0)

        # Calculate rates
        tokens_per_minute = (
            total_tokens / duration_minutes if duration_minutes > 0 else 0.0
        )
        cost_per_hour = (
            (total_cost / duration_minutes) * 60 if duration_minutes > 0 else 0.0
        )

        # Average response time from recent data
        recent_response_times = [rt for _, rt in self._response_times]
        avg_response_time = (
            sum(recent_response_times) / len(recent_response_times)
            if recent_response_times
            else 0.0
        )

        # Calculate efficiency score (tokens per dollar)
        efficiency_score = total_tokens / total_cost if total_cost > 0 else 0.0

        return {
            "tokens_per_minute": tokens_per_minute,
            "cost_per_hour": cost_per_hour,
            "average_response_time": avg_response_time,
            "total_duration_minutes": duration_minutes,
            "messages_count": messages_count,
            "efficiency_score": efficiency_score,
        }

    def _handle_session_change(
        self, new_id: str, session_data: SessionBlockDict
    ) -> None:
        """Handle session change with analytics.

        Args:
            new_id: New session ID
            session_data: New session data
        """
        old_id = self._state.current_session_id

        # End previous session if exists
        if old_id is not None:
            self._handle_session_end()

        # Start new session
        self._state.current_session_id = new_id
        self._state.session_start_time = time.time()
        self._state.total_tokens_tracked = session_data.get("totalTokens", 0)
        self._state.total_cost_tracked = session_data.get("costUSD", 0.0)

        if old_id is None:
            logger.info(f"New session started: {new_id}")
        else:
            logger.info(f"Session changed from {old_id} to {new_id}")

        # Create analytics data if enabled
        analytics: Optional[SessionAnalytics] = None
        if self._enable_analytics:
            performance_metrics = self._calculate_performance_metrics(session_data)
            analytics = {
                "session_id": new_id,
                "start_time": session_data.get("startTime", ""),
                "end_time": None,
                "duration_minutes": 0.0,
                "state": SessionState.ACTIVE.name,
                "performance_metrics": performance_metrics,
                "validation_result": {
                    "is_valid": True,
                    "errors": [],
                    "warnings": [],
                    "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "data_quality_score": 1.0,
                },
                "token_usage": {
                    "total": session_data.get("totalTokens", 0),
                    "input": session_data.get("tokenCounts", {}).get("inputTokens", 0),
                    "output": session_data.get("tokenCounts", {}).get(
                        "outputTokens", 0
                    ),
                },
                "cost_breakdown": {
                    "total": session_data.get("costUSD", 0.0),
                    "per_token": session_data.get("costUSD", 0.0)
                    / max(session_data.get("totalTokens", 1), 1),
                },
            }

            # Add to history
            self._session_history.append(analytics)

            # Limit history size
            if len(self._session_history) > self._max_history_entries:
                self._session_history = self._session_history[
                    -self._max_history_entries :
                ]

        # Notify callbacks
        self._notify_callbacks(
            SessionEvent.SESSION_START, new_id, session_data, analytics
        )

    def _handle_session_update(self, session_data: SessionBlockDict) -> None:
        """Handle session update.

        Args:
            session_data: Updated session data
        """
        if self._state.current_session_id is None:
            return

        # Update tracking metrics
        self._state.total_tokens_tracked = session_data.get("totalTokens", 0)
        self._state.total_cost_tracked = session_data.get("costUSD", 0.0)

        # Check for limit conditions
        if self._is_session_limited(session_data):
            self._state.current_state = SessionState.LIMITED
            self._notify_callbacks(
                SessionEvent.SESSION_LIMIT_REACHED,
                self._state.current_session_id,
                session_data,
            )

        # Notify about update
        analytics: Optional[SessionAnalytics] = None
        if self._enable_analytics:
            performance_metrics = self._calculate_performance_metrics(session_data)
            validation_result: SessionValidationResult = {
                "is_valid": True,
                "errors": [],
                "warnings": [],
                "validation_timestamp": datetime.now(timezone.utc).isoformat(),
                "data_quality_score": 1.0,
            }
            analytics = {
                "session_id": self._state.current_session_id,
                "start_time": session_data.get("startTime", ""),
                "end_time": None,
                "duration_minutes": session_data.get("durationMinutes", 0.0),
                "state": self._state.current_state.name,
                "performance_metrics": performance_metrics,
                "validation_result": validation_result,
                "token_usage": {
                    "total": session_data.get("totalTokens", 0),
                    "input": session_data.get("tokenCounts", {}).get("inputTokens", 0),
                    "output": session_data.get("tokenCounts", {}).get(
                        "outputTokens", 0
                    ),
                },
                "cost_breakdown": {
                    "total": session_data.get("costUSD", 0.0),
                    "per_token": session_data.get("costUSD", 0.0)
                    / max(session_data.get("totalTokens", 1), 1),
                },
            }

        self._notify_callbacks(
            SessionEvent.SESSION_UPDATE,
            self._state.current_session_id,
            session_data,
            analytics,
        )

    def _is_session_limited(self, session_data: SessionBlockDict) -> bool:
        """Check if session has hit limits.

        Args:
            session_data: Session data to check

        Returns:
            True if session is limited
        """
        # Check for limit messages
        limit_messages = session_data.get("limitMessages", [])
        return len(limit_messages) > 0

    def _handle_session_end(self) -> None:
        """Handle session end with final analytics."""
        if self._state.current_session_id is None:
            return

        session_id = self._state.current_session_id
        logger.info(f"Session ended: {session_id}")

        # Calculate final analytics
        analytics: Optional[SessionAnalytics] = None
        if self._enable_analytics and self._session_history:
            # Find the current session in history and update it
            for i, hist_entry in enumerate(self._session_history):
                if hist_entry["session_id"] == session_id:
                    current_time = datetime.now(timezone.utc).isoformat()
                    duration = time.time() - (
                        self._state.session_start_time or time.time()
                    )

                    self._session_history[i]["end_time"] = current_time
                    self._session_history[i]["duration_minutes"] = duration / 60
                    self._session_history[i]["state"] = SessionState.INACTIVE.name

                    analytics = self._session_history[i]
                    break

        # Reset state
        self._state.current_session_id = None
        self._state.session_start_time = None
        self._state.current_state = SessionState.INACTIVE

        # Notify callbacks
        self._notify_callbacks(SessionEvent.SESSION_END, session_id, None, analytics)

    def _notify_callbacks(
        self,
        event: SessionEvent,
        session_id: str,
        session_data: Optional[SessionBlockDict],
        analytics: Optional[SessionAnalytics] = None,
    ) -> None:
        """Notify all registered callbacks about session events.

        Args:
            event: Type of session event
            session_id: Session identifier
            session_data: Session data (if available)
            analytics: Session analytics (if available)
        """
        for callback in self._callbacks:
            try:
                callback(event, session_id, session_data, analytics)
            except Exception as e:
                logger.error(f"Session callback error: {e}", exc_info=True)
                self._state.validation_errors.append(f"Callback error: {str(e)}")

    def register_callback(self, callback: SessionCallbackProtocol) -> None:
        """Register type-safe session monitoring callback.

        Args:
            callback: Type-safe callback function
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.debug(
                f"Registered session callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}"
            )

    def unregister_callback(self, callback: SessionCallbackProtocol) -> None:
        """Unregister session monitoring callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(
                f"Unregistered session callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}"
            )

    @property
    def current_session_id(self) -> Optional[str]:
        """Get current active session ID."""
        return self._state.current_session_id

    @property
    def current_session_state(self) -> SessionState:
        """Get current session state."""
        return self._state.current_state

    @property
    def session_count(self) -> int:
        """Get total number of sessions tracked."""
        return len(self._session_history)

    @property
    def session_history(self) -> List[SessionAnalytics]:
        """Get comprehensive session history with analytics."""
        return self._session_history.copy()

    @property
    def performance_metrics(self) -> Optional[SessionPerformanceMetrics]:
        """Get current session performance metrics."""
        if not self._enable_analytics or self._state.current_session_id is None:
            return None

        # Find current session in history
        for analytics in self._session_history:
            if analytics["session_id"] == self._state.current_session_id:
                return analytics["performance_metrics"]

        return None

    @property
    def analytics_enabled(self) -> bool:
        """Check if analytics are enabled."""
        return self._enable_analytics

    @property
    def validation_errors(self) -> List[str]:
        """Get current validation errors."""
        return self._state.validation_errors.copy()

    def get_session_analytics(self, session_id: str) -> Optional[SessionAnalytics]:
        """Get analytics for a specific session.

        Args:
            session_id: Session to get analytics for

        Returns:
            Session analytics or None if not found
        """
        for analytics in self._session_history:
            if analytics["session_id"] == session_id:
                return analytics
        return None

    def clear_validation_errors(self) -> None:
        """Clear accumulated validation errors."""
        self._state.validation_errors.clear()
        logger.debug("Validation errors cleared")

    def get_performance_summary(self) -> Dict[str, Union[int, float]]:
        """Get overall performance summary across all sessions.

        Returns:
            Performance summary statistics
        """
        if not self._session_history:
            return {
                "total_sessions": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "average_duration_minutes": 0.0,
                "average_tokens_per_minute": 0.0,
                "average_cost_per_hour": 0.0,
            }

        total_tokens = sum(
            analytics["token_usage"]["total"] for analytics in self._session_history
        )
        total_cost = sum(
            analytics["cost_breakdown"]["total"] for analytics in self._session_history
        )
        total_duration = sum(
            analytics["duration_minutes"] for analytics in self._session_history
        )

        avg_duration = total_duration / len(self._session_history)
        avg_tokens_per_min = sum(
            analytics["performance_metrics"]["tokens_per_minute"]
            for analytics in self._session_history
        ) / len(self._session_history)
        avg_cost_per_hour = sum(
            analytics["performance_metrics"]["cost_per_hour"]
            for analytics in self._session_history
        ) / len(self._session_history)

        return {
            "total_sessions": len(self._session_history),
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "average_duration_minutes": avg_duration,
            "average_tokens_per_minute": avg_tokens_per_min,
            "average_cost_per_hour": avg_cost_per_hour,
        }
