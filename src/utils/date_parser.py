""" Date Parsing Utilities for Daily Standup Agent. Handles parsing of natural language date queries"""

from datetime import datetime, date, timedelta
import re
import pytz
from typing import Tuple
from src.config import TIMEZONE


WAT = pytz.timezone(TIMEZONE)


def get_today_wat() -> date:
    """Get today's date in WAT timezone."""
    return datetime.now(WAT).date()


def get_last_monday() -> date:
    """Get the date of the last Monday (start of current week)."""
    today = get_today_wat()
    # 0 = Monday, 6 = Sunday
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)


def parse_date_query(query: str) -> date:
    """
    Parse a date from natural language query.
    
    Supports:
    - "today" → current date
    - "yesterday" → current date - 1 day
    - "day before yesterday" → current date - 2 days
    - "YYYY-MM-DD" → explicit date
    - "last Friday" → calculate last Friday
    
    Args:
        query: Natural language date query
        
    Returns:
        Parsed date object
        
    Raises:
        ValueError: If date cannot be parsed
    """
    query_lower = query.lower().strip()
    today = get_today_wat()
    
    # Handle "today"
    if "today" in query_lower:
        return today
    
    # Handle "yesterday"
    if "yesterday" in query_lower and "day before yesterday" not in query_lower:
        return today - timedelta(days=1)
    
    # Handle "day before yesterday"
    if "day before yesterday" in query_lower:
        return today - timedelta(days=2)
    
    # Handle explicit date formats (YYYY-MM-DD)
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    date_match = re.search(date_pattern, query)
    if date_match:
        date_str = date_match.group()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")
    
    # Handle "last [day of week]"
    days_of_week = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    for day_name, day_num in days_of_week.items():
        if f"last {day_name}" in query_lower:
            # Calculate days back to the last occurrence of that day
            days_back = (today.weekday() - day_num) % 7
            if days_back == 0:
                days_back = 7  # If today is that day, go back a week
            return today - timedelta(days=days_back)
    
    # Handle "N days ago"
    days_ago_pattern = r'(\d+)\s+days?\s+ago'
    days_ago_match = re.search(days_ago_pattern, query_lower)
    if days_ago_match:
        days = int(days_ago_match.group(1))
        return today - timedelta(days=days)
    
    # Default: assume today if no specific date mentioned
    return today


def parse_date_range_query(query: str) -> Tuple[date, date]:
    """
    Parse a date range from natural language query.
    
    Supports:
    - "this week" → Last Monday to today
    - "last week" → Previous Monday to Sunday
    - "last two weeks" → Two calendar weeks back
    - "last 7 days" → 7 days back from today
    - "last N days" → N days back from today
    - "from [date] to [date]" → Explicit range
    - "[date] to [date]" → Explicit range
    - Single date → That date only (start_date == end_date)
    
    Args:
        query: Natural language date range query
        
    Returns:
        Tuple of (start_date, end_date) inclusive
        
    Raises:
        ValueError: If date range cannot be parsed
    """
    query_lower = query.lower().strip()
    today = get_today_wat()
    
    # Handle "this week" - Last Monday to today
    if "this week" in query_lower:
        last_monday = get_last_monday()
        return (last_monday, today)
    
    # Handle "last week" - Previous Monday to Sunday
    if re.search(r'\blast week\b', query_lower):
        last_monday = get_last_monday()
        # Go back to previous week's Monday
        prev_monday = last_monday - timedelta(days=7)
        prev_sunday = prev_monday + timedelta(days=6)
        return (prev_monday, prev_sunday)
    
    # Handle "last two weeks" - Two calendar weeks back
    if "last two weeks" in query_lower or "last 2 weeks" in query_lower:
        last_monday = get_last_monday()
        # Go back two weeks
        two_weeks_ago_monday = last_monday - timedelta(days=14)
        prev_sunday = last_monday - timedelta(days=1)
        return (two_weeks_ago_monday, prev_sunday)
    
    # Handle "past week" - Last 7 days
    if "past week" in query_lower:
        start_date = today - timedelta(days=6)  # 6 days back + today = 7 days
        return (start_date, today)
    
    # Handle "past two weeks" or "past 2 weeks" - Last 14 days
    if "past two weeks" in query_lower or "past 2 weeks" in query_lower:
        start_date = today - timedelta(days=13)  # 13 days back + today = 14 days
        return (start_date, today)
    
    # Handle "last N days" - N days back from today (inclusive of today)
    last_days_pattern = r'last\s+(\d+)\s+days?'
    last_days_match = re.search(last_days_pattern, query_lower)
    if last_days_match:
        num_days = int(last_days_match.group(1))
        start_date = today - timedelta(days=num_days - 1)
        return (start_date, today)
    
    # Handle "past N days" - N days back from today (inclusive of today)
    past_days_pattern = r'past\s+(\d+)\s+days?'
    past_days_match = re.search(past_days_pattern, query_lower)
    if past_days_match:
        num_days = int(past_days_match.group(1))
        start_date = today - timedelta(days=num_days - 1)
        return (start_date, today)
    
    # Handle explicit date ranges: "from YYYY-MM-DD to YYYY-MM-DD" or "YYYY-MM-DD to YYYY-MM-DD"
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    date_matches = re.findall(date_pattern, query)
    if len(date_matches) >= 2:
        try:
            start = datetime.strptime(date_matches[0], "%Y-%m-%d").date()
            end = datetime.strptime(date_matches[1], "%Y-%m-%d").date()
            if start > end:
                start, end = end, start  # Swap if in wrong order
            return (start, end)
        except ValueError:
            raise ValueError(f"Invalid date format in range")
    
    # Handle single date - return same date as both start and end
    if len(date_matches) == 1:
        try:
            single_date = datetime.strptime(date_matches[0], "%Y-%m-%d").date()
            return (single_date, single_date)
        except ValueError:
            raise ValueError(f"Invalid date format")
    
    # Handle "today" as single date
    if "today" in query_lower:
        return (today, today)
    
    # Handle "yesterday" as single date
    if "yesterday" in query_lower:
        yesterday = today - timedelta(days=1)
        return (yesterday, yesterday)
    
    # Default: today only
    return (today, today)


def format_date_friendly(target_date: date) -> str:
    """
    Format a date in a friendly way.
    
    Args:
        target_date: Date to format
        
    Returns:
        Friendly formatted string (e.g., "Today", "Yesterday", "November 15, 2025")
    """
    today = get_today_wat()
    
    if target_date == today:
        return "Today"
    elif target_date == today - timedelta(days=1):
        return "Yesterday"
    elif target_date == today - timedelta(days=2):
        return "Day Before Yesterday"
    else:
        return target_date.strftime("%B %d, %Y")


def format_date_range_friendly(start_date: date, end_date: date) -> str:
    """
    Format a date range in a friendly way.
    
    Args:
        start_date: Start of range
        end_date: End of range
        
    Returns:
        Friendly formatted string
    """
    if start_date == end_date:
        return format_date_friendly(start_date)
    
    today = get_today_wat()
    last_monday = get_last_monday()
    
    # Check if it's "this week"
    if start_date == last_monday and end_date == today:
        return "This Week"
    
    # Check if it's "last week"
    prev_monday = last_monday - timedelta(days=7)
    prev_sunday = prev_monday + timedelta(days=6)
    if start_date == prev_monday and end_date == prev_sunday:
        return "Last Week"
    
    # Otherwise format as range
    return f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"