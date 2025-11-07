""" Time Window Logic for Daily Standup Agent. Handles WAT timezone and submission window validation"""

from datetime import datetime, time
import pytz
from src.config import TIMEZONE, WINDOW_START, WINDOW_END


# WAT timezone (West Africa Time - UTC+1)
WAT = pytz.timezone(TIMEZONE)


def get_current_wat_time() -> datetime:
    """Get current time in WAT timezone."""
    return datetime.now(WAT)


def is_within_window() -> bool:
    """
    Check if current time is within submission window.
    
    Returns:
        True if within window, False otherwise
    """
    now = get_current_wat_time().time()
    return WINDOW_START <= now <= WINDOW_END


def get_window_status() -> str:
    """
    Get current window status.
    
    Returns:
        "before", "during", or "after"
    """
    now = get_current_wat_time().time()
    
    if now < WINDOW_START:
        return "before"
    elif now > WINDOW_END:
        return "after"
    else:
        return "during"


def format_time_12h(time_obj: time) -> str:
    """
    Format time object to 12-hour format string.
    
    Args:
        time_obj: time object to format
        
    Returns:
        Formatted time string (e.g., "9:30 AM", "12:30 PM")
    """
    hour = time_obj.hour
    minute = time_obj.minute
    
    period = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    
    return f"{display_hour}:{minute:02d} {period}"


def get_window_message(user_name: str) -> str:
    """
    Get appropriate message based on window status using env configuration.
    
    Args:
        user_name: Name of the user
        
    Returns:
        Formatted message for the current window status
    """
    status = get_window_status()
    
    window_start_str = format_time_12h(WINDOW_START)
    window_end_str = format_time_12h(WINDOW_END)
    
    if status == "before":
        return f"""Thanks for being so early, {user_name}!

However, standup submissions don't open until {window_start_str} WAT. 
Please come back then to submit your update.

In the meantime, feel free to ask me for yesterday's summary!"""
    
    elif status == "after":
        return f"""Hey {user_name}!

Unfortunately, today's standup window closed at {window_end_str} WAT. 
Your update for today can no longer be included in the daily summary.

You can submit your standup tomorrow starting at {window_start_str} WAT.

Want to see today's summary? Just ask!"""
    
    else:
        # This shouldn't be called during window, but just in case
        return f"Perfect timing, {user_name}!"


def get_submission_time_wat() -> datetime:
    """Get current submission time in WAT timezone."""
    return get_current_wat_time()