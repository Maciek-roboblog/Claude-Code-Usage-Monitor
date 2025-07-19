"""Unified session monitoring - combines tracking and validation."""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SessionMonitor:
    """Monitors sessions with tracking and validation."""

    def __init__(self) -> None:
        """Initialize session monitor."""
        self._current_session_id: Optional[str] = None
        self._session_callbacks: List[
            Callable[[str, str, Optional[Dict[str, Any]]], None]
        ] = []
        self._session_history: List[Dict[str, Any]] = []

    def update(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Update session tracking with new data and validate.

        Args:
            data: Monitoring data with blocks

        Returns:
            Tuple of (is_valid, error_messages)
        """
        is_valid: bool
        errors: List[str]
        is_valid, errors = self.validate_data(data)
        if not is_valid:
            logger.warning(f"Data validation failed: {errors}")
            return is_valid, errors

        blocks: List[Dict[str, Any]] = data.get("blocks", [])

        active_session: Optional[Dict[str, Any]] = None
        for block in blocks:
            if block.get("isActive", False):
                active_session = block
                break

        if active_session:
            session_id: Optional[str] = active_session.get("id")
            if session_id is not None and session_id != self._current_session_id:
                self._on_session_change(
                    self._current_session_id, session_id, active_session
                )
                self._current_session_id = session_id
        elif self._current_session_id is not None:
            self._on_session_end(self._current_session_id)
            self._current_session_id = None

        return is_valid, errors

    def validate_data(self, data: Any) -> Tuple[bool, List[str]]:
        """Validate monitoring data structure and content.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: List[str] = []

        if not isinstance(data, dict):
            errors.append("Data must be a dictionary")
            return False, errors

        if "blocks" not in data:
            errors.append("Missing required key: blocks")

        if "blocks" in data:
            blocks: Any = data["blocks"]
            if not isinstance(blocks, list):
                errors.append("blocks must be a list")
            else:
                for i, block in enumerate(blocks):
                    block_errors: List[str] = self._validate_block(block, i)
                    errors.extend(block_errors)

        return len(errors) == 0, errors

    def _validate_block(self, block: Any, index: int) -> List[str]:
        """Validate individual block.

        Args:
            block: Block to validate
            index: Block index for error messages

        Returns:
            List of error messages
        """
        errors: List[str] = []

        if not isinstance(block, dict):
            errors.append(f"Block {index} must be a dictionary")
            return errors

        required_fields: List[str] = ["id", "isActive", "totalTokens", "costUSD"]
        for field in required_fields:
            if field not in block:
                errors.append(f"Block {index} missing required field: {field}")

        if "totalTokens" in block and not isinstance(
            block["totalTokens"], (int, float)
        ):
            errors.append(f"Block {index} totalTokens must be numeric")

        if "costUSD" in block and not isinstance(block["costUSD"], (int, float)):
            errors.append(f"Block {index} costUSD must be numeric")

        if "isActive" in block and not isinstance(block["isActive"], bool):
            errors.append(f"Block {index} isActive must be boolean")

        return errors

    def _on_session_change(
        self, old_id: Optional[str], new_id: str, session_data: Dict[str, Any]
    ) -> None:
        """Handle session change.

        Args:
            old_id: Previous session ID
            new_id: New session ID
            session_data: New session data
        """
        if old_id is None:
            logger.info(f"New session started: {new_id}")
        else:
            logger.info(f"Session changed from {old_id} to {new_id}")

        self._session_history.append(
            {
                "id": new_id,
                "started_at": session_data.get("startTime"),
                "tokens": session_data.get("totalTokens", 0),
                "cost": session_data.get("costUSD", 0),
            }
        )

        for callback in self._session_callbacks:
            try:
                callback("session_start", new_id, session_data)
            except Exception as e:
                logger.exception(f"Session callback error: {e}")

    def _on_session_end(self, session_id: str) -> None:
        """Handle session end.

        Args:
            session_id: Ended session ID
        """
        logger.info(f"Session ended: {session_id}")

        for callback in self._session_callbacks:
            try:
                callback("session_end", session_id, None)
            except Exception as e:
                logger.exception(f"Session callback error: {e}")

    def register_callback(
        self, callback: Callable[[str, str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """Register session change callback.

        Args:
            callback: Function(event_type, session_id, session_data)
        """
        if callback not in self._session_callbacks:
            self._session_callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[str, str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """Unregister session change callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._session_callbacks:
            self._session_callbacks.remove(callback)

    @property
    def current_session_id(self) -> Optional[str]:
        """Get current active session ID."""
        return self._current_session_id

    @property
    def session_count(self) -> int:
        """Get total number of sessions tracked."""
        return len(self._session_history)

    @property
    def session_history(self) -> List[Dict[str, Any]]:
        """Get session history."""
        return self._session_history.copy()
