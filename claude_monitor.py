#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
import threading
from datetime import datetime, timedelta

import pytz

from usage_analyzer.api import analyze_usage

# All internal calculations use UTC, display timezone is configurable
UTC_TZ = pytz.UTC

# Notification persistence configuration
NOTIFICATION_MIN_DURATION = 5  # seconds - minimum time to display notifications

# Global notification state tracker
notification_states = {
    'switch_to_custom': {'triggered': False, 'timestamp': None},
    'exceed_max_limit': {'triggered': False, 'timestamp': None}, 
    'tokens_will_run_out': {'triggered': False, 'timestamp': None}
}

def update_notification_state(notification_type, condition_met, current_time):
    """Update notification state and return whether to show notification."""
    state = notification_states[notification_type]
    
    if condition_met:
        if not state['triggered']:
            # First time triggering - record timestamp
            state['triggered'] = True
            state['timestamp'] = current_time
        return True
    else:
        if state['triggered']:
            # Check if minimum duration has passed
            elapsed = (current_time - state['timestamp']).total_seconds()
            if elapsed >= NOTIFICATION_MIN_DURATION:
                # Reset state after minimum duration
                state['triggered'] = False
                state['timestamp'] = None
                return False
            else:
                # Still within minimum duration - keep showing
                return True
        return False

# Terminal handling for Unix-like systems
try:
    import termios

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

def format_time(minutes):
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def create_token_progress_bar(percentage, width=50):
    """Create a token usage progress bar with bracket style."""
    filled = int(width * percentage / 100)

    # Create the bar with green fill and red empty space
    green_bar = "█" * filled
    red_bar = "░" * (width - filled)

    # Color codes
    green = "\033[92m"  # Bright green
    red = "\033[91m"  # Bright red
    reset = "\033[0m"

    return f"🟢 [{green}{green_bar}{red}{red_bar}{reset}] {percentage:.1f}%"


def create_time_progress_bar(elapsed_minutes, total_minutes, width=50):
    """Create a time progress bar showing time until reset."""
    if total_minutes <= 0:
        percentage = 0
    else:
        percentage = min(100, (elapsed_minutes / total_minutes) * 100)

    filled = int(width * percentage / 100)

    # Create the bar with blue fill and red empty space
    blue_bar = "█" * filled
    red_bar = "░" * (width - filled)

    # Color codes
    blue = "\033[94m"  # Bright blue
    red = "\033[91m"  # Bright red
    reset = "\033[0m"

    remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
    return f"⏰ [{blue}{blue_bar}{red}{red_bar}{reset}] {remaining_time}"


def print_header():
    """Return the stylized header with sparkles as a list of strings."""
    cyan = "\033[96m"
    blue = "\033[94m"
    reset = "\033[0m"

    # Sparkle pattern
    sparkles = f"{cyan}✦ ✧ ✦ ✧ {reset}"

    return [
        f"{sparkles}{cyan}CLAUDE CODE USAGE MONITOR{reset} {sparkles}",
        f"{blue}{'=' * 60}{reset}",
        "",
    ]


def show_loading_screen():
    """Display a loading screen while fetching data."""
    cyan = "\033[96m"
    yellow = "\033[93m"
    gray = "\033[90m"
    reset = "\033[0m"

    screen_buffer = []
    screen_buffer.append("\033[H")  # Home position
    screen_buffer.extend(print_header())
    screen_buffer.append("")
    screen_buffer.append(f"{cyan}⏳ Loading...{reset}")
    screen_buffer.append("")
    screen_buffer.append(f"{yellow}Fetching Claude usage data...{reset}")
    screen_buffer.append("")
    screen_buffer.append(f"{gray}This may take a few seconds{reset}")

    # Clear screen and print buffer
    print("\033[2J" + "\n".join(screen_buffer) + "\033[J", end="", flush=True)


def get_velocity_indicator(burn_rate):
    """Get velocity emoji based on burn rate."""
    if burn_rate < 50:
        return "🐌"  # Slow
    elif burn_rate < 150:
        return "➡️"  # Normal
    elif burn_rate < 300:
        return "🚀"  # Fast
    else:
        return "⚡"  # Very fast


