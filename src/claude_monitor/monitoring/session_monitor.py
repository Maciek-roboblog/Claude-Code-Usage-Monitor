"""Unified session monitoring - combines tracking and validation."""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SessionMonitor:
    """Monitors sessions with tracking and validation."""

    def __init__(self):
        """
        Initialize the SessionMonitor with empty session state, callback list, and session history.
        """
        self._current_session_id: Optional[str] = None
        self._session_callbacks: List[Callable] = []
        self._session_history: List[Dict[str, Any]] = []

    def update(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates and updates the session state with new monitoring data.
        
        Processes the provided data to identify the currently active session. If the active session changes, triggers session change handling; if no session is active but one was previously, triggers session end handling.
        
        Parameters:
            data (Dict[str, Any]): Monitoring data containing session blocks.
        
        Returns:
            Tuple[bool, List[str]]: A tuple where the first element indicates if the data is valid, and the second is a list of validation error messages.
        """
        is_valid, errors = self.validate_data(data)
        if not is_valid:
            logger.warning(f"Data validation failed: {errors}")
            return is_valid, errors

        blocks = data.get("blocks", [])

        active_session = None
        for block in blocks:
            if block.get("isActive", False):
                active_session = block
                break

        if active_session:
            session_id = active_session.get("id")
            if session_id != self._current_session_id:
                self._on_session_change(
                    self._current_session_id, session_id, active_session
                )
                self._current_session_id = session_id
        elif self._current_session_id is not None:
            self._on_session_end(self._current_session_id)
            self._current_session_id = None

        return is_valid, errors

    def validate_data(self, data: Any) -> Tuple[bool, List[str]]:
        """
        Validates the structure and required fields of monitoring data.
        
        Checks that the input is a dictionary containing a "blocks" list, and that each block has the necessary fields with correct types.
        
        Returns:
            A tuple containing a boolean indicating validation success and a list of error messages.
        """
        errors = []

        if not isinstance(data, dict):
            errors.append("Data must be a dictionary")
            return False, errors

        if "blocks" not in data:
            errors.append("Missing required key: blocks")

        if "blocks" in data:
            blocks = data["blocks"]
            if not isinstance(blocks, list):
                errors.append("blocks must be a list")
            else:
                for i, block in enumerate(blocks):
                    block_errors = self._validate_block(block, i)
                    errors.extend(block_errors)

        return len(errors) == 0, errors

    def _validate_block(self, block: Any, index: int) -> List[str]:
        """
        Validates the structure and required fields of a single session block.
        
        Parameters:
            block: The block to validate.
            index: The index of the block, used for error message context.
        
        Returns:
            A list of error messages describing any validation failures for the block.
        """
        errors = []

        if not isinstance(block, dict):
            errors.append(f"Block {index} must be a dictionary")
            return errors

        required_fields = ["id", "isActive", "totalTokens", "costUSD"]
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
        """
        Handles logic when the active session changes, including updating session history and notifying registered callbacks of the session start event.
        
        Parameters:
        	old_id (Optional[str]): The previous session ID, or None if there was no prior session.
        	new_id (str): The new active session ID.
        	session_data (Dict[str, Any]): Data associated with the new session.
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
                logger.error(f"Session callback error: {e}")

    def _on_session_end(self, session_id: str) -> None:
        """
        Handles the end of a session by logging the event and notifying all registered callbacks with the session end event.
        """
        logger.info(f"Session ended: {session_id}")

        for callback in self._session_callbacks:
            try:
                callback("session_end", session_id, None)
            except Exception as e:
                logger.error(f"Session callback error: {e}")

    def register_callback(self, callback: Callable) -> None:
        """
        Registers a callback to be invoked on session start or end events.
        
        The callback should accept three arguments: event_type (str), session_id (str), and session_data (dict).
        """
        if callback not in self._session_callbacks:
            self._session_callbacks.append(callback)

    def unregister_callback(self, callback: Callable) -> None:
        """
        Removes a previously registered callback from the session event listeners.
        
        If the callback is not registered, no action is taken.
        """
        if callback in self._session_callbacks:
            self._session_callbacks.remove(callback)

    @property
    def current_session_id(self) -> Optional[str]:
        """
        Returns the ID of the currently active session, or None if no session is active.
        """
        return self._current_session_id

    @property
    def session_count(self) -> int:
        """
        Return the total number of sessions recorded in the session history.
        """
        return len(self._session_history)

    @property
    def session_history(self) -> List[Dict[str, Any]]:
        """
        Return a copy of the session history containing details of all tracked sessions.
        
        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a session's details.
        """
        return self._session_history.copy()
