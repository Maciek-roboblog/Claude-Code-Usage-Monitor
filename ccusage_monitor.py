#!/usr/bin/env python3

import subprocess
import json
import sys
import time
from datetime import datetime, timedelta, timezone
import os
import argparse
import pytz
from collections import defaultdict
import calendar


def run_ccusage():
    """Execute ccusage blocks --json command and return parsed JSON data."""
    try:
        result = subprocess.run(['ccusage', 'blocks', '--json'], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running ccusage: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return None


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
    green_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    green = '\033[92m'  # Bright green
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    return f"🟢 [{green}{green_bar}{red}{red_bar}{reset}] {percentage:.1f}%"


def create_time_progress_bar(elapsed_minutes, total_minutes, width=50):
    """Create a time progress bar showing time until reset."""
    if total_minutes <= 0:
        percentage = 0
    else:
        percentage = min(100, (elapsed_minutes / total_minutes) * 100)
    
    filled = int(width * percentage / 100)
    
    # Create the bar with blue fill and red empty space
    blue_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    blue = '\033[94m'   # Bright blue
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
    return f"⏰ [{blue}{blue_bar}{red}{red_bar}{reset}] {remaining_time}"


def create_session_progress_bar(used_sessions, total_sessions, width=50):
    """Create a session usage progress bar."""
    if total_sessions <= 0:
        percentage = 0
    else:
        percentage = min(100, (used_sessions / total_sessions) * 100)
    
    filled = int(width * percentage / 100)
    
    # Create the bar with orange fill and gray empty space
    orange_bar = '█' * filled
    gray_bar = '░' * (width - filled)
    
    # Color codes
    orange = '\033[93m'  # Yellow/orange
    gray = '\033[90m'    # Gray
    reset = '\033[0m'
    
    remaining_sessions = max(0, total_sessions - used_sessions)
    return f"📅 [{orange}{orange_bar}{gray}{gray_bar}{reset}] {remaining_sessions} left"


def create_prediction_progress_bar(predicted_tokens, max_tokens, width=50):
    """Create a prediction progress bar for estimated session burn."""
    if max_tokens <= 0:
        percentage = 0
    else:
        percentage = min(100, (predicted_tokens / max_tokens) * 100)
    
    filled = int(width * percentage / 100)
    
    # Create the bar with purple fill and gray empty space
    purple_bar = '█' * filled
    gray_bar = '░' * (width - filled)
    
    # Color codes
    purple = '\033[95m'  # Magenta/purple
    gray = '\033[90m'    # Gray
    reset = '\033[0m'
    
    return f"🔮 [{purple}{purple_bar}{gray}{gray_bar}{reset}] {percentage:.1f}%"


def print_header():
    """Print the stylized header with sparkles."""
    cyan = '\033[96m'
    blue = '\033[94m'
    reset = '\033[0m'
    
    # Sparkle pattern
    sparkles = f"{cyan}✦ ✧ ✦ ✧ {reset}"
    
    print(f"{sparkles}{cyan}CLAUDE TOKEN MONITOR{reset} {sparkles}")
    print(f"{blue}{'=' * 60}{reset}")
    print()


def get_velocity_indicator(burn_rate):
    """Get velocity emoji based on burn rate."""
    if burn_rate < 50:
        return '🐌'  # Slow
    elif burn_rate < 150:
        return '➡️'  # Normal
    elif burn_rate < 300:
        return '🚀'  # Fast
    else:
        return '⚡'  # Very fast


def calculate_hourly_burn_rate(blocks, current_time):
    """Calculate burn rate based on all sessions in the last hour."""
    if not blocks:
        return 0
    
    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = 0
    
    for block in blocks:
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        # Parse start time
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Skip gaps
        if block.get('isGap', False):
            continue
            
        # Determine session end time
        if block.get('isActive', False):
            # For active sessions, use current time
            session_actual_end = current_time
        else:
            # For completed sessions, use actualEndTime or current time
            actual_end_str = block.get('actualEndTime')
            if actual_end_str:
                session_actual_end = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00'))
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
        total_session_duration = (session_actual_end - start_time).total_seconds() / 60  # minutes
        hour_duration = (session_end_in_hour - session_start_in_hour).total_seconds() / 60  # minutes
        
        if total_session_duration > 0:
            session_tokens = block.get('totalTokens', 0)
            tokens_in_hour = session_tokens * (hour_duration / total_session_duration)
            total_tokens += tokens_in_hour
    
    # Return tokens per minute
    return total_tokens / 60 if total_tokens > 0 else 0


def get_next_reset_time(current_time, custom_reset_hour=None, timezone_str='Europe/Warsaw'):
    """Calculate next token reset time based on fixed 5-hour intervals.
    Default reset times in specified timezone: 04:00, 09:00, 14:00, 18:00, 23:00
    Or use custom reset hour if provided.
    """
    # Convert to specified timezone
    try:
        target_tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Warning: Unknown timezone '{timezone_str}', using Europe/Warsaw")
        target_tz = pytz.timezone('Europe/Warsaw')
    
    # If current_time is timezone-aware, convert to target timezone
    if current_time.tzinfo is not None:
        target_time = current_time.astimezone(target_tz)
    else:
        # Assume current_time is in target timezone if not specified
        target_time = target_tz.localize(current_time)
    
    if custom_reset_hour is not None:
        # Use single daily reset at custom hour
        reset_hours = [custom_reset_hour]
    else:
        # Default 5-hour intervals
        reset_hours = [4, 9, 14, 18, 23]
    
    # Get current hour and minute
    current_hour = target_time.hour
    current_minute = target_time.minute
    
    # Find next reset hour
    next_reset_hour = None
    for hour in reset_hours:
        if current_hour < hour or (current_hour == hour and current_minute == 0):
            next_reset_hour = hour
            break
    
    # If no reset hour found today, use first one tomorrow
    if next_reset_hour is None:
        next_reset_hour = reset_hours[0]
        next_reset_date = target_time.date() + timedelta(days=1)
    else:
        next_reset_date = target_time.date()
    
    # Create next reset datetime in target timezone
    next_reset = target_tz.localize(
        datetime.combine(next_reset_date, datetime.min.time().replace(hour=next_reset_hour)),
        is_dst=None
    )
    
    # Convert back to the original timezone if needed
    if current_time.tzinfo is not None and current_time.tzinfo != target_tz:
        next_reset = next_reset.astimezone(current_time.tzinfo)
    
    return next_reset


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Claude Token Monitor - Real-time token usage monitoring')
    parser.add_argument('--plan', type=str, default='pro', 
                        choices=['pro', 'max5', 'max20', 'custom_max'],
                        help='Claude plan type (default: pro). Use "custom_max" to auto-detect from highest previous block')
    parser.add_argument('--reset-hour', type=int, 
                        help='Change the reset hour (0-23) for daily limits')
    parser.add_argument('--timezone', type=str, default='Europe/Warsaw',
                        help='Timezone for reset times (default: Europe/Warsaw). Examples: US/Eastern, Asia/Tokyo, UTC')
    parser.add_argument('--session', action='store_true',
                        help='Enable session monitoring features')
    return parser.parse_args()


def count_monthly_sessions(blocks, current_time):
    """Count sessions in the current month and calculate sessions remaining."""
    if not blocks:
        return 0, 50
    
    # Get current month boundaries
    current_month = current_time.month
    current_year = current_time.year
    
    # Count unique sessions in current month (excluding gaps and active sessions)
    monthly_sessions = 0
    seen_sessions = set()
    
    for block in blocks:
        if block.get('isGap', False):
            continue
            
        start_time_str = block.get('startTime')
        if not start_time_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        
        # Check if session is in current month
        if start_time.month == current_month and start_time.year == current_year:
            # Use session start time as unique identifier
            session_id = start_time_str
            if session_id not in seen_sessions:
                seen_sessions.add(session_id)
                monthly_sessions += 1
    
    sessions_remaining = max(0, 50 - monthly_sessions)
    return monthly_sessions, sessions_remaining


def calculate_max_burn_from_history(blocks):
    """Calculate the maximum burn rate from previous completed sessions."""
    if not blocks:
        return 0
    
    max_burn = 0
    
    for block in blocks:
        if block.get('isGap', False) or block.get('isActive', False):
            continue
            
        start_time_str = block.get('startTime')
        actual_end_str = block.get('actualEndTime')
        
        if not start_time_str or not actual_end_str:
            continue
            
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(actual_end_str.replace('Z', '+00:00'))
        
        duration_minutes = (end_time - start_time).total_seconds() / 60
        
        if duration_minutes > 0:
            tokens = block.get('totalTokens', 0)
            burn_rate = tokens / duration_minutes
            max_burn = max(max_burn, burn_rate)
    
    return max_burn


def predict_session_burn(current_tokens, burn_rate, session_duration_minutes=300):
    """Predict total tokens for current session based on burn rate."""
    if burn_rate <= 0:
        return current_tokens
    
    # Estimate how long session has been running
    if current_tokens > 0:
        estimated_elapsed = current_tokens / burn_rate
        remaining_time = max(0, session_duration_minutes - estimated_elapsed)
        predicted_additional = burn_rate * remaining_time
        return current_tokens + predicted_additional
    
    return burn_rate * session_duration_minutes


def get_token_limit(plan, blocks=None):
    """Get token limit based on plan type."""
    if plan == 'custom_max' and blocks:
        # Find the highest token count from all previous blocks
        max_tokens = 0
        for block in blocks:
            if not block.get('isGap', False) and not block.get('isActive', False):
                tokens = block.get('totalTokens', 0)
                if tokens > max_tokens:
                    max_tokens = tokens
        # Return the highest found, or default to pro if none found
        return max_tokens if max_tokens > 0 else 7000
    
    limits = {
        'pro': 7000,
        'max5': 35000,
        'max20': 140000
    }
    return limits.get(plan, 7000)


def main():
    """Main monitoring loop."""
    args = parse_args()
    
    # For 'custom_max' plan, we need to get data first to determine the limit
    if args.plan == 'custom_max':
        initial_data = run_ccusage()
        if initial_data and 'blocks' in initial_data:
            token_limit = get_token_limit(args.plan, initial_data['blocks'])
        else:
            token_limit = get_token_limit('pro')  # Fallback to pro
    else:
        token_limit = get_token_limit(args.plan)
    
    try:
        # Initial screen clear and hide cursor
        os.system('clear' if os.name == 'posix' else 'cls')
        print('\033[?25l', end='', flush=True)  # Hide cursor
        
        while True:
            # Move cursor to top without clearing
            print('\033[H', end='', flush=True)
            
            data = run_ccusage()
            if not data or 'blocks' not in data:
                print("Failed to get usage data")
                continue
            
            # Find the active block
            active_block = None
            for block in data['blocks']:
                if block.get('isActive', False):
                    active_block = block
                    break
            
            if not active_block:
                print("No active session found")
                continue
            
            # Extract data from active block
            tokens_used = active_block.get('totalTokens', 0)
            
            # Check if tokens exceed limit and switch to custom_max if needed
            if tokens_used > token_limit and args.plan == 'pro':
                # Auto-switch to custom_max when pro limit is exceeded
                new_limit = get_token_limit('custom_max', data['blocks'])
                if new_limit > token_limit:
                    token_limit = new_limit
            
            usage_percentage = (tokens_used / token_limit) * 100 if token_limit > 0 else 0
            tokens_left = token_limit - tokens_used
            
            # Time calculations
            start_time_str = active_block.get('startTime')
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                current_time = datetime.now(start_time.tzinfo)
                elapsed = current_time - start_time
                elapsed_minutes = elapsed.total_seconds() / 60
            else:
                elapsed_minutes = 0
            
            session_duration = 300  # 5 hours in minutes
            remaining_minutes = max(0, session_duration - elapsed_minutes)
            
            # Calculate burn rate from ALL sessions in the last hour
            burn_rate = calculate_hourly_burn_rate(data['blocks'], current_time)
            
            if args.session:
                # Calculate monthly session statistics
                monthly_sessions, sessions_remaining = count_monthly_sessions(data['blocks'], current_time)

                # Calculate max burn rate from historical data
                max_historical_burn = calculate_max_burn_from_history(data['blocks'])

                # Predict total burn for current session
                predicted_total_burn = predict_session_burn(tokens_used, burn_rate)
            else:
                monthly_sessions = sessions_remaining = 0
                max_historical_burn = 0
                predicted_total_burn = tokens_used
            
            # Reset time calculation - use fixed schedule or custom hour with timezone
            reset_time = get_next_reset_time(current_time, args.reset_hour, args.timezone)
            
            # Calculate time to reset
            time_to_reset = reset_time - current_time
            minutes_to_reset = time_to_reset.total_seconds() / 60
            
            # Predicted end calculation - when tokens will run out based on burn rate
            if burn_rate > 0 and tokens_left > 0:
                minutes_to_depletion = tokens_left / burn_rate
                predicted_end_time = current_time + timedelta(minutes=minutes_to_depletion)
            else:
                # If no burn rate or tokens already depleted, use reset time
                predicted_end_time = reset_time
            
            # Color codes
            cyan = '\033[96m'
            green = '\033[92m'
            blue = '\033[94m'
            red = '\033[91m'
            yellow = '\033[93m'
            white = '\033[97m'
            gray = '\033[90m'
            reset = '\033[0m'
            
            # Display header
            print_header()
            
            # Token Usage section
            print(f"📊 {white}Token Usage:{reset}    {create_token_progress_bar(usage_percentage)}")
            print()
            
            # Time to Reset section - calculate progress based on time since last reset
            # Estimate time since last reset (max 5 hours = 300 minutes)
            time_since_reset = max(0, 300 - minutes_to_reset)
            print(f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(time_since_reset, 300)}")
            print()
            
            # Detailed stats
            print(f"🎯 {white}Tokens:{reset}         {white}{tokens_used:,}{reset} / {gray}~{token_limit:,}{reset} ({cyan}{tokens_left:,} left{reset})")
            print(f"🔥 {white}Burn Rate:{reset}      {yellow}{burn_rate:.1f}{reset} {gray}tokens/min{reset}")
            print()
            
            if args.session:
                # Session usage with progress bar
                print(f"📊 {white}Sessions Used:{reset}   {create_session_progress_bar(monthly_sessions, 50)}")
                print()

                # Predicted total burn with progress bar (compare against token limit)
                print(f"🔮 {white}Session Predicted:{reset} {create_prediction_progress_bar(predicted_total_burn, token_limit)}")
                print()

                # Additional stats without bars
                print(f"📊 {white}Max Burn Rate:{reset} {yellow}{max_historical_burn:.1f}{reset} {gray}tokens/min{reset}")
                print(f"🔥 {white}Current Burn:{reset}  {yellow}{burn_rate:.1f}{reset} {gray}tokens/min{reset}")
                print()
            
            # Predictions - convert to configured timezone for display
            try:
                local_tz = pytz.timezone(args.timezone)
            except:
                local_tz = pytz.timezone('Europe/Warsaw')
            predicted_end_local = predicted_end_time.astimezone(local_tz)
            reset_time_local = reset_time.astimezone(local_tz)
            
            predicted_end_str = predicted_end_local.strftime("%H:%M")
            reset_time_str = reset_time_local.strftime("%H:%M")
            print(f"🏁 {white}Predicted End:{reset} {predicted_end_str}")
            print(f"🔄 {white}Token Reset:{reset}   {reset_time_str}")
            print()
            
            # Show notification if we switched to custom_max
            show_switch_notification = False
            if tokens_used > 7000 and args.plan == 'pro' and token_limit > 7000:
                show_switch_notification = True
            
            # Notification when tokens exceed max limit
            show_exceed_notification = tokens_used > token_limit
            
            # Show notifications
            if show_switch_notification:
                print(f"🔄 {yellow}Tokens exceeded Pro limit - switched to custom_max ({token_limit:,}){reset}")
                print()
            
            if show_exceed_notification:
                print(f"🚨 {red}TOKENS EXCEEDED MAX LIMIT! ({tokens_used:,} > {token_limit:,}){reset}")
                print()
            
            # Warning if tokens will run out before reset
            if predicted_end_time < reset_time:
                print(f"⚠️  {red}Tokens will run out BEFORE reset!{reset}")
                print()
            
            # Status line
            current_time_str = datetime.now().strftime("%H:%M:%S")
            print(f"⏰ {gray}{current_time_str}{reset} 📝 {cyan}Smooth sailing...{reset} | {gray}Ctrl+C to exit{reset} 🟨")
            
            # Clear any remaining lines below to prevent artifacts
            print('\033[J', end='', flush=True)
            
            time.sleep(3)
            
    except KeyboardInterrupt:
        # Show cursor before exiting
        print('\033[?25h', end='', flush=True)
        print(f"\n\n{cyan}Monitoring stopped.{reset}")
        # Clear the terminal
        os.system('clear' if os.name == 'posix' else 'cls')
        sys.exit(0)
    except Exception:
        # Show cursor on any error
        print('\033[?25h', end='', flush=True)
        raise


if __name__ == "__main__":
    main()