def calculate_hourly_burn_rate(blocks, current_time):
    """Calculate burn rate based on all sessions in the last hour."""
    if not blocks:
        return 0

    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = 0

    for block in blocks:
        start_time_str = block.get("startTime")
        if not start_time_str:
            continue

        # Parse start time - data from usage_analyzer is in UTC
        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        # Ensure it's in UTC for calculations
        if start_time.tzinfo is None:
            start_time = UTC_TZ.localize(start_time)
        else:
            start_time = start_time.astimezone(UTC_TZ)

        # Skip gaps
        if block.get("isGap", False):
            continue

        # Determine session end time
        if block.get("isActive", False):
            # For active sessions, use current time
            session_actual_end = current_time
        else:
            # For completed sessions, use actualEndTime or current time
            actual_end_str = block.get("actualEndTime")
            if actual_end_str:
                session_actual_end = datetime.fromisoformat(
                    actual_end_str.replace("Z", "+00:00")
                )
                # Ensure it's in UTC for calculations
                if session_actual_end.tzinfo is None:
                    session_actual_end = UTC_TZ.localize(session_actual_end)
                else:
                    session_actual_end = session_actual_end.astimezone(UTC_TZ)
            else:
                session_actual_end = current_time

        # Check if session overlaps with the last hour
        if session_actual_end < one_hour_ago:
            # Session ended before the last hour
            continue

        # Calculate how much of this session falls within the last hour
        session_start_in_hour = max(start_time, one_hour_ago)
        session_end_in_hour = min(session_actual_end, current_time)

        if session_end_in_hour <= session_start_in_hour:
            continue

        # Calculate portion of tokens used in the last hour
        total_session_duration = (
            session_actual_end - start_time
        ).total_seconds() / 60  # minutes
        hour_duration = (
            session_end_in_hour - session_start_in_hour
        ).total_seconds() / 60  # minutes

        if total_session_duration > 0:
            session_tokens = block.get("totalTokens", 0)
            tokens_in_hour = session_tokens * (hour_duration / total_session_duration)
            total_tokens += tokens_in_hour

    # Return tokens per minute
    return total_tokens / 60 if total_tokens > 0 else 0




def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Claude Token Monitor - Real-time token usage monitoring"
    )
    parser.add_argument(
        "--plan",
        type=str,
        default="pro",
        choices=["pro", "max5", "max20", "custom_max"],
        help='Claude plan type (default: pro). Use "custom_max" to auto-detect from highest previous block',
    )
    parser.add_argument(
        "--reset-hour", type=int, help="Change the reset hour (0-23) for daily limits"
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default="Europe/Warsaw",
        help="Timezone for reset times (default: Europe/Warsaw). Examples: US/Eastern, Asia/Tokyo, UTC",
    )
    return parser.parse_args()


def get_token_limit(plan, blocks=None):
    # TODO calculate old based on limits
    limits = {"pro": 44000, "max5": 220000, "max20": 880000}

    """Get token limit based on plan type."""
    if plan == "custom_max" and blocks:
        max_tokens = 0
        for block in blocks:
            if not block.get("isGap", False) and not block.get("isActive", False):
                tokens = block.get("totalTokens", 0)
                if tokens > max_tokens:
                    max_tokens = tokens
        return max_tokens if max_tokens > 0 else limits["pro"]

    return limits.get(plan, 44000)


def setup_terminal():
    """Setup terminal for raw mode to prevent input interference."""
    if not HAS_TERMIOS or not sys.stdin.isatty():
        return None

    try:
        # Save current terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        # Set terminal to non-canonical mode (disable echo and line buffering)
        new_settings = termios.tcgetattr(sys.stdin)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)
        return old_settings
    except Exception:
        return None


def restore_terminal(old_settings):
    """Restore terminal to original settings."""
    # Show cursor and exit alternate screen buffer
    print("\033[?25h\033[?1049l", end="", flush=True)

    if old_settings and HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)
        except Exception:
            pass


def flush_input():
    """Flush any pending input to prevent display corruption."""
    if HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass


