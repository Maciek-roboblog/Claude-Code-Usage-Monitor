"""
Constants for i18n translation keys.

This module centralizes all keys used for internationalization
of the Claude Usage Monitor.
"""


# Main interface messages
class UI:
    """Main user interface messages."""

    HEADER_TITLE = "ui.header.title"
    LOADING_MESSAGE = "ui.loading.message"
    LOADING_DETAIL = "ui.loading.detail"
    LOADING_WAIT = "ui.loading.wait"
    STATUS_RUNNING = "ui.status.running"
    EXIT_INSTRUCTION = "ui.exit.instruction"
    MONITORING_STOPPED = "ui.monitoring.stopped"


# Status and metrics messages
class STATUS:
    """Status messages and performance indicators."""

    TOKEN_USAGE = "status.token_usage"
    TIME_TO_RESET = "status.time_to_reset"
    TOKENS = "status.tokens"
    BURN_RATE = "status.burn_rate"
    PREDICTED_END = "status.predicted_end"
    TOKEN_RESET = "status.token_reset"
    TOKENS_LEFT = "status.tokens_left"
    LEFT_WORD = "status.left_word"
    NO_ACTIVE_SESSION = "status.no_active_session"
    CUSTOM_LIMIT_DETECTED = "status.custom_limit_detected"
    FALLBACK_PRO_LIMIT = "status.fallback_pro_limit"


# Error messages
class ERROR:
    """Error messages and technical issues."""

    DATA_FETCH_FAILED = "error.data_fetch_failed"
    NOT_LOGGED_IN = "error.not_logged_in"
    NETWORK_CONNECTION = "error.network_connection"
    POSSIBLE_CAUSES = "error.possible_causes"
    UNKNOWN_MESSAGE_KEY = "error.unknown_message_key"


# Notification messages
class NOTIFICATION:
    """User notifications and alerts."""

    LIMIT_EXCEEDED = "notification.limit_exceeded"
    TOKENS_EXCEEDED_MAX = "notification.tokens_exceeded_max"
    TOKENS_EXHAUSTED = "notification.tokens_exhausted"
    SWITCH_TO_CUSTOM = "notification.switch_to_custom"


# Messages for JSON formatter and reports
class REPORT:
    """Messages for reports and JSON formatter."""

    SESSION_SUMMARY = "report.session_summary"
    ACTIVE_SESSIONS = "report.active_sessions"
    COMPLETED_SESSIONS = "report.completed_sessions"
    NO_SESSION_BLOCKS = "report.no_session_blocks"
    TOTAL_COST = "report.total_cost"
    SESSION_ID_TOKENS = "report.session_id_tokens"


# Command-line interface messages
class CLI:
    """Messages for the command-line interface."""

    DESCRIPTION = "cli.description"
    HELP_LANGUAGE = "cli.help.language"
    HELP_PLAN = "cli.help.plan"
    HELP_TIMEZONE = "cli.help.timezone"
    HELP_WATCH = "cli.help.watch"


# Validation and test messages
class VALIDATION:
    """Messages for validation and tests."""

    TEST_MESSAGE = "validation.test_message"
    FALLBACK_TEST = "validation.fallback_test"


# Messages avec pluriels
class PLURAL:
    """Messages nécessitant gestion des pluriels."""

    SESSIONS_ACTIVE = "plural.sessions_active"
    TOKENS_LEFT = "plural.tokens_left"
    MINUTES_REMAINING = "plural.minutes_remaining"
    SESSIONS_COMPLETED = "plural.sessions_completed"


# Compilation of all keys for verification
ALL_MESSAGE_KEYS = {
    # UI
    UI.HEADER_TITLE,
    UI.LOADING_MESSAGE,
    UI.LOADING_DETAIL,
    UI.LOADING_WAIT,
    UI.STATUS_RUNNING,
    UI.EXIT_INSTRUCTION,
    UI.MONITORING_STOPPED,
    # Status
    STATUS.TOKEN_USAGE,
    STATUS.TIME_TO_RESET,
    STATUS.TOKENS,
    STATUS.BURN_RATE,
    STATUS.PREDICTED_END,
    STATUS.TOKEN_RESET,
    STATUS.TOKENS_LEFT,
    STATUS.LEFT_WORD,
    STATUS.NO_ACTIVE_SESSION,
    STATUS.CUSTOM_LIMIT_DETECTED,
    STATUS.FALLBACK_PRO_LIMIT,
    # Error
    ERROR.DATA_FETCH_FAILED,
    ERROR.NOT_LOGGED_IN,
    ERROR.NETWORK_CONNECTION,
    ERROR.POSSIBLE_CAUSES,
    ERROR.UNKNOWN_MESSAGE_KEY,
    # Notification
    NOTIFICATION.LIMIT_EXCEEDED,
    NOTIFICATION.TOKENS_EXCEEDED_MAX,
    NOTIFICATION.TOKENS_EXHAUSTED,
    NOTIFICATION.SWITCH_TO_CUSTOM,
    # Report
    REPORT.SESSION_SUMMARY,
    REPORT.ACTIVE_SESSIONS,
    REPORT.COMPLETED_SESSIONS,
    REPORT.NO_SESSION_BLOCKS,
    REPORT.TOTAL_COST,
    REPORT.SESSION_ID_TOKENS,
    # CLI
    CLI.DESCRIPTION,
    CLI.HELP_LANGUAGE,
    CLI.HELP_PLAN,
    CLI.HELP_TIMEZONE,
    CLI.HELP_WATCH,
    # Plural
    PLURAL.SESSIONS_ACTIVE,
    PLURAL.TOKENS_LEFT,
    PLURAL.MINUTES_REMAINING,
    PLURAL.SESSIONS_COMPLETED,
    # Plural
    PLURAL.SESSIONS_ACTIVE,
    PLURAL.TOKENS_LEFT,
    PLURAL.MINUTES_REMAINING,
    PLURAL.SESSIONS_COMPLETED,
    # Report
    REPORT.SESSION_SUMMARY,
    REPORT.ACTIVE_SESSIONS,
    REPORT.COMPLETED_SESSIONS,
    REPORT.NO_SESSION_BLOCKS,
    REPORT.TOTAL_COST,
    REPORT.SESSION_ID_TOKENS,
}


def validate_message_key(key: str) -> bool:
    """
    Validate that a message key is recognized.

    Args:
        key: Message key to validate

    Returns:
        True if the key is valid, False otherwise
    """
    return key in ALL_MESSAGE_KEYS


def get_all_message_keys() -> set:
    """
    Return the set of all defined message keys.

    Returns:
        Set containing all message keys
    """
    return ALL_MESSAGE_KEYS.copy()
