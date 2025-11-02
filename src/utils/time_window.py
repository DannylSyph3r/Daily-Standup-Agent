"""
Time Window Logic for Daily Standup Agent
Handles WAT timezone and submission window validation
"""
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
    Check if current time is within submission window (9:30 AM - 12:30 PM WAT).
    
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


def get_window_message(user_name: str) -> str:
    """
    Get appropriate message based on window status.
    
    Args:
        user_name: Name of the user
        
    Returns:
        Formatted message for the current window status
    """
    status = get_window_status()
    
    if status == "before":
        return f"""Thanks for being so early, {user_name}! 😊

However, standup submissions don't open until 9:30 AM WAT. 
Please come back then to submit your update.

In the meantime, feel free to ask me for yesterday's summary!"""
    
    elif status == "after":
        return f"""Hey {user_name}!

Unfortunately, today's standup window closed at 12:30 PM WAT. 
Your update for today can no longer be included in the daily summary.

You can submit your standup tomorrow starting at 9:30 AM WAT.

Want to see today's summary? Just ask! 📊"""
    
    else:
        # This shouldn't be called during window, but just in case
        return f"Perfect timing, {user_name}! ✅"


def get_submission_time_wat() -> datetime:
    """Get current submission time in WAT timezone."""
    return get_current_wat_time()