def main():
    """Main monitoring loop."""
    args = parse_args()

    # Define color codes at the beginning to ensure they're available in exception handlers
    cyan = "\033[96m"
    red = "\033[91m"
    yellow = "\033[93m"
    white = "\033[97m"
    gray = "\033[90m"
    reset = "\033[0m"



    # Create event for clean refresh timing
    stop_event = threading.Event()

    # Setup terminal to prevent input interference
    old_terminal_settings = setup_terminal()

    # For 'custom_max' plan, we need to get data first to determine the limit
    if args.plan == "custom_max":
        print(
            f"{cyan}Fetching initial data to determine custom max token limit...{reset}"
        )
        initial_data = analyze_usage()
        if initial_data and "blocks" in initial_data:
            token_limit = get_token_limit(args.plan, initial_data["blocks"])
            print(f"{cyan}Custom max token limit detected: {token_limit:,}{reset}")
        else:
            token_limit = get_token_limit("pro")  # Fallback to pro
            print(
                f"{yellow}Failed to fetch data, falling back to Pro limit: {token_limit:,}{reset}"
            )
    else:
        token_limit = get_token_limit(args.plan)

    try:
        # Enter alternate screen buffer, clear and hide cursor
        print("\033[?1049h\033[2J\033[H\033[?25l", end="", flush=True)

        # Show loading screen immediately
        show_loading_screen()

        while True:
            # Flush any pending input to prevent display corruption
            flush_input()

            # Build complete screen in buffer
            screen_buffer = []
            screen_buffer.append("\033[H")  # Home position

            data = analyze_usage()
            if not data or "blocks" not in data:
                screen_buffer.extend(print_header())
                screen_buffer.append(f"{red}Failed to get usage data{reset}")
                screen_buffer.append("")
                screen_buffer.append(f"{yellow}Possible causes:{reset}")
                screen_buffer.append("  • You're not logged into Claude")
                screen_buffer.append("  • Network connection issues")
                screen_buffer.append("")
                screen_buffer.append(
                    f"{gray}Retrying in 3 seconds... (Ctrl+C to exit){reset}"
                )
                # Clear screen and print buffer
                print(
                    "\033[2J" + "\n".join(screen_buffer) + "\033[J", end="", flush=True
                )
                stop_event.wait(timeout=3.0)
                continue

            # Find the active block
            active_block = None
            for block in data["blocks"]:
                if block.get("isActive", False):
                    active_block = block
                    break

            if not active_block:
                screen_buffer.extend(print_header())
                screen_buffer.append(
                    "📊 \033[97mToken Usage:\033[0m    \033[92m🟢 [\033[92m░"
                    + "░" * 49
                    + "\033[0m] 0.0%\033[0m"
                )
                screen_buffer.append("")
                screen_buffer.append(
                    "🎯 \033[97mTokens:\033[0m         \033[97m0\033[0m / \033[90m~{:,}\033[0m (\033[96m0 left\033[0m)".format(
                        token_limit
                    )
                )
                screen_buffer.append(
                    "🔥 \033[97mBurn Rate:\033[0m      \033[93m0.0\033[0m \033[90mtokens/min\033[0m"
                )
                screen_buffer.append("")
                # Use configured timezone for time display
                try:
                    display_tz = pytz.timezone(args.timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    display_tz = pytz.timezone("Europe/Warsaw")
                current_time_display = datetime.now(UTC_TZ).astimezone(display_tz)
                current_time_str = current_time_display.strftime("%H:%M:%S")
                screen_buffer.append(
                    "⏰ \033[90m{}\033[0m 📝 \033[96mNo active session\033[0m | \033[90mCtrl+C to exit\033[0m 🟨".format(
                        current_time_str
                    )
                )
                # Clear screen and print buffer
                print(
                    "\033[2J" + "\n".join(screen_buffer) + "\033[J", end="", flush=True
                )
                stop_event.wait(timeout=3.0)
                continue

            # Extract data from active block
            tokens_used = active_block.get("totalTokens", 0)
            
            # Store original limit for notification
            original_limit = get_token_limit(args.plan)

            # Check if tokens exceed limit and switch to custom_max if needed
            if tokens_used > token_limit and args.plan != "custom_max":
                # Auto-switch to custom_max when any plan limit is exceeded
                new_limit = get_token_limit("custom_max", data["blocks"])
                if new_limit > token_limit:
                    token_limit = new_limit

            usage_percentage = (
                (tokens_used / token_limit) * 100 if token_limit > 0 else 0
            )
            tokens_left = token_limit - tokens_used

            # Time calculations - all internal calculations in UTC
            start_time_str = active_block.get("startTime")
            if start_time_str:
                start_time = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00")
                )
                # Ensure start_time is in UTC
                if start_time.tzinfo is None:
                    start_time = UTC_TZ.localize(start_time)
                else:
                    start_time = start_time.astimezone(UTC_TZ)
            
            # Extract endTime from active block (comes in UTC from usage_analyzer)
            end_time_str = active_block.get("endTime")
            if end_time_str:
                reset_time = datetime.fromisoformat(
                    end_time_str.replace("Z", "+00:00")
                )
                # Ensure reset_time is in UTC
                if reset_time.tzinfo is None:
                    reset_time = UTC_TZ.localize(reset_time)
                else:
                    reset_time = reset_time.astimezone(UTC_TZ)
            else:
                # Fallback: if no endTime, estimate 5 hours from startTime
                reset_time = start_time + timedelta(hours=5) if start_time_str else datetime.now(UTC_TZ) + timedelta(hours=5)
            
            # Always use UTC for internal calculations
            current_time = datetime.now(UTC_TZ)

            # Calculate burn rate from ALL sessions in the last hour
            burn_rate = calculate_hourly_burn_rate(data["blocks"], current_time)

            # Calculate time to reset
            time_to_reset = reset_time - current_time
            minutes_to_reset = time_to_reset.total_seconds() / 60

            # Predicted end calculation - when tokens will run out based on burn rate
            if burn_rate > 0 and tokens_left > 0:
                minutes_to_depletion = tokens_left / burn_rate
                predicted_end_time = current_time + timedelta(
                    minutes=minutes_to_depletion
                )
            else:
                # If no burn rate or tokens already depleted, use reset time
                predicted_end_time = reset_time

            # Display header
            screen_buffer.extend(print_header())

            # Token Usage section
            screen_buffer.append(
                f"📊 {white}Token Usage:{reset}    {create_token_progress_bar(usage_percentage)}"
            )
            screen_buffer.append("")

            # Time to Reset section - calculate progress based on actual session duration
            if start_time_str and end_time_str:
                # Calculate actual session duration and elapsed time
                total_session_minutes = (reset_time - start_time).total_seconds() / 60
                elapsed_session_minutes = (current_time - start_time).total_seconds() / 60
                elapsed_session_minutes = max(0, elapsed_session_minutes)  # Ensure non-negative
            else:
                # Fallback to 5 hours if times not available
                total_session_minutes = 300
                elapsed_session_minutes = max(0, 300 - minutes_to_reset)
            
            screen_buffer.append(
                f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(elapsed_session_minutes, total_session_minutes)}"
            )
            screen_buffer.append("")

            # Detailed stats
            screen_buffer.append(
                f"🎯 {white}Tokens:{reset}         {white}{tokens_used:,}{reset} / {gray}~{token_limit:,}{reset} ({cyan}{tokens_left:,} left{reset})"
            )
            screen_buffer.append(
                f"🔥 {white}Burn Rate:{reset}      {yellow}{burn_rate:.1f}{reset} {gray}tokens/min{reset}"
            )
            screen_buffer.append("")

            # Predictions - convert to configured timezone for display
            try:
                local_tz = pytz.timezone(args.timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                local_tz = pytz.timezone("Europe/Warsaw")
            predicted_end_local = predicted_end_time.astimezone(local_tz)
            reset_time_local = reset_time.astimezone(local_tz)

            predicted_end_str = predicted_end_local.strftime("%H:%M")
            reset_time_str = reset_time_local.strftime("%H:%M")
            screen_buffer.append(f"🏁 {white}Predicted End:{reset} {predicted_end_str}")
            screen_buffer.append(f"🔄 {white}Token Reset:{reset}   {reset_time_str}")
            screen_buffer.append("")

            # Update persistent notifications using current conditions
            show_switch_notification = update_notification_state(
                'switch_to_custom', token_limit > original_limit, current_time
            )
            show_exceed_notification = update_notification_state(
                'exceed_max_limit', tokens_used > token_limit, current_time
            )
            show_tokens_will_run_out = update_notification_state(
                'tokens_will_run_out', predicted_end_time < reset_time, current_time
            )

            # Display persistent notifications
            if show_switch_notification:
                screen_buffer.append(
                    f"🔄 {yellow}Tokens exceeded {args.plan.upper()} limit - switched to custom_max ({token_limit:,}){reset}"
                )
                screen_buffer.append("")

            if show_exceed_notification:
                screen_buffer.append(
                    f"🚨 {red}TOKENS EXCEEDED MAX LIMIT! ({tokens_used:,} > {token_limit:,}){reset}"
                )
                screen_buffer.append("")

            if show_tokens_will_run_out:
                screen_buffer.append(
                    f"⚠️  {red}Tokens will run out BEFORE reset!{reset}"
                )
                screen_buffer.append("")

            # Status line - use configured timezone for consistency
            try:
                display_tz = pytz.timezone(args.timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                display_tz = pytz.timezone("Europe/Warsaw")
            current_time_display = datetime.now(UTC_TZ).astimezone(display_tz)
            current_time_str = current_time_display.strftime("%H:%M:%S")
            screen_buffer.append(
                f"⏰ {gray}{current_time_str}{reset} 📝 {cyan}Smooth sailing...{reset} | {gray}Ctrl+C to exit{reset} 🟨"
            )

            # Clear screen and print entire buffer at once
            print("\033[2J" + "\n".join(screen_buffer) + "\033[J", end="", flush=True)

            stop_event.wait(timeout=3.0)

    except KeyboardInterrupt:
        # Set the stop event for immediate response
        stop_event.set()
        # Restore terminal settings
        restore_terminal(old_terminal_settings)
        print(f"\n\n{cyan}Monitoring stopped.{reset}")
        sys.exit(0)
    except Exception as e:
        # Restore terminal on any error
        restore_terminal(old_terminal_settings)
        print(f"\n\nError: {e}")
        raise


if __name__ == "__main__":
    main()
